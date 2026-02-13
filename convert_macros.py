#!/usr/bin/env python3
"""Batch-convert LDPlayer macro files to module JSON.

Usage:
  python convert_macros.py
  python convert_macros.py --input-dir macros --output-dir modules
  python convert_macros.py --scale-x 0.5 --scale-y 0.5
"""

from __future__ import annotations

import argparse
import io
import os
import sys

# Force UTF-8 stdout/stderr on Windows (prevents CP949 codec errors)
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

from macro_converter import convert_macro_folder


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-convert LD macro files to module JSON")
    parser.add_argument("--input-dir", default="macros", help="Input folder with .txt/.json macro files")
    parser.add_argument("--output-dir", default="modules", help="Output folder for converted JSON")
    parser.add_argument("--scale-x", type=float, default=1.0, help="Scale x coordinates")
    parser.add_argument("--scale-y", type=float, default=1.0, help="Scale y coordinates")
    parser.add_argument("--default-delay", type=float, default=0.2, help="Fallback delay between taps")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"Input directory not found: {input_dir}")
        return 1

    created = convert_macro_folder(
        input_dir=input_dir,
        output_dir=Path(args.output_dir),
        scale_x=args.scale_x,
        scale_y=args.scale_y,
        default_delay_s=args.default_delay,
    )

    if not created:
        print(f"No macro files found in {input_dir}")
        return 1

    print(f"Converted {len(created)} files -> {args.output_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
