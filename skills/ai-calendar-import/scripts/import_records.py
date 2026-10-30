#!/usr/bin/env python3
"""AICalendar v1 client. Standard library only; explicit, resumable imports."""
import argparse
from contextlib import contextmanager
import datetime as dt
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import ssl
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler, ProxyHandler


DEFAULT_CONFIG = '~/.config/aicalendar/client.json'
VPS_CONFIG = '~/.config/aicalendar/client-vps.json'
LAN_NETWORKS = tuple(ipaddress.IPv4Network(value) for value in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load(path):
    return json.loads(Path(path).expanduser().read_text())


def private_write(path, value):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Plans are immutable: never overwrite a previous plan or a symlink.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write('\n')


def check_private(path):
    path = Path(path).expanduser()
    if path.stat().st_mode & 0o077:
        raise ValueError(f'Private file must have mode 0600: {path}')
    return path


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, config=None, via_vps=False):
        settings = load(check_private(config or (VPS_CONFIG if via_vps else DEFAULT_CONFIG)))
        self.base = settings['base_url'].rstrip('/')
        self.via_vps = via_vps
        self._upload_ready = False
        parsed = urlparse(self.base)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('base_url cannot contain credentials, query, or fragment')
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', '::1', 'localhost')):
            raise ValueError('HTTPS is required except for a local loopback demo')
        try:
            address = ipaddress.IPv4Address(parsed.hostname)
        except (ipaddress.AddressValueError, TypeError):
            address = None
        if via_vps:
            if parsed.scheme != 'https' or address is None or not address.is_global or parsed.port != 8443:
                raise ValueError('--via-vps requires the primary VPS public IPv4 HTTPS entrance on port 8443')
            if config is not None and self.base != load(check_private(VPS_CONFIG))['base_url'].rstrip('/'):
                raise ValueError('Custom VPS base_url must match ~/.config/aicalendar/client-vps.json')
        elif parsed.hostname not in ('127.0.0.1', '::1', 'localhost') and not (address is not None and any(address in network for network in LAN_NETWORKS)):
            raise ValueError('Default requests require direct NAS LAN HTTPS to an RFC1918 IPv4 address. --config does not authorize public access; use --via-vps only when the user explicitly requests VPS uploading.')
        self.token = check_private(settings['token_file']).read_text().strip()
        if not self.token:
            raise ValueError('Token is empty')
        ca_file = settings.get('ca_file')
        context = ssl.create_default_context(cafile=str(Path(ca_file).expanduser()) if ca_file else None)
        handlers = [NoRedirect(), HTTPSHandler(context=context)]
        if not via_vps:
            # A LAN destination must not be routed through environment/system proxies.
            handlers.append(ProxyHandler({}))
        self.opener = build_opener(*handlers)

    def network_error(self, error):
        self._upload_ready = False
        route = 'VPS' if self.via_vps else 'NAS LAN'
        return ValueError(f'{route} request failed: {error}. Import stopped without switching routes. Preserve the original plan and files; resume when the same authorized entrance is reachable.')

    def request(self, path, body=None, retry=False, timeout=None):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        if data is not None and len(data) > 1048576:
            raise ValueError('Batch exceeds 1 MiB')
        if data is not None and not self._upload_ready:
            self.request('imports', timeout=8)
            self._upload_ready = True
        attempts = 3 if retry and self.via_vps else 1
        request_timeout = timeout if timeout is not None else (35 if data is not None or self.via_vps else 8)
        for attempt in range(attempts):
            request = Request(self.base + '/ingest/v1/' + path, data=data, headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
            try:
                with self.opener.open(request, timeout=request_timeout) as response:
                    return json.load(response)
            except HTTPError as error:
                try:
                    payload = json.loads(error.read())
                except ValueError:
                    payload = {'error': 'non-JSON response'}
                if error.code in (429, 502, 503, 504) and attempt + 1 < attempts:
                    time.sleep(attempt + 1)
                    continue
                raise ValueError(json.dumps({'http_status': error.code, 'response': payload}, ensure_ascii=False)) from None
            except (URLError, TimeoutError, OSError) as error:
                if attempt + 1 < attempts:
                    time.sleep(attempt + 1)
                    continue
                raise self.network_error(error) from None

    @contextmanager
    def download(self, path):
        request = Request(self.base + '/ingest/v1/' + path, headers={'Authorization': 'Bearer ' + self.token})
        try:
            with self.opener.open(request, timeout=120) as response:
                yield response
        except (URLError, TimeoutError, OSError) as error:
            raise self.network_error(error) from None

    def activities(self, source=None):
        items = []
        while True:
            query = {'offset': len(items), 'limit': 1000, 'include_hidden': 'true'}
            if source:
                query['source'] = source
            page = self.request('activities?' + urlencode(query), retry=True)
            items.extend(page['items'])
            if len(items) >= page['total'] or not page['items']:
                return items


def validate(payload):
    records = payload.get('records')
    if payload.get('schema_version') != 1 or not isinstance(records, list):
        raise ValueError('Expected schema_version=1 and records array')
    keys = set()
    for index, record in enumerate(records):
        required = {'source', 'external_id', 'activity_date', 'timezone', 'title', 'summary', 'tags', 'spans', 'quality', 'provenance', 'record_state', 'user_message_count', 'first_activity_at', 'last_activity_at'}
        if required - record.keys():
            raise ValueError(f'Record {index + 1} missing fields: {sorted(required - record.keys())}')
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', record['source']):
            raise ValueError('Invalid source namespace')
        key = (record['source'], record['external_id'])
        if key in keys or not key[1]:
            raise ValueError('Missing or duplicate external_id in this input')
        keys.add(key)
        dt.date.fromisoformat(record['activity_date'])
        count = record['user_message_count']
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError('user_message_count must be a nonnegative integer or null')
        if (count is None) != (record['quality']['count'] == 'unknown'):
            raise ValueError('Unknown counts require null and quality.count=unknown')
        if record['record_state'] not in ('partial', 'final'):
            raise ValueError('Invalid record_state')
        if not record['title'].strip():
            raise ValueError('Title cannot be empty')
    if not records and not payload.get('coverage'):
        raise ValueError('No records or coverage supplied')
    return records


def prepare(payload, client, upsert):
    records = validate(payload)
    if upsert:
        existing = {}
        for source in sorted({r['source'] for r in records}):
            for item in client.activities(source):
                existing[(source, item['record']['external_id'])] = item
        for record in records:
            record.pop('expected_version', None)
            item = existing.get((record['source'], record['external_id']))
            if item:
                if not record.get('source_label') and item['record'].get('source_label'):
                    record['source_label'] = item['record']['source_label']
                record['expected_version'] = item['version']
    else:
        for record in records:
            record.pop('expected_version', None)
    batches = []
    current = []
    def batch(rows, coverage=None):
        value = {'schema_version': 1, 'mode': 'upsert' if upsert else 'insert_only', 'records': rows}
        if coverage:
            value['coverage'] = coverage
        value['idempotency_key'] = 'skill-' + digest(value)
        return value
    for record in records:
        trial = batch(current + [record])
        if len(trial['records']) > 200 or len(json.dumps(trial, ensure_ascii=False).encode()) > 850000:
            if not current:
                raise ValueError('A single record exceeds the batch size')
            batches.append(batch(current)); current = []
        current.append(record)
    if current:
        batches.append(batch(current))
    # Coverage is committed only after all record batches succeed.
    coverage = payload.get('coverage', [])
    for i in range(0, len(coverage), 40):
        batches.append(batch([], coverage[i:i + 40]))
    plan = {'plan_version': 1, 'base_url': client.base if client else None, 'created_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'batches': batches}
    plan['digest'] = digest(batches)
    return plan


def run(args):
    if args.command == 'validate':
        value = load(args.file)
        records = validate(value)
        return {'valid': True, 'records': len(records), 'note': 'Core offline validation passed; server preview performs authoritative validation.'}
    client = Client(args.config, via_vps=args.via_vps)
    if args.command == 'status':
        return client.request('imports', retry=True)
    if args.command == 'lookup':
        return {'items': client.activities(args.source)}
    if args.command == 'prepare':
        plan = prepare(load(args.file), client, args.upsert)
        private_write(args.out, plan)
        return {'plan': str(Path(args.out).expanduser()), 'batches': len(plan['batches']), 'records': sum(len(b['records']) for b in plan['batches']), 'digest': plan['digest']}
    plan = load(args.plan)
    if plan.get('plan_version') != 1 or plan.get('digest') != digest(plan['batches']):
        raise ValueError('Plan integrity check failed; create a new plan from reviewed input')
    if plan['base_url'] != client.base:
        raise ValueError('Plan destination differs from current client configuration')
    if args.command == 'preview':
        results = [client.request('imports/preview', batch, retry=True) for batch in plan['batches']]
        return {'batches': results, 'conflicts': sum(r['conflicts'] for r in results)}
    results = []
    committed_versions = {}
    for i, batch in enumerate(plan['batches']):
        preview = client.request('imports/preview', batch, retry=True)
        if preview['conflicts']:
            raise ValueError(json.dumps({'stopped_at_batch': i + 1, 'completed_batches': len(results), 'preview': preview}, ensure_ascii=False))
        result = client.request('imports', batch, retry=True)
        receipt = client.request('imports/' + result['id'], retry=True)
        if not receipt['committed'] or receipt['id'] != result['id']:
            raise ValueError('Import receipt verification failed')
        for item in receipt['items']:
            committed_versions[(item['source'], item['external_id'])] = item['version']
        results.append(result)
        print(json.dumps({'progress': i + 1, 'total_batches': len(plan['batches']), 'id': result['id'], 'replay': result['replay']}, ensure_ascii=False), file=sys.stderr)
    expected = {(r['source'], r['external_id']): r for b in plan['batches'] for r in b['records']}
    checked = 0
    superseded = []
    for source in sorted({key[0] for key in expected}):
        found = {(a['record']['source'], a['record']['external_id']): a for a in client.activities(source)}
        for key, record in expected.items():
            if key[0] != source:
                continue
            activity = found.get(key)
            version = committed_versions[key]
            if activity is None or activity['version'] < version:
                raise ValueError(f'Committed record missing or version regressed for {key}; inspect service state before retrying')
            if activity['version'] > version:
                superseded.append({'source': key[0], 'external_id': key[1], 'committed_version': version, 'current_version': activity['version']})
                continue
            stored = activity['record']
            if any(stored.get(k) != record.get(k) for k in ('activity_date', 'user_message_count', 'record_state', 'timezone', 'quality')) or stored.get('source_label', '') != (record.get('source_label') or '').strip() or any(stored.get(k) != record[k].strip() for k in ('title', 'summary')) or stored.get('tags', []) != sorted({tag.strip() for tag in record['tags'] if tag.strip()}):
                raise ValueError(f'Readback differs for {key}; inspect concurrent updates before retrying')
            checked += 1
    return {'committed': True, 'exact_current': not superseded, 'verified_records': checked, 'superseded_records': superseded, 'batches': [{'id': r['id'], 'inserted': r['inserted'], 'updated': r['updated'], 'unchanged': r['unchanged'], 'replay': r['replay']} for r in results], 'calendar_url': client.base + '/'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', help='Private LAN configuration; with --via-vps, base_url must match the primary client-vps.json')
    parser.add_argument('--via-vps', action='store_true', help='Use client-vps.json instead of direct NAS LAN access, only when the user explicitly requests VPS uploading')
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('validate');p.add_argument('--file', required=True)
    p = commands.add_parser('prepare');p.add_argument('--file', required=True);p.add_argument('--out', required=True);p.add_argument('--upsert', action='store_true')
    for name in ('preview', 'submit'):
        p = commands.add_parser(name);p.add_argument('--plan', required=True)
    commands.add_parser('status')
    p = commands.add_parser('lookup');p.add_argument('--source', required=True)
    try:
        args = parser.parse_args()
        result = run(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == 'preview' and result['conflicts']:
            raise SystemExit(2)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
