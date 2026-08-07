"""Camera 2D: pan (cx, cy = tọa độ lưới đang ở giữa khung nhìn) + zoom.

Tách riêng khỏi main.py vì đây là 1 tiện ích thuần túy (không phụ thuộc
world/colony/pygame event) - có thể tái sử dụng hoặc test độc lập.
"""
import numpy as np

from . import config as cfg


class Camera2D:
    def __init__(self, cx, cy, zoom=1.0):
        self.cx = cx
        self.cy = cy
        self.zoom = zoom

    def cell_px(self):
        return cfg.BASE_CELL_PX * self.zoom

    def world_to_screen(self, x, y, center_x, center_y):
        cell = self.cell_px()
        sx = center_x + (x - self.cx) * cell
        sy = center_y + (y - self.cy) * cell
        return sx, sy

    def screen_to_world(self, sx, sy, center_x, center_y):
        cell = self.cell_px()
        x = self.cx + (sx - center_x) / cell
        y = self.cy + (sy - center_y) / cell
        return x, y

    def zoom_at(self, factor, mx, my, center_x, center_y):
        wx, wy = self.screen_to_world(mx, my, center_x, center_y)
        self.zoom = float(np.clip(self.zoom * factor, cfg.MIN_ZOOM, cfg.MAX_ZOOM))
        cell = self.cell_px()
        self.cx = wx - (mx - center_x) / cell
        self.cy = wy - (my - center_y) / cell

    def pan(self, dx_px, dy_px):
        cell = self.cell_px()
        self.cx -= dx_px / cell
        self.cy -= dy_px / cell
