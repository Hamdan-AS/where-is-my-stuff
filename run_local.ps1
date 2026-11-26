$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$candidates = @(
    @{ Command = (Join-Path $projectRoot '.venv\Scripts\python.exe'); Arguments = @() },
    @{ Command = 'py'; Arguments = @('-3') },
    @{ Command = 'python'; Arguments = @() }
)
$python = $null
$pythonArguments = @()
$foundPython = $false
foreach ($candidate in $candidates) {
    $command = $candidate.Command
    $arguments = $candidate.Arguments
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { continue }
    try {
        & $command @arguments -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>$null
        if ($LASTEXITCODE -ne 0) { continue }
        $foundPython = $true
        & $command @arguments -c 'import django, PIL, qrcode, dj_database_url, dotenv' 2>$null
        if ($LASTEXITCODE -ne 0) { continue }
        $python = $command
        $pythonArguments = $arguments
        break
    }
    catch { continue }
}
if (-not $python) {
    if ($foundPython) { throw 'Project dependencies are unavailable. Use a Python environment with requirements.txt installed.' }
    throw 'Python 3.10 or newer is required. No working Python interpreter was found.'
}

$selectedPort = $null
foreach ($candidatePort in 8765..8774) {
    $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $candidatePort)
    try {
        $probe.Start()
        $probe.Stop()
        $selectedPort = $candidatePort
        break
    }
    catch {
        try { $probe.Stop() } catch { }
    }
}

if ($null -eq $selectedPort) {
    throw 'Ports 8765 through 8774 are busy. Close an unused local server and try again.'
}

# This submission runs locally on SQLite and does not require Docker or a .env file.
$env:DATABASE_URL = ''
$env:DJANGO_SETTINGS_MODULE = 'config.settings'

Push-Location $projectRoot
try {
    & $python @pythonArguments manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }

    $url = "http://127.0.0.1:$selectedPort/"
    Write-Host "Starting Where Is My Stuff? at $url"
    Write-Host 'Keep this window open while using the site. Press Ctrl+C to stop.'
    & $python @pythonArguments manage.py runserver "127.0.0.1:$selectedPort"
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
