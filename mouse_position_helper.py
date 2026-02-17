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


def measure_game_rect() -> None:
    """Interactive measurement of game_rect (top-left + bottom-right corners)."""
    print("[game_rect measurement]")
    input("Move cursor to TOP-LEFT corner of the game area, then press Enter...")
    x1, y1 = get_pointer_xy()
    print(f"  #1: x={x1}, y={y1}")

    input("Move cursor to BOTTOM-RIGHT corner of the game area, then press Enter...")
    x2, y2 = get_pointer_xy()
    print(f"  #2: x={x2}, y={y2}")

    width = x2 - x1
    height = y2 - y1
    print(f'=> game_rect: {{"left": {x1}, "top": {y1}, "width": {width}, "height": {height}}}')


def main() -> int:
    print("[Mouse Position Helper]")
    print("- Enter: capture current cursor position")
    print("- r + Enter: measure game_rect (top-left & bottom-right)")
    print("- q + Enter: quit")

    count = 0
    while True:
        cmd = input("> ").strip().lower()
        if cmd == "q":
            break
        if cmd == "r":
            measure_game_rect()
            continue
        x, y = get_pointer_xy()
        count += 1
        print(f"#{count}: x={x}, y={y}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
