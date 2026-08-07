# -*- coding: utf-8 -*-
"""Test cho pixel_editor.py - chu yeu la logic AppState (khong dung QUA
nhieu vao viec ve UI tung frame, vi phan do chu can chay-khong-crash la
du, da kiem bang tay/bang mat khi phat trien)."""
import unittest

import pixel_editor as pe


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


if __name__ == "__main__":
    unittest.main()
