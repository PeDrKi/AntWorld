# -*- coding: utf-8 -*-
"""Chay toan bo test tu dong cua du an bang 1 lenh:

    python run_tests.py

(tuong duong `python -m unittest discover -s tests -v`, chi la go ngan
gon hon va khong can nho cu phap discover).
"""
import sys
import unittest

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir="tests")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
