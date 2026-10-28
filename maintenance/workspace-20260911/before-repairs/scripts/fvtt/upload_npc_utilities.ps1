$ErrorActionPreference='Stop'
$taskRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$manifest=Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'discussion/npc/fvtt/refresh-20260902/utility-upload-manifest.json')|ConvertFrom-Json
$remoteTarget='Administrator@43.136.97.169'
$key='C:\Users\Fifholz\.ssh\server_20260816_ed25519'
$payload64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($manifest|ConvertTo-Json -Depth 6 -Compress)))
function Invoke-RemoteUtility([string]$Script){
 $bootstrap='$script=[Console]::In.ReadToEnd(); & ([scriptblock]::Create($script))'
 $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($bootstrap))
 $response=$Script | & ssh -o BatchMode=yes -o ConnectTimeout=12 -i $key $remoteTarget powershell.exe -NoProfile -OutputFormat Text -EncodedCommand $encoded
 if($LASTEXITCODE -ne 0){throw 'Remote utility operation failed'}
 return ($response|Out-String).Trim()
}
$script=@'
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$dir='C:\foundryvtt\Data\worlds\taiyi\assets\npc\utility'
New-Item -ItemType Directory -Path $dir -Force|Out-Null
'@
$script+="`n`$manifest=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$payload64'))|ConvertFrom-Json`n"
$script+=@'
foreach($e in $manifest.entries){$file=Join-Path $dir ([IO.Path]::GetFileName($e.file));if((Test-Path -LiteralPath $file) -and (Get-FileHash -LiteralPath $file).Hash.ToLower() -ne $e.sha256){throw 'Utility asset collision'}}
'@
Invoke-RemoteUtility $script|Out-Null
foreach($entry in $manifest.entries){
 $local=Join-Path $taskRoot $entry.file
 & scp -q -i $key $local ($remoteTarget+':C:/foundryvtt/Data/worlds/taiyi/assets/npc/utility/'+[IO.Path]::GetFileName($local))
 if($LASTEXITCODE -ne 0){throw 'Utility upload failed'}
}
$script+=@'

$results=@();foreach($e in $manifest.entries){$file=Join-Path $dir ([IO.Path]::GetFileName($e.file));$hash=(Get-FileHash -LiteralPath $file).Hash.ToLower();if($hash -ne $e.sha256){throw 'Utility hash mismatch'};$results+=[pscustomobject]@{path=$e.remote;sha256=$hash;verified=$true}}
$results|ConvertTo-Json -Compress
'@
$result=Invoke-RemoteUtility $script
$result|Set-Content -LiteralPath (Join-Path $taskRoot 'discussion/npc/fvtt/refresh-20260902/utility-upload-report.json') -Encoding utf8
Write-Output $result
