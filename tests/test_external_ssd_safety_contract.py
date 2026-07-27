from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "lib" / "ExternalSsdSafety.psm1"
IDENTITY_CONFIG = REPO_ROOT / "configs" / "external_ssd_dut_identity.json"
RUNNER_DIR = REPO_ROOT / "scripts" / "runners"


def ps_quote(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class ExternalSsdSafetyContractTests(unittest.TestCase):
    def test_all_external_runners_use_shared_preflight(self) -> None:
        runners = sorted(RUNNER_DIR.glob("run_external_ssd*.ps1"))
        self.assertEqual(len(runners), 14)

        for runner in runners:
            text = runner.read_text(encoding="utf-8-sig")
            with self.subTest(runner=runner.name):
                self.assertIn("ExternalSsdSafety.psm1", text)
                self.assertIn("$DutPreflight = Assert-ExternalSsdTarget", text)
                self.assertNotIn('$TestFile -like "E:\\validation\\*"', text)
                self.assertNotIn("Get-Volume -DriveLetter E", text)
                preflight_at = text.index(
                    "$DutPreflight = Assert-ExternalSsdTarget"
                )
                new_item_at = text.find("New-Item -ItemType Directory")
                if new_item_at >= 0:
                    self.assertLess(preflight_at, new_item_at)

    def test_manifest_producing_runners_record_safe_preflight(self) -> None:
        excluded = {
            "run_external_ssd_qd_smoke.ps1",
            "run_external_ssd_traced_sustained.ps1",
        }
        for runner in sorted(RUNNER_DIR.glob("run_external_ssd*.ps1")):
            if runner.name in excluded:
                continue
            with self.subTest(runner=runner.name):
                text = runner.read_text(encoding="utf-8-sig")
                self.assertIn("dut_preflight = $DutPreflight", text)

    def test_enrollment_config_omits_raw_serial(self) -> None:
        config = json.loads(IDENTITY_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["dut_id"], "external_ssd_dut_01")
        self.assertEqual(config["expected"]["bus_type"], "USB")
        self.assertNotIn("serial_number", config["expected"])
        self.assertRegex(
            config["expected"]["disk_fingerprint_sha256"],
            r"^[0-9a-f]{64}$",
        )

    def test_canonical_path_contract_rejects_escape_prefix_and_ads(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp:
            base = Path(temp)
            allowed = base / "validation"
            nested = allowed / "nested"
            sibling = base / "validation_evil"
            nested.mkdir(parents=True)
            sibling.mkdir()

            script = f"""
$ErrorActionPreference = "Stop"
Import-Module {ps_quote(MODULE_PATH)} -Force
$accepted = Resolve-ExternalSsdTargetPath `
    -TestFile {ps_quote(nested / "target.bin")} `
    -AllowedRoot {ps_quote(allowed)}
$escapeRejected = $false
$prefixRejected = $false
$adsRejected = $false
$reparseRejected = $false
try {{
    Resolve-ExternalSsdTargetPath `
        -TestFile {ps_quote(allowed / ".." / "escape.bin")} `
        -AllowedRoot {ps_quote(allowed)} | Out-Null
}} catch {{ $escapeRejected = $true }}
try {{
    Resolve-ExternalSsdTargetPath `
        -TestFile {ps_quote(sibling / "target.bin")} `
        -AllowedRoot {ps_quote(allowed)} | Out-Null
}} catch {{ $prefixRejected = $true }}
try {{
    Resolve-ExternalSsdTargetPath `
        -TestFile {ps_quote(allowed / "target.bin:stream")} `
        -AllowedRoot {ps_quote(allowed)} | Out-Null
}} catch {{ $adsRejected = $true }}
$junction = {ps_quote(allowed / "junction")}
New-Item -ItemType Junction -Path $junction -Target {ps_quote(sibling)} |
    Out-Null
try {{
    Resolve-ExternalSsdTargetPath `
        -TestFile (Join-Path $junction "target.bin") `
        -AllowedRoot {ps_quote(allowed)} | Out-Null
}} catch {{ $reparseRejected = $true }}
Remove-Item -LiteralPath $junction -Force
[ordered]@{{
    accepted = $accepted.canonical_target
    escape_rejected = $escapeRejected
    prefix_rejected = $prefixRejected
    ads_rejected = $adsRejected
    reparse_rejected = $reparseRejected
}} | ConvertTo-Json -Compress
"""
            result = run_powershell(script)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout.strip())
        self.assertTrue(verdict["accepted"].endswith("target.bin"))
        self.assertTrue(verdict["escape_rejected"])
        self.assertTrue(verdict["prefix_rejected"])
        self.assertTrue(verdict["ads_rejected"])
        self.assertTrue(verdict["reparse_rejected"])

    def test_identity_record_matches_fingerprint_and_rejects_mismatch(self) -> None:
        material = "MODEL TEST|SERIAL-TEST-001|DISK-TEST-001|USB"
        fingerprint = hashlib.sha256(material.encode()).hexdigest()
        script = f"""
$ErrorActionPreference = "Stop"
Import-Module {ps_quote(MODULE_PATH)} -Force
$expected = [pscustomobject]@{{
    drive_letter = "E"
    file_system = "exFAT"
    volume_label = "Test SSD"
    volume_unique_id = "volume-test-001"
    size_bytes = 1000
    disk_friendly_name = "Model Test"
    bus_type = "USB"
    disk_fingerprint_sha256 = "{fingerprint}"
    require_not_boot = $true
    require_not_system = $true
}}
$volume = [pscustomobject]@{{
    DriveLetter = "E"
    FileSystem = "exFAT"
    FileSystemLabel = "Test SSD"
    UniqueId = "volume-test-001"
    Size = [uint64]1000
}}
$disk = [pscustomobject]@{{
    FriendlyName = "Model Test"
    SerialNumber = "SERIAL-TEST-001"
    UniqueId = "DISK-TEST-001"
    BusType = "USB"
    IsBoot = $false
    IsSystem = $false
}}
$matched = Assert-ExternalSsdIdentityRecord `
    -Expected $expected -Volume $volume -Disk $disk
$labelRejected = $false
$bootRejected = $false
$volume.FileSystemLabel = "Wrong"
try {{
    Assert-ExternalSsdIdentityRecord `
        -Expected $expected -Volume $volume -Disk $disk | Out-Null
}} catch {{ $labelRejected = $true }}
$volume.FileSystemLabel = "Test SSD"
$disk.IsBoot = $true
try {{
    Assert-ExternalSsdIdentityRecord `
        -Expected $expected -Volume $volume -Disk $disk | Out-Null
}} catch {{ $bootRejected = $true }}
[ordered]@{{
    matched = $matched.identity_match
    fingerprint = $matched.disk_fingerprint_sha256
    label_rejected = $labelRejected
    boot_rejected = $bootRejected
    leaks_serial = ($matched.PSObject.Properties.Name -contains "serial_number")
}} | ConvertTo-Json -Compress
"""
        result = run_powershell(script)

        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout.strip())
        self.assertTrue(verdict["matched"])
        self.assertEqual(verdict["fingerprint"], fingerprint)
        self.assertTrue(verdict["label_rejected"])
        self.assertTrue(verdict["boot_rejected"])
        self.assertFalse(verdict["leaks_serial"])


if __name__ == "__main__":
    unittest.main()
