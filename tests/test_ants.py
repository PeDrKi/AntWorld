# -*- coding: utf-8 -*-
"""Test cho ants.py (AntColony) - phan mo phong lon nhat va phuc tap
nhat cua du an (dung mang NumPy, khong OOP tung con kien).

Trong tam: CHAY THAT NHIEU TICK lien tuc (mo phong ngan gon lai README
mo ta: da tung chay 60-90 nghin tick de can bang so lieu), roi kiem tra
cac BAT BIEN (invariants) phai luon dung bat ke bao nhieu tick da troi
qua:
    - khong co NaN/inf trong vi tri, goc quay
    - so kien con song khong bao gio vuot tran MAX_ANTS_PER_COLONY
    - so kien con song khong am

Day la loai loi de "lot luoi" nhat khi chi test thu cong bang mat (vd:
choi thu vai chuc giay), vi nhieu loi can bang so lieu chi lo ra sau rat
nhieu tick (hang nghin) khi 1 truong hop hiem gap moi xay ra.
"""
import unittest

import numpy as np

from antworld import config as cfg
from antworld.ants import AntColony
from antworld.world import SurfaceWorld, UndergroundWorld


def make_colony(n_start=None, max_ants=None):
    n_start = n_start if n_start is not None else cfg.NUM_ANTS
    max_ants = max_ants if max_ants is not None else cfg.MAX_ANTS_PER_COLONY
    surface = SurfaceWorld()
    underground = UndergroundWorld(nest_pos=cfg.NEST_POS)
    colony = AntColony(n_start, max_ants, surface, underground, nest_pos=cfg.NEST_POS)
    return colony


class TestAntColonyBasics(unittest.TestCase):
    def test_init_population_matches_num_ants(self):
        colony = make_colony()
        self.assertEqual(int(np.sum(colony.alive)), cfg.NUM_ANTS)

    def test_allocated_slots_match_max_ants(self):
        colony = make_colony()
        self.assertEqual(colony.n, cfg.MAX_ANTS_PER_COLONY)
        self.assertEqual(len(colony.alive), cfg.MAX_ANTS_PER_COLONY)


class TestAntColonySimulationInvariants(unittest.TestCase):
    """Chay mo phong dai (nhung van du nhanh de nam trong 1 lan chay test
    thong thuong) va kiem tra cac bat bien co ban."""

    N_TICKS = 1500  # đủ để đi qua vài chu kỳ trứng->ấu trùng->thợ mới

    @classmethod
    def setUpClass(cls):
        cls.colony = make_colony()
        for _ in range(cls.N_TICKS):
            cls.colony.update()

    def test_no_nan_or_inf_in_positions(self):
        self.assertFalse(np.isnan(self.colony.x).any(), "Vi tri x co NaN")
        self.assertFalse(np.isnan(self.colony.y).any(), "Vi tri y co NaN")
        self.assertFalse(np.isinf(self.colony.x).any(), "Vi tri x co inf")
        self.assertFalse(np.isinf(self.colony.y).any(), "Vi tri y co inf")

    def test_no_nan_in_theta(self):
        self.assertFalse(np.isnan(self.colony.theta).any())

    def test_population_within_bounds(self):
        population = int(np.sum(self.colony.alive))
        self.assertGreaterEqual(population, 0)
        self.assertLessEqual(
            population, cfg.MAX_ANTS_PER_COLONY,
            f"Dan so ({population}) vuot tran MAX_ANTS_PER_COLONY "
            f"({cfg.MAX_ANTS_PER_COLONY}) - AntColony cap phat khong du "
            f"cho so nay, co the gay loi index ngoai mang."
        )

    def test_depth_within_valid_layers(self):
        alive_depth = self.colony.depth[self.colony.alive]
        if len(alive_depth) == 0:
            self.skipTest("Dan da tuyet chung trong qua trinh test - "
                           "khong con kien song de kiem tra tang.")
        self.assertGreaterEqual(alive_depth.min(), 0)
        self.assertLessEqual(alive_depth.max(), cfg.DEPTH_GRAVEYARD)

    def test_storage_never_negative(self):
        self.assertGreaterEqual(self.colony.underground.food_in_storage, 0)
        self.assertGreaterEqual(self.colony.underground.water_in_storage, 0)


if __name__ == "__main__":
    unittest.main()
