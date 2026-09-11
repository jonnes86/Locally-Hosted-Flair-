# Flair Local — Local Control for Flair Smart Vents

## Objective

Build a fully local controller for personally-owned Flair Smart Vents, eliminating dependence on Flair's cloud API. The finished system integrates with Home Assistant OS via MQTT Discovery, using Ecobee room sensors for temperature and occupancy data.

## Current Phase: Phase 1 — Receive-Only RF Discovery

Using an RTL-SDR V3 to characterize the Flair 915 MHz RF protocol before selecting transceiver hardware.

## Architecture Overview

```
┌──────────────────┐     MQTT      ┌──────────────┐
│  Home Assistant   │◄────────────►│  Local Flair  │
│  OS (VMware VM)   │              │   Gateway     │
│                   │              │               │
│  ┌─────────────┐  │              │  915 MHz RF   │
│  │ Ecobee      │  │              │      │        │
│  │ Integration │  │              └──────┼────────┘
│  │ (temp/occ)  │  │                     │
│  └─────────────┘  │                     ▼
│                   │              ┌──────────────┐
│  ┌─────────────┐  │              │  Flair Smart  │
│  │ Flair MQTT  │  │              │  Vent (×N)    │
│  │ Integration │  │              └──────────────┘
│  └─────────────┘  │
└──────────────────┘
```

## Hardware

### Current (Phase 1 — Receive Only)

| Item | Model | Purpose |
|------|-------|---------|
| SDR Receiver | RTL-SDR.com Blog V3 (R820T2 + RTL2832U) | Wideband receive-only scanning |
| Antenna | 915 MHz antenna | ISM band reception |
| Host PC | Windows 11 Pro x64 | Capture and analysis |
| Flair Gateway | Flair Puck or Bridge (model TBD) | Existing Flair gateway |
| Flair Vents | Flair Smart Vent (×N) | Target devices |
| Ecobee Sensors | Ecobee Room Sensors (×N per room) | Temperature + occupancy |
| Home Assistant | HA OS on VMware OVA | Automation platform |

### Future (Phase 2+ — TBD after RF characterization)

| Item | Model | Purpose |
|------|-------|---------|
| Transceiver | TBD — depends on observed protocol | Local gateway radio |
| Gateway platform | TBD (ESP32 / RPi / custom) | Runs local gateway software |

## Project Structure

```
flair-local/
├── README.md                 ← This file
├── .gitignore                ← Excludes raw IQ files
├── docs/
│   ├── capture-plan.md       ← Step-by-step experiment plan
│   ├── protocol-notes.md     ← Protocol observations and hypotheses
│   ├── signal-inventory.md   ← Catalog of discovered RF signals
│   └── hardware-decisions.md ← Hardware selection rationale
├── captures/
│   ├── README.md             ← Naming conventions and file formats
│   ├── metadata/             ← JSON metadata for each capture (Git-tracked)
│   ├── raw/                  ← Raw IQ files (NOT in Git)
│   ├── processed/            ← Derived files (NOT in Git)
│   └── analysis/             ← Spectrograms, analysis outputs (Git-tracked)
├── tools/
│   ├── scan/                 ← Wideband scanning scripts
│   │   ├── flair_scan.py     ← rtl_power wrapper with metadata
│   │   └── plot_scan.py      ← Scan result visualization
│   ├── capture/              ← Narrow-band IQ capture scripts
│   │   └── flair_capture.py  ← rtl_sdr wrapper with metadata
│   └── analysis/             ← Signal analysis tools
│       └── compare_captures.py ← Compare capture metadata
├── gateway/                  ← Future: local gateway software
├── home-assistant/           ← Future: HA integration configs
└── tests/                    ← Future: automated tests
```

## Design Principles

1. **Receive first, transmit later.** Fully characterize the protocol before selecting TX hardware.
2. **Document everything.** Every observation is tagged with confidence level.
3. **Reproducible.** All experiments use scripted captures with full metadata.
4. **No cloud.** The finished system operates without Internet.
5. **Fail safe.** HVAC safety logic enforces minimum airflow and fails open.
6. **Own your devices.** All equipment is personally owned and authorized for testing.

## Safety

- Phase 1 is **receive-only** — no RF transmissions.
- All Flair equipment is personally owned.
- HVAC safety logic (minimum airflow, fail-open) is a hard requirement.
- No interference with other devices or networks.

## Quick Start — Phase 1

See [docs/capture-plan.md](docs/capture-plan.md) for the full experiment plan.

### 1. Verify RTL-SDR
```powershell
rtl_test -t
```

### 2. Baseline scan (no Flair devices powered)
```powershell
python tools/scan/flair_scan.py --start 902e6 --stop 928e6 --bin-width 25000 --interval 1 --duration 120 --gain 20 --output captures/metadata/baseline_noflair
```

### 3. Active scan (Flair idle)
```powershell
python tools/scan/flair_scan.py --start 902e6 --stop 928e6 --bin-width 25000 --interval 1 --duration 300 --gain 20 --output captures/metadata/scan_flair_idle
```

### 4. Narrow capture at discovered frequency
```powershell
python tools/capture/flair_capture.py --freq <discovered_hz> --rate 2048000 --gain 20 --duration 30 --label vent01-open --device vent01
```

## License

Personal research project. Not affiliated with Flair or Ecobee.
