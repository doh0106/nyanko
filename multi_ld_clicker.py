#!/usr/bin/env python3
"""LDPlayer multi-instance fixed-click orchestrator via ADB.

Usage:
  python multi_ld_clicker.py --config config.json
"""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import threading
import time
import unicodedata

# Force UTF-8 stdout/stderr on Windows (prevents CP949 codec errors)
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class TapAction:
    action: Literal["tap", "screenshot", "sleep", "clear_data", "start_app", "stop_app", "clipboard", "app_switch"] = "tap"
    x: int = 0
    y: int = 0
    wait_before_s: float = 0.0
    delay_after_s: float = 0.5
    screenshot_name: str = ""
    app_package: str = ""
    text: str = ""
    source_res_w: int = 0
    source_res_h: int = 0


@dataclass
class InstanceConfig:
    name: str
    adb_serial: str
    enabled: bool
    startup_wait_s: float
    loop_delay_s: float
    taps: list[TapAction]
    screenshot_every_loops: int
    connect_retries: int
    connect_retry_delay_s: float


@dataclass
class AppConfig:
    log_dir: Path
    iterations: int
    modules_dir: Path
    instances: list[InstanceConfig]


def run_cmd(cmd: list[str], *, timeout: float = 20, text: bool = True) -> subprocess.CompletedProcess:
    encoding = "utf-8" if text else None
    return subprocess.run(cmd, capture_output=True, text=text, encoding=encoding, errors="replace", timeout=timeout, check=False)


def adb(serial: str, args: list[str], *, timeout: float = 20, text: bool = True) -> subprocess.CompletedProcess:
    return run_cmd(["adb", "-s", serial] + args, timeout=timeout, text=text)


def adb_connect(serial: str) -> subprocess.CompletedProcess:
    return run_cmd(["adb", "connect", serial], timeout=12)


def ensure_device(serial: str, retries: int = 3, retry_delay_s: float = 2.0) -> None:
    attempts = max(1, retries)
    last_stdout = ""
    last_stderr = ""

    for i in range(1, attempts + 1):
        adb_connect(serial)
        result = adb(serial, ["get-state"], timeout=10)
        last_stdout = result.stdout
        last_stderr = result.stderr
        if result.returncode == 0 and "device" in result.stdout:
            return

        if i < attempts:
            print(f"[{serial}] ADB not ready, retry {i}/{attempts} ...")
            time.sleep(retry_delay_s)

    raise RuntimeError(
        f"{serial}: ADB not ready after {attempts} attempts. "
        f"stdout={last_stdout!r} stderr={last_stderr!r}. "
        f"Check adb devices / LD ADB setting / serial(port)."
    )


def tap(serial: str, x: int, y: int) -> None:
    result = adb(serial, ["shell", "input", "tap", str(x), str(y)], timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"{serial}: tap ({x},{y}) failed: {result.stderr.strip()}")


def clear_data(serial: str, package: str) -> None:
    result = adb(serial, ["shell", "pm", "clear", package], timeout=20)
    if result.returncode != 0 or "Success" not in result.stdout:
        raise RuntimeError(f"{serial}: clear_data failed for {package}: {result.stdout.strip()} {result.stderr.strip()}")


def start_app(serial: str, package: str) -> None:
    result = adb(serial, ["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"], timeout=20)
    if result.returncode != 0:
        raise RuntimeError(f"{serial}: start_app failed for {package}: {result.stderr.strip()}")


def stop_app(serial: str, package: str) -> None:
    result = adb(serial, ["shell", "am", "force-stop", package], timeout=15)
    if result.returncode != 0:
        raise RuntimeError(f"{serial}: stop_app failed for {package}: {result.stderr.strip()}")


def clipboard_input(serial: str, text: str) -> None:
    result = adb(serial, ["shell", "input", "text", text], timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"{serial}: clipboard input failed: {result.stderr.strip()}")


def app_switch(serial: str) -> None:
    result = adb(serial, ["shell", "input", "keyevent", "KEYCODE_APP_SWITCH"], timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"{serial}: app_switch failed: {result.stderr.strip()}")


def get_display_size(serial: str) -> tuple[int, int]:
    """Query current display size via 'adb shell wm size'."""
    result = adb(serial, ["shell", "wm", "size"], timeout=10)
    # Parse last line: "Physical size: 720x1280" or "Override size: ..."
    for line in reversed(result.stdout.strip().splitlines()):
        if "x" in line and ":" in line:
            dims = line.split(":")[-1].strip().split("x")
            if len(dims) == 2:
                return int(dims[0]), int(dims[1])
    return 0, 0


def rotate_if_needed(
    x: int, y: int,
    src_w: int, src_h: int,
    disp_w: int, disp_h: int,
) -> tuple[int, int]:
    """Rotate coordinates when source and display orientations differ.

    Handles landscape module on portrait display (and vice versa).
    Uses ROTATION_90 (CW) mapping which is standard for Android games.
    """
    src_landscape = src_w > src_h
    disp_landscape = disp_w > disp_h

    if src_landscape == disp_landscape:
        return x, y

    if src_landscape and not disp_landscape:
        # landscape -> portrait (ROTATION_90 CW)
        return y, disp_h - 1 - x
    # portrait -> landscape
    return disp_w - 1 - y, x


def screenshot(serial: str, output_path: Path) -> None:
    result = adb(serial, ["exec-out", "screencap", "-p"], timeout=20, text=False)
    if result.returncode != 0:
        stderr = (result.stderr.decode("utf-8", errors="ignore") if isinstance(result.stderr, bytes) else str(result.stderr))
        raise RuntimeError(f"{serial}: screenshot failed: {stderr.strip()}")

    if not result.stdout:
        raise RuntimeError(f"{serial}: screenshot failed: empty output")

    output_path.write_bytes(result.stdout)


def _parse_tap(t: dict) -> TapAction:
    return TapAction(
        action=str(t.get("action", "tap")),
        x=int(t.get("x", 0)),
        y=int(t.get("y", 0)),
        wait_before_s=float(t.get("wait_before_s", 0.0)),
        delay_after_s=float(t.get("delay_after_s", 0.5)),
        screenshot_name=str(t.get("screenshot_name", "")),
        app_package=str(t.get("app_package", "")),
        text=str(t.get("text", "")),
    )


def _apply_scaling(taps: list[dict], scale_x: float, scale_y: float) -> list[dict]:
    scaled: list[dict] = []
    for t in taps:
        copied = dict(t)
        if "x" in copied:
            copied["x"] = int(round(float(copied["x"]) * scale_x))
        if "y" in copied:
            copied["y"] = int(round(float(copied["y"]) * scale_y))
        scaled.append(copied)
    return scaled


def _find_module_file(modules_dir: Path, module_name: str) -> Path:
    """Find module file with unicode normalization fallback (NFC/NFD)."""
    direct = modules_dir / f"{module_name}.json"
    if direct.exists():
        return direct
    # filesystem may use NFD (macOS/some Linux); config strings are typically NFC
    normalized_name = unicodedata.normalize("NFC", module_name)
    for candidate in modules_dir.glob("*.json"):
        if unicodedata.normalize("NFC", candidate.stem) == normalized_name:
            return candidate
    raise FileNotFoundError(f"Module not found: {direct}")


def _resolve_steps(steps: list[dict], modules_dir: Path) -> list[TapAction]:
    """Resolve steps (mix of module references and inline actions) into flat TapAction list."""
    result: list[TapAction] = []
    for step in steps:
        if "module" in step:
            module_name = step["module"]
            module_path = _find_module_file(modules_dir, module_name)
            raw_taps = json.loads(module_path.read_text(encoding="utf-8"))

            # Extract _meta (recorded resolution) if present
            meta_w, meta_h = 0, 0
            action_taps = []
            for t in raw_taps:
                if "_meta" in t:
                    meta_w = int(t["_meta"].get("res_w", 0))
                    meta_h = int(t["_meta"].get("res_h", 0))
                else:
                    action_taps.append(t)

            scale_x = float(step.get("scale_x", 1.0))
            scale_y = float(step.get("scale_y", 1.0))
            if scale_x != 1.0 or scale_y != 1.0:
                action_taps = _apply_scaling(action_taps, scale_x, scale_y)

            for t in action_taps:
                parsed = _parse_tap(t)
                parsed.source_res_w = meta_w
                parsed.source_res_h = meta_h
                result.append(parsed)
        else:
            result.append(_parse_tap(step))
    return result


def load_config(path: Path) -> AppConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    modules_dir = Path(raw.get("modules_dir", "modules"))

    instances: list[InstanceConfig] = []
    for inst in raw["instances"]:
        has_taps = "taps" in inst
        has_steps = "steps" in inst
        if has_taps and has_steps:
            raise ValueError(f"Instance '{inst.get('name')}': cannot use both 'taps' and 'steps'")

        if has_steps:
            taps = _resolve_steps(inst["steps"], modules_dir)
        elif has_taps:
            taps = [_parse_tap(t) for t in inst["taps"]]
        else:
            taps = []

        instances.append(
            InstanceConfig(
                name=str(inst["name"]),
                adb_serial=str(inst["adb_serial"]),
                enabled=bool(inst.get("enabled", True)),
                startup_wait_s=float(inst.get("startup_wait_s", 2)),
                loop_delay_s=float(inst.get("loop_delay_s", 2)),
                taps=taps,
                screenshot_every_loops=int(inst.get("screenshot_every_loops", 0)),
                connect_retries=int(inst.get("connect_retries", 5)),
                connect_retry_delay_s=float(inst.get("connect_retry_delay_s", 2.0)),
            )
        )

    return AppConfig(
        log_dir=Path(raw.get("log_dir", "logs")),
        iterations=int(raw.get("iterations", 0)),
        modules_dir=modules_dir,
        instances=instances,
    )


def wait_or_stop(stop_event: threading.Event, seconds: float) -> bool:
    if seconds <= 0:
        return stop_event.is_set()
    return stop_event.wait(timeout=seconds)


def worker(config: AppConfig, inst: InstanceConfig, stop_event: threading.Event) -> None:
    try:
        if not inst.enabled:
            print(f"[{inst.name}] disabled -> skip")
            return

        print(f"[{inst.name}] waiting {inst.startup_wait_s}s before start")
        if wait_or_stop(stop_event, inst.startup_wait_s):
            print(f"[{inst.name}] stop requested before startup")
            return

        ensure_device(inst.adb_serial, retries=inst.connect_retries, retry_delay_s=inst.connect_retry_delay_s)
        print(f"[{inst.name}] connected: {inst.adb_serial}")

        disp_w, disp_h = get_display_size(inst.adb_serial)
        print(f"[{inst.name}] display: {disp_w}x{disp_h}")

        inst_log_dir = config.log_dir / inst.name
        inst_log_dir.mkdir(parents=True, exist_ok=True)

        loops = 0
        while not stop_event.is_set():
            loops += 1
            loop_started = time.time()
            print(f"[{inst.name}] loop {loops} start ({len(inst.taps)} actions)")

            for i, action in enumerate(inst.taps, start=1):
                if wait_or_stop(stop_event, action.wait_before_s):
                    break

                elapsed = time.time() - loop_started
                if action.action == "tap":
                    tx, ty = action.x, action.y
                    if action.source_res_w > 0 and disp_w > 0:
                        tx, ty = rotate_if_needed(
                            tx, ty,
                            action.source_res_w, action.source_res_h,
                            disp_w, disp_h,
                        )
                    tap(inst.adb_serial, tx, ty)
                    print(f"[{inst.name}] tap#{i} ({tx}, {ty}) t+{elapsed:.2f}s")
                elif action.action == "screenshot":
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    label = action.screenshot_name or f"step{i}"
                    shot_path = inst_log_dir / f"{ts}_loop{loops}_{label}.png"
                    screenshot(inst.adb_serial, shot_path)
                    print(f"[{inst.name}] screenshot#{i} saved: {shot_path} t+{elapsed:.2f}s")
                elif action.action == "sleep":
                    print(f"[{inst.name}] sleep#{i} {action.delay_after_s:.2f}s t+{elapsed:.2f}s")
                elif action.action == "clear_data":
                    if not action.app_package:
                        raise RuntimeError(f"[{inst.name}] clear_data needs app_package")
                    clear_data(inst.adb_serial, action.app_package)
                    print(f"[{inst.name}] clear_data#{i} {action.app_package} t+{elapsed:.2f}s")
                elif action.action == "start_app":
                    if not action.app_package:
                        raise RuntimeError(f"[{inst.name}] start_app needs app_package")
                    start_app(inst.adb_serial, action.app_package)
                    print(f"[{inst.name}] start_app#{i} {action.app_package} t+{elapsed:.2f}s")
                elif action.action == "stop_app":
                    if not action.app_package:
                        raise RuntimeError(f"[{inst.name}] stop_app needs app_package")
                    stop_app(inst.adb_serial, action.app_package)
                    print(f"[{inst.name}] stop_app#{i} {action.app_package} t+{elapsed:.2f}s")
                elif action.action == "clipboard":
                    if not action.text:
                        pass  # empty clipboard clear from LD macro, skip
                    else:
                        clipboard_input(inst.adb_serial, action.text)
                        print(f"[{inst.name}] clipboard#{i} t+{elapsed:.2f}s")
                elif action.action == "app_switch":
                    app_switch(inst.adb_serial)
                    print(f"[{inst.name}] app_switch#{i} t+{elapsed:.2f}s")
                else:
                    raise RuntimeError(f"[{inst.name}] unsupported action: {action.action}")

                if wait_or_stop(stop_event, action.delay_after_s):
                    break

            if stop_event.is_set():
                print(f"[{inst.name}] stop requested")
                break

            if inst.screenshot_every_loops > 0 and loops % inst.screenshot_every_loops == 0:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                shot_path = inst_log_dir / f"{ts}_loop{loops}.png"
                screenshot(inst.adb_serial, shot_path)
                print(f"[{inst.name}] screenshot saved: {shot_path}")

            if config.iterations > 0 and loops >= config.iterations:
                print(f"[{inst.name}] reached iterations={config.iterations} -> stop")
                break

            if wait_or_stop(stop_event, inst.loop_delay_s):
                print(f"[{inst.name}] stop requested")
                break
    except Exception as exc:
        print(f"[{inst.name}] ERROR: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fixed tap sequences on multiple LDPlayer windows via ADB")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    args = parser.parse_args()

    app_config = load_config(Path(args.config))
    app_config.log_dir.mkdir(parents=True, exist_ok=True)
    stop_event = threading.Event()

    threads: list[threading.Thread] = []
    for inst in app_config.instances:
        t = threading.Thread(target=worker, args=(app_config, inst, stop_event), daemon=False)
        t.start()
        threads.append(t)

    failed = False
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        failed = True
        print("Interrupted by user, requesting stop...")
        stop_event.set()
        for t in threads:
            t.join(timeout=5)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
