# -*- coding: utf-8 -*-
"""Ant World 2D - launcher o thu muc goc du an.

Du an dung "src layout": toan bo code game nam trong package
src/antworld/ (xem README.md - muc "Cau truc du an"). File nay chi lam 1
viec duy nhat: dam bao src/ nam trong sys.path roi goi vao
antworld.__main__.main() - giup lenh quen thuoc

    python main.py

tiep tuc chay dung nhu truoc, ke ca khi dong goi bang PyInstaller (xem
packaging/AntWorld2D.spec, entry point tro thang vao file nay).
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(_PROJECT_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from antworld.__main__ import main

if __name__ == "__main__":
    main()
