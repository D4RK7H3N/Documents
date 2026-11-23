# Watches the school's public API and restarts the Cloudflare tunnel when it
# stops answering. The tunnel connector sometimes loses its edge connection
# and does not come back on its own - the app then gets 502 / 1033 from
# Cloudflare even though the backend on 127.0.0.1:8000 is perfectly fine.
#
# Scheduled to run every 5 minutes by the task "SMS-Tunnel-Watchdog".

$ErrorActionPreference = 'SilentlyContinue'

$serviceName = 'Cloudflared'
    $checkUrl    = 'https://sms.darkzhub.asia/api/sections/'
$logFile     = 'C:\SMS-Tunnel\watchdog.log'
$logDir      = Split-Path -Parent $logFile

function Write-Log([string]$message) {
    try {
        if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
        $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
        Add-Content -Path $logFile -Value "$stamp  $message"
    } catch { }
}

# A 401 means the tunnel is working: the request reached Django and Django
# asked for credentials. Anything else (no answer, 502, 1033) means the
# tunnel is not connected.
function Test-PublicApi {
    try {
        $response = Invoke-WebRequest -Uri $checkUrl -UseBasicParsing -TimeoutSec 25 -ErrorAction Stop
        return ($response.StatusCode -eq 401)
    } catch {
        $status = $null
        try { $status = [int]$_.Exception.Response.StatusCode } catch { }
        if ($status -eq 401) { return $true }
        return $false
    }
}

$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if (-not $service) {
    Write-Log "the service '$serviceName' does not exist - nothing to watch"
    exit 1
}

if (Test-PublicApi) {
    Write-Log "public API is answering - the tunnel is healthy"
    exit 0
}

Write-Log "the public API is not answering - restarting the tunnel"

try {
    Restart-Service -Name $serviceName -Force -ErrorAction Stop
    Start-Sleep -Seconds 25
    if (Test-PublicApi) {
        Write-Log "the tunnel is back - the public API answers again"
    } else {
        Write-Log "the tunnel was restarted but the public API still does not answer"
    }
} catch {
    Write-Log "could not restart the tunnel: $($_.Exception.Message)"
}
