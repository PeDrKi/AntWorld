# -*- coding: utf-8 -*-
"""
fonts.py: nap font TrueType RIENG (dong goi san trong assets/fonts/) thay
vi dung pygame.font.SysFont("arial"/"consolas", ...).

TAI SAO CAN FILE NAY (xem thao luan chi tiet trong README.md):
    pygame.font.SysFont(...) khong doc file font truc tiep - no DI TIM
    mot font co dung TEN do tren may dang chay luc do. Cach nay co 2 van
    de:
      1) Khong dam bao may nao cung co dung font ten "Arial"/"Consolas"
         cai san, nen chu co the hien thi khac nhau tren tung may.
      2) Khi dong goi thanh .exe bang PyInstaller, co che do-font-he-thong
         nay hay KHONG hoat dong on dinh trong moi truong da dong goi -
         neu khong tim thay font, pygame am tham roi ve font mac dinh
         tich hop san (khong co dau tieng Viet) -> chu co dau bi vo/mat
         dau/hien o vuong.

Giai phap: dung 2 file .ttf ma nguon mo, co san day du dau tieng Viet,
dong goi ngay trong project (assets/fonts/), roi load truc tiep bang
pygame.font.Font(duong_dan_file, size). Cach nay cho ket qua GIONG HET
NHAU tren moi may, ke ca ban .exe da dong goi (xem AntWorld2D.spec, phan
da them assets/fonts/*.ttf vao datas).

    - Be Vietnam Pro (Regular/Bold): chu thuong, dung cho hau het text.
    - JetBrains Mono: chu deu nhau (monospace), dung cho HUD/so lieu can
      thang hang cot.
    Ca hai deu la font mien phi, giay phep SIL Open Font License 1.1.
"""
import os
import sys

import pygame

# Cung 1 kieu xu ly duong dan nhu ASSETS_DIR trong game_state.py: khi
# chay binh thuong tu source (src/antworld/fonts.py), assets/ nam o THU
# MUC GOC du an (2 cap tren src/antworld/); khi da dong goi thanh .exe
# (--onefile) thi file duoc giai nen tam vao sys._MEIPASS (khong doi, vi
# PyInstaller gop 'assets' vao thang goc cua ban dong goi bat ke source
# layout - xem packaging/AntWorld2D.spec).
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _FONTS_DIR = os.path.join(sys._MEIPASS, "assets", "fonts")
else:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _FONTS_DIR = os.path.join(_PROJECT_ROOT, "assets", "fonts")

_REGULAR_PATH = os.path.join(_FONTS_DIR, "BeVietnamPro-Regular.ttf")
_BOLD_PATH = os.path.join(_FONTS_DIR, "BeVietnamPro-Bold.ttf")
_MONO_PATH = os.path.join(_FONTS_DIR, "JetBrainsMono-Regular.ttf")

_cache = {}


def _load(path, size):
    key = (path, size)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    if not pygame.font.get_init():
        pygame.font.init()
    try:
        f = pygame.font.Font(path, size)
    except Exception as e:
        # Phong khi thieu file font (vi du quen copy assets/fonts/ khi
        # dong goi .exe) - roi ve font mac dinh cua pygame de game van
        # chay duoc thay vi crash, du tieng Viet co the bi mat dau trong
        # truong hop nay. In canh bao ra console de de phat hien loi.
        print(f'[fonts.py] KHONG doc duoc font "{path}": {e} '
              f'- dang dung font du phong (co the bi mat dau tieng Viet).')
        f = pygame.font.SysFont(None, size)
    _cache[key] = f
    return f


def get_font(size, bold=False):
    """Font chu thuong (Be Vietnam Pro) - dung cho hau het text trong game
    va cong cu (tieu de, nhan nut, thong bao...)."""
    return _load(_BOLD_PATH if bold else _REGULAR_PATH, size)


def get_mono_font(size):
    """Font chu deu nhau (JetBrains Mono) - dung cho HUD/bang so lieu can
    thang hang, giong vai tro cua 'consolas' truoc day."""
    return _load(_MONO_PATH, size)
