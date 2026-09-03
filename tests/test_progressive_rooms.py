# -*- coding: utf-8 -*-
"""Test cho tổ "phát triển dần" (progressive rooms): tổ CHÍNH lúc bật lập
tổ thật (cfg.FOUNDING_MODE_ENABLED) chỉ có ĐÚNG Phòng chúa (+ Phòng gác
cửa) sau khi chúa đào xong - các phòng khác (kho/nước/trứng/ấu trùng/
nhộng/nghĩa địa) TỰ TÁCH RA dần theo dân số, xem
UndergroundWorld.unlock_room()/GameState._check_room_unlocks().

Lưu ý: test KHÔNG dựa vào mô phỏng tự nhiên chạy hàng trăm nghìn tick để
dân số tăng tới ngưỡng (chậm, không đáng tin cậy vì cân bằng game có thể
khiến tổ tuyệt chủng nếu không có người chơi hỗ trợ) - thay vào đó gọi
thẳng GameState._check_room_unlocks(population) với dân số TỰ CHỌN.
"""
import unittest

import numpy as np
import pygame

from antworld import config as cfg
from antworld import game_state
from antworld.world import UndergroundWorld


def _advance_past_founding(gs, max_ticks=20000):
    ticks = 0
    while gs.colony.founding_phase and ticks < max_ticks:
        gs.step_simulation()
        ticks += 1


class TestUndergroundWorldProgressive(unittest.TestCase):
    def test_default_construction_unlocks_all_rooms(self):
        """progressive=False (mặc định, dùng cho tổ đối thủ) - hành vi CŨ
        không đổi: đủ 8 phòng ở đúng vị trí thiết kế ngay từ đầu."""
        uw = UndergroundWorld(cfg.NEST_POS, "")
        self.assertEqual(uw.unlocked_rooms, set(range(8)))
        for room in uw.rooms:
            self.assertNotEqual(tuple(room[2]), tuple(uw.queen_room)) if room[0] != 2 else None

    def test_progressive_construction_only_queen_and_guard_unlocked(self):
        uw = UndergroundWorld(cfg.NEST_POS, "", progressive=True)
        self.assertEqual(uw.unlocked_rooms, {2, 5})

    def test_progressive_locked_rooms_collapse_onto_queen_position_and_depth(self):
        uw = UndergroundWorld(cfg.NEST_POS, "", progressive=True)
        for room_id in (0, 1, 3, 4, 6, 7):
            pos_attr = uw._room_pos_attr[room_id]
            depth_attr = uw._room_depth_attr[room_id]
            self.assertEqual(tuple(getattr(uw, pos_attr)), tuple(uw.queen_room))
            self.assertEqual(getattr(uw, depth_attr), uw.queen_depth)

    def test_guard_room_always_at_its_own_real_position(self):
        """Phòng gác cửa LUÔN mở sẵn (đơn giản hoá có chủ đích) - không
        gộp vào Phòng chúa dù progressive=True."""
        uw = UndergroundWorld(cfg.NEST_POS, "", progressive=True)
        self.assertNotEqual(tuple(uw.guard_room), tuple(uw.queen_room))
        self.assertEqual(uw.guard_depth, cfg.DEPTH_GUARD)

    def test_unlock_room_moves_to_real_designed_position(self):
        uw = UndergroundWorld(cfg.NEST_POS, "", progressive=True)
        ok = uw.unlock_room(0)
        self.assertTrue(ok)
        self.assertIn(0, uw.unlocked_rooms)
        self.assertNotEqual(tuple(uw.storage), tuple(uw.queen_room))
        self.assertEqual(uw.storage_depth, cfg.DEPTH_STORAGE)
        self.assertEqual(uw.rooms[0][5], cfg.DEPTH_STORAGE)

    def test_unlock_room_returns_false_when_called_twice(self):
        uw = UndergroundWorld(cfg.NEST_POS, "", progressive=True)
        self.assertTrue(uw.unlock_room(0))
        self.assertFalse(uw.unlock_room(0))

    def test_unlock_room_invalid_id_returns_false(self):
        uw = UndergroundWorld(cfg.NEST_POS, "", progressive=True)
        self.assertFalse(uw.unlock_room(2))  # phòng chúa vốn đã "mở" từ đầu
        self.assertFalse(uw.unlock_room(99))

    def test_room_center_and_radius_by_id_uses_queen_radius_while_locked(self):
        """Kiến 'lượn' (STATE_DWELL) trong 1 phòng CÒN KHOÁ phải dùng ĐÚNG
        bán kính hiện tại của Phòng chúa (nơi nó thực sự đang đứng) - nếu
        dùng nhầm bán kính GỐC của chính phòng đó, kiến có thể lượn ra
        ngoài vòng tròn đang vẽ."""
        uw = UndergroundWorld(cfg.NEST_POS, "", progressive=True)
        queen_center, queen_radius = uw.room_center_and_radius_by_id(2, founding_phase=False)
        locked_center, locked_radius = uw.room_center_and_radius_by_id(0, founding_phase=False)
        self.assertEqual(tuple(locked_center), tuple(queen_center))
        self.assertEqual(locked_radius, queen_radius)

    def test_room_center_and_radius_by_id_uses_founding_chamber_radius_during_founding(self):
        uw = UndergroundWorld(cfg.NEST_POS, "", progressive=True)
        _center, radius = uw.room_center_and_radius_by_id(0, founding_phase=True)
        self.assertEqual(radius, cfg.ROOM_RADIUS_FOUNDING_CHAMBER)

    def test_room_center_and_radius_by_id_uses_own_radius_once_unlocked(self):
        uw = UndergroundWorld(cfg.NEST_POS, "", progressive=True)
        uw.unlock_room(0)
        center, radius = uw.room_center_and_radius_by_id(0, founding_phase=False)
        self.assertEqual(tuple(center), tuple(uw.storage))
        self.assertEqual(radius, uw._base_radius[0])


class TestGameStateRoomUnlockSchedule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_new_game_starts_with_only_queen_and_guard_room(self):
        gs = game_state.GameState()
        self.assertEqual(gs.underground_world.unlocked_rooms, {2, 5})

    def test_egg_room_unlocks_immediately_after_founding_completes(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        gs.check_alerts()
        self.assertIn(4, gs.underground_world.unlocked_rooms)

    def test_check_room_unlocks_follows_schedule_order(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        gs._check_room_unlocks(cfg.FOUNDING_NANITIC_TARGET)
        self.assertEqual(gs.underground_world.unlocked_rooms, {2, 4, 5})
        gs._check_room_unlocks(8)
        self.assertEqual(gs.underground_world.unlocked_rooms, {1, 2, 4, 5})
        gs._check_room_unlocks(40)
        self.assertEqual(gs.underground_world.unlocked_rooms, set(range(8)))

    def test_check_room_unlocks_logs_event_and_toast(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        n_events_before = len(gs.events)
        gs._check_room_unlocks(8)
        self.assertGreater(len(gs.events), n_events_before)
        self.assertIn("đào thêm", gs.events[-1]["text"])
        self.assertIsNotNone(gs.events[-1]["pos"])

    def test_check_room_unlocks_idempotent(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        gs._check_room_unlocks(40)
        n_events_after_first = len(gs.events)
        gs._check_room_unlocks(40)
        self.assertEqual(len(gs.events), n_events_after_first)

    def test_only_nest_in_the_game_uses_progressive_unlocking(self):
        """Game chỉ có ĐÚNG 1 tổ (của người chơi) - không có tổ đối thủ nào
        khác né tránh cơ chế này (xem invasion.py: quân xâm nhập không có
        tổ/nhà riêng) - khi bật lập tổ thật, tổ DUY NHẤT đó PHẢI luôn dùng
        progressive=True, không có ngoại lệ."""
        gs = game_state.GameState()
        self.assertTrue(cfg.FOUNDING_MODE_ENABLED)
        self.assertNotEqual(gs.underground_world.unlocked_rooms, set(range(8)))

    def test_foraging_ant_redirected_to_queen_chamber_while_storage_locked(self):
        gs = game_state.GameState()
        _advance_past_founding(gs)
        uw = gs.underground_world
        self.assertNotIn(0, uw.unlocked_rooms)
        self.assertEqual(tuple(uw.storage), tuple(uw.queen_room))
        self.assertEqual(uw.storage_depth, uw.queen_depth)

    def test_render_all_depths_without_crash_at_every_unlock_stage(self):
        from antworld import hud
        from antworld.render_underground import draw_underground_layer

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        _advance_past_founding(gs)
        screen = gs.screen
        populations_to_try = [0, cfg.FOUNDING_NANITIC_TARGET, 8, 12, 18, 28, 40]
        for pop in populations_to_try:
            gs._check_room_unlocks(pop)
            for depth in range(6):
                screen.fill((0, 0, 0))
                draw_underground_layer(gs, screen, depth)

    def test_save_load_preserves_unlocked_rooms(self):
        import os

        gs = game_state.GameState()
        _advance_past_founding(gs)
        gs._check_room_unlocks(12)
        expected = set(gs.underground_world.unlocked_rooms)
        try:
            self.assertTrue(gs.save_game())
            gs2 = game_state.GameState()
            gs2.load_game()
            self.assertEqual(gs2.underground_world.unlocked_rooms, expected)
            self.assertEqual(tuple(gs2.underground_world.storage), tuple(gs.underground_world.storage))
        finally:
            if os.path.exists(game_state.SAVE_PATH):
                os.remove(game_state.SAVE_PATH)


if __name__ == "__main__":
    unittest.main()
