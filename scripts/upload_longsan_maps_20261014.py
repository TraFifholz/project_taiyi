"""Upload the prepared WebP release to the verified Taiyi asset directory."""
from pathlib import Path
import base64,hashlib,json,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'assets/maps/longsan-delivery-20261014/web'
REPORT=ROOT/'maintenance/reports/longsan-delivery-20261014'
HOST='Administrator@43.136.97.169'
KEY=r'C:\Users\Fifholz\.ssh\server_20260816_ed25519'
STAGE='C:/foundryvtt/Data/worlds/taiyi/assets/maps/longsan-20261014-upload/'
BASE='https://fvtt.univare.icu/worlds/taiyi/assets/maps/longsan-20261014/'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def remote(script):
 bootstrap="$ProgressPreference='SilentlyContinue';$script=[Console]::In.ReadToEnd(); & ([scriptblock]::Create($script))"
 encoded=base64.b64encode(bootstrap.encode('utf-16le')).decode()
 result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-i',KEY,HOST,'powershell.exe','-NoProfile','-OutputFormat','Text','-EncodedCommand',encoded],input=script.encode('utf-8'),capture_output=True)
 if result.returncode:raise RuntimeError(result.stdout.decode('utf-8','replace')+'\n'+result.stderr.decode('utf-8','replace'))
 return result.stdout.decode('utf-8','replace').strip()
def finalize_local():
 d=json.loads((WEB/'manifest.json').read_text('utf-8'));d['source_archive']='龙散市-地图-output.zip'
 (WEB/'manifest.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),'utf-8')
 (WEB/'README.txt').write_text('Longsan map release 2026-10-14. Eight 8192x6144 WebP maps and eight 3072x2304 previews. Default: day-metro-clean. Viewer: index.html. Coordinates: 48x36 km. 8K WebP quality 94, preview quality 86. Original SVGs: longsan-editable-svg.zip; all 8K WebP: longsan-webp-maps.zip.\nFoundry asset paths: worlds/taiyi/assets/maps/longsan-20261014/<filename>.\nThe original audit is preserved as supplied, not a new geometry audit.\n','utf-8')
 with zipfile.ZipFile(WEB/'longsan-webp-maps.zip','w',zipfile.ZIP_STORED) as z:
  for p in sorted(WEB.glob('*-8k.webp')):z.write(p,p.name)
  for p in (WEB/'manifest.json',WEB/'positions.json',WEB/'source-audit.json',WEB/'README.txt'):z.write(p,p.name)
 for p in WEB.glob('*.zip'):
  with zipfile.ZipFile(p) as z:assert z.testzip() is None
 entries=[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p),'url':BASE+p.name} for p in sorted(WEB.iterdir()) if p.is_file()]
 (REPORT/'upload-manifest.json').write_text(json.dumps({'base_url':BASE,'files':entries,'total_bytes':sum(x['bytes'] for x in entries)},ensure_ascii=False,indent=2),'utf-8')
 return entries
def main():
 verify_only='--verify-only' in sys.argv
 entries=json.loads((REPORT/'upload-manifest.json').read_text('utf-8'))['files'] if verify_only else finalize_local()
 for i,e in enumerate(entries):
  assert sha(WEB/e['name'])==e['sha256']
  if verify_only:continue
  result=subprocess.run(['scp','-q','-o','BatchMode=yes','-o','ConnectTimeout=12','-i',KEY,str(WEB/e['name']),HOST+':'+STAGE+e['name']],capture_output=True)
  if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace'))
  print(json.dumps({'uploaded':i+1,'files':len(entries),'name':e['name'],'bytes':e['bytes']}),flush=True)
 payload=base64.b64encode(json.dumps(entries).encode('utf-8')).decode()
 script=r'''$ErrorActionPreference='Stop'
$root='C:\foundryvtt\Data\worlds\taiyi\assets\maps'
$stage='C:\foundryvtt\Data\worlds\taiyi\assets\maps\longsan-20261014-upload'
$dest='C:\foundryvtt\Data\worlds\taiyi\assets\maps\longsan-20261014'
foreach($p in @($stage,$dest)){if(-not [IO.Path]::GetFullPath($p).StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Path guard failed'}}
if(Test-Path -LiteralPath $dest){throw 'Final path exists; no overwrite permitted'}
if(-not (Test-Path -LiteralPath $stage)){throw 'Upload stage missing'}
$entries=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('PAYLOAD'))|ConvertFrom-Json
if(@(Get-ChildItem -LiteralPath $stage -File).Count -ne $entries.Count){throw 'Unexpected staged files'}
$checks=@()
foreach($e in $entries){$p=Join-Path $stage $e.name;if([IO.Path]::GetFileName($p) -ne $e.name){throw 'Bad file name'};if((Get-Item -LiteralPath $p).Length -ne $e.bytes){throw 'Size mismatch'};$hash=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower();if($hash -ne $e.sha256){throw ('Hash mismatch '+$e.name)};$checks+=[pscustomobject]@{name=$e.name;sha256=$hash;bytes=$e.bytes;verified=$true}}
Move-Item -LiteralPath $stage -Destination $dest
$after=@();foreach($e in $entries){$p=Join-Path $dest $e.name;if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() -ne $e.sha256){throw 'Final readback mismatch'};$after+=$e.name}
[pscustomobject]@{world='taiyi';directory=$dest;verified_files=$checks;final_readback=$after;published=$true}|ConvertTo-Json -Depth 5 -Compress
'''.replace('PAYLOAD',payload)
 (REPORT/'verify-and-publish.ps1').write_text(script,'utf-8')
 data=json.loads(remote(script));(REPORT/'server-upload-verification.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8')
 print(json.dumps({'published':data['published'],'files':len(data['verified_files']),'url':BASE+'index.html','upload_bytes':sum(e['bytes'] for e in entries)}),flush=True)
if __name__=='__main__':
 sys.stdout.reconfigure(encoding='utf-8');main()
