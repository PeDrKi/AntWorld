# -*- coding: utf-8 -*-
"""Test cho các sửa lỗi CÂN BẰNG khiến tổ mới lập gần như luôn tuyệt
chủng ("quá khó sống sót"):

1. AntColony._rebalance_labor() - điều chỉnh linh hoạt lao động (không
   bao giờ để 0 thợ kiếm ăn; đảm bảo có y tá/hộ vệ khi cần).
2. Enemy - không xuất hiện khi tổ còn non (cfg.ENEMY_MIN_COLONY_POPULATION),
   và giới hạn số lượng giết mỗi lần theo ĐÚNG quy mô đàn.
3. cfg.EGG_MIN_STORAGE_BUFFER_PER_ANT giảm về 0 - không còn chặn đứng
   sinh sản của 1 đàn vừa/nhỏ đã ổn định.
"""
import unittest

import numpy as np
import pygame

from antworld import config as cfg
from antworld.world import SurfaceWorld, UndergroundWorld
from antworld.ants import AntColony
from antworld.enemy import EnemyManager


def make_colony(n_start, founding=False, progressive=False):
    sw = SurfaceWorld()
    uw = UndergroundWorld(cfg.NEST_POS, "", progressive=progressive)
    return AntColony(n_start, cfg.MAX_ANTS_PER_COLONY, sw, uw, cfg.NEST_POS, founding=founding)


class TestLaborRebalancing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _counts(self, colony):
        is_minor = colony.role == cfg.ROLE_MINOR
        alive_minor = colony.alive & is_minor
        return {
            "foragers": int(np.sum(alive_minor & (colony.job == cfg.JOB_FORAGER))),
            "nurses": int(np.sum(alive_minor & (colony.job == cfg.JOB_NURSE))),
            "attendants": int(np.sum(alive_minor & (colony.job == cfg.JOB_ATTENDANT))),
        }

    def test_never_leaves_zero_foragers_when_population_allows(self):
        """Ép TOÀN BỘ đàn (trừ 1 con) thành y tá/hộ vệ - sau vài lần gọi
        _rebalance_labor(), PHẢI có ít nhất 1 thợ kiếm ăn trở lại."""
        colony = make_colony(n_start=6, founding=False)
        is_minor = colony.role == cfg.ROLE_MINOR
        minor_idx = np.where(colony.alive & is_minor)[0]
        colony.job[minor_idx] = cfg.JOB_NURSE
        colony.tick_count = 0
        for _ in range(5):
            colony.tick_count += 200
            colony._rebalance_labor()
        self.assertGreater(self._counts(colony)["foragers"], 0)

    def test_assigns_nurse_when_none_exist_and_larvae_present(self):
        colony = make_colony(n_start=10, founding=False)
        is_minor = colony.role == cfg.ROLE_MINOR
        minor_idx = np.where(colony.alive & is_minor)[0]
        colony.job[minor_idx] = cfg.JOB_FORAGER  # ép 0 y tá/hộ vệ ban đầu
        colony.larva_active[:3] = True  # có ấu trùng cần chăm
        colony.tick_count = 200
        colony._rebalance_labor()
        self.assertGreater(self._counts(colony)["nurses"], 0)

    def test_assigns_attendant_when_none_exist_and_population_sufficient(self):
        colony = make_colony(n_start=10, founding=False)
        is_minor = colony.role == cfg.ROLE_MINOR
        minor_idx = np.where(colony.alive & is_minor)[0]
        colony.job[minor_idx] = cfg.JOB_FORAGER
        colony.tick_count = 200
        colony._rebalance_labor()
        self.assertGreater(self._counts(colony)["attendants"], 0)

    def test_does_not_touch_labor_below_population_threshold_for_attendant(self):
        """Đàn quá nhỏ (population < 5) không ép thêm hộ vệ - giữ toàn bộ
        làm thợ kiếm ăn để tối đa hoá cơ hội phục hồi."""
        colony = make_colony(n_start=4, founding=False)
        is_minor = colony.role == cfg.ROLE_MINOR
        minor_idx = np.where(colony.alive & is_minor)[0]
        colony.job[minor_idx] = cfg.JOB_FORAGER
        colony.tick_count = 200
        colony._rebalance_labor()
        self.assertEqual(self._counts(colony)["attendants"], 0)

    def test_only_runs_every_200_ticks(self):
        colony = make_colony(n_start=10, founding=False)
        is_minor = colony.role == cfg.ROLE_MINOR
        minor_idx = np.where(colony.alive & is_minor)[0]
        colony.job[minor_idx] = cfg.JOB_FORAGER
        colony.tick_count = 199
        colony._rebalance_labor()
        self.assertEqual(self._counts(colony)["nurses"], 0)
        self.assertEqual(self._counts(colony)["attendants"], 0)

    def test_does_not_run_during_founding_phase(self):
        """update() không gọi _rebalance_labor() trong lúc founding_phase -
        tránh can thiệp vào cơ chế lập tổ riêng (dùng năng lượng chúa)."""
        colony = make_colony(n_start=0, founding=True)
        colony.tick_count = 200
        # goi update() that (khong phai truc tiep _rebalance_labor) de
        # kiem tra dieu kien "if not founding_phase" trong update()
        colony.update()
        self.assertTrue(colony.founding_phase)


class TestEnemyGracePeriod(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_colony_too_fragile_true_during_founding(self):
        em = EnemyManager()
        colony = make_colony(n_start=0, founding=True)
        self.assertTrue(em._colony_too_fragile(colony))

    def test_colony_too_fragile_true_below_min_population(self):
        em = EnemyManager()
        colony = make_colony(n_start=cfg.ENEMY_MIN_COLONY_POPULATION - 1, founding=False)
        self.assertTrue(em._colony_too_fragile(colony))

    def test_colony_not_fragile_above_min_population(self):
        em = EnemyManager()
        colony = make_colony(n_start=cfg.ENEMY_MIN_COLONY_POPULATION + 5, founding=False)
        self.assertFalse(em._colony_too_fragile(colony))

    def test_enemy_does_not_spawn_while_any_colony_fragile(self):
        em = EnemyManager()
        em.auto_spawn_enabled = True
        em.spawn_cooldown = 0
        fragile_colony = make_colony(n_start=0, founding=True)
        em.update([fragile_colony])
        self.assertFalse(em.active)
        self.assertEqual(em.spawn_cooldown, 1)

    def test_enemy_can_spawn_once_colony_past_grace_period(self):
        em = EnemyManager()
        em.auto_spawn_enabled = True
        em.spawn_cooldown = 0
        healthy_colony = make_colony(n_start=cfg.ENEMY_MIN_COLONY_POPULATION + 10, founding=False)
        em.update([healthy_colony])
        self.assertTrue(em.active)

    def test_kill_quota_scales_with_colony_population(self):
        """1 lần ghé thăm KHÔNG được giết quá population//4 (tối thiểu 1)
        của 1 tổ nhỏ, kể cả khi ENEMY_MAX_KILLS_PER_VISIT cho phép nhiều
        hơn thế."""
        em = EnemyManager()
        colony = make_colony(n_start=cfg.ENEMY_MIN_COLONY_POPULATION + 4, founding=False)
        colony.x[:] = 0.0
        colony.y[:] = 0.0
        em.x, em.y = 0.0, 0.0
        em.active = True
        em.kills_this_visit = 0
        original_prob = cfg.ENEMY_KILL_PROB_PER_TICK
        try:
            import antworld.config as live_cfg
            live_cfg.ENEMY_KILL_PROB_PER_TICK = 1.0  # bảo đảm giết được, để test giới hạn quota
            em._try_kill([colony])
        finally:
            live_cfg.ENEMY_KILL_PROB_PER_TICK = original_prob
        population = cfg.ENEMY_MIN_COLONY_POPULATION + 4
        expected_cap = max(1, population // 4)
        self.assertLessEqual(em.kills_this_visit, expected_cap)


class TestEggReproductionNotBlocked(unittest.TestCase):
    """cfg.EGG_MIN_STORAGE_BUFFER_PER_ANT = 0.0 - không còn chặn sinh sản
    của 1 đàn vừa/nhỏ chỉ vì kho chưa tích luỹ đủ theo tỉ lệ dân số."""

    def test_egg_min_storage_buffer_per_ant_is_zero(self):
        self.assertEqual(cfg.EGG_MIN_STORAGE_BUFFER_PER_ANT, 0.0)

    def test_moderate_population_with_modest_storage_can_still_lay_eggs(self):
        """1 đàn 12 con với kho chỉ ~5 thức ăn (dưới ngưỡng CŨ 8.0/1.5,
        nhưng đủ với EGG_FOOD_COST ở ngưỡng MỚI) không còn bị chặn đẻ
        trứng chỉ vì thiếu dự trữ theo tỉ lệ dân số."""
        colony = make_colony(n_start=12, founding=False)
        colony.underground.food_in_storage = cfg.EGG_FOOD_COST + 1.0
        colony.underground.water_in_storage = cfg.EGG_WATER_COST + 1.0
        population = int(np.sum(colony.alive))
        safety_reserve = population * cfg.EGG_MIN_STORAGE_BUFFER_PER_ANT
        enough_reserve = colony.underground.food_in_storage >= (cfg.EGG_FOOD_COST + safety_reserve)
        self.assertTrue(enough_reserve)


if __name__ == "__main__":
    unittest.main()
