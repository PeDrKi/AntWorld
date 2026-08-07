"""Ant World 2D - bản chuyển từ 3D sang 2D theo TẦNG (layer).

Thay vì 1 khối 3D xoay được, thế giới giờ là 1 chồng các TẦNG PHẲNG 2D
(giống lát cắt ngang bể nuôi kiến, hoặc các "Z-level" trong game như Dwarf
Fortress/RimWorld): Tầng 0 luôn là MẶT ĐẤT nhìn từ trên xuống. Các tầng bên
dưới (1, 2, 3, ...) là các phòng ngầm - gác cửa, kho, bể nước, trứng, ấu
trùng, phòng chúa, nghĩa địa, và các phòng người chơi tự đào - mỗi phòng
chiếm 1 tầng riêng.

Chạy: python main.py

Điều khiển:
  - Giữ CTRL + LĂN CHUỘT      : chuyển qua lại giữa các tầng (lên/xuống)
  - LĂN CHUỘT (không giữ Ctrl): zoom vào/ra tầng đang xem
  - Giữ CHUỘT PHẢI + di chuột : kéo (pan) để di chuyển góc nhìn
  - Phím mũi tên Lên/Xuống    : cũng chuyển tầng (thay thế cho Ctrl+Scroll)
  - Esc                       : thoát

Thanh công cụ dưới màn hình:
  - "Dat thuc an/Tha ke thu/Dao phong/Dat da/Dat nuoc": CHỈ dùng được khi
    đang xem Tầng 0 (Mặt đất) - vì đây là các thao tác đặt trên mặt đất.
  - "Xoa": dùng được ở MỌI tầng - xóa đúng nội dung của tầng đang xem
    (mặt đất: thức ăn/đá/nước/kiến; tầng ngầm: phòng tự đào + kiến đang ở
    tầng đó).
  - "Theo doi": dùng được ở MỌI tầng - bấm trúng 1 con kiến bất kỳ (tổ
    nào cũng được) để camera TỰ ĐỘNG bám theo nó, kể cả khi nó di chuyển
    sang tầng khác (mặt đất <-> hầm). Bấm vào chỗ trống để ngừng theo dõi.
    Tự kéo camera / tự đổi tầng bằng tay cũng sẽ tự ngừng theo dõi.
  - "Tam dung" / "Toc do xN": điều khiển thời gian mô phỏng.
  - "Tai sinh thuc an: BAT/TAT": bật/tắt thức ăn tự xuất hiện theo chu kỳ.
  - "Ke thu tu nhien: BAT/TAT": bật/tắt việc kẻ thù tự động xuất hiện.

--- KIẾN TRÚC FILE (đã tách module cho gọn, xem chi tiết trong từng file) ---
  config.py             - hằng số cấu hình toàn bộ game
  world.py              - SurfaceWorld (mặt đất) + UndergroundWorld (hầm)
  ants.py               - AntColony: đàn kiến dạng mảng NumPy (mô phỏng)
  enemy.py              - kẻ thù tự nhiên trên mặt đất
  camera.py             - Camera2D: pan/zoom màn hình <-> tọa độ lưới
  ui_widgets.py         - Button: nút bấm UI đơn giản
  game_state.py         - GameState: gom dữ liệu + logic điều khiển (world,
                          colony, camera, tool, toggle...) - main.py chỉ
                          cần gọi vào đây, không tự giữ state
  render_surface.py     - vẽ tầng mặt đất + draw_ants (dùng chung mọi tầng)
  render_underground.py - vẽ các tầng ngầm (từng phòng chức năng riêng)
  hud.py                - biểu đồ, bảng thống kê, thanh công cụ
  main.py (file này)    - CHỈ còn: khởi tạo pygame, dựng GameState, vòng
                          lặp sự kiện gọi vào các module trên
"""
import pygame

import config as cfg
from game_state import GameState
import hud
from render_surface import draw_surface_layer
from render_underground import draw_underground_layer


def handle_events(state):
    """Xử lý toàn bộ sự kiện pygame trong 1 khung hình. Trả về False nếu
    người dùng muốn thoát (đóng cửa sổ / nhấn Esc)."""
    mods = pygame.key.get_mods()
    ctrl_held = bool(mods & pygame.KMOD_CTRL)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        elif event.type == pygame.VIDEORESIZE:
            state.handle_resize(event.w, event.h)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            elif event.key == pygame.K_UP:
                state.stop_follow()
                state.change_layer(-1)
            elif event.key == pygame.K_DOWN:
                state.stop_follow()
                state.change_layer(1)
        elif event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if ctrl_held:
                state.stop_follow()
                state.change_layer(-1 if event.y > 0 else 1)
            else:
                factor = cfg.ZOOM_STEP if event.y > 0 else 1.0 / cfg.ZOOM_STEP
                state.camera.zoom_at(factor, mx, my, state.CENTER_X, state.CENTER_Y)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                handled = False
                for b in state.buttons:
                    if b.handle_click(event.pos):
                        handled = True
                        break
                if not handled and state.current_tool is not None:
                    pos = state.get_canvas_sim_xy(event.pos)
                    if pos is not None:
                        state.perform_tool_action(state.current_tool, pos[0], pos[1], state.current_layer)
            elif event.button == 3:
                state.stop_follow()
                state.panning = True
                state.last_mouse = event.pos
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3:
                state.panning = False
        elif event.type == pygame.MOUSEMOTION:
            if state.panning:
                dx = event.pos[0] - state.last_mouse[0]
                dy = event.pos[1] - state.last_mouse[1]
                state.camera.pan(dx, dy)
                state.last_mouse = event.pos

    # --- kéo chuột trái liên tục để rải (thức ăn/đá/nước/xóa) ---
    if state.current_tool in state.DRAG_TOOLS and pygame.mouse.get_pressed()[0]:
        if state.drag_cooldown <= 0:
            pos = state.get_canvas_sim_xy(pygame.mouse.get_pos())
            if pos is not None:
                state.perform_tool_action(state.current_tool, pos[0], pos[1], state.current_layer)
                state.drag_cooldown = state.DRAG_PLACE_INTERVAL_FRAMES
        else:
            state.drag_cooldown -= 1
    else:
        state.drag_cooldown = 0

    return True


def render(state):
    screen = state.screen
    if state.current_layer == 0:
        screen.fill(cfg.COLOR_BG_SURFACE)
        draw_surface_layer(state, screen)
    else:
        screen.fill(cfg.COLOR_BG_UNDERGROUND)
        draw_underground_layer(state, screen, state.current_layer)

    hud.draw_graph(state, screen)
    hud.draw_hud(state, screen)
    hud.draw_toolbar(state, screen)
    pygame.display.flip()


def main(max_frames=None):
    pygame.init()
    state = GameState()
    hud.build_toolbar(state)

    state.panning = False
    state.last_mouse = (0, 0)
    frame_no = 0
    running = True

    while running:
        running = handle_events(state)

        if not state.sim_paused:
            for _ in range(state.sim_speed):
                state.step_simulation()

        state.update_follow_camera()
        render(state)
        state.clock.tick(cfg.FPS)

        state.frame_counter += 1
        frame_no += 1
        if max_frames is not None and frame_no >= max_frames:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
