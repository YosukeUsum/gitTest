#!/usr/bin/env python3
"""Tetris CLI エントリーポイント。

実行: python main.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tetris_cli.ui_curses import main  # noqa: E402

if __name__ == "__main__":
    main()
