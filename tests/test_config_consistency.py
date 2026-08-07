# -*- coding: utf-8 -*-
"""
Kiem tra config.py TU NHAT QUAN (khong mau thuan noi bo), va - quan trong
hon - kiem tra README.md khong "noi khac" voi config.py that.

Ly do co file nay: du an tung bi README ghi "khoi tao 20 con, toi da 1000
con" trong khi config.py thuc te la NUM_ANTS=10, MAX_ANTS_PER_COLONY=200.
Loai loi nay (tai lieu troi noi khoi code that) rat de tai dien moi lan co
ai do doi 1 hang so ma quen luot lai README - nen thay vi chi sua 1 lan,
ta viet test tu dong doc ca 2 nguon va SO SANH, de lan sau neu lech nua
thi test se do (thay vi phai ai do doc ky tay moi phat hien ra).
"""
import os
import re
import unittest

from antworld import config as cfg

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(PROJECT_ROOT, "README.md")


class TestConfigInternalConsistency(unittest.TestCase):
    """Cac hang so trong config.py phai tu logic voi nhau."""

    def test_num_ants_not_over_max(self):
        self.assertLessEqual(
            cfg.NUM_ANTS, cfg.MAX_ANTS_PER_COLONY,
            "NUM_ANTS (so kien khoi tao) khong duoc lon hon "
            "MAX_ANTS_PER_COLONY (tran dan so) - neu khong AntColony se "
            "cap phat mang qua nho so voi so kien khoi tao that."
        )

    def test_grid_size_positive_and_reasonable(self):
        self.assertGreater(cfg.GRID_SIZE, 0)
        # gioi han tren chi de bat loi go nham so 0, khong phai luat cung
        self.assertLess(cfg.GRID_SIZE, 100_000)

    def test_depth_layers_are_distinct(self):
        depths = [
            cfg.DEPTH_QUEEN, cfg.DEPTH_GRAVEYARD,
        ]
        self.assertEqual(len(depths), len(set(depths)),
                          "Cac hang so DEPTH_* dang bi trung gia tri.")


class TestReadmeMatchesConfig(unittest.TestCase):
    """README.md mo ta so lieu dan so - phai KHOP voi config.py that,
    khong duoc la so lieu cu con sot lai tu ban truoc."""

    @classmethod
    def setUpClass(cls):
        with open(README_PATH, encoding="utf-8") as f:
            cls.readme_text = f.read()

    def test_readme_mentions_correct_starting_population(self):
        # Tim cau dang: "khoi tao **10 con**"
        m = re.search(r"khởi tạo \*\*(\d+) con\*\*", self.readme_text)
        self.assertIsNotNone(
            m, "Khong tim thay cau 'khoi tao **N con**' trong README.md - "
               "co the cau chu da doi cach viet, can cap nhat lai regex "
               "trong test nay cho khop."
        )
        readme_value = int(m.group(1))
        self.assertEqual(
            readme_value, cfg.NUM_ANTS,
            f"README.md dang ghi 'khoi tao {readme_value} con' nhung "
            f"config.py thuc te la NUM_ANTS={cfg.NUM_ANTS}. Sua 1 trong 2 "
            f"cho khop (uu tien sua README de mo ta dung hanh vi that)."
        )

    def test_readme_mentions_correct_max_population(self):
        # Tim cau dang: "toi da 200\n  con" (co the xuong dong giua so va "con")
        m = re.search(r"tối đa (\d+)\s*\n?\s*con", self.readme_text)
        self.assertIsNotNone(
            m, "Khong tim thay cau 'toi da N con' trong README.md - co "
               "the cau chu da doi cach viet, can cap nhat lai regex "
               "trong test nay cho khop."
        )
        readme_value = int(m.group(1))
        self.assertEqual(
            readme_value, cfg.MAX_ANTS_PER_COLONY,
            f"README.md dang ghi 'toi da {readme_value} con' nhung "
            f"config.py thuc te la MAX_ANTS_PER_COLONY={cfg.MAX_ANTS_PER_COLONY}. "
            f"Sua 1 trong 2 cho khop (uu tien sua README de mo ta dung "
            f"hanh vi that)."
        )

    def test_readme_chua_nho_toi_da_khop_max(self):
        # Cau "chi no duoc neu dan CHUA cham tran N con" cung phai khop
        m = re.search(r"chạm trần (\d+) con", self.readme_text)
        if m is None:
            self.skipTest("README khong con cau 'cham tran N con' - bo qua.")
        readme_value = int(m.group(1))
        self.assertEqual(readme_value, cfg.MAX_ANTS_PER_COLONY)


if __name__ == "__main__":
    unittest.main()
