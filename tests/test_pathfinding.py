# -*- coding: utf-8 -*-
"""Test cho pathfinding.py (VisibilityPathfinder - any-angle A* trên
visibility graph).

Đây là module RỦI RO CAO NHẤT trong toàn bộ phần tìm đường: 2 lỗi hình
học tinh vi (rò rỉ qua khe nối giữa 2 ô vật cản liền kề/sát biên bản đồ,
và lỗi `numpy.bool_ + numpy.bool_` trả về phép OR thay vì cộng số nguyên
khiến cơ chế phát hiện "điểm kẹp chéo" chưa từng chạy đúng) từng ẩn náu
trong đây và CHỈ được phát hiện qua kiểm thử thủ công tạm thời, không
phải bộ test tự động - file này bổ sung lại các phép kiểm tra đó thành
regression test thật sự, để nếu ai vô tình tái tạo lỗi tương tự, bộ test
sẽ báo đỏ ngay thay vì phải phát hiện bằng mắt.

LƯU Ý QUAN TRỌNG khi viết test mới cho module này: VisibilityPathfinder
dùng THẲNG hằng số cfg.GRID_SIZE (không đọc surface.terrain.shape) để xử
lý biên bản đồ - mọi surface giả lập dùng trong test PHẢI có
terrain.shape == (cfg.GRID_SIZE, cfg.GRID_SIZE) đúng kích thước thật,
nếu không sẽ lỗi ngay ở bước đệm biên (_extract_vertices).
"""
import unittest

import numpy as np

from antworld import config as cfg
from antworld.pathfinding import VisibilityPathfinder
from antworld.world import SurfaceWorld

N = cfg.GRID_SIZE


class _FakeSurface:
    """Vỏ bọc tối giản - chỉ cần đúng 2 thuộc tính mà VisibilityPathfinder
    đọc tới (terrain, terrain_version) - cho phép dựng bản đồ TÙY Ý, xác
    định trước, không phụ thuộc gì vào SurfaceWorld thật (không ngẫu
    nhiên, không sinh vật cản mặc định)."""
    __slots__ = ("terrain", "terrain_version")


def _make_surface(blocked):
    """blocked: mảng bool (GRID_SIZE, GRID_SIZE). Trả về (surface, pathfinder)."""
    assert blocked.shape == (N, N), "terrain giả lập phải đúng (GRID_SIZE, GRID_SIZE)"
    surf = _FakeSurface()
    surf.terrain = np.where(blocked, cfg.TERRAIN_ROCK, cfg.TERRAIN_EMPTY).astype(np.int8)
    surf.terrain_version = 1
    return surf, VisibilityPathfinder(surf)


def _blank(n=N):
    return np.zeros((n, n), dtype=bool)


def _path_has_collision(blocked, path, samples=200, eps=1e-3):
    """Kiểm chứng ĐỘC LẬP (không dùng lại VisibilityPathfinder) xem đường
    đi có thực sự xuyên vật cản hay không. Lấy mẫu dày trên từng đoạn, và
    với MỖI điểm mẫu, "rung" nhẹ theo phương VUÔNG GÓC với đoạn thẳng sang
    CẢ 2 phía: nếu CẢ 2 phía đều là ô vật cản thì điểm đó chắc chắn nằm
    kẹp giữa 2 khối đặc (va chạm thật); nếu chỉ 1 phía đặc còn phía kia
    trống thì đó là đi SÁT MẶT NGOÀI 1 vật cản (hợp lệ). Cách làm ngây thơ
    (chỉ floor(x),floor(y) rồi loại biên) SAI với đoạn đúng trục (dx=0
    hoặc dy=0) vì mọi điểm mẫu trên đó đều "nằm trên biên" theo 1 trục -
    đây chính là cái bẫy đã gặp phải khi viết thực nghiệm kiểm chứng thủ
    công lần đầu."""
    n = blocked.shape[0]

    def blocked_at(x, y):
        xi = min(max(int(np.floor(x)), 0), n - 1)
        yi = min(max(int(np.floor(y)), 0), n - 1)
        return bool(blocked[xi, yi])

    for i in range(len(path) - 1):
        a = np.array(path[i], dtype=float)
        b = np.array(path[i + 1], dtype=float)
        d = b - a
        length = float(np.hypot(*d))
        if length < 1e-9:
            continue
        perp = np.array([-d[1], d[0]]) / length
        for t in np.linspace(0.001, 0.999, samples):
            pt = a + t * d
            side1 = blocked_at(pt[0] + eps * perp[0], pt[1] + eps * perp[1])
            side2 = blocked_at(pt[0] - eps * perp[0], pt[1] - eps * perp[1])
            if side1 and side2:
                return True
    return False


class TestBasicVisibility(unittest.TestCase):
    def test_direct_line_when_no_obstacle(self):
        _, pf = _make_surface(_blank())
        path = pf.find_path((1, 1), (10, 10))
        self.assertEqual(path, [(10.0, 10.0)])

    def test_line_of_sight_blocked_by_single_obstacle(self):
        blocked = _blank()
        blocked[5, 5] = True
        _, pf = _make_surface(blocked)
        self.assertFalse(pf.line_of_sight((4.5, 5.5), (5.5, 5.5)))

    def test_line_of_sight_true_when_grazing_isolated_corner(self):
        # 1 vật cản CÔ LẬP - tia đi CHẠM ĐÚNG 1 góc của nó (không cắt vào
        # nội thất) vẫn phải được coi là "nhìn thấy" (không bị chặn) - đây
        # chính là lý do các góc vật cản được dùng làm đỉnh của visibility
        # graph (mục II bài báo FA-A*): đường đi tối ưu ĐƯỢC PHÉP chạm sát
        # góc vật cản. Ô (10,10) chiếm x:[10,11) y:[10,11); đường chéo từ
        # (9,11) tới (11,9) đi ĐÚNG qua điểm góc (10,10) mà không hề cắt
        # vào phần diện tích nào khác của ô - khác với đường chéo (9,9)->
        # (11,11) vốn xuyên thẳng qua GIỮA ô (bị chặn thật, xem test dưới).
        blocked = _blank()
        blocked[10, 10] = True
        _, pf = _make_surface(blocked)
        self.assertTrue(pf.line_of_sight((9.0, 11.0), (11.0, 9.0)))

    def test_line_of_sight_false_when_diagonal_cuts_through_cell_interior(self):
        # Đối chứng với test grazing ở trên: đường chéo (9,9)->(11,11) đi
        # xuyên qua ĐÚNG GIỮA ô (10,10) (không phải chỉ chạm góc) - PHẢI
        # bị chặn.
        blocked = _blank()
        blocked[10, 10] = True
        _, pf = _make_surface(blocked)
        self.assertFalse(pf.line_of_sight((9.0, 9.0), (11.0, 11.0)))


class TestSeamLeakRegression(unittest.TestCase):
    """Regression test cho lỗi "rò rỉ qua khe nối": 1 tia đi CHÍNH XÁC dọc
    theo đường ranh giới chung giữa 2 ô vật cản LIỀN KỀ (hoặc giữa 1 ô vật
    cản và BIÊN bản đồ) không được coi là "nhìn thấy nhau". Trước khi vá,
    phép kiểm tra slab-test từng ô riêng lẻ bỏ sót trường hợp này vì tia
    không cắt vào NỘI THẤT MỞ của ô nào cả (nó luôn nằm đúng trên biên của
    cả hai)."""

    def test_vertical_ray_along_shared_edge_of_two_blocked_cells_is_blocked(self):
        blocked = _blank()
        blocked[7, 8] = True
        blocked[8, 8] = True  # 2 ô liền kề THEO TRỤC X, cùng bị chặn
        _, pf = _make_surface(blocked)
        # đoạn thẳng dọc theo x=8, từ y=8 tới y=9 - đúng đường ranh giới
        # chung giữa 2 ô trên, PHẢI bị chặn (nằm kẹp giữa 2 khối đặc)
        self.assertFalse(pf.line_of_sight((8.0, 8.0), (8.0, 9.0)))

    def test_horizontal_ray_along_shared_edge_is_blocked(self):
        blocked = _blank()
        blocked[8, 7] = True
        blocked[8, 8] = True  # 2 ô liền kề THEO TRỤC Y
        _, pf = _make_surface(blocked)
        self.assertFalse(pf.line_of_sight((8.0, 8.0), (9.0, 8.0)))

    def test_ray_along_single_face_of_isolated_wall_is_still_visible(self):
        # Đối chứng: CHỈ 1 bên là vật cản, bên kia trống - phải HỢP LỆ
        # (kiến đi sát mặt ngoài 1 vật cản được, không phải "kẹp"). Nếu vá
        # lỗi khe nối theo kiểu "quá tay" (chặn luôn cả trường hợp này) sẽ
        # làm hỏng khả năng đi sát rìa vật cản bình thường.
        blocked = _blank()
        blocked[8, 8] = True  # CHỈ 1 ô, không có ô liền kề nào khác
        _, pf = _make_surface(blocked)
        self.assertTrue(pf.line_of_sight((8.0, 8.0), (8.0, 9.0)))

    def test_obstacle_adjacent_to_map_boundary_seam_is_blocked(self):
        # Vật cản nằm SÁT BIÊN bản đồ cũng tạo "khe nối" với chính biên đó
        # (biên cũng được coi là đặc - kiến không đi ra ngoài bản đồ).
        blocked = _blank()
        blocked[8, 0] = True  # sát biên dưới (y=0)
        _, pf = _make_surface(blocked)
        self.assertFalse(pf.line_of_sight((8.0, 0.0), (9.0, 0.0)))

    def test_l_shaped_wall_forces_detour_not_shortcut_through_seam(self):
        """Tái hiện đúng trường hợp phát hiện thủ công ban đầu: tường hình
        chữ L, trước khi vá đường đi "trượt" qua đúng khe nối và xuyên
        tường; sau khi vá phải đi vòng qua đầu tường."""
        blocked = _blank()
        blocked[5:15, 8] = True
        blocked[14, 8:15] = True
        _, pf = _make_surface(blocked)
        path = pf.find_path((2.0, 2.0), (18.0, 18.0))
        self.assertIsNotNone(path)
        full = [(2.0, 2.0)] + path
        self.assertFalse(_path_has_collision(blocked, full))


class TestPinchPointRegression(unittest.TestCase):
    """Regression test cho lỗi `numpy.bool_ + numpy.bool_` trả về phép OR
    logic thay vì cộng số nguyên trong _extract_vertices() - khiến điều
    kiện "cnt == 2 và kẹp chéo" không bao giờ đúng, và điều kiện "cnt == 4"
    (bị vây kín hoàn toàn) cũng không bao giờ đúng."""

    def test_diagonal_pinch_blocks_cut_through(self):
        blocked = _blank()
        # (5,5) và (6,6) chéo nhau bị chặn; (6,5) và (5,6) trống -> kẹp chéo
        blocked[5, 5] = True
        blocked[6, 6] = True
        _, pf = _make_surface(blocked)
        self.assertFalse(pf.line_of_sight((5.0, 6.0), (6.0, 5.0)))

    def test_pinch_point_excluded_from_vertex_list(self):
        blocked = _blank()
        blocked[5, 5] = True
        blocked[6, 6] = True
        _, pf = _make_surface(blocked)
        pf._rebuild_vertices_if_needed()
        pinch = np.array([6.0, 6.0])  # tọa độ góc kẹp - KHÔNG được là đỉnh
        for v in pf._vertices:
            self.assertFalse(np.allclose(v, pinch))

    def test_fully_enclosed_corner_not_added_as_vertex(self):
        # 1 o hoan toan bi vay kin boi 4 o vat can (khong co huong nao
        # thoat) - goc giua chung KHONG duoc coi la dinh huu ich (cnt==4
        # phai bi loai dung).
        blocked = _blank()
        blocked[5, 5] = blocked[6, 5] = blocked[5, 6] = blocked[6, 6] = True
        _, pf = _make_surface(blocked)
        pf._rebuild_vertices_if_needed()
        center = np.array([6.0, 6.0])
        matches = [v for v in pf._vertices if np.allclose(v, center)]
        self.assertEqual(len(matches), 0)


class TestPathCorrectness(unittest.TestCase):
    def test_no_path_when_fully_enclosed(self):
        blocked = _blank()
        blocked[3:7, 3] = True
        blocked[3:7, 6] = True
        blocked[3, 3:7] = True
        blocked[6, 3:7] = True
        _, pf = _make_surface(blocked)
        path = pf.find_path((1.0, 1.0), (4.5, 4.5))
        self.assertIsNone(path)

    def test_random_maps_never_produce_colliding_path(self):
        """Kiểm chứng thống kê: trên nhiều bản đồ và cặp truy vấn ngẫu
        nhiên, KHÔNG có đường đi nào thực sự xuyên vật cản - đây chính là
        cách đã phát hiện ra cả 2 lỗi thật ở trên trước khi có test này."""
        rng = np.random.default_rng(0)
        tested = 0
        for _ in range(6):
            blocked = rng.random((N, N)) < 0.1
            blocked[0:3, 0:3] = False
            blocked[N - 3:N, N - 3:N] = False
            _, pf = _make_surface(blocked)
            free = np.argwhere(~blocked)
            idxs = rng.integers(0, len(free), size=(8, 2))
            for i, j in idxs:
                s = tuple(free[i].astype(float) + 0.5)
                t = tuple(free[j].astype(float) + 0.5)
                path = pf.find_path(s, t)
                if path is None:
                    continue
                tested += 1
                full = [s] + path
                self.assertFalse(
                    _path_has_collision(blocked, full),
                    f"duong di xuyen vat can: {s} -> {t}: {full}",
                )
        self.assertGreater(tested, 0, "khong truy van nao thanh cong - test khong co y nghia")

    def test_path_is_never_longer_than_a_naive_direct_line_would_suggest_is_impossible(self):
        # Kiem tra "khong am" don gian: do dai duong di tra ve phai >=
        # khoang cach duong chim bay (bat dang thuc tam giac) - bat loi
        # cong don khoang cach sai (vd cong nham 1 diem 2 lan).
        blocked = _blank()
        blocked[5:15, 8] = True
        blocked[14, 8:15] = True
        _, pf = _make_surface(blocked)
        start = (2.0, 2.0)
        path = pf.find_path(start, (18.0, 18.0))
        pts = [start] + path
        total = sum(
            np.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)
        )
        straight = np.hypot(18.0 - 2.0, 18.0 - 2.0)
        self.assertGreaterEqual(total + 1e-6, straight)


class TestCaching(unittest.TestCase):
    def test_terrain_version_change_triggers_rebuild(self):
        blocked = _blank()
        surf, pf = _make_surface(blocked)
        path = pf.find_path((1.0, 1.0), (18.0, 18.0))
        self.assertEqual(path, [(18.0, 18.0)])  # đường thẳng, chưa có vật cản

        # thêm 1 bức tường chắn đường thẳng NHƯNG chừa 1 khe hở ở 1 đầu để
        # vẫn còn đường vòng đi được (nếu chắn kín HẾT bề rộng bản đồ thì
        # đúng ra find_path phải trả về None - xem test_no_path_when_...)
        blocked[0:35, 9] = True
        surf.terrain = np.where(blocked, cfg.TERRAIN_ROCK, cfg.TERRAIN_EMPTY).astype(np.int8)
        surf.terrain_version += 1
        path2 = pf.find_path((1.0, 1.0), (18.0, 18.0))
        self.assertIsNotNone(path2)
        self.assertNotEqual(path2, [(18.0, 18.0)])  # phải đi vòng, không còn là đường thẳng

    def test_no_rebuild_when_terrain_version_unchanged(self):
        """Không cần đúng logic nội bộ, chỉ cần quan sát được từ bên
        ngoài: gọi find_path 2 lần liên tiếp không đổi địa hình phải cho
        CÙNG kết quả và không lỗi (cache không bị hỏng qua nhiều lần gọi)."""
        blocked = _blank()
        blocked[5, 5] = True
        _, pf = _make_surface(blocked)
        p1 = pf.find_path((1.0, 1.0), (18.0, 18.0))
        p2 = pf.find_path((1.0, 1.0), (18.0, 18.0))
        self.assertEqual(p1, p2)


class TestOnRealSurfaceWorld(unittest.TestCase):
    """Kiểm tra trên SurfaceWorld THẬT (không phải fake) - đảm bảo
    VisibilityPathfinder hoạt động đúng với dữ liệu do world.py sinh ra
    thật sự (địa hình mặc định lúc khởi tạo, kiểu tường đá "con rắn" dài
    ngoằn ngoèo), không chỉ với dữ liệu tối giản trong các test ở trên."""

    def test_default_world_terrain_path_never_collides(self):
        world = SurfaceWorld()
        blocked = world.terrain != cfg.TERRAIN_EMPTY
        pf = VisibilityPathfinder(world)
        free = np.argwhere(~blocked)
        if len(free) < 2:
            self.skipTest("khong du o trong tren ban do mac dinh")
        rng = np.random.default_rng(1)
        idxs = rng.integers(0, len(free), size=(15, 2))
        tested = 0
        for i, j in idxs:
            s = tuple(free[i].astype(float) + 0.5)
            t = tuple(free[j].astype(float) + 0.5)
            path = pf.find_path(s, t)
            if path is None:
                continue
            tested += 1
            full = [s] + path
            self.assertFalse(_path_has_collision(blocked, full))
        self.assertGreater(tested, 0)


if __name__ == "__main__":
    unittest.main()
