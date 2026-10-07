#!/usr/bin/env python3
"""Lossless conversation archives: pack, prepare, resume upload, verify, unpack."""
import argparse
import base64
import datetime as dt
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from import_records import Client, digest, load, private_write

PART = 384 * 1024
FORMAT = 'aicalendar.conversation.v1'


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fragments(text):
    # Splitting characters, rather than UTF-8 bytes, preserves all Unicode.
    return [text[i:i + 16000] for i in range(0, len(text), 16000)] or ['']


def pack(header, messages, sources, out, source_names=None):
    """sources contains stable private snapshots, never live files."""
    out = Path(out).expanduser()
    specs = []
    for i, path in enumerate(sources):
        path = Path(path)
        size = path.stat().st_size
        specs.append({'id': f'source-{i}', 'name': source_names[i] if source_names else path.name, 'media_type': 'application/octet-stream', 'bytes': size, 'sha256': file_hash(path), 'parts': max(1, math.ceil(size / PART))})
    expanded = hashlib.sha256()
    size = count = 0
    out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as gz:
        def line(value):
            nonlocal size
            data = json_bytes(value) + b'\n'
            if len(data) > 1048576:
                raise ValueError('Archive line too large; preserve the source and split the normalized content')
            expanded.update(data); size += len(data)
            if size > 512 * 1024 * 1024:
                raise ValueError('Archive exceeds 512 MiB expanded; split the source into explicitly identified volumes, never truncate')
            gz.write(data)
        line({'type': 'header', 'format': FORMAT, 'source': header['source'], 'conversation_id': header['conversation_id'], 'title': header['title'], 'sources': specs})
        seen = set()
        for message in messages:
            identifier = message['id']
            if identifier in seen:
                raise ValueError('Duplicate message ID; retain separate revisions with distinct stable IDs')
            seen.add(identifier)
            text = message['content']
            if not isinstance(text, str):
                text = json.dumps(text, ensure_ascii=False, indent=2)
            pieces = fragments(text)
            for index, piece in enumerate(pieces):
                line({'type': 'message', 'id': identifier, 'role': message['role'], 'at': message.get('at'), 'content': piece, 'part': index, 'parts': len(pieces), 'attributes': message.get('attributes', {})})
            count += 1
        for path, spec in zip(sources, specs):
            with Path(path).open('rb') as source:
                for index in range(spec['parts']):
                    line({'type': 'source_chunk', 'id': spec['id'], 'part': index, 'data': base64.b64encode(source.read(PART)).decode('ascii')})
    encoded_size = out.stat().st_size
    if encoded_size > 128 * 1024 * 1024:
        raise ValueError('Archive exceeds 128 MiB compressed; keep the source and split into explicit volumes')
    manifest = {k: header[k] for k in ('source', 'conversation_id', 'title', 'coverage', 'note')}
    if header.get('source_label'): manifest['source_label'] = header['source_label']
    manifest.update(schema_version=1, captured_at=dt.datetime.now(dt.timezone.utc).isoformat(), sha256=file_hash(out), bytes=encoded_size, parts=math.ceil(encoded_size/PART), expanded_sha256=expanded.hexdigest(), expanded_bytes=size, message_count=count, source_count=len(specs))
    private_write(str(out) + '.manifest.json', manifest)
    return {'archive': str(out), 'manifest': str(out)+'.manifest.json', 'messages': count, 'source_files': len(specs), 'bytes': encoded_size}


def snapshot(source, destination):
    # Copy exactly the observed size. A live log's unfinished tail is retained.
    with Path(source).open('rb') as src, Path(destination).open('xb') as dst:
        os.chmod(destination, 0o600)
        remaining = os.fstat(src.fileno()).st_size
        while remaining:
            data = src.read(min(PART, remaining))
            if not data:
                raise ValueError('Source shrank while copying; retry from a consistent export')
            dst.write(data); remaining -= len(data)


def prepare(path, manifest_path, client, out):
    path = Path(path).expanduser().resolve()
    manifest = load(manifest_path or str(path)+'.manifest.json')
    if file_hash(path) != manifest['sha256'] or path.stat().st_size != manifest['bytes']:
        raise ValueError('Archive changed since packing')
    plan = {'plan_version': 1, 'base_url': client.base, 'archive_file': str(path), 'manifest': manifest}
    plan['digest'] = digest(plan)
    private_write(out, plan)
    return {'plan': str(out), 'messages': manifest['message_count'], 'sources': manifest['source_count'], 'parts': manifest['parts'], 'coverage': manifest['coverage']}


def submit(plan_path, client):
    plan = load(plan_path)
    expected = plan.pop('digest')
    if plan.get('plan_version') != 1 or digest(plan) != expected or plan['base_url'] != client.base:
        raise ValueError('Plan changed or destination differs; do not modify a retry plan')
    manifest = plan['manifest']
    path = Path(plan['archive_file'])
    if file_hash(path) != manifest['sha256'] or path.stat().st_size != manifest['bytes']:
        raise ValueError('Archive differs from the fixed plan')
    archive = client.request('archives/prepare', manifest, retry=True)
    replay = archive['state'] == 'committed'
    if not replay:
        received = set(archive.get('received_parts', []))
        with path.open('rb') as stream:
            for index in range(manifest['parts']):
                data = stream.read(PART)
                if index in received:
                    continue
                client.request(f"archives/{archive['id']}/parts", {'index': index, 'sha256': hashlib.sha256(data).hexdigest(), 'data': base64.b64encode(data).decode('ascii')}, retry=True)
                print(json.dumps({'uploaded_part': index + 1, 'parts': manifest['parts']}), file=sys.stderr)
        client.request(f"archives/{archive['id']}/commit", {}, retry=True)
    stored = client.request('archives/' + archive['id'], retry=True)
    if stored['state'] != 'committed' or stored['manifest']['sha256'] != manifest['sha256'] or stored['manifest']['expanded_sha256'] != manifest['expanded_sha256']:
        raise ValueError('Committed archive receipt verification failed')
    # Read the actual stored bytes, not only a metadata receipt.
    from urllib.request import Request
    h = hashlib.sha256(); size = 0
    req = Request(client.base + '/ingest/v1/archives/' + archive['id'] + '/download', headers={'Authorization': 'Bearer ' + client.token})
    with client.opener.open(req, timeout=120) as response:
        while data := response.read(PART):
            h.update(data); size += len(data)
    if h.hexdigest() != manifest['sha256'] or size != manifest['bytes']:
        raise ValueError('Archive download differs; preserve the plan and source files')
    return {'committed': True, 'verified_download': True, 'replay': replay, 'archive_id': archive['id'], 'messages': manifest['message_count'], 'source_files': manifest['source_count'], 'coverage': manifest['coverage']}


def unpack(path, out):
    out = Path(out).expanduser()
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    files = {}; progress = {}; hashes = {}; counts = {}; message = None
    try:
        with gzip.open(path, 'rt', encoding='utf-8') as src, (out/'messages.jsonl').open('x') as messages:
            os.chmod(out/'messages.jsonl', 0o600)
            header = json.loads(next(src))
            if header['type'] != 'header' or header['format'] != FORMAT:
                raise ValueError('Unknown archive format')
            for spec in header['sources']:
                # Ignore source names for output paths; never trust archive paths.
                target = out / f"original-{len(files):03d}.bin"
                files[spec['id']] = target.open('xb'); os.chmod(target, 0o600)
                progress[spec['id']] = 0; hashes[spec['id']] = hashlib.sha256(); counts[spec['id']] = 0
            for line in src:
                row = json.loads(line)
                if row['type'] == 'message':
                    if row['part'] == 0:
                        if message is not None: raise ValueError('Incomplete preceding message')
                        message = dict(row); message['content'] = ''
                    if message is None or row['id'] != message['id'] or row['part'] != message['part']:
                        raise ValueError('Message fragments are out of order')
                    message['content'] += row['content']; message['part'] += 1
                    if message['part'] == message['parts']:
                        message.pop('part'); message.pop('parts'); messages.write(json.dumps(message, ensure_ascii=False)+'\n'); message = None
                elif row['type'] == 'source_chunk':
                    key = row['id']; data = base64.b64decode(row['data'], validate=True)
                    if progress[key] != row['part']: raise ValueError('Source fragments are out of order')
                    files[key].write(data); hashes[key].update(data); counts[key] += len(data); progress[key] += 1
                else: raise ValueError('Unknown archive record')
            if message is not None: raise ValueError('Incomplete final message')
            for spec in header['sources']:
                key = spec['id']
                if hashes[key].hexdigest() != spec['sha256'] or counts[key] != spec['bytes'] or progress[key] != spec['parts']:
                    raise ValueError('Original source checksum mismatch')
            private_write(out/'sources.json', header)
    finally:
        for stream in files.values(): stream.close()
    return {'unpacked': str(out), 'original_files_verified': len(files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='~/.config/aicalendar/client.json')
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('pack'); p.add_argument('--file', required=True); p.add_argument('--source-file', action='append', default=[]); p.add_argument('--out', required=True);p.add_argument('--source-label')
    p = commands.add_parser('prepare');p.add_argument('--archive', required=True);p.add_argument('--manifest');p.add_argument('--out', required=True)
    p = commands.add_parser('submit');p.add_argument('--plan', required=True)
    p = commands.add_parser('list');p.add_argument('--source', default='');p.add_argument('--conversation-id', default='')
    p = commands.add_parser('unpack');p.add_argument('--archive', required=True);p.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'pack':
            value = load(args.file)
            if args.source_label: value['source_label'] = args.source_label
            with tempfile.TemporaryDirectory(prefix='aicalendar-pack-') as temp:
                sources = []
                for i, source in enumerate([args.file]+args.source_file):
                    target = Path(temp)/f'{i:03d}-{Path(source).name}'; snapshot(source,target);sources.append(target)
                result = pack(value, value['messages'], sources, args.out, source_names=[Path(p).name for p in [args.file]+args.source_file])
        elif args.command == 'unpack': result = unpack(args.archive, args.out)
        else:
            client = Client(args.config)
            if args.command == 'prepare': result = prepare(args.archive,args.manifest,client,args.out)
            elif args.command == 'submit': result = submit(args.plan,client)
            else:
                from urllib.parse import urlencode
                result = client.request('archives?'+urlencode({'source': args.source, 'conversation_id':args.conversation_id,'limit':100}),retry=True)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError, OSError, KeyError, TypeError, EOFError) as error:
        print(str(error),file=sys.stderr);raise SystemExit(1)

if __name__ == '__main__': main()
