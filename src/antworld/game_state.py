"""GameState: gom toàn bộ dữ liệu + logic điều khiển (không phải vẽ) vào 1
chỗ, để main.py chỉ còn là vòng lặp sự kiện pygame gọi vào đây, và các
module render_*.py/hud.py chỉ cần nhận `state` để đọc dữ liệu cần vẽ - thay
vì main.py cũ nhồi tất cả (world, colony, camera, toolbar, render, vòng
lặp...) vào 1 hàm main() 900 dòng dùng closures.
"""
import os
import pickle
import sys

import numpy as np
import pygame

from . import config as cfg
from . import fonts
from .world import SurfaceWorld, UndergroundWorld
from .ants import AntColony
from .enemy import EnemyManager
from .invasion import InvasionManager
from .camera import Camera2D
from .sprite_manager import SpriteManager
from .maze_demo import MazeDemo

# Khi chạy bình thường từ source (src/antworld/game_state.py): assets/
# nằm ở THƯ MỤC GỐC dự án (2 cấp trên src/antworld/). Khi được đóng gói
# thành .exe bằng PyInstaller (chế độ --onefile), file được giải nén tạm
# vào thư mục sys._MEIPASS lúc chạy - phải trỏ theo đó thay vì theo vị trí
# file .py (không còn tồn tại trong bản .exe).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    ASSETS_DIR = os.path.join(sys._MEIPASS, "assets")
else:
    ASSETS_DIR = os.path.join(_PROJECT_ROOT, "assets")

# File lưu ván chơi PHẢI nằm cạnh file .exe thật (không phải thư mục tạm
# _MEIPASS - thư mục đó bị xóa ngay khi tắt app, lưu vào đó thì mất ngay).
# Khi chạy từ source thì lưu ở thư mục gốc dự án (cạnh assets/, main.py).
if getattr(sys, "frozen", False):
    SAVE_DIR = os.path.dirname(sys.executable)
else:
    SAVE_DIR = _PROJECT_ROOT
SAVE_PATH = os.path.join(SAVE_DIR, cfg.SAVE_FILE_NAME)

# Thư mục sprite TÙY CHỈNH do người chơi tự thêm vào (ảnh pixel art tự vẽ)
# - PHẢI đặt cạnh file .exe/.py thật (giống SAVE_DIR ở trên), KHÔNG phải
# trong _MEIPASS, vì người chơi cần TỰ TAY thêm/đổi file ảnh vào đây lúc
# đang dùng bản .exe đã đóng gói - thư mục _MEIPASS là thư mục tạm, không
# thể thêm file vào và bị xóa ngay khi tắt app.
SPRITES_DIR = os.path.join(SAVE_DIR, "assets", "sprites")


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

        # Dung font TrueType rieng dong goi san (fonts.py) thay vi SysFont
        # - dam bao chu tieng Viet co dau hien thi dung tren MOI may, ke
        # ca sau khi dong goi thanh .exe bang PyInstaller (xem fonts.py
        # de biet ly do chi tiet).
        self.font = fonts.get_font(16)
        self.font_small = fonts.get_font(13)
        self.font_big = fonts.get_font(22, bold=True)
        self.font_hud = fonts.get_mono_font(15)

        # Canvas mô phỏng giờ chiếm TOÀN BỘ cửa sổ (thanh công cụ/bảng
        # thống kê/biểu đồ không còn là dải cố định chiếm chỗ nữa - chúng
        # là các Panel NỔI TRÊN canvas, kéo/thu gọn được - xem hud.py)
        self.CANVAS_H = self.SCREEN_H
        self.CENTER_X = self.SCREEN_W / 2.0
        self.CENTER_Y = self.CANVAS_H / 2.0

        # --- Thế giới mô phỏng (logic không đổi so với bản 3D, chỉ khác ở
        # chỗ độ sâu giờ là số tầng rời rạc thay vì z liên tục) ---
        self.surface_world = SurfaceWorld(protected_nests=[cfg.NEST_POS])
        self.underground_world = UndergroundWorld(cfg.NEST_POS, "")
        # Giai đoạn lập tổ (xem khối config FOUNDING_* trong config.py) -
        # n_start PHẢI = 0 khi bật (chưa có thợ nào, đúng thực tế 1 tổ luôn
        # bắt đầu từ đúng 1 chúa).
        founding = cfg.FOUNDING_MODE_ENABLED
        main_n_start = 0 if founding else cfg.NUM_ANTS
        self.colony = AntColony(
            main_n_start, cfg.MAX_ANTS_PER_COLONY, self.surface_world, self.underground_world,
            cfg.NEST_POS, founding=founding,
        )
        self.enemy = EnemyManager()
        # Đàn kiến NGOẠI LAI - xuất hiện theo đợt để cướp phá rồi rút, KHÔNG
        # phải 1 tổ cố định thứ 2 (xem invasion.py). Chỉ có ĐÚNG 1 tổ trên
        # bản đồ (của người chơi).
        self.invasion = InvasionManager()
        self.ALL_COLONIES = [self.colony]

        self.camera = Camera2D(cfg.GRID_SIZE / 2.0, cfg.GRID_SIZE / 2.0, zoom=1.0)

        # Sprite pixel art TÙY CHỌN do người chơi tự thêm (xem sprite_manager.py
        # để biết quy ước đặt tên file) - nếu thư mục trống/không tồn tại,
        # mọi thứ vẫn vẽ vector như trước, không có gì thay đổi.
        self.sprites = SpriteManager(SPRITES_DIR)

        # tầng đang xem: 0 = mặt đất, >=1 = tầng ngầm
        self.current_layer = 0
        # Hiệu ứng chớp đen mờ dần MỖI KHI current_layer vừa đổi - xem
        # LAYER_FADE_TICKS trong config.py. 0 = không có lớp phủ (bình
        # thường); > 0 = đang mờ dần, đếm ngược mỗi khung hình render tới 0.
        self.layer_fade_tick = 0

        # Đang lập tổ (xem cfg.FOUNDING_MODE_ENABLED): mặc định camera +
        # tầng đang xem trỏ vào MẶT ĐẤT trống trơn - vì lúc này chưa có
        # con thợ nào để thấy, người chơi sẽ tưởng nhầm là game bị lỗi/
        # trống rỗng nếu không được đưa thẳng xuống chỗ chúa ngay từ đầu.
        # Tự động focus vào "Phòng chúa" (nơi con chúa DUY NHẤT đang ở,
        # xem draw_queen trong render_underground.py - luôn vẽ chúa bất kể
        # dân số) với zoom vừa đủ để nhìn rõ cả phòng.
        if self.colony.founding_phase:
            self.current_layer = cfg.DEPTH_QUEEN
            qx, qy = self.underground_world.queen_room
            self.camera.cx, self.camera.cy = float(qx), float(qy)
            # Zoom tính theo HỐC LẬP TỔ nhỏ (ROOM_RADIUS_FOUNDING_CHAMBER),
            # KHÔNG phải "Phòng chúa" đầy đủ (ROOM_RADIUS_QUEEN, to hơn gần
            # 5 lần) - xem giải thích trong config.py. Zoom gần hơn hẳn so
            # với phòng chúa trưởng thành vì hốc lúc này bé tí.
            self.camera.zoom = 3.8

        # --- Trạng thái công cụ / thời gian mô phỏng ---
        self.current_tool = None  # None | "food" | "enemy" | "rock" | "water" | "erase" | "follow"
        self.sim_paused = False
        self.sim_speed = 1
        self.food_respawn_enabled = True
        self.food_respawn_tick = 0
        self.grid_visible = True
        self.graph_visible = True
        self.frame_counter = 0
        self.history_tick = 0
        self.pop_history_main = []

        # --- Game Over (tổ tuyệt chủng) - xem check_alerts()/_trigger_game_over()
        # /restart_game() bên dưới - trước đây khi dân số về 0 game chỉ
        # hiện 1 toast rồi mô phỏng tiếp tục chạy vô nghĩa mãi mãi. ---
        self.game_over = False
        self.game_over_panel = None
        self.peak_population = 0  # dân số CAO NHẤT từng đạt được - cập
                                   # nhật mỗi tick trong step_simulation(),
                                   # dùng để tóm tắt lúc Game Over

        # --- Thông báo nổi bật (toast) - xem TOAST_* trong config.py ---
        self.toasts = []            # list các dict {msg, color, created}
        self._prev_alert_flags = {}  # trạng thái cảnh báo tick TRƯỚC, để chỉ
                                     # báo khi CHUYỂN từ bình thường -> có vấn
                                     # đề (không báo liên tục mỗi frame khi
                                     # tình trạng đó vẫn đang tiếp diễn)

        self.DRAG_TOOLS = {"food", "rock", "water", "erase"}
        self.DRAG_PLACE_INTERVAL_FRAMES = 6
        self.drag_cooldown = 0

        # --- Camera theo dõi 1 con kiến cụ thể ---
        # follow_colony: tham chiếu trực tiếp tới self.colony (đối tượng,
        # so sánh bằng "is"); follow_idx: vị
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

        # --- Tab "Demo mê cung": xem switch_tab()/visible_panels() và
        # maze_demo.py. Đây là 1 bản đồ MINH HỌA riêng biệt, world tách
        # hẳn khỏi surface_world/colony thật - đổi tab hay bấm "mê cung
        # mới" trong đó không ảnh hưởng gì tới ván chơi thật đang chạy
        # ngầm (mô phỏng vẫn tiếp tục dù đang xem tab nào).
        self.active_tab = "sim"  # "sim" | "maze"
        self.maze_demo = MazeDemo()
        self.maze_panel = None
        self.tab_panel = None

        # Toast giải thích tình huống lúc mới lập tổ - đưa RA CUỐI __init__
        # (không phải chỗ vừa focus camera ở trên) vì add_toast() cần
        # self.frame_counter đã tồn tại (khởi tạo muộn hơn phía trên).
        if self.colony.founding_phase:
            self.add_toast(
                "Chỉ có 1 chúa duy nhất - đang tự đẻ trứng bằng năng lượng "
                "dự trữ. Xem Tầng 3 (Phòng trứng) để theo dõi trứng.",
                color=(230, 190, 230),
            )

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

        from . import hud
        hud.build_toolbar(self)

    # ------------------------------------------------------------------
    def max_layer_overall(self):
        return self.underground_world.max_depth()

    def change_layer(self, delta):
        new_layer = int(np.clip(self.current_layer + delta, 0, self.max_layer_overall()))
        if new_layer != self.current_layer:
            self.current_layer = new_layer
            self.trigger_layer_fade()

    def set_layer(self, target):
        """Nhảy THẲNG tới 1 tầng cụ thể (khác với change_layer() vốn CỘNG
        DỒN theo bước) - dùng cho mini-map tầng (bấm trực tiếp vào 1 ô)."""
        new_layer = int(np.clip(target, 0, self.max_layer_overall()))
        if new_layer != self.current_layer:
            self.stop_follow()
            self.current_layer = new_layer
            self.trigger_layer_fade()

    def trigger_layer_fade(self):
        """Bắt đầu (hoặc khởi động lại nếu đang giữa chừng) hiệu ứng chớp
        đen mờ dần - gọi NGAY SAU KHI current_layer vừa đổi giá trị, dù đổi
        bằng cách nào (phím tắt, lăn chuột, hay camera tự bám theo kiến)."""
        self.layer_fade_tick = cfg.LAYER_FADE_TICKS

    def advance_layer_fade(self):
        """Gọi 1 lần mỗi khung hình render (main.py) để đếm ngược hiệu ứng."""
        if self.layer_fade_tick > 0:
            self.layer_fade_tick -= 1

    def layer_fade_alpha(self):
        """Độ mờ (0-255) của lớp phủ đen hiện tại - 0 nghĩa là không vẽ gì
        (bình thường). Dùng easing bậc 2 (tick^2) thay vì tuyến tính để cảm
        giác mượt hơn: mờ NHANH lúc mới đổi tầng (gây chú ý ngay), rồi CHẬM
        dần khi gần hiện rõ hoàn toàn tầng mới (không bị "hụt" đột ngột)."""
        if cfg.LAYER_FADE_TICKS <= 0 or self.layer_fade_tick <= 0:
            return 0
        t = self.layer_fade_tick / cfg.LAYER_FADE_TICKS
        return int(255 * (t * t))

    # ------------------------------------------------------------------
    # Hàm hỗ trợ đặt thức ăn / tái sinh (thuần logic, không cần entity
    # riêng như bản Ursina - pygame vẽ lại toàn bộ mỗi khung hình)
    # ------------------------------------------------------------------
    def place_food_at(self, gx, gy, amount=8.0, food_type=None):
        gx = int(np.clip(gx, 0, cfg.GRID_SIZE - 1))
        gy = int(np.clip(gy, 0, cfg.GRID_SIZE - 1))
        if self.surface_world.terrain[gx, gy] != cfg.TERRAIN_EMPTY:
            return  # ô đã có đá/nước - không cho thức ăn mọc đè lên
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
        if tool in ("food", "enemy", "rock", "water") and layer != 0:
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
        elif tool == "rock":
            # Đặt ĐÚNG 1 ô đá (add_rock_cell), KHÔNG dùng add_obstacle với
            # bán kính 1.4 như trước - bán kính đó tô hẳn 1 khối tròn 5 ô
            # (hình dấu cộng) chỉ trong 1 lần bấm, trái với kỳ vọng "1 lần
            # đặt = 1 ô". Vì đây là DRAG_TOOLS (rê chuột đặt liên tục), rê
            # qua nhiều ô sẽ tự nối thành 1 bức tường dài - đúng tinh thần
            # "đá = từng ô một, ghép thành tường" như lúc sinh thế giới.
            self.surface_world.add_rock_cell(int(sim_x), int(sim_y))
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
                # Ở tầng ngầm không còn phòng tự đào để xóa (đã bỏ chức
                # năng đào phòng) - "Xóa" ở đây chỉ còn tác dụng loại bỏ
                # kiến đang đứng gần điểm bấm (không ảnh hưởng 7 phòng gốc
                # vì phòng gốc không phải là kiến, không bị xóa được).
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
            self.trigger_layer_fade()
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
        role = "Linh gac" if bool(colony.is_guard[idx]) else (
            "Y ta" if bool(colony.carrying[idx]) and int(colony.carry_type[idx]) == 0 else "Tho"
        )
        mang = ""
        if bool(colony.carrying[idx]):
            ct = int(colony.carry_type[idx])
            mang = " | dang mang: " + ("thuc an" if ct == 1 else "nuoc" if ct == 2 else "au trung/khac")
        return f"Theo doi: {role}, tang {int(colony.depth[idx])}, tuoi {int(colony.age[idx])} tick{mang}"

    # ------------------------------------------------------------------
    def switch_tab(self, name):
        """Chuyển giữa tab \"Mo phong\" (ván chơi chính) và \"Demo me cung\"
        (minh họa thuật toán tìm đường - xem maze_demo.py, world hoàn
        toàn tách biệt). Mô phỏng chính vẫn chạy ngầm bình thường ở cả 2
        tab, chỉ phần HIỂN THỊ và các panel/công cụ tương ứng đổi theo."""
        if name == self.active_tab:
            return
        self.active_tab = name
        self.stop_follow()
        if name == "sim":
            self.current_tool = None
        elif name == "maze":
            self.maze_demo.ensure_generated()

    def visible_panels(self):
        """Danh sách panel THỰC SỰ hiển thị (và nhận sự kiện chuột) ở tab
        hiện tại - tab_panel (nút chuyển tab) luôn hiện; các panel còn lại
        tùy thuộc active_tab, xem hud.build_toolbar().

        Khi game_over=True, panel Game Over được CHÈN LÊN ĐẦU danh sách -
        đứng trước mọi panel khác nên click vào nút "Chơi lại" của nó
        LUÔN được xử lý trước (xem __main__.py: vòng lặp dừng lại ở panel
        ĐẦU TIÊN xử lý được sự kiện chuột)."""
        if self.active_tab == "maze":
            panels = [p for p in (self.tab_panel, self.maze_panel) if p is not None]
        else:
            panels = [p for p in (self.tab_panel, self.toolbar_panel, self.stats_panel,
                                   self.graph_panel, getattr(self, "layer_map_panel", None)) if p is not None]
        if self.game_over and self.game_over_panel is not None:
            panels = [self.game_over_panel] + panels
        return panels

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
    # Thông báo nổi bật (toast) - hiện cố định góc màn hình, không phụ
    # thuộc panel nào, tự biến mất sau vài giây. Dùng cho cả cảnh báo sự
    # kiện quan trọng LẪN xác nhận lưu/tải ván chơi.
    # ------------------------------------------------------------------
    def add_toast(self, message, color=(235, 235, 235)):
        self.toasts.append({"msg": message, "color": color, "created": self.frame_counter})
        if len(self.toasts) > cfg.TOAST_MAX_VISIBLE:
            self.toasts = self.toasts[-cfg.TOAST_MAX_VISIBLE:]

    def update_toasts(self):
        """Gọi 1 lần mỗi khung hình render - dọn các toast đã hết hạn."""
        if not self.toasts:
            return
        self.toasts = [
            t for t in self.toasts if self.frame_counter - t["created"] < cfg.TOAST_TTL_FRAMES
        ]

    def check_alerts(self):
        """So sánh các tình trạng quan trọng (đói/khát/kẻ thù/đàn ngoại lai/
        tuyệt chủng) với khung hình TRƯỚC - chỉ bắn ra 1 toast đúng lúc
        CHUYỂN từ bình thường sang có vấn đề, không báo liên tục mỗi khung
        hình trong lúc tình trạng đó vẫn đang tiếp diễn (xem
        _prev_alert_flags). Gọi 1 lần mỗi khung hình render, SAU khi mô
        phỏng đã chạy xong các tick của khung hình đó."""
        c = self.colony.counts()

        col_bad = (255, 95, 90)
        col_warn = (255, 190, 70)

        flags = {
            "main_starving": (c["is_starving"], "To dang doi thuc an!", col_bad),
            "main_dehydrated": (c["is_dehydrated"], "To dang khat nuoc!", col_warn),
            "enemy_active": (self.enemy.active, "Ke thu xuat hien tren mat dat!", col_warn),
            "invasion_active": (self.invasion.active, "Dan kien ngoai lai dang tien ve to!", col_bad),
            # LƯU Ý: loại trừ founding_phase - lúc mới bắt đầu lập tổ, dân
            # số THỢ luôn bằng 0 là chuyện BÌNH THƯỜNG (chỉ có chúa, chưa
            # nở con nào - xem AntColony.founding_phase), KHÔNG phải tuyệt
            # chủng. Nếu không loại trừ, bật chế độ lập tổ (FOUNDING_MODE_
            # ENABLED) sẽ khiến toast "Tổ đã tuyệt chủng!" bắn ra NGAY LÚC
            # vừa mở ván chơi mới.
            "main_extinct": (c["population"] == 0 and not c["founding_phase"], "To da tuyet chung!", col_bad),
        }
        for key, (active, msg, color) in flags.items():
            was_active = self._prev_alert_flags.get(key, False)
            if active and not was_active:
                self.add_toast(msg, color)
                if key == "main_extinct" and not self.game_over:
                    self._trigger_game_over()
            self._prev_alert_flags[key] = active

    def _trigger_game_over(self):
        """Kích hoạt màn hình Game Over khi tổ CHÍNH THỨC tuyệt chủng (dân
        số về 0 SAU KHI đã qua giai đoạn lập tổ - xem điều kiện main_extinct
        ở check_alerts()). Dừng hẳn mô phỏng (người chơi vẫn xem được cảnh
        vật/thành quả cuối cùng, chỉ không chạy tiếp nữa) và dựng sẵn 1
        panel tóm tắt + nút "Chơi lại" (xem hud.build_game_over_panel).

        Trước đây hành vi duy nhất khi tuyệt chủng là hiện 1 toast rồi mô
        phỏng vẫn chạy tiếp mãi mãi ở trạng thái 0 kiến - không có lối ra,
        không có cách bắt đầu lại - đây là bản vá cho khoảng trống đó."""
        self.game_over = True
        self.sim_paused = True
        self.stop_follow()
        c = self.colony.counts()
        self._game_over_stats = {
            "peak_population": self.peak_population,
            "ticks_survived": self.history_tick,
            "total_births": c.get("total_births", 0),
            "total_deaths": c.get("total_deaths", 0),
            "total_food_collected": c.get("total_food_collected", 0.0),
            "waves_survived": max(0, self.invasion.wave_number - (1 if self.invasion.active else 0)),
            "invaders_killed": getattr(self.invasion, "total_invaders_killed", 0),
        }
        from . import hud
        hud.build_game_over_panel(self)

    def restart_game(self):
        """Bắt đầu lại TOÀN BỘ ván chơi từ đầu (như vừa mở game) - gọi khi
        người chơi bấm nút "Chơi lại tu dau" trên màn hình Game Over. Giữ
        nguyên kích thước cửa sổ hiện tại (người chơi có thể đã tự kéo
        giãn) thay vì quay về kích thước mặc định trong config.py - tái sử
        dụng handle_resize() để vừa khôi phục đúng kích thước vừa dựng lại
        toàn bộ toolbar/panel cho khớp (handle_resize gọi hud.build_toolbar
        bên trong)."""
        old_w, old_h = self.SCREEN_W, self.SCREEN_H
        self.__init__()
        self.handle_resize(old_w, old_h)

    # ------------------------------------------------------------------
    # Lưu / tải ván chơi - dùng pickle để lưu nguyên trạng thái mô phỏng
    # (2 đàn kiến, thế giới mặt đất, kẻ thù...) vào 1 file DUY NHẤT cạnh
    # file chạy (main.py hoặc .exe) - lưu đè lần sau, không cần chọn tên.
    # KHÔNG lưu bất kỳ thứ gì thuộc giao diện (panel, nút, font, màn hình
    # pygame...) - chỉ lưu đúng phần "thế giới mô phỏng" thuần dữ liệu.
    # ------------------------------------------------------------------
    def save_game(self):
        data = {
            "version": 2,   # v2: bỏ tổ đối thủ cố định, thêm đàn kiến ngoại
                             # lai (invasion) - KHÔNG tương thích ngược với
                             # file lưu v1 (xem load_game)
            "colony": self.colony,
            "surface_world": self.surface_world,
            "enemy": self.enemy,
            "invasion": self.invasion,
            "camera_cx": self.camera.cx,
            "camera_cy": self.camera.cy,
            "camera_zoom": self.camera.zoom,
            "current_layer": self.current_layer,
            "sim_paused": self.sim_paused,
            "sim_speed": self.sim_speed,
            "food_respawn_enabled": self.food_respawn_enabled,
            "food_respawn_tick": self.food_respawn_tick,
            "history_tick": self.history_tick,
            "pop_history_main": list(self.pop_history_main),
        }
        try:
            tmp_path = SAVE_PATH + ".tmp"
            with open(tmp_path, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp_path, SAVE_PATH)  # ghi ra file tạm rồi mới đổi
                                              # tên - tránh hỏng file lưu cũ
                                              # nếu quá trình ghi bị ngắt
                                              # giữa chừng (mất điện, crash)
            self.add_toast("Da luu van choi", (140, 230, 150))
            return True
        except Exception as e:
            self.add_toast(f"Loi khi luu: {e}", (255, 95, 90))
            return False

    def load_game(self):
        if not os.path.exists(SAVE_PATH):
            self.add_toast("Chua co van choi nao duoc luu", (255, 190, 70))
            return False
        try:
            with open(SAVE_PATH, "rb") as f:
                data = pickle.load(f)
            if data.get("version", 1) < 2:
                # File lưu từ bản CŨ (còn tổ đối thủ cố định) - không tương
                # thích với cấu trúc ván chơi hiện tại (chỉ 1 tổ + đàn kiến
                # ngoại lai theo đợt), từ chối tải thay vì tải lỗi/crash.
                self.add_toast(
                    "File luu tu ban cu khong con tuong thich - hay bat dau van moi",
                    (255, 190, 70),
                )
                return False
            self.colony = data["colony"]
            self.surface_world = data["surface_world"]
            self.underground_world = self.colony.underground
            self.enemy = data["enemy"]
            self.invasion = data.get("invasion", InvasionManager())
            self.ALL_COLONIES = [self.colony]
            self.camera.cx = data["camera_cx"]
            self.camera.cy = data["camera_cy"]
            self.camera.zoom = data["camera_zoom"]
            self.current_layer = data["current_layer"]
            self.sim_paused = data["sim_paused"]
            self.sim_speed = data["sim_speed"]
            self.food_respawn_enabled = data["food_respawn_enabled"]
            self.food_respawn_tick = data.get("food_respawn_tick", 0)
            self.history_tick = data.get("history_tick", 0)
            self.pop_history_main = list(data.get("pop_history_main", []))
            self.stop_follow()  # tránh tham chiếu "lơ lửng" tới đàn kiến cũ
            self._prev_alert_flags = {}  # để tình trạng cảnh báo tính lại
                                          # đúng từ đầu, không báo nhầm ngay
                                          # khung hình đầu sau khi tải
            self.add_toast("Da tai van choi", (140, 230, 150))
            return True
        except Exception as e:
            self.add_toast(f"Loi khi tai: {e}", (255, 95, 90))
            return False

    # ------------------------------------------------------------------
    def step_simulation(self):
        """1 tick mô phỏng: cập nhật đàn kiến, kẻ thù tự nhiên, đàn ngoại
        lai (nếu đang có đợt xâm nhập), tái sinh thức ăn, lấy mẫu lịch sử
        dân số cho biểu đồ. Gọi sim_speed lần mỗi khung hình."""
        was_founding = self.colony.founding_phase
        self.colony.update(enemy=self.enemy, invasion=self.invasion)
        if was_founding and not self.colony.founding_phase:
            # Vừa chuyển giao xong (đủ FOUNDING_NANITIC_TARGET thợ đầu
            # tiên) - báo cho người chơi biết, vì họ đang xem "Phòng chúa"
            # (đã tự focus camera vào đó lúc mới mở game, xem __init__) và
            # có thể không để ý dân số vừa đổi trong bảng thống kê.
            self.add_toast(
                "Lứa thợ đầu tiên đã trưởng thành - tổ chính thức hoạt động!",
                color=(190, 230, 190),
            )

        was_invasion_active = self.invasion.active
        self.invasion.update(self.colony)
        if was_invasion_active and not self.invasion.active:
            # Đợt xâm nhập vừa kết thúc (rút lui hết hoặc bị đánh bại hoàn
            # toàn) - báo kết quả để người chơi không phải tự đoán.
            if self.invasion.total_invaders_killed > 0 and self.invasion.total_food_stolen < 0.01 \
                    and self.invasion.total_brood_stolen == 0:
                self.add_toast("Da danh lui dan kien ngoai lai!", color=(190, 230, 190))
            else:
                self.add_toast("Dan kien ngoai lai da rut lui, mang theo chien loi pham", color=(255, 190, 70))

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
            if len(self.pop_history_main) > cfg.HISTORY_MAX_POINTS:
                del self.pop_history_main[0]

        # Dùng trực tiếp np.sum(alive) (rẻ) thay vì colony.counts() (tính
        # nhiều số liệu khác không cần ở đây) - theo dõi dân số CAO NHẤT
        # từng đạt được, hiển thị lại lúc Game Over (xem _trigger_game_over)
        # để người chơi thấy được thành quả tốt nhất, không chỉ con số 0
        # lúc tổ vừa tuyệt chủng.
        pop_now = int(self.colony.alive.sum())
        if pop_now > self.peak_population:
            self.peak_population = pop_now
