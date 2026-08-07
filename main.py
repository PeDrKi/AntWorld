"""Ant World 2D - bản chuyển từ 3D sang 2D theo TẦNG (layer).

Thay vì 1 khối 3D xoay được, thế giới giờ là 1 chồng các TẦNG PHẲNG 2D
(giống lát cắt ngang bể nuôi kiến, hoặc các "Z-level" trong game như Dwarf
Fortress/RimWorld): Tầng 0 luôn là MẶT ĐẤT nhìn từ trên xuống. Các tầng bên
dưới (1, 2, 3, ...) là các phòng ngầm - kho, ấu trùng, phòng chúa, và các
phòng người chơi tự đào - mỗi phòng chiếm 1 tầng riêng.

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
  - "Tam dung" / "Toc do xN": điều khiển thời gian mô phỏng.
  - "Tai sinh thuc an: BAT/TAT": bật/tắt thức ăn tự xuất hiện theo chu kỳ.
"""
import math
import os

import numpy as np
import pygame

import config as cfg
from world import SurfaceWorld, UndergroundWorld
from ants import AntColony
from enemy import EnemyManager


# =======================================================================
# Camera 2D: pan (cx, cy = tọa độ lưới đang ở giữa khung nhìn) + zoom
# =======================================================================
class Camera2D:
    def __init__(self, cx, cy, zoom=1.0):
        self.cx = cx
        self.cy = cy
        self.zoom = zoom

    def cell_px(self):
        return cfg.BASE_CELL_PX * self.zoom

    def world_to_screen(self, x, y, center_x, center_y):
        cell = self.cell_px()
        sx = center_x + (x - self.cx) * cell
        sy = center_y + (y - self.cy) * cell
        return sx, sy

    def screen_to_world(self, sx, sy, center_x, center_y):
        cell = self.cell_px()
        x = self.cx + (sx - center_x) / cell
        y = self.cy + (sy - center_y) / cell
        return x, y

    def zoom_at(self, factor, mx, my, center_x, center_y):
        wx, wy = self.screen_to_world(mx, my, center_x, center_y)
        self.zoom = float(np.clip(self.zoom * factor, cfg.MIN_ZOOM, cfg.MAX_ZOOM))
        cell = self.cell_px()
        self.cx = wx - (mx - center_x) / cell
        self.cy = wy - (my - center_y) / cell

    def pan(self, dx_px, dy_px):
        cell = self.cell_px()
        self.cx -= dx_px / cell
        self.cy -= dy_px / cell


# =======================================================================
# Nút bấm UI đơn giản (pygame.Rect + text)
# =======================================================================
class Button:
    def __init__(self, rect, text, on_click=None, toggle=False, active=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.toggle = toggle
        self.active = active

    def draw(self, surf, font):
        color = COLOR_BTN_ACTIVE if self.active else COLOR_BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=5)
        pygame.draw.rect(surf, (90, 90, 100), self.rect, width=1, border_radius=5)
        label = font.render(self.text, True, (240, 240, 240))
        lr = label.get_rect(center=self.rect.center)
        surf.blit(label, lr)

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            if self.on_click:
                self.on_click()
            return True
        return False


COLOR_BTN = (40, 40, 45)
COLOR_BTN_ACTIVE = (70, 130, 180)


def rgb(r, g, b, a=255):
    return (int(r), int(g), int(b), int(a))


def main(max_frames=None):
    pygame.init()
    pygame.display.set_caption("Ant World 2D - tung lop / tung tang")
    screen = pygame.display.set_mode((cfg.SCREEN_W, cfg.SCREEN_H))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("arial", 16)
    font_small = pygame.font.SysFont("arial", 13)
    font_big = pygame.font.SysFont("arial", 22, bold=True)
    font_hud = pygame.font.SysFont("consolas", 15)

    CANVAS_H = cfg.SCREEN_H - cfg.TOOLBAR_H
    CENTER_X = cfg.SCREEN_W / 2.0
    CENTER_Y = CANVAS_H / 2.0

    # -------------------------------------------------------------
    # Thế giới mô phỏng (logic hoàn toàn không đổi so với bản 3D, chỉ
    # khác ở chỗ độ sâu giờ là số tầng rời rạc thay vì z liên tục)
    # -------------------------------------------------------------
    surface_world = SurfaceWorld(protected_nests=[cfg.NEST_POS, cfg.RIVAL_NEST_POS])
    underground_world = UndergroundWorld(cfg.NEST_POS, "")
    colony = AntColony(cfg.NUM_ANTS, surface_world, underground_world, cfg.NEST_POS)

    rival_underground = UndergroundWorld(cfg.RIVAL_NEST_POS, "Doi thu - ")
    rival_colony = AntColony(cfg.NUM_RIVAL_ANTS, surface_world, rival_underground, cfg.RIVAL_NEST_POS)

    enemy = EnemyManager()
    ALL_COLONIES = [colony, rival_colony]
    ALL_UNDERGROUNDS = [underground_world, rival_underground]

    camera = Camera2D(cfg.GRID_SIZE / 2.0, cfg.GRID_SIZE / 2.0, zoom=1.0)

    # tầng đang xem: 0 = mặt đất, >=1 = tầng ngầm
    current_layer = 0

    def max_layer_overall():
        return max(underground_world.max_depth(), rival_underground.max_depth())

    # -------------------------------------------------------------
    # Trạng thái công cụ / thời gian mô phỏng
    # -------------------------------------------------------------
    current_tool = None  # None | "food" | "enemy" | "dig" | "rock" | "water" | "erase"
    sim_paused = False
    sim_speed = 1
    food_respawn_enabled = True
    food_respawn_tick = 0
    grid_visible = True
    graph_visible = True
    frame_counter = 0
    history_tick = 0
    pop_history_main = []
    pop_history_rival = []

    DRAG_TOOLS = {"food", "rock", "water", "erase"}
    DRAG_PLACE_INTERVAL_FRAMES = 6
    drag_cooldown = 0

    # -------------------------------------------------------------
    # Hàm hỗ trợ đặt thức ăn / tái sinh (thuần logic, không cần entity
    # riêng như bản Ursina - pygame vẽ lại toàn bộ mỗi khung hình)
    # -------------------------------------------------------------
    def place_food_at(gx, gy, amount=8.0, food_type=None):
        gx = int(np.clip(gx, 0, cfg.GRID_SIZE - 1))
        gy = int(np.clip(gy, 0, cfg.GRID_SIZE - 1))
        if food_type is None:
            types = list(cfg.FOOD_TYPE_WEIGHTS.keys())
            weights = list(cfg.FOOD_TYPE_WEIGHTS.values())
            food_type = int(np.random.choice(types, p=weights))
        surface_world.food[gx, gy] += amount
        surface_world.food_type[gx, gy] = food_type

    def do_random_food_respawn():
        surface_world.respawn_random_cluster()

    # -------------------------------------------------------------
    # Chuyển đổi tọa độ màn hình <-> tọa độ lưới mô phỏng
    # -------------------------------------------------------------
    def get_canvas_sim_xy(mouse_pos):
        mx, my = mouse_pos
        if my >= CANVAS_H:
            return None  # đang trỏ vào thanh công cụ, không phải khung nhìn
        x, y = camera.screen_to_world(mx, my, CENTER_X, CENTER_Y)
        if 0 <= x <= cfg.GRID_SIZE and 0 <= y <= cfg.GRID_SIZE:
            return float(np.clip(x, 1, cfg.GRID_SIZE - 2)), float(np.clip(y, 1, cfg.GRID_SIZE - 2))
        return None

    def perform_tool_action(tool, sim_x, sim_y, layer):
        if tool in ("food", "enemy", "dig", "rock", "water") and layer != 0:
            return  # các công cụ này chỉ có nghĩa trên mặt đất (Tầng 0)

        if tool == "food":
            place_food_at(int(sim_x), int(sim_y))
        elif tool == "enemy":
            enemy.force_spawn_at(sim_x, sim_y)
        elif tool == "dig":
            underground_world.dig_new_room(sim_x, sim_y)
        elif tool == "rock":
            surface_world.add_obstacle(int(sim_x), int(sim_y), cfg.TERRAIN_ROCK, cfg.ROCK_CLUSTER_RADIUS)
        elif tool == "water":
            surface_world.add_obstacle(int(sim_x), int(sim_y), cfg.TERRAIN_WATER, cfg.WATER_CLUSTER_RADIUS)
        elif tool == "erase":
            if layer == 0:
                surface_world.clear_food_near(sim_x, sim_y, cfg.ERASE_RADIUS)
                surface_world.remove_features_near(sim_x, sim_y, cfg.ERASE_RADIUS)
                for col in ALL_COLONIES:
                    on_surface = col.alive & (col.depth == 0)
                    if np.any(on_surface):
                        idx = np.where(on_surface)[0]
                        dist2 = (col.x[idx] - sim_x) ** 2 + (col.y[idx] - sim_y) ** 2
                        kill_idx = idx[dist2 <= cfg.ERASE_RADIUS ** 2]
                        if len(kill_idx) > 0:
                            col.alive[kill_idx] = False
                            col.underground.total_deaths += len(kill_idx)
            else:
                for uworld in ALL_UNDERGROUNDS:
                    dug_room = uworld.find_dug_room_near(sim_x, sim_y, layer, cfg.ERASE_RADIUS)
                    if dug_room is not None:
                        uworld.remove_room(dug_room[0])
                for col in ALL_COLONIES:
                    on_layer = col.alive & (col.depth == layer)
                    if np.any(on_layer):
                        idx = np.where(on_layer)[0]
                        dist2 = (col.x[idx] - sim_x) ** 2 + (col.y[idx] - sim_y) ** 2
                        kill_idx = idx[dist2 <= cfg.ERASE_RADIUS ** 2]
                        if len(kill_idx) > 0:
                            col.alive[kill_idx] = False
                            col.underground.total_deaths += len(kill_idx)

    # -------------------------------------------------------------
    # Thanh công cụ (nút bấm)
    # -------------------------------------------------------------
    buttons = []

    def set_tool(name):
        nonlocal current_tool
        current_tool = None if current_tool == name else name
        for b in tool_buttons:
            b.active = (b.text_tool == current_tool)

    tool_buttons = []

    def make_tool_button(label, tool_name, x, y, w=108, h=30):
        b = Button((x, y, w, h), label, on_click=lambda: set_tool(tool_name))
        b.text_tool = tool_name
        tool_buttons.append(b)
        buttons.append(b)
        return b

    row1_y = cfg.SCREEN_H - cfg.TOOLBAR_H + 6
    row2_y = row1_y + 38
    x = 10
    for label, tool_name in [
        ("Dat thuc an", "food"), ("Tha ke thu", "enemy"), ("Dao phong", "dig"),
        ("Dat da", "rock"), ("Dat nuoc", "water"), ("Xoa", "erase"),
    ]:
        make_tool_button(label, tool_name, x, row1_y)
        x += 114

    pause_btn = Button((x + 10, row1_y, 90, 30), "Tam dung")
    speed_btn = Button((x + 108, row1_y, 90, 30), "Toc do: x1")

    def toggle_pause():
        nonlocal sim_paused
        sim_paused = not sim_paused
        pause_btn.text = "Tiep tuc" if sim_paused else "Tam dung"
        pause_btn.active = sim_paused

    def cycle_speed():
        nonlocal sim_speed
        sim_speed = {1: 2, 2: 4, 4: 1}[sim_speed]
        speed_btn.text = f"Toc do: x{sim_speed}"

    pause_btn.on_click = toggle_pause
    speed_btn.on_click = cycle_speed
    buttons += [pause_btn, speed_btn]

    respawn_btn = Button((10, row2_y, 190, 26), "Tai sinh thuc an: BAT", active=True)
    grid_btn = Button((208, row2_y, 150, 26), "Luoi o vuong: BAT", active=True)
    graph_btn = Button((366, row2_y, 130, 26), "Bieu do: HIEN", active=True)
    layer_up_btn = Button((cfg.SCREEN_W - 150, row2_y, 60, 26), "Tang ^")
    layer_down_btn = Button((cfg.SCREEN_W - 84, row2_y, 60, 26), "Tang v")

    def toggle_respawn():
        nonlocal food_respawn_enabled
        food_respawn_enabled = not food_respawn_enabled
        respawn_btn.text = f"Tai sinh thuc an: {'BAT' if food_respawn_enabled else 'TAT'}"
        respawn_btn.active = food_respawn_enabled

    def toggle_grid():
        nonlocal grid_visible
        grid_visible = not grid_visible
        grid_btn.text = f"Luoi o vuong: {'BAT' if grid_visible else 'TAT'}"
        grid_btn.active = grid_visible

    def toggle_graph():
        nonlocal graph_visible
        graph_visible = not graph_visible
        graph_btn.text = f"Bieu do: {'HIEN' if graph_visible else 'AN'}"
        graph_btn.active = graph_visible

    def change_layer(delta):
        nonlocal current_layer
        current_layer = int(np.clip(current_layer + delta, 0, max_layer_overall()))

    respawn_btn.on_click = toggle_respawn
    grid_btn.on_click = toggle_grid
    graph_btn.on_click = toggle_graph
    layer_up_btn.on_click = lambda: change_layer(-1)
    layer_down_btn.on_click = lambda: change_layer(1)
    buttons += [respawn_btn, grid_btn, graph_btn, layer_up_btn, layer_down_btn]

    # -------------------------------------------------------------
    # Vẽ 1 tầng (mặt đất hoặc 1 tầng ngầm)
    # -------------------------------------------------------------
    def layer_name(depth):
        if depth == 0:
            return "Mat dat"
        if depth == cfg.DEPTH_STORAGE:
            return "Kho thuc an"
        if depth == cfg.DEPTH_NURSERY:
            return "Au trung"
        if depth == cfg.DEPTH_QUEEN:
            return "Phong chua"
        return f"Phong dao (tang {depth})"

    def draw_grid_lines(surf):
        cell = camera.cell_px()
        x0, y0 = camera.world_to_screen(0, 0, CENTER_X, CENTER_Y)
        step = cell
        gx = x0
        col_i = 0
        while gx < cfg.SCREEN_W + step:
            if gx >= -step:
                pygame.draw.line(surf, (0, 0, 0, 40), (gx, max(0, y0)), (gx, min(CANVAS_H, y0 + cfg.GRID_SIZE * cell)), 1)
            gx += step
            col_i += 1
        gy = y0
        while gy < CANVAS_H + step:
            if gy >= -step:
                pygame.draw.line(surf, (0, 0, 0, 40), (max(0, x0), gy), (min(cfg.SCREEN_W, x0 + cfg.GRID_SIZE * cell), gy), 1)
            gy += step

    def draw_surface_layer(surf):
        cell = camera.cell_px()
        x0, y0 = camera.world_to_screen(0, 0, CENTER_X, CENTER_Y)
        ground_rect = pygame.Rect(x0, y0, cfg.GRID_SIZE * cell, cfg.GRID_SIZE * cell)
        pygame.draw.rect(surf, cfg.COLOR_GROUND_FILL, ground_rect)

        if grid_visible and cell >= 3:
            draw_grid_lines(surf)

        # --- địa hình: đá + nước (lấy mẫu thưa theo bước lưới cho nhanh) ---
        terrain = surface_world.terrain
        step = max(1, int(1 / max(cell / cfg.BASE_CELL_PX, 0.05)))
        for gx in range(0, cfg.GRID_SIZE, step):
            for gy in range(0, cfg.GRID_SIZE, step):
                t = terrain[gx, gy]
                if t == cfg.TERRAIN_EMPTY:
                    continue
                sx, sy = camera.world_to_screen(gx, gy, CENTER_X, CENTER_Y)
                if t == cfg.TERRAIN_ROCK:
                    color = (120, 118, 112)
                else:
                    color = (70, 140, 200)
                r = max(1, int(cell * step * 0.55))
                pygame.draw.rect(surf, color, (sx - r / 2, sy - r / 2, r, r))

        # --- thức ăn (lấy mẫu thưa) ---
        food = surface_world.food
        food_type = surface_world.food_type
        fstep = 1 if cell > 10 else 2
        for gx in range(0, cfg.GRID_SIZE, fstep):
            for gy in range(0, cfg.GRID_SIZE, fstep):
                if food[gx, gy] > 0.5:
                    ftype = int(food_type[gx, gy])
                    fc = cfg.FOOD_TYPE_COLOR.get(ftype, (60, 150, 60))
                    sx, sy = camera.world_to_screen(gx, gy, CENTER_X, CENTER_Y)
                    r = max(2, int(cell * 0.28))
                    pygame.draw.circle(surf, fc, (int(sx), int(sy)), r)

        # --- lỗ tổ 2 bên ---
        for pos, color in ((cfg.NEST_POS, (30, 22, 14)), (cfg.RIVAL_NEST_POS, (45, 20, 18))):
            sx, sy = camera.world_to_screen(pos[0], pos[1], CENTER_X, CENTER_Y)
            r = max(3, int(cell * 1.4))
            pygame.draw.circle(surf, color, (int(sx), int(sy)), r)
            pygame.draw.circle(surf, (0, 0, 0), (int(sx), int(sy)), r, 2)

        # --- kẻ thù ---
        if enemy.active:
            sx, sy = camera.world_to_screen(enemy.x, enemy.y, CENTER_X, CENTER_Y)
            r = max(3, int(cell * 0.6))
            pts = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
            pygame.draw.polygon(surf, (220, 30, 30), pts)

        draw_ants(surf, colony, (25, 25, 25), (215, 120, 30))
        draw_ants(surf, rival_colony, (120, 30, 25), (230, 140, 40))

    def draw_room_floor(surf, cx, cy, r_px, room_rgb, room_id):
        """Vẽ 1 phòng ngầm như 1 KHU VỰC SÀN thật sự (không phải hình tròn
        trang trí) - có viền tường đất bo tròn + lớp sàn sáng hơn bên trong
        + vài chấm vân sàn để mắt nhận ra ngay đây là không gian kiến có
        thể đi lại/hoạt động bên trong, khác hẳn đường hành lang mảnh."""
        # viền tường đất (đậm, dày) rồi lớp sàn (nhạt hơn, mờ dịu ở giữa)
        wall_color = tuple(max(0, c - 60) for c in room_rgb)
        floor_color = tuple(min(255, c + 45) for c in room_rgb)
        pygame.draw.circle(surf, wall_color, (cx, cy), r_px + max(2, int(r_px * 0.12)))
        pygame.draw.circle(surf, floor_color, (cx, cy), r_px)
        pygame.draw.circle(surf, room_rgb, (cx, cy), max(1, int(r_px * 0.78)))

        # vân sàn: vài chấm cố định (không đổi mỗi khung hình) để trông có
        # kết cấu, không phẳng lì
        rng_local = np.random.RandomState(room_id * 97 + 13)
        n_dots = int(np.clip(r_px * r_px / 90, 5, 26))
        ang = rng_local.uniform(0, 2 * np.pi, n_dots)
        rad = np.sqrt(rng_local.uniform(0, 1, n_dots)) * r_px * 0.82
        dot_color = tuple(max(0, c - 35) for c in room_rgb)
        for a, rr in zip(ang, rad):
            dx = int(math.cos(a) * rr)
            dy = int(math.sin(a) * rr)
            dr = max(1, int(r_px * 0.05))
            pygame.draw.circle(surf, dot_color, (cx + dx, cy + dy), dr)

        pygame.draw.circle(surf, (0, 0, 0), (cx, cy), r_px + max(2, int(r_px * 0.12)), 2)

    def draw_underground_layer(surf, depth):
        pygame.draw.rect(surf, cfg.COLOR_BG_UNDERGROUND, (0, 0, cfg.SCREEN_W, CANVAS_H))
        cell = camera.cell_px()
        if grid_visible and cell >= 3:
            draw_grid_lines(surf)

        for uworld, base_rgb in ((underground_world, (0, 200, 255)), (rival_underground, (255, 120, 90))):
            # giếng (thang máy) - chỉ hiện nếu tổ này CÓ phòng ở tầng này
            has_room_here = any(r[5] == depth for r in uworld.rooms)
            if has_room_here:
                sx, sy = camera.world_to_screen(float(uworld.shaft_xy[0]), float(uworld.shaft_xy[1]), CENTER_X, CENTER_Y)
                r = max(3, int(cell * 0.8))
                pygame.draw.circle(surf, cfg.COLOR_SHAFT, (int(sx), int(sy)), r)
                pygame.draw.circle(surf, (90, 90, 90), (int(sx), int(sy)), r, 1)

            for room in uworld.rooms:
                room_id, name, center, radius, room_rgb, room_depth = room
                if room_depth != depth:
                    continue
                cx, cy = camera.world_to_screen(float(center[0]), float(center[1]), CENTER_X, CENTER_Y)
                # hành lang nối giếng <-> phòng (cùng tầng) - vẽ TRƯỚC, mảnh
                # và mờ hơn, để rõ ràng đây chỉ là đường DI CHUYỂN, không
                # phải nơi kiến "ở lại hoạt động"
                sx, sy = camera.world_to_screen(float(uworld.shaft_xy[0]), float(uworld.shaft_xy[1]), CENTER_X, CENTER_Y)
                pygame.draw.line(surf, (95, 85, 78), (int(sx), int(sy)), (int(cx), int(cy)), max(1, int(cell * 0.09)))

                r_px = max(10, int(radius * cell))
                draw_room_floor(surf, int(cx), int(cy), r_px, room_rgb, room_id)

                if room_id == 2:  # phòng chúa - vẽ thêm biểu tượng chúa (bụng to)
                    pygame.draw.ellipse(
                        surf, tuple(max(0, c - 25) for c in room_rgb),
                        (cx - r_px * 0.5, cy - r_px * 0.3, r_px * 1.0, r_px * 0.6)
                    )
                label = font_small.render(name, True, (235, 235, 235))
                surf.blit(label, label.get_rect(center=(cx, cy - r_px - 12)))

        draw_ants(surf, colony, (220, 220, 220), (235, 190, 70), depth_filter=depth)
        draw_ants(surf, rival_colony, (200, 160, 155), (240, 170, 60), depth_filter=depth)

    def draw_ants(surf, colony_obj, color_normal, color_carry, depth_filter=0):
        mask = colony_obj.alive & (colony_obj.depth == depth_filter)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        cell = camera.cell_px()
        xs, ys = colony_obj.x[idx], colony_obj.y[idx]
        carrying = colony_obj.carrying[idx]
        is_major = colony_obj.role[idx] == cfg.ROLE_MAJOR
        sxs = CENTER_X + (xs - camera.cx) * cell
        sys_ = CENTER_Y + (ys - camera.cy) * cell
        for i in range(len(idx)):
            sx, sy = sxs[i], sys_[i]
            if sx < -10 or sx > cfg.SCREEN_W + 10 or sy < -10 or sy > CANVAS_H + 10:
                continue
            base_r = cell * 0.16
            r = max(1, int(base_r * (cfg.MAJOR_SIZE_SCALE if is_major[i] else 1.0)))
            color = color_carry if carrying[i] else color_normal
            pygame.draw.circle(surf, color, (int(sx), int(sy)), r)

    # -------------------------------------------------------------
    # Biểu đồ dân số theo thời gian (panel góc phải trên)
    # -------------------------------------------------------------
    def draw_graph(surf):
        if not graph_visible or len(pop_history_main) < 2:
            return
        panel_x = cfg.SCREEN_W - cfg.GRAPH_PANEL_W - 12
        panel_y = 12
        panel = pygame.Rect(panel_x, panel_y, cfg.GRAPH_PANEL_W, cfg.GRAPH_PANEL_H)
        s = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 130))
        surf.blit(s, panel.topleft)
        title = font_small.render("Dan so theo thoi gian", True, (255, 255, 255))
        surf.blit(title, (panel_x + 8, panel_y + 6))

        max_val = max(colony.n, rival_colony.n, 1)
        pad = 10
        gx0, gx1 = panel_x + pad, panel_x + panel.w - pad
        gy0, gy1 = panel_y + panel.h - pad, panel_y + 26

        def to_points(hist):
            n = len(hist)
            pts = []
            for i, v in enumerate(hist):
                t = i / max(1, cfg.HISTORY_MAX_POINTS - 1)
                x = gx0 + t * (gx1 - gx0)
                y = gy0 - min(1.0, v / max_val) * (gy0 - gy1)
                pts.append((x, y))
            return pts

        if len(pop_history_main) >= 2:
            pygame.draw.lines(surf, (30, 30, 30), False, to_points(pop_history_main), 2)
        if len(pop_history_rival) >= 2:
            pygame.draw.lines(surf, (200, 60, 50), False, to_points(pop_history_rival), 2)

    # -------------------------------------------------------------
    # HUD (góc trên trái)
    # -------------------------------------------------------------
    def draw_hud(surf):
        c = colony.counts()
        r = rival_colony.counts()
        canh_bao = "  *** DAN KIEN DANG DOI ***" if c["is_starving"] else ""
        khat = "  *** DAN KIEN DANG KHAT NUOC ***" if c["is_dehydrated"] else ""
        ke_thu = "  *** CO KE THU TREN MAT DAT ***" if enemy.active else ""
        lines = [
            f"TO CHINH - Dan so: {c['population']}/{colony.n} (linh: {c['soldiers']})   "
            f"Sinh: {c['total_births']}  Chet: {c['total_deaths']}",
            f"TO DOI THU - Dan so: {r['population']}/{rival_colony.n} (linh: {r['soldiers']})   "
            f"Sinh: {r['total_births']}  Chet: {r['total_deaths']}",
            f"Kho: {c['food_in_storage']:.0f}  Au trung: {c['food_in_nursery']:.0f}  "
            f"Nuoc: {c['water_in_storage']:.0f}  Ke thu da giet: {enemy.total_kills}"
            f"{canh_bao}{khat}{ke_thu}",
            "Ctrl+Lan chuot: doi tang | Lan chuot: zoom | Chuot phai+keo: di chuyen | Esc: thoat",
        ]
        panel = pygame.Surface((900, 20 * len(lines) + 10), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 140))
        surf.blit(panel, (8, 8))
        for i, line in enumerate(lines):
            txt = font_hud.render(line, True, (255, 255, 255))
            surf.blit(txt, (14, 12 + i * 20))

        # --- nhãn tầng hiện tại, to, dễ thấy ---
        name = layer_name(current_layer)
        label = font_big.render(f"Tang {current_layer}: {name}", True, (255, 255, 80))
        lr = label.get_rect(topright=(cfg.SCREEN_W - 12, 8))
        bg = pygame.Surface((lr.w + 16, lr.h + 10), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 140))
        surf.blit(bg, (lr.x - 8, lr.y - 5))
        surf.blit(label, lr)

    def draw_toolbar(surf):
        pygame.draw.rect(surf, (22, 22, 26), (0, cfg.SCREEN_H - cfg.TOOLBAR_H, cfg.SCREEN_W, cfg.TOOLBAR_H))
        for b in buttons:
            b.draw(surf, font)
        hint = "Chon cong cu, CLICK hoac GIU+KEO chuot trai de dung (tru Dao phong/Tha ke thu)"
        if current_tool in ("food", "enemy", "dig", "rock", "water") and current_layer != 0:
            hint = "Cong cu nay chi dung duoc o Tang 0 (Mat dat) - doi tang bang Ctrl+Lan chuot"
        txt = font_small.render(hint, True, (255, 230, 90))
        surf.blit(txt, (10, cfg.SCREEN_H - 18))

    # -------------------------------------------------------------
    # Vòng lặp chính
    # -------------------------------------------------------------
    running = True
    panning = False
    last_mouse = (0, 0)
    frame_no = 0

    while running:
        mods = pygame.key.get_mods()
        ctrl_held = bool(mods & pygame.KMOD_CTRL)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_UP:
                    change_layer(-1)
                elif event.key == pygame.K_DOWN:
                    change_layer(1)
            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if ctrl_held:
                    change_layer(-1 if event.y > 0 else 1)
                else:
                    factor = cfg.ZOOM_STEP if event.y > 0 else 1.0 / cfg.ZOOM_STEP
                    camera.zoom_at(factor, mx, my, CENTER_X, CENTER_Y)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    handled = False
                    for b in buttons:
                        if b.handle_click(event.pos):
                            handled = True
                            break
                    if not handled and current_tool is not None:
                        pos = get_canvas_sim_xy(event.pos)
                        if pos is not None:
                            perform_tool_action(current_tool, pos[0], pos[1], current_layer)
                elif event.button == 3:
                    panning = True
                    last_mouse = event.pos
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3:
                    panning = False
            elif event.type == pygame.MOUSEMOTION:
                if panning:
                    dx = event.pos[0] - last_mouse[0]
                    dy = event.pos[1] - last_mouse[1]
                    camera.pan(dx, dy)
                    last_mouse = event.pos

        # --- kéo chuột trái liên tục để rải (thức ăn/đá/nước/xóa) ---
        if current_tool in DRAG_TOOLS and pygame.mouse.get_pressed()[0]:
            if drag_cooldown <= 0:
                pos = get_canvas_sim_xy(pygame.mouse.get_pos())
                if pos is not None:
                    perform_tool_action(current_tool, pos[0], pos[1], current_layer)
                    drag_cooldown = DRAG_PLACE_INTERVAL_FRAMES
            else:
                drag_cooldown -= 1
        else:
            drag_cooldown = 0

        # --- cập nhật mô phỏng ---
        if not sim_paused:
            for _ in range(sim_speed):
                colony.update()
                rival_colony.update()
                enemy.update(ALL_COLONIES)
                if enemy.active:
                    surface_world.deposit_danger(enemy.x, enemy.y)
                if food_respawn_enabled:
                    food_respawn_tick += 1
                    if food_respawn_tick % cfg.FOOD_RESPAWN_INTERVAL == 0:
                        do_random_food_respawn()

                history_tick += 1
                if history_tick % cfg.HISTORY_SAMPLE_INTERVAL == 0:
                    pop_history_main.append(int(colony.alive.sum()))
                    pop_history_rival.append(int(rival_colony.alive.sum()))
                    if len(pop_history_main) > cfg.HISTORY_MAX_POINTS:
                        del pop_history_main[0]
                        del pop_history_rival[0]

        # --- vẽ ---
        if current_layer == 0:
            screen.fill(cfg.COLOR_BG_SURFACE)
            draw_surface_layer(screen)
        else:
            screen.fill(cfg.COLOR_BG_UNDERGROUND)
            draw_underground_layer(screen, current_layer)

        draw_graph(screen)
        draw_hud(screen)
        draw_toolbar(screen)

        pygame.display.flip()
        clock.tick(cfg.FPS)

        frame_counter += 1
        frame_no += 1
        if max_frames is not None and frame_no >= max_frames:
            running = False

    pygame.quit()


if __name__ == "__main__":
    main()
