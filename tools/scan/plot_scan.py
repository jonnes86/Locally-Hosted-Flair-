#!/usr/bin/env python3
"""Plot rtl_power scan CSV output as a heatmap/waterfall.

Reads the CSV output from rtl_power (via flair_scan.py) and produces
a spectrogram/waterfall plot and a max-hold spectrum plot.

Usage:
    python plot_scan.py captures/metadata/scan_idle.csv
    python plot_scan.py captures/metadata/scan_idle.csv --output scan_result.png
"""

import argparse
import csv
import sys
import os

try:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime
except ImportError:
    print("ERROR: This script requires numpy and matplotlib.")
    print("Install them with: pip install numpy matplotlib")
    sys.exit(1)


def parse_rtl_power_csv(filepath):
    """Parse rtl_power CSV output.

    Each row: date, time, hz_low, hz_high, hz_step, num_samples, dB values...
    """
    timestamps = []
    freq_starts = []
    freq_steps = []
    num_bins_list = []
    all_powers = []

    with open(filepath, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 7:
                continue
            try:
                dt = datetime.strptime(f"{row[0].strip()} {row[1].strip()}", "%Y-%m-%d %H:%M:%S")
                hz_low = float(row[2])
                hz_high = float(row[3])
                hz_step = float(row[4])
                num_samples = int(row[5])
                powers = [float(x) for x in row[6:]]

                timestamps.append(dt)
                freq_starts.append(hz_low)
                freq_steps.append(hz_step)
                num_bins_list.append(len(powers))
                all_powers.append((hz_low, hz_step, powers))
            except (ValueError, IndexError):
                continue

    return timestamps, all_powers


def main():
    parser = argparse.ArgumentParser(description="Plot rtl_power scan results")
    parser.add_argument("csvfile", help="Path to rtl_power CSV output")
    parser.add_argument("--output", "-o", default=None,
                        help="Output image path (default: <csvfile>.png)")
    parser.add_argument("--title", default="Flair RF Scan — 902-928 MHz",
                        help="Plot title")
    args = parser.parse_args()

    if not os.path.isfile(args.csvfile):
        print(f"ERROR: File not found: {args.csvfile}")
        sys.exit(1)

    output_path = args.output or f"{os.path.splitext(args.csvfile)[0]}.png"

    print(f"Parsing {args.csvfile}...")
    timestamps, all_powers = parse_rtl_power_csv(args.csvfile)

    if not all_powers:
        print("ERROR: No valid data found in CSV.")
        sys.exit(1)

    print(f"Found {len(timestamps)} sweep rows.")

    # Build a unified frequency axis from all rows
    # (rtl_power may output multiple rows per sweep for different sub-bands)
    all_freqs = set()
    for hz_low, hz_step, powers in all_powers:
        for i in range(len(powers)):
            all_freqs.add(hz_low + i * hz_step)
    freq_axis = sorted(all_freqs)
    freq_mhz = np.array(freq_axis) / 1e6

    # Build max-hold spectrum
    max_hold = {f: -999.0 for f in freq_axis}
    for hz_low, hz_step, powers in all_powers:
        for i, p in enumerate(powers):
            f = hz_low + i * hz_step
            if p > max_hold.get(f, -999.0):
                max_hold[f] = p

    max_spectrum = np.array([max_hold[f] for f in freq_axis])

    # Plot
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(freq_mhz, max_spectrum, linewidth=0.5, color='blue')
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Power (dB)")
    ax.set_title(args.title)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(freq_mhz.min(), freq_mhz.max())

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"Plot saved to {output_path}")


if __name__ == "__main__":
    main()
