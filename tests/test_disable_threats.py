# -*- coding: utf-8 -*-
"""Test cho nút bật/tắt HOÀN TOÀN kẻ thù tự nhiên và đàn kiến ngoại lai
xâm nhập - xem GameState.toggle_enemy_spawn()/toggle_invasion_spawn() và
EnemyManager.auto_spawn_enabled / InvasionManager.auto_spawn_enabled.
"""
import os
import unittest

import pygame

from antworld import config as cfg
from antworld import game_state, hud


def _advance_past_founding(gs, max_ticks=20000):
    ticks = 0
    while gs.queen_walk_active and ticks < max_ticks:
        gs.step_simulation()
        ticks += 1
    return ticks


class TestDisableThreats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_invasion_auto_spawn_enabled_by_default(self):
        gs = game_state.GameState()
        self.assertTrue(gs.invasion.auto_spawn_enabled)

    def test_toggle_invasion_spawn_flips_state_and_button(self):
        gs = game_state.GameState()
        hud.build_toolbar(gs)
        btn = next(b for b in gs.buttons if "Dan xam nhap" in b.text)
        self.assertIn("BAT", btn.text)
        btn.on_click()
        self.assertFalse(gs.invasion.auto_spawn_enabled)
        self.assertIn("TAT", btn.text)
        self.assertFalse(btn.active)
        btn.on_click()
        self.assertTrue(gs.invasion.auto_spawn_enabled)
        self.assertIn("BAT", btn.text)

    def test_disabled_invasion_never_spawns_a_wave(self):
        gs = game_state.GameState()
        gs.invasion.auto_spawn_enabled = False
        _advance_past_founding(gs)
        for _ in range(cfg.INVASION_FIRST_WAVE_TICK + 500):
            gs.step_simulation()
        self.assertFalse(gs.invasion.active)
        self.assertEqual(gs.invasion.wave_number, 0)

    def test_enabled_invasion_can_spawn_a_wave(self):
        gs = game_state.GameState()
        self.assertTrue(gs.invasion.auto_spawn_enabled)
        _advance_past_founding(gs)
        # Ép dân số đủ lớn + tick gần mốc đợt đầu để xác nhận CÓ THỂ sinh
        # ra đợt xâm nhập khi bật (không cần chờ tick đúng như thật)
        gs.invasion.tick_count = cfg.INVASION_FIRST_WAVE_TICK
        gs.invasion.update(gs.colony)
        self.assertTrue(gs.invasion.active)

    def test_enemy_and_invasion_toggles_are_independent(self):
        gs = game_state.GameState()
        hud.build_toolbar(gs)
        enemy_btn = next(b for b in gs.buttons if "Ke thu tu nhien" in b.text)
        inv_btn = next(b for b in gs.buttons if "Dan xam nhap" in b.text)
        inv_btn.on_click()
        self.assertFalse(gs.invasion.auto_spawn_enabled)
        self.assertTrue(gs.enemy.auto_spawn_enabled)  # không bị ảnh hưởng

    def test_both_threats_disabled_no_deaths_from_them_over_long_run(self):
        gs = game_state.GameState()
        gs.enemy.auto_spawn_enabled = False
        gs.invasion.auto_spawn_enabled = False
        _advance_past_founding(gs)
        for _ in range(6000):
            gs.step_simulation()
        self.assertFalse(gs.enemy.active)
        self.assertFalse(gs.invasion.active)
        self.assertEqual(gs.enemy.total_kills, 0)
        self.assertEqual(gs.invasion.total_guards_killed_by_invasion, 0)

    def test_settings_survive_save_load_round_trip(self):
        gs = game_state.GameState()
        gs.enemy.auto_spawn_enabled = False
        gs.invasion.auto_spawn_enabled = False
        try:
            self.assertTrue(gs.save_game())
            gs2 = game_state.GameState()
            gs2.load_game()
            self.assertFalse(gs2.enemy.auto_spawn_enabled)
            self.assertFalse(gs2.invasion.auto_spawn_enabled)
        finally:
            if os.path.exists(game_state.SAVE_PATH):
                os.remove(game_state.SAVE_PATH)

    def test_loading_old_invasion_save_without_flag_defaults_to_enabled(self):
        """File lưu từ bản CŨ hơn (trước khi InvasionManager có
        auto_spawn_enabled) không có thuộc tính này - phải mặc định BẬT,
        không được crash lúc tải."""
        import pickle
        from antworld.invasion import InvasionManager

        gs = game_state.GameState()
        old_invasion = InvasionManager()
        del old_invasion.auto_spawn_enabled  # gia lap file luu CU

        data = {
            "version": 2,
            "colony": gs.colony,
            "surface_world": gs.surface_world,
            "enemy": gs.enemy,
            "invasion": old_invasion,
            "camera_cx": gs.camera.cx,
            "camera_cy": gs.camera.cy,
            "camera_zoom": gs.camera.zoom,
            "current_layer": gs.current_layer,
            "sim_paused": gs.sim_paused,
            "sim_speed": gs.sim_speed,
            "food_respawn_enabled": gs.food_respawn_enabled,
            "food_respawn_tick": gs.food_respawn_tick,
            "history_tick": gs.history_tick,
            "pop_history_main": list(gs.pop_history_main),
        }
        try:
            with open(game_state.SAVE_PATH, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            gs2 = game_state.GameState()
            ok = gs2.load_game()
            self.assertTrue(ok)
            self.assertTrue(gs2.invasion.auto_spawn_enabled)
        finally:
            if os.path.exists(game_state.SAVE_PATH):
                os.remove(game_state.SAVE_PATH)


if __name__ == "__main__":
    unittest.main()
