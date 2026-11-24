# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules

if sys.platform == 'darwin':
    hiddenimports = ['webview.platforms.cocoa']
elif sys.platform == 'win32':
    hiddenimports = ['webview.platforms.edgechromium']
else:
    hiddenimports = []

hiddenimports += collect_submodules('timelog')


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('timelog/desktop/ui', 'timelog/desktop/ui'), ('timelog/server/otj_guide.md', 'timelog/server')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['playwright'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='timelog-mcp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=sys.platform != 'darwin',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['timelog/desktop/ui/icons/timelog.ico'] if sys.platform == 'win32' else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='timelog-mcp',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='TimelogMCP.app',
        icon=None,
        bundle_identifier='uk.ac.qmul.timelog-mcp',
    )
