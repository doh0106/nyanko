#!/usr/bin/env python3
"""LDPlayer multi-instance fixed-click orchestrator via ADB.

Usage:
  python multi_ld_clicker.py --config config.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class TapAction:
    action: Literal["tap", "screenshot", "sleep"] = "tap"
    x: int = 0
    y: int = 0
    wait_before_s: float = 0.0
    delay_after_s: float = 0.5
    screenshot_name: str = ""


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
    instances: list[InstanceConfig]


def run_cmd(cmd: list[str], *, timeout: float = 20, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=text, timeout=timeout, check=False)


def adb(serial: str, args: list[str], *, timeout: float = 20, text: bool = True) -> subprocess.CompletedProcess:
    return run_cmd(["adb", "-s", serial] + args, timeout=timeout, text=text)


def adb_connect(serial: str) -> subprocess.CompletedProcess:
    return run_cmd(["adb", "connect", serial], timeout=12)


def ensure_device(serial: str, retries: int = 3, retry_delay_s: float = 2.0) -> None:
    attempts = max(1, retries)
    last_stdout = ""
    last_stderr = ""

    for i in range(1, attempts + 1):
        # LDPlayer 로컬 TCP serial(127.0.0.1:5555 등)은 connect가 필요한 경우가 많음
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


def screenshot(serial: str, output_path: Path) -> None:
    result = adb(serial, ["exec-out", "screencap", "-p"], timeout=20, text=False)
    if result.returncode != 0:
        stderr = (result.stderr.decode("utf-8", errors="ignore") if isinstance(result.stderr, bytes) else str(result.stderr))
        raise RuntimeError(f"{serial}: screenshot failed: {stderr.strip()}")

    if not result.stdout:
        raise RuntimeError(f"{serial}: screenshot failed: empty output")

    output_path.write_bytes(result.stdout)


def load_config(path: Path) -> AppConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))

    instances: list[InstanceConfig] = []
    for inst in raw["instances"]:
        taps = [
            TapAction(
                action=str(t.get("action", "tap")),
                x=int(t.get("x", 0)),
                y=int(t.get("y", 0)),
                wait_before_s=float(t.get("wait_before_s", 0.0)),
                delay_after_s=float(t.get("delay_after_s", 0.5)),
                screenshot_name=str(t.get("screenshot_name", "")),
            )
            for t in inst["taps"]
        ]
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
        instances=instances,
    )


def worker(config: AppConfig, inst: InstanceConfig) -> None:
    try:
        if not inst.enabled:
            print(f"[{inst.name}] disabled -> skip")
            return

        print(f"[{inst.name}] waiting {inst.startup_wait_s}s before start")
        time.sleep(inst.startup_wait_s)

        ensure_device(inst.adb_serial, retries=inst.connect_retries, retry_delay_s=inst.connect_retry_delay_s)
        print(f"[{inst.name}] connected: {inst.adb_serial}")

        loops = 0
        while True:
            loops += 1
            loop_started = time.time()
            print(f"[{inst.name}] loop {loops} start")

            for i, action in enumerate(inst.taps, start=1):
                if action.wait_before_s > 0:
                    time.sleep(action.wait_before_s)

                elapsed = time.time() - loop_started
                if action.action == "tap":
                    tap(inst.adb_serial, action.x, action.y)
                    print(f"[{inst.name}] tap#{i} ({action.x}, {action.y}) t+{elapsed:.2f}s")
                elif action.action == "screenshot":
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    label = action.screenshot_name or f"step{i}"
                    shot_path = config.log_dir / f"{inst.name}_{ts}_loop{loops}_{label}.png"
                    screenshot(inst.adb_serial, shot_path)
                    print(f"[{inst.name}] screenshot#{i} saved: {shot_path} t+{elapsed:.2f}s")
                elif action.action == "sleep":
                    print(f"[{inst.name}] sleep#{i} {action.delay_after_s:.2f}s t+{elapsed:.2f}s")
                else:
                    raise RuntimeError(f"[{inst.name}] unsupported action: {action.action}")

                if action.delay_after_s > 0:
                    time.sleep(action.delay_after_s)

            if inst.screenshot_every_loops > 0 and loops % inst.screenshot_every_loops == 0:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                shot_path = config.log_dir / f"{inst.name}_{ts}_loop{loops}.png"
                screenshot(inst.adb_serial, shot_path)
                print(f"[{inst.name}] screenshot saved: {shot_path}")

            if config.iterations > 0 and loops >= config.iterations:
                print(f"[{inst.name}] reached iterations={config.iterations} -> stop")
                break

            time.sleep(inst.loop_delay_s)
    except Exception as exc:
        print(f"[{inst.name}] ERROR: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fixed tap sequences on multiple LDPlayer windows via ADB")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    args = parser.parse_args()

    app_config = load_config(Path(args.config))
    app_config.log_dir.mkdir(parents=True, exist_ok=True)

    threads: list[threading.Thread] = []
    for inst in app_config.instances:
        t = threading.Thread(target=worker, args=(app_config, inst), daemon=False)
        t.start()
        threads.append(t)

    failed = False
    for t in threads:
        try:
            t.join()
        except KeyboardInterrupt:
            failed = True
            print("Interrupted by user")
            break

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
