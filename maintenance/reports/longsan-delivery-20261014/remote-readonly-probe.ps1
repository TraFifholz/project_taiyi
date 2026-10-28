$ErrorActionPreference='Stop'
$w=Get-Content -LiteralPath 'C:\foundryvtt\Data\worlds\taiyi\world.json' -Raw|ConvertFrom-Json
[pscustomobject]@{world=$w.id;title=$w.title;system=$w.system}|ConvertTo-Json -Compress
Get-ChildItem -LiteralPath 'C:\foundryvtt\Data\worlds\taiyi\assets' -Directory|Select-Object Name|ConvertTo-Json -Compress
foreach($p in @('C:\Caddy\Caddyfile','C:\caddy\Caddyfile','C:\tools\caddy\Caddyfile','C:\foundryvtt\Caddyfile')){if(Test-Path -LiteralPath $p){Write-Output ('ROUTING_FILE '+$p)}}
