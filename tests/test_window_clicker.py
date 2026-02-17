from __future__ import annotations

import json
from pathlib import Path

import pytest

from window_clicker import (
    AppConfig,
    ScreenshotTarget,
    TapAction,
    _parse_tap,
    load_config,
)


class TestParseTap:
    def test_defaults(self):
        tap = _parse_tap({})
        assert tap.action == "tap"
        assert tap.x == 0
        assert tap.y == 0
        assert tap.delay_after_s == 0.5

    def test_all_fields(self):
        tap = _parse_tap({
            "action": "clipboard",
            "x": 10,
            "y": 20,
            "wait_before_s": 0.3,
            "delay_after_s": 0.7,
            "screenshot_name": "shot",
            "app_package": "com.test",
            "text": "hello",
        })
        assert tap.action == "clipboard"
        assert tap.text == "hello"


class TestLoadConfig:
    def _write_config(self, tmp_path: Path, config: dict) -> Path:
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def _base_config(self, **overrides) -> dict:
        cfg = {
            "screenshot_targets": [
                {"name": "ld-1", "adb_serial": "127.0.0.1:5555"},
            ],
            "steps": [],
        }
        cfg.update(overrides)
        return cfg

    def test_basic_load(self, tmp_path: Path):
        config = self._base_config(steps=[{"action": "tap", "x": 640, "y": 360}])
        app = load_config(self._write_config(tmp_path, config))
        assert len(app.actions) == 1
        assert app.actions[0].action == "tap"
        assert app.actions[0].x == 640
        assert app.actions[0].y == 360

    def test_screenshot_targets(self, tmp_path: Path):
        targets = [
            {"name": "ld-1", "adb_serial": "127.0.0.1:5555"},
            {"name": "ld-2", "adb_serial": "127.0.0.1:5557"},
        ]
        config = self._base_config(screenshot_targets=targets)
        app = load_config(self._write_config(tmp_path, config))
        assert len(app.screenshot_targets) == 2
        assert app.screenshot_targets[0].name == "ld-1"
        assert app.screenshot_targets[1].adb_serial == "127.0.0.1:5557"

    def test_empty_steps(self, tmp_path: Path):
        config = self._base_config()
        app = load_config(self._write_config(tmp_path, config))
        assert app.actions == []

    def test_no_screenshot_targets(self, tmp_path: Path):
        config = self._base_config()
        del config["screenshot_targets"]
        app = load_config(self._write_config(tmp_path, config))
        assert app.screenshot_targets == []

    def test_defaults(self, tmp_path: Path):
        config = self._base_config()
        app = load_config(self._write_config(tmp_path, config))
        assert app.startup_wait_s == 2
        assert app.loop_delay_s == 2
        assert app.connect_retries == 5
        assert app.iterations == 0

    def test_tap_coordinates_used_directly(self, tmp_path: Path):
        config = self._base_config(
            steps=[
                {"action": "tap", "x": 480, "y": 301},
                {"action": "tap", "x": 100, "y": 200},
            ],
        )
        app = load_config(self._write_config(tmp_path, config))
        assert app.actions[0].x == 480
        assert app.actions[0].y == 301
        assert app.actions[1].x == 100
        assert app.actions[1].y == 200
