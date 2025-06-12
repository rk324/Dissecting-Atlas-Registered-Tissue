# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['./src/main/main.py'],
    pathex=['./src/main'],
    binaries=[],
    datas=[('./src/main/constants.py', '.'), ('./src/main/images.py', '.'), ('./src/main/pages.py', '.'), ('./src/main/STalign.py', '.'), ('./src/main/utils.py', '.'), ('./atlases', 'atlases/'), ('./resources', 'resources/'), ('./VisuAlign-v0_9', 'VisuAlign-v0_9/')],
    hiddenimports=['scipy', 'scipy._lib.array_api_compat.numpy.fft', 'jaraco', 'jaraco.text', 'PIL._tkinter_finder','skimage.segmentation'],
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
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='dart',
)
