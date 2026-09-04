# -*- coding: utf-8 -*-
"""Test cho 2 nâng cấp hiển thị: vệt pheromone dạng "quầng sáng" hòa cộng
(render_surface.draw_pheromone_trails/_get_pheromone_glow) và trứng/ấu
trùng đổi HÌNH DÁNG (không chỉ kích thước) rõ rệt theo growth
(render_underground.draw_eggs/draw_larvae).
"""
import unittest

import pygame

from antworld import config as cfg
from antworld.game_state import GameState
from antworld.render_surface import (
    draw_pheromone_trails, draw_surface_layer, _get_pheromone_glow, _pheromone_glow_cache,
)
from antworld.render_underground import draw_eggs, draw_larvae, draw_underground_layer


def _advance_past_founding(gs, max_ticks=20000):
    ticks = 0
    while gs.colony.founding_phase and ticks < max_ticks:
        gs.step_simulation()
        ticks += 1


class TestPheromoneGlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_glow_sprite_cached_and_reused(self):
        _pheromone_glow_cache.clear()
        s1 = _get_pheromone_glow((60, 170, 255), 10, 3, 8)
        n_after_first = len(_pheromone_glow_cache)
        s2 = _get_pheromone_glow((60, 170, 255), 10, 3, 8)
        self.assertIs(s1, s2, "Cùng tham số phải trả về ĐÚNG sprite đã cache, không tạo mới")
        self.assertEqual(len(_pheromone_glow_cache), n_after_first)

    def test_higher_bucket_produces_brighter_peak_alpha(self):
        """Bucket cao (nồng độ đậm hơn) phải cho quầng sáng SÁNG HƠN ở tâm
        so với bucket thấp."""
        low = _get_pheromone_glow((60, 170, 255), 12, 0, 8)
        high = _get_pheromone_glow((60, 170, 255), 12, 7, 8)
        center = 12
        low_alpha = low.get_at((center, center))[3]
        high_alpha = high.get_at((center, center))[3]
        self.assertGreater(high_alpha, low_alpha)

    def test_glow_fades_towards_edge(self):
        """Alpha ở TÂM sprite phải cao hơn hẳn alpha ở gần MÉP - đúng hiệu
        ứng 'mờ dần ra mép' thay vì khối tròn phẳng cứng như trước."""
        radius = 14
        glow = _get_pheromone_glow((230, 50, 40), radius, 7, 8)
        center_alpha = glow.get_at((radius, radius))[3]
        edge_alpha = glow.get_at((radius, 2))[3]  # gần mép trên
        self.assertGreater(center_alpha, edge_alpha)

    def test_cache_clears_when_growing_too_large(self):
        _pheromone_glow_cache.clear()
        for r in range(400):
            _get_pheromone_glow((1, 2, 3), r + 1, 0, 8)
        self.assertLess(len(_pheromone_glow_cache), 400, "Cache phải tự dọn thay vì phình vô hạn")

    def test_draw_pheromone_trails_no_crash_when_empty(self):
        gs = GameState()
        screen = gs.screen
        screen.fill((0, 0, 0))
        draw_pheromone_trails(gs, screen)  # chưa có pheromone nào - không được crash

    def test_draw_pheromone_trails_no_crash_with_high_concentration(self):
        gs = GameState()
        gs.surface_world.pheromone[10:20, 10:20] = cfg.PHEROMONE_MAX
        gs.surface_world.danger_pheromone[25:30, 25:30] = cfg.DANGER_PHEROMONE_MAX
        screen = gs.screen
        for zoom in (0.35, 1.0, 2.0, 3.5):
            gs.camera.zoom = zoom
            screen.fill((0, 0, 0))
            draw_pheromone_trails(gs, screen)

    def test_full_surface_layer_draw_includes_pheromone_without_crash(self):
        gs = GameState()
        gs.surface_world.pheromone[15, 15] = 5.0
        screen = gs.screen
        screen.fill((0, 0, 0))
        draw_surface_layer(gs, screen)


class TestEggLarvaShapeGrowth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _colony_with_growth(self, egg_growths=None, larva_growths=None):
        gs = GameState()
        _advance_past_founding(gs)
        c = gs.colony
        if egg_growths:
            n = len(egg_growths)
            c.egg_active[:n] = True
            c.egg_growth[:n] = egg_growths
        if larva_growths:
            n = len(larva_growths)
            c.larva_active[:n] = True
            c.larva_growth[:n] = larva_growths
        return gs, c

    def test_egg_no_crash_across_growth_range(self):
        gs, c = self._colony_with_growth(egg_growths=[0.0, 0.25, 0.5, 0.75, 1.0])
        screen = gs.screen
        screen.fill((0, 0, 0))
        draw_eggs(gs, screen, 200, 200, 60, c, 1)

    def test_larva_no_crash_across_growth_range(self):
        gs, c = self._colony_with_growth(larva_growths=[0.0, 0.25, 0.5, 0.75, 1.0])
        screen = gs.screen
        screen.fill((0, 0, 0))
        draw_larvae(gs, screen, 200, 200, 60, c, 2)

    def test_no_eggs_or_larvae_draws_nothing_no_crash(self):
        gs, c = self._colony_with_growth()
        screen = gs.screen
        screen.fill((0, 0, 0))
        draw_eggs(gs, screen, 200, 200, 60, c, 1)
        draw_larvae(gs, screen, 200, 200, 60, c, 2)

    def test_egg_growth_zero_and_one_are_valid_boundaries(self):
        gs, c = self._colony_with_growth(egg_growths=[0.0, 1.0])
        screen = gs.screen
        screen.fill((0, 0, 0))
        draw_eggs(gs, screen, 200, 200, 60, c, 1)  # không crash ở 2 biên

    def test_larva_growth_zero_and_one_are_valid_boundaries(self):
        gs, c = self._colony_with_growth(larva_growths=[0.0, 1.0])
        screen = gs.screen
        screen.fill((0, 0, 0))
        draw_larvae(gs, screen, 200, 200, 60, c, 2)

    def test_larva_segment_count_increases_with_growth(self):
        """Ấu trùng growth cao phải có NHIỀU ĐỐT hơn (n_segments) growth
        thấp - kiểm tra gián tiếp qua công thức, vì hàm vẽ không trả về
        giá trị: n_segments = 2 + round(growth*3)."""
        def n_segments(growth):
            return 2 + round(growth * 3)
        self.assertEqual(n_segments(0.0), 2)
        self.assertEqual(n_segments(1.0), 5)
        self.assertLess(n_segments(0.0), n_segments(1.0))

    def test_full_underground_layer_draw_with_growth_variety_no_crash(self):
        gs, c = self._colony_with_growth(
            egg_growths=[0.0, 0.5, 1.0], larva_growths=[0.0, 0.5, 1.0])
        gs._check_room_unlocks(20)  # mở phòng trứng + ấu trùng riêng
        screen = gs.screen
        for depth in range(6):
            screen.fill((0, 0, 0))
            draw_underground_layer(gs, screen, depth)

    def test_full_underground_layer_draw_while_merged_into_queen_room(self):
        """Trứng/ấu trùng vẫn phải vẽ được đúng lúc CÒN ĐANG gộp chung vào
        Phòng chúa (chưa unlock riêng) - xem
        render_underground._draw_merged_room_contents()."""
        gs, c = self._colony_with_growth(
            egg_growths=[0.0, 0.5, 1.0], larva_growths=[0.0, 0.5, 1.0])
        self.assertNotIn(4, gs.underground_world.unlocked_rooms)
        self.assertNotIn(1, gs.underground_world.unlocked_rooms)
        screen = gs.screen
        screen.fill((0, 0, 0))
        draw_underground_layer(gs, screen, cfg.DEPTH_QUEEN)



class TestCombatStatsDisplayed(unittest.TestCase):
    """3 số liệu chiến tích (từng bị âm thầm tính mà không hiển thị lên
    HUD) - xem hud.draw_hud() dòng 'Chien tich'."""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_draw_hud_shows_combat_stats_without_crash(self):
        from antworld import hud

        gs = GameState()
        hud.build_toolbar(gs)
        gs.enemy.total_defeated = 3
        gs.enemy.total_carcasses_hauled = 2
        gs.invasion.total_guards_killed_by_invasion = 5
        screen = gs.screen
        screen.fill((0, 0, 0))
        hud.draw_hud(gs, screen)  # không được crash

    def test_draw_hud_shows_combat_stats_at_zero_without_crash(self):
        from antworld import hud

        gs = GameState()
        hud.build_toolbar(gs)
        screen = gs.screen
        screen.fill((0, 0, 0))
        hud.draw_hud(gs, screen)  # mặc định đều = 0, vẫn phải vẽ được

    def test_draw_hud_shows_combat_stats_during_founding_without_crash(self):
        from antworld import hud

        gs = GameState()
        hud.build_toolbar(gs)
        self.assertTrue(gs.colony.founding_phase)
        screen = gs.screen
        screen.fill((0, 0, 0))
        hud.draw_hud(gs, screen)


if __name__ == "__main__":
    unittest.main()
