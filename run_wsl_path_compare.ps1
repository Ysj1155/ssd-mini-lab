# run_wsl_path_compare.ps1
#
# Purpose:
#   Launch the WSL path comparison fio script from Windows PowerShell.
#
# Safety:
#   The WSL script uses regular files only and does not target raw block devices.
#
# Usage:
#   cd D:\ssd_lab
#   .\run_wsl_path_compare.ps1

$ErrorActionPreference = "Stop"

$BaseDir = "D:\ssd_lab"
$WslDistro = $env:SSD_LAB_WSL_DISTRO

if ([string]::IsNullOrWhiteSpace($WslDistro)) {
    $WslDistro = "Ubuntu"
}

$WslScript = "/mnt/d/ssd_lab/scripts/run_wsl_path_compare.sh"

Write-Host "=== Launch WSL path comparison ==="
Write-Host "BaseDir   : $BaseDir"
Write-Host "WSL distro: $WslDistro"
Write-Host "WSL script: $WslScript"
Write-Host ""

wsl.exe -d $WslDistro -- bash $WslScript

Write-Host ""
Write-Host "[DONE] WSL path comparison launcher completed."
