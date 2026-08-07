@echo off
REM Dong goi Ant World 2D thanh 1 file .exe doc lap (app Windows that su,
REM co icon rieng, khong hien cua so console den).
REM Chay file nay tu thu muc goc cua du an (noi co main.py).

echo === Cai dat thu vien can thiet ===
pip install -r requirements.txt
pip install -r requirements-build.txt

echo.
echo === Dong goi bang PyInstaller ===
pyinstaller AntWorld2D.spec --noconfirm

echo.
echo === XONG! ===
echo File .exe nam tai: dist\AntWorld2D\AntWorld2D.exe
echo Co the copy ca thu muc dist\AntWorld2D\ sang may khac de chay (khong
echo can cai Python tren may do).
pause
