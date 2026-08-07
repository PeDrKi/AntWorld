# -*- coding: utf-8 -*-
"""Test cho fonts.py - dung de bat SOM neu file .ttf bi thieu/hong, thay
vi phai doi den luc chay game/dong goi .exe moi phat hien chu tieng Viet
bi mat dau (chinh la loi da sua truoc do)."""
import os
import unittest

import pygame

from antworld import fonts


class TestFontFiles(unittest.TestCase):
    def test_font_files_exist_on_disk(self):
        for path in (fonts._REGULAR_PATH, fonts._BOLD_PATH, fonts._MONO_PATH):
            self.assertTrue(
                os.path.isfile(path),
                f"Thieu file font: {path} - kiem tra lai assets/fonts/ "
                f"(va neu dang dong goi .exe, kiem tra datas trong .spec)."
            )


class TestFontLoading(unittest.TestCase):
    def test_get_font_returns_font_object(self):
        f = fonts.get_font(16)
        self.assertIsInstance(f, pygame.font.Font)

    def test_get_font_bold_variant(self):
        f = fonts.get_font(16, bold=True)
        self.assertIsInstance(f, pygame.font.Font)

    def test_get_mono_font_returns_font_object(self):
        f = fonts.get_mono_font(14)
        self.assertIsInstance(f, pygame.font.Font)

    def test_same_size_returns_cached_same_object(self):
        f1 = fonts.get_font(18)
        f2 = fonts.get_font(18)
        self.assertIs(f1, f2, "get_font(18) hai lan phai tra ve CUNG 1 "
                               "object da cache, khong load lai file moi "
                               "lan goi (ton hieu nang).")

    def test_render_vietnamese_diacritics_does_not_crash(self):
        f = fonts.get_font(20)
        sample = "Tầng 1: Đường hầm - Kiến chúa đang đẻ trứng, ướt, ểnh"
        surf = f.render(sample, True, (255, 255, 255))
        # chu co dau chac chan rong hon 0 - neu font thieu glyph, pygame
        # van khong crash nhung day la check "co ve gi do duoc ve ra"
        self.assertGreater(surf.get_width(), 0)
        self.assertGreater(surf.get_height(), 0)


if __name__ == "__main__":
    unittest.main()
