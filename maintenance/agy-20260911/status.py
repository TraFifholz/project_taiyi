from pathlib import Path
import collections
import json

base = Path(__file__).resolve().parent
rows = []
for line in (base/'run.ndjson').read_text(encoding='utf-8').splitlines():
    try:
        rows.append(json.loads(line))
    except json.JSONDecodeError:
        pass
steps = [r['step_update'] for r in rows if r.get('event') == 'step_update']
print(json.dumps({'events':dict(collections.Counter(r.get('event') for r in rows)),
                  'last_steps':[{'index':s.get('step_index'),'state':s.get('state'),
                    'type':s.get('step_type'),'tool':s.get('tool_name'),
                    'file':s.get('tool_info',{}).get('parameters',{}).get('AbsolutePath'),
                    'output':str(s.get('tool_info',{}).get('output',''))[:160]}
                    for s in steps[-5:]]},ensure_ascii=True))
for row in rows:
    if row.get('event') not in ('init','step_update'):
        print(json.dumps(row,ensure_ascii=True)[:2200])
err=(base/'run.stderr.log').read_text(encoding='utf-8',errors='replace')
if err:
    print(err[-1000:])
