# -*- coding: utf-8 -*-
"""Chay toan bo test tu dong cua du an bang 1 lenh:

    python run_tests.py

(tuong duong `python -m unittest discover -s tests -v`, chi la go ngan
gon hon va khong can nho cu phap discover).
"""
import os
import sys
import unittest

# Du an dung cau truc "src layout": package chinh nam trong src/antworld/,
# cong cu doc lap nam trong tools/. Them ca hai vao sys.path de cac test
# import duoc "antworld.xxx" va "pixel_editor" ma khong can cai dat package
# (xem conftest.py o cung thu muc de pytest cung lam dieu tuong tu).
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(_PROJECT_ROOT, "src"), os.path.join(_PROJECT_ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir="tests")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
