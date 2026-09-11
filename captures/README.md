# Captures Directory

## Purpose

This directory stores metadata, hashes, and analysis results for RF captures. **Raw IQ files are NOT committed to Git** — they are excluded via `.gitignore`.

## File Naming Convention

```
YYYYMMDD-HHMMSS_flair_<device>_<action>_fc-<hz>_sr-<sps>_gain-<db>.<ext>
```

### Fields

| Field | Description | Example |
|-------|-------------|--------|
| `YYYYMMDD-HHMMSS` | UTC timestamp of capture start | `20260910-201500` |
| `device` | Device identifier | `vent01`, `puck01`, `bridge01`, `all` |
| `action` | What happened during capture | See action list below |
| `fc-<hz>` | Center frequency in Hz | `fc-915000000` |
| `sr-<sps>` | Sample rate in samples/sec | `sr-2048000` |
| `gain-<db>` | Tuner gain in dB (x10 for decimals) | `gain-200` (= 20.0 dB) |

### Standard Actions

| Action | Description |
|--------|-------------|
| `idle` | System powered on, no commands issued |
| `vent01-open` | Vent 01 commanded to 100% open |
| `vent01-half` | Vent 01 commanded to 50% |
| `vent01-close` | Vent 01 commanded to 0% (closed) |
| `vent01-powerup` | Vent 01 battery reinserted |
| `vent01-powerdown` | Vent 01 battery removed |
| `vent01-button` | Physical button pressed on Vent 01 |
| `vent01-pairing` | Pairing mode initiated for Vent 01 |
| `baseline` | No Flair devices powered on |
| `scan` | Wideband frequency scan |

### File Extensions

| Extension | Content | Git-tracked? |
|-----------|---------|-------------|
| `.raw` | Raw unsigned 8-bit IQ (rtl_sdr native) | ❌ NO |
| `.cu8` | Raw unsigned 8-bit IQ (alternate name) | ❌ NO |
| `.cs8` | Raw signed 8-bit IQ | ❌ NO |
| `.cf32` | 32-bit float complex IQ | ❌ NO |
| `.wav` | WAV-wrapped IQ | ❌ NO |
| `.json` | Capture metadata | ✅ YES |
| `.csv` | Scan results (rtl_power output) | ✅ YES |
| `.sha256` | SHA-256 hash of raw file | ✅ YES |
| `.png` | Screenshots, spectrograms | ✅ YES |
| `.md` | Analysis notes | ✅ YES |

## Metadata

Every capture MUST have an accompanying `.json` metadata file. See `metadata/` for the template and completed metadata files.

## Directory Structure

```
captures/
├── README.md               ← This file
├── metadata/               ← JSON metadata for each capture (Git-tracked)
│   └── capture_template.json
├── raw/                    ← Raw IQ files (NOT in Git)
├── processed/              ← Converted/filtered files (NOT in Git)
└── analysis/               ← Analysis outputs, spectrograms (Git-tracked)
```
