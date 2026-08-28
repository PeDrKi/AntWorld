# -*- coding: utf-8 -*-
"""Tab demo "Tìm đường trong mê cung": sinh 1 mê cung chuẩn (perfect maze,
xem maze_generator.py), đặt tổ kiến làm điểm XUẤT PHÁT và 1 miếng thức ăn
làm ĐÍCH, rồi dùng lại NGUYÊN VẸN module pathfinding.py (visibility graph
+ A* any-angle - xem module đó để biết chi tiết thuật toán) để tìm và
minh họa trực quan đường đi ngắn nhất xuyên mê cung.

Tách HOÀN TOÀN khỏi AntColony/SurfaceWorld thật - đây chỉ là 1 bản đồ
MINH HỌA độc lập (world giả lập riêng, không đụng state.surface_world/
state.colony), không ảnh hưởng gì tới ván chơi chính đang chạy song song.
Trước đây có 1 phiên bản rải thẳng mê cung vào bản đồ THẬT (nút "Sinh me
cung" trong toolbar chính) - đã bỏ vì đó là thao tác PHÁ HỦY không thể
hoàn tác (xóa sạch đá/nước/thức ăn đã đặt, nước mất vĩnh viễn) và từng
gây ra hàng loạt lỗi tinh vi khi va chạm với trạng thái đàn kiến SỐNG.
"""
import math
import time

import numpy as np
import pygame

from . import config as cfg
from . import maze_generator
from . import pathfinding
from .fonts import render_cached


class _FakeSurface:
    """Vỏ bọc tối giản - CHỈ có đúng 2 thuộc tính mà
    pathfinding.VisibilityPathfinder cần đọc (terrain, terrain_version) -
    nhờ vậy dùng lại được NGUYÊN thuật toán tìm đường thật của game cho
    bản đồ mê cung demo này, không phải cài đặt lại lần 2."""
    __slots__ = ("terrain", "terrain_version")


class MazeDemo:
    GRID = cfg.GRID_SIZE  # PHẢI khớp cfg.GRID_SIZE - pathfinding.py dùng
                          # thẳng hằng số này (không đọc từ terrain.shape)
                          # để xử lý biên bản đồ, xem VisibilityPathfinder.
    ANT_DISPLAY_SPEED = 0.14  # tốc độ "kiến minh họa" đi trên đường (ô/khung hình)

    def __init__(self):
        self._fake = _FakeSurface()
        self._fake.terrain = np.zeros((self.GRID, self.GRID), dtype=np.int8)
        self._fake.terrain_version = 0
        self.pathfinder = pathfinding.VisibilityPathfinder(self._fake)
        self.show_graph = True
        self.show_grid = True
        self.nest = (0.5, 0.5)
        self.food = (0.5, 0.5)
        self.path = None
        self.path_length = 0.0
        self.search_time_ms = 0.0
        self.build_time_ms = 0.0
        self.anim_t = 0.0
        # KHÔNG gọi regenerate() ở đây - việc dựng visibility graph có thể
        # mất tới ~10 giây ở mật độ mê cung dày nhất (xem maze_generator.
        # generate_perfect_maze), nếu làm ngay trong __init__ thì CẢ GAME
        # sẽ mất chừng đó thời gian để khởi động, kể cả khi người chơi
        # chưa từng mở tab "Demo mê cung". Thay vào đó, chỉ dựng khi thực
        # sự cần - xem ensure_generated(), được gọi từ
        # GameState.switch_tab() đúng lúc người chơi CHUYỂN SANG tab này.
        self._generated = False

    def ensure_generated(self):
        """Dựng mê cung (nếu chưa có) - gọi đúng lúc người chơi thực sự
        cần xem tab này (switch_tab), không phải lúc khởi động game."""
        if not self._generated:
            self.regenerate()
            self._generated = True

    # ------------------------------------------------------------------
    def regenerate(self, seed=None):
        """Sinh mê cung MỚI + chọn lại tổ/thức ăn + tìm lại đường đi. World
        RIÊNG hoàn toàn (self._fake) - không đụng gì tới bản đồ thật đang
        chơi, có thể bấm lại bao nhiêu lần tùy thích, không mất gì cả."""
        rng = np.random.default_rng(seed)
        n = self.GRID
        nest_x, nest_y = n // 2, n // 2

        blocked, _num_cells = maze_generator.generate_perfect_maze(n, nest_x, nest_y, rng)
        self._fake.terrain[:, :] = np.where(blocked, cfg.TERRAIN_ROCK, cfg.TERRAIN_EMPTY)
        self._fake.terrain_version += 1

        self.nest = (float(nest_x) + 0.5, float(nest_y) + 0.5)
        far_cell = maze_generator.farthest_point(blocked, (nest_x, nest_y))
        self.food = (float(far_cell[0]) + 0.5, float(far_cell[1]) + 0.5)

        t0 = time.perf_counter()
        # _rebuild_if_needed (dựng visibility graph, phần TỐN THỜI GIAN
        # NHẤT - có thể tới ~10s ở mật độ mê cung dày nhất) nằm trong lần
        # gọi find_path đầu tiên này - đo RIÊNG để hiển thị cho người xem
        # biết đâu là chi phí "dựng đồ thị 1 lần" so với "tìm đường".
        self.pathfinder._rebuild_if_needed()
        self.build_time_ms = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        self.path = self.pathfinder.find_path(self.nest, self.food)
        self.search_time_ms = (time.perf_counter() - t0) * 1000.0

        self.path_length = 0.0
        if self.path:
            pts = [self.nest] + self.path
            self.path_length = sum(
                math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                for i in range(len(pts) - 1)
            )
        self.anim_t = 0.0

    # ------------------------------------------------------------------
    def step(self):
        """Gọi 1 lần mỗi khung hình (bất kể mô phỏng chính có tạm dừng
        hay không) để "kiến minh họa" tiếp tục bò dọc đường đi đã tìm
        được; tới đích thì dừng khựng lại 1 chút rồi tự quay lại từ tổ."""
        if not self.path:
            return
        self.anim_t += self.ANT_DISPLAY_SPEED
        if self.anim_t > self.path_length + 25:
            self.anim_t = 0.0

    def ant_position(self):
        """Vị trí (x, y) hiện tại của kiến minh họa trên đường đi, ứng với
        self.anim_t (đứng yên tại đích nếu đã đi hết đường)."""
        if not self.path:
            return self.nest
        pts = [self.nest] + self.path
        remaining = min(self.anim_t, self.path_length)
        for i in range(len(pts) - 1):
            seg = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            if seg < 1e-9:
                continue
            if remaining <= seg:
                t = remaining / seg
                return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t,
                        pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
            remaining -= seg
        return self.food

    # ------------------------------------------------------------------
    def _compute_transform(self, screen_w, canvas_h):
        margin = 46
        info_h = 18 + 20 * 4 + 14  # chừa đủ chỗ cho hộp thông tin (4 dòng) bên dưới bàn cờ
        bottom_reserve = info_h + 80  # + chỗ cho panel "Che do xem" (luôn
                                       # đặt cố định giữa-dưới màn hình,
                                       # xem hud.build_toolbar) để không
                                       # bao giờ đè lên hộp thông tin
        avail_w = max(50, screen_w - 2 * margin)
        avail_h = max(50, canvas_h - margin - bottom_reserve)
        scale = min(avail_w / self.GRID, avail_h / self.GRID)
        ox = (screen_w - self.GRID * scale) / 2.0
        oy = margin + max(0, (avail_h - self.GRID * scale) / 2.0)
        return scale, ox, oy

    def render(self, state, surf):
        scale, ox, oy = self._compute_transform(state.SCREEN_W, state.CANVAS_H)

        def to_px(pt):
            return (ox + pt[0] * scale, oy + pt[1] * scale)

        board = pygame.Rect(int(ox), int(oy), int(self.GRID * scale) + 1, int(self.GRID * scale) + 1)
        pygame.draw.rect(surf, (58, 48, 34), board)

        # --- Tường mê cung ---
        blocked_idx = np.argwhere(self._fake.terrain != cfg.TERRAIN_EMPTY)
        wall_rect_w = int(math.ceil(scale)) + 1
        for x, y in blocked_idx:
            r = pygame.Rect(int(ox + x * scale), int(oy + y * scale), wall_rect_w, wall_rect_w)
            pygame.draw.rect(surf, (96, 88, 78), r)

        if self.show_grid and scale >= 6:
            grid_color = (70, 62, 48)
            for i in range(self.GRID + 1):
                x = int(ox + i * scale)
                pygame.draw.line(surf, grid_color, (x, int(oy)), (x, int(oy + self.GRID * scale)))
                y = int(oy + i * scale)
                pygame.draw.line(surf, grid_color, (int(ox), y), (int(ox + self.GRID * scale), y))

        # --- Các đỉnh của visibility graph (minh họa cách thuật toán chỉ
        # xét GÓC LỒI của vật cản, không phải toàn bộ ô lưới) ---
        if self.show_graph:
            for vx, vy in self.pathfinder._vertices:
                px, py = to_px((vx, vy))
                pygame.draw.circle(surf, (110, 150, 190), (int(px), int(py)), 2)

        # --- Đường đi tìm được (any-angle - có thể "chéo" qua nhiều ô) ---
        if self.path:
            pts_px = [to_px(self.nest)] + [to_px(p) for p in self.path]
            if len(pts_px) >= 2:
                pygame.draw.lines(surf, (255, 205, 80), False, pts_px, max(2, int(scale * 0.14)))
            for p in pts_px[1:-1]:
                pygame.draw.circle(surf, (255, 205, 80), (int(p[0]), int(p[1])), max(3, int(scale * 0.16)))
        else:
            msg = render_cached(state.font, "Khong tim duoc duong (bi vay kin hoan toan)", (255, 120, 110))
            surf.blit(msg, (ox, oy - 26))

        # --- Tổ kiến (điểm xuất phát) ---
        nx_px, ny_px = to_px(self.nest)
        rad = max(7, int(scale * 0.4))
        pygame.draw.circle(surf, (120, 200, 255), (int(nx_px), int(ny_px)), rad)
        pygame.draw.circle(surf, (15, 15, 15), (int(nx_px), int(ny_px)), rad, width=2)
        lbl = render_cached(state.font_small, "To", (235, 245, 255))
        surf.blit(lbl, (nx_px - lbl.get_width() / 2, ny_px - rad - 16))

        # --- Thức ăn (đích) ---
        fx_px, fy_px = to_px(self.food)
        pygame.draw.circle(surf, (140, 230, 130), (int(fx_px), int(fy_px)), rad)
        pygame.draw.circle(surf, (15, 15, 15), (int(fx_px), int(fy_px)), rad, width=2)
        lbl2 = render_cached(state.font_small, "Thuc an", (235, 255, 235))
        surf.blit(lbl2, (fx_px - lbl2.get_width() / 2, fy_px - rad - 16))

        # --- Kiến minh họa đang bò dọc đường đi ---
        axp, ayp = to_px(self.ant_position())
        arad = max(5, int(scale * 0.3))
        pygame.draw.circle(surf, (250, 250, 250), (int(axp), int(ayp)), arad)
        pygame.draw.circle(surf, (35, 30, 25), (int(axp), int(ayp)), arad, width=2)

        # --- Thông tin thuật toán ---
        info_lines = [
            f"So dinh visibility graph: {len(self.pathfinder._vertices)}",
            f"Do dai duong di: {self.path_length:.2f} o (any-angle, khong rang cua)",
            f"Thoi gian dung do thi (1 lan/me cung): {self.build_time_ms:.0f} ms",
            f"Thoi gian tim duong (truy van nay): {self.search_time_ms:.2f} ms",
        ]
        panel_w = 420
        panel_h = 18 + 20 * len(info_lines)
        info_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        info_surf.fill((18, 18, 22, 210))
        for i, line in enumerate(info_lines):
            txt = render_cached(state.font_small, line, (225, 225, 230))
            info_surf.blit(txt, (10, 8 + i * 20))
        surf.blit(info_surf, (int(ox), int(oy + self.GRID * scale + 10)))
