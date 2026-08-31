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


class TestFoodSpoilage(unittest.TestCase):
    """SurfaceWorld.decay_food() - thuc an de lau khong ai nhat se HONG
    dan roi bien mat, khac han hanh vi cu (ton tai vinh vien cho toi khi
    bi an het). Xem FOOD_SPOIL_* trong config.py."""

    def setUp(self):
        self.sw = SurfaceWorld()
        self.sw.food[:] = 0
        self.sw.food_age[:] = 0

    def test_fresh_food_does_not_decay_before_threshold(self):
        self.sw.food[10, 10] = 8.0
        for _ in range(cfg.FOOD_SPOIL_TICKS):
            self.sw.decay_food()
        self.assertEqual(self.sw.food[10, 10], 8.0, "Khong duoc giam gia tri truoc nguong FOOD_SPOIL_TICKS")

    def test_food_age_resets_when_cell_becomes_empty(self):
        self.sw.food[10, 10] = 8.0
        for _ in range(500):
            self.sw.decay_food()
        self.sw.food[10, 10] = 0.0  # gia lap kien an het
        self.sw.decay_food()
        self.assertEqual(self.sw.food_age[10, 10], 0.0)

    def test_food_fully_expires_after_spoiling(self):
        """Regression test cho 1 loi cu the da gap: dung sai nguong so
        sanh (>0.5 thay vi >0) de xac dinh 'o con thuc an' khien qua
        trinh hong TU DUNG LAI som (ngay luc gia tri giam duoi 0.5), de
        lai 1 luong 'tan du' ton tai VINH VIEN, khong bao gio dat toi
        FOOD_MIN_VALUE de bi xoa han."""
        self.sw.food[10, 10] = 8.0
        for _ in range(cfg.FOOD_SPOIL_TICKS + 2000):
            self.sw.decay_food()
            if self.sw.food[10, 10] <= 0:
                break
        self.assertEqual(self.sw.food[10, 10], 0.0, "Thuc an hong phai bien mat HAN, khong con tan du")
        self.assertEqual(self.sw.food_age[10, 10], 0.0)

    def test_refreshing_food_prevents_early_spoilage(self):
        self.sw.food[5, 5] = 8.0
        for t in range(cfg.FOOD_SPOIL_TICKS + 100):
            self.sw.decay_food()
            if t == cfg.FOOD_SPOIL_TICKS // 2:
                self.sw.food[5, 5] += 1.0
                self.sw.food_age[5, 5] = 0.0
        self.assertGreater(
            self.sw.food[5, 5], 8.0,
            "Lam moi (bo sung them) thuc an phai reset dong ho hong, chua duoc phep hong som",
        )

    def test_respawned_cluster_starts_fresh(self):
        self.sw.terrain[:] = cfg.TERRAIN_EMPTY
        cx, cy = self.sw.respawn_random_cluster()
        self.assertEqual(self.sw.food_age[cx, cy], 0.0)

    def test_manual_placement_starts_fresh(self):
        """place_food_at() trong game_state.py cung phai reset food_age -
        kiem tra gian tiep qua GameState de bao phu ca duong nay."""
        import pygame
        from antworld.game_state import GameState
        pygame.init()
        gs = GameState()
        gs.surface_world.terrain[12, 12] = cfg.TERRAIN_EMPTY  # dam bao khong bi chan boi da/nuoc ngau nhien
        gs.surface_world.food_age[12, 12] = 999.0
        gs.place_food_at(12, 12, amount=5.0)
        self.assertEqual(gs.surface_world.food_age[12, 12], 0.0)


class TestNestRoomGrowth(unittest.TestCase):
    """UndergroundWorld.update_room_sizes() - phong gan lien quy mo dan
    (Kho/Au trung/Nuoc/Trung) phai LON DAN theo dan so, cac phong con lai
    (Chua/Gac cua/Nghia dia/Nhong) phai GIU NGUYEN kich thuoc goc."""

    def setUp(self):
        self.ug = UndergroundWorld(nest_pos=cfg.NEST_POS)

    def _radius(self, room_id):
        for r in self.ug.rooms:
            if r[0] == room_id:
                return r[3]
        return None

    def test_growable_rooms_increase_with_population(self):
        for room_id in cfg.ROOM_GROWABLE_IDS:
            self.ug.update_room_sizes(population=10)
            r10 = self._radius(room_id)
            self.ug.update_room_sizes(population=200)
            r200 = self._radius(room_id)
            self.assertGreater(
                r200, r10,
                f"Phong id={room_id} khong lon them khi dan so tang tu 10 len 200",
            )

    def test_non_growable_rooms_stay_fixed(self):
        fixed_ids = [r[0] for r in self.ug.rooms if r[0] not in cfg.ROOM_GROWABLE_IDS]
        before = {rid: self._radius(rid) for rid in fixed_ids}
        self.ug.update_room_sizes(population=200)
        for rid in fixed_ids:
            self.assertEqual(
                self._radius(rid), before[rid],
                f"Phong id={rid} KHONG duoc phep doi kich thuoc theo dan so",
            )

    def test_update_is_idempotent_for_same_population(self):
        self.ug.update_room_sizes(population=77)
        r1 = self._radius(cfg.ROOM_GROWABLE_IDS[0])
        self.ug.update_room_sizes(population=77)
        r2 = self._radius(cfg.ROOM_GROWABLE_IDS[0])
        self.assertEqual(r1, r2, "Goi lai voi CUNG 1 dan so khong duoc cong don sai")

    def test_room_can_shrink_back_if_population_drops(self):
        """Khong bi ket o kich thuoc lon nhat tung dat - phai PHAN ANH
        DAN SO HIEN TAI, khong phai dinh cao lich su (dan so co the giam
        do chet choc/xam luoc)."""
        room_id = cfg.ROOM_GROWABLE_IDS[0]
        self.ug.update_room_sizes(population=200)
        r_big = self._radius(room_id)
        self.ug.update_room_sizes(population=5)
        r_small = self._radius(room_id)
        self.assertLess(r_small, r_big)


if __name__ == "__main__":
    unittest.main()
