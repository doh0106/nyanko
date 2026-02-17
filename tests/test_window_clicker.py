from __future__ import annotations

import json
from pathlib import Path

import pytest

from window_clicker import (
    AppConfig,
    GameRect,
    ResolvedAction,
    ScreenshotTarget,
    TapAction,
    _parse_tap,
    _resolve_steps,
    game_to_screen,
    load_config,
)


class TestGameToScreen:
    """Proportional mapping from game pixels to screen coordinates."""

    def test_center(self):
        rect = GameRect(left=0, top=0, width=960, height=540)
        sx, sy = game_to_screen(640, 360, 1280, 720, rect)
        assert sx == 480
        assert sy == 270

    def test_origin(self):
        rect = GameRect(left=100, top=50, width=960, height=540)
        sx, sy = game_to_screen(0, 0, 1280, 720, rect)
        assert sx == 100
        assert sy == 50

    def test_bottom_right(self):
        rect = GameRect(left=0, top=0, width=960, height=540)
        sx, sy = game_to_screen(1280, 720, 1280, 720, rect)
        assert sx == 960
        assert sy == 540

    def test_with_offset(self):
        rect = GameRect(left=100, top=31, width=960, height=540)
        sx, sy = game_to_screen(640, 360, 1280, 720, rect)
        assert sx == 100 + 480
        assert sy == 31 + 270

    def test_quarter_point(self):
        rect = GameRect(left=0, top=0, width=960, height=540)
        sx, sy = game_to_screen(320, 180, 1280, 720, rect)
        assert sx == 240
        assert sy == 135

    def test_different_resolution(self):
        rect = GameRect(left=0, top=0, width=320, height=540)
        sx, sy = game_to_screen(360, 640, 720, 1280, rect)
        assert sx == 160
        assert sy == 270


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


class TestResolveSteps:
    _DEFAULT_RECT = GameRect(left=0, top=0, width=960, height=540)
    _DEFAULT_RES_W = 1280
    _DEFAULT_RES_H = 720

    def test_inline_action(self):
        steps = [{"action": "tap", "x": 10, "y": 20}]
        result = _resolve_steps(steps, self._DEFAULT_RECT, self._DEFAULT_RES_W, self._DEFAULT_RES_H)
        assert len(result) == 1
        assert result[0].tap.action == "tap"
        assert result[0].tap.x == 10
        assert result[0].rect == self._DEFAULT_RECT

    def test_step_game_rect_override(self):
        override_rect = {"left": 320, "top": 0, "width": 320, "height": 540}
        steps = [{"action": "tap", "x": 100, "y": 200, "game_rect": override_rect, "game_resolution": {"w": 720, "h": 1280}}]
        result = _resolve_steps(steps, self._DEFAULT_RECT, self._DEFAULT_RES_W, self._DEFAULT_RES_H)

        assert result[0].rect == GameRect(left=320, top=0, width=320, height=540)
        assert result[0].res_w == 720
        assert result[0].res_h == 1280

    def test_mixed_steps_default_and_override(self):
        steps = [
            {"action": "tap", "x": 640, "y": 360},
            {"action": "tap", "x": 360, "y": 640, "game_rect": {"left": 320, "top": 0, "width": 320, "height": 540}, "game_resolution": {"w": 720, "h": 1280}},
            {"action": "screenshot", "screenshot_name": "done"},
        ]
        result = _resolve_steps(steps, self._DEFAULT_RECT, self._DEFAULT_RES_W, self._DEFAULT_RES_H)

        assert len(result) == 3
        assert result[0].rect == self._DEFAULT_RECT
        assert result[0].res_w == 1280
        assert result[1].rect == GameRect(left=320, top=0, width=320, height=540)
        assert result[1].res_w == 720
        assert result[2].rect == self._DEFAULT_RECT

    def test_empty_steps(self):
        result = _resolve_steps([], self._DEFAULT_RECT, self._DEFAULT_RES_W, self._DEFAULT_RES_H)
        assert result == []


class TestLoadConfig:
    def _write_config(self, tmp_path: Path, config: dict) -> Path:
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def _base_config(self, **overrides) -> dict:
        cfg = {
            "game_rect": {"left": 0, "top": 0, "width": 960, "height": 540},
            "game_resolution": {"w": 1280, "h": 720},
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
        assert app.game_rect == GameRect(left=0, top=0, width=960, height=540)
        assert app.game_res_w == 1280
        assert app.game_res_h == 720
        assert len(app.actions) == 1
        assert app.actions[0].tap.action == "tap"

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

    def test_default_resolution(self, tmp_path: Path):
        config = self._base_config()
        del config["game_resolution"]
        app = load_config(self._write_config(tmp_path, config))
        assert app.game_res_w == 1280
        assert app.game_res_h == 720

    def test_no_screenshot_targets(self, tmp_path: Path):
        config = self._base_config()
        del config["screenshot_targets"]
        app = load_config(self._write_config(tmp_path, config))
        assert app.screenshot_targets == []

    def test_actions_carry_correct_rect(self, tmp_path: Path):
        rect = {"left": 100, "top": 50, "width": 800, "height": 450}
        config = self._base_config(
            game_rect=rect,
            steps=[
                {"action": "tap", "x": 640, "y": 360},
                {"action": "tap", "x": 320, "y": 180},
            ],
        )
        app = load_config(self._write_config(tmp_path, config))
        for ra in app.actions:
            assert ra.rect == GameRect(left=100, top=50, width=800, height=450)
            assert ra.res_w == 1280

    def test_defaults(self, tmp_path: Path):
        config = self._base_config()
        app = load_config(self._write_config(tmp_path, config))
        assert app.startup_wait_s == 2
        assert app.loop_delay_s == 2
        assert app.connect_retries == 5
        assert app.iterations == 0


class TestEndToEndMapping:
    """Integration: config load -> game_to_screen."""

    def test_tap_maps_correctly(self, tmp_path: Path):
        config = {
            "game_rect": {"left": 100, "top": 31, "width": 960, "height": 540},
            "game_resolution": {"w": 1280, "h": 720},
            "steps": [{"action": "tap", "x": 640, "y": 360}],
            "screenshot_targets": [],
        }
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        app = load_config(path)
        ra = app.actions[0]
        sx, sy = game_to_screen(ra.tap.x, ra.tap.y, ra.res_w, ra.res_h, ra.rect)
        assert sx == 100 + 480
        assert sy == 31 + 270
