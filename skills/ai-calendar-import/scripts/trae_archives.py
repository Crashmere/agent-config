"""TraeX available-history snapshots; no source writes, no model summarization."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import tempfile
from archive_conversations import pack, snapshot, json_bytes


def stamp(value):
    if value is None or isinstance(value, (int, float)) and value <= 0: return None
    try:
        if isinstance(value, (int, float)):
            return dt.datetime.fromtimestamp(value / 1000 if value > 10**11 else value, dt.timezone.utc).isoformat()
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).isoformat()
    except (ValueError, TypeError, OSError): return None


def readable(item):
    if isinstance(item.get('text'), str): return item['text']
    content = item.get('content')
    if isinstance(content, str): return content
    if isinstance(content, list) and all(isinstance(p,dict) and p.get('type') in ('text','input_text','output_text') and isinstance(p.get('text'),str) for p in content):
        return '\n'.join(p['text'] for p in content)
    # Multimodal blocks, tool arguments/results and unknown fields stay visible
    # as JSON, and the original source also retains their exact representation.
    return json.dumps(item, ensure_ascii=False, indent=2)


def projection_messages(path):
    for line in path.open():
        row = json.loads(line); item = json.loads(row['item_json'])
        kind = item.get('type') or row['item_type']
        role = 'user' if kind == 'userMessage' else 'assistant' if kind in ('agentMessage','reasoning') else 'system' if kind in ('contextCompaction','taskNotification') else 'tool'
        identifier = hashlib.sha256(json_bytes([row['turn_id'],row['item_id']])).hexdigest()
        yield {'id': identifier, 'role': role, 'at': stamp(row['created_at_ms']), 'content': readable(item), 'attributes': {'platform_type': kind, 'turn_id': row['turn_id'], 'item_id':row['item_id']}}


def rollout_messages(path):
    seen = set()
    for line in path.open(errors='replace'):
        try: record = json.loads(line)
        except ValueError: continue  # Exact unfinished/malformed bytes remain in the source artifact.
        kind = record.get('type'); payload = record.get('payload',{})
        if not isinstance(payload, dict): continue
        if kind == 'response_item': items = [payload]
        elif kind == 'history_mutation': items = payload.get('items',[])
        elif kind == 'event_msg' and payload.get('type') in ('user_message','agent_message'):
            items = [{'role':'user' if payload['type']=='user_message' else 'assistant','content':payload.get('message','')}]
        else: continue
        for item in items:
            if not isinstance(item,dict): continue
            metadata=item.get('internal_chat_message_metadata_passthrough') or {}
            at=stamp(metadata.get('create_time') or record.get('timestamp'))
            identifier=hashlib.sha256(json_bytes([item,at])).hexdigest()
            if identifier in seen: continue
            seen.add(identifier)
            role=item.get('role') or ('tool' if item.get('type') in ('function_call','function_call_output') else 'unknown')
            if role not in ('user','assistant','tool','system','developer'): role='unknown'
            yield {'id':identifier,'role':role,'at':at,'content':readable(item),'attributes':{'platform_type':item.get('type','message'),'source_event':kind}}


def archive_thread(thread, rollout, history, source, directory, source_label=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    with tempfile.TemporaryDirectory(prefix='snapshot-',dir=directory) as temp:
        sources=[];names=[]
        raw=Path(temp)/'trae-rollout.jsonl'
        if rollout is not None:
            snapshot(rollout,raw);sources.append(raw);names.append(Path(rollout).name)
        projection=Path(temp)/'trae-projection.jsonl';count=0
        with projection.open('x') as output:
            os.chmod(projection, 0o600)
            if history is not None:
                for row in history.execute('SELECT * FROM thread_items WHERE thread_id=? ORDER BY rollout_ordinal,item_id',(thread['id'],)):
                    output.write(json.dumps(dict(row),ensure_ascii=False)+'\n');count+=1
        # Use the projection for the readable conversation; retain both sources
        # to recover revisions/compactions and additional fields later.
        sources.append(projection);names.append('thread-items.jsonl')
        turns=Path(temp)/'trae-turns.jsonl'
        with turns.open('x') as output:
            os.chmod(turns,0o600)
            if history is not None:
                for row in history.execute('SELECT * FROM thread_turns WHERE thread_id=? ORDER BY rollout_ordinal',(thread['id'],)):
                    output.write(json.dumps(dict(row),ensure_ascii=False)+'\n')
        sources.append(turns);names.append('thread-turns.jsonl')
        messages=projection_messages(projection) if count else rollout_messages(raw)
        header={'source':source,'conversation_id':thread['id'],'title':(thread['name'] or thread['title'] or 'AI 会话')[:160],'coverage':'partial','note':'保存该会话当前可取得的全部日志和投影，包含所选日期以外的上下文；源平台已删除的内容和仅有引用的附件不能保证恢复。原始文件保留压缩、重放和未完成末行，可供后续重新解析。'}
        if source_label: header['source_label']=source_label
        if rollout is None: header['note'] += ' 本机原始 rollout 已缺失，仅保存仍可取得的消息投影和轮次元数据；零值时间显示为未知。'
        return pack(header,messages,sources,directory/(thread['id']+'.jsonl.gz'), source_names=names)
