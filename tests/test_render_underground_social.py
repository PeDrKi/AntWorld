# -*- coding: utf-8 -*-
"""Test cho render_underground.draw_ant_social_fx() - hieu ung THUAN HIEN
THI (khong dung gi den mo phong): dau hieu nghi ngoi (STATE_DWELL) va lap
lanh 'chai chuot' (grooming) giua 2 con o gan nhau.

Boi canh: hanh vi nay phu thuoc dan so tu nhien vuot qua giai doan lap to
(co the mat rat nhieu tick mo phong va khong on dinh ve so luong) - nen
test o day CUONG EP truc tiep vao mang du lieu cua AntColony (dat vai con
vao STATE_DWELL, vi tri gan nhau) thay vi cho mo phong tu nhien dat toi
trang thai do, de test nhanh va on dinh.
"""
import unittest

import numpy as np
import pygame

from antworld import config as cfg
from antworld.game_state import GameState
from antworld.render_underground import draw_ant_social_fx, draw_underground_layer


def _advance_past_founding(gs, max_ticks=20000):
    ticks = 0
    while gs.colony.founding_phase and ticks < max_ticks:
        gs.step_simulation()
        ticks += 1


class TestAntSocialFx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def _force_dwelling_pair(self, gs, depth=cfg.DEPTH_GUARD, distance=0.05):
        """Cưỡng ép 2 con kiến còn sống ĐẦU TIÊN vào cùng 1 tầng, cùng
        STATE_DWELL, đứng RẤT GẦN nhau - đủ điều kiện để cả 2 nhánh hiệu
        ứng (nghỉ ngơi + chải chuốt) có cơ hội được vẽ."""
        colony = gs.colony
        alive_idx = np.where(colony.alive)[0]
        self.assertGreaterEqual(len(alive_idx), 2, "Cần ít nhất 2 con sống để test cặp gần nhau")
        a, b = int(alive_idx[0]), int(alive_idx[1])
        colony.depth[a] = colony.depth[b] = depth
        colony.state[a] = colony.state[b] = cfg.STATE_DWELL
        colony.x[a], colony.y[a] = 5.0, 5.0
        colony.x[b], colony.y[b] = 5.0 + distance, 5.0
        return a, b

    def test_no_crash_with_zero_dwelling_ants(self):
        gs = GameState()
        _advance_past_founding(gs)
        gs.colony.state[:] = cfg.STATE_SEARCHING  # ép KHÔNG con nào rảnh
        screen = gs.screen
        screen.fill((0, 0, 0))
        draw_ant_social_fx(gs, screen, gs.colony, 0)  # không được crash, không vẽ gì

    def test_no_crash_with_single_dwelling_ant(self):
        gs = GameState()
        _advance_past_founding(gs)
        idx = np.where(gs.colony.alive)[0]
        gs.colony.state[:] = cfg.STATE_SEARCHING
        gs.colony.state[idx[0]] = cfg.STATE_DWELL
        gs.colony.depth[idx[0]] = cfg.DEPTH_GUARD
        screen = gs.screen
        for _ in range(10):
            gs.frame_counter += 1
            screen.fill((0, 0, 0))
            draw_ant_social_fx(gs, screen, gs.colony, cfg.DEPTH_GUARD)  # không crash (nhánh 1 con, không có cặp)

    def test_close_dwelling_pair_renders_across_many_frames_without_crash(self):
        gs = GameState()
        _advance_past_founding(gs)
        self._force_dwelling_pair(gs, depth=cfg.DEPTH_GUARD, distance=0.05)
        screen = gs.screen
        for frame in range(150):  # đủ dài để phase-cycling (mod 3 / mod 5) chắc chắn vẽ cả 2 nhánh
            gs.frame_counter = frame
            screen.fill((0, 0, 0))
            draw_ant_social_fx(gs, screen, gs.colony, cfg.DEPTH_GUARD)

    def test_far_apart_dwelling_pair_never_grooms_but_still_rests(self):
        """2 con RẢNH RỖI nhưng ở XA nhau (> GROOMING_DISTANCE) - không
        được coi là 1 cặp chải chuốt (chỉ nhánh nghỉ ngơi chạy, nhánh
        grooming phải tự loại trừ qua kiểm tra khoảng cách) - vẫn không
        được crash."""
        gs = GameState()
        _advance_past_founding(gs)
        self._force_dwelling_pair(gs, depth=cfg.DEPTH_GUARD, distance=cfg.GROOMING_DISTANCE * 5)
        screen = gs.screen
        for frame in range(60):
            gs.frame_counter = frame
            screen.fill((0, 0, 0))
            draw_ant_social_fx(gs, screen, gs.colony, cfg.DEPTH_GUARD)

    def test_many_close_dwelling_ants_same_room_no_crash(self):
        """Nhiều hơn 2 con (kiểm tra vòng lặp O(n^2) cặp không lỗi chỉ số
        khi n > 2) - dùng toàn bộ số con sống hiện có, ép hết vào 1 phòng,
        đứng rất sát nhau."""
        gs = GameState()
        _advance_past_founding(gs)
        idx = np.where(gs.colony.alive)[0]
        gs.colony.depth[idx] = cfg.DEPTH_GUARD
        gs.colony.state[idx] = cfg.STATE_DWELL
        for i, real_i in enumerate(idx):
            gs.colony.x[real_i] = 5.0 + 0.02 * i
            gs.colony.y[real_i] = 5.0
        screen = gs.screen
        for frame in range(80):
            gs.frame_counter = frame
            screen.fill((0, 0, 0))
            draw_ant_social_fx(gs, screen, gs.colony, cfg.DEPTH_GUARD)

    def test_full_underground_layer_draw_includes_social_fx_without_crash(self):
        """Kiểm tra tích hợp thật (không gọi thẳng draw_ant_social_fx) -
        draw_underground_layer() PHẢI tự gọi nó đúng chỗ, không crash."""
        gs = GameState()
        _advance_past_founding(gs)
        self._force_dwelling_pair(gs, depth=cfg.DEPTH_GUARD, distance=0.05)
        screen = gs.screen
        for frame in range(30):
            gs.frame_counter = frame
            screen.fill((0, 0, 0))
            draw_underground_layer(gs, screen, cfg.DEPTH_GUARD)


if __name__ == "__main__":
    unittest.main()
