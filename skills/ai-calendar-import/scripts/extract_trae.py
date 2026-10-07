#!/usr/bin/env python3
"""Extract local TraeX user activity to a private review draft; never uploads.

Uses the UI history projection where available. Falls back only to explicitly
typed user events or user.text with original create_time; never counts raw roles.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo
from import_records import private_write


def connect(path):
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    return connection


def text_content(item):
    content = item.get('content', [])
    if isinstance(content, str):
        return content
    return '\n'.join(part.get('text', '') for part in content if isinstance(part, dict) and part.get('type') in ('text', 'input_text'))


def timestamp(value):
    if isinstance(value, (int, float)):
        if value > 10**11:
            value /= 1000
        return dt.datetime.fromtimestamp(value, dt.timezone.utc)
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(dt.timezone.utc)


def fallback(path):
    messages = {}
    revision = False
    malformed = 0
    for line in path.open():
        try:
            record = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        payload = record.get('payload', {})
        kind = record.get('type')
        if not isinstance(payload, dict):
            continue
        revision |= kind == 'compacted' or payload.get('type') == 'thread_rolled_back' or (kind == 'history_mutation' and payload.get('operation') == 'replace')
        candidates = []
        if kind == 'event_msg' and payload.get('type') == 'user_message':
            candidates.append((record.get('timestamp'), payload.get('message', ''), 'legacy_user_event'))
        if kind == 'history_mutation':
            for item in payload.get('items', []):
                if not isinstance(item, dict) or item.get('role') != 'user':
                    continue
                metadata = item.get('internal_chat_message_metadata_passthrough') or {}
                if 'user.text' in metadata.get('content_item_kinds', []) and metadata.get('create_time') is not None:
                    candidates.append((metadata['create_time'], text_content(item), 'original_user_text'))
        for created, text, method in candidates:
            if created is None:
                continue
            try:
                when = timestamp(created)
            except (ValueError, TypeError, OSError):
                continue
            # Compaction can assign new item IDs to identical original messages.
            key = (round(when.timestamp(), 3), hashlib.sha256(text.encode()).hexdigest())
            messages.setdefault(key, (when, text, method))
    return list(messages.values()), revision, malformed


def extract(args):
    home = Path(args.cli_home).expanduser().resolve()
    source_db = home / 'state_5.sqlite'
    if not source_db.exists():
        raise ValueError('Expected TraeX state_5.sqlite is missing; inspect this version instead of guessing its schema')
    state = connect(source_db)
    history_path = home / 'thread_history_1.sqlite'
    history = connect(history_path) if history_path.exists() else None
    zone = ZoneInfo(args.timezone)
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    if start > end:
        raise ValueError('Start date must not exceed end date')
    sessions_root = (home / 'sessions').resolve()
    report = collections.Counter()
    records, contexts = [], []
    unknown = []
    for thread in state.execute('SELECT id,source,title,name,rollout_path FROM threads'):
        report['threads_seen'] += 1
        if thread['source'] != 'cli':
            report['noninteractive_or_subagent_skipped'] += 1
            continue
        path = Path(thread['rollout_path']).expanduser().resolve()
        # Only read the actual session directory, not arbitrary paths from a DB row.
        if not path.is_relative_to(sessions_root) or not path.is_file():
            report['missing_or_external_rollout'] += 1
            continue
        messages = []
        method = 'history_projection'
        count_quality = 'observed'
        if history is not None:
            try:
                for row in history.execute("SELECT created_at_ms,item_json FROM thread_items WHERE thread_id=? AND item_type='userMessage' ORDER BY created_at_ms,rollout_ordinal", (thread['id'],)):
                    item = json.loads(row['item_json'])
                    messages.append((timestamp(row['created_at_ms']), text_content(item), 'projected_user_message'))
                projection = history.execute('SELECT has_revision_controls FROM thread_history_projection_state WHERE thread_id=?', (thread['id'],)).fetchone()
                if projection and projection['has_revision_controls']:
                    count_quality = 'estimated'
            except (sqlite3.OperationalError, ValueError, TypeError) as error:
                raise ValueError('History projection schema or timestamps changed; review before importing') from error
        if not messages:
            method = 'explicit_user_event_fallback'
            messages, revision, malformed = fallback(path)
            report['malformed_or_unfinished_lines'] += malformed
            count_quality = 'estimated'
            if not messages:
                report['no_recoverable_user_messages'] += 1
                continue
        report[method + '_threads'] += 1
        days = collections.defaultdict(list)
        # A message ID can be regenerated, so de-duplicate identical original time/content.
        seen = set()
        for when, text, origin in messages:
            key = (round(when.timestamp(), 3), hashlib.sha256(text.encode()).hexdigest())
            if key in seen:
                continue
            seen.add(key)
            day = when.astimezone(zone).date()
            if start <= day <= end:
                days[day.isoformat()].append((when, text, origin))
        for day, rows in sorted(days.items()):
            rows.sort(key=lambda r: r[0])
            existing_title = (thread['name'] or thread['title'] or '').strip()
            if not existing_title:
                existing_title = '待整理的 AI 会话'
            external_id = thread['id'] + '/' + day
            record = {
                'source': args.source, 'external_id': external_id, 'conversation_id': thread['id'],
                'activity_date': day, 'timezone': args.timezone,
                'first_activity_at': rows[0][0].isoformat(), 'last_activity_at': rows[-1][0].isoformat(),
                'user_message_count': len(rows), 'title': existing_title[:160], 'summary': '', 'tags': [], 'spans': [],
                'quality': {'count': count_quality, 'time': 'observed_timestamps', 'topic': 'source_title'},
                'provenance': {'method': 'trae_' + method, 'producer': 'ai-calendar-import', 'source_ref': thread['id'], 'produced_at': dt.datetime.now(dt.timezone.utc).isoformat()},
                'record_state': 'partial' if day >= dt.datetime.now(zone).date().isoformat() else 'final',
            }
            records.append(record)
            contexts.append({'source': args.source, 'external_id': external_id, 'title': record['title'], 'count_quality': count_quality, 'user_messages': [{'at': when.isoformat(), 'text': text[:args.snippet_chars]} for when, text, _ in rows[:args.max_snippets]], 'total_user_messages': len(rows), 'needs_topic_review': True})
    state.close()
    if history:
        history.close()
    payload = {'schema_version': 1, 'mode': 'insert_only', 'records': records, 'coverage': [{'source': args.source, 'from': args.start, 'to': args.end, 'status': 'partial', 'note': '按本地可恢复历史整理；投影、回退与平台历史保留可能影响完整性。'}]}
    private_write(args.out, payload)
    private_write(args.context_out, {'review_context': contexts, 'diagnostics': dict(report), 'note': 'Local sensitive excerpts for topic review; never send this file to the calendar API or commit it.'})
    return {'draft': str(Path(args.out).expanduser()), 'review_context': str(Path(args.context_out).expanduser()), 'records': len(records), 'recoverable_user_messages': sum(r['user_message_count'] for r in records), 'diagnostics': dict(report), 'upload_performed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = os.environ.get('TRAECLI_HOME') or str(Path(os.environ.get('TRAE_HOME', str(Path.home() / '.trae'))) / 'cli')
    parser.add_argument('--cli-home', default=root)
    parser.add_argument('--from', dest='start', required=True)
    parser.add_argument('--to', dest='end', required=True)
    parser.add_argument('--source', default='trae-personal')
    parser.add_argument('--timezone', default='Asia/Shanghai')
    parser.add_argument('--out', required=True)
    parser.add_argument('--context-out', required=True)
    parser.add_argument('--max-snippets', type=int, default=8)
    parser.add_argument('--snippet-chars', type=int, default=800)
    try:
        print(json.dumps(extract(parser.parse_args()), ensure_ascii=False, indent=2))
    except (ValueError, OSError, sqlite3.Error) as error:
        print(str(error), file=__import__('sys').stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
