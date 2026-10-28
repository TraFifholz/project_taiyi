$ErrorActionPreference='Stop'
$cfg='C:\Caddy\Caddyfile'
$expected='CB5B351B00C4B397A575D5DBD7DCDF396568232E46CC2A9CBC0A17C08672C2D1'
if((Get-FileHash -LiteralPath $cfg).Hash -ne $expected){throw 'Routing file changed since read'}
$bytes=[IO.File]::ReadAllBytes($cfg);$text=[IO.File]::ReadAllText($cfg)
$pattern='(?m)^fvtt\.univare\.icu[ \t]*\{[ \t]*\r?$'
if([regex]::Matches($text,$pattern).Count -ne 1){throw 'Expected single Foundry site'}
$nl=if($text.Contains("`r`n")){"`r`n"}else{"`n"}
$insertion=$nl+"`t# Longsan map viewer: this exact owned HTML file only"+$nl+"`theader /worlds/taiyi/assets/maps/longsan-20261014/index.html >Content-Type `"text/html; charset=utf-8`""
$new=[regex]::Replace($text,$pattern,('$0'+$insertion))
if($new.Replace($insertion,'') -cne $text){throw 'Unexpected routing change'}
$backupDir='C:\Caddy\backups\longsan-map-20261014'
New-Item -ItemType Directory -Path $backupDir -Force|Out-Null
$backup=Join-Path $backupDir 'Caddyfile.original';$candidate=Join-Path $backupDir 'Caddyfile.candidate'
if(Test-Path -LiteralPath $backup){throw 'Backup already exists'}
[IO.File]::WriteAllBytes($backup,$bytes)
$bom=($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191)
[IO.File]::WriteAllText($candidate,$new,(New-Object Text.UTF8Encoding($bom)))
$validation=& 'C:\Caddy\caddy.exe' validate --config $candidate --adapter caddyfile 2>&1|Out-String
if($LASTEXITCODE -ne 0){throw ('Candidate validation failed: '+$validation)}
if((Get-FileHash -LiteralPath $cfg).Hash -ne $expected){throw 'Routing file changed during preparation'}
[IO.File]::WriteAllBytes($cfg,[IO.File]::ReadAllBytes($candidate))
$reload=& 'C:\Caddy\caddy.exe' reload --config $cfg --adapter caddyfile 2>&1|Out-String
if($LASTEXITCODE -ne 0){[IO.File]::WriteAllBytes($cfg,$bytes);& 'C:\Caddy\caddy.exe' reload --config $cfg --adapter caddyfile|Out-Null;throw 'Reload failed; original restored'}
[pscustomobject]@{before_sha256=$expected.ToLower();after_sha256=(Get-FileHash -LiteralPath $cfg).Hash.ToLower();backup=$backup;candidate_validated=$true;reload_succeeded=$true;exact_path='/worlds/taiyi/assets/maps/longsan-20261014/index.html';only_change='Deferred Content-Type override for this HTML file';rollback='Restore Caddyfile.original and reload'}|ConvertTo-Json -Compress
