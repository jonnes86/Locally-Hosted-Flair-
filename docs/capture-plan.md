# Flair RF Capture Plan — Phase 1: Receive-Only Discovery

**Version:** 1.0  
**Date:** 2026-09-10  
**Status:** Active  
**Phase:** 1 — Receive-only characterization  

## Objective

Systematically discover the RF characteristics of the Flair Smart Vent protocol in the 902–928 MHz US ISM band using a receive-only RTL-SDR V3. No transmissions, replays, pairing attempts, or device modifications.

## Equipment

| Item | Model | Role |
|------|-------|------|
| SDR Receiver | RTL-SDR.com Blog V3 (R820T2 + RTL2832U) | Receive-only wideband scanner |
| Antenna | 915 MHz antenna (details TBD) | ISM band reception |
| Flair Bridge/Puck | (serial TBD) | Gateway — issues commands to vents |
| Flair Smart Vent | Vent 01 (serial TBD) | Target device |
| Host PC | Windows 11 Pro x64, Python 3.14 | Capture and analysis |

## Physical Setup

1. Place the 915 MHz antenna on a stable surface with clear line of sight to both the Puck/Bridge and the vent.
2. Start with the Puck/Bridge and vent **3–6 feet** (1–2 m) from the antenna.
3. Do NOT place the antenna directly against either device — this causes receiver overload.
4. Keep other 915 MHz devices (LoRa, Zigbee 900, utility meters) away or powered down if possible.
5. Note any ambient 915 MHz sources that cannot be removed.
6. Record the physical layout with a diagram or photo for each session.

## Gain Settings

- **Automatic Gain Control (AGC): DISABLED** for all controlled captures.
- Start with **gain = 20 dB** (conservative).
- If signals are too weak, increase in 5 dB steps: 20 → 25 → 30 → 35 → 40.
- If signals clip or show flat-top distortion, decrease gain.
- Document the gain used for every single capture.
- A reference noise-floor capture at each gain setting should be taken before experiments begin.

## Step 0: Environment Verification

Before any Flair captures:

1. Run `rtl_test -t` to verify the RTL-SDR is detected and working.
2. Run a short `rtl_power` scan of 902–928 MHz with all Flair devices **powered off** to establish the RF noise floor and identify ambient signals.
3. Save this as a baseline: `YYYYMMDD-HHMMSS_baseline_noflair_scan.csv`
4. Document any persistent signals — these are NOT Flair.

## Step 1: Wideband Frequency Scan

**Goal:** Identify which frequencies within 902–928 MHz show activity correlated with Flair devices.

### Procedure

1. Power ON the Flair Puck/Bridge and vent(s). Wait 2 minutes for them to establish communication.
2. Run the wideband scan script:
   ```
   python tools/scan/flair_scan.py --start 902e6 --stop 928e6 --bin-width 25000 --interval 1 --duration 300 --gain 20 --output captures/metadata/scan_flair_idle
   ```
   This scans 902–928 MHz in 25 kHz bins, capturing 1-second sweeps for 5 minutes.
3. During the scan, **do not** issue any commands. Let the system idle.
4. Save output and metadata.
5. Repeat the scan while commanding Vent 01 to **open** via the Flair app at a precisely noted time.
6. Repeat for **50%** and **close**.
7. Compare the three scans against the baseline to identify frequencies with Flair-correlated activity.

### Expected Outcome

- One or more frequency channels will show bursts of energy correlated with Flair commands.
- If no single channel dominates, frequency hopping is likely.
- If hopping is present, note the pattern of channel usage and dwell times.

## Step 2: Narrow-Band Characterization

**Goal:** Capture raw IQ data at each discovered active frequency for detailed analysis.

### Procedure

For each active frequency identified in Step 1:

1. Center the RTL-SDR on that frequency.
2. Use a sample rate of **2.048 Msps** (or 2.4 Msps if needed for bandwidth).
3. Capture raw IQ during each controlled action (see Experiment Matrix below).
4. Use the capture script:
   ```
   python tools/capture/flair_capture.py --freq <center_hz> --rate 2048000 --gain 20 --duration 30 --label vent01-open --device vent01
   ```
5. Record exact timestamps of:
   - Capture start
   - App command issued
   - Any visible vent movement
   - Capture end

## Step 3: Experiment Matrix

Each experiment captures **one action at a time**. All other variables are held constant.

| # | Experiment | Flair App Action | Expected RF | Priority |
|---|-----------|-----------------|-------------|----------|
| 1 | Baseline idle | None — system powered on, no commands | Periodic keepalive/polling | HIGH |
| 2 | Vent 01 → Open (100%) | Command open via app | Command burst + ACK | HIGH |
| 3 | Vent 01 → 50% | Command 50% via app | Command burst + ACK | HIGH |
| 4 | Vent 01 → Close (0%) | Command close via app | Command burst + ACK | HIGH |
| 5 | Repeat: Vent 01 → Open | Same as #2 | Compare with #2 | HIGH |
| 6 | Repeat: Vent 01 → Close | Same as #4 | Compare with #4 | HIGH |
| 7 | Vent physical button | Press button on vent (if supported) | Vent-originated burst | MEDIUM |
| 8 | Vent battery removal | Remove battery from Vent 01 | Communication loss / alerts | MEDIUM |
| 9 | Vent battery reinsertion | Reinsert battery | Power-up sequence / re-registration | MEDIUM |
| 10 | Extended idle (30+ min) | None | Periodic polling interval measurement | MEDIUM |
| 11 | Pairing mode | Initiate pairing (ONLY after all above are captured) | Pairing handshake | LOW — LAST |

### Controls

- Only ONE action per capture.
- Wait at least 60 seconds of silence before and after the action.
- Use the same gain, sample rate, and antenna position for all captures in a session.
- Label captures with sequential experiment numbers.
- Cross-reference captures with the Flair app's command log if accessible.

## Step 4: Signal Analysis

**Goal:** Characterize the discovered signals.

For each captured signal:

1. Open in **Inspectrum** or **SDR++** to visually examine:
   - Burst duration
   - Occupied bandwidth
   - Modulation envelope
   - Repeat patterns
2. Open in **Universal Radio Hacker (URH)** to:
   - Auto-detect modulation (ASK/OOK, FSK, GFSK, etc.)
   - Measure symbol rate
   - Extract raw bitstreams
   - Compare bitstreams across captures of the same action
   - Compare bitstreams across different actions
3. Document findings in `docs/signal-inventory.md`.

## Step 5: Protocol Hypothesis

**Goal:** Develop initial hypotheses about the protocol structure.

Based on bitstream analysis:

1. Identify fixed preamble / sync words.
2. Look for device address fields (compare across devices).
3. Look for command fields (compare open vs. close vs. 50%).
4. Look for sequence counters (compare repeated identical commands).
5. Look for checksums or CRCs (trailing bytes that change with payload).
6. Assess whether encryption is present (high entropy in payload).
7. Document ALL findings in `docs/protocol-notes.md` with clear confidence levels.

## Decision Gate: Phase 1 → Phase 2

Before proceeding to Phase 2 (transceiver hardware selection), the following must be documented:

- [ ] Active frequency/frequencies identified
- [ ] Channel spacing measured (if multiple channels)
- [ ] Hopping behavior characterized (or confirmed absent)
- [ ] Modulation type determined
- [ ] Symbol rate measured
- [ ] Occupied bandwidth measured
- [ ] Burst timing characterized
- [ ] Preamble/sync word identified
- [ ] Basic packet structure hypothesized
- [ ] Encryption assessment completed
- [ ] Hardware requirements document (`docs/hardware-decisions.md`) drafted

Only then should transceiver hardware be selected and purchased.

## Safety and Legal Notes

- **Receive only.** No transmissions during Phase 1.
- All equipment is personally owned by the operator.
- Operations are within the US ISM band (47 CFR Part 15).
- No attempt to interfere with, jam, or disrupt any device.
- No attempt to access networks, servers, or accounts belonging to others.
