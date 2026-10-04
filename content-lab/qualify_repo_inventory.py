"""Reproduce PR004 40k/160k synthetic Git inventory resource observations.

Linux worker getrusage observations are separate from installed Windows receipts.
Cold = first new process, warm = second new process reusing the same store;
OS caches are not evicted. No source checkout, hooks, network or code execution.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo_inventory as inv


def make_fixture(root, count):
    root.mkdir()
    env = inv.git_environment() | {
        'GIT_AUTHOR_NAME': 'Synthetic Fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
        'GIT_COMMITTER_NAME': 'Synthetic Fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
        'GIT_AUTHOR_DATE': '2026-10-04T00:00:00+0000', 'GIT_COMMITTER_DATE': '2026-10-04T00:00:00+0000',
    }
    def git(*args, data=None, stdin=None):
        return subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull, '-C', str(root), *args],
                              input=data, stdin=stdin, capture_output=True, check=True, env=env).stdout.strip()
    git('init', '-q')
    oid = git('hash-object', '-w', '--stdin', data=b'x')
    with tempfile.TemporaryFile() as source:
        for n in range(count):
            source.write(b'100644 blob ' + oid + b'\tf%08d_' % n + b'x' * 210 + b'.py\0')
        source.seek(0)
        tree = git('mktree', '-z', stdin=source)
    head = git('commit-tree', tree.decode(), data=b'Synthetic inventory qualification\n')
    git('update-ref', 'HEAD', head.decode())


def observe(root, store):
    if not Path('/proc/self/status').is_file():
        raise ValueError('LINUX_PROC_RESOURCE_OBSERVATION_REQUIRED')
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        child = subprocess.Popen([sys.executable, '-I', '-B', __file__, '--worker', str(root), str(store)],
                                 stdout=output, stderr=errors)
        while child.poll() is None:
            time.sleep(.01)
        output.seek(0)
        errors.seek(0)
        if child.returncode:
            raise RuntimeError(errors.read(65536).decode('utf-8', errors='replace'))
        result = json.loads(output.read(65536))
        # getrusage inside the owned worker avoids mismatched /proc PID
        # namespaces and includes short-lived Git children between samples.
        if result['application_peak_rss_bytes'] <= 0 or result['git_child_peak_rss_bytes'] <= 0:
            raise ValueError('RSS_OBSERVATION_UNAVAILABLE')
        result.update(rss_method='worker getrusage RUSAGE_SELF and RUSAGE_CHILDREN; Linux KiB to bytes',
                      process_exit=child.returncode)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--worker', nargs=2, type=Path)
    args = parser.parse_args()
    if args.worker:
        root, store = args.worker
        metrics = {}
        profile = {'root': str(root), 'namespace': 'fixture', 'source_roots': ['.'], 'exclusions': []}
        receipt = inv.inventory(store, 'synthetic', profile, metrics=metrics)
        db = inv.repo.db_for(store)
        try:
            tail = dict(db.execute('SELECT ordinal,path,state FROM repo_entries WHERE snapshot_id=? ORDER BY ordinal DESC LIMIT 1', (receipt['snapshotId'],)).fetchone())
        finally:
            db.close()
        import resource
        print(json.dumps({'receipt': receipt, 'metrics': metrics, 'tail': tail,
                          'application_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                          'git_child_peak_rss_bytes': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024,
                          'main_database_bytes': (store / 'content.sqlite3').stat().st_size}))
        return
    if args.output is None or args.output.exists():
        parser.error('--output must be a new directory')
    output = args.output.absolute()
    output.mkdir(parents=True)
    observations = []
    for count in (40000, 160000):
        root, store = output / f'repo-{count}', output / f'store-{count}'
        make_fixture(root, count)
        for temperature in ('cold', 'warm'):
            result = observe(root, store)
            result.update(entries=count, temperature=temperature)
            observations.append(result)
    peaks = [o['application_peak_rss_bytes'] for o in observations]
    growth = max(o['application_peak_rss_bytes'] for o in observations if o['entries'] == 160000) - max(
        o['application_peak_rss_bytes'] for o in observations if o['entries'] == 40000)
    receipt = {'schema': 'occ.repo-inventory-resource-observation.v1',
               'platform': platform.platform(), 'python': platform.python_version(),
               'git': subprocess.run(['git', '--version'], capture_output=True, check=True).stdout.decode().strip(),
               'cold_definition': 'first new process; OS caches were not evicted',
               'warm_definition': 'second new process; same fixture/store; validates and reuses existing snapshot',
               'windows_installed_device': 'NOT_RUN',
               'observations': observations,
               'peak_at_most_64_mib': max(peaks) <= 67108864,
               'fourfold_corpus_rss_growth_bytes': growth,
               'growth_at_most_16_mib': growth <= 16777216}
    (output / 'RESOURCE_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
