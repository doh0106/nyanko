from __future__ import annotations

import json
from pathlib import Path

import pytest

from macro_converter import (
    _extract_operations,
    _parse_operations,
    convert_macro_file,
    convert_macro_folder,
)


class TestExtractOperations:
    def test_flat_operations(self):
        raw = {
            "operations": [
                {"operationId": "PutMultiTouch", "timing": 100},
                {"operationId": "PutMultiTouch", "timing": 200},
            ]
        }
        ops = _extract_operations(raw)
        assert len(ops) == 2
        assert ops[0]["timing"] == 100

    def test_merged_records_flatten(self):
        raw = {
            "mergedRecords": [
                {
                    "timing": 1000,
                    "operations": [
                        {"operationId": "PutMultiTouch", "timing": 0},
                        {"operationId": "PutMultiTouch", "timing": 500},
                    ],
                },
                {
                    "timing": 3000,
                    "operations": [
                        {"operationId": "PutMultiTouch", "timing": 100},
                    ],
                },
            ]
        }
        ops = _extract_operations(raw)
        assert len(ops) == 3
        assert ops[0]["timing"] == 1000  # 1000 + 0
        assert ops[1]["timing"] == 1500  # 1000 + 500
        assert ops[2]["timing"] == 3100  # 3000 + 100

    def test_empty_returns_empty(self):
        assert _extract_operations({}) == []

    def test_operations_takes_priority_over_merged(self):
        raw = {
            "operations": [{"operationId": "X", "timing": 50}],
            "mergedRecords": [{"timing": 0, "operations": [{"operationId": "Y"}]}],
        }
        ops = _extract_operations(raw)
        assert len(ops) == 1
        assert ops[0]["operationId"] == "X"


class TestParseOperations:
    def test_put_multi_touch_state1(self):
        ops = [
            {
                "operationId": "PutMultiTouch",
                "timing": 0,
                "points": [{"state": 1, "x": 100, "y": 200}],
            }
        ]
        result = _parse_operations(ops)
        assert len(result) == 1
        assert result[0]["action"] == "tap"
        assert result[0]["x"] == 100
        assert result[0]["y"] == 200

    def test_put_multi_touch_state0_ignored(self):
        ops = [
            {
                "operationId": "PutMultiTouch",
                "timing": 0,
                "points": [{"state": 0, "x": 100, "y": 200}],
            }
        ]
        result = _parse_operations(ops)
        assert len(result) == 0

    def test_put_multi_touch_no_points_ignored(self):
        ops = [{"operationId": "PutMultiTouch", "timing": 0, "points": []}]
        result = _parse_operations(ops)
        assert len(result) == 0

    def test_ime_clipboard(self):
        ops = [
            {"operationId": "ImeClipboard", "timing": 0, "text": "hello"}
        ]
        result = _parse_operations(ops)
        assert len(result) == 1
        assert result[0]["action"] == "clipboard"
        assert result[0]["text"] == "hello"

    def test_android_app_switch(self):
        ops = [{"operationId": "AndroidAppSwitch", "timing": 0}]
        result = _parse_operations(ops)
        assert len(result) == 1
        assert result[0]["action"] == "app_switch"

    def test_unknown_operation_ignored(self):
        ops = [{"operationId": "SomeUnknown", "timing": 0}]
        result = _parse_operations(ops)
        assert len(result) == 0

    def test_timing_cumulation(self):
        ops = [
            {
                "operationId": "PutMultiTouch",
                "timing": 1000,
                "points": [{"state": 1, "x": 10, "y": 20}],
            },
            {
                "operationId": "PutMultiTouch",
                "timing": 3500,
                "points": [{"state": 1, "x": 30, "y": 40}],
            },
        ]
        result = _parse_operations(ops)
        assert result[0]["wait_before_s"] == 1.0
        assert result[1]["wait_before_s"] == 2.5

    def test_scaling(self):
        ops = [
            {
                "operationId": "PutMultiTouch",
                "timing": 0,
                "points": [{"state": 1, "x": 100, "y": 200}],
            }
        ]
        result = _parse_operations(ops, scale_x=0.5, scale_y=2.0)
        assert result[0]["x"] == 50
        assert result[0]["y"] == 400

    def test_default_delay(self):
        ops = [
            {
                "operationId": "PutMultiTouch",
                "timing": 0,
                "points": [{"state": 1, "x": 0, "y": 0}],
            }
        ]
        result = _parse_operations(ops, default_delay_s=0.7)
        assert result[0]["delay_after_s"] == 0.7

    def test_sort_by_timing(self):
        ops = [
            {
                "operationId": "PutMultiTouch",
                "timing": 2000,
                "points": [{"state": 1, "x": 2, "y": 0}],
            },
            {
                "operationId": "PutMultiTouch",
                "timing": 500,
                "points": [{"state": 1, "x": 1, "y": 0}],
            },
        ]
        result = _parse_operations(ops)
        assert result[0]["x"] == 1
        assert result[1]["x"] == 2


class TestConvertMacroFile:
    def test_flat_file(self, tmp_path: Path):
        macro = {
            "operations": [
                {
                    "operationId": "PutMultiTouch",
                    "timing": 0,
                    "points": [{"state": 1, "x": 50, "y": 60}],
                },
                {
                    "operationId": "ImeClipboard",
                    "timing": 500,
                    "text": "test_text",
                },
            ]
        }
        path = tmp_path / "macro.json"
        path.write_text(json.dumps(macro), encoding="utf-8")

        result = convert_macro_file(path)
        assert len(result) == 2
        assert result[0]["action"] == "tap"
        assert result[1]["action"] == "clipboard"

    def test_merged_records_file(self, tmp_path: Path):
        macro = {
            "mergedRecords": [
                {
                    "timing": 0,
                    "operations": [
                        {
                            "operationId": "PutMultiTouch",
                            "timing": 100,
                            "points": [{"state": 1, "x": 10, "y": 20}],
                        }
                    ],
                },
                {
                    "timing": 2000,
                    "operations": [
                        {
                            "operationId": "PutMultiTouch",
                            "timing": 0,
                            "points": [{"state": 1, "x": 30, "y": 40}],
                        }
                    ],
                },
            ]
        }
        path = tmp_path / "macro.json"
        path.write_text(json.dumps(macro), encoding="utf-8")

        result = convert_macro_file(path)
        assert len(result) == 2
        assert result[0]["wait_before_s"] == 0.1
        assert result[1]["wait_before_s"] == 1.9


class TestConvertMacroFolder:
    def test_batch_convert(self, tmp_path: Path):
        input_dir = tmp_path / "macros"
        output_dir = tmp_path / "modules"
        input_dir.mkdir()

        macro_a = {
            "operations": [
                {
                    "operationId": "PutMultiTouch",
                    "timing": 0,
                    "points": [{"state": 1, "x": 1, "y": 2}],
                }
            ]
        }
        macro_b = {
            "operations": [
                {
                    "operationId": "AndroidAppSwitch",
                    "timing": 0,
                }
            ]
        }
        (input_dir / "tap_macro.txt").write_text(json.dumps(macro_a), encoding="utf-8")
        (input_dir / "switch_macro.json").write_text(json.dumps(macro_b), encoding="utf-8")

        created = convert_macro_folder(input_dir, output_dir)
        assert len(created) == 2
        assert (output_dir / "tap_macro.json").exists()
        assert (output_dir / "switch_macro.json").exists()

        loaded = json.loads((output_dir / "tap_macro.json").read_text(encoding="utf-8"))
        assert loaded[0]["action"] == "tap"

    def test_empty_folder(self, tmp_path: Path):
        input_dir = tmp_path / "empty"
        output_dir = tmp_path / "out"
        input_dir.mkdir()

        created = convert_macro_folder(input_dir, output_dir)
        assert created == []
