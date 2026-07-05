# -*- mode: python ; coding: utf-8 -*-

# Skip PyInstaller's per-binary ad-hoc signing for the bundled Flet.app.
# Its inner Flet binary has framework dependencies (flutter_secure_storage_darwin.framework)
# that codesign refuses to sign as a bare binary. The final .app is signed post-build
# with `codesign --deep`, which handles the nested bundle correctly.
from PyInstaller.utils import osx as _pyi_osx
_orig_sign_binary = _pyi_osx.sign_binary
def _sign_binary_skip_flet(filename, *args, **kwargs):
    if 'Flet.app' in str(filename):
        return
    return _orig_sign_binary(filename, *args, **kwargs)
_pyi_osx.sign_binary = _sign_binary_skip_flet


a = Analysis(
    ['run_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('resources/exiftool', 'resources/exiftool')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MediaMap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='MediaMap.app',
    icon=None,
    bundle_identifier='eu.marcel-jan.mediamap',
)
