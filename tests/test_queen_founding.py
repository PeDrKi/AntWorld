# -*- coding: utf-8 -*-
"""Test cho quy trình LẬP TỔ: kiến chúa tự đi bộ trên mặt đất tìm chỗ rồi
đào hang xuống lòng đất (GameState.update_queen_founding()/
update_queen_walk_camera(), cfg.QUEEN_WALK_*/QUEEN_DIG_TICKS) - THAY VÌ
chỉ được đặt sẵn yên vị trong 1 hốc lập tổ có sẵn như phiên bản trước.
"""
import unittest

import pygame

from antworld import config as cfg
from antworld import game_state


class TestQueenFoundingWalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    def test_new_game_starts_with_queen_walking_on_surface(self):
        """Ván mới LUÔN bắt đầu từ đúng 1 chúa đang đi bộ trên mặt đất
        (population=0, chưa có thợ nào) - không phải 1 tổ đã có sẵn thợ."""
        gs = game_state.GameState()
        self.assertTrue(cfg.FOUNDING_MODE_ENABLED)
        self.assertTrue(gs.colony.founding_phase)
        self.assertEqual(int(gs.colony.alive.sum()), 0)
        self.assertTrue(gs.queen_walk_active)
        self.assertTrue(gs.queen_has_wings, "Chua vua 'ha canh' phai con canh")
        self.assertEqual(gs.queen_dig_timer, 0)
        self.assertEqual(gs.current_layer, 0, "Phai dang o MAT DAT, chua xuong long dat voi")

    def test_queen_sheds_wings_after_reaching_first_waypoint(self):
        gs = game_state.GameState()
        ticks = 0
        while gs.queen_has_wings and ticks < 20000:
            gs.step_simulation()
            ticks += 1
        self.assertFalse(gs.queen_has_wings)
        self.assertGreater(ticks, 0)

    def test_queen_walk_target_never_lands_on_blocked_terrain(self):
        gs = game_state.GameState()
        for _ in range(50):
            tx, ty = gs._pick_queen_walk_target()
            self.assertFalse(bool(gs.surface_world.is_blocked(int(tx), int(ty))),
                              "Diem dung KHONG duoc roi vao o da/nuoc")
            self.assertGreaterEqual(tx, 0)
            self.assertLess(tx, cfg.GRID_SIZE)
            self.assertGreaterEqual(ty, 0)
            self.assertLess(ty, cfg.GRID_SIZE)

    def test_full_founding_sequence_ends_underground_at_queen_room(self):
        """Chạy hết trình tự: đi bộ -> đào hang -> tự chuyển camera + tầng
        đang xem xuống đúng Phòng chúa dưới lòng đất."""
        gs = game_state.GameState()
        ticks = 0
        while gs.queen_walk_active and ticks < 20000:
            gs.step_simulation()
            ticks += 1
        self.assertFalse(gs.queen_walk_active, "Phai da dao xong trong gioi han tick")
        self.assertEqual(gs.current_layer, cfg.DEPTH_QUEEN)
        qx, qy = gs.underground_world.queen_room
        self.assertAlmostEqual(gs.camera.cx, float(qx), places=3)
        self.assertAlmostEqual(gs.camera.cy, float(qy), places=3)
        self.assertTrue(gs.colony.founding_phase, "Van dang lap to (chua de trung), chi la da vao long dat")

    def test_first_workers_hatch_after_full_founding_sequence(self):
        """Sau khi đào xong, chúa bắt đầu đẻ trứng bằng dự trữ riêng, và
        cuối cùng đủ số nanitic đầu tiên -> founding_phase tắt hẳn."""
        gs = game_state.GameState()
        ticks = 0
        while gs.colony.founding_phase and ticks < 200000:
            gs.step_simulation()
            ticks += 1
        self.assertFalse(gs.colony.founding_phase)
        self.assertGreaterEqual(int(gs.colony.alive.sum()), cfg.FOUNDING_NANITIC_TARGET)

    def test_camera_follows_queen_smoothly_while_walking(self):
        gs = game_state.GameState()
        gs.step_simulation()
        gs.update_queen_walk_camera()
        # Camera phai NHUC NHICH ve phia chua (khong dung im tai vi tri cu),
        # nhung KHONG nhay thang toi (bam muot dan, xem FOLLOW_CAMERA_SMOOTH)
        self.assertNotEqual((gs.camera.cx, gs.camera.cy), (gs.queen_walk_x, gs.queen_walk_y))

    def test_render_does_not_crash_during_walk_and_dig_stages(self):
        from antworld import hud
        from antworld.render_surface import draw_surface_layer
        from antworld.render_underground import draw_underground_layer

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        screen = gs.screen

        # Giai doan dang di bo (con canh)
        screen.fill((0, 0, 0))
        draw_surface_layer(gs, screen)

        # Chay toi khi bat dau dao (dig_timer > 0) va ve thu
        ticks = 0
        while gs.queen_dig_timer == 0 and gs.queen_walk_active and ticks < 20000:
            gs.step_simulation()
            ticks += 1
        screen.fill((0, 0, 0))
        draw_surface_layer(gs, screen)

        # Chay het, ve lai canh Phong chua duoi long dat
        while gs.queen_walk_active and ticks < 20000:
            gs.step_simulation()
            ticks += 1
        screen.fill((0, 0, 0))
        draw_underground_layer(gs, screen, gs.current_layer)

    def test_save_and_load_mid_founding_walk_round_trips(self):
        import os

        gs = game_state.GameState()
        gs.step_simulation()  # chua da nhuc nhich 1 chut, khac vi tri ban dau
        try:
            ok = gs.save_game()
            self.assertTrue(ok)
            saved_x, saved_y = gs.queen_walk_x, gs.queen_walk_y
            saved_hops = gs.queen_walk_hops_left

            gs2 = game_state.GameState()  # 1 van MOI (chua khac vi tri) roi tai de
            gs2.load_game()
            self.assertTrue(gs2.queen_walk_active)
            self.assertAlmostEqual(gs2.queen_walk_x, saved_x, places=4)
            self.assertAlmostEqual(gs2.queen_walk_y, saved_y, places=4)
            self.assertEqual(gs2.queen_walk_hops_left, saved_hops)
        finally:
            if os.path.exists(game_state.SAVE_PATH):
                os.remove(game_state.SAVE_PATH)

    def test_founding_controls_panel_visible_only_while_walking(self):
        """Panel 'Điều khiển lập tổ' chỉ được nhận click (visible_panels())
        đúng lúc chúa còn trên mặt đất - biến mất ngay khi đã vào lòng đất,
        kẻo chiếm chỗ click vô hình vô ích ở góc màn hình."""
        from antworld import hud

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        self.assertIn(gs.founding_panel, gs.visible_panels())

        ticks = 0
        while gs.queen_walk_active and ticks < 20000:
            gs.step_simulation()
            ticks += 1
        self.assertNotIn(gs.founding_panel, gs.visible_panels())

    def test_adjust_queen_walk_speed_clamped_to_config_range(self):
        gs = game_state.GameState()
        gs.adjust_queen_walk_speed(-999)
        self.assertAlmostEqual(gs.queen_walk_speed, cfg.QUEEN_WALK_SPEED_MIN)
        gs.adjust_queen_walk_speed(999)
        self.assertAlmostEqual(gs.queen_walk_speed, cfg.QUEEN_WALK_SPEED_MAX)

    def test_adjust_queen_dig_speed_mult_clamped_to_config_range(self):
        gs = game_state.GameState()
        gs.adjust_queen_dig_speed_mult(-999)
        self.assertAlmostEqual(gs.queen_dig_speed_mult, cfg.QUEEN_DIG_SPEED_MULT_MIN)
        gs.adjust_queen_dig_speed_mult(999)
        self.assertAlmostEqual(gs.queen_dig_speed_mult, cfg.QUEEN_DIG_SPEED_MULT_MAX)

    def test_adjust_queen_wander_radius_clamped_to_config_range(self):
        gs = game_state.GameState()
        gs.adjust_queen_wander_radius(-999)
        self.assertAlmostEqual(gs.queen_wander_radius, cfg.QUEEN_WALK_RADIUS_MIN)
        gs.adjust_queen_wander_radius(999)
        self.assertAlmostEqual(gs.queen_wander_radius, cfg.QUEEN_WALK_RADIUS_MAX)

    def test_adjust_queen_walk_hops_clamped_to_config_range(self):
        gs = game_state.GameState()
        gs.adjust_queen_walk_hops(-999)
        self.assertEqual(gs.queen_walk_hops_left, cfg.QUEEN_WALK_HOPS_STEP_MIN)
        gs.adjust_queen_walk_hops(999)
        self.assertEqual(gs.queen_walk_hops_left, cfg.QUEEN_WALK_HOPS_STEP_MAX)

    def test_higher_dig_speed_mult_finishes_digging_faster(self):
        """Tăng queen_dig_speed_mult phải làm chúa đào XONG SỚM HƠN (ít
        tick mô phỏng hơn) so với giữ nguyên mặc định - đây là mục đích
        cốt lõi của thanh điều chỉnh này."""
        gs_slow = game_state.GameState()
        gs_slow.queen_walk_hops_left = 0  # bỏ qua bước đi bộ, vào thẳng đào
        ticks_slow = 0
        while gs_slow.queen_walk_active and ticks_slow < 20000:
            gs_slow.step_simulation()
            ticks_slow += 1

        gs_fast = game_state.GameState()
        gs_fast.queen_walk_hops_left = 0
        gs_fast.queen_dig_speed_mult = cfg.QUEEN_DIG_SPEED_MULT_MAX
        ticks_fast = 0
        while gs_fast.queen_walk_active and ticks_fast < 20000:
            gs_fast.step_simulation()
            ticks_fast += 1

        self.assertLess(ticks_fast, ticks_slow)

    def test_higher_walk_speed_reaches_waypoints_faster(self):
        gs_slow = game_state.GameState()
        gs_slow.queen_walk_speed = cfg.QUEEN_WALK_SPEED_MIN
        ticks_slow = 0
        while gs_slow.queen_has_wings and ticks_slow < 20000:
            gs_slow.step_simulation()
            ticks_slow += 1

        gs_fast = game_state.GameState()
        gs_fast.queen_walk_speed = cfg.QUEEN_WALK_SPEED_MAX
        ticks_fast = 0
        while gs_fast.queen_has_wings and ticks_fast < 20000:
            gs_fast.step_simulation()
            ticks_fast += 1

        self.assertLess(ticks_fast, ticks_slow)

    def test_larger_wander_radius_produces_targets_farther_from_nest(self):
        import math

        nx, ny = cfg.NEST_POS
        gs = game_state.GameState()

        gs.queen_wander_radius = cfg.QUEEN_WALK_RADIUS_MIN
        small_dists = []
        for _ in range(40):
            tx, ty = gs._pick_queen_walk_target()
            small_dists.append(math.hypot(tx - nx, ty - ny))

        gs.queen_wander_radius = cfg.QUEEN_WALK_RADIUS_MAX
        large_dists = []
        for _ in range(40):
            tx, ty = gs._pick_queen_walk_target()
            large_dists.append(math.hypot(tx - nx, ty - ny))

        self.assertLess(sum(small_dists) / len(small_dists), sum(large_dists) / len(large_dists))

    def test_setting_hops_to_zero_skips_remaining_wander_stops(self):
        gs = game_state.GameState()
        gs.queen_walk_hops_left = 0
        ticks = 0
        # Chạy tới khi chạm điểm dừng HIỆN TẠI (không phải hops=0 lập tức -
        # vẫn phải đi hết quãng đường tới điểm dừng ĐANG NHẮM TỚI trước).
        while gs.queen_dig_timer == 0 and gs.queen_walk_active and ticks < 20000:
            gs.step_simulation()
            ticks += 1
        self.assertTrue(gs.queen_dig_timer > 0 or not gs.queen_walk_active)

    def test_runtime_adjustments_survive_save_load_round_trip(self):
        import os

        gs = game_state.GameState()
        gs.adjust_queen_walk_speed(0.02)
        gs.adjust_queen_dig_speed_mult(0.5)
        gs.adjust_queen_wander_radius(1.0)
        gs.adjust_queen_walk_hops(2)
        try:
            self.assertTrue(gs.save_game())
            gs2 = game_state.GameState()
            gs2.load_game()
            self.assertAlmostEqual(gs2.queen_walk_speed, gs.queen_walk_speed)
            self.assertAlmostEqual(gs2.queen_dig_speed_mult, gs.queen_dig_speed_mult)
            self.assertAlmostEqual(gs2.queen_wander_radius, gs.queen_wander_radius)
            self.assertEqual(gs2.queen_walk_hops_left, gs.queen_walk_hops_left)
        finally:
            if os.path.exists(game_state.SAVE_PATH):
                os.remove(game_state.SAVE_PATH)

    def test_loading_old_save_without_queen_walk_fields_does_not_crash(self):
        """File luu tu BAN CU (truoc khi co tinh nang lap to nay) khong co
        cac truong queen_walk_* - phai co gia tri mac dinh an toan, khong
        duoc crash luc tai."""
        import os
        import pickle

        gs = game_state.GameState()
        _advance = 0
        while int(gs.colony.alive.sum()) == 0 and _advance < 20000:
            gs.step_simulation()
            _advance += 1

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
            # KHONG co queen_walk_* - gia lap file luu tu ban cu
        }
        try:
            with open(game_state.SAVE_PATH, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            gs2 = game_state.GameState()
            ok = gs2.load_game()
            self.assertTrue(ok)
            self.assertFalse(gs2.queen_walk_active)
        finally:
            if os.path.exists(game_state.SAVE_PATH):
                os.remove(game_state.SAVE_PATH)


if __name__ == "__main__":
    unittest.main()
