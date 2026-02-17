#!/usr/bin/env python3
"""pyautogui-based window clicker for LDPlayer.

Clicks on ONE LD Player window via pyautogui (LD multi-sync replicates
to other instances).  ADB is used only for screenshots and app control
across all screenshot_targets.

Usage:
  python window_clicker.py --config config-window.json
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

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------------
# ADB helpers
# ---------------------------------------------------------------------------

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


def take_screenshot(serial: str, output_path: Path) -> None:
    result = adb(serial, ["exec-out", "screencap", "-p"], timeout=20, text=False)
    if result.returncode != 0:
        stderr = (result.stderr.decode("utf-8", errors="ignore") if isinstance(result.stderr, bytes) else str(result.stderr))
        raise RuntimeError(f"{serial}: screenshot failed: {stderr.strip()}")

    if not result.stdout:
        raise RuntimeError(f"{serial}: screenshot failed: empty output")

    output_path.write_bytes(result.stdout)


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


def app_switch(serial: str) -> None:
    result = adb(serial, ["shell", "input", "keyevent", "KEYCODE_APP_SWITCH"], timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"{serial}: app_switch failed: {result.stderr.strip()}")


def wait_or_stop(stop_event: threading.Event, seconds: float) -> bool:
    if seconds <= 0:
        return stop_event.is_set()
    return stop_event.wait(timeout=seconds)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

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


@dataclass
class ScreenshotTarget:
    name: str
    adb_serial: str


@dataclass
class AppConfig:
    log_dir: Path
    iterations: int
    startup_wait_s: float
    loop_delay_s: float
    connect_retries: int
    connect_retry_delay_s: float
    actions: list[TapAction]
    screenshot_targets: list[ScreenshotTarget]


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

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


def load_config(path: Path) -> AppConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))

    actions = [_parse_tap(s) for s in raw.get("steps", [])]

    targets = [
        ScreenshotTarget(name=str(t["name"]), adb_serial=str(t["adb_serial"]))
        for t in raw.get("screenshot_targets", [])
    ]

    return AppConfig(
        log_dir=Path(raw.get("log_dir", "logs")),
        iterations=int(raw.get("iterations", 1)),
        startup_wait_s=float(raw.get("startup_wait_s", 2)),
        loop_delay_s=float(raw.get("loop_delay_s", 2)),
        connect_retries=int(raw.get("connect_retries", 5)),
        connect_retry_delay_s=float(raw.get("connect_retry_delay_s", 2.0)),
        actions=actions,
        screenshot_targets=targets,
    )


# ---------------------------------------------------------------------------
# ADB fan-out helpers
# ---------------------------------------------------------------------------

def _for_all_targets(targets: list[ScreenshotTarget], fn, *args) -> None:
    """Run fn(target.adb_serial, *args) for every target, log errors."""
    for t in targets:
        try:
            fn(t.adb_serial, *args)
        except Exception as exc:
            print(f"[{t.name}] {exc}")


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

def worker(config: AppConfig, stop_event: threading.Event) -> None:
    import pyautogui
    pyautogui.FAILSAFE = False

    try:
        print(f"waiting {config.startup_wait_s}s before start")
        if wait_or_stop(stop_event, config.startup_wait_s):
            print("stop requested before startup")
            return

        # Connect all ADB targets
        for t in config.screenshot_targets:
            ensure_device(t.adb_serial, retries=config.connect_retries, retry_delay_s=config.connect_retry_delay_s)
            print(f"[{t.name}] connected: {t.adb_serial}")

        # Create log dirs per target
        log_dirs: dict[str, Path] = {}
        for t in config.screenshot_targets:
            d = config.log_dir / t.name
            d.mkdir(parents=True, exist_ok=True)
            log_dirs[t.name] = d

        loops = 0
        while not stop_event.is_set():
            loops += 1
            loop_started = time.time()
            print(f"loop {loops} start ({len(config.actions)} actions)")

            for i, action in enumerate(config.actions, start=1):
                if wait_or_stop(stop_event, action.wait_before_s):
                    break

                elapsed = time.time() - loop_started

                if action.action == "tap":
                    pyautogui.click(action.x, action.y)
                    print(f"  tap#{i} ({action.x},{action.y}) t+{elapsed:.2f}s")

                elif action.action == "screenshot":
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    label = action.screenshot_name or f"step{i}"
                    for t in config.screenshot_targets:
                        shot_path = log_dirs[t.name] / f"{ts}_loop{loops}_{label}.png"
                        try:
                            take_screenshot(t.adb_serial, shot_path)
                            print(f"  [{t.name}] screenshot#{i} saved: {shot_path} t+{elapsed:.2f}s")
                        except Exception as exc:
                            print(f"  [{t.name}] screenshot#{i} failed: {exc}")

                elif action.action == "sleep":
                    print(f"  sleep#{i} {action.delay_after_s:.2f}s t+{elapsed:.2f}s")

                elif action.action == "clear_data":
                    if not action.app_package:
                        raise RuntimeError("clear_data needs app_package")
                    _for_all_targets(config.screenshot_targets, clear_data, action.app_package)
                    print(f"  clear_data#{i} {action.app_package} t+{elapsed:.2f}s")

                elif action.action == "start_app":
                    if not action.app_package:
                        raise RuntimeError("start_app needs app_package")
                    _for_all_targets(config.screenshot_targets, start_app, action.app_package)
                    print(f"  start_app#{i} {action.app_package} t+{elapsed:.2f}s")

                elif action.action == "stop_app":
                    if not action.app_package:
                        raise RuntimeError("stop_app needs app_package")
                    _for_all_targets(config.screenshot_targets, stop_app, action.app_package)
                    print(f"  stop_app#{i} {action.app_package} t+{elapsed:.2f}s")

                elif action.action == "clipboard":
                    if action.text:
                        import pyperclip
                        pyperclip.copy(action.text)
                        pyautogui.hotkey("ctrl", "v")
                        print(f"  clipboard#{i} t+{elapsed:.2f}s")

                elif action.action == "app_switch":
                    _for_all_targets(config.screenshot_targets, app_switch)
                    print(f"  app_switch#{i} t+{elapsed:.2f}s")

                else:
                    raise RuntimeError(f"unsupported action: {action.action}")

                if wait_or_stop(stop_event, action.delay_after_s):
                    break

            if stop_event.is_set():
                print("stop requested")
                break

            if config.iterations > 0 and loops >= config.iterations:
                print(f"reached iterations={config.iterations} -> stop")
                break

            if wait_or_stop(stop_event, config.loop_delay_s):
                print("stop requested")
                break
    except Exception as exc:
        print(f"ERROR: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="pyautogui window clicker for LDPlayer")
    parser.add_argument("--config", default="config-window.json", help="Path to config JSON")
    args = parser.parse_args()

    app_config = load_config(Path(args.config))
    app_config.log_dir.mkdir(parents=True, exist_ok=True)
    stop_event = threading.Event()

    t = threading.Thread(target=worker, args=(app_config, stop_event), daemon=False)
    t.start()

    try:
        t.join()
    except KeyboardInterrupt:
        print("Interrupted by user, requesting stop...")
        stop_event.set()
        t.join(timeout=5)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
