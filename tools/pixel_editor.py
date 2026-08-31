# -*- coding: utf-8 -*-
"""
AntWorld Pixel Studio - ban Python (Pygame)
=============================================
Ban chuyen the tu cong cu ve pixel art antworld_pixel_studio.html sang
mot ung dung Python doc lap, dung chung engine (pygame) voi game AntWorld
de khong phai them thu vien nao moi va xuat PNG tuong thich 100% voi
sprite_manager.py cua game (nen trong suot, dung ten file theo quy uoc).

CACH CHAY (tu thu muc goc du an):
    python tools/pixel_editor.py

PNG xuat ra se duoc luu vao:  assets/sprites/<ten_sprite>.png
(dung thu muc va dung quy uoc ten file ma sprite_manager.py dang doc)

PHIM TAT:
    B = but (pencil)      E = tay (eraser)
    G = do mau (fill)     I = hut mau (eyedropper)
    Ctrl+Z = hoan tac      Ctrl+Y = lam lai
"""
import os
import sys
import copy
import pygame

# Cong cu nay nam trong tools/, tach rieng khoi package game (src/antworld/)
# nhung dung chung fonts.py + sprite_data.py voi game de xuat PNG tuong
# thich 100%. Them src/ vao sys.path de import duoc antworld.* du chay
# truc tiep bang "python tools/pixel_editor.py" (khong can cai dat package).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.join(_PROJECT_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from antworld import fonts
from antworld.sprite_data import PALETTE_GROUPS, PRESET_SPRITES, DEFAULT_PIXELS

# ------------------------------------------------------------------
# Duong dan xuat file - dung dung thu muc assets/sprites/ o goc du an
# ma sprite_manager.py cua game AntWorld doc.
# ------------------------------------------------------------------
BASE_DIR = _PROJECT_ROOT
SPRITES_DIR = os.path.join(BASE_DIR, "assets", "sprites")

# ------------------------------------------------------------------
# Mau giao dien (giu tinh than dark/amber giong ban HTML goc)
# ------------------------------------------------------------------
COL_BG = (23, 19, 15)
COL_PANEL = (34, 27, 20)
COL_PANEL2 = (43, 34, 25)
COL_BORDER = (74, 58, 40)
COL_BORDER_SOFT = (58, 47, 34)
COL_TEXT = (236, 223, 200)
COL_TEXT_DIM = (169, 152, 126)
COL_ACCENT = (215, 120, 32)
COL_ACCENT2 = (230, 192, 90)
COL_DANGER = (192, 87, 74)
COL_GOOD = (127, 174, 94)
COL_CANVAS_BG = (32, 25, 15)

pygame.init()
pygame.display.set_caption("AntWorld Pixel Studio (Python)")

WIN_W, WIN_H = 1360, 860
screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
clock = pygame.time.Clock()

# Dung chung module fonts.py voi game (assets/fonts/*.ttf) thay vi
# SysFont - dam bao tool nay cung hien thi dung tieng Viet tren moi may,
# giong ly do da sua trong game_state.py.
font_small = fonts.get_font(13)
font_normal = fonts.get_font(15)
font_bold = fonts.get_font(15, bold=True)
font_title = fonts.get_font(20, bold=True)
font_mono = fonts.get_mono_font(12)


def draw_text(surf, text, pos, font, color=COL_TEXT, max_w=None):
    if max_w:
        # cat bot neu qua dai (khong wrap, chi de tranh trang ra ngoai)
        while font.size(text)[0] > max_w and len(text) > 1:
            text = text[:-1]
    img = font.render(text, True, color)
    surf.blit(img, pos)
    return img.get_width()


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(h, alpha=255):
    r, g, b = hex_to_rgb(h)
    return (r, g, b, alpha)


# ============================================================
# STATE
# ============================================================
class Sprite:
    """1 sprite = 1 hoặc NHIỀU khung hình (frame) cùng kích thước, dùng để
    dựng hoạt ảnh (đi bộ, vẫy càng...) - xem FRAME_* trong AppState và
    App.build_frame_strip(). Trước đây mỗi sprite chỉ có ĐÚNG 1 tấm pixel
    tĩnh duy nhất.

    `pixels` được giữ lại làm PROPERTY trỏ tới khung đang chọn
    (frames[frame_idx]) - để toàn bộ phần code còn lại của tool (vẽ, tô
    màu, đối xứng, undo/redo, xuất PNG...) vốn thao tác thẳng trên
    `sp.pixels` không cần sửa gì cả: chúng tự động "chỉ áp dụng lên khung
    đang mở", đúng như 1 công cụ animation cần hoạt động."""
    __slots__ = ("size", "frames", "frame_idx", "label")

    def __init__(self, size, label):
        self.size = size
        self.frames = [[None] * (size * size)]
        self.frame_idx = 0
        self.label = label

    @property
    def pixels(self):
        return self.frames[self.frame_idx]

    @pixels.setter
    def pixels(self, value):
        self.frames[self.frame_idx] = value

    @property
    def n_frames(self):
        return len(self.frames)

    def add_frame(self, copy_current=True):
        """Chèn 1 khung MỚI ngay SAU khung đang chọn, rồi chuyển sang
        khung mới đó. copy_current=True: nhân bản nội dung khung hiện tại
        (thường tiện hơn khi vẽ hoạt ảnh - chỉnh sửa nhỏ từ khung trước,
        thay vì vẽ lại từ đầu); False: khung trắng hoàn toàn."""
        blank_or_copy = self.frames[self.frame_idx][:] if copy_current else [None] * (self.size * self.size)
        self.frames.insert(self.frame_idx + 1, blank_or_copy)
        self.frame_idx += 1

    def delete_frame(self):
        """Xóa khung đang chọn - LUÔN giữ lại ít nhất 1 khung (trả về
        False, không làm gì, nếu đây là khung DUY NHẤT)."""
        if len(self.frames) <= 1:
            return False
        del self.frames[self.frame_idx]
        self.frame_idx = min(self.frame_idx, len(self.frames) - 1)
        return True

    def move_frame(self, delta):
        """Đổi chỗ khung đang chọn với khung liền kề (delta=-1 sang trái/
        delta=+1 sang phải) - dùng để sắp lại THỨ TỰ phát hoạt ảnh."""
        new_idx = self.frame_idx + delta
        if 0 <= new_idx < len(self.frames):
            self.frames[self.frame_idx], self.frames[new_idx] = self.frames[new_idx], self.frames[self.frame_idx]
            self.frame_idx = new_idx
            return True
        return False


class AppState:
    def __init__(self):
        self.sprites = {}
        self.order = []
        self.current = None
        self.tool = "pencil"
        self.color = "#d77820"
        self.color_rgb = list(hex_to_rgb("#d77820"))
        self.recent_colors = []  # hex, mới nhất ở đầu, tối đa 10, không trùng
        self.brush_size = 1      # 1..3, áp dụng cho bút/tẩy (không áp dụng
                                  # cho đổ màu/hút màu/đường thẳng/hcn)
        self.zoom = 20
        self.show_grid = True
        self.symmetry_h = False
        self.symmetry_v = False
        self.painting = False
        self.shape_start = None       # (x, y) lúc bắt đầu kéo đường thẳng/HCN
        self.shape_preview_end = None  # (x, y) hiện tại khi đang kéo (chỉ để xem trước)
        self.rect_filled = False      # công cụ HCN: viền hay đặc
        self.anim_playing = False
        self.anim_timer = 0
        self.anim_frame_idx = 0

        # --- Phát hoạt ảnh CÁC KHUNG HÌNH của CHÍNH sprite đang mở (khác
        # anim_playing ở trên - đó là lướt/đổi qua CÁC SPRITE KHÁC NHAU,
        # vd thợ<->thợ đang mang đồ, không phải các khung trong 1 sprite).
        # Xem App.build_frame_strip()/_update_frame_anim(). ---
        self.frame_anim_playing = False
        self.frame_anim_timer = 0.0
        self.frame_anim_idx = 0
        self.frame_fps = 6          # số khung/giây lúc phát xem trước - 6
                                     # khung/giây là tốc độ "đi bộ" dễ xem,
                                     # chỉnh được qua nút +/- (xem
                                     # App.change_frame_fps)
        self.onion_skin = True      # hiện MỜ khung TRƯỚC đó ngay dưới
                                     # khung đang vẽ - giúp canh đúng vị
                                     # trí từng chi tiết giữa 2 khung liên
                                     # tiếp (kỹ thuật "onion skinning" kinh
                                     # điển của mọi phần mềm vẽ hoạt ảnh)
        self.history = {}
        self.status = ""
        self.status_timer = 0

    def new_sprite(self, name, size, label=None):
        n, i = name, 2
        while n in self.sprites:
            n = f"{name}_{i}"
            i += 1
        self.sprites[n] = Sprite(size, label or n)
        self.history[n] = {"undo": [], "redo": []}
        self.order.append(n)
        return n

    def sp(self):
        return self.sprites[self.current]

    def toast(self, msg):
        self.status = msg
        self.status_timer = 160  # frames (~2.6s at 60fps)

    def push_history(self):
        """Lưu snapshot TOÀN BỘ danh sách khung + khung đang chọn (không
        chỉ mỗi `pixels` của khung hiện tại) - để Hoàn tác/Làm lại hoạt
        động ĐÚNG ngay cả khi giữa lúc đó người dùng có chuyển qua lại
        giữa các khung khác nhau."""
        h = self.history[self.current]
        sp = self.sp()
        h["undo"].append(([f[:] for f in sp.frames], sp.frame_idx))
        if len(h["undo"]) > 60:
            h["undo"].pop(0)
        h["redo"].clear()

    def undo(self):
        h = self.history[self.current]
        if not h["undo"]:
            return
        sp = self.sp()
        h["redo"].append(([f[:] for f in sp.frames], sp.frame_idx))
        sp.frames, sp.frame_idx = h["undo"].pop()

    def redo(self):
        h = self.history[self.current]
        if not h["redo"]:
            return
        sp = self.sp()
        h["undo"].append(([f[:] for f in sp.frames], sp.frame_idx))
        sp.frames, sp.frame_idx = h["redo"].pop()

    def remember_color(self, hexcolor):
        """Ghi mau vao danh sach 'vua dung', moi nhat len dau, khong
        trung lap, toi da 10 mau."""
        if not hexcolor:
            return
        if hexcolor in self.recent_colors:
            self.recent_colors.remove(hexcolor)
        self.recent_colors.insert(0, hexcolor)
        del self.recent_colors[10:]

    def _mirror_points(self, x, y, size):
        """Tra ve danh sach cac diem doi xung can ve cung, tuy theo
        doi xung ngang/doc dang bat. Luon bao gom (x,y) goc."""
        pts = {(x, y)}
        if self.symmetry_h:
            pts.add((size - 1 - x, y))
        if self.symmetry_v:
            pts.add((x, size - 1 - y))
        if self.symmetry_h and self.symmetry_v:
            pts.add((size - 1 - x, size - 1 - y))
        return pts

    def set_pixel(self, x, y, color):
        sp = self.sp()
        for px, py in self._mirror_points(x, y, sp.size):
            sp.pixels[py * sp.size + px] = color

    def paint_stamp(self, x, y, color):
        """Ve 1 'con dau' vuong kich thuoc brush_size x brush_size, tam
        tai (x,y) - dung cho but/tay khi brush_size > 1. brush_size=1
        thi hanh vi giong het set_pixel() truoc day."""
        sp = self.sp()
        half = self.brush_size // 2
        for oy in range(-half, self.brush_size - half):
            for ox in range(-half, self.brush_size - half):
                px, py = x + ox, y + oy
                if 0 <= px < sp.size and 0 <= py < sp.size:
                    self.set_pixel(px, py, color)

    def line_points(self, x0, y0, x1, y1):
        """Thuat toan Bresenham - tra ve danh sach (x,y) tao thanh 1
        duong thang tu (x0,y0) den (x1,y1), khong bo sot o nao."""
        points = []
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            points.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return points

    def rect_points(self, x0, y0, x1, y1):
        """Tra ve danh sach (x,y) cua 1 hinh chu nhat giua 2 goc
        (x0,y0)-(x1,y1) - dac neu rect_filled=True, chi vien neu khong."""
        xmin, xmax = min(x0, x1), max(x0, x1)
        ymin, ymax = min(y0, y1), max(y0, y1)
        points = []
        for y in range(ymin, ymax + 1):
            for x in range(xmin, xmax + 1):
                on_border = x in (xmin, xmax) or y in (ymin, ymax)
                if self.rect_filled or on_border:
                    points.append((x, y))
        return points

    def flood_fill(self, x0, y0, color):
        sp = self.sp()
        size, pixels = sp.size, sp.pixels
        target = pixels[y0 * size + x0]
        if target == color:
            return
        stack = [(x0, y0)]
        seen = set()
        while stack:
            x, y = stack.pop()
            if x < 0 or y < 0 or x >= size or y >= size:
                continue
            key = (x, y)
            if key in seen:
                continue
            if pixels[y * size + x] != target:
                continue
            seen.add(key)
            for mx, my in self._mirror_points(x, y, size):
                pixels[my * size + mx] = color
            stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    def apply_tool_at(self, x, y, is_start):
        sp = self.sp()
        if self.tool == "pencil":
            self.paint_stamp(x, y, self.color)
        elif self.tool == "eraser":
            self.paint_stamp(x, y, None)
        elif self.tool == "fill":
            if is_start:
                self.flood_fill(x, y, self.color)
        elif self.tool == "eyedropper":
            if is_start:
                c = sp.pixels[y * sp.size + x]
                if c:
                    self.color = c
                    self.color_rgb = list(hex_to_rgb(c))
                    self.remember_color(c)
                    self.toast(f"Da hut mau: {c}")
                else:
                    self.toast("Ô này đang trống (trong suốt)")
        # "line" va "rect" khong ve ngay o day - chung duoc xu ly rieng
        # bang shape_start/shape_preview_end (xem handle_mouse_down/up
        # trong App) vi can XEM TRUOC khi dang keo, chi commit luc tha chuot.


class _FramePreviewShim:
    """Vỏ bọc NHẸ (giả lập) chỉ có đúng 2 thuộc tính (size, pixels) - dùng
    để đưa 1 KHUNG CỤ THỂ của sprite vào ô xem trước (preview_game_rect/
    preview_big_rect trong App.draw_canvas) khi đang PHÁT hoạt ảnh nhiều
    khung, mà không cần tạo hẳn 1 Sprite() đầy đủ (không cần frames/
    frame_idx/label ở đây, chỉ cần đọc pixel để vẽ)."""
    __slots__ = ("size", "pixels")

    def __init__(self, size, pixels):
        self.size = size
        self.pixels = pixels


state = AppState()
for name, size, label in PRESET_SPRITES:
    state.new_sprite(name, size, label)
for name, px in DEFAULT_PIXELS.items():
    if name in state.sprites:
        state.sprites[name].pixels = px[:]
state.current = state.order[0]


# ============================================================
# WIDGETS (immediate-mode style: rebuilt every frame)
# ============================================================
class Button:
    def __init__(self, rect, label, on_click, active=False, danger=False,
                 font=None, tip=""):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.active = active
        self.danger = danger
        self.font = font or font_normal
        self.hover = False
        self.tip = tip

    def draw(self, surf, clip_offset=(0, 0)):
        r = self.rect.move(clip_offset)
        bg = COL_PANEL2
        border = COL_BORDER
        text_col = COL_TEXT
        if self.active:
            bg = COL_ACCENT
            text_col = (20, 15, 10)
        elif self.danger:
            border = COL_DANGER
            text_col = COL_DANGER
        elif self.hover:
            bg = tuple(min(255, c + 12) for c in COL_PANEL2)
        pygame.draw.rect(surf, bg, r, border_radius=6)
        pygame.draw.rect(surf, border, r, width=1, border_radius=6)
        label = self.label
        max_w = r.w - 10  # chua het chu 5px moi ben, tranh chu tran ra ngoai nut
        while self.font.size(label)[0] > max_w and len(label) > 1:
            label = label[:-1]
        if label != self.label:
            label = label.rstrip() + "…"
        img = self.font.render(label, True, text_col)
        tw, th = img.get_size()
        surf.blit(img, (r.centerx - tw // 2, r.centery - th // 2))

    def handle_click(self, pos, offset=(0, 0)):
        r = self.rect.move(offset)
        if r.collidepoint(pos):
            if self.on_click:
                self.on_click()
            return True
        return False

    def update_hover(self, pos, offset=(0, 0)):
        r = self.rect.move(offset)
        self.hover = r.collidepoint(pos)


class Swatch:
    """1 o mau trong bang mau ben phai."""
    def __init__(self, rect, name, hexcolor, on_click):
        self.rect = pygame.Rect(rect)
        self.name = name
        self.hexcolor = hexcolor
        self.on_click = on_click
        self.hover = False

    def draw(self, surf, offset=(0, 0), selected=False):
        r = self.rect.move(offset)
        pygame.draw.rect(surf, hex_to_rgb(self.hexcolor), (r.x, r.y, 18, 18), border_radius=4)
        pygame.draw.rect(surf, COL_BORDER if not selected else COL_ACCENT2,
                          (r.x, r.y, 18, 18), width=2 if selected else 1, border_radius=4)
        img = font_small.render(self.name, True, COL_TEXT if not self.hover else COL_ACCENT2)
        surf.blit(img, (r.x + 24, r.y + 2))

    def handle_click(self, pos, offset=(0, 0)):
        r = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, self.rect.h).move(offset)
        if r.collidepoint(pos):
            self.on_click(self.hexcolor)
            return True
        return False


class TextBox:
    def __init__(self, rect, text=""):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.active = False

    def draw(self, surf, offset=(0, 0)):
        r = self.rect.move(offset)
        pygame.draw.rect(surf, (20, 16, 11), r, border_radius=5)
        pygame.draw.rect(surf, COL_ACCENT if self.active else COL_BORDER, r, width=1, border_radius=5)
        img = font_normal.render(self.text, True, COL_TEXT)
        surf.blit(img, (r.x + 8, r.centery - img.get_height() // 2))
        if self.active and (pygame.time.get_ticks() // 500) % 2 == 0:
            cx = r.x + 8 + img.get_width() + 2
            pygame.draw.line(surf, COL_ACCENT2, (cx, r.y + 5), (cx, r.bottom - 5), 1)

    def handle_click(self, pos, offset=(0, 0)):
        r = self.rect.move(offset)
        self.active = r.collidepoint(pos)
        return self.active

    def handle_key(self, event):
        if not self.active:
            return
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.active = False
        elif event.unicode and event.unicode.isprintable():
            self.text += event.unicode


# ============================================================
# APP (layout + logic)
# ============================================================
class App:
    def __init__(self):
        self.rename_box = TextBox((0, 0, 10, 10), state.sp().label)
        self.hexinput_box = TextBox((0, 0, 10, 10), state.color)
        self.right_scroll = 0.0        # vi tri cuon HIEN TAI (mượt, chạy dần tới target)
        self.right_scroll_target = 0.0  # vi tri cuon MUC TIEU (nhay ngay khi lan chuot)
        self.buttons = []
        self.swatches = []
        self.tab_buttons = []
        self.size_buttons = []
        self.canvas_rect = pygame.Rect(0, 0, 0, 0)
        self.preview_game_rect = pygame.Rect(0, 0, 0, 0)
        self.preview_big_rect = pygame.Rect(0, 0, 0, 0)
        # cac thanh truot dang keo (R/G/B/zoom) - luu rect KHUNG cua lan
        # ve gan nhat de tinh gia tri khi ren chuot, va key nao dang duoc
        # keo (None = khong keo thanh nao)
        self.slider_specs = {}   # key -> dict(rect, value, minv, maxv, on_change)
        self.active_slider = None
        self.recent_swatch_rects = []  # [(rect, hexcolor), ...] cua lan ve gan nhat
        self.running = True

    # ---------- actions ----------
    def set_tool(self, name):
        state.tool = name
        state.shape_start = None
        state.shape_preview_end = None

    def set_color(self, hexcolor):
        state.color = hexcolor
        state.color_rgb = list(hex_to_rgb(hexcolor))
        self.hexinput_box.text = hexcolor
        state.remember_color(hexcolor)

    def set_color_from_rgb(self):
        """Cap nhat state.color (hex) tu 3 gia tri R/G/B hien tai - goi
        moi khi keo 1 trong 3 thanh truot mau."""
        r, g, b = state.color_rgb
        hexcolor = f"#{r:02x}{g:02x}{b:02x}"
        state.color = hexcolor
        self.hexinput_box.text = hexcolor

    def set_transparent(self):
        state.color = None
        state.toast('Đang vẽ = xóa (trong suốt) - như tẩy')

    def select_sprite(self, name):
        state.current = name
        self.rename_box.text = state.sp().label
        state.shape_start = None
        state.shape_preview_end = None

    def clear_canvas(self):
        state.push_history()
        sp = state.sp()
        sp.pixels = [None] * (sp.size * sp.size)
        state.toast("Đã xóa toàn bộ canvas")

    def dup_sprite(self):
        sp = state.sp()
        name = state.new_sprite(state.current + "_copy", sp.size, sp.label + " (2)")
        # Nhân bản TOÀN BỘ danh sách khung (không chỉ khung đang mở) - nếu
        # không, nhân bản 1 sprite đang có sẵn hoạt ảnh nhiều khung sẽ vô
        # tình làm MẤT hết các khung khác, chỉ còn lại khung đang xem.
        state.sprites[name].frames = [f[:] for f in sp.frames]
        state.sprites[name].frame_idx = sp.frame_idx
        self.select_sprite(name)
        state.toast(f"Đã nhân bản sprite ({sp.n_frames} khung)")

    def del_sprite(self):
        if len(state.order) <= 1:
            state.toast("Phải còn ít nhất 1 sprite")
            return
        idx = state.order.index(state.current)
        del state.sprites[state.current]
        del state.history[state.current]
        state.order.pop(idx)
        self.select_sprite(state.order[max(0, idx - 1)])

    def apply_rename(self):
        label = self.rename_box.text.strip()
        if not label:
            return
        state.sp().label = label
        state.toast(f'Đã đổi tên hiển thị (tên file xuất vẫn là "{state.current}.png")')

    # ---------- khung hình (frame) - dựng hoạt ảnh nhiều khung ----------
    def add_frame(self):
        state.push_history()
        state.sp().add_frame(copy_current=True)
        state.toast(f"Đã thêm khung mới (nhân bản khung trước) - tổng {state.sp().n_frames} khung")

    def add_blank_frame(self):
        state.push_history()
        state.sp().add_frame(copy_current=False)
        state.toast(f"Đã thêm khung TRẮNG mới - tổng {state.sp().n_frames} khung")

    def delete_frame(self):
        sp = state.sp()
        if sp.n_frames <= 1:
            state.toast("Phải còn ít nhất 1 khung")
            return
        state.push_history()
        sp.delete_frame()
        state.toast(f"Đã xóa khung - còn lại {sp.n_frames} khung")

    def move_frame_left(self):
        if state.sp().frame_idx == 0:
            return
        state.push_history()
        state.sp().move_frame(-1)

    def move_frame_right(self):
        sp = state.sp()
        if sp.frame_idx >= sp.n_frames - 1:
            return
        state.push_history()
        sp.move_frame(1)

    def select_frame(self, idx):
        sp = state.sp()
        if 0 <= idx < sp.n_frames:
            sp.frame_idx = idx
            state.frame_anim_playing = False  # chon tay 1 khung -> dung phat tu dong, tranh giat hinh

    def prev_frame(self):
        sp = state.sp()
        self.select_frame((sp.frame_idx - 1) % sp.n_frames)

    def next_frame(self):
        sp = state.sp()
        self.select_frame((sp.frame_idx + 1) % sp.n_frames)

    def toggle_frame_anim(self):
        state.frame_anim_playing = not state.frame_anim_playing
        state.frame_anim_timer = 0.0
        state.frame_anim_idx = state.sp().frame_idx

    def toggle_onion_skin(self):
        state.onion_skin = not state.onion_skin

    def change_frame_fps(self, delta):
        state.frame_fps = max(1, min(24, state.frame_fps + delta))

    def apply_hex_color(self):
        txt = self.hexinput_box.text.strip()
        if not txt.startswith("#"):
            txt = "#" + txt
        if len(txt) == 7:
            try:
                hex_to_rgb(txt)
                self.set_color(txt)
                state.toast(f"Đã chọn màu {txt}")
            except Exception:
                state.toast("Mã màu không hợp lệ (dùng dạng #rrggbb)")
        else:
            state.toast("Mã màu không hợp lệ (dùng dạng #rrggbb)")

    def set_brush_size(self, size):
        state.brush_size = size

    def toggle_rect_filled(self):
        state.rect_filled = not state.rect_filled

    def toggle_anim(self):
        state.anim_playing = not state.anim_playing
        state.anim_timer = 0
        state.anim_frame_idx = 0

    def resize_canvas(self, new_size):
        sp = state.sp()
        if sp.size == new_size:
            return
        sp.size = new_size
        # Làm TRỐNG LẠI TOÀN BỘ khung (không chỉ khung đang mở) - giữ
        # nguyên SỐ LƯỢNG khung hiện có (đổi kích thước không có lý do gì
        # xóa mất tiến độ dựng hoạt ảnh, chỉ cần vẽ lại nội dung từng khung
        # ở kích thước mới).
        sp.frames = [[None] * (new_size * new_size) for _ in sp.frames]
        state.history[state.current] = {"undo": [], "redo": []}
        state.toast(f"Đã đổi kích thước canvas sang {new_size}x{new_size} (mọi khung đều được làm trống)")

    def change_zoom(self, delta):
        state.zoom = max(6, min(40, state.zoom + delta))

    def set_zoom_value(self, value):
        state.zoom = max(6, min(40, int(value)))

    def register_slider(self, key, rect, value, minv, maxv, on_change):
        """Ghi lai 1 thanh truot de ve + xu ly keo o frame nay. Goi lai
        moi frame (giong Button) vi toa do co the doi khi resize cua so."""
        self.slider_specs[key] = {
            "rect": pygame.Rect(rect), "value": value,
            "minv": minv, "maxv": maxv, "on_change": on_change,
        }

    def _slider_value_from_pos(self, key, pos):
        spec = self.slider_specs.get(key)
        if not spec:
            return None
        r = spec["rect"]
        t = (pos[0] - r.x) / max(1, r.w)
        t = max(0.0, min(1.0, t))
        return spec["minv"] + t * (spec["maxv"] - spec["minv"])

    def draw_sliders(self):
        for key, spec in self.slider_specs.items():
            r = spec["rect"]
            pygame.draw.rect(screen, (20, 16, 11), r, border_radius=4)
            pygame.draw.rect(screen, COL_BORDER, r, width=1, border_radius=4)
            t = (spec["value"] - spec["minv"]) / max(1e-6, (spec["maxv"] - spec["minv"]))
            t = max(0.0, min(1.0, t))
            handle_x = r.x + int(t * r.w)
            handle_col = COL_ACCENT2 if self.active_slider == key else COL_ACCENT
            pygame.draw.circle(screen, handle_col, (handle_x, r.centery), 8)
            pygame.draw.circle(screen, COL_BORDER, (handle_x, r.centery), 8, width=1)

    def toggle_symmetry_h(self):
        state.symmetry_h = not state.symmetry_h

    def toggle_symmetry_v(self):
        state.symmetry_v = not state.symmetry_v

    def toggle_grid(self):
        state.show_grid = not state.show_grid

    # ---------- export ----------
    def sprite_to_surface(self, sp, frame_idx=None):
        """Ve 1 KHUNG DUY NHAT cua sprite ra Surface - mac dinh la khung
        DANG CHON (sp.frame_idx), truyen frame_idx de lay khung khac (dung
        khi ghep spritesheet - xem sprite_to_spritesheet_surface)."""
        frame = sp.frames[sp.frame_idx if frame_idx is None else frame_idx]
        surf = pygame.Surface((sp.size, sp.size), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        for y in range(sp.size):
            for x in range(sp.size):
                c = frame[y * sp.size + x]
                if c:
                    surf.set_at((x, y), hex_to_rgba(c, 255))
        return surf

    def sprite_to_spritesheet_surface(self, sp):
        """Ghép TẤT CẢ khung của sprite thành 1 ảnh spritesheet NGANG (mỗi
        khung size x size, xếp liên tiếp trái->phải theo ĐÚNG thứ tự phát)
        - định dạng xuất chuẩn cho sprite nhiều khung, để phần engine của
        game (sprite_manager.py) có thể đọc/cắt lại sau này (mỗi khung =
        tổng_chiều_rộng // số_khung)."""
        n = sp.n_frames
        sheet = pygame.Surface((sp.size * n, sp.size), pygame.SRCALPHA)
        sheet.fill((0, 0, 0, 0))
        for i in range(n):
            sheet.blit(self.sprite_to_surface(sp, frame_idx=i), (i * sp.size, 0))
        return sheet

    def ensure_dir(self):
        os.makedirs(SPRITES_DIR, exist_ok=True)

    def export_native(self):
        self.ensure_dir()
        sp = state.sp()
        path = os.path.join(SPRITES_DIR, f"{state.current}.png")
        if sp.n_frames > 1:
            # NHIỀU khung: xuất thành 1 spritesheet ngang DUY NHẤT chứa
            # đủ mọi khung - nếu chỉ xuất khung đang xem như sprite tĩnh sẽ
            # LÀM MẤT toàn bộ các khung còn lại một cách âm thầm, rất dễ
            # gây nhầm "tưởng đã lưu xong cả hoạt ảnh" mà thực ra chỉ lưu
            # được 1 khung.
            surf = self.sprite_to_spritesheet_surface(sp)
            pygame.image.save(surf, path)
            state.toast(f"Đã lưu {sp.n_frames} khung (spritesheet ngang, {sp.size}x{sp.size}/khung): assets/sprites/{state.current}.png")
        else:
            surf = self.sprite_to_surface(sp)
            pygame.image.save(surf, path)
            state.toast(f"Đã lưu: assets/sprites/{state.current}.png")

    def export_big(self):
        self.ensure_dir()
        sp = state.sp()
        surf = self.sprite_to_surface(sp)
        big = pygame.transform.scale(surf, (sp.size * 8, sp.size * 8))
        path = os.path.join(SPRITES_DIR, f"{state.current}@8x.png")
        pygame.image.save(big, path)
        suffix = f" (chỉ khung #{sp.frame_idx + 1}/{sp.n_frames} đang xem)" if sp.n_frames > 1 else ""
        state.toast(f"Đã lưu bản phóng to 8x: assets/sprites/{state.current}@8x.png{suffix}")

    def export_all(self):
        self.ensure_dir()
        for name in state.order:
            sp = state.sprites[name]
            surf = (self.sprite_to_spritesheet_surface(sp) if sp.n_frames > 1
                    else self.sprite_to_surface(sp))
            pygame.image.save(surf, os.path.join(SPRITES_DIR, f"{name}.png"))
        # sprite sheet tong hop (tham khao nhanh, khong dung de game doc) -
        # voi sprite nhieu khung, chi lay khung DANG XEM cho gon (spritesheet
        # nay chi de xem tong quan, khong phai file dung de game doc)
        pad, label_h, cell, cols = 6, 14, 96, 4
        rows = (len(state.order) + cols - 1) // cols
        sheet = pygame.Surface((cols * (cell + pad) + pad, rows * (cell + pad + label_h) + pad))
        sheet.fill((32, 25, 15))
        for i, name in enumerate(state.order):
            col, row = i % cols, i // cols
            ox = pad + col * (cell + pad)
            oy = pad + row * (cell + pad + label_h)
            pygame.draw.rect(sheet, (42, 36, 25), (ox, oy, cell, cell))
            sp = state.sprites[name]
            src = self.sprite_to_surface(sp)
            scaled = pygame.transform.scale(src, (cell, cell))
            sheet.blit(scaled, (ox, oy))
            pygame.draw.rect(sheet, COL_BORDER, (ox, oy, cell, cell), width=1)
            label_text = name + (f" ({sp.n_frames}kh)" if sp.n_frames > 1 else "")
            img = font_mono.render(label_text, True, COL_TEXT)
            sheet.blit(img, (ox, oy + cell + 2))
        pygame.image.save(sheet, os.path.join(SPRITES_DIR, "antworld_sprite_sheet.png"))
        state.toast(f"Đã lưu TOÀN BỘ {len(state.order)} sprite + 1 sprite sheet vào assets/sprites/")

    # ---------- canvas interaction ----------
    def cell_from_pos(self, pos):
        sp = state.sp()
        rel_x = pos[0] - self.canvas_rect.x
        rel_y = pos[1] - self.canvas_rect.y
        if rel_x < 0 or rel_y < 0:
            return None
        x = int(rel_x // state.zoom)
        y = int(rel_y // state.zoom)
        if x < 0 or y < 0 or x >= sp.size or y >= sp.size:
            return None
        return x, y

    def cell_from_pos_clamped(self, pos):
        """Giong cell_from_pos, nhung LUON tra ve 1 o hop le (ep ve cham
        bien gan nhat) thay vi None khi chuot ra ngoai canvas - dung cho
        xem truoc duong thang/hinh chu nhat luc dang keo, de keo ra ngoai
        bien van "dinh" vao canh/goc thay vi mat huong xem truoc."""
        sp = state.sp()
        rel_x = pos[0] - self.canvas_rect.x
        rel_y = pos[1] - self.canvas_rect.y
        x = int(rel_x // state.zoom)
        y = int(rel_y // state.zoom)
        x = max(0, min(sp.size - 1, x))
        y = max(0, min(sp.size - 1, y))
        return x, y

    # ---------- layout / draw ----------
    def layout(self):
        w, h = screen.get_size()
        self.W, self.H = w, h
        self.header_h = 54
        self.footer_h = 46
        self.left_w = 230
        self.right_w = 270
        self.tabbar_h = 78
        self.toolbar_h = 40

    def build_left_panel(self):
        self.buttons = []
        x0, y0 = 12, self.header_h + 12
        w = self.left_w - 24

        def sec(title, y):
            return y

        y = y0
        draw_text(screen, "CÔNG CỤ", (x0, y), font_small, COL_TEXT_DIM)
        y += 20
        tool_w = (w - 6) // 2
        tools = [("pencil", "Bút (B)"), ("eraser", "Tẩy (E)"),
                 ("fill", "Đổ màu (G)"), ("eyedropper", "Hút màu (I)"),
                 ("line", "Đường thẳng (L)"), ("rect", "Hình CN (R)")]
        for i, (key, label) in enumerate(tools):
            col, row = i % 2, i // 2
            rect = (x0 + col * (tool_w + 6), y + row * 34, tool_w, 30)
            self.buttons.append(Button(rect, label, (lambda k=key: self.set_tool(k)),
                                        active=(state.tool == key), font=font_small))
        y += 34 * 3 + 10

        if state.tool == "rect":
            self.buttons.append(Button((x0, y, w, 28),
                                        f"HCN: {'ĐẶC' if state.rect_filled else 'VIỀN'}",
                                        self.toggle_rect_filled, active=state.rect_filled,
                                        font=font_small))
            y += 34
        elif state.tool in ("pencil", "eraser"):
            draw_text(screen, f"Cỡ bút: {state.brush_size}px", (x0, y), font_small, COL_TEXT)
            y += 18
            bw = (w - 2 * 6) // 3
            for i, sz in enumerate([1, 2, 3]):
                rect = (x0 + i * (bw + 6), y, bw, 26)
                self.buttons.append(Button(rect, f"{sz}", (lambda s=sz: self.set_brush_size(s)),
                                            active=(state.brush_size == sz), font=font_small))
            y += 32
        y += 10

        draw_text(screen, "CHỈNH SỬA", (x0, y), font_small, COL_TEXT_DIM)
        y += 20
        self.buttons.append(Button((x0, y, w, 30), "Hoàn tác (Ctrl+Z)", state.undo, font=font_small))
        y += 34
        self.buttons.append(Button((x0, y, w, 30), "Làm lại (Ctrl+Y)", state.redo, font=font_small))
        y += 34
        self.buttons.append(Button((x0, y, w, 30),
                                    f"Đối xứng ngang: {'BẬT' if state.symmetry_h else 'TẮT'}",
                                    self.toggle_symmetry_h, active=state.symmetry_h, font=font_small))
        y += 34
        self.buttons.append(Button((x0, y, w, 30),
                                    f"Đối xứng dọc: {'BẬT' if state.symmetry_v else 'TẮT'}",
                                    self.toggle_symmetry_v, active=state.symmetry_v, font=font_small))
        y += 34
        self.buttons.append(Button((x0, y, w, 30), "Xóa toàn bộ canvas", self.clear_canvas,
                                    danger=True, font=font_small))
        y += 44

        draw_text(screen, "HIỂN THỊ", (x0, y), font_small, COL_TEXT_DIM)
        y += 20
        draw_text(screen, f"Thu phóng: {state.zoom}px", (x0, y), font_small, COL_TEXT)
        y += 18
        self.buttons.append(Button((x0, y, 28, 24), "-", lambda: self.change_zoom(-2), font=font_normal))
        self.register_slider("zoom", (x0 + 34, y + 4, w - 34 - 34 - 6, 16),
                              state.zoom, 6, 40, self.set_zoom_value)
        self.buttons.append(Button((x0 + w - 28, y, 28, 24), "+", lambda: self.change_zoom(2), font=font_normal))
        y += 30
        self.buttons.append(Button((x0, y, w, 30), f"Lưới: {'BẬT' if state.show_grid else 'TẮT'}",
                                    self.toggle_grid, active=state.show_grid, font=font_small))
        y += 44

        draw_text(screen, "KÍCH THƯỚC CANVAS", (x0, y), font_small, COL_TEXT_DIM)
        y += 20
        sizes = [8, 12, 16, 24, 32, 48]
        sz_w = (w - 2 * 6) // 3
        self.size_buttons = []
        for i, s in enumerate(sizes):
            col, row = i % 3, i // 3
            rect = (x0 + col * (sz_w + 6), y + row * 32, sz_w, 28)
            active = state.sp().size == s
            self.buttons.append(Button(rect, f"{s}", (lambda ss=s: self.resize_canvas(ss)),
                                        active=active, font=font_small))
        y += 32 * 2 + 10
        hint = "Đổi kích thước sẽ làm trống canvas của sprite đang chọn."
        self._wrap_text(hint, (x0, y), w, font_small, COL_TEXT_DIM)

    def _wrap_text(self, text, pos, max_w, font, color):
        words = text.split(" ")
        lines, cur = [], ""
        for wd in words:
            test = (cur + " " + wd).strip()
            if font.size(test)[0] > max_w and cur:
                lines.append(cur)
                cur = wd
            else:
                cur = test
        if cur:
            lines.append(cur)
        x, y = pos
        for ln in lines:
            img = font.render(ln, True, color)
            screen.blit(img, (x, y))
            y += 15

    def build_right_panel(self):
        self.swatches = []
        self.recent_swatch_rects = []
        rx = self.W - self.right_w + 12
        y = self.header_h + 12 - self.right_scroll
        w = self.right_w - 24

        top = y
        draw_text(screen, "MÀU ĐANG CHỌN", (rx, y), font_small, COL_TEXT_DIM)
        y += 22
        swatch_rect = pygame.Rect(rx, y, 34, 34)
        if state.color:
            pygame.draw.rect(screen, hex_to_rgb(state.color), swatch_rect, border_radius=6)
        else:
            pygame.draw.rect(screen, (50, 42, 30), swatch_rect, border_radius=6)
            pygame.draw.line(screen, COL_DANGER, swatch_rect.topleft, swatch_rect.bottomright, 2)
        pygame.draw.rect(screen, COL_BORDER, swatch_rect, width=1, border_radius=6)
        self.hexinput_box.rect = pygame.Rect(rx + 42, y + 3, w - 42, 28)
        self.hexinput_box.draw(screen)
        y += 44

        # Thanh trượt R/G/B - kéo trực tiếp để pha màu, khớp tức thì với
        # mã hex và ô màu đang chọn phía trên (kéo tới đâu cập nhật tới đó).
        r, g, b = state.color_rgb
        slider_labels = [("r", "R", r, (220, 90, 90)), ("g", "G", g, (90, 200, 110)),
                          ("b", "B", b, (100, 140, 230))]
        for key, label, val, dot_col in slider_labels:
            draw_text(screen, f"{label} {val}", (rx, y), font_small, COL_TEXT)
            pygame.draw.circle(screen, dot_col, (rx + w - 8, y + 6), 5)
            self.register_slider(f"color_{key}", (rx, y + 16, w, 14), val, 0, 255,
                                  (lambda v, k=key: self._set_color_channel(k, v)))
            y += 34
        y += 6

        self.buttons.append(Button((rx, y, w, 26), "Áp dụng mã màu (Enter)", self.apply_hex_color, font=font_small))
        y += 32
        self.buttons.append(Button((rx, y, w, 28), 'Chọn "trong suốt" (tẩy)', self.set_transparent,
                                    active=(state.color is None), font=font_small))
        y += 38

        if state.recent_colors:
            draw_text(screen, "MÀU VỪA DÙNG", (rx, y), font_small, COL_TEXT_DIM)
            y += 18
            sw_size, gap = 22, 4
            per_row = max(1, (w + gap) // (sw_size + gap))
            for i, hexcolor in enumerate(state.recent_colors):
                col, row = i % per_row, i // per_row
                rect = pygame.Rect(rx + col * (sw_size + gap), y + row * (sw_size + gap), sw_size, sw_size)
                pygame.draw.rect(screen, hex_to_rgb(hexcolor), rect, border_radius=4)
                border_col = COL_ACCENT2 if hexcolor == state.color else COL_BORDER
                pygame.draw.rect(screen, border_col, rect, width=2 if hexcolor == state.color else 1, border_radius=4)
                self.recent_swatch_rects.append((rect.copy(), hexcolor))
            rows_used = (len(state.recent_colors) + per_row - 1) // per_row
            y += rows_used * (sw_size + gap) + 12

        draw_text(screen, "BẢNG MÀU GAME (bấm để chọn)", (rx, y), font_small, COL_TEXT_DIM)
        y += 20
        for group in PALETTE_GROUPS:
            img = font_bold.render(group["label"], True, COL_ACCENT2)
            screen.blit(img, (rx, y))
            y += 18
            for cname, chex in group["colors"]:
                rect = (rx, y, w, 20)
                sw = Swatch(rect, cname, chex, self.set_color)
                self.swatches.append(sw)
                y += 22
            y += 6
        self.right_content_h = (y - top) + self.right_scroll

    def _set_color_channel(self, channel, value):
        idx = {"r": 0, "g": 1, "b": 2}[channel]
        state.color_rgb[idx] = int(max(0, min(255, value)))
        self.set_color_from_rgb()

    def build_tabs(self):
        self.tab_buttons = []
        x0 = self.left_w + 12
        y0 = self.header_h + 8
        w_avail = self.W - self.left_w - self.right_w - 24
        x, y = x0, y0
        row_h = 26
        for name in state.order:
            label = state.sprites[name].label
            tw = font_small.size(label)[0] + 16
            if x + tw > x0 + w_avail and x > x0:
                x = x0
                y += row_h + 4
            rect = (x, y, tw, row_h)
            self.tab_buttons.append(
                Button(rect, label, (lambda n=name: self.select_sprite(n)),
                       active=(name == state.current), font=font_small))
            x += tw + 6
        self.buttons.extend(self.tab_buttons)
        self.tabbar_bottom = y + row_h

    def build_canvas_toolbar(self):
        x0 = self.left_w + 12
        y = self.tabbar_bottom + 8
        self.rename_box.rect = pygame.Rect(x0, y, 220, 28)
        self.rename_box.draw(screen)
        self.buttons.append(Button((x0 + 228, y, 100, 28), "Đổi tên", self.apply_rename, font=font_small))
        self.buttons.append(Button((x0 + 334, y, 100, 28), "Nhân bản", self.dup_sprite, font=font_small))
        self.buttons.append(Button((x0 + 440, y, 110, 28), "Xóa sprite", self.del_sprite,
                                    danger=True, font=font_small))
        hint = f'sẽ xuất ra: {state.current}.png'
        draw_text(screen, hint, (x0 + 560, y + 6), font_small, COL_TEXT_DIM)
        self.toolbar_bottom = y + 28

    def build_canvas(self):
        sp = state.sp()
        px = sp.size * state.zoom
        x0 = self.left_w + 12
        y0 = self.toolbar_bottom + 14
        avail_w = self.W - self.left_w - self.right_w - 24 - 190  # tru cho cot preview
        cx = x0 + max(0, (avail_w - px) // 2)
        self.canvas_rect = pygame.Rect(cx, y0, px, px)

        # preview column
        pcx = x0 + avail_w + 10
        draw_text(screen, "XEM THẬT (như trong game)", (pcx, y0), font_small, COL_TEXT_DIM)
        self.preview_game_rect = pygame.Rect(pcx, y0 + 18, sp.size * 4, sp.size * 4)
        draw_text(screen, "XEM 8×", (pcx, self.preview_game_rect.bottom + 10), font_small, COL_TEXT_DIM)
        self.preview_big_rect = pygame.Rect(pcx, self.preview_game_rect.bottom + 28, sp.size * 8, sp.size * 8)

        # nut xem hoat anh - doi nhan tuy co "cap doi" (vd _carry) hay khong
        pair = self.anim_pair_name()
        if pair:
            label = "[X] Dừng hoạt ảnh" if state.anim_playing else "[>] Xem hoạt ảnh (đổi/mang)"
        else:
            label = "[X] Dừng lướt" if state.anim_playing else "[>] Lướt qua tất cả sprite"
        anim_btn_w = max(170, self.preview_big_rect.w)
        anim_y = self.preview_big_rect.bottom + 10
        self.buttons.append(Button((pcx, anim_y, anim_btn_w, 28), label, self.toggle_anim,
                                    active=state.anim_playing, font=font_small))
        if state.anim_playing:
            anim_sp_name = self._anim_frame_names()[state.anim_frame_idx % max(1, len(self._anim_frame_names()))]
            draw_text(screen, f"đang chiếu: {anim_sp_name}", (pcx, anim_y + 32), font_small, COL_TEXT_DIM)

    def build_frame_strip(self):
        """Khu vực KHUNG HÌNH (frame) ngay dưới canvas chính - nơi quản lý
        nhiều khung pixel-art của CÙNG 1 sprite để dựng hoạt ảnh (đi bộ,
        vẫy càng...): thêm/nhân bản/xóa/đổi thứ tự khung, phát thử vòng
        lặp, và bật/tắt xem mờ khung trước (onion skin). Trước đây mỗi
        sprite chỉ vẽ được ĐÚNG 1 tấm tĩnh, không có khái niệm "khung"."""
        sp = state.sp()
        x0 = self.canvas_rect.x
        y = self.canvas_rect.bottom + 14
        w_avail = max(320, self.canvas_rect.w)

        draw_text(screen, f"KHUNG HÌNH (ANIMATION) - {sp.n_frames} khung", (x0, y), font_small, COL_TEXT_DIM)
        y += 20

        # --- Hàng 1: dải thumbnail từng khung, bấm vào để chọn ---
        thumb_slot = 40   # khoảng cách tâm-tới-tâm giữa 2 ô thumbnail liên tiếp
        thumb_box = 34    # kích thước khung viền hiển thị (px)
        self.frame_thumb_rects = []
        for i, frame_px in enumerate(sp.frames):
            fx = x0 + i * thumb_slot
            rect = pygame.Rect(fx, y, thumb_box, thumb_box)
            selected = (i == sp.frame_idx)
            pygame.draw.rect(screen, COL_CANVAS_BG, rect)
            cell_px = max(1, thumb_box // sp.size)
            off = (thumb_box - cell_px * sp.size) // 2
            for py in range(sp.size):
                for px_ in range(sp.size):
                    c = frame_px[py * sp.size + px_]
                    if c:
                        pygame.draw.rect(screen, hex_to_rgb(c),
                                          (rect.x + off + px_ * cell_px, rect.y + off + py * cell_px,
                                           cell_px, cell_px))
            pygame.draw.rect(screen, COL_ACCENT2 if selected else COL_BORDER, rect,
                              width=2 if selected else 1)
            idx_img = font_small.render(str(i + 1), True, COL_TEXT_DIM)
            screen.blit(idx_img, (rect.centerx - idx_img.get_width() // 2, rect.bottom + 1))
            self.frame_thumb_rects.append((rect.copy(), i))
        y += thumb_box + 18

        # --- Hàng 2: các nút thao tác khung + phát thử + onion skin ---
        bw, bh, gap = 96, 26, 6
        bx = x0
        self.buttons.append(Button((bx, y, bw, bh), "+ Nhân bản", self.add_frame, font=font_small,
                                    tip="Thêm khung mới, sao chép từ khung đang xem"))
        bx += bw + gap
        self.buttons.append(Button((bx, y, bw, bh), "+ Trắng", self.add_blank_frame, font=font_small))
        bx += bw + gap
        self.buttons.append(Button((bx, y, bw, bh), "Xóa khung", self.delete_frame,
                                    danger=(sp.n_frames > 1), font=font_small))
        bx += bw + gap + 4
        self.buttons.append(Button((bx, y, 34, bh), "<", self.move_frame_left, font=font_small,
                                    tip="Đổi chỗ với khung trước (,)"))
        bx += 34 + 4
        self.buttons.append(Button((bx, y, 34, bh), ">", self.move_frame_right, font=font_small,
                                    tip="Đổi chỗ với khung sau (.)"))
        bx += 34 + gap + 8

        play_label = "[X] Dừng phát" if state.frame_anim_playing else "[>] Phát thử"
        self.buttons.append(Button((bx, y, 110, bh), play_label, self.toggle_frame_anim,
                                    active=state.frame_anim_playing, font=font_small))
        bx += 110 + gap
        draw_text(screen, f"{state.frame_fps} fps", (bx, y + 6), font_small, COL_TEXT)
        bx += 42
        self.buttons.append(Button((bx, y, 24, bh), "-", lambda: self.change_frame_fps(-1), font=font_small))
        bx += 24 + 4
        self.buttons.append(Button((bx, y, 24, bh), "+", lambda: self.change_frame_fps(1), font=font_small))
        bx += 24 + gap + 8

        self.buttons.append(Button((bx, y, 150, bh), f"Xem mờ khung trước: {'BẬT' if state.onion_skin else 'TẮT'}",
                                    self.toggle_onion_skin, active=state.onion_skin, font=font_small))
        self.frame_strip_bottom = y + bh + 8

    def handle_frame_thumb_click(self, pos):
        """Trả về True nếu click trúng 1 thumbnail khung (đã xử lý), để
        handle_mouse_down() biết dừng lại, không coi đó là 1 nét vẽ trên
        canvas chính."""
        for rect, idx in getattr(self, "frame_thumb_rects", []):
            if rect.collidepoint(pos):
                self.select_frame(idx)
                return True
        return False

    def draw_canvas(self):
        sp = state.sp()
        z = state.zoom
        pygame.draw.rect(screen, COL_CANVAS_BG, self.canvas_rect.inflate(4, 4))
        # checkerboard nen (bao thi trong suot)
        cb = 8
        for gy in range(0, self.canvas_rect.h, cb):
            for gx in range(0, self.canvas_rect.w, cb):
                if (gx // cb + gy // cb) % 2 == 0:
                    pygame.draw.rect(screen, (40, 33, 24),
                                      (self.canvas_rect.x + gx, self.canvas_rect.y + gy, cb, cb))

        # Onion skin: hiện MỜ khung TRƯỚC khung đang vẽ, giúp canh đúng vị
        # trí giữa 2 khung hoạt ảnh liên tiếp (vd chân bước sang bước kế
        # tiếp lệch bao nhiêu) mà không cần liên tục bấm qua lại xem thử.
        # Chỉ hiện khi: có bật (onion_skin), sprite có từ 2 khung trở lên,
        # và KHÔNG phải đang xem khung đầu tiên (không có khung nào trước
        # nó để hiện).
        if state.onion_skin and sp.n_frames > 1 and sp.frame_idx > 0:
            prev_frame = sp.frames[sp.frame_idx - 1]
            onion = pygame.Surface(self.canvas_rect.size, pygame.SRCALPHA)
            for y in range(sp.size):
                for x in range(sp.size):
                    c = prev_frame[y * sp.size + x]
                    if c:
                        pygame.draw.rect(onion, (*hex_to_rgb(c), 100), (x * z, y * z, z, z))
            screen.blit(onion, self.canvas_rect.topleft)

        for y in range(sp.size):
            for x in range(sp.size):
                c = sp.pixels[y * sp.size + x]
                if c:
                    r = (self.canvas_rect.x + x * z, self.canvas_rect.y + y * z, z, z)
                    pygame.draw.rect(screen, hex_to_rgb(c), r)

        # Xem truoc duong thang / hinh chu nhat dang keo (chua ve that len
        # sprite - chi ve tam thoi de nguoi dung thay hinh se ra sao truoc
        # khi tha chuot). Ve theo dung phep doi xung dang bat, giong het
        # luc commit that o handle_mouse_up.
        if state.tool in ("line", "rect") and state.shape_start and state.shape_preview_end:
            x0s, y0s = state.shape_start
            x1s, y1s = state.shape_preview_end
            pts = (state.line_points(x0s, y0s, x1s, y1s) if state.tool == "line"
                   else state.rect_points(x0s, y0s, x1s, y1s))
            preview_rgb = hex_to_rgb(state.color) if state.color else (255, 255, 255)
            preview_layer = pygame.Surface(self.canvas_rect.size, pygame.SRCALPHA)
            drawn = set()
            for (px_, py_) in pts:
                for mx, my in state._mirror_points(px_, py_, sp.size):
                    if (mx, my) in drawn or not (0 <= mx < sp.size and 0 <= my < sp.size):
                        continue
                    drawn.add((mx, my))
                    pygame.draw.rect(preview_layer, (*preview_rgb, 150),
                                      (mx * z, my * z, z, z))
            screen.blit(preview_layer, self.canvas_rect.topleft)

        if state.show_grid and z >= 6:
            grid_col = (0, 0, 0, 90)
            gs = pygame.Surface(self.canvas_rect.size, pygame.SRCALPHA)
            for i in range(sp.size + 1):
                pygame.draw.line(gs, grid_col, (i * z, 0), (i * z, sp.size * z))
                pygame.draw.line(gs, grid_col, (0, i * z), (sp.size * z, i * z))
            screen.blit(gs, self.canvas_rect.topleft)
        pygame.draw.rect(screen, COL_BORDER, self.canvas_rect, width=2)

        # preview boxes - dung sprite dang "chieu" (co the la sprite khac
        # neu dang bat Xem hoat anh), khong phai luon la sprite dang sua
        anim_sp = self._anim_current_sprite()
        for rect, scale in ((self.preview_game_rect, 4), (self.preview_big_rect, 8)):
            pygame.draw.rect(screen, COL_CANVAS_BG, rect.inflate(4, 4))
            for y in range(anim_sp.size):
                for x in range(anim_sp.size):
                    c = anim_sp.pixels[y * anim_sp.size + x]
                    if c:
                        pygame.draw.rect(screen, hex_to_rgb(c),
                                          (rect.x + x * scale, rect.y + y * scale, scale, scale))
            pygame.draw.rect(screen, COL_BORDER, rect, width=1)


    def build_footer(self):
        y = self.H - self.footer_h + 8
        self.buttons.append(Button((16, y, 230, 30), "Lưu PNG (kích thước gốc)", self.export_native, font=font_small))
        self.buttons.append(Button((256, y, 230, 30), "Lưu PNG (phóng to 8x)", self.export_big, font=font_small))
        self.buttons.append(Button((496, y, 260, 30), "Lưu TOÀN BỘ + sprite sheet", self.export_all, font=font_small))

    def draw_header(self):
        pygame.draw.rect(screen, (28, 22, 15), (0, 0, self.W, self.header_h))
        pygame.draw.line(screen, COL_BORDER, (0, self.header_h), (self.W, self.header_h), 2)
        draw_text(screen, "ANTWORLD PIXEL STUDIO", (18, 16), font_title, COL_ACCENT2)
        draw_text(screen, "Vẽ asset pixel art cho game đàn kiến", (330, 20), font_small, COL_TEXT_DIM)
        hint = "B bút · E tẩy · G đổ màu · I hút màu · L đường · R hcn · [ ] cỡ bút · , . đổi khung · Ctrl+Z hoàn tác"
        hint_w = font_small.size(hint)[0]
        draw_text(screen, hint, (self.W - hint_w - 18, 20), font_small, COL_TEXT_DIM)

    def draw_footer(self):
        y = self.H - self.footer_h
        pygame.draw.rect(screen, (28, 22, 15), (0, y, self.W, self.footer_h))
        pygame.draw.line(screen, COL_BORDER, (0, y), (self.W, y), 2)
        draw_text(screen, f"Xuất file vào: {SPRITES_DIR}", (770, y + 15), font_small, COL_TEXT_DIM,
                  max_w=self.W - 790)

    def draw_toast(self):
        if state.status_timer > 0 and state.status:
            state.status_timer -= 1
            img = font_normal.render(state.status, True, COL_TEXT)
            pad = 12
            w, h = img.get_size()
            rect = pygame.Rect(0, 0, w + pad * 2, h + pad)
            rect.centerx = self.W // 2
            rect.bottom = self.H - self.footer_h - 20
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (0, 0, 0, 200), s.get_rect(), border_radius=8)
            pygame.draw.rect(s, COL_ACCENT, s.get_rect(), width=1, border_radius=8)
            screen.blit(s, rect.topleft)
            screen.blit(img, (rect.x + pad, rect.y + pad // 2))

    def draw_panel_backgrounds(self):
        pygame.draw.rect(screen, COL_PANEL, (0, self.header_h, self.left_w, self.H - self.header_h - self.footer_h))
        pygame.draw.line(screen, COL_BORDER, (self.left_w, self.header_h), (self.left_w, self.H - self.footer_h), 2)
        rx = self.W - self.right_w
        pygame.draw.rect(screen, COL_PANEL, (rx, self.header_h, self.right_w, self.H - self.header_h - self.footer_h))
        pygame.draw.line(screen, COL_BORDER, (rx, self.header_h), (rx, self.H - self.footer_h), 2)

    # ---------- frame ----------
    def frame(self):
        self.layout()
        self._update_smooth_scroll()
        self._update_animation()
        screen.fill(COL_BG)
        self.draw_panel_backgrounds()
        self.draw_header()
        self.buttons = []
        self.slider_specs = {}
        self.build_left_panel()
        self.build_tabs()
        self.build_canvas_toolbar()
        self.build_canvas()
        self.draw_canvas()
        self.build_frame_strip()
        self.build_right_panel()
        self.build_footer()

        mouse_pos = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update_hover(mouse_pos)
            b.draw(screen)
        for sw in self.swatches:
            sw.hover = pygame.Rect(sw.rect).collidepoint(mouse_pos)
            sw.draw(screen, selected=(state.color == sw.hexcolor))
        self.draw_sliders()

        self.draw_footer()
        self.draw_toast()
        pygame.display.flip()

    def _update_smooth_scroll(self):
        """Cuon 'muot' - vi tri hien tai luon truot dan toi vi tri muc
        tieu (thay vi nhay coc tuc thi), moi lan chuot lan chi doi TARGET,
        con gia tri thuc te di chuyen dan qua vai frame."""
        diff = self.right_scroll_target - self.right_scroll
        if abs(diff) < 0.5:
            self.right_scroll = self.right_scroll_target
        else:
            self.right_scroll += diff * 0.25

    def _update_animation(self):
        self._update_frame_anim()
        if not state.anim_playing:
            return
        state.anim_timer += 1
        if state.anim_timer >= 24:  # ~0.4 giay o 60fps
            state.anim_timer = 0
            names = self._anim_frame_names()
            if names:
                state.anim_frame_idx = (state.anim_frame_idx + 1) % len(names)

    def _update_frame_anim(self):
        """Tick bo dem phat hoat anh CAC KHUNG cua CHINH sprite dang mo -
        toc do phat theo state.frame_fps (khung/giay), chinh duoc qua nut
        +/- (xem App.change_frame_fps), khac han toc do co dinh 0.4s/lan
        cua anim_playing (luot qua sprite khac) o tren."""
        if not state.frame_anim_playing:
            return
        sp = state.sp()
        if sp.n_frames <= 1:
            state.frame_anim_playing = False
            return
        state.frame_anim_timer += 1.0
        ticks_per_frame = 60.0 / max(1, state.frame_fps)
        if state.frame_anim_timer >= ticks_per_frame:
            state.frame_anim_timer -= ticks_per_frame
            state.frame_anim_idx = (state.frame_anim_idx + 1) % sp.n_frames

    def anim_pair_name(self):
        """Neu sprite dang chon co 1 'ban sao mang do vat' (hau to
        _carry) hoac chinh no la ban _carry, tra ve TEN cua sprite doi
        cap - dung de xem truoc hoat anh 'tho khong mang <-> tho mang'."""
        cur = state.current
        if cur.endswith("_carry") and cur[:-6] in state.sprites:
            return cur[:-6]
        paired = cur + "_carry"
        if paired in state.sprites:
            return paired
        return None

    def _anim_frame_names(self):
        pair = self.anim_pair_name()
        if pair:
            return [state.current, pair]
        return state.order  # khong co cap doi -> luot qua TAT CA sprite

    def _anim_current_sprite(self):
        # Uu tien phat hoat anh CAC KHUNG cua sprite dang mo (neu dang
        # bat) - day la thu nguoi dung MUON THAY nhat luc dang dung hoat
        # anh nhieu khung, nen kiem tra truoc ca anim_playing (luot sprite
        # khac) o duoi.
        sp = state.sp()
        if state.frame_anim_playing and sp.n_frames > 1:
            idx = state.frame_anim_idx % sp.n_frames
            return _FramePreviewShim(sp.size, sp.frames[idx])
        if not state.anim_playing:
            return sp
        names = self._anim_frame_names()
        if not names:
            return sp
        idx = state.anim_frame_idx % len(names)
        return state.sprites[names[idx]]

    def handle_mouse_down(self, event):
        pos = event.pos
        if event.button == 1:
            # Thanh truot (R/G/B/zoom) - kiem tra TRUOC button, vi vung
            # bam co the sat nhau. Cho phep bam hoi le ra ngoai track 1
            # chut (margin doc) de de "tom" hon.
            for key, spec in self.slider_specs.items():
                grab_rect = spec["rect"].inflate(0, 14)
                if grab_rect.collidepoint(pos):
                    self.active_slider = key
                    value = self._slider_value_from_pos(key, pos)
                    spec["on_change"](value)
                    return
            for b in self.buttons:
                if b.rect.collidepoint(pos):
                    b.on_click()
                    return
            for sw in self.swatches:
                if pygame.Rect(sw.rect).collidepoint(pos):
                    sw.on_click(sw.hexcolor)
                    return
            for rect, hexcolor in self.recent_swatch_rects:
                if rect.collidepoint(pos):
                    self.set_color(hexcolor)
                    return
            if self.hexinput_box.rect.collidepoint(pos):
                self.hexinput_box.active = True
                self.rename_box.active = False
                return
            if self.rename_box.rect.collidepoint(pos):
                self.rename_box.active = True
                self.hexinput_box.active = False
                return
            if self.handle_frame_thumb_click(pos):
                return
            self.hexinput_box.active = False
            self.rename_box.active = False
            cell = self.cell_from_pos(pos)
            if cell is None:
                return
            if state.tool in ("line", "rect"):
                # Chi GHI NHO diem bat dau + xem truoc - chua ve that len
                # canvas. Ve that (va push_history) dien ra 1 LAN DUY NHAT
                # luc tha chuot (handle_mouse_up), de undo hoan tac ca
                # duong/hinh vua ve trong 1 buoc thay vi tung o le.
                state.push_history()
                state.shape_start = cell
                state.shape_preview_end = cell
                state.painting = True
            else:
                state.push_history()
                state.painting = True
                state.apply_tool_at(cell[0], cell[1], True)
        elif event.button == 3:
            # chuot phai = tay nhanh (ap dung ca brush_size hien tai)
            cell = self.cell_from_pos(pos)
            if cell:
                state.push_history()
                state.paint_stamp(cell[0], cell[1], None)
        elif event.button == 4:
            if self.canvas_rect.collidepoint(pos):
                self.change_zoom(2)
            else:
                self.right_scroll_target = max(0, self.right_scroll_target - 60)
        elif event.button == 5:
            if self.canvas_rect.collidepoint(pos):
                self.change_zoom(-2)
            else:
                self.right_scroll_target = min(getattr(self, "right_content_h", 0),
                                                self.right_scroll_target + 60)

    def handle_mouse_up(self, event):
        if event.button == 1:
            if self.active_slider is not None:
                # Neu vua keo 1 trong 3 thanh mau (khong phai zoom), ghi
                # mau cuoi cung vao "vua dung" - chi ghi 1 LAN luc tha
                # chuot, khong ghi lien tuc moi frame dang keo.
                if self.active_slider.startswith("color_"):
                    state.remember_color(state.color)
                self.active_slider = None
                return
            if state.tool in ("line", "rect") and state.shape_start:
                x0, y0 = state.shape_start
                x1, y1 = state.shape_preview_end or state.shape_start
                pts = (state.line_points(x0, y0, x1, y1) if state.tool == "line"
                       else state.rect_points(x0, y0, x1, y1))
                for (px, py) in pts:
                    state.paint_stamp(px, py, state.color)
                state.shape_start = None
                state.shape_preview_end = None
            state.painting = False

    def handle_mouse_motion(self, event):
        if self.active_slider is not None:
            value = self._slider_value_from_pos(self.active_slider, event.pos)
            if value is not None:
                self.slider_specs[self.active_slider]["on_change"](value)
            return
        if not state.painting:
            return
        if state.tool in ("line", "rect"):
            cell = self.cell_from_pos_clamped(event.pos)
            if cell:
                state.shape_preview_end = cell
        elif state.tool in ("pencil", "eraser"):
            cell = self.cell_from_pos(event.pos)
            if cell:
                state.apply_tool_at(cell[0], cell[1], False)

    def handle_key(self, event):
        if self.rename_box.active:
            self.rename_box.handle_key(event)
            return
        if self.hexinput_box.active:
            self.hexinput_box.handle_key(event)
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.apply_hex_color()
            return
        mods = pygame.key.get_mods()
        ctrl = mods & pygame.KMOD_CTRL
        if ctrl and event.key == pygame.K_z:
            state.undo()
        elif ctrl and event.key == pygame.K_y:
            state.redo()
        elif event.key == pygame.K_b:
            self.set_tool("pencil")
        elif event.key == pygame.K_e:
            self.set_tool("eraser")
        elif event.key == pygame.K_g:
            self.set_tool("fill")
        elif event.key == pygame.K_i:
            self.set_tool("eyedropper")
        elif event.key == pygame.K_l:
            self.set_tool("line")
        elif event.key == pygame.K_r:
            self.set_tool("rect")
        elif event.key in (pygame.K_LEFTBRACKET, pygame.K_MINUS):
            self.set_brush_size(max(1, state.brush_size - 1))
        elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_EQUALS):
            self.set_brush_size(min(3, state.brush_size + 1))
        elif event.key == pygame.K_COMMA:
            self.prev_frame()
        elif event.key == pygame.K_PERIOD:
            self.next_frame()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    global screen
                    screen = pygame.display.set_mode((max(1000, event.w), max(700, event.h)), pygame.RESIZABLE)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_down(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(event)
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
            self.frame()
            clock.tick(60)
        pygame.quit()


if __name__ == "__main__":
    App().run()
