"""Split oversized conversations into ordered messages and exact source volumes."""
from pathlib import Path
import tempfile
from archive_conversations import pack, file_hash, json_bytes
from import_records import private_write

VOLUME_BYTES = 48 * 1024 * 1024
SINGLE_ARCHIVE_BYTES = 96 * 1024 * 1024


def pack_conversation(header, messages, sources, out, source_names=None):
    """Return every archive; callers must include all volumes in their upload index."""
    messages = list(messages)
    sources = [Path(p) for p in sources]
    names = source_names or [p.name for p in sources]
    # Allow for JSON escaping and base64 expansion before choosing the normal path.
    estimate = sum(p.stat().st_size * 4 // 3 for p in sources)
    estimate += sum(len(json_bytes(m)) * 2 for m in messages)
    if estimate <= SINGLE_ARCHIVE_BYTES:
        return [pack(header, messages, sources, out, source_names=names)]

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix='volumes-', dir=out.parent) as temp:
        root = Path(temp)
        groups, group, size = [], [], 0
        for message in messages:
            length = len(json_bytes(message)) * 2
            if group and size + length > VOLUME_BYTES:
                groups.append(group)
                group, size = [], 0
            group.append(message)
            size += length
        if group:
            groups.append(group)

        pieces, descriptors = [], []
        for index, (source, name) in enumerate(zip(sources, names)):
            spec = {'name': name, 'bytes': source.stat().st_size,
                    'sha256': file_hash(source), 'parts': []}
            with source.open('rb') as stream:
                part = 0
                while True:
                    data = stream.read(VOLUME_BYTES)
                    if not data and part:
                        break
                    part += 1
                    piece = root / f'source-{index:03d}.part-{part:03d}.bin'
                    piece.write_bytes(data)
                    piece.chmod(0o600)
                    pieces.append(piece)
                    spec['parts'].append({'name': piece.name, 'bytes': len(data),
                                          'sha256': file_hash(piece), 'volume': len(pieces)})
                    if not data:
                        break
            descriptors.append(spec)

        total = max(len(pieces), len(groups))
        identifiers = [header['conversation_id']] + [
            header['conversation_id'] + f'-volume-{i:03d}' for i in range(2, total + 1)]
        reassembly = root / 'reassembly.json'
        private_write(reassembly, {
            'format': 'aicalendar-conversation-volumes-v1',
            'conversation_id': header['conversation_id'], 'volumes': identifiers,
            'source_files': descriptors,
            'message_counts': [len(groups[i]) if i < len(groups) else 0 for i in range(total)],
            'note': 'Read message volumes in order. Concatenate each source file\'s parts '
                    'in order and verify its original SHA-256. Volume numbers are one based.',
        })
        results = []
        for index, identifier in enumerate(identifiers):
            volume_header = dict(header, conversation_id=identifier)
            volume_header['note'] += (
                f' Complete archive volume {index + 1}/{total}; read messages and '
                'reassemble exact original source files according to reassembly.json.')
            if index:
                volume_header['title'] = (header['title'] + f' · {index + 1}/{total}')[:160]
            path = out if not index else out.with_name(identifier + '.jsonl.gz')
            volume_sources = [reassembly] + ([pieces[index]] if index < len(pieces) else [])
            results.append(pack(volume_header, groups[index] if index < len(groups) else [],
                                volume_sources, path,
                                source_names=[p.name for p in volume_sources]))
        return results
