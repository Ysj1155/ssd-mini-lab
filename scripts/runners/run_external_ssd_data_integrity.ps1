# scripts/runners/run_external_ssd_data_integrity.ps1
#
# Safe file-target data-integrity MVP:
#   1. Write a new 4 GiB verification file with fio CRC32C metadata.
#   2. Read the complete file back with fio verify-only.
#   3. Collect read-only pre/post evidence and synchronized host counters.
#
# The target is retained after completion. This script never targets a raw disk,
# overwrites an existing file, or removes user data.

param(
    [string]$ExperimentLabel = "",
    [string]$TestFile = "E:\validation\ssd_lab_verify_4g",

    [ValidateRange(100, 60000)]
    [int]$ObserverSampleIntervalMs = 1000,

    [switch]$ConfirmSamePort,
    [switch]$ConfirmDedicatedVerificationFileWrite
)

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$SafetyModule = Join-Path $BaseDir "scripts\lib\ExternalSsdSafety.psm1"
$DutIdentityConfig = Join-Path $BaseDir "configs\external_ssd_dut_identity.json"
Import-Module $SafetyModule -Force
$ResultRoot = Join-Path $BaseDir "results\external_ssd"
$ExperimentRoot = Join-Path $ResultRoot "_experiments"
$ObserverScript = Join-Path $BaseDir "scripts\observers\collect_external_ssd_observer.ps1"
$HostObserverScript = Join-Path $BaseDir "scripts\observers\collect_windows_storage_counters.ps1"
$ExpectedBytes = 4GB
$RequiredFreeBytes = 8GB

if ([string]::IsNullOrWhiteSpace($ExperimentLabel)) {
    $ExperimentLabel = "data_integrity_4g_$(Get-Date -Format 'yyyyMMdd')"
}

$SafeExperiment = $ExperimentLabel -replace '[^A-Za-z0-9_.-]', '_'
$RunId = "sustained_${SafeExperiment}"
$ResultDir = Join-Path $ResultRoot $RunId
$ExperimentDir = Join-Path $ExperimentRoot $SafeExperiment
$ExperimentManifestPath = Join-Path $ExperimentDir "experiment_manifest.json"
$RunnerManifestPath = Join-Path $ResultDir "runner_manifest.json"
$HostObserverDir = Join-Path $ResultDir "host_observer"

if (-not $ConfirmSamePort) {
    throw "Re-run with -ConfirmSamePort after confirming the intended physical USB port."
}
if (-not $ConfirmDedicatedVerificationFileWrite) {
    throw "Re-run with -ConfirmDedicatedVerificationFileWrite after confirming that a new dedicated 4 GiB verification file may be written."
}
$DutPreflight = Assert-ExternalSsdTarget `
    -TestFile $TestFile `
    -IdentityConfigPath $DutIdentityConfig `
    -RequireNewTarget `
    -RequiredFreeBytes $RequiredFreeBytes
$TestFile = $DutPreflight.canonical_target
foreach ($RequiredScript in @($ObserverScript, $HostObserverScript)) {
    if (-not (Test-Path -LiteralPath $RequiredScript)) {
        throw "Required observer script not found: $RequiredScript"
    }
}
if ($null -eq (Get-Command fio -ErrorAction SilentlyContinue)) {
    throw "fio command not found. Check PATH before starting the experiment."
}
if (Test-Path -LiteralPath $ExperimentManifestPath) {
    throw "Experiment manifest already exists. Use a new ExperimentLabel: $ExperimentManifestPath"
}
if (Test-Path -LiteralPath $ResultDir) {
    $ExistingEvidence = @(Get-ChildItem -LiteralPath $ResultDir -File -ErrorAction SilentlyContinue)
    if ($ExistingEvidence.Count -gt 0) {
        throw "Result directory already contains evidence. Use a new ExperimentLabel: $ResultDir"
    }
}

New-Item -ItemType Directory -Force $ExperimentDir, $ResultDir, $HostObserverDir | Out-Null

$Phases = @(
    [pscustomobject][ordered]@{
        order = 1
        name = "write_crc32c"
        operation = "write"
        status = "planned"
        fio_json = "${RunId}_phase1_write.json"
        started_at = $null
        completed_at = $null
    },
    [pscustomobject][ordered]@{
        order = 2
        name = "verify_crc32c"
        operation = "read_verify"
        status = "planned"
        fio_json = "${RunId}_phase2_verify.json"
        started_at = $null
        completed_at = $null
    }
)

$ExperimentManifest = [ordered]@{
    schema_version = "1.0"
    experiment_id = $SafeExperiment
    test_protocol_id = "EXT-DATA-INTEGRITY-001"
    requirement_ids = @("REQ-DATA-009", "REQ-HOST-OBS-010", "REQ-DUT-ID-012", "REQ-ENV-001", "REQ-OBS-001", "REQ-TRACE-001", "REQ-LIMIT-001")
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_data_integrity.ps1"
    question = "Can a newly written 4 GiB file be read back completely with no CRC32C verification error?"
    safety = "canonical new file target on the enrolled DUT; existing targets and raw physical drives are refused; target is retained after execution"
    dut_preflight = $DutPreflight
    interpretation_boundary = "This verifies one Windows/USB/exFAT file-target data path. It does not prove power-loss protection, media endurance, NAND behavior, or internal error-correction coverage."
    fixed_controls = [ordered]@{
        same_physical_usb_port_confirmed = [bool]$ConfirmSamePort
        dedicated_verification_file_write_confirmed = [bool]$ConfirmDedicatedVerificationFileWrite
        test_file = $TestFile
        expected_file_bytes = $ExpectedBytes
        initial_free_bytes = [long]$DutPreflight.size_remaining_bytes
        ioengine = "windowsaio"
        block_size = "1M"
        iodepth = 4
        direct = 1
        numjobs = 1
        verify = "crc32c"
        host_observer_interval_ms = $ObserverSampleIntervalMs
    }
    target_preparation = [ordered]@{
        method = "dotnet_filestream_create_new_set_length"
        started_at = $null
        completed_at = $null
        status = "planned"
        observed_file_bytes = $null
    }
    phases = $Phases
    analysis_evidence = @()
    error = $null
}

$RunnerManifest = [ordered]@{
    schema_version = "1.0"
    role = "runner"
    run_id = $RunId
    experiment_id = $SafeExperiment
    test_case_id = "EXT-DATA-INTEGRITY-001"
    requirement_ids = $ExperimentManifest.requirement_ids
    started_at = (Get-Date).ToString("o")
    completed_at = $null
    status = "started"
    result = "observation"
    runner = "scripts/runners/run_external_ssd_data_integrity.ps1"
    safety = $ExperimentManifest.safety
    dut_preflight = $DutPreflight
    result_dir = $ResultDir
    test_file = $TestFile
    conditions = [ordered]@{
        size = "4G"
        planned_bytes = $ExpectedBytes
        bs = "1M"
        iodepth = 4
        direct = 1
        numjobs = 1
        ioengine = "windowsaio"
        verify = "crc32c"
        verify_fatal = 1
        time_based = $false
    }
    runs = @()
    host_observer = @()
}

function Save-Json {
    param([object]$Value, [string]$Path)
    $Value | ConvertTo-Json -Depth 12 | Out-File -LiteralPath $Path -Encoding utf8
}

function Save-Manifests {
    Save-Json -Value $ExperimentManifest -Path $ExperimentManifestPath
    Save-Json -Value $RunnerManifest -Path $RunnerManifestPath
}

function Initialize-DedicatedVerificationFile {
    $ExperimentManifest.target_preparation.status = "running"
    $ExperimentManifest.target_preparation.started_at = (Get-Date).ToString("o")
    Save-Manifests

    $Stream = $null
    try {
        $Stream = [System.IO.FileStream]::new(
            $TestFile,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None
        )
        $Stream.SetLength($ExpectedBytes)
        $Stream.Flush($true)
    }
    finally {
        if ($null -ne $Stream) {
            $Stream.Dispose()
        }
    }

    $PreparedFile = Get-Item -LiteralPath $TestFile -ErrorAction Stop
    $ExperimentManifest.target_preparation.observed_file_bytes = $PreparedFile.Length
    $ExperimentManifest.target_preparation.completed_at = (Get-Date).ToString("o")
    if ($PreparedFile.Length -ne $ExpectedBytes) {
        $ExperimentManifest.target_preparation.status = "failed"
        Save-Manifests
        throw "Dedicated verification file has an unexpected length. Expected=$ExpectedBytes, actual=$($PreparedFile.Length)"
    }

    $ExperimentManifest.target_preparation.status = "complete"
    Save-Manifests
}

function Invoke-StaticObserver {
    param([string]$Phase)

    $env:SSD_LAB_EXTERNAL_TESTFILE = $TestFile
    $env:SSD_LAB_EXTERNAL_SUSTAINED_LABEL = $RunId
    powershell -ExecutionPolicy Bypass -File $ObserverScript -RunLabel $RunId -Phase $Phase
    if ($LASTEXITCODE -ne 0) {
        throw "Static observer $Phase failed with exit code $LASTEXITCODE"
    }
}

function Start-HostObserver {
    param([string]$Phase)

    $StopFile = Join-Path $HostObserverDir "${Phase}.stop"
    if (Test-Path -LiteralPath $StopFile) {
        Remove-Item -LiteralPath $StopFile -Force
    }

    $Arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$HostObserverScript`"",
        "-RunId", "`"$RunId`"",
        "-Phase", "`"$Phase`"",
        "-TargetDrive", "$($DutPreflight.identity.drive_letter)",
        "-OutputDir", "`"$HostObserverDir`"",
        "-StopFile", "`"$StopFile`"",
        "-SampleIntervalMs", "$ObserverSampleIntervalMs",
        "-MaxDurationSec", "900"
    )
    $Process = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $Arguments `
        -PassThru `
        -WindowStyle Hidden

    Start-Sleep -Seconds 2
    return [pscustomobject]@{
        process = $Process
        phase = $Phase
        stop_file = $StopFile
        manifest = Join-Path $HostObserverDir "${Phase}_manifest.json"
    }
}

function Stop-HostObserver {
    param([object]$Handle)

    New-Item -ItemType File -Force -Path $Handle.stop_file | Out-Null
    if (-not $Handle.process.WaitForExit(15000)) {
        $Handle.process.Kill()
    }

    $ObserverStatus = "limited"
    if (Test-Path -LiteralPath $Handle.manifest) {
        try {
            $ObserverStatus = (Get-Content -Raw -LiteralPath $Handle.manifest | ConvertFrom-Json).status
        }
        catch {
            $ObserverStatus = "limited"
        }
    }

    $RunnerManifest.host_observer += [ordered]@{
        phase = $Handle.phase
        status = $ObserverStatus
        manifest = $Handle.manifest
        stop_file = $Handle.stop_file
    }
    Save-Manifests
}

function Invoke-IntegrityPhase {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Phase
    )

    $OutFile = Join-Path $ResultDir $Phase.fio_json
    $LogPrefix = $OutFile.Substring(0, $OutFile.Length - ".json".Length)
    $Phase.status = "running"
    $Phase.started_at = (Get-Date).ToString("o")
    Save-Manifests

    $RunRecord = [ordered]@{
        phase_order = $Phase.order
        phase_name = $Phase.name
        operation = $Phase.operation
        started_at = (Get-Date).ToString("o")
        completed_at = $null
        status = "started"
        exit_code = $null
        fio_json = $OutFile
        log_prefix = $LogPrefix
    }

    $FioArgs = @(
        "--name=$($Phase.name)",
        "--filename=$TestFile",
        "--bs=1M",
        "--iodepth=4",
        "--size=4G",
        "--numjobs=1",
        "--ioengine=windowsaio",
        "--direct=1",
        "--thread=1",
        "--verify=crc32c",
        "--verify_fatal=1",
        "--verify_dump=1",
        "--verify_state_save=0",
        "--unlink=0",
        "--group_reporting=1",
        "--log_avg_msec=1000",
        "--write_bw_log=$LogPrefix",
        "--write_iops_log=$LogPrefix",
        "--write_lat_log=$LogPrefix",
        "--output-format=json",
        "--output=$OutFile"
    )

    if ($Phase.operation -eq "write") {
        $FioArgs += @("--rw=write", "--do_verify=0", "--overwrite=1")
    }
    else {
        $FioArgs += @("--rw=read", "--verify_only=1", "--do_verify=1", "--readonly")
    }

    $HostHandle = Start-HostObserver -Phase $Phase.name
    $FioExitCode = 1
    try {
        Write-Host "=== Running phase $($Phase.order): $($Phase.name) ==="
        & fio @FioArgs
        $FioExitCode = $LASTEXITCODE
    }
    finally {
        Stop-HostObserver -Handle $HostHandle
    }

    $RunRecord.completed_at = (Get-Date).ToString("o")
    $RunRecord.exit_code = $FioExitCode
    $RunRecord.status = if ($FioExitCode -eq 0) { "complete" } else { "failed" }
    $RunnerManifest.runs += $RunRecord
    $Phase.completed_at = (Get-Date).ToString("o")
    $Phase.status = $RunRecord.status
    Save-Manifests

    if ($FioExitCode -ne 0) {
        throw "fio phase $($Phase.name) failed with exit code $FioExitCode"
    }
    if (-not (Test-Path -LiteralPath $OutFile)) {
        throw "fio JSON was not created: $OutFile"
    }
    if (-not (Test-Path -LiteralPath $TestFile)) {
        throw "Verification target is missing after phase $($Phase.name): $TestFile"
    }

    $Job = (Get-Content -Raw -LiteralPath $OutFile | ConvertFrom-Json).jobs[0]
    if ([int]$Job.error -ne 0) {
        throw "fio JSON reports job error $($Job.error) in phase $($Phase.name)"
    }
    $Direction = if ($Phase.operation -eq "write") { $Job.write } else { $Job.read }
    if ([long]$Direction.io_bytes -ne $ExpectedBytes) {
        throw "Phase $($Phase.name) completed unexpected bytes. Expected=$ExpectedBytes, actual=$($Direction.io_bytes)"
    }
    $ObservedFile = Get-Item -LiteralPath $TestFile -ErrorAction Stop
    if ([long]$ObservedFile.Length -ne $ExpectedBytes) {
        throw "Verification target length mismatch. Expected=$ExpectedBytes, actual=$($ObservedFile.Length)"
    }
}

Save-Manifests

Write-Host "=== External SSD file-target integrity MVP ==="
Write-Host "Experiment : $SafeExperiment"
Write-Host "Test file  : $TestFile"
Write-Host "Write      : 4 GiB, CRC32C, bs=1M, QD4"
Write-Host "Verify     : complete verify-only read"
Write-Host "Manifest   : $ExperimentManifestPath"
Write-Host ""

try {
    Write-Host "=== Preparing new dedicated 4 GiB verification file ==="
    Initialize-DedicatedVerificationFile
    Invoke-StaticObserver -Phase "pre"
    Invoke-IntegrityPhase -Phase $Phases[0]
    Invoke-IntegrityPhase -Phase $Phases[1]
    Invoke-StaticObserver -Phase "post"

    $RunnerManifest.completed_at = (Get-Date).ToString("o")
    $RunnerManifest.status = "complete"
    $ExperimentManifest.completed_at = (Get-Date).ToString("o")
    $ExperimentManifest.status = "complete"
    Save-Manifests
}
catch {
    if ($ExperimentManifest.target_preparation.status -eq "running") {
        $ExperimentManifest.target_preparation.status = "failed"
        $ExperimentManifest.target_preparation.completed_at = (Get-Date).ToString("o")
    }
    foreach ($Phase in $Phases) {
        if ($Phase.status -eq "running") {
            $Phase.status = "failed"
            $Phase.completed_at = (Get-Date).ToString("o")
        }
    }
    $RunnerManifest.completed_at = (Get-Date).ToString("o")
    $RunnerManifest.status = "failed"
    $ExperimentManifest.completed_at = (Get-Date).ToString("o")
    $ExperimentManifest.status = "failed"
    $ExperimentManifest.error = $_.Exception.Message
    Save-Manifests
    throw
}

Write-Host "=== Integrity execution completed ==="
Write-Host "The 4 GiB target is retained. Run the analyzer before deciding whether to remove it."
Write-Host "Result directory: $ResultDir"
