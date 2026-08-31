"""Widget UI đơn giản dùng chung cho thanh công cụ (pygame.Rect + text).

Tách riêng khỏi main.py vì đây là tiện ích UI thuần túy, không phụ thuộc
world/colony - có thể tái sử dụng cho các panel khác nếu cần.
"""
import pygame

from .fonts import render_cached

COLOR_BTN = (40, 40, 45)
COLOR_BTN_ACTIVE = (70, 130, 180)

# Mỗi "style" là (mau_khong_active, mau_active, mau_vien) - dùng để NHÓM
# các nút theo MÀU SẮC để mắt nhận ra ngay từng nhóm chức năng, thay vì
# tất cả cùng 1 màu xám như trước (khó phân biệt "đặt vật thể" với "bật/
# tắt" hay "điều khiển thời gian"):
#   - "place"  : các công cụ ĐẶT lên mặt đất (thức ăn/đá/nước/đào phòng) -
#                tông màu đất/cam ấm, gợi liên tưởng "vật chất trên nền đất"
#   - "danger" : hành động có tính "rủi ro/tấn công" (thả kẻ thù) - đỏ
#   - "tool"   : công cụ THAO TÁC/CHỌN (xóa, theo dõi) - xanh dương
#   - "time"   : điều khiển thời gian (tạm dừng, tốc độ) - tím
#   - "toggle" : công tắc BẬT/TẮT (đỏ = TẮT, xanh lá = BẬT - đúng trực giác
#                đèn giao thông, không cần đọc chữ mới biết trạng thái)
#   - "nav"    : điều hướng camera/tầng - vàng đồng
BUTTON_STYLES = {
    "default": ((40, 40, 45), (70, 130, 180), (90, 90, 100)),
    "place": ((54, 58, 40), (205, 125, 40), (98, 106, 70)),
    "danger": ((58, 40, 40), (205, 70, 55), (108, 74, 74)),
    "tool": ((40, 50, 58), (64, 145, 205), (84, 104, 124)),
    "time": ((46, 42, 58), (150, 110, 220), (100, 90, 125)),
    "toggle": ((66, 42, 42), (54, 158, 86), (110, 84, 84)),
    "nav": ((58, 52, 30), (205, 165, 60), (112, 100, 62)),
}


def draw_pixel_rect(surf, rect, fill_color, border_color=None, border_width=1, bevel=True):
    """Vẽ 1 khối chữ nhật GÓC VUÔNG (không bo tròn) kiểu UI pixel-art cổ
    điển - tùy chọn thêm "bevel" (viền sáng ở cạnh trên/trái, viền tối ở
    cạnh dưới/phải) để trông như 1 nút bấm nổi khối 8-bit thay vì 1 khối
    màu phẳng lì. Dùng THAY cho mọi chỗ trước đây gọi
    `pygame.draw.rect(..., border_radius=N)` - toàn bộ game (panel, nút,
    thanh máu/năng lượng, ô tầng...) đổi sang cùng 1 kiểu bo góc vuông này
    để đồng nhất phong cách pixel art xuyên suốt, thay vì chỉ sprite nhân
    vật là pixel còn khung UI lại bo tròn/mượt hiện đại."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, fill_color, rect)
    if bevel and rect.w > 2 and rect.h > 2:
        light = tuple(min(255, c + 40) for c in fill_color[:3])
        dark = tuple(max(0, c - 40) for c in fill_color[:3])
        pygame.draw.line(surf, light, rect.topleft, (rect.right - 1, rect.top))
        pygame.draw.line(surf, light, rect.topleft, (rect.left, rect.bottom - 1))
        pygame.draw.line(surf, dark, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
        pygame.draw.line(surf, dark, (rect.right - 1, rect.top), (rect.right - 1, rect.bottom - 1))
    if border_color is not None and border_width > 0:
        pygame.draw.rect(surf, border_color, rect, width=border_width)


class Button:
    def __init__(self, rect, text, on_click=None, toggle=False, active=False, style="default"):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.toggle = toggle
        self.active = active
        self.style = style  # xem BUTTON_STYLES ở trên
        # Vị trí TƯƠNG ĐỐI so với panel chứa nó (góc trên-trái nội dung
        # panel) - dùng khi nút này thuộc 1 Panel có thể kéo di chuyển được
        # (xem Panel.reposition_children() bên dưới). None nếu nút đứng
        # độc lập, không thuộc panel nào (vị trí luôn cố định như cũ).
        self.rel_pos = None

    def bind_to_panel(self, panel, rel_x, rel_y):
        """Gắn nút này vào 1 Panel tại vị trí tương đối (rel_x, rel_y) tính
        từ góc trên-trái phần NỘI DUNG (dưới thanh tiêu đề) của panel."""
        self.rel_pos = (rel_x, rel_y)
        panel.children.append(self)
        self.reposition(panel)

    def reposition(self, panel):
        if self.rel_pos is None:
            return
        cx, cy = panel.content_pos()
        self.rect.topleft = (cx + self.rel_pos[0], cy + self.rel_pos[1])

    def draw(self, surf, font):
        base, active_c, border = BUTTON_STYLES.get(self.style, BUTTON_STYLES["default"])
        color = active_c if self.active else base
        draw_pixel_rect(surf, self.rect, color, border, border_width=2 if self.active else 1)
        label = render_cached(font, self.text, (250, 250, 250))
        lr = label.get_rect(center=self.rect.center)
        surf.blit(label, lr)

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            if self.on_click:
                self.on_click()
            return True
        return False


class Panel:
    """1 "cửa sổ" nổi trên màn hình (không phải cửa sổ hệ điều hành thật -
    pygame chỉ có 1 cửa sổ duy nhất - mà là 1 khung UI có thanh tiêu đề,
    KÉO DI CHUYỂN được tới bất kỳ đâu trong màn hình, và THU GỌN được lại
    chỉ còn thanh tiêu đề) để người chơi tự sắp xếp, tránh che khuất khung
    nhìn mô phỏng. Dùng cho thanh công cụ / bảng thống kê / biểu đồ."""

    TITLE_H = 26

    def __init__(self, x, y, w, h, title, collapsed=False):
        self.x, self.y = x, y
        self.w, self.h = w, h  # kích thước lúc MỞ RỘNG (không tính title bar)
        self.title = title
        self.collapsed = collapsed
        self.dragging = False
        self.drag_offset = (0, 0)
        self.children = []  # các Button gắn vào panel này (xem bind_to_panel)
        # Cache nen mo (SRCALPHA) cua draw_frame() - key (w, h) cua LAN
        # DUNG GAN NHAT, chi tao lai Surface khi kich thuoc panel THAY DOI
        # (resize/thu gon), thay vi MOI KHUNG HINH deu cap phat + fill 1
        # Surface SRCALPHA moi (rat ton kem, do thuc te ~60 lan/giay x so
        # panel dang mo). Vi vi tri panel co the DI CHUYEN (keo) nhung
        # KICH THUOC (w,h) hau nhu khong doi khi keo, cache theo (w,h) la
        # du, khong can theo (x,y).
        self._bg_cache_key = None
        self._bg_cache_surf = None

    def outer_rect(self):
        h = self.TITLE_H if self.collapsed else self.TITLE_H + self.h
        return pygame.Rect(int(self.x), int(self.y), self.w, h)

    def content_pos(self):
        return (int(self.x), int(self.y) + self.TITLE_H)

    def title_bar_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.TITLE_H)

    def collapse_button_rect(self):
        r = self.title_bar_rect()
        return pygame.Rect(r.right - 24, r.top + 3, 20, 20)

    def reposition_children(self):
        for b in self.children:
            b.reposition(self)

    def move_to(self, x, y, screen_w, screen_h):
        """Di chuyển panel tới (x, y), giữ nguyên trong màn hình (không cho
        kéo thanh tiêu đề ra ngoài khung nhìn, mất luôn không tìm lại được)."""
        self.x = float(max(0, min(x, screen_w - self.w)))
        self.y = float(max(0, min(y, screen_h - self.TITLE_H)))
        self.reposition_children()

    # --- Xử lý sự kiện chuột - GỌI TRƯỚC khi xử lý sự kiện của canvas mô
    # phỏng bên dưới, để việc kéo/thu gọn panel KHÔNG bị "xuyên" xuống dưới
    # thành thao tác đặt thức ăn/đào phòng/v.v. ---
    def handle_mousedown(self, pos):
        """Trả True nếu sự kiện này thuộc về panel (đã xử lý xong, không
        cho lan xuống canvas nữa), False nếu bấm ở ngoài panel."""
        if not self.outer_rect().collidepoint(pos):
            return False
        if self.collapse_button_rect().collidepoint(pos):
            self.collapsed = not self.collapsed
            return True
        if self.title_bar_rect().collidepoint(pos):
            self.dragging = True
            self.drag_offset = (pos[0] - self.x, pos[1] - self.y)
            return True
        if self.collapsed:
            return True  # thu gọn rồi thì cả thân coi như title bar
        for b in self.children:
            if b.handle_click(pos):
                return True
        return True  # bấm vào khoảng trống trong panel cũng "nuốt" sự kiện

    def handle_mouseup(self):
        self.dragging = False

    def handle_mousemotion(self, pos, screen_w, screen_h):
        if self.dragging:
            self.move_to(pos[0] - self.drag_offset[0], pos[1] - self.drag_offset[1], screen_w, screen_h)

    def contains(self, pos):
        return self.outer_rect().collidepoint(pos)

    def draw_frame(self, surf, font_title):
        """Vẽ khung + thanh tiêu đề (KHÔNG vẽ nội dung bên trong - nội dung
        do nơi gọi tự vẽ vào vùng content_pos()/content_rect, sau khi gọi
        hàm này, để mỗi panel tự quyết cách vẽ nội dung riêng của nó)."""
        r = self.outer_rect()
        cache_key = (r.w, r.h)
        if self._bg_cache_key != cache_key:
            bg = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            bg.fill((18, 18, 22, 232))
            self._bg_cache_surf = bg
            self._bg_cache_key = cache_key
        surf.blit(self._bg_cache_surf, r.topleft)
        pygame.draw.rect(surf, (90, 90, 100), r, width=1)

        tb = self.title_bar_rect()
        pygame.draw.rect(surf, (42, 42, 50), tb)
        pygame.draw.rect(surf, (90, 90, 100), tb, width=1)
        # Chấm "tay cầm" nhỏ để gợi ý có thể kéo, tránh người chơi không
        # biết panel này di chuyển được - vẽ Ô VUÔNG nhỏ (không phải chấm
        # tròn) để nhất quán với phong cách pixel-art góc vuông của toàn
        # bộ UI, thay vì lẫn 1 chi tiết tròn mượt vào giữa các khối vuông
        for i in range(3):
            pygame.draw.rect(surf, (140, 140, 150), (tb.x + 9, tb.y + 7 + i * 5, 2, 2))
        label = render_cached(font_title, self.title, (235, 235, 235))
        surf.blit(label, (tb.x + 20, tb.y + 5))

        cb = self.collapse_button_rect()
        draw_pixel_rect(surf, cb, (60, 60, 72), (100, 100, 112))
        symbol = "+" if self.collapsed else "-"
        sym = render_cached(font_title, symbol, (230, 230, 230))
        surf.blit(sym, sym.get_rect(center=cb.center))
