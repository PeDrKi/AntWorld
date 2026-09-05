# -*- coding: utf-8 -*-
"""Test cho tính năng ẩn/hiện TOÀN BỘ panel cùng lúc (phím Tab) - xem
GameState.toggle_ui_hidden()/visible_panels() và hud.draw_ui_hidden_hint().
"""
import unittest

import pygame

from antworld import game_state, hud
from antworld.ui_widgets import Panel


class TestUiHidden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_ui_not_hidden_by_default(self):
        gs = game_state.GameState()
        self.assertFalse(gs.ui_hidden)

    def test_toggle_ui_hidden_flips_state(self):
        gs = game_state.GameState()
        gs.toggle_ui_hidden()
        self.assertTrue(gs.ui_hidden)
        gs.toggle_ui_hidden()
        self.assertFalse(gs.ui_hidden)

    def test_visible_panels_empty_while_hidden_in_sim_tab(self):
        gs = game_state.GameState()
        hud.build_toolbar(gs)
        self.assertGreater(len(gs.visible_panels()), 0)
        gs.toggle_ui_hidden()
        self.assertEqual(gs.visible_panels(), [])

    def test_visible_panels_empty_while_hidden_in_maze_tab(self):
        gs = game_state.GameState()
        hud.build_toolbar(gs)
        gs.active_tab = "maze"
        self.assertGreater(len(gs.visible_panels()), 0)
        gs.toggle_ui_hidden()
        self.assertEqual(gs.visible_panels(), [])

    def test_game_over_panel_still_visible_while_ui_hidden(self):
        """Panel Game Over là NGOẠI LỆ duy nhất - vẫn phải hiện dù đang
        ẩn toàn bộ giao diện, để người chơi biết tổ đã tuyệt chủng và bấm
        được nút Chơi lại."""
        gs = game_state.GameState()
        hud.build_toolbar(gs)
        gs.toggle_ui_hidden()
        gs.game_over = True
        gs.game_over_panel = Panel(100, 100, 200, 100, "Game Over")
        self.assertIn(gs.game_over_panel, gs.visible_panels())

    def test_draw_ui_hidden_hint_only_draws_when_hidden(self):
        gs = game_state.GameState()
        screen = gs.screen
        screen.fill((0, 0, 0))
        hud.draw_ui_hidden_hint(gs, screen)  # ui_hidden=False -> khong ve gi, khong crash

        gs.toggle_ui_hidden()
        screen.fill((0, 0, 0))
        hud.draw_ui_hidden_hint(gs, screen)  # ui_hidden=True -> ve, khong crash

    def test_render_does_not_crash_while_ui_hidden_sim_tab(self):
        from antworld.__main__ import render

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        gs.toggle_ui_hidden()
        render(gs)  # không được crash

    def test_render_does_not_crash_while_ui_hidden_maze_tab(self):
        from antworld.__main__ import render

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        gs.active_tab = "maze"
        gs.toggle_ui_hidden()
        render(gs)  # không được crash

    def test_tab_key_toggles_ui_hidden_through_handle_events(self):
        from antworld.__main__ import handle_events

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        self.assertFalse(gs.ui_hidden)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
        handle_events(gs)
        self.assertTrue(gs.ui_hidden)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
        handle_events(gs)
        self.assertFalse(gs.ui_hidden)


if __name__ == "__main__":
    unittest.main()
