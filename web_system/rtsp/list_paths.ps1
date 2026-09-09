$ErrorActionPreference = "Stop"

$url = "http://localhost:9997/v3/paths/list"
Write-Host "Querying: $url"
Invoke-RestMethod -Uri $url -Method Get | ConvertTo-Json -Depth 8
