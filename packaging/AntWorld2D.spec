# PyInstaller spec file - đóng gói Ant World 2D thành 1 file .exe độc lập
# chạy như 1 app Windows thật sự (icon riêng, không hiện cửa sổ console
# đen, có sẵn trên Desktop/Start Menu, không cần cài Python để chạy).
#
# File này nằm trong packaging/ (không phải thư mục gốc dự án) - mọi
# đường dẫn bên dưới đều viết TƯƠNG ĐỐI so với packaging/, tức lùi 1 cấp
# (..) để về thư mục gốc, nơi có main.py, src/, assets/.
#
# Cách dùng: chạy build_exe.bat trong CÙNG thư mục này (nó tự cd về thư
# mục gốc dự án trước khi gọi pyinstaller - xem file đó), hoặc chạy thủ
# công TỪ THƯ MỤC GỐC dự án:
#     pyinstaller packaging/AntWorld2D.spec --noconfirm
# File .exe kết quả nằm trong dist/AntWorld2D/AntWorld2D.exe (dist/ được
# tạo ở thư mục hiện hành lúc gọi lệnh, tức thư mục gốc dự án).

import os

_SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
_PROJECT_ROOT = os.path.dirname(_SPEC_DIR)

block_cipher = None

a = Analysis(
    [os.path.join(_PROJECT_ROOT, 'main.py')],
    pathex=[os.path.join(_PROJECT_ROOT, 'src')],
    binaries=[],
    # Gói kèm icon.png/icon.ico + toàn bộ assets/fonts/*.ttf vào bản build
    # (bắt buộc phải có fonts/ ở đây, không thì chữ tiếng Việt sẽ mất dấu
    # trong bản .exe - xem giải thích trong fonts.py).
    datas=[(os.path.join(_PROJECT_ROOT, 'assets'), 'assets')],
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
    icon=os.path.join(_PROJECT_ROOT, 'assets', 'icon.ico'),  # icon taskbar + file .exe
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
