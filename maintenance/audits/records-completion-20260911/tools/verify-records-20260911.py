from pathlib import Path
import hashlib, json, re, ast
root=Path('D:/Project Taiyi')
audit=root/'records/audits/records-completion-20260911'
files=[p for p in (audit/'before').rglob('*.md')]
updated=[p.relative_to(audit/'before').as_posix() for p in files]
created=[f'records/memory/session-{i:02d}.md' for i in (9,10,12)]
raw=sorted((root/'records').glob('*.txt'))
expected=['5BDF587BDFCE3DF90D60A8DB69A9BF2C2DD8B2D4375D53E33B52A312324F52F6','123FA63E20EF5873F0C567DB1168175F161C4CF8D50B218A79ED4153505BC47D','2A857DA988C873DD4B82C69D8494A93DDA380A0D18C68D1D996EB5BF1D63F27E','71D42F6F736962555CFEE77F1CE3659753D6C8F5F2D8AAB25B499CC4C569A8C3','A04B85481097A9157FA40DD9A7BAEC1E35D16CD9E343184BADC47F74C170B4C0','4CBF5328A77942F4DCA450F649859C163429AB49738EAA3FA29ADB81628FA8B']
# Baseline hashes captured before record edits; use the exact full set.
expected=['5BDF587BDFCE3DF90D60A8DB69A9BF2C2DD8B2D4375D53E33B52A312324F52F6','123FA63E20EF5873F0C567DB1168175F161C4CF8D50B218A79ED4153505BC47D','2A857DA988C873DD4B82C69D8494A93DDA380A0D18C68D1D996EB5BF1D63F27E','71D42F6F736962555CFEE77F1CE3659753D6C8F5F2D8AAB25B499CC4C569A8C3','A04B85481097A9157FA40DD9A7BAEC1E35D16CD9E343184BADC47F74C170B4C0','4CBF5328A77942F4DCA450F649859C163429AB49738EAA132DF908F047774388','1B2FC161DC1F6273CC088943042F7FAAFCFAF599127018279000368950763458','1EAB1D32699411792024EECC01503AAA117BB522745B4DB204BF569FE80BCFD1','EC515C6751AA520316FA8B23EDDAEBE08E92609829D32051ACA302C3D6598011','03218BE0550076CFFD069DA4FCB9D03DD86246C1547A8BFDE1FFE797782B3F9F','58D0906D485291F06349FFCF9551C4F22FB0A0046A082EA3FA29ADB81628FA8B','8B6F2611132DEA7124681C72D58BB18C6BBE2DF98B43523AB06D6388211618B8']
assert [hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in raw]==expected
summaries=[root/f'records/memory/session-{i:02d}.md' for i in range(1,13)]
assert all(p.exists() for p in summaries)
missing=[]; link_count=0; ref_count=0
for name in updated+created:
    p=root/name
    text=p.read_text(encoding='utf-8')
    assert '\ufffd' not in text, name
    # Check all new/changed local Markdown links; old unrelated broken links are separated.
    previous=(audit/'before'/name)
    oldlinks=set(re.findall(r'\]\(([^)]+)\)',previous.read_text(encoding='utf-8-sig'))) if previous.exists() else set()
    for link in re.findall(r'\]\(([^)]+)\)',text):
        if link in oldlinks or '://' in link or link.startswith('#'): continue
        target=link.split('#')[0]
        if target:
            link_count+=1
            if not (p.parent/target).exists(): missing.append((name,link))
    for session,line in re.findall(r'S(9|10|12):L(\d+)',text):
        assert 1<=int(line)<=len(raw[int(session)-1].read_text(encoding='utf-8-sig').splitlines()), (name,session,line)
        ref_count+=1
assert not missing,missing
index=(root/'records/README.md').read_text(encoding='utf-8')
rows=re.findall(r'^\| S(\d+) \| `([^`]+\.txt)`',index,re.M)
assert len(rows)==12 and all((root/'records'/f).exists() for _,f in rows)
assert '\n\n| S12 |' not in index
report={'raw_transcripts_unchanged':12,'summary_files_present':12,'index_rows_resolve':12,'new_local_links_checked':link_count,'source_line_references_in_bounds':ref_count,'updated':updated,'created':created,'raw_hashes':dict(zip([p.name for p in raw],expected)),'not_verified':['Foundry character sheets, final wounds and balances','S10 clock value direct transcript attribution','remaining downtime versus epilogue timeline']}
(audit/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['raw_hashes','updated','created']},ensure_ascii=False,indent=2))
