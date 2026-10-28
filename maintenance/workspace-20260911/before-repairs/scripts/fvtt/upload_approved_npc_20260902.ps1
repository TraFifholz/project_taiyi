$ErrorActionPreference='Stop'
$taskRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$base=Join-Path $taskRoot 'discussion/npc/fvtt/approved-20260902'
$manifest=Get-Content -Raw -LiteralPath (Join-Path $base 'asset-upload-manifest.json')|ConvertFrom-Json
$key='C:\Users\Fifholz\.ssh\server_20260816_ed25519'
$target='Administrator@43.136.97.169'
$payload=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($manifest|ConvertTo-Json -Depth 5 -Compress)))
function Remote([string]$body){
 $bootstrap='$script=[Console]::In.ReadToEnd(); & ([scriptblock]::Create($script))'
 $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($bootstrap))
 $r=$body|& ssh -o BatchMode=yes -o ConnectTimeout=12 -i $key $target powershell.exe -NoProfile -OutputFormat Text -EncodedCommand $encoded
 if($LASTEXITCODE -ne 0){throw 'Remote validation failed'}
 return ($r|Out-String).Trim()
}
$script=@'
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
'@
$script+="`n`$data=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$payload'))|ConvertFrom-Json`n"
$script+=@'
foreach($e in $data.entries){
 $p=[IO.Path]::GetFullPath((Join-Path 'C:\foundryvtt\Data' $e.remote))
 if(-not $p.StartsWith('C:\foundryvtt\Data\worlds\taiyi\assets\npc\',[StringComparison]::OrdinalIgnoreCase)){throw 'Path guard failed'}
 if((Test-Path -LiteralPath $p) -and (Get-FileHash -LiteralPath $p).Hash.ToLower() -ne $e.sha256){throw 'Asset collision'}
}
'@
Remote $script|Out-Null
foreach($e in $manifest.entries){& scp -q -i $key (Join-Path $taskRoot $e.file) ($target+':C:/foundryvtt/Data/'+$e.remote);if($LASTEXITCODE -ne 0){throw 'Upload failed'}}
$script+=@'

$report=@();foreach($e in $data.entries){$p=Join-Path 'C:\foundryvtt\Data' $e.remote;$hash=(Get-FileHash -LiteralPath $p).Hash.ToLower();if($hash -ne $e.sha256){throw 'Hash mismatch'};$report+=[pscustomobject]@{path=$e.remote;sha256=$hash;verified=$true}}
$report|ConvertTo-Json -Compress
'@
$report=Remote $script
$report|Set-Content -LiteralPath (Join-Path $base 'asset-upload-report.json') -Encoding utf8
Write-Output $report
