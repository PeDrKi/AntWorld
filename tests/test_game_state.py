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

import game_state


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


if __name__ == "__main__":
    unittest.main()
