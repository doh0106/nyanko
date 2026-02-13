"""Core logic for converting LDPlayer macro files to tap action arrays.

Supports both flat `operations` and nested `mergedRecords` formats,
with three operation types: PutMultiTouch, ImeClipboard, AndroidAppSwitch.
"""

from __future__ import annotations

import json
from pathlib import Path

_DEFAULT_DELAY_S = 0.2
# LD Player stores touch coords as pixel * divisor.  For 320 DPI the
# divisor is 22.5 (verified from edge-tap recordings).  Override via
# --coord-divisor if your emulator uses a different DPI.
LD_COORD_DIVISOR = 22.5


def _clamp_nonnegative(v: float) -> float:
    return v if v >= 0 else 0.0


def _extract_operations(raw: dict) -> list[dict]:
    """Flatten mergedRecords (with cumulative timing offsets) or return flat operations."""
    if "operations" in raw:
        return raw["operations"]

    merged = raw.get("mergedRecords", [])
    ops: list[dict] = []
    for record in merged:
        base_timing = int(record.get("timing", 0))
        for op in record.get("operations", []):
            copied = dict(op)
            copied["timing"] = base_timing + int(op.get("timing", 0))
            ops.append(copied)
    return ops


def _needs_ld_scaling(ops: list[dict], res_w: int, res_h: int) -> bool:
    """Check whether raw coordinates exceed display resolution (LD internal space)."""
    for op in ops:
        if op.get("operationId") != "PutMultiTouch":
            continue
        for p in op.get("points") or []:
            if float(p.get("x", 0)) > res_w or float(p.get("y", 0)) > res_h:
                return True
    return False


def _parse_operations(
    ops: list[dict],
    scale_x: float = 1.0,
    scale_y: float = 1.0,
    default_delay_s: float = _DEFAULT_DELAY_S,
) -> list[dict]:
    """Convert raw operations into our tap action format.

    Supported operationIds:
      - PutMultiTouch (state=1 only) → tap
      - ImeClipboard → clipboard
      - AndroidAppSwitch → app_switch
    """
    events: list[tuple[int, dict]] = []  # (timing_ms, action_dict)

    for op in ops:
        op_id = op.get("operationId", "")
        timing = int(op.get("timing", 0))

        if op_id == "PutMultiTouch":
            points = op.get("points") or []
            if not points:
                continue
            p0 = points[0]
            if int(p0.get("state", 1)) != 1:
                continue
            x = int(round(float(p0.get("x", 0)) * scale_x))
            y = int(round(float(p0.get("y", 0)) * scale_y))
            events.append((timing, {"action": "tap", "x": x, "y": y}))

        elif op_id == "ImeClipboard":
            text = op.get("text", "")
            events.append((timing, {"action": "clipboard", "text": text}))

        elif op_id == "AndroidAppSwitch":
            events.append((timing, {"action": "app_switch"}))

    events.sort(key=lambda e: e[0])

    taps: list[dict] = []
    prev_timing = 0
    for timing, action_dict in events:
        wait_before_s = _clamp_nonnegative((timing - prev_timing) / 1000.0)
        entry = {
            **action_dict,
            "wait_before_s": round(wait_before_s, 3),
            "delay_after_s": round(default_delay_s, 3),
        }
        taps.append(entry)
        prev_timing = timing

    return taps


def convert_macro_file(
    path: Path,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
    default_delay_s: float = _DEFAULT_DELAY_S,
    coord_divisor: float = LD_COORD_DIVISOR,
) -> list[dict]:
    """Convert a single LD macro file to a list of tap actions.

    LD Player stores touch coordinates in an internal space (pixel * divisor).
    When recordInfo has resolution data and raw coordinates exceed it, we
    divide by coord_divisor (default 22.5 for 320 DPI) to get pixel coords.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    ops = _extract_operations(raw)

    info = raw.get("recordInfo", {})
    res_w = int(info.get("resolutionWidth", 0))
    res_h = int(info.get("resolutionHeight", 0))

    if res_w > 0 and res_h > 0 and _needs_ld_scaling(ops, res_w, res_h):
        scale_x /= coord_divisor
        scale_y /= coord_divisor

    return _parse_operations(ops, scale_x, scale_y, default_delay_s)


def convert_macro_folder(
    input_dir: Path,
    output_dir: Path,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
    default_delay_s: float = _DEFAULT_DELAY_S,
    coord_divisor: float = LD_COORD_DIVISOR,
) -> list[Path]:
    """Batch-convert all .txt/.json/.record macro files in input_dir to output_dir.

    Returns list of created output paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    sources = (
        sorted(input_dir.glob("*.txt"))
        + sorted(input_dir.glob("*.json"))
        + sorted(input_dir.glob("*.record"))
    )

    for src in sources:
        taps = convert_macro_file(src, scale_x, scale_y, default_delay_s, coord_divisor)
        out_path = output_dir / f"{src.stem}.json"
        out_path.write_text(
            json.dumps(taps, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        created.append(out_path)
        print(f"  {src.name} -> {out_path.name} ({len(taps)} actions)")

    return created
