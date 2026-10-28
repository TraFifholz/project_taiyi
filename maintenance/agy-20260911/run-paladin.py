"""Run the user's AGY handoff through the local Clash proxy and retain output."""
from pathlib import Path
import datetime
import json
import os
import subprocess

root = Path(r'D:\Project Taiyi')
out = root / 'maintenance/agy-20260911'
out.mkdir(parents=True, exist_ok=True)
prompt = (root / 'campaign/prep/agy/20260911-paladin-input.md').read_text(encoding='utf-8')
env = os.environ.copy()
proxy = 'http://127.0.0.1:7890'
for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
    env[key] = proxy
env['NO_PROXY'] = env['no_proxy'] = 'localhost,127.0.0.1,::1'
args = [r'D:\Tools\agy\agy.exe', '--model','gemini-3.1-pro-high',
        '--conversation','cb257ae0-e423-4ce4-859d-54c277d08ece', '--effort','high', '--mode','accept-edits',
        '--dangerously-skip-permissions', '--output-format','stream-json',
        '--print-timeout','30m', '-p',prompt]
meta = {'model':'gemini-3.1-pro-high','proxy':proxy,'cwd':str(root),
        'started_at':datetime.datetime.now().astimezone().isoformat(),
        'input':'campaign/prep/agy/20260911-paladin-input.md',
        'mode':'accept-edits','auto_approve_tools':True}
with (out/'paladin-run.ndjson').open('wb') as stdout, (out/'paladin-run.stderr.log').open('wb') as stderr:
    process = subprocess.Popen(args,cwd=root,env=env,stdout=stdout,stderr=stderr,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    meta['pid'] = process.pid
    (out/'paladin-run.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'pid':process.pid,'status':'running','proxy':proxy}),flush=True)
    code = process.wait()
meta['exit_code'] = code
meta['ended_at'] = datetime.datetime.now().astimezone().isoformat()
(out/'paladin-run.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'completed','exit_code':code}),flush=True)
