# -*- coding: utf-8 -*-
"""
AntWorld Pixel Studio - ban Python (Pygame)
=============================================
Ban chuyen the tu cong cu ve pixel art antworld_pixel_studio.html sang
mot ung dung Python doc lap, dung chung engine (pygame) voi game AntWorld
de khong phai them thu vien nao moi va xuat PNG tuong thich 100% voi
sprite_manager.py cua game (nen trong suot, dung ten file theo quy uoc).

CACH CHAY:
    python pixel_editor.py

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

from sprite_data import PALETTE_GROUPS, PRESET_SPRITES, DEFAULT_PIXELS

# ------------------------------------------------------------------
# Duong dan xuat file - dung dung thu muc assets/sprites/ ma
# sprite_manager.py cua game AntWorld doc.
# ------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

FONT_NAME = None  # dung font mac dinh he thong (co ho tro Unicode co ban)

pygame.init()
pygame.display.set_caption("AntWorld Pixel Studio (Python)")

WIN_W, WIN_H = 1360, 860
screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.RESIZABLE)
clock = pygame.time.Clock()

font_small = pygame.font.SysFont(FONT_NAME, 13)
font_normal = pygame.font.SysFont(FONT_NAME, 15)
font_bold = pygame.font.SysFont(FONT_NAME, 15, bold=True)
font_title = pygame.font.SysFont(FONT_NAME, 20, bold=True)
font_mono = pygame.font.SysFont("consolas,couriernew,monospace", 12)


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
    __slots__ = ("size", "pixels", "label")

    def __init__(self, size, label):
        self.size = size
        self.pixels = [None] * (size * size)
        self.label = label


class AppState:
    def __init__(self):
        self.sprites = {}
        self.order = []
        self.current = None
        self.tool = "pencil"
        self.color = "#d77820"
        self.zoom = 20
        self.show_grid = True
        self.symmetry_h = False
        self.symmetry_v = False
        self.painting = False
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
        h = self.history[self.current]
        h["undo"].append(self.sp().pixels[:])
        if len(h["undo"]) > 60:
            h["undo"].pop(0)
        h["redo"].clear()

    def undo(self):
        h = self.history[self.current]
        if not h["undo"]:
            return
        h["redo"].append(self.sp().pixels[:])
        self.sp().pixels = h["undo"].pop()

    def redo(self):
        h = self.history[self.current]
        if not h["redo"]:
            return
        h["undo"].append(self.sp().pixels[:])
        self.sp().pixels = h["redo"].pop()

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
            self.set_pixel(x, y, self.color)
        elif self.tool == "eraser":
            self.set_pixel(x, y, None)
        elif self.tool == "fill":
            if is_start:
                self.flood_fill(x, y, self.color)
        elif self.tool == "eyedropper":
            if is_start:
                c = sp.pixels[y * sp.size + x]
                if c:
                    self.color = c
                    self.toast(f"Da hut mau: {c}")
                else:
                    self.toast("O nay dang trong (trong suot)")


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
        img = self.font.render(self.label, True, text_col)
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
        self.right_scroll = 0
        self.buttons = []
        self.swatches = []
        self.tab_buttons = []
        self.size_buttons = []
        self.canvas_rect = pygame.Rect(0, 0, 0, 0)
        self.preview_game_rect = pygame.Rect(0, 0, 0, 0)
        self.preview_big_rect = pygame.Rect(0, 0, 0, 0)
        self.running = True

    # ---------- actions ----------
    def set_tool(self, name):
        state.tool = name

    def set_color(self, hexcolor):
        state.color = hexcolor
        self.hexinput_box.text = hexcolor

    def set_transparent(self):
        state.color = None
        state.toast('Dang ve = xoa (trong suot) - nhu tay')

    def select_sprite(self, name):
        state.current = name
        self.rename_box.text = state.sp().label

    def clear_canvas(self):
        state.push_history()
        sp = state.sp()
        sp.pixels = [None] * (sp.size * sp.size)
        state.toast("Da xoa toan bo canvas")

    def dup_sprite(self):
        sp = state.sp()
        name = state.new_sprite(state.current + "_copy", sp.size, sp.label + " (2)")
        state.sprites[name].pixels = sp.pixels[:]
        self.select_sprite(name)
        state.toast("Da nhan ban sprite")

    def del_sprite(self):
        if len(state.order) <= 1:
            state.toast("Phai con it nhat 1 sprite")
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
        state.toast(f'Da doi ten hien thi (ten file xuat van la "{state.current}.png")')

    def apply_hex_color(self):
        txt = self.hexinput_box.text.strip()
        if not txt.startswith("#"):
            txt = "#" + txt
        if len(txt) == 7:
            try:
                hex_to_rgb(txt)
                self.set_color(txt)
                state.toast(f"Da chon mau {txt}")
            except Exception:
                state.toast("Ma mau khong hop le (dung dang #rrggbb)")
        else:
            state.toast("Ma mau khong hop le (dung dang #rrggbb)")

    def resize_canvas(self, new_size):
        sp = state.sp()
        if sp.size == new_size:
            return
        sp.size = new_size
        sp.pixels = [None] * (new_size * new_size)
        state.history[state.current] = {"undo": [], "redo": []}
        state.toast(f"Da doi kich thuoc canvas sang {new_size}x{new_size} (canvas duoc lam trong)")

    def change_zoom(self, delta):
        state.zoom = max(6, min(40, state.zoom + delta))

    def toggle_symmetry_h(self):
        state.symmetry_h = not state.symmetry_h

    def toggle_symmetry_v(self):
        state.symmetry_v = not state.symmetry_v

    def toggle_grid(self):
        state.show_grid = not state.show_grid

    # ---------- export ----------
    def sprite_to_surface(self, sp):
        surf = pygame.Surface((sp.size, sp.size), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        for y in range(sp.size):
            for x in range(sp.size):
                c = sp.pixels[y * sp.size + x]
                if c:
                    surf.set_at((x, y), hex_to_rgba(c, 255))
        return surf

    def ensure_dir(self):
        os.makedirs(SPRITES_DIR, exist_ok=True)

    def export_native(self):
        self.ensure_dir()
        sp = state.sp()
        surf = self.sprite_to_surface(sp)
        path = os.path.join(SPRITES_DIR, f"{state.current}.png")
        pygame.image.save(surf, path)
        state.toast(f"Da luu: assets/sprites/{state.current}.png")

    def export_big(self):
        self.ensure_dir()
        sp = state.sp()
        surf = self.sprite_to_surface(sp)
        big = pygame.transform.scale(surf, (sp.size * 8, sp.size * 8))
        path = os.path.join(SPRITES_DIR, f"{state.current}@8x.png")
        pygame.image.save(big, path)
        state.toast(f"Da luu ban phong to 8x: assets/sprites/{state.current}@8x.png")

    def export_all(self):
        self.ensure_dir()
        for name in state.order:
            surf = self.sprite_to_surface(state.sprites[name])
            pygame.image.save(surf, os.path.join(SPRITES_DIR, f"{name}.png"))
        # sprite sheet tong hop (tham khao nhanh, khong dung de game doc)
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
            img = font_mono.render(name, True, COL_TEXT)
            sheet.blit(img, (ox, oy + cell + 2))
        pygame.image.save(sheet, os.path.join(SPRITES_DIR, "antworld_sprite_sheet.png"))
        state.toast(f"Da luu TOAN BO {len(state.order)} sprite + 1 sprite sheet vao assets/sprites/")

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
        draw_text(screen, "CONG CU", (x0, y), font_small, COL_TEXT_DIM)
        y += 20
        tool_w = (w - 6) // 2
        tools = [("pencil", "Bg But (B)"), ("eraser", "Tay (E)"),
                 ("fill", "Do mau (G)"), ("eyedropper", "Hut mau (I)")]
        tools = [("pencil", "But (B)"), ("eraser", "Tay (E)"),
                 ("fill", "Do mau (G)"), ("eyedropper", "Hut mau (I)")]
        for i, (key, label) in enumerate(tools):
            col, row = i % 2, i // 2
            rect = (x0 + col * (tool_w + 6), y + row * 34, tool_w, 30)
            self.buttons.append(Button(rect, label, (lambda k=key: self.set_tool(k)),
                                        active=(state.tool == key), font=font_small))
        y += 34 * 2 + 16

        draw_text(screen, "CHINH SUA", (x0, y), font_small, COL_TEXT_DIM)
        y += 20
        self.buttons.append(Button((x0, y, w, 30), "Hoan tac (Ctrl+Z)", state.undo, font=font_small))
        y += 34
        self.buttons.append(Button((x0, y, w, 30), "Lam lai (Ctrl+Y)", state.redo, font=font_small))
        y += 34
        self.buttons.append(Button((x0, y, w, 30),
                                    f"Doi xung ngang: {'BAT' if state.symmetry_h else 'TAT'}",
                                    self.toggle_symmetry_h, active=state.symmetry_h, font=font_small))
        y += 34
        self.buttons.append(Button((x0, y, w, 30),
                                    f"Doi xung doc: {'BAT' if state.symmetry_v else 'TAT'}",
                                    self.toggle_symmetry_v, active=state.symmetry_v, font=font_small))
        y += 34
        self.buttons.append(Button((x0, y, w, 30), "Xoa toan bo canvas", self.clear_canvas,
                                    danger=True, font=font_small))
        y += 44

        draw_text(screen, "HIEN THI", (x0, y), font_small, COL_TEXT_DIM)
        y += 20
        draw_text(screen, f"Thu phong: {state.zoom}px", (x0, y), font_small, COL_TEXT)
        y += 20
        self.buttons.append(Button((x0, y, 34, 26), "-", lambda: self.change_zoom(-2), font=font_normal))
        self.buttons.append(Button((x0 + w - 34, y, 34, 26), "+", lambda: self.change_zoom(2), font=font_normal))
        y += 34
        self.buttons.append(Button((x0, y, w, 30), f"Luoi: {'BAT' if state.show_grid else 'TAT'}",
                                    self.toggle_grid, active=state.show_grid, font=font_small))
        y += 44

        draw_text(screen, "KICH THUOC CANVAS", (x0, y), font_small, COL_TEXT_DIM)
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
        hint = "Doi kich thuoc se lam trong canvas cua sprite dang chon."
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
        rx = self.W - self.right_w + 12
        y = self.header_h + 12 - self.right_scroll
        w = self.right_w - 24

        top = y
        draw_text(screen, "MAU DANG CHON", (rx, y), font_small, COL_TEXT_DIM)
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
        y += 40
        self.buttons.append(Button((rx, y, w, 26), "Ap dung ma mau (Enter)", self.apply_hex_color, font=font_small))
        y += 32
        self.buttons.append(Button((rx, y, w, 28), 'Chon "trong suot" (tay)', self.set_transparent,
                                    active=(state.color is None), font=font_small))
        y += 40

        draw_text(screen, "BANG MAU GAME (bam de chon)", (rx, y), font_small, COL_TEXT_DIM)
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
        self.buttons.append(Button((x0 + 228, y, 100, 28), "Doi ten", self.apply_rename, font=font_small))
        self.buttons.append(Button((x0 + 334, y, 100, 28), "Nhan ban", self.dup_sprite, font=font_small))
        self.buttons.append(Button((x0 + 440, y, 110, 28), "Xoa sprite", self.del_sprite,
                                    danger=True, font=font_small))
        hint = f'se xuat ra: {state.current}.png'
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
        draw_text(screen, "XEM THAT (nhu trong game)", (pcx, y0), font_small, COL_TEXT_DIM)
        self.preview_game_rect = pygame.Rect(pcx, y0 + 18, sp.size * 4, sp.size * 4)
        draw_text(screen, "XEM 8x", (pcx, self.preview_game_rect.bottom + 10), font_small, COL_TEXT_DIM)
        self.preview_big_rect = pygame.Rect(pcx, self.preview_game_rect.bottom + 28, sp.size * 8, sp.size * 8)

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
        for y in range(sp.size):
            for x in range(sp.size):
                c = sp.pixels[y * sp.size + x]
                if c:
                    r = (self.canvas_rect.x + x * z, self.canvas_rect.y + y * z, z, z)
                    pygame.draw.rect(screen, hex_to_rgb(c), r)
        if state.show_grid and z >= 6:
            grid_col = (0, 0, 0, 90)
            gs = pygame.Surface(self.canvas_rect.size, pygame.SRCALPHA)
            for i in range(sp.size + 1):
                pygame.draw.line(gs, grid_col, (i * z, 0), (i * z, sp.size * z))
                pygame.draw.line(gs, grid_col, (0, i * z), (sp.size * z, i * z))
            screen.blit(gs, self.canvas_rect.topleft)
        pygame.draw.rect(screen, COL_BORDER, self.canvas_rect, width=2)

        # preview boxes
        for rect, scale in ((self.preview_game_rect, 4), (self.preview_big_rect, 8)):
            pygame.draw.rect(screen, COL_CANVAS_BG, rect.inflate(4, 4))
            for y in range(sp.size):
                for x in range(sp.size):
                    c = sp.pixels[y * sp.size + x]
                    if c:
                        pygame.draw.rect(screen, hex_to_rgb(c),
                                          (rect.x + x * scale, rect.y + y * scale, scale, scale))
            pygame.draw.rect(screen, COL_BORDER, rect, width=1)

    def build_footer(self):
        y = self.H - self.footer_h + 8
        self.buttons.append(Button((16, y, 230, 30), "Luu PNG (kich thuoc goc)", self.export_native, font=font_small))
        self.buttons.append(Button((256, y, 230, 30), "Luu PNG (phong to 8x)", self.export_big, font=font_small))
        self.buttons.append(Button((496, y, 260, 30), "Luu TOAN BO + sprite sheet", self.export_all, font=font_small))

    def draw_header(self):
        pygame.draw.rect(screen, (28, 22, 15), (0, 0, self.W, self.header_h))
        pygame.draw.line(screen, COL_BORDER, (0, self.header_h), (self.W, self.header_h), 2)
        draw_text(screen, "ANTWORLD PIXEL STUDIO", (18, 16), font_title, COL_ACCENT2)
        draw_text(screen, "Ve asset pixel art cho game dan kien", (330, 20), font_small, COL_TEXT_DIM)
        hint = "B but * E tay * G do mau * I hut mau * Ctrl+Z hoan tac"
        hint_w = font_small.size(hint)[0]
        draw_text(screen, hint, (self.W - hint_w - 18, 20), font_small, COL_TEXT_DIM)

    def draw_footer(self):
        y = self.H - self.footer_h
        pygame.draw.rect(screen, (28, 22, 15), (0, y, self.W, self.footer_h))
        pygame.draw.line(screen, COL_BORDER, (0, y), (self.W, y), 2)
        msg = "assets/sprites/"
        draw_text(screen, f"Xuat file vao: {SPRITES_DIR}", (770, y + 15), font_small, COL_TEXT_DIM,
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
        screen.fill(COL_BG)
        self.draw_panel_backgrounds()
        self.draw_header()
        self.buttons = []
        self.build_left_panel()
        self.build_tabs()
        self.build_canvas_toolbar()
        self.build_canvas()
        self.draw_canvas()
        self.build_right_panel()
        self.build_footer()

        mouse_pos = pygame.mouse.get_pos()
        for b in self.buttons:
            b.update_hover(mouse_pos)
            b.draw(screen)
        for sw in self.swatches:
            sw.hover = pygame.Rect(sw.rect).collidepoint(mouse_pos)
            sw.draw(screen, selected=(state.color == sw.hexcolor))

        self.draw_footer()
        self.draw_toast()
        pygame.display.flip()

    def handle_mouse_down(self, event):
        pos = event.pos
        if event.button == 1:
            for b in self.buttons:
                if b.rect.collidepoint(pos):
                    b.on_click()
                    return
            for sw in self.swatches:
                if pygame.Rect(sw.rect).collidepoint(pos):
                    sw.on_click(sw.hexcolor)
                    return
            if self.hexinput_box.rect.collidepoint(pos):
                self.hexinput_box.active = True
                self.rename_box.active = False
                return
            if self.rename_box.rect.collidepoint(pos):
                self.rename_box.active = True
                self.hexinput_box.active = False
                return
            self.hexinput_box.active = False
            self.rename_box.active = False
            cell = self.cell_from_pos(pos)
            if cell:
                state.push_history()
                state.painting = True
                state.apply_tool_at(cell[0], cell[1], True)
        elif event.button == 3:
            # chuot phai = tay nhanh
            cell = self.cell_from_pos(pos)
            if cell:
                state.push_history()
                state.set_pixel(cell[0], cell[1], None)
        elif event.button == 4:
            if self.canvas_rect.collidepoint(pos):
                self.change_zoom(2)
            else:
                self.right_scroll = max(0, self.right_scroll - 25)
        elif event.button == 5:
            if self.canvas_rect.collidepoint(pos):
                self.change_zoom(-2)
            else:
                self.right_scroll = min(getattr(self, "right_content_h", 0), self.right_scroll + 25)

    def handle_mouse_up(self, event):
        if event.button == 1:
            state.painting = False

    def handle_mouse_motion(self, event):
        if state.painting and (state.tool in ("pencil", "eraser")):
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
