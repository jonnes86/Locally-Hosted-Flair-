#!/usr/bin/env python3
"""FSK demodulator for Flair Smart Vent captures.

Loads a CU8 IQ capture, finds bursts, demodulates FSK,
and extracts bitstreams/hex data from each packet.

Usage:
    python fsk_demod.py captures/raw/CAPTURE.cu8 --rate 2048000
"""

import argparse
import json
import os
import sys

try:
    import numpy as np
except ImportError:
    print("ERROR: Requires numpy. pip install numpy")
    sys.exit(1)


def load_cu8(filepath, sample_rate=2048000):
    """Load unsigned 8-bit IQ file as complex float array."""
    raw = np.fromfile(filepath, dtype=np.uint8)
    iq = raw.astype(np.float32) - 127.5
    iq = iq / 127.5
    samples = iq[0::2] + 1j * iq[1::2]
    return samples


def fm_demod(samples):
    """FM demodulate: compute instantaneous frequency via phase difference."""
    # Compute phase of each sample
    phase = np.angle(samples)
    # Unwrap phase
    phase_unwrap = np.unwrap(phase)
    # Instantaneous frequency = derivative of phase
    freq = np.diff(phase_unwrap)
    return freq


def find_bursts(freq, sample_rate, threshold_factor=3.0, min_samples=50):
    """Find signal bursts in FM-demodulated data using energy detection."""
    # Compute rolling energy (absolute instantaneous frequency)
    window = int(sample_rate * 0.0005)  # 0.5ms window
    if window < 10:
        window = 10

    # Use absolute value of frequency deviation
    abs_freq = np.abs(freq)

    # Compute noise floor from quietest 50% of signal
    sorted_vals = np.sort(abs_freq)
    noise_floor = np.mean(sorted_vals[:len(sorted_vals) // 2])
    threshold = noise_floor * threshold_factor

    # Smooth with moving average
    kernel = np.ones(window) / window
    smoothed = np.convolve(abs_freq, kernel, mode='same')

    # Find regions above threshold
    above = smoothed > threshold
    bursts = []
    in_burst = False
    start = 0

    for i in range(len(above)):
        if above[i] and not in_burst:
            start = i
            in_burst = True
        elif not above[i] and in_burst:
            if i - start >= min_samples:
                bursts.append((start, i))
            in_burst = False

    if in_burst and len(above) - start >= min_samples:
        bursts.append((start, len(above)))

    return bursts, threshold, noise_floor


def demod_burst(freq_data, samples_per_symbol=29):
    """Demodulate a single burst from FM-demodulated frequency data.

    Returns raw bits based on frequency polarity (above/below center).
    """
    # Center the frequency data
    center = np.median(freq_data)
    centered = freq_data - center

    # Determine bits by sign of frequency deviation
    # Positive freq = 1, Negative freq = 0 (or vice versa)
    n_symbols = len(centered) // samples_per_symbol

    bits = []
    for i in range(n_symbols):
        chunk = centered[i * samples_per_symbol:(i + 1) * samples_per_symbol]
        # Use majority vote within each symbol period
        if np.sum(chunk > 0) > len(chunk) // 2:
            bits.append(1)
        else:
            bits.append(0)

    return bits


def manchester_decode(bits):
    """Decode Manchester-encoded bitstream.

    Manchester: each data bit is encoded as a transition:
    - Data 1 = low-to-high (01)
    - Data 0 = high-to-low (10)
    (IEEE convention; some use inverted)

    Returns decoded bits, or None if not valid Manchester.
    """
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
            # Manchester violation - could be sync or error
            errors += 1
            decoded.append(0)  # Best guess

    return decoded, errors


def bits_to_hex(bits):
    """Convert bit array to hex string."""
    # Pad to multiple of 8
    while len(bits) % 8 != 0:
        bits.append(0)

    hex_str = ""
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        hex_str += f"{byte:02X} "

    return hex_str.strip()


def bits_to_string(bits):
    """Convert bit array to binary string."""
    return ''.join(str(b) for b in bits)


def try_multiple_sps(freq_data, sps_candidates):
    """Try multiple samples-per-symbol values and return best result."""
    results = []
    for sps in sps_candidates:
        bits = demod_burst(freq_data, samples_per_symbol=sps)
        if len(bits) < 4:
            continue

        # Try Manchester decode
        decoded, errors = manchester_decode(bits)
        error_rate = errors / max(len(bits) // 2, 1)

        # Score: prefer more bits with fewer errors
        score = len(decoded) * (1 - error_rate)

        results.append({
            'sps': sps,
            'raw_bits': bits,
            'decoded_bits': decoded,
            'manchester_errors': errors,
            'error_rate': error_rate,
            'score': score
        })

    if not results:
        return None

    # Return best scoring result
    return max(results, key=lambda x: x['score'])


def main():
    parser = argparse.ArgumentParser(description="Flair FSK Demodulator")
    parser.add_argument("iqfile", help="Path to CU8 IQ file")
    parser.add_argument("--rate", type=int, default=2048000,
                        help="Sample rate (default: 2048000)")
    parser.add_argument("--threshold", type=float, default=3.0,
                        help="Burst detection threshold factor (default: 3.0)")
    parser.add_argument("--max-bursts", type=int, default=30,
                        help="Maximum bursts to process (default: 30)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output JSON file for results")

    args = parser.parse_args()

    if not os.path.isfile(args.iqfile):
        print(f"ERROR: File not found: {args.iqfile}")
        sys.exit(1)

    file_size = os.path.getsize(args.iqfile)
    total_samples = file_size // 2
    total_seconds = total_samples / args.rate

    print(f"=== Flair FSK Demodulator ===")
    print(f"File: {args.iqfile}")
    print(f"Size: {file_size:,} bytes ({file_size / 1e6:.1f} MB)")
    print(f"Duration: {total_seconds:.1f} seconds")
    print()

    # Load IQ data
    print("Loading IQ data...")
    samples = load_cu8(args.iqfile, args.rate)
    print(f"Loaded {len(samples):,} complex samples")

    # FM demodulate
    print("FM demodulating...")
    freq = fm_demod(samples)

    # Find bursts
    print("Finding bursts...")
    bursts, threshold, noise_floor = find_bursts(freq, args.rate, args.threshold)
    print(f"Noise floor: {noise_floor:.6f}, Threshold: {threshold:.6f}")
    print(f"Found {len(bursts)} burst(s)")

    if not bursts:
        print("No bursts found. Try lowering --threshold.")
        sys.exit(0)

    # Candidate samples-per-symbol values
    # 14µs → 29 sps, 27µs → 55 sps at 2.048 Msps
    sps_candidates = [25, 27, 29, 31, 33, 50, 53, 55, 57, 60]

    print(f"\n{'='*80}")
    print(f"Demodulating bursts (trying {len(sps_candidates)} SPS candidates each)")
    print(f"{'='*80}")

    all_packets = []

    for idx, (start, end) in enumerate(bursts[:args.max_bursts]):
        duration_ms = (end - start) / args.rate * 1000
        time_s = start / args.rate

        if duration_ms < 0.5:
            continue  # Skip very short glitches

        burst_freq = freq[start:end]

        result = try_multiple_sps(burst_freq, sps_candidates)
        if result is None:
            continue

        raw_bits = result['raw_bits']
        decoded_bits = result['decoded_bits']
        sps = result['sps']
        errors = result['manchester_errors']

        raw_hex = bits_to_hex(list(raw_bits))
        decoded_hex = bits_to_hex(list(decoded_bits))

        print(f"\n--- Burst {idx + 1} @ t={time_s:.3f}s ({duration_ms:.1f}ms) "
              f"[SPS={sps}] ---")
        print(f"  Raw bits ({len(raw_bits)}): {bits_to_string(raw_bits[:80])}"
              f"{'...' if len(raw_bits) > 80 else ''}")
        print(f"  Raw hex:     {raw_hex[:80]}{'...' if len(raw_hex) > 80 else ''}")

        if errors / max(len(raw_bits) // 2, 1) < 0.3:
            print(f"  Manchester ({len(decoded_bits)} bits, {errors} errors): "
                  f"{bits_to_string(decoded_bits[:60])}"
                  f"{'...' if len(decoded_bits) > 60 else ''}")
            print(f"  Decoded hex: {decoded_hex[:80]}"
                  f"{'...' if len(decoded_hex) > 80 else ''}")
        else:
            print(f"  Manchester decode: too many errors ({errors}/"
                  f"{len(raw_bits)//2}) — may not be Manchester encoded")

        packet = {
            'burst_index': idx + 1,
            'time_seconds': round(time_s, 4),
            'duration_ms': round(duration_ms, 2),
            'samples_per_symbol': sps,
            'raw_bit_count': len(raw_bits),
            'raw_hex': raw_hex,
            'raw_bits': bits_to_string(raw_bits),
            'manchester_errors': errors,
            'decoded_bit_count': len(decoded_bits),
            'decoded_hex': decoded_hex,
            'decoded_bits': bits_to_string(decoded_bits)
        }
        all_packets.append(packet)

    # Summary
    print(f"\n{'='*80}")
    print(f"Summary: {len(all_packets)} packets demodulated from {len(bursts)} bursts")
    print(f"{'='*80}")

    if len(all_packets) >= 2:
        print("\nPacket comparison (looking for fixed vs. changing bytes):")
        hex_lists = [p['decoded_hex'].split() for p in all_packets
                     if len(p['decoded_hex'].split()) >= 4]

        if len(hex_lists) >= 2:
            min_len = min(len(h) for h in hex_lists)
            print(f"\n  Byte position analysis ({min_len} bytes compared "
                  f"across {len(hex_lists)} packets):")
            print(f"  {'Pos':<5} {'Values across packets':<60} {'Status'}")
            print(f"  {'-'*75}")

            for pos in range(min_len):
                values = [h[pos] for h in hex_lists if pos < len(h)]
                unique = set(values)
                status = "FIXED" if len(unique) == 1 else f"VARIES ({len(unique)} values)"
                vals_str = ', '.join(values[:8])
                print(f"  {pos:<5} {vals_str:<60} {status}")

    # Save results
    if args.output is None:
        base = os.path.splitext(os.path.basename(args.iqfile))[0]
        args.output = os.path.join("captures", "analysis", base, "packets.json")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({
            'source_file': os.path.basename(args.iqfile),
            'sample_rate': args.rate,
            'total_seconds': float(total_seconds),
            'burst_count': len(bursts),
            'packet_count': len(all_packets),
            'packets': all_packets
        }, f, indent=2)
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
