@echo off
REM Dong goi Ant World 2D thanh 1 file .exe doc lap (app Windows that su,
REM co icon rieng, khong hien cua so console den).
REM
REM Co the chay file nay tu BAT KY DAU (kem ca bang cach double-click
REM trong Explorer) - no tu dong chuyen ve thu muc goc du an (1 cap tren
REM packaging/, noi co main.py, requirements.txt) truoc khi lam gi khac.
cd /d "%~dp0\.."

echo === Cai dat thu vien can thiet ===
pip install -r requirements.txt
pip install -r requirements-build.txt

echo.
echo === Dong goi bang PyInstaller ===
pyinstaller packaging\AntWorld2D.spec --noconfirm

echo.
echo === XONG! ===
echo File .exe nam tai: dist\AntWorld2D\AntWorld2D.exe
echo Co the copy ca thu muc dist\AntWorld2D\ sang may khac de chay (khong
echo can cai Python tren may do).
pause
