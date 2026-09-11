#!/usr/bin/env python3
"""Analyze raw IQ captures for Flair RF bursts.

Loads a CU8 (unsigned 8-bit IQ) capture and:
1. Computes signal amplitude envelope
2. Detects bursts above a noise threshold
3. Measures burst timing, duration, and spacing
4. Generates time-domain and spectrogram plots around bursts
5. Optionally extracts burst segments for further analysis

Usage:
    python burst_detect.py captures/raw/CAPTURE.cu8 --rate 2048000 --action-time 10
"""

import argparse
import json
import os
import sys

try:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
except ImportError:
    print("ERROR: Requires numpy and matplotlib. pip install numpy matplotlib")
    sys.exit(1)


def load_cu8(filepath, max_seconds=None, sample_rate=2048000):
    """Load unsigned 8-bit IQ file as complex float array."""
    if max_seconds:
        max_bytes = int(max_seconds * sample_rate * 2)
    else:
        max_bytes = -1

    raw = np.fromfile(filepath, dtype=np.uint8, count=max_bytes)
    # Convert to float complex: I and Q are interleaved unsigned bytes
    iq = raw.astype(np.float32) - 127.5
    iq = iq / 127.5  # Normalize to [-1, 1]
    samples = iq[0::2] + 1j * iq[1::2]
    return samples


def compute_envelope(samples, decimation=1024):
    """Compute amplitude envelope with decimation for overview."""
    mag = np.abs(samples)
    # Reshape and take max per block for envelope
    n = len(mag) // decimation * decimation
    mag = mag[:n].reshape(-1, decimation)
    envelope = mag.max(axis=1)
    avg = mag.mean(axis=1)
    return envelope, avg


def detect_bursts(envelope, threshold, min_gap_blocks=5):
    """Find contiguous regions above threshold.

    Returns list of (start_block, end_block, peak_amplitude).
    """
    above = envelope > threshold
    bursts = []
    in_burst = False
    start = 0
    gap_count = 0

    for i in range(len(above)):
        if above[i]:
            if not in_burst:
                start = i
                in_burst = True
            gap_count = 0
        else:
            if in_burst:
                gap_count += 1
                if gap_count >= min_gap_blocks:
                    end = i - gap_count
                    peak = float(envelope[start:end+1].max())
                    bursts.append((start, end, peak))
                    in_burst = False
                    gap_count = 0

    if in_burst:
        end = len(envelope) - 1
        peak = float(envelope[start:end+1].max())
        bursts.append((start, end, peak))

    return bursts


def spectrogram_burst(samples, burst_start_sample, burst_end_sample, sample_rate, context_samples=0):
    """Compute spectrogram around a burst."""
    start = max(0, burst_start_sample - context_samples)
    end = min(len(samples), burst_end_sample + context_samples)
    segment = samples[start:end]

    fft_size = 1024
    overlap = fft_size // 2
    step = fft_size - overlap

    n_windows = (len(segment) - fft_size) // step
    if n_windows <= 0:
        return None, None, None

    spec = np.zeros((n_windows, fft_size))
    window = np.hanning(fft_size)

    for i in range(n_windows):
        s = i * step
        chunk = segment[s:s+fft_size] * window
        fft = np.fft.fftshift(np.fft.fft(chunk))
        spec[i] = 20 * np.log10(np.abs(fft) + 1e-10)

    freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, 1/sample_rate))
    times = np.arange(n_windows) * step / sample_rate + start / sample_rate

    return spec, freqs, times


def main():
    parser = argparse.ArgumentParser(description="Flair RF Burst Detector")
    parser.add_argument("iqfile", help="Path to CU8 IQ file")
    parser.add_argument("--rate", type=int, default=2048000,
                        help="Sample rate (default: 2048000)")
    parser.add_argument("--action-time", type=float, default=None,
                        help="Seconds after start when action was performed")
    parser.add_argument("--threshold-db", type=float, default=6.0,
                        help="Burst detection threshold above noise floor in dB (default: 6)")
    parser.add_argument("--max-seconds", type=float, default=None,
                        help="Only load first N seconds (saves RAM)")
    parser.add_argument("--decimation", type=int, default=1024,
                        help="Decimation factor for envelope (default: 1024)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory for plots")
    parser.add_argument("--burst-spectrograms", type=int, default=5,
                        help="Number of burst spectrograms to generate (default: 5)")

    args = parser.parse_args()

    if not os.path.isfile(args.iqfile):
        print(f"ERROR: File not found: {args.iqfile}")
        sys.exit(1)

    file_size = os.path.getsize(args.iqfile)
    total_samples = file_size // 2  # CU8 = 2 bytes per complex sample
    total_seconds = total_samples / args.rate

    print(f"=== Flair RF Burst Detector ===")
    print(f"File: {args.iqfile}")
    print(f"Size: {file_size:,} bytes ({file_size/1e6:.1f} MB)")
    print(f"Sample rate: {args.rate/1e6:.3f} Msps")
    print(f"Duration: {total_seconds:.1f} seconds")
    print(f"Decimation: {args.decimation} (envelope resolution: {args.decimation/args.rate*1000:.2f} ms)")
    print()

    # Output directory
    if args.output_dir is None:
        base = os.path.splitext(os.path.basename(args.iqfile))[0]
        args.output_dir = os.path.join("captures", "analysis", base)
    os.makedirs(args.output_dir, exist_ok=True)

    # Load data
    load_sec = args.max_seconds or total_seconds
    print(f"Loading {load_sec:.1f} seconds of IQ data...")
    samples = load_cu8(args.iqfile, max_seconds=args.max_seconds, sample_rate=args.rate)
    print(f"Loaded {len(samples):,} complex samples")

    # Compute envelope
    print("Computing amplitude envelope...")
    envelope, avg_envelope = compute_envelope(samples, args.decimation)
    time_axis = np.arange(len(envelope)) * args.decimation / args.rate

    # Determine noise floor and threshold
    noise_floor = np.median(avg_envelope)
    noise_floor_db = 20 * np.log10(noise_floor + 1e-10)
    threshold_linear = noise_floor * (10 ** (args.threshold_db / 20))

    print(f"Noise floor (median): {noise_floor:.6f} ({noise_floor_db:.1f} dB)")
    print(f"Detection threshold: {args.threshold_db} dB above noise = {20*np.log10(threshold_linear+1e-10):.1f} dB")

    # Detect bursts
    print("Detecting bursts...")
    bursts = detect_bursts(envelope, threshold_linear, min_gap_blocks=3)

    print(f"\nFound {len(bursts)} burst(s)")
    print()

    if bursts:
        print(f"{'#':<4} {'Start (s)':<12} {'End (s)':<12} {'Duration (ms)':<16} {'Peak Amp':<12} {'Relative to action'}")
        print("-" * 80)

        burst_info = []
        for i, (start_blk, end_blk, peak) in enumerate(bursts):
            start_sec = start_blk * args.decimation / args.rate
            end_sec = end_blk * args.decimation / args.rate
            duration_ms = (end_sec - start_sec) * 1000
            peak_db = 20 * np.log10(peak + 1e-10)

            action_rel = ""
            if args.action_time is not None:
                delta = start_sec - args.action_time
                if abs(delta) < 2:
                    action_rel = f"<<< {delta:+.2f}s from action"
                else:
                    action_rel = f"{delta:+.1f}s"

            print(f"{i+1:<4} {start_sec:<12.3f} {end_sec:<12.3f} {duration_ms:<16.1f} {peak_db:<12.1f} {action_rel}")

            burst_info.append({
                "burst_number": i + 1,
                "start_seconds": round(start_sec, 4),
                "end_seconds": round(end_sec, 4),
                "duration_ms": round(duration_ms, 2),
                "peak_amplitude_db": round(peak_db, 1),
                "start_sample": int(start_blk * args.decimation),
                "end_sample": int(end_blk * args.decimation)
            })

        # Burst timing statistics
        if len(bursts) >= 2:
            intervals = []
            for i in range(1, len(bursts)):
                prev_end = bursts[i-1][1] * args.decimation / args.rate
                curr_start = bursts[i][0] * args.decimation / args.rate
                intervals.append(curr_start - prev_end)

            print(f"\nBurst timing statistics:")
            print(f"  Inter-burst gaps: min={min(intervals)*1000:.1f} ms, max={max(intervals)*1000:.1f} ms, median={np.median(intervals)*1000:.1f} ms")
            if len(intervals) >= 3:
                print(f"  Mean gap: {np.mean(intervals)*1000:.1f} ms, std: {np.std(intervals)*1000:.1f} ms")

        # Save burst info
        burst_json = os.path.join(args.output_dir, "bursts.json")
        with open(burst_json, "w") as f:
            json.dump({
                "source_file": os.path.basename(args.iqfile),
                "sample_rate": args.rate,
                "total_seconds": float(total_seconds),
                "noise_floor_db": float(round(noise_floor_db, 1)),
                "threshold_db": float(args.threshold_db),
                "action_time_seconds": args.action_time,
                "burst_count": len(bursts),
                "bursts": burst_info
            }, f, indent=2)
        print(f"\nBurst data saved to {burst_json}")

    # --- Plot 1: Full timeline ---
    print("\nGenerating timeline plot...")
    fig, ax = plt.subplots(figsize=(16, 4))
    ax.plot(time_axis, 20 * np.log10(envelope + 1e-10), linewidth=0.3, color='blue', label='Peak envelope')
    ax.axhline(y=20*np.log10(threshold_linear+1e-10), color='red', linestyle='--', linewidth=0.8, label='Threshold')

    if args.action_time is not None:
        ax.axvline(x=args.action_time, color='green', linestyle='-', linewidth=1.5,
                    label=f'Action at {args.action_time}s', alpha=0.8)

    # Mark bursts
    for i, (start_blk, end_blk, peak) in enumerate(bursts):
        start_sec = start_blk * args.decimation / args.rate
        end_sec = end_blk * args.decimation / args.rate
        ax.axvspan(start_sec, end_sec, alpha=0.2, color='red')

    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Amplitude (dB)")
    ax.set_title(f"RF Burst Timeline — {os.path.basename(args.iqfile)}")
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)

    timeline_path = os.path.join(args.output_dir, "timeline.png")
    plt.tight_layout()
    plt.savefig(timeline_path, dpi=150)
    plt.close()
    print(f"Timeline saved to {timeline_path}")

    # --- Plot 2: Spectrograms of individual bursts ---
    if bursts and args.burst_spectrograms > 0:
        n_specs = min(args.burst_spectrograms, len(bursts))
        # Prioritize bursts near the action time
        if args.action_time is not None:
            sorted_bursts = sorted(enumerate(bursts),
                                    key=lambda x: abs(x[1][0] * args.decimation / args.rate - args.action_time))
        else:
            sorted_bursts = list(enumerate(bursts))

        for idx, (burst_idx, (start_blk, end_blk, peak)) in enumerate(sorted_bursts[:n_specs]):
            start_sample = start_blk * args.decimation
            end_sample = end_blk * args.decimation
            context = args.rate // 10  # 100ms context

            print(f"Generating spectrogram for burst {burst_idx+1}...")
            spec, freqs, times = spectrogram_burst(samples, start_sample, end_sample, args.rate, context)
            if spec is None:
                continue

            fig, ax = plt.subplots(figsize=(12, 5))
            im = ax.pcolormesh(times * 1000,  # ms
                               freqs / 1000,   # kHz
                               spec.T,
                               shading='auto', cmap='viridis',
                               vmin=np.percentile(spec, 5),
                               vmax=np.percentile(spec, 99))
            ax.set_xlabel("Time (ms from capture start)")
            ax.set_ylabel("Frequency offset (kHz)")
            ax.set_title(f"Burst {burst_idx+1} — t={start_blk*args.decimation/args.rate:.3f}s")
            plt.colorbar(im, ax=ax, label="Power (dB)")

            spec_path = os.path.join(args.output_dir, f"burst_{burst_idx+1:03d}_spectrogram.png")
            plt.tight_layout()
            plt.savefig(spec_path, dpi=150)
            plt.close()
            print(f"  Saved to {spec_path}")

    print(f"\nAll outputs saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
