"""Foreground, resumable repository scan without Native Messaging deadlines."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_context as repo
from repo_manifest import operator_scope, write_manifest


def scan(profile_path, alias, *, snapshot_id=None, page_rows=100, progress=lambda status: None):
    store, source = operator_scope(profile_path, alias)
    snapshot_id = snapshot_id or repo.start_scan(store, alias, source)
    while True:
        if operator_scope(profile_path, alias) != (store, source):
            raise ValueError('PROFILE_CHANGED')
        db = repo.db_for(store)
        try:
            snap = repo.load_snapshot(db, source['namespace'], snapshot_id)
            if snap['alias'] != alias or json.loads(snap['profile']) != source:
                raise ValueError('PROFILE_CHANGED')
        finally:
            db.close()
        status = repo.scan_page(store, source['namespace'], snapshot_id, limit=page_rows)
        progress({k: status[k] for k in ('snapshot_id', 'cursor', 'total', 'state', 'counts')})
        if status['state'] == 'CORRUPT':
            raise ValueError('CONTEXT_CORRUPT')
        if status['state'] == 'COMPLETE':
            return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--resume-snapshot')
    parser.add_argument('--manifest-output', type=Path)
    args = parser.parse_args(argv)
    try:
        status = scan(args.profile, args.repository, snapshot_id=args.resume_snapshot,
                      progress=lambda value: print(json.dumps(value), file=sys.stderr))
        if args.manifest_output:
            store, source = operator_scope(args.profile, args.repository)
            batch = write_manifest(store, args.repository, source, status['snapshot_id'], args.manifest_output)
            status['batch_id'] = batch['batch_id']
        print(json.dumps(status, ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({'state': 'BLOCKED', 'reason': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
