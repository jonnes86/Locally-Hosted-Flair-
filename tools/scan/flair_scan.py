#!/usr/bin/env python3
"""Flair RF Scanner — Wideband sweep of 902-928 MHz using rtl_power.

Scans the US ISM band in configurable bins to identify frequencies
with Flair-correlated activity. Wraps rtl_power with proper metadata
generation and output organization.

Usage:
    python flair_scan.py --start 902e6 --stop 928e6 --bin-width 25000 \
        --interval 1 --duration 300 --gain 20 --output captures/metadata/scan_idle

The RTL-SDR V3 has ~2.4 MHz instantaneous bandwidth, so rtl_power
automatically steps across the full range in successive sweeps.

Output:
    - CSV file with rtl_power output
    - JSON metadata file
    - SHA-256 hash file
"""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import shutil


def find_rtl_power():
    """Locate rtl_power executable."""
    rtl_power = shutil.which("rtl_power")
    if rtl_power:
        return rtl_power
    # Check common Windows install locations
    common_paths = [
        os.path.join(os.environ.get("ProgramFiles", ""), "rtl-sdr", "rtl_power.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "rtl-sdr", "rtl_power.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""), "rtl-sdr", "rtl_power.exe"),
    ]
    for p in common_paths:
        if os.path.isfile(p):
            return p
    return None


def sha256_file(filepath):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_metadata(args, csv_path, start_time, end_time, sha256):
    """Generate capture metadata JSON."""
    return {
        "capture_id": os.path.basename(args.output),
        "type": "wideband_scan",
        "version": "1.0",
        "date_utc": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date_local": datetime.datetime.now().astimezone().isoformat(),
        "phase": "1",
        "equipment": {
            "sdr": {
                "model": "RTL-SDR.com Blog V3",
                "chipset": "R820T2 + RTL2832U"
            }
        },
        "rf_parameters": {
            "start_frequency_hz": int(args.start),
            "stop_frequency_hz": int(args.stop),
            "bin_width_hz": int(args.bin_width),
            "gain_db": args.gain,
            "agc": False,
            "ppm_correction": args.ppm
        },
        "scan": {
            "interval_seconds": args.interval,
            "total_duration_seconds": args.duration,
            "csv_filename": os.path.basename(csv_path),
            "csv_sha256": sha256,
            "csv_filesize_bytes": os.path.getsize(csv_path)
        },
        "capture_start_utc": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_end_utc": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notes": args.notes or ""
    }


def main():
    parser = argparse.ArgumentParser(
        description="Flair RF Scanner — Wideband sweep of ISM band using rtl_power"
    )
    parser.add_argument("--start", type=float, default=902e6,
                        help="Start frequency in Hz (default: 902 MHz)")
    parser.add_argument("--stop", type=float, default=928e6,
                        help="Stop frequency in Hz (default: 928 MHz)")
    parser.add_argument("--bin-width", type=int, default=25000,
                        help="Bin width in Hz (default: 25000)")
    parser.add_argument("--interval", type=int, default=1,
                        help="Sweep interval in seconds (default: 1)")
    parser.add_argument("--duration", type=int, default=300,
                        help="Total scan duration in seconds (default: 300)")
    parser.add_argument("--gain", type=float, default=20.0,
                        help="Tuner gain in dB (default: 20.0). AGC is disabled.")
    parser.add_argument("--ppm", type=int, default=0,
                        help="Frequency correction in PPM (default: 0)")
    parser.add_argument("--output", type=str, required=True,
                        help="Output base path (without extension)")
    parser.add_argument("--notes", type=str, default="",
                        help="Optional notes for metadata")
    parser.add_argument("--rtl-power-path", type=str, default=None,
                        help="Path to rtl_power executable if not in PATH")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the command without executing")

    args = parser.parse_args()

    # Find rtl_power
    rtl_power = args.rtl_power_path or find_rtl_power()
    if not rtl_power:
        print("ERROR: rtl_power not found. Install rtl-sdr tools and ensure rtl_power is in PATH.")
        print("  Windows: Download from https://ftp.osmocom.org/binaries/windows/rtl-sdr/")
        print("  Or specify --rtl-power-path /path/to/rtl_power.exe")
        sys.exit(1)

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    csv_path = f"{args.output}.csv"
    meta_path = f"{args.output}.json"
    hash_path = f"{args.output}.sha256"

    # Build rtl_power command
    # rtl_power -f start:stop:bin_width -g gain -i interval -e duration output.csv
    cmd = [
        rtl_power,
        "-f", f"{int(args.start)}:{int(args.stop)}:{int(args.bin_width)}",
        "-g", str(args.gain),
        "-i", str(args.interval),
        "-e", str(args.duration),
        "-p", str(args.ppm),
        csv_path
    ]

    print(f"=== Flair RF Scanner ===")
    print(f"Frequency range: {args.start/1e6:.3f} - {args.stop/1e6:.3f} MHz")
    print(f"Bin width: {args.bin_width/1e3:.1f} kHz")
    print(f"Gain: {args.gain} dB (AGC disabled)")
    print(f"Interval: {args.interval} s")
    print(f"Duration: {args.duration} s ({args.duration/60:.1f} min)")
    print(f"Output: {csv_path}")
    print(f"Command: {' '.join(cmd)}")
    print()

    if args.dry_run:
        print("DRY RUN — command not executed.")
        return

    # Run scan
    start_time = datetime.datetime.now(datetime.timezone.utc)
    print(f"Scan started at {start_time.isoformat()}")
    print(f"Will run for {args.duration} seconds. Press Ctrl+C to stop early.")
    print()

    try:
        result = subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: rtl_power exited with code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
    except FileNotFoundError:
        print(f"\nERROR: Could not execute {rtl_power}")
        print("Ensure rtl_power is installed and the RTL-SDR is connected.")
        sys.exit(1)

    end_time = datetime.datetime.now(datetime.timezone.utc)

    if not os.path.isfile(csv_path):
        print(f"\nERROR: Output file {csv_path} was not created.")
        sys.exit(1)

    # Hash the output
    file_hash = sha256_file(csv_path)
    with open(hash_path, "w") as f:
        f.write(f"{file_hash}  {os.path.basename(csv_path)}\n")
    print(f"\nSHA-256: {file_hash}")

    # Generate metadata
    metadata = generate_metadata(args, csv_path, start_time, end_time, file_hash)
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata: {meta_path}")

    print(f"\nScan complete. Duration: {(end_time - start_time).total_seconds():.1f}s")
    print(f"Output files:")
    print(f"  CSV:      {csv_path}")
    print(f"  Metadata: {meta_path}")
    print(f"  Hash:     {hash_path}")


if __name__ == "__main__":
    main()
