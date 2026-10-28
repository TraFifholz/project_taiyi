param([switch]$Write)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$manifestPath = Join-Path $taskRoot 'discussion/npc/fvtt/asset-manifest.json'
$assetManifest = Get-Content -Raw -LiteralPath $manifestPath -Encoding utf8 | ConvertFrom-Json
if ($assetManifest.worldId -ne 'taiyi') { throw 'Unexpected world' }
$files = @($assetManifest.entries | ForEach-Object {
  [pscustomobject]@{ path = ('avatars/' + [IO.Path]::GetFileName($_.avatar)); sha256 = $_.avatarSha256 }
  [pscustomobject]@{ path = ('portraits/' + [IO.Path]::GetFileName($_.portrait)); sha256 = $_.portraitSha256 }
})
$payload64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -InputObject $files -Depth 3 -Compress)))
$keyPath = 'C:\Users\Fifholz\.ssh\server_20260816_ed25519'
$remoteTarget = 'Administrator@43.136.97.169'
function Invoke-RemoteNpcScript([string]$Body) {
  $bootstrap = '$script=[Console]::In.ReadToEnd(); & ([scriptblock]::Create($script))'
  $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($bootstrap))
  $result = $Body | & ssh -o BatchMode=yes -o ConnectTimeout=12 -i $keyPath $remoteTarget powershell.exe -NoProfile -OutputFormat Text -EncodedCommand $encoded
  if ($LASTEXITCODE -ne 0) { throw 'Remote operation failed' }
  return $result
}
$preamble = @'
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$assetRoot='C:\foundryvtt\Data\worlds\taiyi\assets\npc'
$world=[IO.File]::ReadAllText('C:\foundryvtt\Data\worlds\taiyi\world.json',[Text.Encoding]::UTF8)|ConvertFrom-Json
if($world.id -ne 'taiyi' -or $world.system -ne 'swade'){throw 'World guard failed'}
'@
$dataStatement = "`n`$files=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$payload64'))|ConvertFrom-Json`n"
$preflight = @'
$exists=0
foreach($entry in $files){
  $file=[IO.Path]::GetFullPath((Join-Path $assetRoot $entry.path))
  if(-not $file.StartsWith($assetRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid asset path'}
  if(Test-Path -LiteralPath $file){$exists++; if((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower() -ne $entry.sha256){throw ('Asset collision: '+$entry.path)}}
}
[pscustomobject]@{world='taiyi';files=$files.Count;alreadyMatching=$exists;missing=$files.Count-$exists}|ConvertTo-Json -Compress
'@
$preflightText = Invoke-RemoteNpcScript ($preamble + $dataStatement + $preflight)
Write-Output $preflightText
if (-not $Write) { exit 0 }
$create = "`nNew-Item -ItemType Directory -Path `$assetRoot -Force | Out-Null"
Invoke-RemoteNpcScript ($preamble + $create) | Out-Null
foreach ($kind in @('avatars', 'portraits')) {
  $localPath = Join-Path $taskRoot ('discussion/npc/fvtt/assets/' + $kind)
  & scp -q -r -i $keyPath $localPath ($remoteTarget + ':C:/foundryvtt/Data/worlds/taiyi/assets/npc/')
  if ($LASTEXITCODE -ne 0) { throw ('Upload failed: ' + $kind) }
}
$verify = @'
$mismatches=@()
foreach($entry in $files){$file=Join-Path $assetRoot $entry.path;if(-not(Test-Path -LiteralPath $file)){$mismatches+=('missing:'+ $entry.path)}elseif((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower() -ne $entry.sha256){$mismatches+=('hash:'+ $entry.path)}}
$http=@('avatars/LS-NPC-088.webp','avatars/LS-NPC-N3.webp','portraits/LS-NPC-090.webp')|ForEach-Object{$r=Invoke-WebRequest -UseBasicParsing -Method Head -Uri ('http://127.0.0.1:30000/worlds/taiyi/assets/npc/'+$_);[pscustomobject]@{path=$_;status=$r.StatusCode;contentType=$r.Headers['Content-Type']}}
[pscustomobject]@{world='taiyi';verifiedAt=(Get-Date).ToUniversalTime().ToString('o');files=$files.Count;matching=$files.Count-$mismatches.Count;mismatches=$mismatches;http=$http}|ConvertTo-Json -Depth 4 -Compress
if($mismatches.Count){exit 1}
'@
$verifyText = Invoke-RemoteNpcScript ($preamble + $dataStatement + $verify)
$verifyObject = $verifyText | ConvertFrom-Json
$verifyObject | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskRoot 'discussion/npc/fvtt/asset-upload-report.json') -Encoding utf8
Write-Output $verifyText
