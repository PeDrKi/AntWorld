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
  - "Dat thuc an/Tha ke thu/Dat da/Dat nuoc": CHỈ dùng được khi đang xem
    Tầng 0 (Mặt đất) - vì đây là các thao tác đặt trên mặt đất.
  - "Xoa": dùng được ở MỌI tầng - xóa đúng nội dung của tầng đang xem
    (mặt đất: thức ăn/đá/nước/kiến; tầng ngầm: kiến đang ở tầng đó).
  - "Theo doi": dùng được ở MỌI tầng - bấm trúng 1 con kiến bất kỳ (tổ
    nào cũng được) để camera TỰ ĐỘNG bám theo nó, kể cả khi nó di chuyển
    sang tầng khác (mặt đất <-> hầm). Bấm vào chỗ trống để ngừng theo dõi.
    Tự kéo camera / tự đổi tầng bằng tay cũng sẽ tự ngừng theo dõi.
  - "Tam dung" / "Toc do xN": điều khiển thời gian mô phỏng.
  - "Tai sinh thuc an: BAT/TAT": bật/tắt thức ăn tự xuất hiện theo chu kỳ.
  - "Ke thu tu nhien: BAT/TAT": bật/tắt việc kẻ thù tự động xuất hiện.

Thanh công cụ / bảng thống kê / biểu đồ đều là các "CỬA SỔ" NỔI TRÊN khung
nhìn mô phỏng (không phải cửa sổ hệ điều hành riêng - pygame chỉ có 1 cửa
sổ - mà là panel UI vẽ đè lên, hoạt động như cửa sổ con):
  - KÉO được: bấm giữ vào THANH TIÊU ĐỀ (có 3 chấm nhỏ bên trái) rồi kéo
    tới bất kỳ vị trí nào trên màn hình.
  - THU GỌN được: bấm nút [-]/[+"] góc phải thanh tiêu đề để thu lại chỉ
    còn thanh tiêu đề (giải phóng khung nhìn) / mở ra lại.
  - Vị trí/trạng thái thu gọn được GIỮ NGUYÊN khi resize cửa sổ.

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

from . import config as cfg
from .game_state import GameState
from . import hud
from .render_surface import draw_surface_layer
from .render_underground import draw_underground_layer


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
            elif event.key == pygame.K_UP and state.active_tab == "sim":
                state.stop_follow()
                state.change_layer(-1)
            elif event.key == pygame.K_DOWN and state.active_tab == "sim":
                state.stop_follow()
                state.change_layer(1)
            elif event.key == pygame.K_s and ctrl_held:
                state.save_game()
            elif event.key == pygame.K_l and ctrl_held:
                state.load_game()
        elif event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            if any(p.contains((mx, my)) for p in state.visible_panels()):
                pass  # con tro dang o tren 1 panel noi - khong tac dong len camera/tang
            elif state.active_tab != "sim":
                pass  # tab Demo me cung khong pan/zoom - luon vua khung nhin
            elif ctrl_held:
                state.stop_follow()
                state.change_layer(-1 if event.y > 0 else 1)
            else:
                factor = cfg.ZOOM_STEP if event.y > 0 else 1.0 / cfg.ZOOM_STEP
                state.camera.zoom_at(factor, mx, my, state.CENTER_X, state.CENTER_Y)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                handled = False
                for panel in state.visible_panels():
                    if panel.handle_mousedown(event.pos):
                        handled = True
                        break
                if not handled and state.active_tab == "sim" and state.current_tool is not None:
                    pos = state.get_canvas_sim_xy(event.pos)
                    if pos is not None:
                        state.perform_tool_action(state.current_tool, pos[0], pos[1], state.current_layer)
            elif event.button == 3:
                # Chỉ bắt đầu kéo (pan) camera nếu KHÔNG bấm trúng 1 panel
                # nổi nào - tránh vừa kéo camera vừa kéo panel bên trên nó
                if state.active_tab == "sim" and not any(p.contains(event.pos) for p in state.visible_panels()):
                    state.stop_follow()
                    state.panning = True
                    state.last_mouse = event.pos
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                for panel in state.visible_panels():
                    panel.handle_mouseup()
            elif event.button == 3:
                state.panning = False
        elif event.type == pygame.MOUSEMOTION:
            for panel in state.visible_panels():
                panel.handle_mousemotion(event.pos, state.SCREEN_W, state.SCREEN_H)
            if state.panning:
                dx = event.pos[0] - state.last_mouse[0]
                dy = event.pos[1] - state.last_mouse[1]
                state.camera.pan(dx, dy)
                state.last_mouse = event.pos

    # --- kéo chuột trái liên tục để rải (thức ăn/đá/nước/xóa) - chỉ ở tab
    # Mo phong, tab Demo me cung không có công cụ đặt/rải ---
    if state.active_tab == "sim" and state.current_tool in state.DRAG_TOOLS and pygame.mouse.get_pressed()[0]:
        mp = pygame.mouse.get_pos()
        over_panel = any(p.contains(mp) for p in state.visible_panels())
        if over_panel:
            pass
        elif state.drag_cooldown <= 0:
            pos = state.get_canvas_sim_xy(mp)
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
    if state.active_tab == "maze":
        screen.fill(cfg.COLOR_BG_SURFACE)
        state.maze_demo.render(state, screen)
        hud.draw_tab_panel(state, screen)
        hud.draw_maze_panel(state, screen)
        hud.draw_toasts(state, screen)
        pygame.display.flip()
        return

    if state.current_layer == 0:
        screen.fill(cfg.COLOR_BG_SURFACE)
        draw_surface_layer(state, screen)
    else:
        screen.fill(cfg.COLOR_BG_UNDERGROUND)
        draw_underground_layer(state, screen, state.current_layer)

    # --- Hiệu ứng chớp đen mờ dần khi vừa đổi tầng (xem trigger_layer_fade
    # trong game_state.py) - vẽ NGAY SAU khung nhìn mô phỏng nhưng TRƯỚC
    # toàn bộ HUD/toolbar/panel nổi bên dưới, để lớp phủ chỉ làm tối phần
    # bản đồ, không làm mờ luôn cả giao diện (vẫn bấm nút bình thường được
    # trong lúc đang chuyển tầng). alpha=0 thì bỏ qua luôn, khỏi tốn 1 lần
    # blit surface mỗi khung hình bình thường (chiếm đa số thời gian chơi).
    fade_alpha = state.layer_fade_alpha()
    if fade_alpha > 0:
        overlay = pygame.Surface((state.SCREEN_W, state.CANVAS_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, fade_alpha))
        screen.blit(overlay, (0, 0))

    hud.draw_graph(state, screen)
    hud.draw_hud(state, screen)
    hud.draw_toolbar(state, screen)
    hud.draw_layer_map(state, screen)
    hud.draw_tab_panel(state, screen)
    hud.draw_toasts(state, screen)
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

        if state.active_tab == "maze":
            state.maze_demo.step()

        state.update_follow_camera()
        state.check_alerts()
        state.update_toasts()
        state.advance_layer_fade()
        render(state)
        state.clock.tick(cfg.FPS)

        state.frame_counter += 1
        frame_no += 1
        if max_frames is not None and frame_no >= max_frames:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
