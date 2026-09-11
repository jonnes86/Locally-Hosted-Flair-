# Flair RF Protocol Notes

**Version:** 1.0  
**Date:** 2026-09-10  
**Status:** Phase 1 — Receive-only discovery  

## Purpose

This document records all observations, hypotheses, and confirmed facts about the Flair Smart Vent RF protocol. Every claim is tagged with a confidence level.

## Confidence Levels

| Level | Meaning |
|-------|---------|
| **CONFIRMED** | Verified by Flair documentation or multiple independent observations |
| **OBSERVED** | Directly seen in our captures with supporting evidence |
| **INFERRED** | Deduced from signal characteristics but not independently confirmed |
| **HYPOTHESIZED** | Educated guess based on available evidence — needs validation |
| **UNKNOWN** | Not yet determined |

---

## Prior Knowledge (Pre-Capture)

These facts are known before any RF captures:

| Fact | Source | Confidence |
|------|--------|------------|
| Flair operates in the US 915 MHz ISM band (902–928 MHz) | Flair product documentation, FCC filings | CONFIRMED |
| Flair Puck/Bridge acts as the gateway | Flair product documentation | CONFIRMED |
| Vent positions: 0% (closed), 50% (half), 100% (open) | Flair app behavior | CONFIRMED |
| Communication uses proprietary 915 MHz RF, not Wi-Fi/Zigbee/Z-Wave/BLE for vent link | Flair documentation | CONFIRMED |
| Flair Puck connects to cloud via Wi-Fi; vent link is separate | Flair documentation | CONFIRMED |

## FCC Filing Research

**Grantee:** Standard Euler, Inc. — Grantee Code: **2AK78**

| Device | FCC ID | Product Code | Filed | Equipment Class | Notes |
|--------|--------|-------------|-------|-----------------|-------|
| Flair Smart Vent | **2AK78VENTI** | VENTI | 2017-08-16 | DXX (Part 15C) | Frequency range: **905–925 MHz** |
| Flair Bridge | **2AK78BRIDGE** | BRIDGE | 2024-06-17 | DXX (Part 15C) | Uses **TI CC1101** transceiver |
| Flair Puck 2 | **2AK78PUCK2** | PUCK2 | 2026-05-06 | DXX (Part 15C) | Wireless Thermostat; includes ANT test reports |
| Flair Puck (original) | **2AK78PUCKU** | PUCKU | (earlier) | Part 15C | Original Puck |
| Flair Bridge Pro | **2AK78BRIDGEPRO** | BRIDGEPRO | (unknown) | Part 15C | Bridge Pro variant |
| Flair Vent (alt) | **2AK78VENTO** | VENTO | (unknown) | Part 15C | Alternate vent model |

### Key FCC Findings

| Finding | Source | Confidence |
|---------|--------|------------|
| Vent operates in **905–925 MHz** range | FCC filing 2AK78VENTI | CONFIRMED |
| Bridge uses **TI CC1101** transceiver | FCC filing 2AK78BRIDGE + web references | CONFIRMED |
| Equipment class is **DXX** (Part 15 Low Power Communication Device Transmitter) | FCC grant records | CONFIRMED |
| DXX classification suggests **NOT frequency hopping** (FHSS would typically be class DSS or DTS) | FCC classification rules | INFERRED |
| CC1101 supports 2-FSK, GFSK, 4-FSK, MSK, OOK/ASK modulations | TI CC1101 datasheet | CONFIRMED (chip capability) |
| Actual modulation used by Flair is likely **2-FSK or GFSK** | CC1101 common configurations | HYPOTHESIZED |
| CC1101 supports data rates from 0.6 to 500 kbps | TI CC1101 datasheet | CONFIRMED (chip capability) |

### Implications for Capture Strategy

1. **Frequency range narrowed:** Focus scanning on **905–925 MHz** (not full 902–928).
2. **No FHSS expected:** DXX classification and CC1101 at low data rates typically use a fixed channel or small channel set — not full frequency hopping. This greatly simplifies capture.
3. **CC1101 compatibility:** The CC1101 is extremely well-documented. Once modulation and data rate are confirmed from captures, an ESP32 + CC1101 module is a strong gateway candidate.
4. **Test reports needed:** The full FCC test reports (PDFs) contain exact modulation type, data rate, occupied bandwidth, and TX power. These should be downloaded from the FCC exhibit pages when accessible.

### Action Items

- [x] Identify FCC IDs for all Flair devices
- [x] Confirm grantee (Standard Euler, Inc.)
- [x] Determine equipment classification (DXX / Part 15C)
- [x] Identify RF transceiver chip (CC1101 in Bridge)
- [ ] Download full test reports from FCC for exact modulation/bandwidth/power
- [ ] Check if Vent uses the same CC1101 or a different transceiver
- [ ] Review internal photos for chip identification on Vent PCB

---

## Physical Layer Observations

### Frequency

| Parameter | Value | Confidence |
|-----------|-------|------------|
| Band | 902–928 MHz ISM | CONFIRMED |
| Center frequency | UNKNOWN | UNKNOWN |
| Channel count | UNKNOWN | UNKNOWN |
| Channel spacing | UNKNOWN | UNKNOWN |
| Frequency hopping | UNKNOWN | UNKNOWN |

### Modulation

| Parameter | Value | Confidence |
|-----------|-------|------------|
| Modulation type | UNKNOWN | UNKNOWN |
| Symbol rate | UNKNOWN | UNKNOWN |
| Deviation (if FSK) | UNKNOWN | UNKNOWN |
| Occupied bandwidth | UNKNOWN | UNKNOWN |

### Timing

| Parameter | Value | Confidence |
|-----------|-------|------------|
| Burst duration | UNKNOWN | UNKNOWN |
| Inter-burst gap | UNKNOWN | UNKNOWN |
| Keepalive interval | UNKNOWN | UNKNOWN |
| Command-to-ACK delay | UNKNOWN | UNKNOWN |

---

## Packet Structure

### Preamble and Sync

| Field | Value | Length | Confidence |
|-------|-------|--------|------------|
| Preamble pattern | UNKNOWN | UNKNOWN | UNKNOWN |
| Sync word | UNKNOWN | UNKNOWN | UNKNOWN |

### Packet Fields (Hypothesized)

```
[Preamble] [Sync] [Header?] [Address?] [Command?] [Payload?] [Sequence?] [CRC/Checksum?]
```

*All field boundaries and contents are UNKNOWN until captures are analyzed.*

---

## Message Types

| Type | Direction | Identified? | Confidence |
|------|-----------|-------------|------------|
| Position command (open/close/50%) | Gateway → Vent | UNKNOWN | UNKNOWN |
| Position acknowledgment | Vent → Gateway | UNKNOWN | UNKNOWN |
| Position report | Vent → Gateway | UNKNOWN | UNKNOWN |
| Battery voltage report | Vent → Gateway | UNKNOWN | UNKNOWN |
| Duct temperature report | Vent → Gateway | UNKNOWN | UNKNOWN |
| Duct pressure report | Vent → Gateway | UNKNOWN | UNKNOWN |
| Keepalive / heartbeat | Both? | UNKNOWN | UNKNOWN |
| Pairing request | Either? | UNKNOWN | UNKNOWN |
| Pairing response | Either? | UNKNOWN | UNKNOWN |

---

## Security Assessment

| Question | Answer | Confidence |
|----------|--------|------------|
| Are packets encrypted? | UNKNOWN | UNKNOWN |
| Is there a rolling counter / nonce? | UNKNOWN | UNKNOWN |
| Is there a CRC or checksum? | UNKNOWN | UNKNOWN |
| Is simple replay possible? | UNKNOWN — do NOT test until Phase 2+ | UNKNOWN |
| Is there a pairing / key exchange? | UNKNOWN | UNKNOWN |

---

## Observations Log

Chronological log of observations during captures.

| Date | Experiment | Observation | Confidence |
|------|-----------|-------------|------------|
| — | — | — | — |

---

## Open Questions

1. What is the exact center frequency or frequencies?
2. Does the protocol use frequency hopping?
3. What modulation scheme is used?
4. Are packets encrypted?
5. What is the packet structure?
6. How does pairing work?
7. Are there rolling counters that prevent replay?
8. What chipset does the Puck/Bridge use for 915 MHz? (May be revealed by FCC filings)
9. Is there a published or reverse-engineered protocol specification?
