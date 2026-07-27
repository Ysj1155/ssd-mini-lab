[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$TestFile,

    [Parameter(Mandatory)]
    [ValidateRange(1, [uint64]::MaxValue)]
    [uint64]$ExpectedFileBytes,

    [string]$IdentityConfigPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$SafetyModule = Join-Path $RepoRoot "scripts\lib\ExternalSsdSafety.psm1"
$IdentityConfigPath = if ([string]::IsNullOrWhiteSpace($IdentityConfigPath)) {
    Join-Path $RepoRoot "configs\external_ssd_dut_identity.json"
}
else {
    $IdentityConfigPath
}
$CheckedAtUtc = (Get-Date).ToUniversalTime().ToString("o")

try {
    Import-Module $SafetyModule -Force
    $Preflight = Assert-ExternalSsdTarget `
        -TestFile $TestFile `
        -IdentityConfigPath $IdentityConfigPath `
        -RequireExistingTarget `
        -ExpectedFileBytes $ExpectedFileBytes

    [pscustomobject][ordered]@{
        schema_version = "1.0"
        check_id = "EXT-DUT-PREFLIGHT-READONLY-001"
        checked_at_utc = $CheckedAtUtc
        mode = "read_only_existing_target"
        workload_invoked = $false
        target_mutated = $false
        expected_file_bytes = $ExpectedFileBytes
        status = "Pass"
        preflight = $Preflight
    } | ConvertTo-Json -Depth 10
}
catch {
    [pscustomobject][ordered]@{
        schema_version = "1.0"
        check_id = "EXT-DUT-PREFLIGHT-READONLY-001"
        checked_at_utc = $CheckedAtUtc
        mode = "read_only_existing_target"
        workload_invoked = $false
        target_mutated = $false
        expected_file_bytes = $ExpectedFileBytes
        status = "Fail"
        error = $_.Exception.Message
    } | ConvertTo-Json -Depth 10
    exit 1
}
