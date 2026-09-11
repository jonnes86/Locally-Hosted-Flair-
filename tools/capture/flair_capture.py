#!/usr/bin/env python3
"""Flair RF Capture — Narrow-band IQ recording using rtl_sdr.

Captures raw IQ data at a specific center frequency for detailed
protocol analysis. Generates metadata and SHA-256 hash automatically.

Usage:
    python flair_capture.py --freq 915000000 --rate 2048000 --gain 20 \
        --duration 30 --label vent01-open --device vent01

Output:
    - Raw IQ file (.cu8) — NOT committed to Git
    - JSON metadata file — committed to Git
    - SHA-256 hash file — committed to Git
"""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import shutil


def find_rtl_sdr():
    """Locate rtl_sdr executable."""
    rtl_sdr = shutil.which("rtl_sdr")
    if rtl_sdr:
        return rtl_sdr
    common_paths = [
        os.path.join(os.environ.get("ProgramFiles", ""), "rtl-sdr", "rtl_sdr.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "rtl-sdr", "rtl_sdr.exe"),
        os.path.join(os.environ.get("USERPROFILE", ""), "rtl-sdr", "rtl_sdr.exe"),
    ]
    for p in common_paths:
        if os.path.isfile(p):
            return p
    return None


def sha256_file(filepath):
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_filename(args, timestamp):
    """Generate standardized capture filename."""
    ts = timestamp.strftime("%Y%m%d-%H%M%S")
    gain_str = str(int(args.gain * 10))  # 20.0 dB -> 200
    return f"{ts}_flair_{args.device}_{args.label}_fc-{int(args.freq)}_sr-{int(args.rate)}_gain-{gain_str}"


def main():
    parser = argparse.ArgumentParser(
        description="Flair RF Capture — Narrow-band IQ recording using rtl_sdr"
    )
    parser.add_argument("--freq", type=float, required=True,
                        help="Center frequency in Hz (e.g., 915000000)")
    parser.add_argument("--rate", type=int, default=2048000,
                        help="Sample rate in samples/sec (default: 2048000)")
    parser.add_argument("--gain", type=float, default=20.0,
                        help="Tuner gain in dB (default: 20.0). AGC is disabled.")
    parser.add_argument("--duration", type=int, default=30,
                        help="Capture duration in seconds (default: 30)")
    parser.add_argument("--label", type=str, required=True,
                        help="Action label (e.g., vent01-open, idle, vent01-close)")
    parser.add_argument("--device", type=str, default="all",
                        help="Device identifier (default: all)")
    parser.add_argument("--ppm", type=int, default=0,
                        help="Frequency correction in PPM (default: 0)")
    parser.add_argument("--output-dir", type=str, default="captures/raw",
                        help="Output directory for raw IQ files")
    parser.add_argument("--meta-dir", type=str, default="captures/metadata",
                        help="Output directory for metadata files")
    parser.add_argument("--notes", type=str, default="",
                        help="Optional notes for metadata")
    parser.add_argument("--rtl-sdr-path", type=str, default=None,
                        help="Path to rtl_sdr executable if not in PATH")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the command without executing")

    args = parser.parse_args()

    # Find rtl_sdr
    rtl_sdr = args.rtl_sdr_path or find_rtl_sdr()
    if not rtl_sdr:
        print("ERROR: rtl_sdr not found. Install rtl-sdr tools and ensure rtl_sdr is in PATH.")
        print("  Windows: Download from https://ftp.osmocom.org/binaries/windows/rtl-sdr/")
        print("  Or specify --rtl-sdr-path /path/to/rtl_sdr.exe")
        sys.exit(1)

    # Ensure output directories exist
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.meta_dir, exist_ok=True)

    # Generate filenames
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    base_name = generate_filename(args, now_utc)

    raw_path = os.path.join(args.output_dir, f"{base_name}.cu8")
    meta_path = os.path.join(args.meta_dir, f"{base_name}.json")
    hash_path = os.path.join(args.meta_dir, f"{base_name}.sha256")

    # Calculate number of samples
    num_samples = int(args.rate * args.duration) * 2  # *2 because I and Q are interleaved

    # Build rtl_sdr command
    cmd = [
        rtl_sdr,
        "-f", str(int(args.freq)),
        "-s", str(int(args.rate)),
        "-g", str(args.gain),
        "-p", str(args.ppm),
        "-n", str(num_samples),
        raw_path
    ]

    print(f"=== Flair RF Capture ===")
    print(f"Center frequency: {args.freq/1e6:.6f} MHz")
    print(f"Sample rate: {args.rate/1e6:.3f} Msps")
    print(f"Gain: {args.gain} dB (AGC disabled)")
    print(f"Duration: {args.duration} s")
    print(f"Samples: {num_samples:,} bytes ({num_samples/1e6:.1f} MB)")
    print(f"Label: {args.label}")
    print(f"Device: {args.device}")
    print(f"Output: {raw_path}")
    print(f"Command: {' '.join(cmd)}")
    print()

    if args.dry_run:
        print("DRY RUN — command not executed.")
        print(f"\nMetadata would be saved to: {meta_path}")
        return

    # Prompt operator for action timing
    print(f"Capture will run for {args.duration} seconds.")
    print(f"Action to perform: {args.label}")
    print("IMPORTANT: Note the exact time you perform the action!")
    print()
    input("Press ENTER to start capture...")

    start_time = datetime.datetime.now(datetime.timezone.utc)
    start_local = datetime.datetime.now().astimezone()
    print(f"\nCapture started at {start_time.isoformat()} (local: {start_local.isoformat()})")
    print(f"Perform '{args.label}' during this capture window.")
    print(f"Recording for {args.duration} seconds...")

    try:
        result = subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: rtl_sdr exited with code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\nCapture interrupted by user.")
    except FileNotFoundError:
        print(f"\nERROR: Could not execute {rtl_sdr}")
        sys.exit(1)

    end_time = datetime.datetime.now(datetime.timezone.utc)

    if not os.path.isfile(raw_path):
        print(f"\nERROR: Output file {raw_path} was not created.")
        sys.exit(1)

    file_size = os.path.getsize(raw_path)
    print(f"\nCapture complete. File size: {file_size:,} bytes ({file_size/1e6:.1f} MB)")

    # Prompt for action timestamp
    print("\n--- Action Timing ---")
    action_offset = input("Approximate seconds after capture start when action was performed (or 'skip'): ").strip()
    if action_offset.lower() == 'skip':
        action_offset_sec = None
    else:
        try:
            action_offset_sec = float(action_offset)
        except ValueError:
            action_offset_sec = None
            print("Could not parse offset, recording as null.")

    # Hash the file
    print("\nComputing SHA-256...")
    file_hash = sha256_file(raw_path)
    with open(hash_path, "w") as f:
        f.write(f"{file_hash}  {os.path.basename(raw_path)}\n")
    print(f"SHA-256: {file_hash}")

    # Build timeline
    timeline = [
        {
            "time_utc": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "time_offset_sec": 0.0,
            "event": "capture_start",
            "details": ""
        }
    ]
    if action_offset_sec is not None:
        timeline.append({
            "time_utc": (start_time + datetime.timedelta(seconds=action_offset_sec)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "time_offset_sec": action_offset_sec,
            "event": "action_performed",
            "details": args.label
        })
    timeline.append({
        "time_utc": end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "time_offset_sec": (end_time - start_time).total_seconds(),
        "event": "capture_end",
        "details": ""
    })

    # Generate metadata
    metadata = {
        "capture_id": base_name,
        "version": "1.0",
        "date_utc": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date_local": start_local.isoformat(),
        "phase": "1",
        "equipment": {
            "sdr": {
                "model": "RTL-SDR.com Blog V3",
                "chipset": "R820T2 + RTL2832U"
            }
        },
        "flair_devices": {
            "target_device": args.device
        },
        "rf_parameters": {
            "center_frequency_hz": int(args.freq),
            "sample_rate_sps": int(args.rate),
            "gain_db": args.gain,
            "agc": False,
            "ppm_correction": args.ppm
        },
        "capture": {
            "action": args.label,
            "duration_seconds": args.duration,
            "raw_filename": os.path.basename(raw_path),
            "raw_format": "cu8",
            "raw_filesize_bytes": file_size,
            "raw_sha256": file_hash,
            "command_line": " ".join(cmd)
        },
        "timeline": timeline,
        "notes": args.notes or ""
    }

    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata: {meta_path}")

    print(f"\n=== Capture Summary ===")
    print(f"  Raw IQ:   {raw_path} ({file_size/1e6:.1f} MB)")
    print(f"  Metadata: {meta_path}")
    print(f"  Hash:     {hash_path}")
    print(f"\nRemember: Raw .cu8 files are NOT committed to Git.")
    print(f"Metadata and hash files ARE committed to Git.")


if __name__ == "__main__":
    main()
