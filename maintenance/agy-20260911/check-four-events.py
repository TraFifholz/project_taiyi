from pathlib import Path
import json
import re
import hashlib

root = Path(r'D:\Project Taiyi')
folder = root / 'campaign/prep/sessions/ep04-events'
manifest = json.loads((root / 'maintenance/agy-20260911/four-events/manifest.json').read_text(encoding='utf-8'))
ids = [entry.get('conversation_id') for entry in manifest]
assert len(ids) == 4 and len(set(ids)) == 4 and all(ids)
assert all(entry['status'] == 'SUCCESS' and entry['exit_code'] == 0 for entry in manifest)
changes = json.loads((root / 'maintenance/agy-20260911/four-events/continuity-edits.json').read_text(encoding='utf-8'))
results = []
for path in sorted(folder.glob('[ABCD]-*.md')):
    text = path.read_text(encoding='utf-8')
    result = {'file':path.name,'characters':len(text),'items':{}}
    for heading in ('事件前五项','事件后五项'):
        match = re.search(r'^## ' + heading + r'\s*\n(.*?)(?=\n#{1,3} |\Z)',text,re.S|re.M)
        assert match, (path.name,heading)
        lines = re.findall(r'^(\d+)\. (.+)$',match.group(1),re.M)
        assert [number for number,_ in lines] == ['1','2','3','4','5'], (path.name,heading,lines)
        for number,sentence in lines:
            assert len(re.findall(r'[。！？!?]',sentence)) == 1 and sentence.endswith('。'), (path.name,heading,number,sentence)
        result['items'][heading] = 5
    draft = Path(changes[path.name[0]]['draft'])
    assert hashlib.sha256(draft.read_bytes()).hexdigest() == changes[path.name[0]]['draft_sha256']
    results.append(result)
assert len(results) == 4
report = {'status':'PASS','independent_conversations':ids,'cards':results,'total_one_sentence_items':40,'raw_drafts_preserved':True}
(root / 'maintenance/agy-20260911/four-events/check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
