#!/usr/bin/env python3
"""Preview (default) or apply the approved 3-release/5-backup retention policy.

Uses only the standard library. Production paths come from the validated portal
registry. Never handles daily/manual backups, live data, or export archives.
"""
import argparse
import collections
import contextlib
import dataclasses
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time

BATCH = re.compile(r"[0-9a-f]{40}\.[A-Za-z0-9]{6}\Z")
STATE = Path('/var/lib/ali-release-retention/state.json')
GATE = Path('/run/lock/ali-release-retention.lock')
REGISTRY = Path('/opt/serverportal/registry.d')
PORTAL_CONFIG = Path('/opt/serverportal/config/portal.json')
DAYS = 7 * 86400


@dataclasses.dataclass
class App:
    id: str
    root: Path
    kind: str
    database: str
    port: int
    units: list


class Busy(Exception):
    pass


def read_small(path, limit=1048576):
    with open(path, 'rb') as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f'oversized metadata: {path}')
    return data


def trusted(path):
    s = path.stat()
    if s.st_uid != 0 or s.st_mode & 0o022:
        raise ValueError(f'not root-managed: {path}')


def load_apps():
    validate = runpy.run_path(str(Path(__file__).with_name('validate-portal.py')))['validate']
    trusted(REGISTRY)
    apps = []
    for link in sorted(REGISTRY.iterdir()):
        if not re.fullmatch(r'[a-z][a-z0-9-]*\.json', link.name):
            raise ValueError('unknown registry entry')
        app_id = link.stem
        target = Path('/opt') / app_id / 'config/portal.json'
        if link.resolve() != target or target.is_symlink():
            raise ValueError(f'unexpected registry target: {app_id}')
        for p in [target, target.parent, target.parent.parent]:
            trusted(p)
        a = validate(read_small(target), app_id)
        resources = {r['id']: r for r in a['resources']}
        for kind in ['backups', 'releases']:
            if resources.get(kind, {}).get('path') != a['root'] + '/' + kind:
                raise ValueError(f'missing {kind} declaration: {app_id}')
        apps.append(App(app_id, Path(a['root']), a['backupKind'], Path(a['database']).name,
                        a['port'], [app_id + '.service']))
    if not apps or any(a.id == 'serverportal' for a in apps):
        raise ValueError('unexpected application registry')
    trusted(PORTAL_CONFIG)
    portal = json.loads(read_small(PORTAL_CONFIG))
    shared = {r['id']: r for r in portal['shared']}
    for kind in ['backups', 'releases']:
        if shared.get('portal-' + kind, {}).get('path') != '/opt/serverportal/' + kind:
            raise ValueError('missing portal retention resource')
    apps.append(App('serverportal', Path('/opt/serverportal'), 'portal', '', 18085,
                    ['serverportal.service', 'serverportal-agent.service']))
    return apps


def tree(path):
    """Return stable, no-follow inode metadata. Link counts are only for sizing."""
    result = []
    dev = path.lstat().st_dev
    def visit(p):
        s = p.lstat()
        if not (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode)) or s.st_dev != dev:
            raise ValueError('symlink, special file or nested mount')
        result.append((str(p.relative_to(path)), s.st_dev, s.st_ino, s.st_mode,
                       s.st_size, s.st_mtime_ns, s.st_blocks, s.st_nlink))
        if stat.S_ISDIR(s.st_mode):
            for name in sorted(os.listdir(p)):
                visit(p / name)
    visit(path)
    return result


def fingerprint(entries):
    # Unlinking another backup changes ctime/nlink of shared media, not its content.
    data = [e[:6] for e in entries]
    return hashlib.sha256(json.dumps(data, separators=(',', ':')).encode()).hexdigest()


def digest(path, cache):
    s = path.stat()
    key = (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if key not in cache:
        with open(path, 'rb') as f:
            cache[key] = hashlib.file_digest(f, 'sha256').hexdigest()
    return cache[key]


def backup_complete(app, path):
    if app.kind == 'sqlite':
        with open(path, 'rb') as f:
            return f.read(16) == b'SQLite format 3\x00'
    if app.kind == 'portal':
        return all((path / p).is_file() for p in ['data/devices.json', 'config/portal.json'])
    m = json.loads(read_small(path / 'manifest.json', 16 * 1048576))
    if m.get('version') not in [1, 2] or not isinstance(m.get('files'), dict) or app.database not in m['files']:
        return False
    for name, sha in m['files'].items():
        rel = Path(name)
        if rel.is_absolute() or '..' in rel.parts or str(rel) != name or not re.fullmatch('[0-9a-f]{64}', sha):
            return False
        if not (path / rel).is_file():
            return False
    return True


def verify_backup(app, path, cache):
    if not backup_complete(app, path):
        raise ValueError(f'incomplete retained backup: {path}')
    if app.kind == 'portal':
        for name in ['data/devices.json', 'config/portal.json']:
            json.loads(read_small(path / name))
        return
    db = path if app.kind == 'sqlite' else path / app.database
    with sqlite3.connect(db.as_uri() + '?mode=ro&immutable=1', uri=True) as conn:
        if conn.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError(f'invalid retained database: {path.name}')
    if app.kind == 'media':
        manifest = json.loads(read_small(path / 'manifest.json', 16 * 1048576))
        for name, sha in manifest['files'].items():
            if digest(path / name, cache) != sha:
                raise ValueError(f'checksum mismatch in retained backup: {path.name}')


def plan_app(app, old_records, now, cache=None):
    cache = {} if cache is None else cache
    for part in ['', 'releases', 'backups']:
        p = app.root / part
        if p.is_symlink() or not p.is_dir():
            raise ValueError(f'unsafe application root: {p}')
    current = read_small(app.root / 'current-commit', 100).decode().strip()
    if not re.fullmatch('[0-9a-f]{40}', current):
        raise ValueError(f'invalid current version: {app.id}')
    releases, backups, protected, records = {}, {}, [], {}
    unverified_releases = set()
    for path in sorted((app.root / 'releases').iterdir()):
        try:
            if not BATCH.fullmatch(path.name):
                raise ValueError('unknown batch name')
            entries = tree(path)
            result = read_small(path / 'result', 32).decode().strip()
            if result not in ['success', 'failed']:
                raise ValueError('unfinished release')
            commit = path.name[:40]
            # A failed upload may have no metadata yet; it is safe only with an explicit recovery result.
            metadata = dict(line.split('=', 1) for line in read_small(path / 'metadata', 2048).decode().splitlines()) if (path / 'metadata').exists() else {}
            if result == 'success' and (metadata.get('commit') != commit or not re.fullmatch('[0-9a-f]{64}', metadata.get('sha256', ''))):
                raise ValueError('missing or invalid release metadata')
            recovery = read_small(path / 'recovery', 32).decode().strip() if (path / 'recovery').exists() else 'unknown'
            releases[path.name] = {'batch': path.name, 'commit': commit, 'result': result,
                                  'finished': (path / 'result').stat().st_mtime,
                                  'recovery': recovery, 'fingerprint': fingerprint(entries),
                                  'sha256': metadata.get('sha256'), 'entries': entries}
        except (OSError, ValueError) as e:
            unverified_releases.add(path.name)
            protected.append({'kind': 'releases', 'name': path.name, 'reason': str(e)})
    success = sorted((r for r in releases.values() if r['result'] == 'success'), key=lambda r: (r['finished'], r['batch']), reverse=True)
    current_batches = {r['batch'] for r in releases.values() if r['commit'] == current}
    if not any(r['commit'] == current for r in success):
        raise ValueError(f'current version has no successful release record: {app.id}')
    keep_releases = {r['batch'] for r in success[:3]} | current_batches
    latest_success = success[0]['finished']
    def eligible(r):
        return r['result'] == 'success' or (r['result'] == 'failed' and r['recovery'] in ['healthy', 'not-needed'] and
                now - r['finished'] > DAYS and latest_success > r['finished'])
    for name, r in releases.items():
        if not eligible(r):
            keep_releases.add(name)
            protected.append({'kind': 'releases', 'name': name, 'reason': 'failed batch lacks safe recovery, age or later success'})
    for path in sorted((app.root / 'backups').iterdir()):
        if not path.name.startswith('before-deploy-'):
            continue
        batch = None
        try:
            batch = path.name[len('before-deploy-'):]
            if app.kind == 'sqlite':
                if not batch.endswith('.sqlite'):
                    raise ValueError('unknown backup name')
                batch = batch[:-7]
            if not BATCH.fullmatch(batch):
                raise ValueError('unknown backup batch')
            entries = tree(path)
            fp = fingerprint(entries)
            r = releases.get(batch)
            if r is None:
                r = old_records.get(path.name)
                if not r or r.get('fingerprint') != fp or r.get('batch') != batch:
                    raise ValueError('missing trusted release receipt')
            verify_backup(app, path, cache)
            receipt = {k: r[k] for k in ['batch', 'commit', 'result', 'finished', 'recovery']}
            receipt['fingerprint'] = fp
            records[path.name] = receipt
            backups[path.name] = dict(receipt, entries=entries)
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as e:
            protected.append({'kind': 'backups', 'name': path.name, 'reason': str(e)})
            # An unverified backup must not lose its only release evidence.
            if batch in releases:
                keep_releases.add(batch)
    ordered = sorted(backups, key=lambda n: (backups[n]['finished'], n), reverse=True)
    keep_backups = set(ordered[:5])
    for name, r in backups.items():
        if r['batch'] in keep_releases or r['batch'] in unverified_releases or not eligible(r):
            keep_backups.add(name)
    deletes = []
    # Backups are deleted first. Receipts preserve provenance of the extra retained backups.
    for kind, items, kept in [('backups', backups, keep_backups), ('releases', releases, keep_releases)]:
        for name, r in items.items():
            if name not in kept:
                deletes.append({'kind': kind, 'name': name, 'fingerprint': r['fingerprint'], 'entries': r['entries']})
    return {'app': app.id, 'current': current, 'keep_releases': sorted(keep_releases),
            'keep_backups': sorted(keep_backups), 'protected': protected, 'delete': deletes}, records, releases


def verify_kept(app, plan, releases, cache):
    for name in plan['keep_backups']:
        verify_backup(app, app.root / 'backups' / name, cache)
    for name in plan['keep_releases']:
        r = releases[name]
        if r['result'] == 'success':
            binary = app.root / 'releases' / name / ('portal' if app.kind == 'portal' else app.id)
            if digest(binary, cache) != r['sha256']:
                raise ValueError(f'retained program checksum mismatch: {app.id}/{name}')
    current = [r for r in releases.values() if r['commit'] == plan['current'] and r['result'] == 'success']
    live = app.root / 'bin' / ('portal' if app.kind == 'portal' else app.id)
    if digest(live, cache) not in {r['sha256'] for r in current}:
        raise ValueError(f'running program does not match current-commit: {app.id}')


def reclaim_bytes(plans):
    nodes = {}
    for p in plans:
        for d in p['delete']:
            for e in d['entries']:
                key = (e[1], e[2])
                n = nodes.setdefault(key, [0, e[7], e[6] * 512, stat.S_ISDIR(e[3])])
                n[0] += 1
    return sum(n[2] for n in nodes.values() if n[3] or n[0] == n[1])


def atomic_state(path, records):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump({'version': 1, 'apps': records}, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def remove_checked(parent, item):
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        path = parent / item['name']
        if fingerprint(tree(path)) != item['fingerprint']:
            raise ValueError(f'candidate changed: {path}')
        if path.is_dir():
            if not shutil.rmtree.avoids_symlink_attacks:
                raise ValueError('fd-based rmtree is required')
            shutil.rmtree(item['name'], dir_fd=fd)
        else:
            os.unlink(item['name'], dir_fd=fd)
    finally:
        os.close(fd)


@contextlib.contextmanager
def lock(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | (0 if path == GATE else os.O_CREAT), 0o600)
    try:
        info = os.fstat(fd)
        if info.st_uid != 0 or info.st_mode & 0o022 or not stat.S_ISREG(info.st_mode):
            raise ValueError(f'unsafe lock: {path}')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise Busy(f'lock held: {path.name}') from e
        yield
    finally:
        os.close(fd)


def run(*args):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20).stdout


def idle_and_healthy(apps):
    for app in apps:
        for unit in app.units:
            if run('systemctl', 'show', unit, '-p', 'ActiveState', '--value').strip() != 'active':
                raise Busy(f'application is not healthy: {unit}')
        run('curl', '--fail', '--silent', '--max-time', '5', f'http://127.0.0.1:{app.port}/healthz')
        if app.kind != 'portal':
            state = run('systemctl', 'show', app.id + '-backup.service', '-p', 'ActiveState', '--value').strip()
            if state not in ['inactive', 'failed']:
                raise Busy(f'backup task active: {app.id}')
    job = json.loads(run('curl', '--fail', '--silent', '--max-time', '5', '--unix-socket',
                         '/run/serverportal/agent.sock', 'http://localhost/jobs'))
    if job.get('state') in ['running', 'queued']:
        raise Busy('portal archive task active')
    for p in Path('/proc').glob('[0-9]*/comm'):
        try:
            if p.read_text().strip() == 'ids':
                raise Busy('cloud backup task active')
        except (FileNotFoundError, ProcessLookupError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='delete eligible items; default is read-only preview')
    parser.add_argument('--expect-plan', help='require this preview digest before deletion')
    args = parser.parse_args()
    os.umask(0o077)
    if os.geteuid() != 0:
        parser.error('run as root on the server')
    try:
        apps = load_apps()
        with contextlib.ExitStack() as stack:
            stack.enter_context(lock(GATE))
            for app in sorted(apps, key=lambda a: a.id):
                stack.enter_context(lock(Path('/run/lock') / (app.id + '-deploy.lock')))
            idle_and_healthy(apps)
            state = json.loads(read_small(STATE, 16 * 1048576)) if STATE.exists() else {'version': 1, 'apps': {}}
            if state.get('version') != 1 or not isinstance(state.get('apps'), dict):
                raise ValueError('invalid retention state')
            plans, receipts, cache = [], {}, {}
            for app in apps:
                plan, records, releases = plan_app(app, state['apps'].get(app.id, {}), time.time(), cache)
                verify_kept(app, plan, releases, cache)
                plans.append(plan)
                receipts[app.id] = records
            report_plans = [{**p, 'delete': [{k: v for k, v in d.items() if k != 'entries'} for d in p['delete']]} for p in plans]
            plan_sha = hashlib.sha256(json.dumps(report_plans, sort_keys=True).encode()).hexdigest()
            report = {'mode': 'apply' if args.apply else 'preview', 'plan_sha256': plan_sha,
                      'estimated_reclaim_bytes': reclaim_bytes(plans), 'apps': report_plans}
            if args.expect_plan and args.expect_plan != plan_sha:
                raise ValueError('preview changed; generate and review a new plan')
            print(json.dumps(report, ensure_ascii=False), flush=True)
            if args.apply:
                # Write provenance before removing any release record. A crash is safe to retry.
                atomic_state(STATE, receipts)
                idle_and_healthy(apps)
                for app, plan in zip(apps, plans):
                    if read_small(app.root / 'current-commit', 100).decode().strip() != plan['current']:
                        raise ValueError('current version changed')
                    for item in plan['delete']:
                        print(json.dumps({'event': 'delete-intent', 'app': app.id, 'kind': item['kind'], 'name': item['name']}), flush=True)
                        remove_checked(app.root / item['kind'], item)
                        if item['kind'] == 'backups':
                            receipts[app.id].pop(item['name'], None)
                        print(json.dumps({'event': 'deleted', 'app': app.id, 'kind': item['kind'], 'name': item['name']}), flush=True)
                atomic_state(STATE, receipts)
                print(json.dumps({'event': 'complete', 'deleted': sum(len(p['delete']) for p in plans)}), flush=True)
    except Busy as e:
        print(json.dumps({'event': 'skipped', 'reason': str(e)}), flush=True)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, subprocess.SubprocessError) as e:
        # Never print command output (portal configuration and backups contain secrets).
        print(json.dumps({'event': 'error', 'reason': str(e)}), file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
