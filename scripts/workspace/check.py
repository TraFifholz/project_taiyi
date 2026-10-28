"""Check active workspace indexes, local links, protected sources and moved files."""
from pathlib import Path
import argparse, hashlib, json, re, urllib.parse, sys

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / 'maintenance/workspace-20260911'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):h.update(chunk)
    return h.hexdigest()

def archived(p):
    s=p.relative_to(ROOT).as_posix()
    return ('/archive/' in s or '/runs/' in s or any(x in s for x in ['/before/','/source-before/','/server-source/']) or p.name.endswith(('-before.md','.before','.bak')))

def check(migration=False):
    errors=[]; links=0
    paths=[ROOT/'WORKSPACE.md', ROOT/'CODEX_INDEX.md', ROOT/'RUNBOOK.md']
    for base in ['campaign','records','assets','foundry','character_sheet']:
        paths.extend(p for p in (ROOT/base).rglob('*.md') if not archived(p))
    # Only top-level indexes in maintenance; evidence remains byte-preserved.
    paths.extend([ROOT/'maintenance/README.md', AUDIT/'README.md'])
    for p in paths:
        text=p.read_text(encoding='utf-8-sig')
        text=re.sub(r'```[\s\S]*?```','',text)
        for target in re.findall(r'!?\[[^\]\n]*\]\(([^\n]+?)\)',text):
            target=target.strip('<>')
            if re.match(r'^(?:https?:|data:|mailto:|app:|codex:|#)',target):continue
            target=urllib.parse.unquote(target.split('#')[0])
            if not target:continue
            if re.match(r'^[A-Za-z]:',target):q=Path(target)
            elif target.startswith('/'):continue
            else:q=p.parent/target
            links+=1
            if not q.exists():errors.append({'file':p.relative_to(ROOT).as_posix(),'broken_link':target})
    index=(ROOT/'records/README.md').read_text(encoding='utf-8')
    rows=re.findall(r'^\| S(\d+) \| `([^`]+\.txt)`',index,re.M)
    summaries=[ROOT/f'records/memory/session-{int(i):02}.md' for i,_ in rows]
    if not all(p.exists() for p in summaries):errors.append('Missing session summary')
    if not all((ROOT/'records'/name).exists() for _,name in rows):errors.append('Missing indexed transcript')
    for path in ['records/prep','discussion']:
        if (ROOT/path).exists():errors.append('Retired directory recreated: '+path)
    protected=json.loads((AUDIT/'protected-hashes.json').read_text(encoding='utf-8'))
    for group in (protected.values() if migration else []):
        for path,digest in group.items():
            if not (ROOT/path).exists() or sha(ROOT/path)!=digest:errors.append('Protected source changed: '+path)
    moves=json.loads((AUDIT/'moves.json').read_text(encoding='utf-8'))['files']
    for x in (moves if migration else []):
        if not (ROOT/x['new']).exists():errors.append('Moved file missing: '+x['new'])
    # Asset bytes and historical generated requests/manifests must stay unchanged.
    preserved=0
    for x in (moves if migration else []):
        old=x['old']; p=ROOT/x['new']
        if p.suffix.lower() in {'.png','.webp','.jpg','.jpeg','.xlsx','.svg'} or '/runs/' in old or old.endswith(('.before','.bak')):
            if sha(p)!=x['sha256']:errors.append('Preserved asset/evidence changed: '+x['new'])
            preserved+=1
    result={'status':'PASS' if not errors else 'FAIL','mode':'migration' if migration else 'current-structure','markdown_files':len(paths),'local_links':links,'summaries':len(summaries),'moved_files_present':len(moves) if migration else None,'preserved_assets_and_run_files':preserved if migration else None,'protected_transcripts':len(protected['raw']) if migration else None,'protected_public_files':len(protected['public']) if migration else None,'errors':errors}
    (AUDIT/'workspace-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2));return bool(errors)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--migration',action='store_true',help='Also verify the one-time 2026-09-11 migration hashes; skip after intentional later source edits.')
    sys.exit(check(parser.parse_args().migration))
