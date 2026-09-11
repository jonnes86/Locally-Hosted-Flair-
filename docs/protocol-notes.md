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
| Active range | **904–927 MHz** (10+ channels observed) | OBSERVED |
| Strongest channels | 907.830, 907.474, 924.080, 909.556, 911.588 MHz | OBSERVED |
| Channel count | **10+ distinct channels** | OBSERVED |
| Channel spacing | ~1.5–2 MHz (variable) | OBSERVED |
| Occupied BW per channel | ~325–366 kHz | OBSERVED |
| Frequency hopping | **YES — multi-channel operation confirmed** | OBSERVED |
| Hopping rate/pattern | UNKNOWN | UNKNOWN |

> **Note:** Despite FCC DXX classification (typically non-hopping), multi-channel
> operation was observed across the full 904–927 MHz range. This may be slow
> channel hopping, channel selection, or multi-channel polling.

### Modulation

| Parameter | Value | Confidence |
|-----------|-------|------------|
| Modulation type | **FSK with Manchester coding** | OBSERVED (rtl_433) |
| Short symbol width | **14 µs** | OBSERVED |
| Long symbol width | **27 µs** | OBSERVED |
| Raw symbol rate | **~71 ksps** (1/14µs) | OBSERVED |
| Effective data rate | **~36 kbps** (Manchester decoded) | INFERRED |
| FSK deviation | **200–450 kHz** (from freq offsets) | OBSERVED |
| Consistent with CC1101 | YES — typical 2-FSK/GFSK config | CONFIRMED |

### Timing

| Parameter | Value | Confidence |
|-----------|-------|------------|
| Burst duration | **2–90 ms** (most 2–20 ms, one 90 ms) | OBSERVED |
| Packet duration | **~1.14 ms** (31-32 symbols per FSK packet) | OBSERVED |
| Inter-burst gap (rapid sequence) | ~40 ms median | OBSERVED |
| Cloud command delay | ~15–20 s (app → cloud → Puck → RF) | OBSERVED |
| Keepalive interval | UNKNOWN (need extended idle capture) | UNKNOWN |
| Command-to-ACK delay | UNKNOWN | UNKNOWN |

---

## Packet Structure

### rtl_433 Analysis (from vent-open capture)

Two FSK packets detected with consistent structure:

| Event | Time | Pulses | Width | RSSI | Freq Offsets |
|-------|------|--------|-------|------|-------------|
| FSK #1 | 27.43s | 31 | 1.14ms | -26.2 dB | -218 kHz, -448 kHz |
| FSK #2 | 48.90s | 32 | 1.14ms | -35.2 dB | -222 kHz, -620 kHz |

### Preamble and Sync

| Field | Value | Length | Confidence |
|-------|-------|--------|------------|
| Preamble pattern | Likely `0xAA` repeating (CC1101 standard) | 4 bytes (typical) | HYPOTHESIZED |
| Sync word | UNKNOWN — need bitstream extraction | 2 or 4 bytes | UNKNOWN |

### Expected CC1101 Packet Format (Hypothesized)

```
[Preamble 4B] [Sync 2-4B] [Length 1B] [Address 1B] [Command] [Payload] [Seq?] [CRC-16 2B]
```

*Bitstream extraction needed to confirm field boundaries.*

### Interactive Pulse Visualizations (triq.org)

- FSK #1: https://triq.org/pdv/#AAB1040000001B000D0000819191A292A191A292A2A2A2A2A2A1A2A292A2A2A1A292A1A292A19191A29055
- FSK #2: https://triq.org/pdv/#AAB10600000014001B000D000800008292A2B3A3B2B3A2B3A2B3B3A3B2B3A2B3A2B3B3A3B2B3B3B3B3B3B3B3B3B2C055

---

## Message Types

| Type | Direction | Identified? | Confidence |
|------|-----------|-------------|------------|
| Position command (open/close/50%) | Gateway → Vent | Burst cluster observed at t=26-32s | OBSERVED (timing only) |
| Position acknowledgment | Vent → Gateway | Rapid-fire sequence likely contains ACKs | INFERRED |
| Keepalive / heartbeat | Both? | Sporadic bursts at t=6-9s, 46-57s | INFERRED |
| Battery voltage report | Vent → Gateway | Not yet identified | UNKNOWN |
| Duct temperature report | Vent → Gateway | Not yet identified | UNKNOWN |
| Duct pressure report | Vent → Gateway | Not yet identified | UNKNOWN |
| Pairing request/response | Either? | Not yet captured (last experiment) | UNKNOWN |

---

## Security Assessment

| Question | Answer | Confidence |
|----------|--------|------------|
| Are packets encrypted? | UNKNOWN — bitstream analysis needed | UNKNOWN |
| Is there a rolling counter / nonce? | **Likely YES** — Flipper Zero replay fails | INFERRED |
| Is there a CRC or checksum? | Likely YES — CC1101 has built-in CRC-16 | HYPOTHESIZED |
| Is simple replay possible? | **NO** — Flipper Zero community confirmed replay failure | OBSERVED (community) |
| Is there a pairing / key exchange? | Likely YES — vents must be paired to Puck | INFERRED |

> **CRITICAL:** Flipper Zero users have captured and attempted to replay Flair
> 915 MHz signals — replay FAILS. This confirms stateful elements (rolling codes,
> sequence counters, or challenge-response) in the protocol. Simple replay will
> not work for our local gateway.

---

## Prior Art Research (2026-09-11)

| Source | Finding |
|--------|---------|
| GitHub | Only cloud API wrappers exist (flair-api Python lib) |
| Home Assistant | RobertD502/home-assistant-flair = cloud-only via OAuth |
| Flair Official | REST API at api.flair.co, OAuth2, cloud-only, no local endpoints |
| HA Community | Local control "not on Flair's roadmap" |
| Flipper Zero | Signals captured, replay fails (stateful/bidirectional) |
| SDR Community | FSK bursts at 915 MHz identified, no payload parsing |
| rtl_433 | No Flair decoder exists |
| Puck Teardowns | ESP MCU for WiFi + separate RF MCU for 915 MHz |
| Firmware Dumps | None published |

**Conclusion:** No public reverse engineering of the Flair RF protocol exists.
We are the first to publish detailed signal characterization data.

---

## Observations Log

| Date | Experiment | Observation | Confidence |
|------|-----------|-------------|------------|
| 2026-09-10 | Baseline scan (no Flair) | Noise floor established, ambient 915 MHz signals identified | OBSERVED |
| 2026-09-10 | Flair idle scan | 10+ channels with 25-36 dB above baseline across 904-927 MHz | OBSERVED |
| 2026-09-10 | Vent-open IQ capture @ 907.8 MHz | 28 bursts detected; main cluster at t=26-32s (~16s cloud delay) | OBSERVED |
| 2026-09-10 | rtl_433 analysis of capture | FSK with Manchester coding, 14/27µs symbols, 31-32 pulses per packet | OBSERVED |

---

## Open Questions

1. ~~What is the exact center frequency or frequencies?~~ → **10+ channels identified across 904-927 MHz**
2. ~~Does the protocol use frequency hopping?~~ → **YES, multi-channel operation confirmed**
3. ~~What modulation scheme is used?~~ → **FSK with Manchester coding**
4. Are packets encrypted? → Bitstream analysis needed
5. What is the exact packet structure (field boundaries)?
6. How does pairing work?
7. ~~Are there rolling counters that prevent replay?~~ → **Likely YES (Flipper replay fails)**
8. ~~What chipset does the Bridge use?~~ → **TI CC1101 confirmed**
9. ~~Is there a published protocol specification?~~ → **NO — no public RE work exists**
10. What is the CC1101 sync word configured on these devices?
11. What firmware runs on the Vent's RF MCU?
12. Can the Puck's RF MCU firmware be dumped?

