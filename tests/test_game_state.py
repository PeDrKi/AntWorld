# -*- coding: utf-8 -*-
"""Test tich hop cap cao nhat: khoi tao GameState THAT (dung nguyen
duong code game.py dung khi choi that - tai sprite, font, sinh 2 doi
tho/dich, dan kien chinh + doi thu) roi chay thu vai tram tick, dam bao
khong crash. Day la "smoke test" bao quat nhat - khong kiem tra chi tiet
tung con so, chi dam bao toan bo cac module ghep lai voi nhau van chay
duoc, vi day la loai loi de xay ra nhat khi sua 1 file rieng le (vd sua
config.py) ma quen kiem tra anh huong toi cho khac.
"""
import unittest

import pygame

from antworld import game_state


def _advance_past_founding(gs, max_ticks=20000):
    """Chạy nhanh qua giai đoạn lập tổ (chúa tự đi tìm chỗ + đào hang +
    đẻ lứa nanitic đầu tiên - xem cfg.FOUNDING_MODE_ENABLED, mặc định BẬT)
    để có 1 đàn kiến ĐÃ CÓ SẴN vài con, giống hệt hành vi TRƯỚC KHI có
    tính năng lập tổ - hầu hết test dưới đây kiểm tra hành vi ĐÀN KIẾN ĐÃ
    ỔN ĐỊNH, không phải bản thân quá trình lập tổ (đã có test riêng trong
    test_queen_founding.py)."""
    ticks = 0
    while int(gs.colony.alive.sum()) == 0 and ticks < max_ticks:
        gs.step_simulation()
        ticks += 1


class TestGameStateSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.gs = game_state.GameState()
        _advance_past_founding(cls.gs)

    def test_fonts_are_real_font_objects(self):
        for f in (self.gs.font, self.gs.font_small, self.gs.font_big, self.gs.font_hud):
            self.assertIsInstance(f, pygame.font.Font)

    def test_colonies_exist_and_populated(self):
        self.assertGreater(int(sum(self.gs.colony.alive)), 0,
                            "Dan kien chinh phai co it nhat vai con luc moi bat dau.")

    def test_run_many_ticks_without_crash(self):
        # Chi can chay khong nem exception la dat - cac bat bien chi tiet
        # hon (NaN, tran dan so...) da duoc test rieng trong test_ants.py
        # o cap do AntColony don le.
        for _ in range(300):
            self.gs.colony.update()

    def test_save_game_after_rendering_does_not_crash(self):
        """Regression test: render_surface.py tung co luc gan cache anh
        nen dia hinh (pygame.Surface) THANG LEN state.surface_world de
        tang toc do ve - nhung surface_world lai bi pickle NGUYEN VEN moi
        khi save_game() (xem save_game() trong game_state.py), va
        pygame.Surface KHONG pickle duoc -> chi can nguoi choi ve ra man
        hinh 1 lan (luon xay ra) roi bam "Luu van choi" la loi ngay. Test
        nay ve thu 1 khung hinh THAT (dung dung code duong dan game that
        di qua) truoc khi goi save_game(), dam bao khong con object nao
        khong pickle-duoc bi gan nham len surface_world/colony/enemy/
        invasion (4 thu duy nhat thuc su bi pickle)."""
        import os
        from antworld import hud
        from antworld.render_surface import draw_surface_layer
        from antworld import config as cfg

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        screen = gs.screen
        screen.fill(cfg.COLOR_BG_SURFACE)
        draw_surface_layer(gs, screen)  # buoc nay tung kich hoat lai loi
        hud.draw_hud(gs, screen)
        hud.draw_toolbar(gs, screen)

        ok = gs.save_game()
        self.assertTrue(
            ok, f"save_game() that bai sau khi render: {gs.toasts[-1]['msg'] if gs.toasts else '?'}"
        )
        if os.path.exists(game_state.SAVE_PATH):
            os.remove(game_state.SAVE_PATH)

    def test_extinction_triggers_game_over_and_restart_recovers(self):
        """Regression test cho tinh nang Game Over: truoc day khi dan so
        ve 0, game chi hien 1 toast roi mo phong van chay tiep VO NGHIA
        mai mai o trang thai 0 kien - khong co man hinh ket thuc, khong co
        cach choi lai. Test nay dam bao: (1) tuyet chung THAT SU (sau khi
        het giai doan lap to) phai bat co game_over + dung mo phong,
        (2) KHONG duoc bao gio bao tuyet chung trong luc dang lap to (dan
        so=0 luc do la BINH THUONG), (3) bam nut "Choi lai" phai dua game
        ve trang thai choi duoc binh thuong, khong con co game_over."""
        from antworld import hud

        gs = game_state.GameState()
        hud.build_toolbar(gs)

        # (2) Dang lap to (dan so=0) KHONG duoc coi la tuyet chung
        gs.colony.founding_phase = True
        gs.check_alerts()
        self.assertFalse(gs.game_over, "Bao nham tuyet chung trong luc dang lap to")

        # (1) Tuyet chung THAT SU sau khi da qua giai doan lap to
        gs.colony.founding_phase = False
        gs.colony.alive[:] = False
        gs.check_alerts()
        self.assertTrue(gs.game_over)
        self.assertTrue(gs.sim_paused)
        self.assertIsNotNone(gs.game_over_panel)

        # (3) Bam nut "Choi lai" phai reset duoc hoan toan
        restart_btn = gs.game_over_panel.children[0]
        restart_btn.on_click()
        self.assertFalse(gs.game_over)
        self.assertFalse(gs.sim_paused)
        self.assertIsNone(gs.game_over_panel)
        # Ngay sau restart, dan so = 0 la BINH THUONG (chua lai bat dau tu
        # dau, dang lap to - xem test_queen_founding.py) - chay nhanh qua
        # giai doan do de xac nhan restart THAT SU hoat dong dung, khong
        # chi la "khong crash" ma con thuc su lap duoc to moi.
        _advance_past_founding(gs)
        self.assertGreater(int(gs.colony.alive.sum()), 0)

        # Chay tiep vai tick sau restart phai on, khong loi
        for _ in range(20):
            gs.step_simulation()
            gs.check_alerts()

    def test_follow_ant_card_shows_and_hides_with_follow_state(self):
        """Thẻ thông tin con kiến đang theo dõi (ant_panel) chỉ được xuất
        hiện trong visible_panels() (và do đó nhận click) khi THỰC SỰ đang
        theo dõi 1 con kiến - không được lẫn vào danh sách panel khi không
        theo dõi ai, kẻo chiếm chỗ click vô hình ở góc màn hình."""
        from antworld import hud
        import numpy as np

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        self.assertNotIn(gs.ant_panel, gs.visible_panels())

        _advance_past_founding(gs)
        idx = int(np.where(gs.colony.alive)[0][0])
        gs.start_follow(gs.colony, idx)
        self.assertIn(gs.ant_panel, gs.visible_panels())

        gs.stop_follow()
        self.assertNotIn(gs.ant_panel, gs.visible_panels())

    def test_draw_ant_card_does_not_crash_while_following_and_simulating(self):
        """draw_ant_card() phải vẽ được (không crash) trong lúc đang theo
        dõi 1 con kiến CÒN SỐNG qua nhiều tick mô phỏng, kể cả khi trạng
        thái/vai trò/tầng của nó thay đổi liên tục."""
        from antworld import hud
        import numpy as np

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        _advance_past_founding(gs)
        idx = int(np.where(gs.colony.alive)[0][0])
        gs.start_follow(gs.colony, idx)
        screen = gs.screen
        for _ in range(60):
            gs.colony.update()
            screen.fill((0, 0, 0))
            hud.draw_ant_card(gs, screen)  # khong duoc nem exception

    def test_follow_next_cycles_through_alive_ants_and_wraps_around(self):
        """follow_next(+1/-1) phải chuyển sang con kiến CÒN SỐNG kế tiếp/
        trước đó trong cùng đàn, và quay vòng (wrap around) khi tới cuối/
        đầu danh sách, thay vì dừng lại hoặc lỗi chỉ số."""
        from antworld import hud
        import numpy as np

        gs = game_state.GameState()
        hud.build_toolbar(gs)
        _advance_past_founding(gs)
        # Ep co IT NHAT 2 con song (nanitic dau tien co the no RAI RAC
        # tung con 1, khong phai cung luc) - can >=2 de test next/prev.
        extra = 0
        while int(gs.colony.alive.sum()) < 2 and extra < 20000:
            gs.step_simulation()
            extra += 1
        alive_idx = np.where(gs.colony.alive)[0]
        gs.start_follow(gs.colony, int(alive_idx[0]))

        gs.follow_next(1)
        self.assertEqual(gs.follow_idx, int(alive_idx[1]))

        gs.follow_next(-1)
        self.assertEqual(gs.follow_idx, int(alive_idx[0]))

        # Lui 1 buoc tu con DAU TIEN -> phai quay VONG ve con CUOI CUNG
        gs.follow_next(-1)
        self.assertEqual(gs.follow_idx, int(alive_idx[-1]))

    def test_follow_next_does_nothing_when_not_following(self):
        gs = game_state.GameState()
        gs.follow_next(1)  # khong duoc crash
        self.assertFalse(gs.is_following())


if __name__ == "__main__":
    unittest.main()
