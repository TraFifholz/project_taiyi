from pathlib import Path
import json,subprocess,hashlib
R=Path('D:/Project Taiyi');A=R/'maintenance/workspace-20260911'
initial=json.loads((A/'migration-result.json').read_text(encoding='utf-8'))
indexes=json.loads((A/'indexes-written.json').read_text(encoding='utf-8'))
repairs=json.loads((A/'repairs.json').read_text(encoding='utf-8'))
changed=set(initial['text_updated']+indexes+repairs)
moves=json.loads((A/'moves.json').read_text(encoding='utf-8'))['files']
unchanged=0
for item in moves:
    if item['new'] in changed:continue
    p=R/item['new'];h=hashlib.sha256(p.read_bytes()).hexdigest()
    assert h==item['sha256'],p
    unchanged+=1
syntax=[]
for name in sorted(changed):
    p=R/name
    if p.suffix in ['.js','.mjs','.cjs']:
        proc=subprocess.run(['node','--check',str(p)],capture_output=True,text=True,encoding='utf-8',errors='replace')
        assert proc.returncode==0,(name,proc.stderr)
        syntax.append(name)
    elif p.suffix=='.py':
        compile(p.read_text(encoding='utf-8-sig'),str(p),'exec');syntax.append(name)
proc=subprocess.run(['node','scripts/validate-campaign-npc-restructure.mjs'],cwd=R,capture_output=True,text=True,encoding='utf-8')
campaign=json.loads(proc.stdout)
assert campaign['errors']==['campaign/episodes/chapter-01/04-特派员.md: unexplained organization exception'],campaign['errors']
(A/'campaign-check.json').write_text(json.dumps(campaign,ensure_ascii=False,indent=2),encoding='utf-8')
result={'status':'PASS','moved_files':len(moves),'unchanged_moved_file_bytes':unchanged,'changed_code_syntax_checked':syntax,'campaign_baseline_only':campaign['errors'],'wiki_build':'passed; existing chunk-size warning','wiki_links':'passed','review_runtime':json.loads((A/'review-runtime.json').read_text(encoding='utf-8-sig'))}
(A/'final-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','moved_files':len(moves),'unchanged_moved_file_bytes':unchanged,'changed_code_syntax_checked':len(syntax),'baseline_errors':len(campaign['errors'])}))
