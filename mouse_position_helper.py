#!/usr/bin/env python3
"""Simple helper to capture current mouse cursor coordinates on desktop.

Use when you want to estimate tap points quickly on Windows.
Press Enter to record current position, type q then Enter to quit.
"""

from __future__ import annotations

import tkinter as tk


def get_pointer_xy() -> tuple[int, int]:
    root = tk.Tk()
    root.withdraw()
    x, y = root.winfo_pointerxy()
    root.destroy()
    return x, y


def main() -> int:
    print("[Mouse Position Helper]")
    print("- Enter: capture current cursor position")
    print("- q + Enter: quit")

    count = 0
    while True:
        cmd = input("> ").strip().lower()
        if cmd == "q":
            break
        x, y = get_pointer_xy()
        count += 1
        print(f"#{count}: x={x}, y={y}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
