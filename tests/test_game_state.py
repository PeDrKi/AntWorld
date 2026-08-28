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


class TestGameStateSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.gs = game_state.GameState()

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
        self.assertGreater(int(gs.colony.alive.sum()), 0)

        # Chay tiep vai tick sau restart phai on, khong loi
        for _ in range(20):
            gs.step_simulation()
            gs.check_alerts()


if __name__ == "__main__":
    unittest.main()
