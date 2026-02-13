#!/usr/bin/env python3
"""Convert LDPlayer macro JSON (operations) into taps for config.json.

Usage:
  python ldmacro_to_config.py --input delete_macro.json --output generated_taps.json
  python ldmacro_to_config.py --input delete_macro.json --output generated_taps.json --scale-x 0.5 --scale-y 0.5
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def clamp_nonnegative(v: float) -> float:
    return v if v >= 0 else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert LD macro operations to config taps")
    parser.add_argument("--input", required=True, help="LD macro JSON path")
    parser.add_argument("--output", required=True, help="Output JSON path (taps array)")
    parser.add_argument("--scale-x", type=float, default=1.0, help="Scale x coordinates")
    parser.add_argument("--scale-y", type=float, default=1.0, help="Scale y coordinates")
    parser.add_argument("--default-delay", type=float, default=0.2, help="Fallback delay between taps")
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    ops = raw.get("operations", [])

    tap_events: list[tuple[int, int, int]] = []  # (timing_ms, x, y)

    for op in ops:
        op_id = op.get("operationId")
        timing = int(op.get("timing", 0))

        if op_id == "PutMultiTouch":
            points = op.get("points") or []
            if not points:
                continue
            # state 1/down as tap trigger (state 0/up can be noisy duplicates)
            p0 = points[0]
            state = int(p0.get("state", 1))
            if state != 1:
                continue
            x = int(round(float(p0.get("x", 0)) * args.scale_x))
            y = int(round(float(p0.get("y", 0)) * args.scale_y))
            tap_events.append((timing, x, y))

    tap_events.sort(key=lambda t: t[0])

    taps: list[dict] = []
    prev_timing = 0
    for i, (timing, x, y) in enumerate(tap_events):
        wait_before_s = clamp_nonnegative((timing - prev_timing) / 1000.0)
        delay_after_s = args.default_delay
        taps.append(
            {
                "action": "tap",
                "x": x,
                "y": y,
                "wait_before_s": round(wait_before_s, 3),
                "delay_after_s": round(delay_after_s, 3),
            }
        )
        prev_timing = timing

    Path(args.output).write_text(json.dumps(taps, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Converted {len(taps)} taps -> {args.output}")
    print("Next: copy this taps array into config.json instances[].taps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
