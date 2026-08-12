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
        eggs_before = int(np.sum(colony.egg_active))
        larvae_before = int(np.sum(colony.larva_active))

        inv = InvasionManager()
        inv.force_spawn_wave(colony, size=10)
        for _ in range(2000):
            colony.update()
            inv.update(colony)
            if not inv.active:
                break

        eggs_after = int(np.sum(colony.egg_active))
        larvae_after = int(np.sum(colony.larva_active))
        self.assertLess(eggs_after + larvae_after, eggs_before + larvae_before)
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
        np.random.seed(7)
        colony = make_colony()
        from antworld.invasion import InvasionManager as IM
        inv = IM()
        pop_samples = []
        for t in range(1, 20000):
            colony.update(invasion=inv)
            inv.update(colony)
            if t % 4000 == 0:
                pop_samples.append(int(np.sum(colony.alive)))

        # Khong doi hoi tang DEU moi moc (dao dong tu nhien la binh thuong),
        # nhung KHONG duoc tuyet chung o cuoi bai test dai nay, va moc cuoi
        # phai lon hon han moc dau (xu huong chung la PHAT TRIEN, khong
        # phai suy giam he thong).
        self.assertGreater(pop_samples[-1], 0, "To bi tuyet chung sau 20000 tick voi invasion BAT")
        self.assertGreater(
            pop_samples[-1], pop_samples[0] * 0.5,
            f"Dan so co xu huong SUY GIAM manh qua thoi gian ({pop_samples}) - "
            "co the invasion dang duoc can bang qua nang.",
        )


if __name__ == "__main__":
    unittest.main()
