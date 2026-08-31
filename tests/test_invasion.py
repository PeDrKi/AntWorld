# -*- coding: utf-8 -*-
"""Test cho invasion.py (InvasionManager) - dan kien NGOAI LAI xam nhap
theo dot (thay cho to doi thu co dinh o ban truoc).

Trong tam:
    - 1 dot xam nhap co the duoc phat dong (force_spawn_wave) va DI QUA DU
      cac trang thai chinh (tiep can -> xuong ham -> cuop pha -> rut lui)
    - cuop duoc thuc an VA trung/au trung that (khong chi thay doi so o
      tren giay)
    - linh gac lam GIAM sat thuong (dau tu vao phong thu phai co y nghia)
    - CAN BANG DAI HAN: mot to bi bo mac (khong ai choi) van PHAT TRIEN
      duoc qua nhieu dot xam nhap, KHONG bi tuyet chung deu dan - day la
      loi thuc te tung phat hien (dot dau qua manh so voi to con non fret,
      da sua trong config.py) nen can 1 test rieng khoa lai, tranh regression.
"""
import unittest

import numpy as np

from antworld import config as cfg
from antworld.ants import AntColony
from antworld.world import SurfaceWorld, UndergroundWorld
from antworld.invasion import (
    InvasionManager, INV_APPROACH, INV_FIGHT_ENTRANCE, INV_DESCEND,
    INV_RAID_STORAGE, INV_RAID_BROOD, INV_RETREAT_UG, INV_RETREAT_SURFACE,
)


def make_colony(n_start=None):
    n_start = n_start if n_start is not None else cfg.NUM_ANTS
    surface = SurfaceWorld()
    underground = UndergroundWorld(nest_pos=cfg.NEST_POS)
    return AntColony(n_start, cfg.MAX_ANTS_PER_COLONY, surface, underground, nest_pos=cfg.NEST_POS)


class TestInvasionBasics(unittest.TestCase):
    def test_starts_inactive(self):
        inv = InvasionManager()
        self.assertFalse(inv.active)
        self.assertEqual(int(np.sum(inv.alive)), 0)

    def test_force_spawn_wave_activates(self):
        colony = make_colony()
        inv = InvasionManager()
        inv.force_spawn_wave(colony, size=6)
        self.assertTrue(inv.active)
        self.assertEqual(int(np.sum(inv.alive)), 6)
        self.assertTrue(np.all(inv.state[inv.alive] == INV_APPROACH))

    def test_wave_progresses_through_states_and_ends(self):
        """Chay du lau va thu thap TAT CA trang thai da trai qua - phai
        thay it nhat 'tien can/xuong ham/cuop pha/rut lui', va cuoi cung
        active phai tu tat (ca doi da chet het hoac rut het ve)."""
        colony = make_colony()
        for _ in range(1500):
            colony.update()
        inv = InvasionManager()
        inv.force_spawn_wave(colony, size=8)

        seen_states = set()
        ended = False
        for t in range(4000):
            colony.update()
            inv.update(colony)
            seen_states.update(np.unique(inv.state[inv.alive]).tolist())
            if not inv.active:
                ended = True
                break

        self.assertTrue(ended, "Dot xam nhap khong tu ket thuc trong 4000 tick")
        # Phai di qua it nhat cac trang thai chinh (khong nhat thiet FIGHT_
        # ENTRANCE - phu thuoc co linh gac hay khong luc do)
        self.assertIn(INV_DESCEND, seen_states)
        self.assertTrue(
            INV_RAID_STORAGE in seen_states or INV_RAID_BROOD in seen_states,
            "Khong co quan nao vao duoc trang thai cuop pha",
        )
        self.assertIn(INV_RETREAT_UG, seen_states)

    def test_steals_food(self):
        colony = make_colony()
        for _ in range(1500):
            colony.update()
        colony.underground.food_in_storage = 500.0  # dam bao chac chan co du de cuop
        food_before = colony.underground.food_in_storage

        inv = InvasionManager()
        inv.force_spawn_wave(colony, size=10)
        for _ in range(2000):
            colony.update()
            inv.update(colony)
            if not inv.active:
                break

        self.assertLess(colony.underground.food_in_storage, food_before)
        self.assertGreater(inv.total_food_stolen, 0)

    def test_steals_brood_eggs_and_larvae(self):
        colony = make_colony()
        for _ in range(1500):
            colony.update()
        # Ep san co trung + au trung de chac chan co gi do de cuop (khong
        # phu thuoc may man cua mo phong tu nhien)
        colony.egg_active[:10] = True
        colony.egg_growth[:10] = 0.5
        colony.larva_active[:10] = True
        colony.larva_growth[:10] = 0.5

        inv = InvasionManager()
        inv.force_spawn_wave(colony, size=10)
        for _ in range(2000):
            colony.update()
            inv.update(colony)
            if not inv.active:
                break

        # LUU Y: KHONG so sanh so trung+au trung TRUOC/SAU raid (tung dung
        # cach nay) - da PHAT HIEN day la 1 khang dinh FLAKY co san (khong
        # lien quan gi toi tinh nang duong di cua quan xam luoc): trong
        # suot ~1000 tick raid dien ra, dan kien VAN sinh san TU NHIEN song
        # song (chua moi de, au trung moi no...), nen tong so trung+au
        # trung co the TANG NET du raid co cuop pha thanh cong that su - da
        # do thuc te: ~15-20% cac lan chay bi fail vi ly do nay, XAY RA CA
        # KHI quan xam luoc di THANG 1 duong (hanh vi truoc khi co
        # pathfinding tranh vat can), tuc khong lien quan gi tinh nang
        # duong di. Dung THANG total_brood_stolen (bo dem RIENG, tang moi
        # lan cuop duoc, khong bi anh huong boi sinh san tu nhien) la phep
        # do DUNG DAN va ON DINH cho "co cuop pha thanh cong khong".
        self.assertGreater(inv.total_brood_stolen, 0)

    def test_guards_reduce_invader_survival(self):
        """Dau tu vao linh gac phai co y nghia: cung 1 quy mo dot xam nhap,
        to CO linh gac phai con nhieu quan xam nhap SONG SOT hon (tuc la
        linh gac da ha duoc nhieu quan xam nhap hon) so voi to KHONG co
        linh gac nao."""
        np.random.seed(42)

        def run(n_guards):
            colony = make_colony()
            colony.alive[:] = False
            n = 20
            colony.alive[:n] = True
            colony.is_guard[:n] = False
            colony.is_guard[:n_guards] = True
            colony.role[:n_guards] = cfg.ROLE_MAJOR
            colony.layer[:n] = cfg.LAYER_SURFACE
            colony.depth[:n] = cfg.LAYER_SURFACE_DEPTH
            nx, ny = colony.nest_pos
            colony.x[:n] = nx
            colony.y[:n] = ny
            colony.state[:n] = cfg.STATE_GUARD_DUTY

            inv = InvasionManager()
            inv.force_spawn_wave(colony, size=10)
            for _ in range(1500):
                colony.update()
                inv.update(colony)
                if not inv.active:
                    break
            return inv.total_invaders_killed

        killed_no_guards = run(0)
        killed_with_guards = run(15)
        self.assertGreaterEqual(
            killed_with_guards, killed_no_guards,
            "Co nhieu linh gac hon nhung KHONG ha duoc nhieu quan xam nhap hon - "
            "co the co loi trong logic giao chien o cua hang.",
        )

    def test_escalation_increases_size_and_shortens_interval(self):
        inv = InvasionManager()
        size0 = inv.next_wave_size
        interval0 = inv.next_wave_interval
        inv._schedule_next_wave()
        self.assertGreaterEqual(inv.next_wave_size, size0)
        self.assertLessEqual(inv.next_wave_interval, interval0)
        # Sau rat nhieu dot, phai bi kep dung trong [MIN, MAX]
        for _ in range(100):
            inv._schedule_next_wave()
        self.assertLessEqual(inv.next_wave_size, cfg.INVASION_MAX_SWARM_SIZE)
        self.assertGreaterEqual(inv.next_wave_interval, cfg.INVASION_INTERVAL_MIN_TICKS)


class TestInvasionLongTermBalance(unittest.TestCase):
    """Loi thuc te tung phat hien: cau hinh mac dinh CU khien 1 to bi bo
    mac tuyet chung DAN DEU qua nhieu dot xam nhap, dai nghich voi cau hinh
    tat invasion (van phat trien khoe manh). Test nay chay ca 2 kich ban
    song song, khoa lai yeu cau: BAT invasion khong duoc lam to giam dan
    xuong 0 mot cach he thong trong dieu kien binh thuong."""

    def test_colony_with_invasion_still_grows_long_term(self):
        if not cfg.INVASION_ENABLED:
            self.skipTest("INVASION_ENABLED dang tat trong config hien tai")

        def run_trial(seed, ticks=14000):
            np.random.seed(seed)
            colony = make_colony()
            from antworld.invasion import InvasionManager as IM
            inv = IM()
            pop_samples = []
            for t in range(1, ticks):
                colony.update(invasion=inv)
                inv.update(colony)
                # Tai sinh thuc an DINH KY giong DUNG vong lap that cua
                # game (xem game_state.py step_simulation) - thieu buoc
                # nay tung khien test flaky sau khi them SurfaceWorld.
                # decay_food(): nguon cung thuc an chi co 1 lan luc khoi
                # tao, khong bao gio duoc bo sung, dan can kiet qua 16000
                # tick du choi that luon co tai sinh bu vao.
                if t % cfg.FOOD_RESPAWN_INTERVAL == 0:
                    colony.surface.respawn_random_cluster()
                if t % 4000 == 0:
                    pop_samples.append(int(np.sum(colony.alive)))
            return pop_samples

        # LUU Y: SurfaceWorld() dung np.random.default_rng() (RIENG BIET,
        # KHONG bi anh huong boi np.random.seed() o tren) de sinh dia
        # hinh/cum thuc an - nghia la MOI LAN chay, BAN DO THUC TE (vi tri
        # da/nuoc/thuc an) deu khac nhau du co "co dinh seed" hay khong.
        # Vi vay 1 lan chay DUY NHAT co the trung dung 1 ban do xui ruii
        # (cum thuc an o qua xa/it) khien dan so giam that qua 1 ban do cu
        # the - KHONG dong nghia co loi he thong. Chay NHIEU lan doc lap
        # (nhieu ban do khac nhau) va xet XU HUONG TRUNG BINH moi dang tin
        # cay, thay vi phan xet qua 1 ban do co the khong dai dien.
        n_trials = 3
        final_ratios = []
        for seed in range(n_trials):
            samples = run_trial(seed)
            ratio = samples[-1] / max(1, samples[0])
            final_ratios.append(ratio)

        avg_ratio = sum(final_ratios) / len(final_ratios)
        self.assertGreater(
            avg_ratio, 1.0,
            f"Trung binh qua {n_trials} ban do KHAC NHAU, dan so co xu huong "
            f"SUY GIAM thay vi phat trien (ty le cuoi/dau tung ban do: "
            f"{[round(r, 2) for r in final_ratios]}) - co the invasion+kinh "
            "te thuc an dang duoc can bang qua nang.",
        )


class TestInvasionRespectsTerrainDefense(unittest.TestCase):
    """Truoc day quan xam luoc tren mat dat di THANG 1 duong ke toi lo to,
    XUYEN QUA ca da/nuoc - nghia la xay tuong da phong thu (du dat duoc ve
    ky thuat) hoan toan KHONG co tac dung can duong xam luoc, chi can duoc
    kien nha di kiem an. Cac test o day khoa lai hanh vi MOI: quan xam
    luoc phai dung CHUNG he thong pathfinding (visibility graph) voi kien
    nha, tuc PHAI ne da/nuoc that su."""

    def test_wall_around_nest_forces_longer_approach(self):
        surface = SurfaceWorld()
        surface.terrain[:] = cfg.TERRAIN_EMPTY
        underground = UndergroundWorld(nest_pos=cfg.NEST_POS)
        colony = AntColony(cfg.NUM_ANTS, cfg.MAX_ANTS_PER_COLONY, surface, underground, nest_pos=cfg.NEST_POS)
        spawn_xy = (2.0, float(cfg.NEST_POS[1]))

        def ticks_to_arrive():
            inv = InvasionManager()
            n = 5
            inv.alive[:n] = True
            inv.x[:n] = spawn_xy[0]
            inv.y[:n] = spawn_xy[1]
            inv.state[:n] = INV_APPROACH
            inv.layer[:n] = cfg.LAYER_SURFACE
            path = colony.pathfinder.find_path(spawn_xy, colony.nest_pos)
            path = path[:cfg.PATH_MAX_WAYPOINTS]
            for k, (wx, wy) in enumerate(path):
                inv.wave_path_x[k] = wx
                inv.wave_path_y[k] = wy
            inv.wave_path_len = len(path)
            for t in range(3000):
                inv._update_approach(colony)
                if inv.state[0] != INV_APPROACH:
                    return t
            self.fail("Quan xam luoc khong bao gio toi noi trong 3000 tick")

        ticks_no_wall = ticks_to_arrive()

        # Xay 1 vong tuong da bao quanh to, chua DUY NHAT 1 khe ho o canh
        # phia bac - buoc bat ky duong di nao toi to deu phai vong qua
        # dung khe ho nay.
        nx, ny = colony.nest_pos
        r = 8
        for gx in range(nx - r, nx + r + 1):
            for gy in range(ny - r, ny + r + 1):
                if (abs(gx - nx) == r or abs(gy - ny) == r) and 0 <= gx < cfg.GRID_SIZE and 0 <= gy < cfg.GRID_SIZE:
                    surface.terrain[gx, gy] = cfg.TERRAIN_ROCK
        for gx in range(nx - 1, nx + 2):
            surface.terrain[gx, ny - r] = cfg.TERRAIN_EMPTY
        surface.terrain_version += 1

        ticks_with_wall = ticks_to_arrive()

        self.assertGreater(
            ticks_with_wall, ticks_no_wall,
            "Tuong da bao quanh to (chi chua 1 khe ho) phai buoc quan xam "
            "luoc mat NHIEU thoi gian hon de tiep can - neu khong, tuong da "
            "khong co tac dung phong thu gi ca.",
        )

    # LUU Y: khong test lai o day rang duong di co "dam xuyen qua da" hay
    # khong - test_pathfinding.py (ham _path_has_collision +
    # TestOnRealSurfaceWorld) da lam dieu nay MOT CACH CHINH XAC roi (xu
    # ly dung ranh gioi/goc o vat can, thu tren ca ban do thuc). Viet lai
    # kiem tra tuong tu o day (da thu) de rat de SAI vi nham lan giua
    # "duong di cham nhe canh/goc 1 o vat can" (BINH THUONG voi
    # pathfinding kieu visibility-graph) voi "duong di xuyen qua long o
    # vat can" (moi la loi that) - test o tren (buoc di vong xa hon) da la
    # bang chung du va DANG TIN CAY hon cho dung 1 dieu can khoa: quan xam
    # luoc CO THUC SU dung colony.pathfinder (khong con di thang xuyen
    # tuong nhu truoc).


if __name__ == "__main__":
    unittest.main()
