# PyInstaller spec file - đóng gói Ant World 2D thành 1 file .exe độc lập
# chạy như 1 app Windows thật sự (icon riêng, không hiện cửa sổ console
# đen, có sẵn trên Desktop/Start Menu, không cần cài Python để chạy).
#
# Cách dùng (trên Windows, đã cài Python + pip install -r requirements.txt
# và requirements-build.txt):
#     pyinstaller AntWorld2D.spec
# File .exe kết quả nằm trong dist/AntWorld2D/AntWorld2D.exe

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],   # gói kèm icon.png/icon.ico vào bản build
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='AntWorld2D',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # KHÔNG hiện cửa sổ console đen - chạy như app thật
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',  # icon taskbar + file .exe
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AntWorld2D',
)
