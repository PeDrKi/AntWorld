# -*- coding: utf-8 -*-
"""Test cho world.py (SurfaceWorld + UndergroundWorld).

Muc tieu: bat cac loi "vo hinh" hay gap khi lam viec voi mang NumPy - vi
du 1 phep tinh sai lam ra NaN/inf, hoac 1 gia tri am khong hop le (thuc an
am, do sau am...) ma neu chi nhin game chay bang mat thi rat kho phat
hien ngay, chi thay hau qua (kien dung yen, tang khong sinh sang...) sau
ca tram tick.
"""
import unittest

import numpy as np

from antworld import config as cfg
from antworld.world import SurfaceWorld, UndergroundWorld


class TestSurfaceWorld(unittest.TestCase):
    def setUp(self):
        self.world = SurfaceWorld()

    def test_grid_shapes_match_config(self):
        n = cfg.GRID_SIZE
        self.assertEqual(self.world.food.shape, (n, n))
        self.assertEqual(self.world.pheromone.shape, (n, n))
        self.assertEqual(self.world.terrain.shape, (n, n))

    def test_no_nan_or_inf_after_init(self):
        for name in ("food", "pheromone", "danger_pheromone"):
            arr = getattr(self.world, name)
            self.assertFalse(np.isnan(arr).any(), f"{name} co gia tri NaN")
            self.assertFalse(np.isinf(arr).any(), f"{name} co gia tri inf")

    def test_food_not_negative(self):
        self.assertGreaterEqual(self.world.food.min(), 0.0)

    def test_decay_pheromone_keeps_values_in_range(self):
        self.world.pheromone[:] = 1.0
        for _ in range(50):
            self.world.decay_pheromone()
        # sau nhieu buoc decay, gia tri phai giam dan va khong am / khong NaN
        self.assertGreaterEqual(self.world.pheromone.min(), 0.0)
        self.assertFalse(np.isnan(self.world.pheromone).any())
        self.assertLess(self.world.pheromone.max(), 1.0)

    def test_rock_generated_as_individual_wall_cells(self):
        """Da phai duoc sinh TUNG O MOT (moi o la 1 feature rieng, ban
        kinh 0.5), khong con la khoi tron dac 1 feature duy nhat nhu
        truoc - xem _spawn_one_rock_wall()/add_rock_cell() trong world.py."""
        rock_features = [f for f in self.world.terrain_features if f[1] == cfg.TERRAIN_ROCK]
        self.assertGreater(len(rock_features), 0, "Phai co it nhat vai o da sau khi khoi tao")
        for fid, ftype, cx, cy, radius in rock_features:
            self.assertEqual(radius, 0.5, "Moi o da rieng le phai co ban kinh dung 1 o (0.5)")

    def test_rock_wall_cells_are_connected_chain(self):
        """Trong CUNG 1 buc tuong, cac o da phai lien tiep nhau (khoang
        cach 1 o) - dam bao thuat toan sinh tuong di TUNG BUOC 1 o, khong
        nhay coc ngau nhien ra nhieu noi roi rac. Vi terrain_features gop
        chung nhieu buc tuong lien tiep nhau trong list, chi CHO PHEP nhay
        xa dung it hon so buc tuong (NUM_ROCK_CLUSTERS) lan - moi lan la
        1 diem CHUYEN sang buc tuong moi, con lai deu phai la o ke ben."""
        w = SurfaceWorld()
        rock_features = [f for f in w.terrain_features if f[1] == cfg.TERRAIN_ROCK]
        if len(rock_features) < 2:
            self.skipTest("Qua it o da sinh ra de kiem tra tinh lien mach.")
        far_jumps = 0
        for i in range(1, len(rock_features)):
            _, _, x0, y0, _ = rock_features[i - 1]
            _, _, x1, y1, _ = rock_features[i]
            dist = abs(x1 - x0) + abs(y1 - y0)
            if dist > 1:
                far_jumps += 1
        self.assertLess(
            far_jumps, cfg.NUM_ROCK_CLUSTERS,
            f"Co {far_jumps} lan 'nhay xa' giua 2 o da lien tiep trong danh "
            f"sach - nhieu hon so buc tuong ({cfg.NUM_ROCK_CLUSTERS}), nghia "
            f"la co buc tuong bi dut doan giua chung thay vi noi lien mach."
        )


class TestUndergroundWorld(unittest.TestCase):
    def setUp(self):
        self.ug = UndergroundWorld(nest_pos=cfg.NEST_POS)

    def test_starvation_tracker_runs_without_error(self):
        # goi thu vai lan voi cac muc dan so khac nhau, chi can khong crash
        # va khong sinh NaN la du - day la ham hay bi sua di sua lai khi
        # can bang lai nguy co "sup dan" (xem README).
        for pop in (0, 1, 10, 200):
            self.ug.update_starvation_tracker(population=pop)
        self.assertFalse(np.isnan(self.ug.food_in_storage))
        self.assertFalse(np.isnan(self.ug.water_in_storage))

    def test_consume_upkeep_never_makes_storage_nan(self):
        for pop in (0, 5, 50, 200):
            self.ug.consume_upkeep(pop)
        self.assertFalse(np.isnan(self.ug.food_in_storage))
        self.assertFalse(np.isnan(self.ug.water_in_storage))


if __name__ == "__main__":
    unittest.main()
