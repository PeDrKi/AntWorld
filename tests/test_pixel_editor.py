# -*- coding: utf-8 -*-
"""Test cho pixel_editor.py - chu yeu la logic AppState (khong dung QUA
nhieu vao viec ve UI tung frame, vi phan do chu can chay-khong-crash la
du, da kiem bang tay/bang mat khi phat trien)."""
import unittest

import pixel_editor as pe  # tools/pixel_editor.py (them vao sys.path boi conftest.py / run_tests.py)


def fresh_state():
    """Tao 1 AppState moi tinh, khong dung chung voi module-level `state`
    (tranh test nay lam ban test khac vi state.sprites la global)."""
    st = pe.AppState()
    st.new_sprite("test_sprite", 8, "Test")
    st.current = "test_sprite"
    return st


class TestPixelDrawing(unittest.TestCase):
    def test_set_pixel_basic(self):
        st = fresh_state()
        st.set_pixel(2, 3, "#ff0000")
        self.assertEqual(st.sp().pixels[3 * 8 + 2], "#ff0000")

    def test_set_pixel_to_none_erases(self):
        st = fresh_state()
        st.set_pixel(1, 1, "#ff0000")
        st.set_pixel(1, 1, None)
        self.assertIsNone(st.sp().pixels[1 * 8 + 1])


class TestSymmetry(unittest.TestCase):
    def test_horizontal_symmetry_mirrors_x(self):
        st = fresh_state()
        st.symmetry_h = True
        st.set_pixel(2, 3, "#00ff00")
        size = st.sp().size
        mirrored = {(2, 3), (size - 1 - 2, 3)}
        painted = {(x, y) for y in range(size) for x in range(size)
                   if st.sp().pixels[y * size + x] == "#00ff00"}
        self.assertEqual(painted, mirrored)

    def test_both_symmetries_mirror_4_ways(self):
        st = fresh_state()
        st.symmetry_h = True
        st.symmetry_v = True
        st.set_pixel(2, 3, "#0000ff")
        size = st.sp().size
        expected = {
            (2, 3), (size - 1 - 2, 3),
            (2, size - 1 - 3), (size - 1 - 2, size - 1 - 3),
        }
        painted = {(x, y) for y in range(size) for x in range(size)
                   if st.sp().pixels[y * size + x] == "#0000ff"}
        self.assertEqual(painted, expected)

    def test_no_symmetry_paints_single_pixel_only(self):
        st = fresh_state()
        st.set_pixel(2, 3, "#ffffff")
        size = st.sp().size
        painted = {(x, y) for y in range(size) for x in range(size)
                   if st.sp().pixels[y * size + x] == "#ffffff"}
        self.assertEqual(painted, {(2, 3)})


class TestFloodFill(unittest.TestCase):
    def test_flood_fill_whole_empty_canvas(self):
        st = fresh_state()
        st.flood_fill(0, 0, "#123456")
        size = st.sp().size
        self.assertTrue(all(c == "#123456" for c in st.sp().pixels))

    def test_flood_fill_respects_boundary(self):
        st = fresh_state()
        size = st.sp().size
        # ve 1 cot doc lam "tuong chan" giua canvas
        for y in range(size):
            st.set_pixel(4, y, "#000000")
        st.flood_fill(0, 0, "#ff00ff")
        left_side_filled = all(
            st.sp().pixels[y * size + x] == "#ff00ff"
            for y in range(size) for x in range(4)
        )
        right_side_untouched = all(
            st.sp().pixels[y * size + x] is None
            for y in range(size) for x in range(5, size)
        )
        self.assertTrue(left_side_filled)
        self.assertTrue(right_side_untouched)


class TestUndoRedo(unittest.TestCase):
    def test_undo_reverts_last_change(self):
        st = fresh_state()
        st.push_history()
        st.set_pixel(0, 0, "#aaaaaa")
        st.undo()
        self.assertIsNone(st.sp().pixels[0])

    def test_redo_reapplies_undone_change(self):
        st = fresh_state()
        st.push_history()
        st.set_pixel(0, 0, "#aaaaaa")
        st.undo()
        st.redo()
        self.assertEqual(st.sp().pixels[0], "#aaaaaa")

    def test_undo_on_empty_history_does_not_crash(self):
        st = fresh_state()
        st.undo()  # khong co gi de undo - khong duoc crash
        self.assertTrue(all(c is None for c in st.sp().pixels))


class TestSpriteManagement(unittest.TestCase):
    def test_new_sprite_avoids_name_collision(self):
        st = fresh_state()
        name2 = st.new_sprite("test_sprite", 8, "Trung ten")
        self.assertNotEqual(name2, "test_sprite")
        self.assertIn(name2, st.sprites)


class TestHexColorHelpers(unittest.TestCase):
    def test_hex_to_rgb(self):
        self.assertEqual(pe.hex_to_rgb("#ff0000"), (255, 0, 0))
        self.assertEqual(pe.hex_to_rgb("00ff00"), (0, 255, 0))

    def test_hex_to_rgba(self):
        self.assertEqual(pe.hex_to_rgba("#0000ff", 128), (0, 0, 255, 128))


class TestBrushSize(unittest.TestCase):
    def test_brush_size_1_paints_single_cell(self):
        st = fresh_state()
        st.brush_size = 1
        st.paint_stamp(3, 3, "#ffffff")
        painted = sum(1 for c in st.sp().pixels if c == "#ffffff")
        self.assertEqual(painted, 1)

    def test_brush_size_3_paints_3x3_block(self):
        st = fresh_state()
        st.brush_size = 3
        st.paint_stamp(3, 3, "#ffffff")
        painted = sum(1 for c in st.sp().pixels if c == "#ffffff")
        self.assertEqual(painted, 9)

    def test_brush_size_clips_at_canvas_edge(self):
        st = fresh_state()
        st.brush_size = 3
        st.paint_stamp(0, 0, "#ffffff")  # o goc - 1 phan con dau ra ngoai bien
        painted = sum(1 for c in st.sp().pixels if c == "#ffffff")
        self.assertEqual(painted, 4)  # chi con 2x2 lot vao trong canvas


class TestLineAndRectTools(unittest.TestCase):
    def test_line_points_diagonal(self):
        st = fresh_state()
        pts = st.line_points(0, 0, 3, 3)
        self.assertEqual(pts, [(0, 0), (1, 1), (2, 2), (3, 3)])

    def test_line_points_horizontal(self):
        st = fresh_state()
        pts = st.line_points(0, 0, 4, 0)
        self.assertEqual(pts, [(x, 0) for x in range(5)])

    def test_line_points_single_point_when_same_cell(self):
        st = fresh_state()
        pts = st.line_points(2, 2, 2, 2)
        self.assertEqual(pts, [(2, 2)])

    def test_rect_points_outline_count(self):
        st = fresh_state()
        st.rect_filled = False
        pts = st.rect_points(0, 0, 4, 4)  # khung 5x5 -> vien = 5*4 = 16 o
        self.assertEqual(len(set(pts)), 16)

    def test_rect_points_filled_count(self):
        st = fresh_state()
        st.rect_filled = True
        pts = st.rect_points(0, 0, 4, 4)  # khung 5x5 dac = 25 o
        self.assertEqual(len(set(pts)), 25)

    def test_rect_points_works_regardless_of_corner_order(self):
        st = fresh_state()
        st.rect_filled = True
        pts_a = set(st.rect_points(0, 0, 3, 3))
        pts_b = set(st.rect_points(3, 3, 0, 0))
        self.assertEqual(pts_a, pts_b)


class TestRecentColors(unittest.TestCase):
    def test_remember_color_adds_to_front(self):
        st = fresh_state()
        st.remember_color("#111111")
        st.remember_color("#222222")
        self.assertEqual(st.recent_colors[:2], ["#222222", "#111111"])

    def test_remember_color_dedupes_and_moves_to_front(self):
        st = fresh_state()
        st.remember_color("#111111")
        st.remember_color("#222222")
        st.remember_color("#111111")
        self.assertEqual(st.recent_colors.count("#111111"), 1)
        self.assertEqual(st.recent_colors[0], "#111111")

    def test_remember_color_caps_at_10(self):
        st = fresh_state()
        for i in range(15):
            st.remember_color(f"#{i:06x}")
        self.assertEqual(len(st.recent_colors), 10)


class TestAnimationPairing(unittest.TestCase):
    """App.anim_pair_name() - dung sprite mau co san (ant_worker_main /
    ant_worker_main_carry) de kiem tra logic ghep cap hoat anh."""

    def test_base_sprite_pairs_with_carry_variant(self):
        app = pe.App()
        original_current = pe.state.current
        try:
            pe.state.current = "ant_worker_main"
            self.assertEqual(app.anim_pair_name(), "ant_worker_main_carry")
        finally:
            pe.state.current = original_current

    def test_carry_variant_pairs_back_to_base(self):
        app = pe.App()
        original_current = pe.state.current
        try:
            pe.state.current = "ant_worker_main_carry"
            self.assertEqual(app.anim_pair_name(), "ant_worker_main")
        finally:
            pe.state.current = original_current

    def test_sprite_without_pair_returns_none(self):
        app = pe.App()
        original_current = pe.state.current
        try:
            pe.state.current = "queen"
            self.assertIsNone(app.anim_pair_name())
        finally:
            pe.state.current = original_current


if __name__ == "__main__":
    unittest.main()
