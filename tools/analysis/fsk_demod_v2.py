#!/usr/bin/env python3
"""Targeted FSK demodulator for Flair Smart Vent captures.

Improvement over fsk_demod.py: applies bandpass filtering at known
signal offset frequencies before demodulation, dramatically improving SNR.

Based on rtl_433 findings:
- Signal offsets: -218 kHz and -448 kHz from center (two FSK tones)
- Signal center: ~333 kHz below SDR center frequency
- FSK deviation: ~115 kHz

Usage:
    python fsk_demod_v2.py captures/raw/CAPTURE.cu8
"""

import argparse
import json
import os
import sys

try:
    import numpy as np
    from scipy import signal as scipy_signal
    HAS_SCIPY = True
except ImportError:
    try:
        import numpy as np
        HAS_SCIPY = False
    except ImportError:
        print("ERROR: Requires numpy. pip install numpy")
        sys.exit(1)


def load_cu8(filepath):
    """Load unsigned 8-bit IQ file as complex float array."""
    raw = np.fromfile(filepath, dtype=np.uint8)
    iq = raw.astype(np.float32) - 127.5
    iq /= 127.5
    return iq[0::2] + 1j * iq[1::2]


def bandpass_filter(samples, sample_rate, center_offset_hz, bandwidth_hz):
    """Frequency-shift and lowpass to isolate a narrow channel."""
    # Shift the desired signal to baseband
    n = np.arange(len(samples))
    shift = np.exp(-1j * 2 * np.pi * center_offset_hz / sample_rate * n)
    shifted = samples * shift

    # Lowpass filter to the signal bandwidth
    cutoff = bandwidth_hz / 2
    nyq = sample_rate / 2

    if HAS_SCIPY:
        # Use scipy for better filter
        order = min(101, len(shifted) // 10)
        if order % 2 == 0:
            order += 1
        taps = scipy_signal.firwin(order, cutoff / nyq)
        filtered = scipy_signal.lfilter(taps, 1.0, shifted)
    else:
        # Simple moving average as fallback
        window = max(3, int(sample_rate / bandwidth_hz))
        kernel = np.ones(window) / window
        filtered = np.convolve(shifted, kernel, mode='same')

    return filtered


def fm_demod(samples):
    """FM demodulate via instantaneous frequency."""
    phase = np.unwrap(np.angle(samples))
    return np.diff(phase)


def compute_envelope(samples, window=512):
    """Compute signal envelope for burst detection."""
    mag = np.abs(samples)
    kernel = np.ones(window) / window
    return np.convolve(mag, kernel, mode='same')


def find_bursts(envelope, sample_rate, threshold_db=10, min_duration_ms=0.3,
                merge_gap_ms=2.0):
    """Find bursts using envelope with dB threshold above noise floor."""
    # Estimate noise floor from bottom 25th percentile
    sorted_env = np.sort(envelope)
    noise_floor = np.mean(sorted_env[:len(sorted_env) // 4])
    if noise_floor < 1e-10:
        noise_floor = 1e-10

    threshold_linear = noise_floor * (10 ** (threshold_db / 20))

    above = envelope > threshold_linear
    min_samples = int(min_duration_ms * sample_rate / 1000)
    merge_samples = int(merge_gap_ms * sample_rate / 1000)

    bursts = []
    in_burst = False
    start = 0

    for i in range(len(above)):
        if above[i] and not in_burst:
            start = i
            in_burst = True
        elif not above[i] and in_burst:
            # Check if gap is small enough to merge
            gap_end = min(i + merge_samples, len(above))
            if np.any(above[i:gap_end]):
                continue  # Stay in burst
            if i - start >= min_samples:
                bursts.append((start, i))
            in_burst = False

    if in_burst and len(above) - start >= min_samples:
        bursts.append((start, len(above)))

    return bursts, float(noise_floor), float(threshold_linear)


def extract_bits_fsk(freq_data, samples_per_symbol):
    """Extract bits from FM-demodulated FSK data."""
    center = np.median(freq_data)
    centered = freq_data - center

    n_symbols = len(centered) // samples_per_symbol
    bits = []
    confidences = []

    for i in range(n_symbols):
        chunk = centered[i * samples_per_symbol:(i + 1) * samples_per_symbol]
        # Use middle 60% of symbol for more reliable detection
        margin = len(chunk) // 5
        if margin > 0:
            chunk = chunk[margin:-margin]
        mean_val = np.mean(chunk)
        bits.append(1 if mean_val > 0 else 0)
        # Confidence: how far from zero
        confidences.append(abs(mean_val) / (np.std(chunk) + 1e-10))

    return bits, confidences


def manchester_decode(bits):
    """Decode Manchester (IEEE 802.3 convention): 10=1, 01=0."""
    if len(bits) % 2 != 0:
        bits = bits[:-1]

    decoded = []
    errors = 0
    for i in range(0, len(bits), 2):
        pair = (bits[i], bits[i + 1])
        if pair == (1, 0):
            decoded.append(1)
        elif pair == (0, 1):
            decoded.append(0)
        else:
            errors += 1
            decoded.append(bits[i])  # Best guess

    return decoded, errors


def manchester_decode_inv(bits):
    """Decode Manchester (inverted convention): 01=1, 10=0."""
    if len(bits) % 2 != 0:
        bits = bits[:-1]

    decoded = []
    errors = 0
    for i in range(0, len(bits), 2):
        pair = (bits[i], bits[i + 1])
        if pair == (0, 1):
            decoded.append(1)
        elif pair == (1, 0):
            decoded.append(0)
        else:
            errors += 1
            decoded.append(bits[i])

    return decoded, errors


def bits_to_hex(bits):
    """Convert bit list to hex string."""
    while len(bits) % 8 != 0:
        bits = bits + [0]
    hex_str = ""
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        hex_str += f"{byte:02X} "
    return hex_str.strip()


def find_preamble(bits, pattern=[1,0,1,0,1,0,1,0]):
    """Find preamble pattern (0xAA = 10101010) in bitstream."""
    pat_len = len(pattern)
    for i in range(len(bits) - pat_len):
        if bits[i:i+pat_len] == pattern:
            return i
    # Try inverted
    inv_pattern = [1-b for b in pattern]
    for i in range(len(bits) - pat_len):
        if bits[i:i+pat_len] == inv_pattern:
            return i
    return -1


def analyze_burst(freq_data, sample_rate, burst_idx, time_s, duration_ms):
    """Analyze a single burst with multiple SPS and decoding strategies."""
    # Try multiple samples-per-symbol values
    sps_candidates = [25, 27, 29, 31, 33, 50, 53, 55, 57]

    best = None
    best_score = -1

    for sps in sps_candidates:
        bits, confidences = extract_bits_fsk(freq_data, sps)
        if len(bits) < 8:
            continue

        avg_confidence = np.mean(confidences) if confidences else 0

        # Try both Manchester conventions
        for convention, decode_fn in [("IEEE", manchester_decode),
                                       ("INV", manchester_decode_inv)]:
            decoded, errors = decode_fn(list(bits))
            if len(decoded) < 4:
                continue

            error_rate = errors / max(len(bits) // 2, 1)

            # Also try without Manchester (raw NRZ)
            score = len(decoded) * (1 - error_rate) * avg_confidence

            if score > best_score:
                best_score = score
                best = {
                    'sps': sps,
                    'convention': convention,
                    'raw_bits': list(bits),
                    'decoded_bits': list(decoded),
                    'errors': errors,
                    'error_rate': error_rate,
                    'confidence': float(avg_confidence),
                    'score': float(score)
                }

        # Also try NRZ (no Manchester)
        nrz_hex = bits_to_hex(list(bits))
        nrz_score = len(bits) * avg_confidence * 0.5  # Lower weight for NRZ
        if nrz_score > best_score:
            best_score = nrz_score
            best = {
                'sps': sps,
                'convention': 'NRZ',
                'raw_bits': list(bits),
                'decoded_bits': list(bits),
                'errors': 0,
                'error_rate': 0,
                'confidence': float(avg_confidence),
                'score': float(nrz_score)
            }

    return best


def main():
    parser = argparse.ArgumentParser(description="Flair FSK Demodulator v2")
    parser.add_argument("iqfile", help="Path to CU8 IQ file")
    parser.add_argument("--rate", type=int, default=2048000)
    parser.add_argument("--signal-offset", type=float, default=-333000,
                        help="Signal center offset from SDR center in Hz "
                             "(default: -333000 based on rtl_433 findings)")
    parser.add_argument("--signal-bw", type=float, default=300000,
                        help="Signal bandwidth in Hz (default: 300000)")
    parser.add_argument("--threshold-db", type=float, default=8,
                        help="Burst detection threshold in dB above noise")
    parser.add_argument("--max-bursts", type=int, default=30)
    parser.add_argument("--scan-offsets", action="store_true",
                        help="Scan multiple frequency offsets to find signals")
    parser.add_argument("--output", "-o", type=str, default=None)

    args = parser.parse_args()

    if not os.path.isfile(args.iqfile):
        print(f"ERROR: File not found: {args.iqfile}")
        sys.exit(1)

    file_size = os.path.getsize(args.iqfile)
    total_samples = file_size // 2
    total_seconds = total_samples / args.rate

    print(f"=== Flair FSK Demodulator v2 ===")
    print(f"File: {args.iqfile}")
    print(f"Size: {file_size:,} bytes ({file_size/1e6:.1f} MB)")
    print(f"Duration: {total_seconds:.1f}s | Rate: {args.rate/1e6:.3f} Msps")
    if HAS_SCIPY:
        print(f"scipy available: YES (good filtering)")
    else:
        print(f"scipy available: NO (install for better results: pip install scipy)")
    print()

    # Load
    print("Loading IQ data...")
    samples = load_cu8(args.iqfile)
    print(f"Loaded {len(samples):,} complex samples")

    # Determine frequency offsets to scan
    if args.scan_offsets:
        offsets = [-600000, -450000, -333000, -218000, -100000,
                   0, 100000, 200000, 333000, 450000, 600000]
        print(f"\nScanning {len(offsets)} frequency offsets...")
    else:
        offsets = [args.signal_offset]

    all_results = []

    for offset in offsets:
        if len(offsets) > 1:
            print(f"\n{'='*60}")
            print(f"Scanning offset: {offset/1000:+.0f} kHz "
                  f"(= {(907800000+offset)/1e6:.3f} MHz)")
            print(f"{'='*60}")

        # Bandpass filter
        print(f"Filtering: offset={offset/1000:+.0f} kHz, BW={args.signal_bw/1000:.0f} kHz...")
        filtered = bandpass_filter(samples, args.rate, offset, args.signal_bw)

        # FM demodulate the filtered signal
        print("FM demodulating filtered signal...")
        freq = fm_demod(filtered)

        # Compute envelope for burst detection
        envelope = compute_envelope(filtered, window=256)

        # Find bursts
        bursts, noise_floor, threshold = find_bursts(
            envelope[:-1], args.rate, args.threshold_db)
        print(f"Found {len(bursts)} burst(s) "
              f"(noise={noise_floor:.6f}, thresh={threshold:.6f})")

        if not bursts:
            continue

        for idx, (start, end) in enumerate(bursts[:args.max_bursts]):
            duration_ms = (end - start) / args.rate * 1000
            time_s = start / args.rate

            if duration_ms < 0.3:
                continue

            burst_freq = freq[start:end]
            result = analyze_burst(burst_freq, args.rate, idx, time_s,
                                   duration_ms)
            if result is None:
                continue

            raw_hex = bits_to_hex(list(result['raw_bits']))
            decoded_hex = bits_to_hex(list(result['decoded_bits']))

            # Look for preamble
            preamble_pos = find_preamble(result['raw_bits'])

            print(f"\n  Burst {idx+1} @ t={time_s:.3f}s ({duration_ms:.1f}ms) "
                  f"[SPS={result['sps']}, {result['convention']}, "
                  f"conf={result['confidence']:.1f}]")
            print(f"    Raw ({len(result['raw_bits'])}b): {raw_hex}")
            if result['convention'] != 'NRZ':
                print(f"    Dec ({len(result['decoded_bits'])}b, "
                      f"{result['errors']}err): {decoded_hex}")
            if preamble_pos >= 0:
                print(f"    *** Preamble (0xAA) found at bit {preamble_pos} ***")

            packet = {
                'offset_hz': offset,
                'freq_mhz': round((907800000 + offset) / 1e6, 3),
                'burst_index': idx + 1,
                'time_seconds': round(time_s, 4),
                'duration_ms': round(duration_ms, 2),
                'sps': result['sps'],
                'convention': result['convention'],
                'confidence': round(result['confidence'], 3),
                'raw_bit_count': len(result['raw_bits']),
                'raw_hex': raw_hex,
                'decoded_bit_count': len(result['decoded_bits']),
                'decoded_hex': decoded_hex,
                'manchester_errors': result['errors'],
                'error_rate': round(result['error_rate'], 3),
                'preamble_position': preamble_pos
            }
            all_results.append(packet)

    # Summary
    print(f"\n{'='*70}")
    print(f"TOTAL: {len(all_results)} packets across {len(offsets)} offset(s)")
    print(f"{'='*70}")

    # Show best packets by confidence
    if all_results:
        sorted_packets = sorted(all_results,
                                key=lambda x: x['confidence'], reverse=True)
        print(f"\nTop packets by confidence:")
        for i, p in enumerate(sorted_packets[:10]):
            print(f"  {i+1}. t={p['time_seconds']:.3f}s "
                  f"offset={p['offset_hz']/1000:+.0f}kHz "
                  f"conf={p['confidence']:.1f} "
                  f"[{p['convention']} SPS={p['sps']}] "
                  f"-> {p['decoded_hex'][:50]}")

    # Save
    if args.output is None:
        base = os.path.splitext(os.path.basename(args.iqfile))[0]
        args.output = os.path.join("captures", "analysis", base,
                                   "packets_v2.json")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({
            'source_file': os.path.basename(args.iqfile),
            'sample_rate': args.rate,
            'offsets_scanned': offsets,
            'packet_count': len(all_results),
            'packets': all_results
        }, f, indent=2)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
