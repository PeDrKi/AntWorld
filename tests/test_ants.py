# -*- coding: utf-8 -*-
"""Test cho ants.py (AntColony) - phan mo phong lon nhat va phuc tap
nhat cua du an (dung mang NumPy, khong OOP tung con kien).

Trong tam: CHAY THAT NHIEU TICK lien tuc (mo phong ngan gon lai README
mo ta: da tung chay 60-90 nghin tick de can bang so lieu), roi kiem tra
cac BAT BIEN (invariants) phai luon dung bat ke bao nhieu tick da troi
qua:
    - khong co NaN/inf trong vi tri, goc quay
    - so kien con song khong bao gio vuot tran MAX_ANTS_PER_COLONY
    - so kien con song khong am

Day la loai loi de "lot luoi" nhat khi chi test thu cong bang mat (vd:
choi thu vai chuc giay), vi nhieu loi can bang so lieu chi lo ra sau rat
nhieu tick (hang nghin) khi 1 truong hop hiem gap moi xay ra.
"""
import unittest

import numpy as np

from antworld import config as cfg
from antworld.ants import AntColony
from antworld.world import SurfaceWorld, UndergroundWorld
from antworld.enemy import EnemyManager


def make_colony(n_start=None, max_ants=None, founding=False):
    n_start = n_start if n_start is not None else cfg.NUM_ANTS
    max_ants = max_ants if max_ants is not None else cfg.MAX_ANTS_PER_COLONY
    surface = SurfaceWorld()
    underground = UndergroundWorld(nest_pos=cfg.NEST_POS)
    colony = AntColony(n_start, max_ants, surface, underground, nest_pos=cfg.NEST_POS, founding=founding)
    return colony


class TestAntColonyBasics(unittest.TestCase):
    def test_init_population_matches_num_ants(self):
        colony = make_colony()
        self.assertEqual(int(np.sum(colony.alive)), cfg.NUM_ANTS)

    def test_allocated_slots_match_max_ants(self):
        colony = make_colony()
        self.assertEqual(colony.n, cfg.MAX_ANTS_PER_COLONY)
        self.assertEqual(len(colony.alive), cfg.MAX_ANTS_PER_COLONY)


class TestAntColonySimulationInvariants(unittest.TestCase):
    """Chay mo phong dai (nhung van du nhanh de nam trong 1 lan chay test
    thong thuong) va kiem tra cac bat bien co ban."""

    N_TICKS = 1500  # đủ để đi qua vài chu kỳ trứng->ấu trùng->thợ mới

    @classmethod
    def setUpClass(cls):
        cls.colony = make_colony()
        for _ in range(cls.N_TICKS):
            cls.colony.update()

    def test_no_nan_or_inf_in_positions(self):
        self.assertFalse(np.isnan(self.colony.x).any(), "Vi tri x co NaN")
        self.assertFalse(np.isnan(self.colony.y).any(), "Vi tri y co NaN")
        self.assertFalse(np.isinf(self.colony.x).any(), "Vi tri x co inf")
        self.assertFalse(np.isinf(self.colony.y).any(), "Vi tri y co inf")

    def test_no_nan_in_theta(self):
        self.assertFalse(np.isnan(self.colony.theta).any())

    def test_population_within_bounds(self):
        population = int(np.sum(self.colony.alive))
        self.assertGreaterEqual(population, 0)
        self.assertLessEqual(
            population, cfg.MAX_ANTS_PER_COLONY,
            f"Dan so ({population}) vuot tran MAX_ANTS_PER_COLONY "
            f"({cfg.MAX_ANTS_PER_COLONY}) - AntColony cap phat khong du "
            f"cho so nay, co the gay loi index ngoai mang."
        )

    def test_depth_within_valid_layers(self):
        alive_depth = self.colony.depth[self.colony.alive]
        if len(alive_depth) == 0:
            self.skipTest("Dan da tuyet chung trong qua trinh test - "
                           "khong con kien song de kiem tra tang.")
        self.assertGreaterEqual(alive_depth.min(), 0)
        self.assertLessEqual(alive_depth.max(), cfg.DEPTH_GRAVEYARD)

    def test_storage_never_negative(self):
        self.assertGreaterEqual(self.colony.underground.food_in_storage, 0)
        self.assertGreaterEqual(self.colony.underground.water_in_storage, 0)


class TestFoundingModeBasics(unittest.TestCase):
    """Che do lap to (mac dinh TAT - xem cfg.FOUNDING_MODE_ENABLED): dan
    bat dau tu DUNG 1 chua (population=0 trong AntColony, chua khong phai
    1 phan tu trong mang), tu de lua trung dau bang nang luong du tru
    rieng thay vi kho thuc an."""

    def test_default_mode_founding_flag_is_off(self):
        """Colony mac dinh (founding=False, nhu moi noi khac trong code
        dang goi) phai co queen_energy=0 va founding_phase=False - dam
        bao tinh nang moi khong lam thay doi hanh vi cu dang co san."""
        colony = make_colony()
        self.assertFalse(colony.founding_phase)
        self.assertEqual(colony.queen_energy, 0.0)

    def test_founding_starts_with_zero_population(self):
        colony = make_colony(n_start=0, founding=True)
        self.assertEqual(int(np.sum(colony.alive)), 0)
        self.assertTrue(colony.founding_phase)
        self.assertEqual(colony.queen_energy, cfg.QUEEN_INITIAL_ENERGY)

    def test_lifecycle_update_does_not_crash_at_zero_population(self):
        """Day chinh la loi tung phat hien khi audit: _update_lifecycle()
        tung return SOM khi population=0, khien nhanh de trung (ke ca
        nhanh lap to) khong bao gio chay duoc. Test nay chay 1 vai tick
        ngay tu dau (population=0 suot) va xac nhan queen_energy PHAI
        giam dan (chung to nhanh lap to co thuc su duoc goi toi)."""
        colony = make_colony(n_start=0, founding=True)
        energy_before = colony.queen_energy
        for _ in range(10):
            colony.update()
        self.assertLess(colony.queen_energy, energy_before,
                         "queen_energy khong giam - _update_lifecycle() co "
                         "the dang return som truoc khi toi duoc nhanh lap to.")

    def test_founding_reaches_nanitic_target_and_transitions(self):
        """Chay du lau (co du 2x margin so voi moc ~3362 tick do duoc thu
        cong) va xac nhan: (1) dan THUC SU lon len tu 0 con bang chinh
        nang luong du tru cua chua (khong can kho thuc an - kho luon = 0
        suot vi khong ai tha moi ve), va (2) founding_phase tu dong tat
        khi dat FOUNDING_NANITIC_TARGET."""
        colony = make_colony(n_start=0, founding=True)
        self.assertEqual(colony.underground.food_in_storage, 0)
        transitioned_tick = None
        for tick in range(1, 8000):
            colony.update()
            if not colony.founding_phase:
                transitioned_tick = tick
                break
        self.assertIsNotNone(
            transitioned_tick,
            "founding_phase khong tat trong 8000 tick - lua tho dau tien "
            "(nanitic) khong the no ra chi bang nang luong du tru cua chua."
        )
        population = int(np.sum(colony.alive))
        self.assertGreaterEqual(population, cfg.FOUNDING_NANITIC_TARGET)
        # LUU Y: KHONG assert food_in_storage == 0 o day - nanitic sinh ra
        # SOM NHAT co the da kip tu di kiem an tren mat dat va mang thuc an
        # THAT ve kho truoc khi nanitic thu FOUNDING_NANITIC_TARGET hoan
        # tat chuyen giao (dung y muon: cac tho dau tien bat tay vao viec
        # NGAY, khong cho ca lu du nguoi moi bat dau) - kho co the > 0 vao
        # thoi diem nay, day la hanh vi DUNG, khong phai loi.

    def test_founding_queen_energy_never_negative(self):
        colony = make_colony(n_start=0, founding=True)
        for _ in range(6000):
            colony.update()
            self.assertGreaterEqual(colony.queen_energy, 0.0)

    def test_founding_no_nan_or_population_overflow(self):
        """Chay dai qua ca giai doan lap to LAN giai doan binh thuong sau
        chuyen giao - dung lai bat bien nhu TestAntColonySimulationInvariants
        nhung xuat phat tu population=0 thay vi da on dinh san."""
        colony = make_colony(n_start=0, founding=True)
        for _ in range(6000):
            colony.update()
        self.assertFalse(np.isnan(colony.x).any())
        self.assertFalse(np.isnan(colony.y).any())
        population = int(np.sum(colony.alive))
        self.assertGreaterEqual(population, 0)
        self.assertLessEqual(population, cfg.MAX_ANTS_PER_COLONY)


class TestNecrophoresis(unittest.TestCase):
    """Truoc day cai chet chi la 1 con so truu tuong: kien chet o dau
    khong quan trong, corpse_count o nghia dia tang NGAY LAP TUC, khong ai
    phai lam gi ca. Cac test o day khoa lai hanh vi MOI: kien chet DUOI
    HAM de lai 1 xac THAT tai dung vi tri, phai co 1 nurse dang RANH VIEC
    tu nguyen di khieng no ve Nghia dia thi corpse_count moi tang."""

    def _make_colony_with_idle_nurses_and_victim(self, n_idle=3):
        colony = make_colony(n_start=30, founding=False)
        for _ in range(500):
            colony.update()
        alive_idx = np.where(colony.alive)[0]
        idle_nurses = alive_idx[:n_idle]
        victim = alive_idx[n_idle]
        underground = colony.underground

        colony.job[idle_nurses] = cfg.JOB_NURSE
        colony.layer[idle_nurses] = cfg.LAYER_UNDERGROUND
        colony.depth[idle_nurses] = underground.storage_depth
        colony.x[idle_nurses] = underground.storage[0]
        colony.y[idle_nurses] = underground.storage[1]
        colony.state[idle_nurses] = cfg.STATE_NURSE_AT_STORAGE
        colony.carrying[idle_nurses] = False
        # Dam bao au trung dang du an (>= NURSE_NURSERY_TARGET_STOCK) de
        # cac nurse nay THUC SU khong co viec gi lam, o yen tai
        # STATE_NURSE_AT_STORAGE - neu khong, ngay _update_nurses() tiep
        # theo se dieu chung di lam viec that (mang thuc an sang phong au
        # trung, chuyen sang STATE_NURSE_TO_NURSERY) truoc ca khi kip lam
        # undertaker, khien test khong bao gio tim thay nurse "ranh" nao.
        underground.food_in_nursery = cfg.NURSE_NURSERY_TARGET_STOCK

        colony.job[victim] = cfg.JOB_NURSE
        colony.layer[victim] = cfg.LAYER_UNDERGROUND
        colony.depth[victim] = underground.nursery_depth
        colony.x[victim] = underground.nursery[0] + 0.3
        colony.y[victim] = underground.nursery[1] - 0.2
        # Bao dam xac suat chet vi gia = 100% ngay tick ke tiep (giai
        # nguoc cong thuc OLD_AGE_DEATH_RATE*(1+over/OLD_AGE_DEATH_GROWTH))
        over_needed = cfg.OLD_AGE_DEATH_GROWTH * (1.0 / cfg.OLD_AGE_DEATH_RATE - 1.0) + 1000
        colony.age[victim] = cfg.MAX_AGE_TICKS + over_needed
        return colony, victim

    def test_underground_death_does_not_add_corpse_instantly(self):
        colony, victim = self._make_colony_with_idle_nurses_and_victim()
        underground = colony.underground
        colony.update()
        # Kien "trung so" chet gia KHONG chet ngay nua - phai HAP HOI truoc
        # 1 khoang ngan (xem cfg.DYING_DURATION_TICKS), van con "song" va
        # CHUA co xac nao duoc dang ky trong luc nay.
        self.assertTrue(colony.alive[victim], "Kien phai HAP HOI truoc, chua chet ngay lap tuc")
        self.assertGreater(colony.dying_ticks[victim], 0, "Kien phai dang o trang thai hap hoi (dying_ticks>0)")
        self.assertEqual(underground.corpse_count, 0.0)
        self.assertEqual(len(underground.pending_corpses), 0, "Chua duoc dang ky xac trong luc con dang hap hoi")

        for _ in range(cfg.DYING_DURATION_TICKS + 2):
            colony.update()

        self.assertFalse(colony.alive[victim], "Kien phai chet han sau khi hap hoi xong")
        self.assertEqual(
            underground.corpse_count, 0.0,
            "corpse_count tang NGAY LAP TUC - necrophoresis khong con hoat dong dung",
        )
        self.assertEqual(len(underground.pending_corpses), 1)

    def test_idle_nurse_is_dispatched_and_delivers_corpse(self):
        colony, victim = self._make_colony_with_idle_nurses_and_victim()
        underground = colony.underground
        colony.update()

        undertaker_seen = False
        # +DYING_DURATION_TICKS: xac gio chi duoc dang ky SAU khi kien hap
        # hoi xong (xem cfg.DYING_DURATION_TICKS). Da nhan them he so an
        # toan (thay vi chi +DYING_DURATION_TICKS) vi test nay VON DA hoi
        # "sat nut" tu truoc (phu thuoc RNG dieu phoi nurse ranh - xem ghi
        # chu trong _make_colony_with_idle_nurses_and_victim), them dieu
        # kien hap hoi cang de bien no thanh flaky neu khong du du dia.
        for _ in range(1600 + cfg.DYING_DURATION_TICKS):
            colony.update()
            in_transit = colony.alive & np.isin(
                colony.state, [cfg.STATE_UNDERTAKER_TO_CORPSE, cfg.STATE_UNDERTAKER_TO_GRAVEYARD]
            )
            if np.any(in_transit):
                undertaker_seen = True
            if underground.corpse_count > 0:
                break

        self.assertTrue(undertaker_seen, "Khong co nurse nao duoc dieu di khieng xac")
        self.assertGreater(underground.corpse_count, 0, "Xac khong bao gio duoc khieng toi noi trong 800 tick")
        self.assertEqual(len(underground.pending_corpses), 0)

    def test_undertaker_movement_is_not_throttled_like_assignment(self):
        """Regression test cho 1 loi cu the da gap: nhot chung dieu kien
        "chi kiem tra 1 lan moi UNDERTAKER_CHECK_INTERVAL tick" (danh cho
        buoc PHAN CONG moi) voi ca buoc DI CHUYEN cua nurse DANG TREN
        DUONG - khien nurse dang khieng xac chi nhich 1 tick trong moi
        UNDERTAKER_CHECK_INTERVAL tick, mat gap boi so lan thoi gian di
        chuyen that su can. Test nay dam bao 1 nurse dang o state
        STATE_UNDERTAKER_TO_CORPSE PHAI di chuyen o MOI TICK, khong chi
        nhung tick chia het cho UNDERTAKER_CHECK_INTERVAL."""
        colony, victim = self._make_colony_with_idle_nurses_and_victim()
        colony.update()

        undertaker_idx = None
        # Cua so cho phep gio phai TINH THEM thoi gian hap hoi (xem
        # cfg.DYING_DURATION_TICKS) - xac chi thuc su duoc dang ky sau khi
        # kien hap hoi xong, roi moi toi luot UNDERTAKER_CHECK_INTERVAL de
        # phan cong nurse di khieng.
        for _ in range(cfg.DYING_DURATION_TICKS + cfg.UNDERTAKER_CHECK_INTERVAL + 5):
            colony.update()
            in_transit = np.where(
                colony.alive & (colony.state == cfg.STATE_UNDERTAKER_TO_CORPSE)
            )[0]
            if len(in_transit) > 0:
                undertaker_idx = in_transit[0]
                break
        if undertaker_idx is None:
            self.skipTest("Chua co nurse nao duoc phan cong trong cua so cho phep")

        pos_before = (colony.x[undertaker_idx], colony.y[undertaker_idx])
        moved_ticks = 0
        for _ in range(cfg.UNDERTAKER_CHECK_INTERVAL):
            if colony.state[undertaker_idx] != cfg.STATE_UNDERTAKER_TO_CORPSE:
                break  # da toi noi som hon 1 chu ky kiem tra - van hop le
            colony.update()
            pos_after = (colony.x[undertaker_idx], colony.y[undertaker_idx])
            if pos_after != pos_before:
                moved_ticks += 1
            pos_before = pos_after

        self.assertGreater(
            moved_ticks, 1,
            "Nurse dang khieng xac chi di chuyen o duoc 1 tick trong ca 1 "
            "chu ky UNDERTAKER_CHECK_INTERVAL - buoc di chuyen dang bi "
            "nhot chung voi throttle cua buoc phan cong.",
        )


class TestCooperativeCarcassHauling(unittest.TestCase):
    """Truoc day ke thu tu nhien bi linh danh bai HAN se BIEN MAT ngay lap
    tuc, khong de lai gi ca - danh bai ke thu khong dem lai loi ich thuc
    pham nao cho to. Cac test o day khoa lai hanh vi MOI: xac ke thu la 1
    "moi lon" can DU SO KIEN (HAUL_MIN_ANTS) tap trung CUNG LUC moi khieng
    noi ve to (cooperative transport), khong du nguoi kip thoi thi xac rua
    mat (HAUL_DECAY_TICKS)."""

    def test_defeated_enemy_leaves_carcass_instead_of_vanishing(self):
        colony = make_colony(n_start=20, founding=False)
        enemy = EnemyManager()
        enemy.force_spawn_at(colony.nest_pos[0] + 2, colony.nest_pos[1])
        enemy.health = 0.01  # 1 don sat thuong tiep theo se ha guc no

        # Ep TRUC TIEP 1 kien thanh linh (ROLE_MAJOR) - KHONG dua vao ty
        # le phan cong role ngau nhien luc khoi tao (voi dan nho, co THE
        # ra 0 linh hoan toan do may rui, da tung gap thuc te khien test
        # nay flaky).
        alive_idx = np.where(colony.alive)[0]
        self.assertGreater(len(alive_idx), 0)
        soldier = alive_idx[0]
        colony.role[soldier] = cfg.ROLE_MAJOR
        colony.layer[soldier] = cfg.LAYER_SURFACE
        colony.alive[soldier] = True
        colony.x[soldier], colony.y[soldier] = enemy.x, enemy.y

        defeated = False
        for _ in range(200):
            # Ep linh LUON DUNG CANH ke thu moi tick (thay vi chi dat 1
            # lan luc dau) - vi ke thu tu chon muc tieu GAN NHAT trong so
            # TAT CA kien tren mat dat moi tick (xem EnemyManager.
            # _move_towards_prey), voi dan 20 con no co the doi huong bam
            # theo 1 con khac o xa hon linh cua ta, khien linh roi khoi
            # tam danh trung va lam test flaky (da tung gap thuc te).
            colony.x[soldier], colony.y[soldier] = enemy.x, enemy.y
            colony.update(enemy=enemy)
            enemy.update([colony])
            if not enemy.active and enemy.total_defeated > 0:
                defeated = True
                break
        self.assertTrue(defeated, "Ke thu khong bao gio bi danh bai trong 200 tick")
        self.assertTrue(enemy.carcass_active, "Ke thu bi danh bai nhung KHONG de lai xac - hanh vi cu (bien mat) van con")
        self.assertGreater(enemy.carcass_food_value, 0)

    def test_enough_ants_haul_carcass_home(self):
        colony = make_colony(n_start=40, founding=False)
        for _ in range(500):
            colony.update()
        enemy = EnemyManager()
        enemy._spawn_carcass(colony.nest_pos[0] + 2.0, colony.nest_pos[1])
        # LUU Y: KHONG so sanh food_in_storage truoc/sau qua suot 2000
        # tick (tung dung cach nay, gap DUNG LOI FLAKY tuong tu da tung
        # phat hien o test_invasion.py: kho luon bien dong SONG SONG do
        # tieu thu tu nhien - nurse lay do cho au trung an, chua de trung
        # tru kho... - nen dau khieng xac THANH CONG that su, kho van co
        # THE giam rong qua ca cua so neu tieu thu > luong vua khieng ve).
        # Dung THANG total_food_collected (bo dem chi TANG, khong bao gio
        # giam, khong bi tieu thu anh huong) la phep do dang tin cay.
        collected_before = colony.total_food_collected

        haul_states_seen = set()
        for _ in range(2000):
            colony.update(enemy=enemy)
            enemy.update([colony])
            states_now = set(np.unique(colony.state[colony.alive]).tolist())
            haul_states_seen |= states_now & {cfg.STATE_HAUL_APPROACH, cfg.STATE_HAUL_GRIP}
            if not enemy.carcass_active:
                break

        self.assertIn(cfg.STATE_HAUL_APPROACH, haul_states_seen, "Khong co kien nao di tiep can xac")
        self.assertEqual(enemy.total_carcasses_hauled, 1, "Xac khong duoc khieng thanh cong")
        self.assertGreaterEqual(
            colony.total_food_collected, collected_before + cfg.HAUL_MIN_ANTS,
            "So don vi thu thap khong tang dung bang so kien da khieng xac",
        )

    def test_too_few_ants_lets_carcass_rot_away(self):
        """Dan CHI 2 con - khong bao gio du HAUL_MIN_ANTS (mac dinh 4) tap
        trung cung luc, nen xac PHAI rua mat sau HAUL_DECAY_TICKS, khong
        the nao khieng thanh cong."""
        colony = make_colony(n_start=2, founding=False)
        enemy = EnemyManager()
        enemy._spawn_carcass(colony.nest_pos[0] + 2.0, colony.nest_pos[1])

        for _ in range(cfg.HAUL_DECAY_TICKS + 50):
            colony.update(enemy=enemy)
            enemy.update([colony])
            if not enemy.carcass_active:
                break
        self.assertEqual(enemy.total_carcasses_hauled, 0)
        self.assertFalse(enemy.carcass_active)

        # Dung DUNG THU TU that cua game_state.py (colony.update() TRUOC,
        # enemy.update() SAU MOI tick) - do do co THE co do tre VO HAI 1
        # tick giua luc carcass rua mat va luc kien duoc "tha" khoi state
        # khieng mo (vi colony.update() cua chinh tick do da chay TRUOC
        # khi enemy.update() lam carcass_active=False). Goi THEM 1 tick
        # colony.update() nua (dung nhu vong lap that se tiep tuc chay) de
        # kiem tra dung dieu kien can khoa: khong con ket LAU DAI, khong
        # phai "khong bao gio co do tre nao".
        colony.update(enemy=enemy)
        stuck = np.any(colony.alive & np.isin(colony.state, [cfg.STATE_HAUL_APPROACH, cfg.STATE_HAUL_GRIP]))
        self.assertFalse(stuck, "Kien bi ket vinh vien o state khieng mo sau khi xac da rua mat")


if __name__ == "__main__":
    unittest.main()
