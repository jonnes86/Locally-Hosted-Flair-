# Hardware Decisions Log

**Version:** 2.0  
**Date:** 2026-09-11  
**Status:** Phase 1b — CC1101 sniffer hardware selected  

## Purpose

This document tracks hardware selection decisions for the Flair local gateway. Hardware choices are driven by observed RF protocol characteristics, NOT assumptions.

## Current Hardware

| Item | Model | Purpose | Status |
|------|-------|---------|--------|
| SDR Receiver | RTL-SDR.com Blog V3 (R820T2/RTL2832U) | Receive-only scanning and capture | ✅ Phase 1a complete |
| Antenna | 915 MHz | ISM band reception | Available |
| Host PC | Windows 11 Pro x64 | Capture and analysis | Active |
| **ESP32 DevKit** | **ESP32-WROOM-32** | **CC1101 sniffer / gateway MCU** | **TO ORDER** |
| **CC1101 Module** | **915 MHz (E07-915M10S or similar)** | **Sub-GHz transceiver** | **TO ORDER** |

## Transceiver Selection Criteria

| Requirement | Determined By | Observed Value | CC1101 Support |
|-------------|---------------|----------------|----------------|
| Frequency coverage | Scan: 904-927 MHz | **905-925 MHz** (10+ channels) | ✅ 300-928 MHz |
| Modulation support | rtl_433 analysis | **FSK with Manchester** | ✅ 2-FSK/GFSK + Manchester |
| Data rate | rtl_433 symbol timing | **~36 kbps** (est. 38.4 kbps) | ✅ 0.6-500 kbps |
| Bandwidth | Scan: per-channel BW | **~325-366 kHz** | ✅ configurable RX BW |
| Frequency hopping | Multi-channel scan | **YES — 10+ channels** | ✅ fast freq switching |
| Timing precision | Burst analysis | **2-90 ms bursts** | ✅ sub-ms packet handling |
| TX power | FCC filing | Part 15 low power | ✅ configurable |

## Candidate Transceivers — **EVALUATED**

| Candidate | Suitability | Rationale |
|-----------|-------------|-----------|
| **TI CC1101** | ✅ **SELECTED** | Same chip as Flair Bridge (FCC confirmed). Native support for observed modulation, data rate, frequency range. Hardware handles demod, sync, CRC. |
| Semtech SX1276 | ❌ Not suitable | LoRa-focused, FSK mode limited. Not CC1101-compatible at protocol level. |
| HackRF One | ⚠️ Overkill | Full SDR, but still requires software demod. Same SNR issues as RTL-SDR. $300+. |
| YARD Stick One | ⚠️ Possible | CC1111-based (CC1101 compatible), but $100+ and less flexible than ESP32+CC1101. |
| Flipper Zero | ⚠️ Limited | Has CC1101 internally, but limited API. Replay fails (community confirmed). |

## Decision Log

| Date | Decision | Rationale | Evidence |
|------|----------|-----------|----------|
| 2026-09-10 | Begin with RTL-SDR V3 receive-only | Discover protocol before selecting TX hardware | Project requirement |
| 2026-09-11 | **Select ESP32 + CC1101** for sniffer/gateway | CC1101 is the same chip Flair Bridge uses. RTL-SDR confirmed modulation and frequencies but can't extract clean packet bytes due to SNR/clock recovery limits. CC1101 handles demod in hardware. | FCC filing 2AK78BRIDGE confirms CC1101. SDR captures confirm FSK + Manchester at ~38.4 kbps on 905-925 MHz. |

## Gateway Platform — **SELECTED**

| Platform | Selection | Rationale |
|----------|-----------|-----------|
| **ESP32 + CC1101** | ✅ **SELECTED** | Low cost (~$8), same transceiver as Flair, ESPHome/Arduino support, WiFi for HA integration, becomes the final gateway hardware |
| Raspberry Pi + USB | ❌ Rejected | Overkill, no native sub-GHz radio |
| Custom PCB | ❌ Rejected (for now) | Premature — ESP32+CC1101 module is sufficient |
| Repurposed Flair Bridge | ❌ Rejected | Firmware likely locked, risk of bricking |

## Wiring & Setup

See [cc1101-wiring.md](cc1101-wiring.md) for complete wiring guide and shopping list.


## Purpose


