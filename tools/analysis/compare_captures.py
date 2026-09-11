#!/usr/bin/env python3
"""Compare metadata from multiple captures.

Reads JSON metadata files and produces a summary table for
comparing captures across experiments.

Usage:
    python compare_captures.py captures/metadata/*.json
"""

import argparse
import json
import os
import sys


def load_metadata(filepath):
    """Load a capture metadata JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Compare capture metadata files")
    parser.add_argument("files", nargs="+", help="JSON metadata files to compare")
    parser.add_argument("--format", choices=["table", "csv"], default="table",
                        help="Output format (default: table)")
    args = parser.parse_args()

    captures = []
    for f in args.files:
        if not f.endswith(".json") or "template" in f.lower():
            continue
        try:
            meta = load_metadata(f)
            captures.append({
                "file": os.path.basename(f),
                "id": meta.get("capture_id", "?"),
                "date": meta.get("date_local", meta.get("date_utc", "?")),
                "action": meta.get("capture", {}).get("action", meta.get("type", "?")),
                "freq_mhz": meta.get("rf_parameters", {}).get("center_frequency_hz", "?"),
                "rate": meta.get("rf_parameters", {}).get("sample_rate_sps", "?"),
                "gain": meta.get("rf_parameters", {}).get("gain_db", "?"),
                "duration": meta.get("capture", meta.get("scan", {})).get("duration_seconds",
                           meta.get("scan", {}).get("total_duration_seconds", "?")),
                "size": meta.get("capture", meta.get("scan", {})).get("raw_filesize_bytes",
                        meta.get("scan", {}).get("csv_filesize_bytes", "?")),
                "sha256": meta.get("capture", meta.get("scan", {})).get("raw_sha256",
                          meta.get("scan", {}).get("csv_sha256", "?"))[:16] + "..." if
                          meta.get("capture", meta.get("scan", {})).get("raw_sha256",
                          meta.get("scan", {}).get("csv_sha256", "")) else "?"
            })
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not parse {f}: {e}", file=sys.stderr)

    if not captures:
        print("No valid capture metadata found.")
        sys.exit(1)

    if args.format == "csv":
        keys = ["id", "date", "action", "freq_mhz", "rate", "gain", "duration", "size"]
        print(",".join(keys))
        for c in captures:
            print(",".join(str(c.get(k, "")) for k in keys))
    else:
        # Table format
        print(f"{'ID':<50} {'Action':<20} {'Freq (Hz)':<15} {'Gain':<6} {'Duration':<10} {'Size':<12}")
        print("-" * 120)
        for c in captures:
            freq = c['freq_mhz']
            if isinstance(freq, (int, float)):
                freq_str = f"{freq}"
            else:
                freq_str = str(freq)
            print(f"{c['id']:<50} {c['action']:<20} {freq_str:<15} {c['gain']:<6} {c['duration']:<10} {c['size']:<12}")

    print(f"\nTotal captures: {len(captures)}")


if __name__ == "__main__":
    main()
