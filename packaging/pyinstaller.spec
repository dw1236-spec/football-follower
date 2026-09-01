# -*- mode: python ; coding: utf-8 -*-
"""Shared PyInstaller spec for the NFL Fantasy Draft Analyzer.

PyInstaller cannot cross-compile: run this spec on each target OS
(Windows 10+, macOS 12+, Ubuntu 20.04+) via the matching build_*
script in this folder to produce that OS's standalone build.
"""
import sys
from pathlib import Path

project_root = Path(SPECPATH).resolve().parent  # noqa: F821 - provided by PyInstaller

a = Analysis(  # noqa: F821
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(project_root / "assets" / "sample_data_template.xlsx"), "assets")],
    hiddenimports=[
        "sklearn.utils._typedefs",
        "sklearn.utils._heap",
        "sklearn.utils._sorting",
        "sklearn.utils._vector_sentinel",
        "sklearn.neighbors._partition_nodes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NFLDraftAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=sys.platform == "darwin",
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NFLDraftAnalyzer",
)

if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name="NFLDraftAnalyzer.app",
        bundle_identifier="com.football-follower.nfldraftanalyzer",
    )
