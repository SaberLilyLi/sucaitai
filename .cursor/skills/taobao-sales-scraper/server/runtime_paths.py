# -*- coding: utf-8 -*-
"""开发态 / PyInstaller 冻结态路径解析。"""
from __future__ import annotations

import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SERVER_DIR.parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    """可写根目录：冻结时为 exe 所在目录，开发时为 Skill 包根。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return SKILL_ROOT


def data_dir() -> Path:
    return app_root() / "data"


def env_path() -> Path:
    """冻结：exe 旁 .env；开发：server/.env。"""
    if is_frozen():
        return app_root() / ".env"
    return SERVER_DIR / ".env"


def frontend_dist() -> Path:
    """前端构建产物：冻结在 _MEIPASS/frontend_dist，开发在 frontend/dist。"""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / "frontend_dist"
    return SKILL_ROOT / "frontend" / "dist"
