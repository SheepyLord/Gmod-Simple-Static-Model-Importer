# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\1peng\\Modding\\ipg\\!runtime_any_model_importer\\release\\pmx_static_importer_project\\gmod_addon', 'gmod_addon'), ('C:\\ProgramData\\miniforge3\\Library\\lib\\tcl8.6', '_tcl_data'), ('C:\\ProgramData\\miniforge3\\Library\\lib\\tk8.6', '_tk_data')]
binaries = [('C:\\ProgramData\\miniforge3\\Library\\bin\\tcl86t.dll', '.'), ('C:\\ProgramData\\miniforge3\\Library\\bin\\tk86t.dll', '.'), ('C:\\ProgramData\\miniforge3\\Library\\bin\\libcrypto-3-x64.dll', '.'), ('C:\\ProgramData\\miniforge3\\Library\\bin\\libssl-3-x64.dll', '.'), ('C:\\ProgramData\\miniforge3\\Library\\bin\\libexpat.dll', '.'), ('C:\\ProgramData\\miniforge3\\Library\\bin\\liblzma.dll', '.'), ('C:\\ProgramData\\miniforge3\\Library\\bin\\libbz2.dll', '.'), ('C:\\ProgramData\\miniforge3\\Library\\bin\\ffi-8.dll', '.'), ('C:\\Program Files\\7-Zip\\7z.exe', '.'), ('C:\\Program Files\\7-Zip\\7z.dll', '.')]
hiddenimports = ['tkinter', '_tkinter', 'PIL.ImageTk', 'trimesh', 'rarfile']
hiddenimports += collect_submodules('tkinter')
hiddenimports += collect_submodules('trimesh')
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['C:\\Users\\1peng\\Modding\\ipg\\!runtime_any_model_importer\\release\\pmx_static_importer_project\\importer_tool\\pyi_rth_tk_paths.py'],
    excludes=['matplotlib'],
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
    name='PMXStaticImporter',
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
