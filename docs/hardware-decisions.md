# Hardware Decisions Log

**Version:** 1.0  
**Date:** 2026-09-10  
**Status:** Phase 1 — No transceiver hardware selected yet  

## Purpose

This document tracks hardware selection decisions for the Flair local gateway. Hardware choices are driven by observed RF protocol characteristics, NOT assumptions.

## Current Hardware

| Item | Model | Purpose | Status |
|------|-------|---------|--------|
| SDR Receiver | RTL-SDR.com Blog V3 (R820T2/RTL2832U) | Receive-only scanning and capture | Available |
| Antenna | 915 MHz (type TBD) | ISM band reception | Available |
| Host PC | Windows 11 Pro x64 | Capture and analysis | Active |

## Transceiver Selection Criteria

**Do NOT select a transceiver until Phase 1 receive-only characterization is complete.**

The transceiver must satisfy ALL of the following, based on observed protocol characteristics:

| Requirement | Determined By | Current Value |
|-------------|---------------|---------------|
| Frequency coverage | Observed center freq + hopping range | UNKNOWN |
| Modulation support | Observed modulation type | UNKNOWN |
| Data rate | Observed symbol rate | UNKNOWN |
| Bandwidth | Observed occupied BW | UNKNOWN |
| Frequency hopping | Observed hop pattern + timing | UNKNOWN |
| Timing precision | Observed burst/ACK timing | UNKNOWN |
| TX power | Puck/Bridge FCC filing | UNKNOWN |

## Candidate Transceivers

*Evaluate AFTER Phase 1 data is collected.*

| Candidate | Freq Range | Modulation | Hop Support | Notes | Suitability |
|-----------|-----------|------------|-------------|-------|-------------|
| TI CC1101 | 300–928 MHz | OOK/2-FSK/GFSK/4-FSK/MSK | Yes (with MCU) | Common in ISM devices | TBD |
| Semtech SX1276 | 137–1020 MHz | LoRa/FSK/OOK | Limited | LoRa-focused | TBD |
| HackRF One | 1 MHz–6 GHz | Any (SDR) | Yes (software) | Full SDR, half-duplex | TBD |
| YARD Stick One | 300–928 MHz | OOK/GFSK/2-FSK/4-FSK/MSK | Yes | CC1111-based, designed for ISM | TBD |
| TI CC1110/CC1111 | 300–928 MHz | Same as CC1101 | Yes | SoC version with 8051 MCU | TBD |
| Flipper Zero (internal) | Sub-GHz | CC1101-based | Yes | Consumer tool, limited API | TBD |

## Decision Log

| Date | Decision | Rationale | Evidence |
|------|----------|-----------|----------|
| 2026-09-10 | Begin with RTL-SDR V3 receive-only | Discover protocol before selecting TX hardware | Project requirement |
| — | — | — | — |

## Gateway Platform Candidates

*Evaluate AFTER transceiver is selected.*

| Platform | Pros | Cons | Suitability |
|----------|------|------|-------------|
| ESP32 + sub-GHz transceiver | Low power, ESPHome compatible, cheap | Limited processing, needs external radio | TBD |
| Raspberry Pi + USB transceiver | Full Linux, easy development | More power, overkill? | TBD |
| Custom PCB | Optimized, compact | Development time, cost for small qty | TBD |
| Repurposed Flair Bridge | Already has correct radio | Requires firmware RE, may be locked | TBD |
