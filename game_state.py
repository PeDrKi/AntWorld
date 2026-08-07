"""GameState: gom toàn bộ dữ liệu + logic điều khiển (không phải vẽ) vào 1
chỗ, để main.py chỉ còn là vòng lặp sự kiện pygame gọi vào đây, và các
module render_*.py/hud.py chỉ cần nhận `state` để đọc dữ liệu cần vẽ - thay
vì main.py cũ nhồi tất cả (world, colony, camera, toolbar, render, vòng
lặp...) vào 1 hàm main() 900 dòng dùng closures.
"""
import numpy as np
import pygame

import config as cfg
from world import SurfaceWorld, UndergroundWorld
from ants import AntColony
from enemy import EnemyManager
from camera import Camera2D


class GameState:
    def __init__(self):
        self.screen = pygame.display.set_mode((cfg.SCREEN_W, cfg.SCREEN_H))
        pygame.display.set_caption("Ant World 2D - tung lop / tung tang")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("arial", 16)
        self.font_small = pygame.font.SysFont("arial", 13)
        self.font_big = pygame.font.SysFont("arial", 22, bold=True)
        self.font_hud = pygame.font.SysFont("consolas", 15)

        self.CANVAS_H = cfg.SCREEN_H - cfg.TOOLBAR_H
        self.CENTER_X = cfg.SCREEN_W / 2.0
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

        # Thanh công cụ - danh sách Button; được hud.build_toolbar() điền vào
        self.buttons = []
        self.tool_buttons = []

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
