"""GameState: gom toàn bộ dữ liệu + logic điều khiển (không phải vẽ) vào 1
chỗ, để main.py chỉ còn là vòng lặp sự kiện pygame gọi vào đây, và các
module render_*.py/hud.py chỉ cần nhận `state` để đọc dữ liệu cần vẽ - thay
vì main.py cũ nhồi tất cả (world, colony, camera, toolbar, render, vòng
lặp...) vào 1 hàm main() 900 dòng dùng closures.
"""
import os
import sys

import numpy as np
import pygame

import config as cfg
from world import SurfaceWorld, UndergroundWorld
from ants import AntColony
from enemy import EnemyManager
from camera import Camera2D

# Khi chạy bình thường: assets/ nằm cạnh file .py này. Khi được đóng gói
# thành .exe bằng PyInstaller (chế độ --onefile), file được giải nén tạm
# vào thư mục sys._MEIPASS lúc chạy - phải trỏ theo đó thay vì theo vị trí
# file .py (không còn tồn tại trong bản .exe).
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    ASSETS_DIR = os.path.join(sys._MEIPASS, "assets")
else:
    ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


class GameState:
    def __init__(self):
        # Cửa sổ CÓ THỂ THAY ĐỔI KÍCH THƯỚC (RESIZABLE) - để nút phóng to
        # (maximize) trên thanh tiêu đề Windows thật sự hoạt động, không bị
        # mờ/vô hiệu như khi cửa sổ cố định kích thước.
        self.SCREEN_W, self.SCREEN_H = cfg.SCREEN_W, cfg.SCREEN_H
        self.screen = pygame.display.set_mode(
            (self.SCREEN_W, self.SCREEN_H), pygame.RESIZABLE
        )
        pygame.display.set_caption("Ant World 2D - tung lop / tung tang")
        self._set_window_icon()
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("arial", 16)
        self.font_small = pygame.font.SysFont("arial", 13)
        self.font_big = pygame.font.SysFont("arial", 22, bold=True)
        self.font_hud = pygame.font.SysFont("consolas", 15)

        # Canvas mô phỏng giờ chiếm TOÀN BỘ cửa sổ (thanh công cụ/bảng
        # thống kê/biểu đồ không còn là dải cố định chiếm chỗ nữa - chúng
        # là các Panel NỔI TRÊN canvas, kéo/thu gọn được - xem hud.py)
        self.CANVAS_H = self.SCREEN_H
        self.CENTER_X = self.SCREEN_W / 2.0
        self.CENTER_Y = self.CANVAS_H / 2.0

        # --- Thế giới mô phỏng (logic không đổi so với bản 3D, chỉ khác ở
        # chỗ độ sâu giờ là số tầng rời rạc thay vì z liên tục) ---
        self.surface_world = SurfaceWorld(protected_nests=[cfg.NEST_POS, cfg.RIVAL_NEST_POS])
        self.underground_world = UndergroundWorld(cfg.NEST_POS, "")
        self.colony = AntColony(
            cfg.NUM_ANTS, cfg.MAX_ANTS_PER_COLONY, self.surface_world, self.underground_world, cfg.NEST_POS
        )
        self.rival_underground = UndergroundWorld(cfg.RIVAL_NEST_POS, "Doi thu - ")
        self.rival_colony = AntColony(
            cfg.NUM_RIVAL_ANTS, cfg.MAX_ANTS_PER_COLONY, self.surface_world, self.rival_underground, cfg.RIVAL_NEST_POS
        )
        self.enemy = EnemyManager()
        self.ALL_COLONIES = [self.colony, self.rival_colony]
        self.ALL_UNDERGROUNDS = [self.underground_world, self.rival_underground]

        self.camera = Camera2D(cfg.GRID_SIZE / 2.0, cfg.GRID_SIZE / 2.0, zoom=1.0)

        # tầng đang xem: 0 = mặt đất, >=1 = tầng ngầm
        self.current_layer = 0

        # --- Trạng thái công cụ / thời gian mô phỏng ---
        self.current_tool = None  # None | "food" | "enemy" | "dig" | "rock" | "water" | "erase"
        self.sim_paused = False
        self.sim_speed = 1
        self.food_respawn_enabled = True
        self.food_respawn_tick = 0
        self.grid_visible = True
        self.graph_visible = True
        self.frame_counter = 0
        self.history_tick = 0
        self.pop_history_main = []
        self.pop_history_rival = []

        self.DRAG_TOOLS = {"food", "rock", "water", "erase"}
        self.DRAG_PLACE_INTERVAL_FRAMES = 6
        self.drag_cooldown = 0

        # --- Camera theo dõi 1 con kiến cụ thể ---
        # follow_colony: tham chiếu trực tiếp tới self.colony hoặc
        # self.rival_colony (đối tượng, so sánh bằng "is"); follow_idx: vị
        # trí của con kiến đó TRONG MẢNG NumPy của đàn đó. None/None nghĩa
        # là không theo dõi con nào.
        self.follow_colony = None
        self.follow_idx = None

        # Thanh công cụ / bảng thống kê / biểu đồ - giờ là các Panel NỔI
        # (ui_widgets.Panel), kéo/thu gọn được; được hud.build_toolbar()
        # tạo và điền vào state.panels (+ state.buttons/tool_buttons).
        self.buttons = []
        self.tool_buttons = []
        self.panels = []
        self.toolbar_panel = None
        self.stats_panel = None
        self.graph_panel = None

    # ------------------------------------------------------------------
    def _set_window_icon(self):
        """Đặt icon cho cửa sổ/taskbar - im lặng bỏ qua nếu không tìm thấy
        file icon (vd chạy từ bản build thiếu file assets)."""
        icon_path = os.path.join(ASSETS_DIR, "icon.png")
        if os.path.isfile(icon_path):
            try:
                pygame.display.set_icon(pygame.image.load(icon_path))
            except pygame.error:
                pass

    def handle_resize(self, new_w, new_h):
        """Gọi khi người dùng kéo giãn/phóng to/thu nhỏ cửa sổ (sự kiện
        pygame.VIDEORESIZE) - cập nhật lại toàn bộ kích thước phụ thuộc và
        dựng lại thanh công cụ. Vị trí các panel người chơi đã tự kéo di
        chuyển sẽ được GIỮ NGUYÊN (xem hud.build_toolbar), chỉ kẹp lại
        trong khung hình mới nếu cửa sổ bị thu nhỏ hơn."""
        new_w = max(cfg.MIN_WINDOW_W, new_w)
        new_h = max(cfg.MIN_WINDOW_H, new_h)
        self.SCREEN_W, self.SCREEN_H = new_w, new_h
        self.screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
        self.CANVAS_H = self.SCREEN_H
        self.CENTER_X = self.SCREEN_W / 2.0
        self.CENTER_Y = self.CANVAS_H / 2.0

        import hud
        hud.build_toolbar(self)

    # ------------------------------------------------------------------
    def max_layer_overall(self):
        return max(self.underground_world.max_depth(), self.rival_underground.max_depth())

    def change_layer(self, delta):
        self.current_layer = int(np.clip(self.current_layer + delta, 0, self.max_layer_overall()))

    # ------------------------------------------------------------------
    # Hàm hỗ trợ đặt thức ăn / tái sinh (thuần logic, không cần entity
    # riêng như bản Ursina - pygame vẽ lại toàn bộ mỗi khung hình)
    # ------------------------------------------------------------------
    def place_food_at(self, gx, gy, amount=8.0, food_type=None):
        gx = int(np.clip(gx, 0, cfg.GRID_SIZE - 1))
        gy = int(np.clip(gy, 0, cfg.GRID_SIZE - 1))
        if food_type is None:
            types = list(cfg.FOOD_TYPE_WEIGHTS.keys())
            weights = list(cfg.FOOD_TYPE_WEIGHTS.values())
            food_type = int(np.random.choice(types, p=weights))
        self.surface_world.food[gx, gy] += amount
        self.surface_world.food_type[gx, gy] = food_type

    def do_random_food_respawn(self):
        self.surface_world.respawn_random_cluster()

    # ------------------------------------------------------------------
    # Chuyển đổi tọa độ màn hình <-> tọa độ lưới mô phỏng
    # ------------------------------------------------------------------
    def get_canvas_sim_xy(self, mouse_pos):
        mx, my = mouse_pos
        if my >= self.CANVAS_H:
            return None  # đang trỏ vào thanh công cụ, không phải khung nhìn
        x, y = self.camera.screen_to_world(mx, my, self.CENTER_X, self.CENTER_Y)
        if 0 <= x <= cfg.GRID_SIZE and 0 <= y <= cfg.GRID_SIZE:
            return float(np.clip(x, 1, cfg.GRID_SIZE - 2)), float(np.clip(y, 1, cfg.GRID_SIZE - 2))
        return None

    def perform_tool_action(self, tool, sim_x, sim_y, layer):
        if tool in ("food", "enemy", "dig", "rock", "water") and layer != 0:
            return  # các công cụ này chỉ có nghĩa trên mặt đất (Tầng 0)

        if tool == "follow":
            # Công cụ "Theo dõi": bấm trúng 1 con kiến (thuộc tổ nào cũng
            # được, ở TẦNG ĐANG XEM) -> camera bắt đầu bám theo nó. Bấm vào
            # chỗ trống (không trúng con nào) -> ngừng theo dõi, giống thao
            # tác "bấm ra ngoài để bỏ chọn" quen thuộc.
            found = self.find_nearest_ant(sim_x, sim_y, layer, cfg.FOLLOW_PICK_RADIUS)
            if found is not None:
                self.start_follow(found[0], found[1])
            else:
                self.stop_follow()
            return

        if tool == "food":
            self.place_food_at(int(sim_x), int(sim_y))
        elif tool == "enemy":
            self.enemy.force_spawn_at(sim_x, sim_y)
        elif tool == "dig":
            self.underground_world.dig_new_room(sim_x, sim_y)
        elif tool == "rock":
            self.surface_world.add_obstacle(int(sim_x), int(sim_y), cfg.TERRAIN_ROCK, cfg.ROCK_CLUSTER_RADIUS)
        elif tool == "water":
            self.surface_world.add_obstacle(int(sim_x), int(sim_y), cfg.TERRAIN_WATER, cfg.WATER_CLUSTER_RADIUS)
        elif tool == "erase":
            if layer == 0:
                self.surface_world.clear_food_near(sim_x, sim_y, cfg.ERASE_RADIUS)
                self.surface_world.remove_features_near(sim_x, sim_y, cfg.ERASE_RADIUS)
                for col in self.ALL_COLONIES:
                    on_surface = col.alive & (col.depth == 0)
                    if np.any(on_surface):
                        idx = np.where(on_surface)[0]
                        dist2 = (col.x[idx] - sim_x) ** 2 + (col.y[idx] - sim_y) ** 2
                        kill_idx = idx[dist2 <= cfg.ERASE_RADIUS ** 2]
                        if len(kill_idx) > 0:
                            col.alive[kill_idx] = False
                            col.underground.total_deaths += len(kill_idx)
                            col.underground.add_corpse(len(kill_idx))
            else:
                for uworld in self.ALL_UNDERGROUNDS:
                    dug_room = uworld.find_dug_room_near(sim_x, sim_y, layer, cfg.ERASE_RADIUS)
                    if dug_room is not None:
                        uworld.remove_room(dug_room[0])
                for col in self.ALL_COLONIES:
                    on_layer = col.alive & (col.depth == layer)
                    if np.any(on_layer):
                        idx = np.where(on_layer)[0]
                        dist2 = (col.x[idx] - sim_x) ** 2 + (col.y[idx] - sim_y) ** 2
                        kill_idx = idx[dist2 <= cfg.ERASE_RADIUS ** 2]
                        if len(kill_idx) > 0:
                            col.alive[kill_idx] = False
                            col.underground.total_deaths += len(kill_idx)
                            col.underground.add_corpse(len(kill_idx))

    # ------------------------------------------------------------------
    # Camera theo dõi 1 con kiến cụ thể
    # ------------------------------------------------------------------
    def find_nearest_ant(self, sim_x, sim_y, layer, max_dist):
        """Tìm con kiến CÒN SỐNG gần điểm (sim_x, sim_y) nhất, ĐANG Ở đúng
        tầng `layer`, trong cả 2 đàn - trả về (colony, idx) hoặc None nếu
        không có con nào trong bán kính max_dist."""
        best = None
        best_d2 = max_dist * max_dist
        for colony in self.ALL_COLONIES:
            mask = colony.alive & (colony.depth == layer)
            if not np.any(mask):
                continue
            idx = np.where(mask)[0]
            dx = colony.x[idx] - sim_x
            dy = colony.y[idx] - sim_y
            d2 = dx * dx + dy * dy
            j = int(np.argmin(d2))
            if d2[j] < best_d2:
                best_d2 = float(d2[j])
                best = (colony, int(idx[j]))
        return best

    def start_follow(self, colony, idx):
        self.follow_colony = colony
        self.follow_idx = idx
        # Phóng to ngay lập tức để nhìn rõ "từng chút một" - chỉ phóng to
        # thêm nếu đang zoom xa hơn mức mục tiêu, không tự thu nhỏ lại nếu
        # người chơi đã zoom gần sẵn từ trước.
        if self.camera.zoom < cfg.FOLLOW_AUTO_ZOOM:
            self.camera.zoom = cfg.FOLLOW_AUTO_ZOOM

    def stop_follow(self):
        self.follow_colony = None
        self.follow_idx = None

    def is_following(self):
        return self.follow_colony is not None and self.follow_idx is not None

    def update_follow_camera(self):
        """Gọi 1 lần mỗi khung hình render (không phải mỗi tick mô phỏng):
        nếu đang theo dõi 1 con kiến, tự chuyển sang đúng tầng nó đang ở và
        cho camera bám mượt theo vị trí của nó. Tự động NGỪNG theo dõi nếu
        con kiến đó đã chết (không "hồi sinh" theo dõi nhầm 1 con kiến mới
        sinh ra tình cờ dùng lại đúng ô nhớ đã trống)."""
        if not self.is_following():
            return
        colony, idx = self.follow_colony, self.follow_idx
        if idx is None or idx >= colony.n or not bool(colony.alive[idx]):
            self.stop_follow()
            return
        new_layer = int(colony.depth[idx])
        target_x = float(colony.x[idx])
        target_y = float(colony.y[idx])
        layer_changed = new_layer != self.current_layer
        self.current_layer = new_layer
        if layer_changed:
            # Kiến "dịch chuyển tức thời" giữa các tầng (đi thang máy lên/
            # xuống hầm - xem README) chứ KHÔNG đi liên tục như trên cùng
            # 1 tầng, nên tọa độ (x, y) của nó cũng đổi đột ngột luôn (từ
            # miệng hang sang hẳn 1 phòng khác). Nếu vẫn bám mượt dần như
            # bình thường, camera sẽ bị trễ lại phía sau vài khung hình,
            # khiến con kiến tạm thời RA KHỎI khung hình - nên ở đúng
            # khung hình đổi tầng này, camera phải bám THẲNG vào vị trí
            # mới ngay lập tức, không mượt dần.
            self.camera.cx = target_x
            self.camera.cy = target_y
        else:
            smooth = cfg.FOLLOW_CAMERA_SMOOTH
            self.camera.cx += (target_x - self.camera.cx) * smooth
            self.camera.cy += (target_y - self.camera.cy) * smooth

    def follow_status_text(self):
        """Chuỗi mô tả ngắn con kiến đang theo dõi, để HUD hiển thị."""
        if not self.is_following():
            return None
        colony, idx = self.follow_colony, self.follow_idx
        ten_to = "Doi thu" if colony is self.rival_colony else "Chinh"
        role = "Linh gac" if bool(colony.is_guard[idx]) else (
            "Y ta" if bool(colony.carrying[idx]) and int(colony.carry_type[idx]) == 0 else "Tho"
        )
        mang = ""
        if bool(colony.carrying[idx]):
            ct = int(colony.carry_type[idx])
            mang = " | dang mang: " + ("thuc an" if ct == 1 else "nuoc" if ct == 2 else "au trung/khac")
        return f"Theo doi: to {ten_to}, {role}, tang {int(colony.depth[idx])}, tuoi {int(colony.age[idx])} tick{mang}"

    # ------------------------------------------------------------------
    def set_tool(self, name):
        self.current_tool = None if self.current_tool == name else name
        for b in self.tool_buttons:
            b.active = (b.text_tool == self.current_tool)

    def toggle_pause(self, pause_btn):
        self.sim_paused = not self.sim_paused
        pause_btn.text = "Tiep tuc" if self.sim_paused else "Tam dung"
        pause_btn.active = self.sim_paused

    def cycle_speed(self, speed_btn):
        self.sim_speed = {1: 2, 2: 4, 4: 1}[self.sim_speed]
        speed_btn.text = f"Toc do: x{self.sim_speed}"

    def toggle_respawn(self, respawn_btn):
        self.food_respawn_enabled = not self.food_respawn_enabled
        respawn_btn.text = f"Tai sinh thuc an: {'BAT' if self.food_respawn_enabled else 'TAT'}"
        respawn_btn.active = self.food_respawn_enabled

    def toggle_grid(self, grid_btn):
        self.grid_visible = not self.grid_visible
        grid_btn.text = f"Luoi o vuong: {'BAT' if self.grid_visible else 'TAT'}"
        grid_btn.active = self.grid_visible

    def toggle_graph(self, graph_btn):
        self.graph_visible = not self.graph_visible
        graph_btn.text = f"Bieu do: {'HIEN' if self.graph_visible else 'AN'}"
        graph_btn.active = self.graph_visible

    def toggle_enemy_spawn(self, enemy_spawn_btn):
        self.enemy.auto_spawn_enabled = not self.enemy.auto_spawn_enabled
        enemy_spawn_btn.text = f"Ke thu tu nhien: {'BAT' if self.enemy.auto_spawn_enabled else 'TAT'}"
        enemy_spawn_btn.active = self.enemy.auto_spawn_enabled

    # ------------------------------------------------------------------
    def step_simulation(self):
        """1 tick mô phỏng: cập nhật 2 đàn, kẻ thù, tái sinh thức ăn, lấy
        mẫu lịch sử dân số cho biểu đồ. Gọi sim_speed lần mỗi khung hình."""
        self.colony.update(enemy=self.enemy, rival=self.rival_colony)
        self.rival_colony.update(enemy=self.enemy, rival=self.colony)
        self.enemy.update(self.ALL_COLONIES)
        if self.enemy.active:
            self.surface_world.deposit_danger(self.enemy.x, self.enemy.y)
        if self.food_respawn_enabled:
            self.food_respawn_tick += 1
            if self.food_respawn_tick % cfg.FOOD_RESPAWN_INTERVAL == 0:
                self.do_random_food_respawn()

        self.history_tick += 1
        if self.history_tick % cfg.HISTORY_SAMPLE_INTERVAL == 0:
            self.pop_history_main.append(int(self.colony.alive.sum()))
            self.pop_history_rival.append(int(self.rival_colony.alive.sum()))
            if len(self.pop_history_main) > cfg.HISTORY_MAX_POINTS:
                del self.pop_history_main[0]
                del self.pop_history_rival[0]
