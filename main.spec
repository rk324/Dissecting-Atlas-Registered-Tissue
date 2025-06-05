# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['/home/rishi/kebschull/LDM-brain-region-excision/src/main/main.py'],
    pathex=['/home/rishi/kebschull/LDM-brain-region-excision/src/main'],
    binaries=[],
    datas=[('/home/rishi/kebschull/LDM-brain-region-excision/src/main/constants.py', '.'), ('/home/rishi/kebschull/LDM-brain-region-excision/src/main/images.py', '.'), ('/home/rishi/kebschull/LDM-brain-region-excision/src/main/pages.py', '.'), ('/home/rishi/kebschull/LDM-brain-region-excision/src/main/STalign.py', '.'), ('/home/rishi/kebschull/LDM-brain-region-excision/src/main/utils.py', '.'), ('/home/rishi/kebschull/LDM-brain-region-excision/atlases', 'atlases/'), ('/home/rishi/kebschull/LDM-brain-region-excision/resources', 'resources/'), ('/home/rishi/kebschull/LDM-brain-region-excision/VisuAlign-v0_9', 'VisuAlign-v0_9/')],
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
