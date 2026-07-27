Set-StrictMode -Version Latest

function Get-ExternalSsdSha256 {
    param([Parameter(Mandatory)][string]$Text)

    $Sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $Bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        $HashBytes = $Sha.ComputeHash($Bytes)
        return ([System.BitConverter]::ToString($HashBytes) -replace "-", "").ToLowerInvariant()
    }
    finally {
        $Sha.Dispose()
    }
}

function Resolve-ExternalSsdTargetPath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$TestFile,
        [Parameter(Mandatory)][string]$AllowedRoot
    )

    if ([string]::IsNullOrWhiteSpace($TestFile)) {
        throw "TestFile is required."
    }
    if ([string]::IsNullOrWhiteSpace($AllowedRoot)) {
        throw "AllowedRoot is required."
    }

    $AllowedItem = Get-Item -LiteralPath $AllowedRoot -ErrorAction Stop
    if (-not $AllowedItem.PSIsContainer) {
        throw "AllowedRoot must be an existing directory: $AllowedRoot"
    }

    $AllowedFull = [System.IO.Path]::GetFullPath($AllowedItem.FullName).TrimEnd("\")
    $TargetFull = [System.IO.Path]::GetFullPath($TestFile)
    if ($TargetFull.StartsWith("\\", [System.StringComparison]::Ordinal)) {
        throw "UNC and device paths are not allowed: $TestFile"
    }
    if ($TargetFull.Length -gt 2 -and $TargetFull.Substring(2).Contains(":")) {
        throw "Alternate data streams are not allowed: $TestFile"
    }

    $ParentText = Split-Path -Parent $TargetFull
    $Leaf = Split-Path -Leaf $TargetFull
    if ([string]::IsNullOrWhiteSpace($Leaf) -or $Leaf -in @(".", "..")) {
        throw "TestFile must name a file below AllowedRoot: $TestFile"
    }
    $ParentItem = Get-Item -LiteralPath $ParentText -ErrorAction Stop
    if (-not $ParentItem.PSIsContainer) {
        throw "Target parent must be a directory: $ParentText"
    }

    $CanonicalParent = [System.IO.Path]::GetFullPath($ParentItem.FullName).TrimEnd("\")
    $AllowedPrefix = $AllowedFull + "\"
    if (
        -not $CanonicalParent.Equals(
            $AllowedFull,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -and
        -not $CanonicalParent.StartsWith(
            $AllowedPrefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw "Canonical target parent escapes AllowedRoot. Target=$TargetFull Root=$AllowedFull"
    }

    $Current = $AllowedItem
    if (($Current.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "AllowedRoot must not be a reparse point: $AllowedFull"
    }
    $RelativeParent = $CanonicalParent.Substring($AllowedFull.Length).TrimStart("\")
    if ($RelativeParent) {
        foreach ($Segment in $RelativeParent.Split("\")) {
            $Current = Get-Item -LiteralPath (Join-Path $Current.FullName $Segment) -ErrorAction Stop
            if (($Current.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Reparse points are not allowed in the target path: $($Current.FullName)"
            }
        }
    }

    $CanonicalTarget = [System.IO.Path]::GetFullPath(
        (Join-Path $CanonicalParent $Leaf)
    )
    if (Test-Path -LiteralPath $CanonicalTarget) {
        $TargetItem = Get-Item -LiteralPath $CanonicalTarget -ErrorAction Stop
        if ($TargetItem.PSIsContainer) {
            throw "TestFile resolves to a directory: $CanonicalTarget"
        }
        if (($TargetItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "TestFile must not be a reparse point: $CanonicalTarget"
        }
        $CanonicalTarget = [System.IO.Path]::GetFullPath($TargetItem.FullName)
    }

    [pscustomobject][ordered]@{
        canonical_target = $CanonicalTarget
        canonical_allowed_root = $AllowedFull
        target_exists = [bool](Test-Path -LiteralPath $CanonicalTarget)
        drive_letter = [System.IO.Path]::GetPathRoot($CanonicalTarget).Substring(0, 1).ToUpperInvariant()
    }
}

function Assert-ExternalSsdIdentityRecord {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$Expected,
        [Parameter(Mandatory)]$Volume,
        [Parameter(Mandatory)]$Disk
    )

    $FingerprintMaterial = @(
        $Disk.FriendlyName.ToString().Trim().ToUpperInvariant()
        $Disk.SerialNumber.ToString().Trim().ToUpperInvariant()
        $Disk.UniqueId.ToString().Trim().ToUpperInvariant()
        $Disk.BusType.ToString().Trim().ToUpperInvariant()
    ) -join "|"
    $ObservedFingerprint = Get-ExternalSsdSha256 -Text $FingerprintMaterial

    $Checks = @(
        [pscustomobject]@{
            name = "drive_letter"
            observed = $Volume.DriveLetter.ToString()
            expected = $Expected.drive_letter.ToString()
        }
        [pscustomobject]@{
            name = "file_system"
            observed = $Volume.FileSystem.ToString()
            expected = $Expected.file_system.ToString()
        }
        [pscustomobject]@{
            name = "volume_label"
            observed = $Volume.FileSystemLabel.ToString()
            expected = $Expected.volume_label.ToString()
        }
        [pscustomobject]@{
            name = "volume_unique_id"
            observed = $Volume.UniqueId.ToString()
            expected = $Expected.volume_unique_id.ToString()
        }
        [pscustomobject]@{
            name = "size_bytes"
            observed = ([uint64]$Volume.Size).ToString()
            expected = ([uint64]$Expected.size_bytes).ToString()
        }
        [pscustomobject]@{
            name = "disk_friendly_name"
            observed = $Disk.FriendlyName.ToString().Trim()
            expected = $Expected.disk_friendly_name.ToString()
        }
        [pscustomobject]@{
            name = "bus_type"
            observed = $Disk.BusType.ToString()
            expected = $Expected.bus_type.ToString()
        }
        [pscustomobject]@{
            name = "disk_fingerprint_sha256"
            observed = $ObservedFingerprint
            expected = $Expected.disk_fingerprint_sha256.ToString()
        }
    )
    foreach ($Check in $Checks) {
        if (-not $Check.observed.Equals($Check.expected, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "DUT identity mismatch for $($Check.name)."
        }
    }
    if ([bool]$Expected.require_not_boot -and [bool]$Disk.IsBoot) {
        throw "DUT identity rejected: target disk is a boot disk."
    }
    if ([bool]$Expected.require_not_system -and [bool]$Disk.IsSystem) {
        throw "DUT identity rejected: target disk is a system disk."
    }

    [pscustomobject][ordered]@{
        identity_match = $true
        drive_letter = $Volume.DriveLetter.ToString().ToUpperInvariant()
        file_system = $Volume.FileSystem.ToString()
        volume_label = $Volume.FileSystemLabel.ToString()
        volume_unique_id = $Volume.UniqueId.ToString()
        size_bytes = [uint64]$Volume.Size
        disk_friendly_name = $Disk.FriendlyName.ToString().Trim()
        bus_type = $Disk.BusType.ToString()
        disk_fingerprint_sha256 = $ObservedFingerprint
        is_boot = [bool]$Disk.IsBoot
        is_system = [bool]$Disk.IsSystem
    }
}

function Assert-ExternalSsdTarget {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$TestFile,
        [Parameter(Mandatory)][string]$IdentityConfigPath,
        [switch]$RequireExistingTarget,
        [switch]$RequireNewTarget,
        [uint64]$ExpectedFileBytes = 0,
        [uint64]$RequiredFreeBytes = 0
    )

    if ($RequireExistingTarget -and $RequireNewTarget) {
        throw "RequireExistingTarget and RequireNewTarget are mutually exclusive."
    }
    $Config = Get-Content -LiteralPath $IdentityConfigPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    if ($Config.schema_version -ne "1.0" -or -not $Config.expected) {
        throw "Unsupported or incomplete DUT identity config: $IdentityConfigPath"
    }

    $PathEvidence = Resolve-ExternalSsdTargetPath `
        -TestFile $TestFile `
        -AllowedRoot $Config.allowed_root
    if (
        -not $PathEvidence.drive_letter.Equals(
            $Config.expected.drive_letter.ToString(),
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw "Target drive does not match enrolled DUT drive."
    }

    $Volume = Get-Volume -DriveLetter $PathEvidence.drive_letter -ErrorAction Stop
    $Partition = Get-Partition -DriveLetter $PathEvidence.drive_letter -ErrorAction Stop
    $Disk = $Partition | Get-Disk -ErrorAction Stop
    $IdentityEvidence = Assert-ExternalSsdIdentityRecord `
        -Expected $Config.expected `
        -Volume $Volume `
        -Disk $Disk

    if ($Volume.HealthStatus -ne "Healthy" -or $Volume.OperationalStatus -notcontains "OK") {
        throw "DUT volume is not Healthy/OK."
    }
    if ($RequireExistingTarget -and -not $PathEvidence.target_exists) {
        throw "Required existing target does not exist: $($PathEvidence.canonical_target)"
    }
    if ($RequireNewTarget -and $PathEvidence.target_exists) {
        throw "New target already exists and will not be overwritten: $($PathEvidence.canonical_target)"
    }
    if ($ExpectedFileBytes -gt 0 -and $PathEvidence.target_exists) {
        $File = Get-Item -LiteralPath $PathEvidence.canonical_target -ErrorAction Stop
        if ([uint64]$File.Length -ne $ExpectedFileBytes) {
            throw "Target size mismatch. Expected=$ExpectedFileBytes Actual=$($File.Length)"
        }
    }
    if ($RequiredFreeBytes -gt 0 -and [uint64]$Volume.SizeRemaining -lt $RequiredFreeBytes) {
        throw "Insufficient DUT free space. Required=$RequiredFreeBytes Actual=$($Volume.SizeRemaining)"
    }

    [pscustomobject][ordered]@{
        dut_id = $Config.dut_id.ToString()
        canonical_target = $PathEvidence.canonical_target
        canonical_allowed_root = $PathEvidence.canonical_allowed_root
        target_exists = $PathEvidence.target_exists
        identity = $IdentityEvidence
        health_status = $Volume.HealthStatus.ToString()
        operational_status = @($Volume.OperationalStatus | ForEach-Object { $_.ToString() })
        size_remaining_bytes = [uint64]$Volume.SizeRemaining
    }
}

Export-ModuleMember -Function @(
    "Resolve-ExternalSsdTargetPath",
    "Assert-ExternalSsdIdentityRecord",
    "Assert-ExternalSsdTarget"
)
