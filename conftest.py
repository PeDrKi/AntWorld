# -*- coding: utf-8 -*-
"""Cho phep import package `antworld` (nam trong src/) va cong cu trong
tools/ ma khong can cai dat du an bang pip -e .

pytest tu dong nap file conftest.py nay o thu muc goc truoc khi chay bat
ky test nao. run_tests.py (dung unittest) cung tu them src/ vao sys.path
theo cach tuong tu, xem file do.
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.join(_PROJECT_ROOT, "src"), os.path.join(_PROJECT_ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
