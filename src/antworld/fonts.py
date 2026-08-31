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


# ---------------------------------------------------------------------
# CACHE KET QUA font.render() - TOI UU HIEU NANG
# ---------------------------------------------------------------------
# pygame.font.Font.render() phai RASTERIZE tung ky tu thanh pixel moi lan
# goi - khong he re, nhung HUD/toolbar goi lai NHIEU LAN MOI KHUNG HINH
# gan nhu CUNG 1 CHUOI CHU (nhan tinh "Dan so", "Linh", ten nut, tieu de
# panel...) - do thuc te (xem profile_game.py) cho thay draw_hud mot minh
# da goi .render() hang chuc lan/khung hinh, chiem ti le dang ke thoi gian
# ve moi frame o toc do 60 FPS.
#
# render_cached(): tra ve THANG Surface DA RENDER TRUOC DO neu cung (font,
# text, color) da tung goi qua - chi rasterize LAI khi CHUOI CHU THAY DOI
# (vd so lieu tang/giam). Dung dict thuong (khong phai functools.lru_cache)
# vi key co chua doi tuong Font (kiem tra hashable qua id sau).
#
# CANH BAO AN TOAN: KHONG duoc chinh sua (vd .fill(), blit len) Surface tra
# ve boi ham nay - vi cung 1 Surface duoc DUNG CHUNG (shared) cho nhieu noi
# goi. Chi duoc phep .blit() no LEN mot Surface khac (giong cach dung binh
# thuong 1 anh da render), khong duoc ve THEM len chinh no.
_render_cache = {}
_RENDER_CACHE_MAX = 4000  # tran an toan - qua nguong thi xoa sach de tranh
                           # phinh bo nho vo han (vd chuoi so dem thay doi
                           # lien tuc moi tick tao ra vo so key khac nhau)


def render_cached(font, text, color, antialias=False):
    """Nhu font.render(text, antialias, color) nhung co cache - xem giai
    thich day du o docstring module phia tren. `color` co the la tuple 3
    hoac 4 phan tu, deu hoat dong binh thuong (dung lam key thang).

    MAC DINH antialias=False (KHAC pygame goc luon mac dinh True) - de
    chu co CANH SAC/RANG CUA giong chu bitmap thay vi vien mo lam mem
    (feathering) - dong nhat voi phong cach PIXEL ART cua toan bo game
    (xem sprite_manager.py dung nearest-neighbor scale, khong smoothscale,
    cho cung ly do). KHONG doi sang font bitmap/pixel that su duoc vi 2
    font hien co (Be Vietnam Pro/JetBrains Mono) la 2 font DUY NHAT da
    kiem chung day du dau tieng Viet co san trong du an - da tim nhung
    khong co font pixel 8-bit nao ho tro day du bang chu cai + dau tieng
    Viet (a, a, a, e, e, o, o, u, u, d + day du 5 dau thanh) de thay the
    an toan; tat AA la each cai thien phong cach ma KHONG lam vo chu."""
    key = (id(font), text, color, antialias)
    img = _render_cache.get(key)
    if img is None:
        if len(_render_cache) >= _RENDER_CACHE_MAX:
            _render_cache.clear()  # rat hiem khi xay ra trong 1 van choi
                                    # binh thuong - chi phong ho truong hop
                                    # bat thuong (vd hien thi so ngau nhien
                                    # lien tuc khong lap lai)
        img = font.render(text, antialias, color)
        _render_cache[key] = img
    return img


# ---------------------------------------------------------------------
# CACHE SURFACE NEN MO MAU DAC (pygame.Surface(..., SRCALPHA) + fill())
# ---------------------------------------------------------------------
# Cung ly do nhu render_cached() o tren: nhieu noi trong hud.py cap phat 1
# Surface SRCALPHA MOI + fill() 1 mau co dinh MOI KHUNG HINH chi de lam
# nen mo phia sau 1 dong canh bao/nhan (kich thuoc + mau hau nhu KHONG DOI
# giua cac khung hinh lien tiep) - cache theo (kich thuoc, mau) tranh cap
# phat lai vo ich.
#
# CANH BAO AN TOAN: giong render_cached(), KHONG duoc ve/fill THEM len
# Surface tra ve - chi duoc .blit() no di noi khac.
_flat_surf_cache = {}
_FLAT_SURF_CACHE_MAX = 500  # nen mo thuong chi co vai chuc to hop
                             # (kich thuoc, mau) khac nhau trong ca game


def get_flat_alpha_surface(size, color):
    """Tra ve 1 Surface SRCALPHA kich thuoc `size`=(w,h) da fill() san mau
    `color` (RGBA) - dung cache, KHONG tao moi neu da co san cung key."""
    key = (size, color)
    surf = _flat_surf_cache.get(key)
    if surf is None:
        if len(_flat_surf_cache) >= _FLAT_SURF_CACHE_MAX:
            _flat_surf_cache.clear()
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill(color)
        _flat_surf_cache[key] = surf
    return surf
