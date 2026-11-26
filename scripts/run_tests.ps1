$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonCommand = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonCommand)) {
    throw 'Python environment not found. Follow COMMANDS.txt to install dependencies first.'
}
$previousDatabaseUrl = $env:DATABASE_URL
$previousSettingsModule = $env:DJANGO_SETTINGS_MODULE
try {
    $env:DATABASE_URL = ''
    $env:DJANGO_SETTINGS_MODULE = 'config.settings'
    Push-Location $projectRoot
    & $pythonCommand manage.py check
    if ($LASTEXITCODE -ne 0) { throw 'Django system check failed.' }

    function Invoke-TestGroup([string]$settingsModule, [string[]]$modules) {
        $env:DJANGO_SETTINGS_MODULE = $settingsModule
        Write-Host "Running $($modules -join ', ') with $settingsModule"
        & $pythonCommand manage.py test @modules --verbosity 1
        if ($LASTEXITCODE -ne 0) { throw "Test group failed: $settingsModule / $($modules -join ', ')" }
    }

    Invoke-TestGroup 'config.settings' @(
        'core.tests', 'core.test_adversarial',
        'core.test_item_features', 'core.test_postgres', 'core.test_screening',
        'core.qa_tests.test_domain', 'core.qa_tests.test_integration'
    )
    Invoke-TestGroup 'core.qa_tests.settings_errors' @('core.qa_tests.test_errors')
    Invoke-TestGroup 'core.qa_tests.settings_state' @('core.qa_tests.test_state')
    Invoke-TestGroup 'core.qa_tests.settings_validation' @('core.qa_tests.test_validation')
    Invoke-TestGroup 'core.qa_tests.settings_verify_media' @(
        'core.qa_tests.test_verify_jpeg', 'core.qa_tests.test_verify_media'
    )
    Invoke-TestGroup 'core.qa_tests.settings_verify_search' @('core.qa_tests.test_verify_search')
    Invoke-TestGroup 'core.qa_tests.settings_verify_state' @('core.qa_tests.test_verify_state')
    Invoke-TestGroup 'core.qa_tests.settings_verify_validation' @('core.qa_tests.test_verify_validation')
    Write-Host 'All test groups passed.'
}
finally {
    Pop-Location -ErrorAction SilentlyContinue
    if ($null -eq $previousDatabaseUrl) { Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue } else { $env:DATABASE_URL = $previousDatabaseUrl }
    if ($null -eq $previousSettingsModule) { Remove-Item Env:DJANGO_SETTINGS_MODULE -ErrorAction SilentlyContinue } else { $env:DJANGO_SETTINGS_MODULE = $previousSettingsModule }
}
