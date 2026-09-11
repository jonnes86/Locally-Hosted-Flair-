#!/usr/bin/env python3
"""Compare two rtl_power scans to find frequencies with new/increased activity.

Subtracts the baseline max-hold spectrum from the active scan to identify
frequencies where the Flair system added energy.

Usage:
    python diff_scans.py captures/metadata/baseline_noflair.csv captures/metadata/scan_flair_idle.csv
"""

import argparse
import csv
import os
import sys

try:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("ERROR: Requires numpy and matplotlib. pip install numpy matplotlib")
    sys.exit(1)


def parse_rtl_power_csv(filepath):
    """Parse rtl_power CSV into a dict of {freq_hz: max_power_dB}."""
    max_hold = {}
    row_count = 0
    with open(filepath, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 7:
                continue
            try:
                hz_low = float(row[2])
                hz_step = float(row[4])
                powers = [float(x) for x in row[6:]]
                for i, p in enumerate(powers):
                    freq = hz_low + i * hz_step
                    if freq not in max_hold or p > max_hold[freq]:
                        max_hold[freq] = p
                row_count += 1
            except (ValueError, IndexError):
                continue
    return max_hold, row_count


def main():
    parser = argparse.ArgumentParser(description="Diff two rtl_power scans")
    parser.add_argument("baseline", help="Baseline CSV (no Flair)")
    parser.add_argument("active", help="Active CSV (Flair on)")
    parser.add_argument("--threshold", type=float, default=5.0,
                        help="Minimum dB increase to flag (default: 5)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output image path")
    parser.add_argument("--top", type=int, default=20,
                        help="Show top N frequency peaks (default: 20)")
    args = parser.parse_args()

    print(f"Parsing baseline: {args.baseline}")
    baseline, b_rows = parse_rtl_power_csv(args.baseline)
    print(f"  {b_rows} rows, {len(baseline)} frequency bins")

    print(f"Parsing active:   {args.active}")
    active, a_rows = parse_rtl_power_csv(args.active)
    print(f"  {a_rows} rows, {len(active)} frequency bins")

    # Find common frequencies
    common_freqs = sorted(set(baseline.keys()) & set(active.keys()))
    print(f"Common frequencies: {len(common_freqs)}")

    if not common_freqs:
        print("ERROR: No common frequencies between scans.")
        sys.exit(1)

    freqs = np.array(common_freqs)
    freqs_mhz = freqs / 1e6
    base_power = np.array([baseline[f] for f in common_freqs])
    act_power = np.array([active[f] for f in common_freqs])
    diff = act_power - base_power

    # Find peaks above threshold
    peaks = [(freqs_mhz[i], diff[i], act_power[i], base_power[i])
             for i in range(len(diff)) if diff[i] >= args.threshold]
    peaks.sort(key=lambda x: -x[1])  # Sort by largest diff

    print(f"\n{'='*72}")
    print(f"Frequencies with >= {args.threshold} dB increase (Flair candidates)")
    print(f"{'='*72}")

    if not peaks:
        print("  No frequencies exceeded the threshold.")
        print("  Try lowering --threshold or running a longer active scan.")
    else:
        print(f"  {'Freq (MHz)':<14} {'Diff (dB)':<12} {'Active (dB)':<14} {'Baseline (dB)':<14}")
        print(f"  {'-'*54}")
        for freq, d, act, base in peaks[:args.top]:
            marker = " <<<" if d >= 10 else ""
            print(f"  {freq:<14.4f} {d:<12.1f} {act:<14.1f} {base:<14.1f}{marker}")

        # Cluster nearby peaks (within 200 kHz) to identify channels
        print(f"\n{'='*72}")
        print("Candidate Flair channels (clustered within 200 kHz)")
        print(f"{'='*72}")

        clusters = []
        used = set()
        for freq, d, act, base in peaks:
            if freq in used:
                continue
            cluster = [(freq, d, act, base)]
            used.add(freq)
            for f2, d2, a2, b2 in peaks:
                if f2 not in used and abs(f2 - freq) <= 0.2:
                    cluster.append((f2, d2, a2, b2))
                    used.add(f2)
            clusters.append(cluster)

        for i, cluster in enumerate(clusters[:10]):
            center = np.mean([c[0] for c in cluster])
            max_diff = max(c[1] for c in cluster)
            bw = (max(c[0] for c in cluster) - min(c[0] for c in cluster)) * 1000  # kHz
            print(f"\n  Channel {i+1}: ~{center:.3f} MHz")
            print(f"    Peak increase: {max_diff:.1f} dB")
            print(f"    Occupied BW:   ~{bw:.0f} kHz (from {len(cluster)} bins)")
            print(f"    Bins: {', '.join(f'{c[0]:.4f}' for c in cluster[:8])}")

    # Plot
    output_path = args.output or os.path.splitext(args.active)[0] + "_diff.png"

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    axes[0].plot(freqs_mhz, base_power, linewidth=0.5, color='blue')
    axes[0].set_ylabel("Power (dB)")
    axes[0].set_title("Baseline (No Flair)")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(freqs_mhz, act_power, linewidth=0.5, color='green')
    axes[1].set_ylabel("Power (dB)")
    axes[1].set_title("Flair Active")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(freqs_mhz, diff, linewidth=0.5, color='red')
    axes[2].axhline(y=args.threshold, color='orange', linestyle='--',
                     linewidth=1, label=f'Threshold ({args.threshold} dB)')
    axes[2].set_xlabel("Frequency (MHz)")
    axes[2].set_ylabel("Difference (dB)")
    axes[2].set_title("Difference (Active - Baseline)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    # Mark peaks
    if peaks:
        peak_freqs = [p[0] for p in peaks[:args.top]]
        peak_diffs = [p[1] for p in peaks[:args.top]]
        axes[2].scatter(peak_freqs, peak_diffs, color='red', s=20, zorder=5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"\nDiff plot saved to {output_path}")


if __name__ == "__main__":
    main()
