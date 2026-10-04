"""Opt-in experiment wrapper around the existing local Content Lab ASR owner.

Requires a complete, already downloaded model directory. Never downloads models.
Transcript output is private local data; it is never an executable proposal.
"""

import argparse
import json
from pathlib import Path
import sys

from content_lab import MAX_AUDIO_BYTES, MODEL_FILES, _digest_file, transcribe_file
from occ_local import excluded_link


def regular_path(path):
    path = path.expanduser().absolute()
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and excluded_link(part)):
            raise ValueError('LINK_REJECTED')
    return path


def run_experiment(audio, output, model_dir, *, language='ru', threads=4):
    audio, output, model_dir = map(regular_path, (audio, output, model_dir))
    if output.exists():
        raise ValueError('OUTPUT_ALREADY_EXISTS')
    if not audio.is_file() or audio.stat().st_size > MAX_AUDIO_BYTES:
        raise ValueError('INPUT_NOT_FILE')
    if language not in {'ru', 'lv', 'en', 'auto'}:
        raise ValueError('UNSUPPORTED_LANGUAGE')
    before = _digest_file(audio)
    models = {name: _digest_file(regular_path(model_dir / name)) for name in MODEL_FILES}
    receipt = transcribe_file(audio, model_dir, language=None if language == 'auto' else language, threads=threads)
    if _digest_file(audio) != before or receipt['input_sha256'] != before:
        raise ValueError('INPUT_CHANGED_DURING_TRANSCRIPTION')
    if models != {name: _digest_file(regular_path(model_dir / name)) for name in MODEL_FILES}:
        raise ValueError('MODEL_CHANGED_DURING_TRANSCRIPTION')
    receipt.update(action_authority=False, dispatch_allowed=False, quality_evaluated=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also rejects an output created while inference was running.
    regular_path(output)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    return {'state': 'COMPLETE', 'input_sha256': before, 'action_authority': False,
            'dispatch_allowed': False, 'quality_evaluated': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--model-dir', required=True, type=Path)
    parser.add_argument('--language', choices=['ru', 'lv', 'en', 'auto'], default='ru')
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run_experiment(args.input, args.output, args.model_dir,
                                        language=args.language, threads=args.threads)))
        return 0
    except (OSError, ValueError, ImportError, RuntimeError) as exc:
        print(json.dumps({'state': 'BLOCKED', 'error_type': type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
