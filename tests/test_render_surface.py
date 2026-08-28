# -*- coding: utf-8 -*-
"""Test cho render_surface.py - tap trung vao duong ve THUC AN/DIA HINH
khi KHONG co sprite tuy chinh (chi con lai duong ve hinh vuong mau phang
du phong).

Boi canh: duong ve nay TUNG BI LOI (pygame.draw.rect nem
"TypeError: rect argument is invalid") vi cac gia tri toa do man hinh
duoc tinh hang loat bang numpy (world_to_screen voi mang numpy dau vao)
tra ve numpy.float32 thay vi float thuong - nhung loi nay KHONG LO RA
trong qua trinh test/choi thu thong thuong vi assets/sprites/food.png
LUON co san, nen nhanh ve sprite luon duoc chon thay vi nhanh du phong.
Loi chi lo ra khi them loai thuc an THU HAI (NECTAR - xem
_use_sprite_for_food_type trong render_surface.py) buoc phai di qua
nhanh ve hinh vuong mau phang do.

Test o day CHU DONG vo hieu hoa sprite (gia lap "khong co sprite tuy
chinh") de dam bao nhanh du phong nay luon duoc kiem tra, khong phu
thuoc vao viec assets/sprites/ co file gi.
"""
import unittest

import numpy as np
import pygame

from antworld import config as cfg
from antworld.game_state import GameState
from antworld.render_surface import draw_surface_layer


class _NoSpriteStub:
    """Gia lap SpriteManager luon bao KHONG co sprite nao - buoc
    draw_surface_layer() di qua moi nhanh ve vector du phong (hinh vuong/
    hinh tron mau phang), bat ke may test co san file .png trong
    assets/sprites/ hay khong."""

    def has(self, filename):
        return False

    def get_static(self, filename, size_px):
        return None

    def get_rotated(self, filename, size_px, angle_deg, step_deg=10):
        return None


class TestDrawSurfaceLayerWithoutSprites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.state = GameState()
        self.state.sprites = _NoSpriteStub()

    def test_draw_with_both_food_types_present_no_sprite(self):
        """Ve toan bo lop mat dat (dia hinh + 2 loai thuc an + kien) khi
        KHONG co sprite nao - phai chay xong khong nem loi, bat ke vi tri
        camera/zoom nao. Day chinh la kich ban tung crash (xem docstring
        module) truoc khi sua loi ep kieu numpy.float32 -> float."""
        surf = self.state.surface_world
        # Dam bao CHAC CHAN co mat ca 2 loai thuc an tren ban do (khong
        # phu thuoc may man cua random seed) truoc khi ve thu.
        surf.food[5:8, 5:8] = 5.0
        surf.food_type[5:8, 5:8] = cfg.FOOD_TYPE_SEED
        surf.food[20:23, 25:28] = 5.0
        surf.food_type[20:23, 25:28] = cfg.FOOD_TYPE_NECTAR

        for zoom in (0.5, 1.0, 2.5):
            self.state.camera.zoom = zoom
            for cx, cy in ((20, 20), (6, 6), (26, 26)):
                self.state.camera.cx, self.state.camera.cy = float(cx), float(cy)
                screen = self.state.screen
                screen.fill(cfg.COLOR_BG_SURFACE)
                try:
                    draw_surface_layer(self.state, screen)
                except TypeError as e:
                    self.fail(
                        f"draw_surface_layer() nem loi khi khong co sprite "
                        f"(zoom={zoom}, cam=({cx},{cy})): {e}"
                    )

    def test_food_type_colors_are_distinct(self):
        """2 loai thuc an PHAI co mau khac nhau ro ret - neu khong, viec
        them loai thuc an thu 2 se vo nghia ve mat hinh anh (nguoi choi
        khong the phan biet duoc cum nao gia tri cao hon chi bang mat)."""
        c1 = cfg.FOOD_TYPE_COLOR[cfg.FOOD_TYPE_SEED]
        c2 = cfg.FOOD_TYPE_COLOR[cfg.FOOD_TYPE_NECTAR]
        dist = sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5
        self.assertGreater(
            dist, 60,
            f"Mau 2 loai thuc an qua giong nhau ({c1} vs {c2}) - kho phan biet bang mat.",
        )

    def test_food_type_weights_sum_to_one(self):
        total = sum(cfg.FOOD_TYPE_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
