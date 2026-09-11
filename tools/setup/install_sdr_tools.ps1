#Requires -Version 5.1
<#
.SYNOPSIS
    Flair Local - Phase 1 SDR Tools Setup Script

.DESCRIPTION
    Downloads and installs receive-only SDR tools for RF analysis:
    - rtl-sdr binaries (rtl_test, rtl_power, rtl_sdr, rtl_fm)
    - Python dependencies (numpy, matplotlib)
    - Instructions for GUI tools (SDR++, URH, Inspectrum)

    This script does NOT modify the RTL-SDR EEPROM or device configuration.

.NOTES
    Run from the flair-local project root directory.
    Requires internet access for downloads.
    Requires Python 3.x with pip.
#>

param(
    [string]$InstallDir = "$env:USERPROFILE\sdr-tools",
    [switch]$SkipPython,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # Speed up Invoke-WebRequest

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Flair Local - Phase 1 SDR Tools Installer" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Create install directory ---
Write-Host "[1/5] Setting up install directory: $InstallDir" -ForegroundColor Yellow

if (-not $DryRun) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    New-Item -ItemType Directory -Path "$InstallDir\rtl-sdr" -Force | Out-Null
}

# --- Step 2: Download rtl-sdr binaries ---
Write-Host "[2/5] Downloading rtl-sdr binaries..." -ForegroundColor Yellow

$rtlSdrUrl = "https://ftp.osmocom.org/binaries/windows/rtl-sdr/rtl-sdr-64bit-20240623.zip"
$rtlSdrZip = "$InstallDir\rtl-sdr-64bit.zip"
$rtlSdrDir = "$InstallDir\rtl-sdr"

if (-not $DryRun) {
    if (-not (Test-Path "$rtlSdrDir\rtl_test.exe")) {
        Write-Host "  Downloading from $rtlSdrUrl ..."
        try {
            Invoke-WebRequest -Uri $rtlSdrUrl -OutFile $rtlSdrZip -UseBasicParsing
            Write-Host "  Extracting to $rtlSdrDir ..."
            Expand-Archive -Path $rtlSdrZip -DestinationPath $rtlSdrDir -Force

            # The archive may have a subdirectory - flatten it
            $subDirs = Get-ChildItem -Path $rtlSdrDir -Directory
            foreach ($sub in $subDirs) {
                Get-ChildItem -Path $sub.FullName -Recurse | Move-Item -Destination $rtlSdrDir -Force -ErrorAction SilentlyContinue
                Remove-Item $sub.FullName -Recurse -Force -ErrorAction SilentlyContinue
            }

            Remove-Item $rtlSdrZip -Force -ErrorAction SilentlyContinue
            Write-Host "  rtl-sdr binaries installed." -ForegroundColor Green
        } catch {
            Write-Host "  WARNING: Could not download rtl-sdr automatically." -ForegroundColor Red
            Write-Host "  Please download manually from:" -ForegroundColor Red
            Write-Host "    https://ftp.osmocom.org/binaries/windows/rtl-sdr/" -ForegroundColor White
            Write-Host "  Extract to: $rtlSdrDir" -ForegroundColor White
        }
    } else {
        Write-Host "  rtl-sdr binaries already present." -ForegroundColor Green
    }
} else {
    Write-Host "  [DRY RUN] Would download rtl-sdr from $rtlSdrUrl"
}

# Add to PATH for this session
$env:PATH = "$rtlSdrDir;$env:PATH"

# --- Step 3: Install Python dependencies ---
Write-Host "[3/5] Installing Python dependencies..." -ForegroundColor Yellow

if (-not $SkipPython -and -not $DryRun) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        Write-Host "  Found Python at: $($pythonCmd.Source)"
        & python -m pip install --upgrade pip 2>&1 | Out-Null
        & python -m pip install numpy matplotlib 2>&1
        Write-Host "  Python dependencies installed." -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Python not found. Install Python 3.x first." -ForegroundColor Red
    }
} elseif ($SkipPython) {
    Write-Host "  Skipped (--SkipPython flag)." -ForegroundColor DarkGray
}

# --- Step 4: Verify installations ---
Write-Host "[4/5] Verifying installations..." -ForegroundColor Yellow

$tools = @(
    @{Name="rtl_test"; Path="$rtlSdrDir\rtl_test.exe"},
    @{Name="rtl_power"; Path="$rtlSdrDir\rtl_power.exe"},
    @{Name="rtl_sdr"; Path="$rtlSdrDir\rtl_sdr.exe"},
    @{Name="rtl_fm"; Path="$rtlSdrDir\rtl_fm.exe"}
)

$allFound = $true
foreach ($tool in $tools) {
    if (Test-Path $tool.Path) {
        Write-Host "  OK  $($tool.Name) -> $($tool.Path)" -ForegroundColor Green
    } else {
        Write-Host "  MISSING  $($tool.Name)" -ForegroundColor Red
        $allFound = $false
    }
}

# Check Python tools
$pythonOk = $false
try {
    $ver = & python --version 2>&1
    Write-Host "  OK  Python -> $ver" -ForegroundColor Green
    $pythonOk = $true
} catch {
    Write-Host "  MISSING  Python" -ForegroundColor Red
}

if ($pythonOk) {
    try {
        & python -c "import numpy; print(f'  OK  numpy -> {numpy.__version__}')" 2>&1
    } catch {
        Write-Host "  MISSING  numpy (pip install numpy)" -ForegroundColor Red
    }
    try {
        & python -c "import matplotlib; print(f'  OK  matplotlib -> {matplotlib.__version__}')" 2>&1
    } catch {
        Write-Host "  MISSING  matplotlib (pip install matplotlib)" -ForegroundColor Red
    }
}

# --- Step 5: PATH instructions ---
Write-Host ""
Write-Host "[5/5] PATH Configuration" -ForegroundColor Yellow
Write-Host ""

$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$rtlSdrDir*") {
    Write-Host "  rtl-sdr is NOT in your permanent PATH." -ForegroundColor Yellow
    Write-Host "  To add it permanently, run:" -ForegroundColor White
    Write-Host ""
    Write-Host "    [Environment]::SetEnvironmentVariable('PATH', `"$rtlSdrDir;`$([Environment]::GetEnvironmentVariable('PATH', 'User'))`", 'User')" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  For this session only, it has been added temporarily." -ForegroundColor DarkGray
} else {
    Write-Host "  rtl-sdr is already in your PATH." -ForegroundColor Green
}

# --- Summary ---
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Setup Summary" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  rtl-sdr binaries: $rtlSdrDir" -ForegroundColor White
Write-Host ""
Write-Host "  NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. PLUG IN your RTL-SDR V3 dongle" -ForegroundColor White
Write-Host ""
Write-Host "  2. INSTALL WinUSB DRIVER via Zadig:" -ForegroundColor White
Write-Host "     a. Download Zadig from: https://zadig.akeo.ie/" -ForegroundColor DarkGray
Write-Host "     b. Run Zadig as Administrator" -ForegroundColor DarkGray
Write-Host "     c. Options -> List All Devices" -ForegroundColor DarkGray
Write-Host "     d. Select 'Bulk-In, Interface (Interface 0)' from dropdown" -ForegroundColor DarkGray
Write-Host "        (It may show as 'RTL2838UHIDIR' or 'RTL2832U')" -ForegroundColor DarkGray
Write-Host "     e. Set driver to 'WinUSB (v6.x.xxxx.xxxxx)'" -ForegroundColor DarkGray
Write-Host "     f. Click 'Replace Driver' or 'Install Driver'" -ForegroundColor DarkGray
Write-Host "     g. DO NOT touch the EEPROM or any other settings" -ForegroundColor Red
Write-Host ""
Write-Host "  3. VERIFY the RTL-SDR:" -ForegroundColor White
Write-Host "     $rtlSdrDir\rtl_test.exe -t" -ForegroundColor Cyan
Write-Host ""
Write-Host "  4. RUN FIRST SCAN (no Flair devices powered):" -ForegroundColor White
Write-Host "     python tools\scan\flair_scan.py --start 902e6 --stop 928e6 --bin-width 25000 --interval 1 --duration 120 --gain 20 --output captures\metadata\baseline_noflair --rtl-power-path $rtlSdrDir\rtl_power.exe" -ForegroundColor Cyan
Write-Host ""
Write-Host "  OPTIONAL GUI TOOLS:" -ForegroundColor Yellow
Write-Host "  - SDR++:     https://www.sdrpp.org/ (or: winget install SDRpp.SDRpp)" -ForegroundColor DarkGray
Write-Host "  - URH:       pip install urh  (Universal Radio Hacker)" -ForegroundColor DarkGray
Write-Host "  - Inspectrum: https://github.com/miek/inspectrum/releases" -ForegroundColor DarkGray
Write-Host ""
