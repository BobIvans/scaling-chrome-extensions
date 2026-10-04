"""Text, final transcripts and advisory proposals share one registry compiler.

Only the loaded operator registry defines capabilities/effects. Source content,
Laya and model responses never register handlers, commands, grants or targets.
"""
from __future__ import annotations

import copy
import re

from automation_core import digest, identifier

OPERATIONS = {'prepare_repo_context', 'find_context', 'compile_ai_packet',
              'show_packet', 'request_more_context', 'inspect_result', 'send_packet'}
EFFECTS = {'LOCAL_READ', 'LOCAL_WRITE', 'AI_MESSAGE'}
CRITICAL = {'repo', 'destination', 'mode', 'amount', 'path'}


def exact(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or set(value) - set(required) - set(optional):
        raise ValueError('ACTION_SCHEMA')
    return value


def text(value):
    if not isinstance(value, str) or not value.strip() or '\0' in value:
        raise ValueError('ACTION_TEXT_REQUIRED')
    return value


def registry(config):
    exact(config, {'schema', 'enabled', 'version', 'capabilities', 'repositories', 'namespaces'},
          {'browser', 'laya', 'voice', 'grants', 'dependency_versions'})
    if config['schema'] != 'occ.action-registry.v1' or config['enabled'] is not True:
        raise ValueError('ACTION_OPERATOR_REGISTRY_REQUIRED')
    text(config['version'])
    if not isinstance(config['capabilities'], dict) or not isinstance(config['repositories'], dict):
        raise ValueError('ACTION_REGISTRY_SCHEMA')
    if not isinstance(config['namespaces'], list) or not config['namespaces']:
        raise ValueError('ACTION_NAMESPACE_REQUIRED')
    for namespace in config['namespaces']:
        identifier(namespace)
    for name, cap in config['capabilities'].items():
        identifier(name)
        exact(cap, {'operation', 'version', 'effect', 'required_slots', 'aliases'})
        if cap['operation'] not in OPERATIONS or cap['effect'] not in EFFECTS:
            raise ValueError('ACTION_REGISTERED_HANDLER_REQUIRED')
        expected = 'AI_MESSAGE' if cap['operation'] == 'send_packet' else 'LOCAL_WRITE' if cap['operation'] in {'prepare_repo_context', 'compile_ai_packet'} else 'LOCAL_READ'
        if cap['effect'] != expected:
            raise ValueError('ACTION_EFFECT_MISMATCH')
        text(cap['version'])
        if not isinstance(cap['required_slots'], list) or not set(cap['required_slots']) <= CRITICAL | {'namespace', 'packet_id'}:
            raise ValueError('ACTION_SLOT_SCHEMA')
        if not isinstance(cap['aliases'], list):
            raise ValueError('ACTION_ALIAS_SCHEMA')
        for alias in cap['aliases']:
            text(alias)
    return config


def route_known(raw, config):
    """Literal command prefix only; never infer effects from free prose."""
    matches = set()
    command = raw.strip().casefold()
    for name, cap in config['capabilities'].items():
        for alias in cap['aliases']:
            if command == alias.casefold() or command.startswith(alias.casefold() + ' '):
                matches.add(name)
    return next(iter(matches)) if len(matches) == 1 else None


def compile_intent(value, config):
    config = registry(config)
    exact(value, {'text', 'modality', 'slots', 'criteria', 'source_refs'}, {'command', 'steps', 'original_text', 'author'})
    raw = text(value['text'])
    for key in ['original_text','author']:
        if key in value:
            text(value[key])
    if value['modality'] not in {'TEXT', 'VOICE', 'LAYA_PROPOSAL'}:
        raise ValueError('ACTION_INPUT_MODALITY')
    if not isinstance(value['slots'], dict) or set(value['slots']) - CRITICAL - {'namespace', 'packet_id'}:
        raise ValueError('ACTION_SLOT_SCHEMA')
    for slot in value['slots'].values():
        if slot is not None:
            text(slot)
    for field in ['criteria', 'source_refs']:
        if not isinstance(value[field], list):
            raise ValueError('ACTION_LIST_SCHEMA')
        for item in value[field]:
            text(item)
    if not value['criteria'] or len(set(value['source_refs'])) != len(value['source_refs']):
        raise ValueError('ACTION_CRITERIA_OR_UNIQUE_REFS_REQUIRED')
    command = value.get('command') or route_known(raw, config)
    if command not in config['capabilities']:
        return {'state': 'UNKNOWN_CAPABILITY', 'development_request': {
            'schema': 'occ.development-request.v1', 'text': raw, 'criteria': value['criteria'],
            'source_refs': value['source_refs'], 'scope': value['slots'], 'authority': 'PROPOSAL_ONLY'}}
    capability = config['capabilities'][command]
    slots = copy.deepcopy(value['slots'])
    missing = [slot for slot in capability['required_slots'] if not slots.get(slot)]
    if capability['effect']=='AI_MESSAGE' and slots.get('mode')!='SEND':
        missing.append('mode_SEND')
    namespace = slots.get('namespace')
    if namespace and namespace not in config['namespaces']:
        raise ValueError('ACTION_NAMESPACE_OUTSIDE_SCOPE')
    repo = slots.get('repo')
    if repo and repo not in config['repositories']:
        missing.append('repo')
    # A typed preview must retain negation/mode in the source; disallow a
    # contradictory write/send command, rather than ignore its negation.
    if capability['effect'] == 'AI_MESSAGE' and (re.search(r'\b(?:не|not|never|no)\s+(?:send|отправ\w*)\b', raw, re.I) or
            re.search(r'\b(?:dry[ -]run|preview[ -]only|без\s+отправ\w*)\b',raw,re.I)):
        missing.append('effect_conflict')
    if missing:
        return {'state': 'NEEDS_INPUT', 'missing_slots': sorted(set(missing)), 'slots': slots}
    steps = value.get('steps') or [{'id': 'main', 'capability': command, 'dependencies': [], 'input_refs': value['source_refs']}]
    steps = validate_dag(steps, config)
    # A proposal DAG cannot smuggle in a capability with a different effect
    # or required slots than the selected command.
    for step in steps:
        cap = config['capabilities'][step['capability']]
        if not set(step['input_refs']) <= set(value['source_refs']):
            raise ValueError('ACTION_DAG_MISSING_INPUT')
        if cap['effect'] != capability['effect'] or any(not slots.get(s) for s in cap['required_slots']):
            raise ValueError('ACTION_PLAN_SCOPE_MISMATCH')
    semantic = {'schema': 'occ.semantic-plan.v1', 'canonicalizer': 'core-json.v1',
                'registry_digest': digest(config), 'command': command, 'capability': capability,
                'goal': raw, 'slots': slots, 'criteria': value['criteria'],
                'source_refs': value['source_refs'], 'steps': steps}
    return {'state': 'COMPILED', 'plan': semantic, 'semantic_hash': digest(semantic)}


def validate_dag(steps, config):
    if not isinstance(steps, list) or not steps:
        raise ValueError('ACTION_DAG_REQUIRED')
    by_id = {}
    for step in steps:
        exact(step, {'id', 'capability', 'dependencies', 'input_refs'})
        name = identifier(step['id'])
        if name in by_id or step['capability'] not in config['capabilities']:
            raise ValueError('ACTION_DAG_DUPLICATE_OR_UNKNOWN')
        if not isinstance(step['dependencies'], list) or not isinstance(step['input_refs'], list):
            raise ValueError('ACTION_DAG_INPUTS')
        for ref in step['input_refs']:
            text(ref)
        by_id[name] = step
    done = set()
    ordered = []
    # Iterative Kahn pass avoids recursion depth as a hidden DAG size ceiling.
    pending = {key: set(row['dependencies']) for key, row in by_id.items()}
    if any(not deps <= by_id.keys() for deps in pending.values()):
        raise ValueError('ACTION_DAG_MISSING_DEPENDENCY')
    while pending:
        ready = [key for key, deps in pending.items() if not deps - done]
        if not ready:
            raise ValueError('ACTION_DAG_CYCLE')
        for key in ready:
            done.add(key)
            ordered.append(copy.deepcopy(by_id[key]))
            del pending[key]
    return ordered


def review_roles(intent, evidence, planner, critic):
    """Explicit role outputs; no role is an authority source."""
    exact(evidence, {'available_refs', 'missing_refs'})
    exact(planner, {'intent_hash', 'proposal'})
    exact(critic, {'intent_hash', 'verdict', 'missing_refs'})
    if planner['intent_hash'] != digest(intent) or critic['intent_hash'] != digest(intent):
        raise ValueError('ACTION_ROLE_INTENT_MISMATCH')
    if critic['verdict'] not in {'ACCEPT', 'RETRIEVE', 'REJECT'}:
        raise ValueError('ACTION_CRITIC_VERDICT')
    missing = sorted(set(evidence['missing_refs']) | set(critic['missing_refs']))
    return {'state': 'NEEDS_CONTEXT' if missing else 'PROPOSAL_REVIEW',
            'missing_refs': missing, 'planner': planner, 'critic': critic, 'authority': 'DATA_ONLY'}


class LayaAdapter:
    """Only an explicit, already installed integration may supply proposals."""
    def __init__(self, interface=None, version=None):
        self.interface, self.version = interface, version

    def discover(self):
        state = 'AVAILABLE' if callable(self.interface) and self.version else 'UNKNOWN' if self.interface else 'UNAVAILABLE'
        return {'state': state, 'version': self.version, 'fallback': 'DIRECT_TYPED_UI', 'vendor_json_import': 'NOT_ASSERTED'}

    def propose(self, value, config):
        if self.discover()['state'] != 'AVAILABLE':
            return {'state': 'UNAVAILABLE', 'fallback': 'DIRECT_TYPED_UI'}
        proposal = self.interface(copy.deepcopy(value))
        exact(proposal, {'text', 'modality', 'slots', 'criteria', 'source_refs'}, {'command', 'steps', 'original_text', 'author'})
        proposal['modality'] = 'LAYA_PROPOSAL'
        return compile_intent(proposal, config)


def permission_diff(old, new):
    fields={'hosts','roots','targets','effects'}
    exact(old,fields);exact(new,fields)
    for scopes in [old,new]:
        for values in scopes.values():
            if not isinstance(values,list):
                raise ValueError('ACTION_PERMISSION_SCHEMA')
            for value in values:text(value)
    added={key:sorted(set(new[key])-set(old[key])) for key in fields}
    removed={key:sorted(set(old[key])-set(new[key])) for key in fields}
    return {'added':added,'removed':removed,'requires_new_scope':any(added.values()),
            'compatible_grant_reuse':not any(added.values())}
