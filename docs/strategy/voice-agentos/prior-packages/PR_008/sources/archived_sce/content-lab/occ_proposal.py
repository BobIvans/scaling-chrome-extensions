"""Validate Laya/voice suggestions as data. This module never enqueues jobs."""

import math

from automation_core import identifier, strict_int

ACTIONS = {
    'search_context', 'intake_once', 'qualification_audit', 'draft_work_item',
    'propose_paper_campaign', 'pause_jobs', 'job_status',
}
ROUTES = {
    'inspect_evidence', 'search_context', 'draft_change',
    'propose_paper_campaign', 'needs_context',
}


def validate_proposal(value):
    if not isinstance(value, dict) or set(value) != {
        'action', 'goal', 'source_refs', 'repeat', 'duration_hours',
    }:
        raise ValueError('VOICE_PROPOSAL_SCHEMA')
    if not isinstance(value['action'], str) or value['action'] not in ACTIONS:
        raise ValueError('UNKNOWN_PROPOSED_ACTION')
    if not isinstance(value['goal'], str) or not 1 <= len(value['goal'].encode('utf-8')) <= 8000:
        raise ValueError('BOUNDED_GOAL_REQUIRED')
    refs = value['source_refs']
    if not isinstance(refs, list) or len(refs) > 20:
        raise ValueError('BOUNDED_SOURCE_REFS_REQUIRED')
    for ref in refs:
        identifier(ref)
    if len(set(refs)) != len(refs):
        raise ValueError('UNIQUE_SOURCE_REFS_REQUIRED')
    if value['repeat'] == 'once':
        if value['duration_hours'] is not None:
            raise ValueError('ONCE_HAS_NO_DURATION')
    elif value['repeat'] == 'hourly':
        strict_int(value['duration_hours'], 1, 24)
    else:
        raise ValueError('UNKNOWN_PROPOSED_REPEAT')
    # Goal and source refs are validated but never returned in the summary.
    return {
        'schema': 'occ.voice-proposal-review.v1', 'state': 'REVIEW_REQUIRED',
        'proposed_action': value['action'], 'source_count': len(refs),
        'authority': 'DATA_ONLY', 'action_authority': False,
        'dispatch_allowed': False, 'job_created': False,
    }


def review_route(value):
    if not isinstance(value, dict) or set(value) != {'proposed_route', 'confidence'}:
        raise ValueError('LAYA_ROUTE_SCHEMA')
    route, confidence = value['proposed_route'], value['confidence']
    if not isinstance(route, str) or route not in ROUTES:
        raise ValueError('UNKNOWN_PROPOSED_ROUTE')
    if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError('BOUNDED_CONFIDENCE_REQUIRED')
    return {
        'schema': 'occ.laya-route-review.v1', 'proposed_route': route,
        'state': 'REVIEW_REQUIRED', 'authority': 'DATA_ONLY',
        'action_authority': False, 'dispatch_allowed': False, 'job_created': False,
    }
