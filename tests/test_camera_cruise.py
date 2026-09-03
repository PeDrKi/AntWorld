# -*- coding: utf-8 -*-
"""Test cho camera "TU LAI" kieu screensaver - GameState.touch_activity()/
update_camera_cruise()/toggle_cruise_enabled() va cfg.CRUISE_* (xem
game_state.py va hud.draw_cruise_indicator()).
"""
import unittest

import numpy as np
import pygame

from antworld import config as cfg
from antworld import game_state


def _advance_past_founding(gs, max_ticks=20000):
    ticks = 0
    while gs.colony.founding_phase and ticks < max_ticks:
        gs.step_simulation()
        ticks += 1


class TestCameraCruise(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_cruise_enabled_by_default_but_not_active_immediately(self):
        gs = game_state.GameState()
        self.assertTrue(gs.cruise_enabled)
        self.assertFalse(gs.cruise_active)

    def test_cruise_activates_only_after_idle_threshold(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        gs.frame_counter = cfg.CRUISE_IDLE_TICKS - 1
        gs.update_camera_cruise()
        self.assertFalse(gs.cruise_active, "Chưa đủ ngưỡng rảnh tay thì KHÔNG được kích hoạt")

        gs.frame_counter = cfg.CRUISE_IDLE_TICKS + 1
        gs.update_camera_cruise()
        self.assertTrue(gs.cruise_active)

    def test_touch_activity_resets_timer_and_stops_cruise_immediately(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        gs.frame_counter = cfg.CRUISE_IDLE_TICKS + 1
        gs.update_camera_cruise()
        self.assertTrue(gs.cruise_active)

        gs.touch_activity()
        self.assertFalse(gs.cruise_active)
        self.assertEqual(gs.last_activity_tick, gs.frame_counter)

        gs.frame_counter += 1
        gs.update_camera_cruise()
        self.assertFalse(gs.cruise_active, "1 khung sau touch_activity chưa thể đủ ngưỡng idle lại")

    def test_camera_moves_smoothly_while_cruising(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        gs.frame_counter = cfg.CRUISE_IDLE_TICKS + 1
        gs.update_camera_cruise()
        self.assertTrue(gs.cruise_active)
        gs.camera.cx, gs.camera.cy = 500.0, 500.0
        before = (gs.camera.cx, gs.camera.cy)
        for f in range(gs.frame_counter + 1, gs.frame_counter + 60):
            gs.frame_counter = f
            gs.update_camera_cruise()
        after = (gs.camera.cx, gs.camera.cy)
        self.assertNotEqual(before, after)

    def test_cruise_never_activates_while_following_an_ant(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        idx = int(np.where(gs.colony.alive)[0][0])
        gs.start_follow(gs.colony, idx)
        gs.last_activity_tick = -cfg.CRUISE_IDLE_TICKS - 100
        gs.frame_counter = 0
        gs.update_camera_cruise()
        self.assertFalse(gs.cruise_active)

    def test_cruise_never_activates_during_queen_founding_walk(self):
        gs = game_state.GameState()
        self.assertTrue(gs.queen_walk_active)
        gs.last_activity_tick = -cfg.CRUISE_IDLE_TICKS - 100
        gs.frame_counter = 0
        gs.update_camera_cruise()
        self.assertFalse(gs.cruise_active)

    def test_cruise_never_activates_on_maze_tab(self):
        gs = game_state.GameState()
        gs.active_tab = "maze"
        gs.last_activity_tick = -cfg.CRUISE_IDLE_TICKS - 100
        gs.frame_counter = 0
        gs.update_camera_cruise()
        self.assertFalse(gs.cruise_active)

    def test_toggle_cruise_enabled_stops_active_cruise_immediately(self):
        from antworld import hud

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        _advance_past_founding(gs)
        gs.frame_counter = cfg.CRUISE_IDLE_TICKS + 1
        gs.update_camera_cruise()
        self.assertTrue(gs.cruise_active)

        btn = next(b for b in gs.buttons if "Camera tu lai" in b.text)
        btn.on_click()
        self.assertFalse(gs.cruise_enabled)
        self.assertFalse(gs.cruise_active)
        self.assertIn("TAT", btn.text)

        btn.on_click()
        self.assertTrue(gs.cruise_enabled)
        self.assertIn("BAT", btn.text)

    def test_starting_follow_stops_active_cruise(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        gs.frame_counter = cfg.CRUISE_IDLE_TICKS + 1
        gs.update_camera_cruise()
        self.assertTrue(gs.cruise_active)

        idx = int(np.where(gs.colony.alive)[0][0])
        gs.start_follow(gs.colony, idx)
        gs.update_camera_cruise()
        self.assertFalse(gs.cruise_active)

    def test_build_cruise_waypoints_includes_surface_and_all_rooms(self):
        gs = game_state.GameState()
        gs._build_cruise_waypoints()
        self.assertGreater(len(gs.cruise_waypoints), 1)
        self.assertEqual(gs.cruise_waypoints[0][2], 0)  # diem dau la mat dat (layer 0)
        room_names = {name for (_x, _y, _layer, name) in gs.cruise_waypoints[1:]}
        self.assertEqual(len(room_names), len(gs.underground_world.rooms))

    def test_draw_cruise_indicator_does_not_crash(self):
        from antworld import hud

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        screen = gs.screen
        screen.fill((0, 0, 0))
        hud.draw_cruise_indicator(gs, screen)  # inactive - khong ve gi

        gs.cruise_active = True
        screen.fill((0, 0, 0))
        hud.draw_cruise_indicator(gs, screen)

    def test_full_cruise_cycle_visits_multiple_waypoints_without_crash(self):
        """Chạy đủ lâu để cruise đi qua vài điểm dừng (đổi cruise_idx) -
        không được crash, và tầng đang xem phải đổi theo đúng waypoint."""
        gs = game_state.GameState()
        _advance_past_founding(gs)
        gs.frame_counter = cfg.CRUISE_IDLE_TICKS + 1
        gs.update_camera_cruise()
        self.assertTrue(gs.cruise_active)
        seen_idx = {gs.cruise_idx}
        f = gs.frame_counter
        for _ in range(cfg.CRUISE_HOLD_TICKS * 3 + 10):
            f += 1
            gs.frame_counter = f
            gs.update_camera_cruise()
            seen_idx.add(gs.cruise_idx)
        self.assertGreater(len(seen_idx), 1, "Phải đi qua HƠN 1 điểm dừng sau nhiều chu kỳ hold")


if __name__ == "__main__":
    unittest.main()
