# -*- coding: utf-8 -*-
"""Test cho Nhat ky su kien (GameState.events/log_event/jump_to_event/
_check_population_milestones) va nut "Tu dong ghe xem su kien" - xem
game_state.py va hud.draw_event_log().
"""
import os
import unittest

import pygame

from antworld import config as cfg
from antworld import game_state


def _advance_past_founding(gs, max_ticks=20000):
    ticks = 0
    while gs.colony.founding_phase and ticks < max_ticks:
        gs.step_simulation()
        ticks += 1


class TestEventLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_new_game_logs_queen_landing_event(self):
        gs = game_state.GameState()
        self.assertEqual(len(gs.events), 1)
        self.assertIn("hạ cánh", gs.events[0]["text"])
        self.assertIsNotNone(gs.events[0]["pos"])

    def test_log_event_appends_and_respects_max_length(self):
        gs = game_state.GameState()
        for i in range(50):
            gs.log_event(f"Sự kiện {i}", pos=None)
        self.assertLessEqual(len(gs.events), 40)
        self.assertEqual(gs.events[-1]["text"], "Sự kiện 49")

    def test_log_event_without_pos_never_moves_camera(self):
        gs = game_state.GameState()
        gs.auto_visit_events = True
        gs.camera.cx, gs.camera.cy = 1.0, 2.0
        gs.log_event("Thông báo chung, không gắn vị trí", pos=None)
        self.assertEqual((gs.camera.cx, gs.camera.cy), (1.0, 2.0))

    def test_auto_visit_moves_camera_when_enabled(self):
        gs = game_state.GameState()
        gs.auto_visit_events = True
        gs.log_event("Test", pos=(9.0, 4.0), layer=3)
        self.assertEqual((gs.camera.cx, gs.camera.cy), (9.0, 4.0))
        self.assertEqual(gs.current_layer, 3)

    def test_auto_visit_disabled_by_default_and_does_not_move_camera(self):
        gs = game_state.GameState()
        self.assertFalse(gs.auto_visit_events)
        gs.camera.cx, gs.camera.cy = 1.0, 2.0
        gs.log_event("Test", pos=(9.0, 4.0), layer=3)
        self.assertEqual((gs.camera.cx, gs.camera.cy), (1.0, 2.0))

    def test_auto_visit_does_not_override_active_following(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        import numpy as np
        idx = int(np.where(gs.colony.alive)[0][0])
        gs.start_follow(gs.colony, idx)
        gs.auto_visit_events = True
        gs.camera.cx, gs.camera.cy = 1.0, 2.0
        gs.log_event("Test", pos=(9.0, 4.0), layer=3)
        self.assertEqual((gs.camera.cx, gs.camera.cy), (1.0, 2.0))

    def test_jump_to_event_moves_camera_to_correct_recent_event(self):
        gs = game_state.GameState()
        gs.log_event("Cũ hơn", pos=(1.0, 1.0), layer=0)
        gs.log_event("Mới nhất", pos=(8.0, 8.0), layer=2)
        gs.camera.cx, gs.camera.cy = 0.0, 0.0
        gs.jump_to_event(0)  # 0 = mới nhất
        self.assertEqual((gs.camera.cx, gs.camera.cy), (8.0, 8.0))
        self.assertEqual(gs.current_layer, 2)

    def test_jump_to_event_with_no_pos_does_nothing(self):
        gs = game_state.GameState()
        gs.log_event("Không vị trí", pos=None)
        gs.camera.cx, gs.camera.cy = 5.0, 5.0
        gs.jump_to_event(0)
        self.assertEqual((gs.camera.cx, gs.camera.cy), (5.0, 5.0))

    def test_jump_to_event_out_of_range_does_not_crash(self):
        gs = game_state.GameState()
        gs.jump_to_event(999)  # không crash dù chưa có/thiếu sự kiện

    def test_population_milestone_fires_once_per_threshold(self):
        gs = game_state.GameState()
        gs._check_population_milestones(10)
        gs._check_population_milestones(10)  # gọi lại CÙNG mốc, không được bắn thêm
        milestone_events = [e for e in gs.events if "10 cá thể" in e["text"]]
        self.assertEqual(len(milestone_events), 1)

    def test_population_milestone_skips_ahead_correctly(self):
        gs = game_state.GameState()
        gs._check_population_milestones(120)  # nhảy thẳng qua 10/25/50/100
        fired = [e["text"] for e in gs.events if "cá thể" in e["text"]]
        self.assertEqual(len(fired), 4)  # 10, 25, 50, 100

    def test_toggle_auto_visit_events_button_label_updates(self):
        from antworld import hud

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        btn = next(b for b in gs.buttons if "Tu dong ghe xem su kien" in b.text)
        self.assertFalse(gs.auto_visit_events)
        self.assertIn("TAT", btn.text)
        btn.on_click()
        self.assertTrue(gs.auto_visit_events)
        self.assertIn("BAT", btn.text)

    def test_event_log_panel_always_visible_in_sim_tab(self):
        from antworld import hud

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        self.assertIn(gs.event_log_panel, gs.visible_panels())

    def test_draw_event_log_does_not_crash_empty_or_populated(self):
        from antworld import hud

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        screen = gs.screen
        screen.fill((0, 0, 0))
        hud.draw_event_log(gs, screen)  # rỗng lúc mới (thật ra đã có 1 sự kiện hạ cánh)

        for i in range(20):
            gs.log_event(f"Sự kiện dài dòng để kiểm tra cắt bớt chữ số {i} " * 2, pos=(1.0, 1.0))
        screen.fill((0, 0, 0))
        hud.draw_event_log(gs, screen)

    def test_events_and_settings_survive_save_load_round_trip(self):
        gs = game_state.GameState()
        gs.auto_visit_events = True
        gs.log_event("Sự kiện cần lưu lại", pos=(3.0, 4.0), layer=1)
        try:
            self.assertTrue(gs.save_game())
            gs2 = game_state.GameState()
            gs2.load_game()
            self.assertTrue(gs2.auto_visit_events)
            self.assertEqual(gs2.events[-1]["text"], "Sự kiện cần lưu lại")
        finally:
            if os.path.exists(game_state.SAVE_PATH):
                os.remove(game_state.SAVE_PATH)

    def test_loading_old_save_without_event_fields_does_not_crash(self):
        import pickle

        gs = game_state.GameState()
        data = {
            "version": 2,
            "colony": gs.colony,
            "surface_world": gs.surface_world,
            "enemy": gs.enemy,
            "invasion": gs.invasion,
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
            # KHONG co events/auto_visit_events/next_milestone_idx
        }
        try:
            with open(game_state.SAVE_PATH, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            gs2 = game_state.GameState()
            ok = gs2.load_game()
            self.assertTrue(ok)
            self.assertEqual(len(gs2.events), 0)
            self.assertFalse(gs2.auto_visit_events)
        finally:
            if os.path.exists(game_state.SAVE_PATH):
                os.remove(game_state.SAVE_PATH)


if __name__ == "__main__":
    unittest.main()
