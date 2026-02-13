from __future__ import annotations

import json
from pathlib import Path

import pytest

from multi_ld_clicker import (
    TapAction,
    _apply_scaling,
    _parse_tap,
    _resolve_steps,
    load_config,
)


class TestParseTap:
    def test_tap_defaults(self):
        tap = _parse_tap({})
        assert tap.action == "tap"
        assert tap.x == 0
        assert tap.y == 0
        assert tap.delay_after_s == 0.5

    def test_tap_with_all_fields(self):
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
        assert tap.app_package == "com.test"


class TestApplyScaling:
    def test_scales_x_and_y(self):
        taps = [{"action": "tap", "x": 100, "y": 200}]
        result = _apply_scaling(taps, 0.5, 2.0)
        assert result[0]["x"] == 50
        assert result[0]["y"] == 400

    def test_no_x_y_fields(self):
        taps = [{"action": "app_switch"}]
        result = _apply_scaling(taps, 0.5, 0.5)
        assert "x" not in result[0]

    def test_does_not_mutate_original(self):
        original = [{"action": "tap", "x": 100, "y": 200}]
        _apply_scaling(original, 0.5, 0.5)
        assert original[0]["x"] == 100


class TestResolveSteps:
    def test_inline_action(self, tmp_path: Path):
        steps = [{"action": "tap", "x": 10, "y": 20}]
        result = _resolve_steps(steps, tmp_path)
        assert len(result) == 1
        assert result[0].action == "tap"
        assert result[0].x == 10

    def test_module_reference(self, tmp_path: Path):
        module_data = [
            {"action": "tap", "x": 50, "y": 60, "wait_before_s": 0.1, "delay_after_s": 0.2}
        ]
        (tmp_path / "tutorial.json").write_text(
            json.dumps(module_data), encoding="utf-8"
        )

        steps = [{"module": "tutorial"}]
        result = _resolve_steps(steps, tmp_path)
        assert len(result) == 1
        assert result[0].x == 50
        assert result[0].y == 60

    def test_module_with_scaling(self, tmp_path: Path):
        module_data = [
            {"action": "tap", "x": 100, "y": 200, "wait_before_s": 0.0, "delay_after_s": 0.2}
        ]
        (tmp_path / "gacha.json").write_text(
            json.dumps(module_data), encoding="utf-8"
        )

        steps = [{"module": "gacha", "scale_x": 0.5, "scale_y": 0.5}]
        result = _resolve_steps(steps, tmp_path)
        assert result[0].x == 50
        assert result[0].y == 100

    def test_mixed_steps(self, tmp_path: Path):
        module_data = [
            {"action": "tap", "x": 10, "y": 20, "wait_before_s": 0.0, "delay_after_s": 0.2}
        ]
        (tmp_path / "skip.json").write_text(
            json.dumps(module_data), encoding="utf-8"
        )

        steps = [
            {"action": "start_app", "app_package": "com.test", "delay_after_s": 1.0},
            {"module": "skip"},
            {"action": "screenshot", "screenshot_name": "done"},
        ]
        result = _resolve_steps(steps, tmp_path)
        assert len(result) == 3
        assert result[0].action == "start_app"
        assert result[1].action == "tap"
        assert result[2].action == "screenshot"

    def test_missing_module_raises(self, tmp_path: Path):
        steps = [{"module": "nonexistent"}]
        with pytest.raises(FileNotFoundError, match="Module not found"):
            _resolve_steps(steps, tmp_path)


class TestLoadConfig:
    def _base_instance(self, **overrides) -> dict:
        inst = {
            "name": "test",
            "adb_serial": "127.0.0.1:5555",
            "taps": [],
        }
        inst.update(overrides)
        return inst

    def test_taps_mode(self, tmp_path: Path):
        config = {
            "instances": [
                self._base_instance(taps=[
                    {"action": "tap", "x": 10, "y": 20}
                ])
            ]
        }
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        app = load_config(path)
        assert len(app.instances) == 1
        assert app.instances[0].taps[0].action == "tap"

    def test_steps_mode(self, tmp_path: Path):
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        module_data = [{"action": "tap", "x": 5, "y": 6, "wait_before_s": 0.0, "delay_after_s": 0.2}]
        (modules_dir / "m1.json").write_text(json.dumps(module_data), encoding="utf-8")

        inst = self._base_instance()
        del inst["taps"]
        inst["steps"] = [{"module": "m1"}]

        config = {"modules_dir": str(modules_dir), "instances": [inst]}
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        app = load_config(path)
        assert len(app.instances[0].taps) == 1
        assert app.instances[0].taps[0].x == 5

    def test_taps_and_steps_raises(self, tmp_path: Path):
        inst = self._base_instance(
            taps=[{"action": "tap", "x": 1, "y": 2}],
            steps=[{"action": "tap", "x": 3, "y": 4}],
        )
        config = {"instances": [inst]}
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        with pytest.raises(ValueError, match="cannot use both"):
            load_config(path)

    def test_empty_taps_ok(self, tmp_path: Path):
        inst = self._base_instance()
        del inst["taps"]
        config = {"instances": [inst]}
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        app = load_config(path)
        assert app.instances[0].taps == []

    def test_modules_dir_default(self, tmp_path: Path):
        config = {"instances": [self._base_instance()]}
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        app = load_config(path)
        assert app.modules_dir == Path("modules")

    def test_backward_compatible_with_existing_config(self, tmp_path: Path):
        """Old config format with only taps should still work."""
        config = {
            "log_dir": "logs",
            "iterations": 5,
            "instances": [
                {
                    "name": "ld-1",
                    "adb_serial": "127.0.0.1:5555",
                    "enabled": True,
                    "startup_wait_s": 3,
                    "loop_delay_s": 2,
                    "screenshot_every_loops": 0,
                    "taps": [
                        {"action": "stop_app", "app_package": "com.example", "delay_after_s": 0.3},
                        {"action": "tap", "x": 100, "y": 200, "delay_after_s": 1.0},
                    ],
                    "connect_retries": 8,
                    "connect_retry_delay_s": 2.0,
                }
            ],
        }
        path = tmp_path / "config.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        app = load_config(path)
        assert app.iterations == 5
        assert len(app.instances[0].taps) == 2
        assert app.instances[0].taps[0].action == "stop_app"
        assert app.instances[0].taps[1].x == 100
