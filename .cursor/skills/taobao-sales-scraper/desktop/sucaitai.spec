# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir for Sucaitai desktop package."""
from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()
SKILL_ROOT = SPEC_DIR.parent
SERVER = SKILL_ROOT / "server"
FRONTEND_DIST = SKILL_ROOT / "frontend" / "dist"
APP_NAME = "\u7d20\u6750\u53f0"  # 素材台

block_cipher = None

a = Analysis(
    [str(SERVER / "desktop_main.py")],
    pathex=[str(SERVER)],
    binaries=[],
    datas=[
        (str(FRONTEND_DIST), "frontend_dist"),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "multipart",
        "app",
        "store",
        "search_runner",
        "detail_runner",
        "intent_parser",
        "onebound_client",
        "runtime_paths",
        "PIL",
        "openpyxl",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "selenium",
        "chromedriver",
        "tkinter",
        "matplotlib",
        "pandas",
        "numpy",
        "scipy",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
