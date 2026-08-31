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


class TestSpriteFrames(unittest.TestCase):
    """Sprite.add_frame()/delete_frame()/move_frame() + tuong thich nguoc
    cua `pixels` (property tro toi frames[frame_idx]) - dung fresh_state(),
    khong dung toi global pe.state, nen khong can don dep sau test."""

    def test_new_sprite_starts_with_one_frame(self):
        st = fresh_state()
        self.assertEqual(st.sp().n_frames, 1)
        self.assertEqual(st.sp().frame_idx, 0)

    def test_pixels_property_reads_current_frame(self):
        st = fresh_state()
        sp = st.sp()
        sp.frames.append([None] * (sp.size * sp.size))
        sp.frame_idx = 1
        sp.pixels[0] = "#abcdef"
        self.assertEqual(sp.frames[1][0], "#abcdef")
        self.assertIsNone(sp.frames[0][0])

    def test_add_frame_copies_current_by_default(self):
        st = fresh_state()
        sp = st.sp()
        st.set_pixel(0, 0, "#ff0000")
        sp.add_frame(copy_current=True)
        self.assertEqual(sp.n_frames, 2)
        self.assertEqual(sp.frame_idx, 1)
        self.assertEqual(sp.pixels[0], "#ff0000")  # da nhan ban tu khung truoc

    def test_add_frame_blank_is_empty(self):
        st = fresh_state()
        sp = st.sp()
        st.set_pixel(0, 0, "#ff0000")
        sp.add_frame(copy_current=False)
        self.assertTrue(all(p is None for p in sp.pixels))

    def test_add_frame_inserts_right_after_current_not_at_end(self):
        """Them khung moi luc dang o khung DAU (frame_idx=0) trong 1
        sprite da co san 3 khung - khung moi phai chen ngay SAU vi tri
        dang xem, khong phai luon luon bi don xuong cuoi danh sach."""
        st = fresh_state()
        sp = st.sp()
        sp.add_frame(copy_current=False)
        sp.add_frame(copy_current=False)
        self.assertEqual(sp.n_frames, 3)
        sp.frame_idx = 0
        sp.add_frame(copy_current=False)
        self.assertEqual(sp.n_frames, 4)
        self.assertEqual(sp.frame_idx, 1)

    def test_delete_frame_refuses_when_only_one_left(self):
        st = fresh_state()
        sp = st.sp()
        self.assertFalse(sp.delete_frame())
        self.assertEqual(sp.n_frames, 1)

    def test_delete_frame_removes_current_and_clamps_index(self):
        st = fresh_state()
        sp = st.sp()
        sp.add_frame(copy_current=False)
        sp.add_frame(copy_current=False)
        self.assertEqual(sp.frame_idx, 2)
        self.assertTrue(sp.delete_frame())
        self.assertEqual(sp.n_frames, 2)
        self.assertEqual(sp.frame_idx, 1)  # da clamp ve khung cuoi con lai

    def test_move_frame_swaps_content_and_follows_selection(self):
        st = fresh_state()
        sp = st.sp()
        st.set_pixel(0, 0, "#111111")
        sp.add_frame(copy_current=False)
        st.set_pixel(0, 0, "#222222")
        # frame 0 = #111111, frame 1 (dang chon) = #222222
        self.assertTrue(sp.move_frame(-1))
        self.assertEqual(sp.frame_idx, 0)
        self.assertEqual(sp.frames[0][0], "#222222")  # da doi cho noi dung
        self.assertEqual(sp.frames[1][0], "#111111")

    def test_move_frame_out_of_bounds_returns_false_and_no_change(self):
        st = fresh_state()
        sp = st.sp()
        self.assertFalse(sp.move_frame(-1))  # da o dau, khong the sang trai them
        self.assertFalse(sp.move_frame(1))   # chi co 1 khung, khong the sang phai


class TestFrameHistorySnapshot(unittest.TestCase):
    """push_history()/undo()/redo() phai chup TOAN BO danh sach khung +
    frame_idx (khong chi mot minh pixels cua khung dang xem) - de Hoan
    tac dung ngay ca khi giua chung nguoi dung co chuyen qua khung khac."""

    def test_undo_restores_full_frame_list_and_index(self):
        st = fresh_state()
        sp = st.sp()
        st.push_history()
        sp.add_frame(copy_current=False)
        self.assertEqual(sp.n_frames, 2)
        st.undo()
        self.assertEqual(sp.n_frames, 1)
        self.assertEqual(sp.frame_idx, 0)

    def test_redo_after_undo_brings_back_added_frame(self):
        st = fresh_state()
        sp = st.sp()
        st.push_history()
        sp.add_frame(copy_current=False)
        st.undo()
        st.redo()
        self.assertEqual(sp.n_frames, 2)

    def test_undo_does_not_bleed_into_other_frames(self):
        """Ve tren khung 1, hoan tac, KHONG duoc lam mat noi dung da ve o
        khung 0 truoc do (moi frame doc lap, undo/redo khong duoc tron
        lan noi dung giua cac khung)."""
        st = fresh_state()
        sp = st.sp()
        st.set_pixel(0, 0, "#111111")
        sp.add_frame(copy_current=False)
        st.push_history()
        st.set_pixel(1, 1, "#222222")
        st.undo()
        self.assertIsNone(sp.frames[1][1 * sp.size + 1])
        self.assertEqual(sp.frames[0][0], "#111111")  # khung 0 khong bi anh huong


class TestAppFrameActions(unittest.TestCase):
    """App.add_frame()/delete_frame()/move_frame_left()/right()/
    select_frame() - cac ham nay thao tac thang len pe.state (global),
    nen swap tam pe.state sang 1 AppState moi tinh trong setUp/tearDown de
    khong lam ban trang thai cho cac test khac."""

    def setUp(self):
        self._orig_state = pe.state
        pe.state = pe.AppState()
        pe.state.new_sprite("test_sprite", 8, "Test")
        pe.state.current = "test_sprite"
        self.app = pe.App()

    def tearDown(self):
        pe.state = self._orig_state

    def test_add_frame_via_app_increments_count(self):
        self.app.add_frame()
        self.assertEqual(pe.state.sp().n_frames, 2)

    def test_add_blank_frame_via_app_is_empty(self):
        pe.state.set_pixel(0, 0, "#ff0000")
        self.app.add_blank_frame()
        self.assertTrue(all(p is None for p in pe.state.sp().pixels))

    def test_delete_frame_via_app_respects_minimum(self):
        self.app.delete_frame()
        self.assertEqual(pe.state.sp().n_frames, 1, "Khong duoc xoa khung DUY NHAT con lai")

    def test_select_frame_switches_active_frame(self):
        self.app.add_frame()
        self.app.select_frame(0)
        self.assertEqual(pe.state.sp().frame_idx, 0)

    def test_select_frame_stops_playback(self):
        self.app.add_frame()
        self.app.toggle_frame_anim()
        self.assertTrue(pe.state.frame_anim_playing)
        self.app.select_frame(0)
        self.assertFalse(pe.state.frame_anim_playing)

    def test_prev_next_frame_wrap_around(self):
        self.app.add_frame()
        self.app.add_frame()  # 3 khung, dang o frame_idx=2
        self.app.next_frame()
        self.assertEqual(pe.state.sp().frame_idx, 0, "Phai quay vong ve khung dau")
        self.app.prev_frame()
        self.assertEqual(pe.state.sp().frame_idx, 2, "Phai quay vong ve khung cuoi")

    def test_toggle_frame_anim_flips_flag(self):
        self.app.add_frame()
        self.assertFalse(pe.state.frame_anim_playing)
        self.app.toggle_frame_anim()
        self.assertTrue(pe.state.frame_anim_playing)
        self.app.toggle_frame_anim()
        self.assertFalse(pe.state.frame_anim_playing)

    def test_toggle_frame_anim_with_single_frame_autostops_on_update(self):
        """Sprite chi co 1 khung ma nguoi dung van bam Phat thu - phai tu
        dung ngay o lan _update_frame_anim() dau tien (khong co gi de
        chay vong lap ca)."""
        self.app.toggle_frame_anim()
        self.app._update_frame_anim()
        self.assertFalse(pe.state.frame_anim_playing)

    def test_frame_anim_cycles_through_frames_over_time(self):
        self.app.add_frame()
        self.app.add_frame()
        self.app.toggle_frame_anim()
        pe.state.frame_fps = 60  # 1 khung/tick de test nhanh, khong phu thuoc thoi gian that
        seen = set()
        for _ in range(10):
            self.app._update_frame_anim()
            seen.add(pe.state.frame_anim_idx)
        self.assertEqual(seen, {0, 1, 2}, "Phai luot qua du ca 3 khung theo thoi gian")

    def test_change_frame_fps_clamped(self):
        pe.state.frame_fps = 6
        self.app.change_frame_fps(-100)
        self.assertEqual(pe.state.frame_fps, 1)
        self.app.change_frame_fps(100)
        self.assertEqual(pe.state.frame_fps, 24)

    def test_move_frame_left_right_via_app(self):
        pe.state.set_pixel(0, 0, "#111111")
        self.app.add_frame()
        pe.state.set_pixel(0, 0, "#222222")
        self.app.move_frame_left()
        self.assertEqual(pe.state.sp().frame_idx, 0)
        self.assertEqual(pe.state.sp().frames[0][0], "#222222")

    def test_dup_sprite_preserves_all_frames(self):
        self.app.add_frame()
        self.app.add_frame()
        self.assertEqual(pe.state.sp().n_frames, 3)
        self.app.dup_sprite()
        self.assertEqual(pe.state.sp().n_frames, 3, "Nhan ban sprite phai giu nguyen SO KHUNG")


class TestSpritesheetExport(unittest.TestCase):
    """App.sprite_to_spritesheet_surface()/export_native() - sprite nhieu
    khung phai xuat thanh 1 spritesheet ngang chua DU moi khung, sprite 1
    khung phai xuat GIONG HET hanh vi cu (khong doi kich thuoc anh)."""

    def setUp(self):
        self._orig_state = pe.state
        pe.state = pe.AppState()
        pe.state.new_sprite("test_sprite", 8, "Test")
        pe.state.current = "test_sprite"
        self.app = pe.App()

    def tearDown(self):
        pe.state = self._orig_state

    def test_single_frame_sprite_surface_size_unchanged(self):
        surf = self.app.sprite_to_surface(pe.state.sp())
        self.assertEqual(surf.get_size(), (8, 8))

    def test_multiframe_spritesheet_width_is_size_times_frame_count(self):
        pe.state.set_pixel(0, 0, "#ff0000")
        self.app.add_frame()
        pe.state.set_pixel(1, 1, "#00ff00")
        self.app.add_frame()
        pe.state.set_pixel(2, 2, "#0000ff")
        sheet = self.app.sprite_to_spritesheet_surface(pe.state.sp())
        self.assertEqual(sheet.get_size(), (24, 8))

    def test_multiframe_spritesheet_places_each_frame_at_correct_offset(self):
        pe.state.set_pixel(0, 0, "#ff0000")
        self.app.add_frame()
        pe.state.set_pixel(1, 1, "#00ff00")
        sheet = self.app.sprite_to_spritesheet_surface(pe.state.sp())
        self.assertEqual(tuple(sheet.get_at((0, 0)))[:3], (255, 0, 0))
        self.assertEqual(tuple(sheet.get_at((8 + 1, 1)))[:3], (0, 255, 0))

    def test_export_native_single_frame_matches_old_behavior(self):
        import os
        import tempfile
        import pygame
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_dir = pe.SPRITES_DIR
            pe.SPRITES_DIR = tmpdir
            try:
                self.app.export_native()
                path = os.path.join(tmpdir, "test_sprite.png")
                self.assertTrue(os.path.exists(path))
                img = pygame.image.load(path)
                self.assertEqual(img.get_size(), (8, 8))
            finally:
                pe.SPRITES_DIR = orig_dir

    def test_export_native_multiframe_saves_full_spritesheet(self):
        import os
        import tempfile
        import pygame
        pe.state.set_pixel(0, 0, "#ff0000")
        self.app.add_frame()
        pe.state.set_pixel(1, 1, "#00ff00")
        with tempfile.TemporaryDirectory() as tmpdir:
            orig_dir = pe.SPRITES_DIR
            pe.SPRITES_DIR = tmpdir
            try:
                self.app.export_native()
                path = os.path.join(tmpdir, "test_sprite.png")
                img = pygame.image.load(path)
                self.assertEqual(img.get_size(), (16, 8), "Phai xuat DU CA 2 khung, khong chi khung dang xem")
            finally:
                pe.SPRITES_DIR = orig_dir


if __name__ == "__main__":
    unittest.main()
