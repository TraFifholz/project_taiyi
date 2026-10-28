"""Run one AGY design-interview turn and retain the exact response and session ID."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import subprocess

root = Path(r'D:\Project Taiyi')
parser = argparse.ArgumentParser()
parser.add_argument('--input', required=True)
parser.add_argument('--name', required=True)
parser.add_argument('--conversation')
args = parser.parse_args()
out = Path(__file__).resolve().parent
prompt_path = (root / args.input).resolve()
prompt = prompt_path.read_text(encoding='utf-8-sig')
event_path = out / f'{args.name}.ndjson'
meta_path = out / f'{args.name}.json'
error_path = out / f'{args.name}.stderr.log'
response_path = out / f'{args.name}-response.md'
if any(path.exists() for path in (event_path, meta_path, error_path, response_path)):
    raise SystemExit('Run name already exists; choose a fresh name to preserve history.')

env = os.environ.copy()
proxy = 'http://127.0.0.1:7890'
for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
    env[key] = proxy
env['NO_PROXY'] = env['no_proxy'] = 'localhost,127.0.0.1,::1'
command = [r'D:\Tools\agy\agy.exe', '--model', 'gemini-3.1-pro-high',
           '--effort', 'high', '--mode', 'plan', '--output-format', 'stream-json',
           '--print-timeout', '15m', '-p', prompt]
if args.conversation:
    command[1:1] = ['--conversation', args.conversation]
meta = {'model': 'gemini-3.1-pro-high', 'mode': 'plan', 'proxy': proxy,
        'cwd': str(root), 'input': args.input,
        'input_sha256': hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
        'started_at': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
        'resumed_conversation': args.conversation}
with event_path.open('wb') as stdout, error_path.open('wb') as stderr:
    process = subprocess.Popen(command, cwd=root, env=env, stdout=stdout, stderr=stderr,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    meta['pid'] = process.pid
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'running', 'pid': process.pid, 'run': args.name}), flush=True)
    code = process.wait()

rows = []
for line in event_path.read_text(encoding='utf-8', errors='replace').splitlines():
    try:
        rows.append(json.loads(line))
    except json.JSONDecodeError:
        continue
meta['exit_code'] = code
meta['ended_at'] = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
for row in rows:
    if row.get('conversation_id'):
        meta['conversation_id'] = row['conversation_id']
    if row.get('session_id'):
        meta['session_id'] = row['session_id']
    if row.get('event') == 'result':
        final_result = row.get('result', {})
        meta['result_status'] = final_result.get('status')
        if final_result.get('conversation_id'):
            meta['conversation_id'] = final_result['conversation_id']
        if isinstance(final_result.get('response'), str):
            response_path.write_text(final_result['response'], encoding='utf-8')
            meta['response_sha256'] = hashlib.sha256(response_path.read_bytes()).hexdigest()
meta['events'] = len(rows)
meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': 'completed', 'exit_code': code, 'events': len(rows),
                  'conversation_id': meta.get('conversation_id'),
                  'session_id': meta.get('session_id')}), flush=True)
raise SystemExit(code)
