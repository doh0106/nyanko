#!/usr/bin/env python3
"""Convert LDPlayer macro JSON (operations) into taps for config.json.

Usage:
  python ldmacro_to_config.py --input macro.json --output generated_taps.json
  python ldmacro_to_config.py --input macro.json --output generated_taps.json --scale-x 0.5 --scale-y 0.5
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys

# Force UTF-8 stdout/stderr on Windows (prevents CP949 codec errors)
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

from macro_converter import LD_COORD_DIVISOR, convert_macro_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert LD macro operations to config taps")
    parser.add_argument("--input", required=True, help="LD macro JSON path")
    parser.add_argument("--output", required=True, help="Output JSON path (taps array)")
    parser.add_argument("--scale-x", type=float, default=1.0, help="Scale x coordinates")
    parser.add_argument("--scale-y", type=float, default=1.0, help="Scale y coordinates")
    parser.add_argument("--default-delay", type=float, default=0.2, help="Fallback delay between taps")
    parser.add_argument("--coord-divisor", type=float, default=LD_COORD_DIVISOR,
                        help=f"LD internal coord divisor (default {LD_COORD_DIVISOR} for 320dpi)")
    args = parser.parse_args()

    taps = convert_macro_file(
        Path(args.input),
        scale_x=args.scale_x,
        scale_y=args.scale_y,
        default_delay_s=args.default_delay,
        coord_divisor=args.coord_divisor,
    )

    Path(args.output).write_text(
        json.dumps(taps, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Converted {len(taps)} actions -> {args.output}")
    print("Next: copy this taps array into config.json instances[].taps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
