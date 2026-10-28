param([switch]$Write)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$metadata=Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'discussion/npc/fvtt/refresh-20260902/monochrome-asset.json')|ConvertFrom-Json
$remoteTarget='Administrator@43.136.97.169'
$key='C:\Users\Fifholz\.ssh\server_20260816_ed25519'
$remotePath='C:\foundryvtt\Data\worlds\taiyi\assets\npc\portraits\LS-NPC-037-relationship-monochrome-20260902.webp'
function Invoke-Check {
  $body=@'
$ErrorActionPreference='Stop'
$p='C:\foundryvtt\Data\worlds\taiyi\assets\npc\portraits\LS-NPC-037-relationship-monochrome-20260902.webp'
if(Test-Path -LiteralPath $p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower()}else{'missing'}
'@
  $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($body))
  $output=& ssh -o BatchMode=yes -o ConnectTimeout=12 -i $key $remoteTarget powershell.exe -NoProfile -EncodedCommand $encoded
  if($LASTEXITCODE -ne 0){throw 'Remote hash check failed'}
  return ($output|Out-String).Trim()
}
$before=Invoke-Check
if($before -ne 'missing' -and $before -ne $metadata.sha256){throw 'Versioned asset collision'}
if($Write -and $before -eq 'missing'){
  & scp -q -i $key (Join-Path $taskRoot $metadata.output) ($remoteTarget+':C:/foundryvtt/Data/worlds/taiyi/assets/npc/portraits/LS-NPC-037-relationship-monochrome-20260902.webp')
  if($LASTEXITCODE -ne 0){throw 'Upload failed'}
}
$after=Invoke-Check
if($Write -and $after -ne $metadata.sha256){throw 'Uploaded hash mismatch'}
[pscustomobject]@{path=$remotePath;before=$before;after=$after;verified=($after -eq $metadata.sha256)}|ConvertTo-Json
