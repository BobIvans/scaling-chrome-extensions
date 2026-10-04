"""Operator CLI for the same typed action dispatcher as desktop/native IPC."""
import argparse
import json
from pathlib import Path
import sys

# Isolated Python excludes the script directory; use only installed siblings.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from automation_core import load_json
from native_adapter import dispatch


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True,type=Path)
    parser.add_argument('action',choices=['INFO','CREATE','GET','CORRECT','ENQUEUE','STOP','RESUME','BIND',
                          'PACKET_START','PACKET_APPEND','PACKET_SEAL','PACKET_PAGE','RECONCILE','IMPORT_RESULT',
                          'SKILL_RECORD','SKILL_INVOKE','CONTINUE'])
    parser.add_argument('--payload',type=Path)
    args=parser.parse_args(argv)
    try:
        value=load_json(args.payload,limit=16_000) if args.payload else {}
        result=dispatch({'type':'durable.action','action':args.action,'payload':value},args.profile)
    except (OSError,ValueError) as exc:
        print(json.dumps({'ok':False,'error':type(exc).__name__}))
        return 1
    print(json.dumps(result,ensure_ascii=False,indent=2))
    # dispatch returns the typed result directly; failures raise above.
    return 0


if __name__=='__main__':raise SystemExit(main())
