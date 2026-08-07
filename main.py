"""Ant World 3D - bản prototype.

Toàn bộ thế giới (mặt đất + hầm ngầm) được hiển thị như 1 khối hộp trong
suốt kiểu "bể nuôi kiến" (formicarium bằng kính) mà bạn xoay/zoom tự do.

Chạy: python main.py

Điều khiển camera (mặc định của Ursina EditorCamera):
  - Giữ CHUỘT PHẢI + di chuột : xoay camera quanh thế giới
  - Lăn chuột                 : zoom vào/ra
  - Giữ CHUỘT PHẢI + W/A/S/D  : bay ngang trong lúc xoay
  - Phím G                    : bật/tắt độ trong suốt của mặt đất
  - Esc                       : thoát

Can thiệp vào thế giới (thanh công cụ dưới màn hình):
  - "Dat thuc an" : chọn rồi CLICK CHUỘT TRÁI lên mặt đất để rải thức ăn
  - "Tha ke thu"  : chọn rồi click để thả kẻ thù ngay tại điểm đó
  - "Dao phong"   : chọn rồi click để đào 1 phòng hầm mới tại điểm đó
  - "Dat da"      : chọn rồi click để đặt 1 cụm đá (chặn đường kiến)
  - "Dat nuoc"    : chọn rồi click để đặt 1 vũng nước (cũng chặn đường)
  - "Tam dung" / "Toc do xN": điều khiển thời gian mô phỏng
  - "Tai sinh thuc an: BAT/TAT": bật/tắt việc thức ăn mới tự xuất hiện
    ngẫu nhiên theo chu kỳ (tắt đi nếu bạn muốn tự kiểm soát hoàn toàn
    nguồn thức ăn bằng công cụ "Dat thuc an")
"""
from ursina import *
import numpy as np
from PIL import Image

import config as cfg
from world import SurfaceWorld, UndergroundWorld
from ants import AntColony
from enemy import EnemyManager


def rgb255(r, g, b, a=255):
    """Ursina's color.rgb()/color.rgba() cần giá trị 0-1, KHÔNG tự chia
    cho 255. Hàm này cho phép dùng thang màu quen thuộc 0-255."""
    return color.rgba(r / 255, g / 255, b / 255, a / 255)

app = Ursina(title="Ant World 3D", borderless=False, size=(cfg.SCREEN_W, cfg.SCREEN_H))
window.color = rgb255(18, 18, 24)
Sky()

# ---------------------------------------------------------------------
# Ánh sáng cơ bản để khối 3D có chiều sâu, đổ bóng nhẹ
# ---------------------------------------------------------------------
DirectionalLight(rotation=(45, -45, 0), shadows=False)
AmbientLight(color=rgb255(200, 200, 210, 140))

# ---------------------------------------------------------------------
# Thế giới mô phỏng (logic không đổi so với bản trước, chỉ thêm trục Z)
# ---------------------------------------------------------------------
surface_world = SurfaceWorld(protected_nests=[cfg.NEST_POS, cfg.RIVAL_NEST_POS])
underground_world = UndergroundWorld(cfg.NEST_POS, "")
colony = AntColony(cfg.NUM_ANTS, surface_world, underground_world, cfg.NEST_POS)

# Tổ đối thủ - cùng bản đồ, cùng nguồn thức ăn/nước (cạnh tranh thật sự)
rival_underground = UndergroundWorld(cfg.RIVAL_NEST_POS, "Doi thu - ")
rival_colony = AntColony(cfg.NUM_RIVAL_ANTS, surface_world, rival_underground, cfg.RIVAL_NEST_POS)

enemy = EnemyManager()
ALL_COLONIES = [colony, rival_colony]

CENTER = cfg.GRID_SIZE / 2.0


def sim_to_world(x, y, z):
    """Đổi tọa độ mô phỏng (x,y ngang, z sâu-âm) sang tọa độ Ursina
    (x ngang, y lên/xuống, z ngang còn lại)."""
    return (float(x) - CENTER, float(z), float(y) - CENTER)


def world_to_sim(wx, wy, wz):
    """Chiều ngược lại của sim_to_world - dùng để đổi điểm click chuột
    (tọa độ Ursina) về tọa độ lưới mô phỏng (x, y)."""
    return (wx + CENTER, wz + CENTER, wy)


# ---------------------------------------------------------------------
# Khối kính bao quanh toàn bộ thế giới (như bể nuôi kiến)
# ---------------------------------------------------------------------
# TẠM TẮT (SHOW_GLASS_BOX = False) để cô lập nguyên nhân gây trắng màn
# hình - nghi ngờ khối hộp trong suốt khổng lồ này kết hợp với vị trí
# camera là thủ phạm. Sau khi xác nhận phần còn lại hiển thị ổn, đổi lại
# thành True để bật lại.
SHOW_GLASS_BOX = False

if SHOW_GLASS_BOX:
    GLASS_TOP = 3.0
    GLASS_BOTTOM = -cfg.WORLD_DEPTH
    glass_height = GLASS_TOP - GLASS_BOTTOM
    glass_box = Entity(
        model="cube",
        scale=(cfg.GRID_SIZE + 2, glass_height, cfg.GRID_SIZE + 2),
        position=(0, (GLASS_TOP + GLASS_BOTTOM) / 2, 0),
        color=rgb255(255, 255, 255, 16),
        double_sided=True,
    )


# ---------------------------------------------------------------------
# Mặt đất - có thể bấm phím G để chuyển giữa đục/trong suốt
# ---------------------------------------------------------------------
def make_grid_texture(tile_px=48, border_px=2):
    """Tạo 1 texture ô vuông TRONG SUỐT (alpha=0) trừ viền đen mảnh quanh
    mép (alpha=255) - dùng cho 1 LỚP RIÊNG nằm trên mặt đất, để đường viền
    lưới luôn hiển thị rõ ràng dù mặt đất có đang bật độ trong suốt (phím
    G) hay không. Viền 2px/48px (~4.2%) = khoảng 1/3 độ dày so với bản
    trước (4px/32px = 12.5%) - tile_px tăng lên 48 để giữ độ nét khi viền
    mỏng hơn, tránh bị răng cưa quá thô."""
    arr = np.zeros((tile_px, tile_px, 4), dtype=np.uint8)
    arr[:border_px, :, 3] = 255
    arr[-border_px:, :, 3] = 255
    arr[:, :border_px, 3] = 255
    arr[:, -border_px:, 3] = 255
    return Image.fromarray(arr, mode="RGBA")


GRID_TEXTURE = Texture(make_grid_texture(), filtering=None)

ground = Entity(
    model="plane",
    scale=(cfg.GRID_SIZE, 1, cfg.GRID_SIZE),
    position=(0, 0, 0),
    color=rgb255(205, 178, 132, 235),
    double_sided=True,
    collider="box",
)
# Lớp lưới ô vuông RIÊNG, nằm ngay trên mặt đất - LUÔN hiển thị đầy đủ độ
# rõ nét (alpha 255) kể cả khi bạn bấm phím G làm mặt đất trong suốt, vì
# đây là 1 entity độc lập, không dùng chung độ trong suốt với ground.
ground_grid_lines = Entity(
    model="plane",
    scale=(cfg.GRID_SIZE, 1, cfg.GRID_SIZE),
    position=(0, 0.01, 0),
    color=color.black,
    texture=GRID_TEXTURE,
    texture_scale=(cfg.GRID_SIZE, cfg.GRID_SIZE),
    double_sided=True,
)
GROUND_OPAQUE_ALPHA = 235
GROUND_TRANSPARENT_ALPHA = 55
ground_transparent = False

# Lỗ tổ trên mặt đất (tổ chính)
nest_hole = Entity(
    model=Cylinder(resolution=12, radius=1.6, height=0.12),
    position=sim_to_world(cfg.NEST_POS[0], cfg.NEST_POS[1], 0.02),
    color=rgb255(30, 22, 14),
)
# Lỗ tổ đối thủ - viền hơi đỏ để phân biệt từ xa
rival_nest_hole = Entity(
    model=Cylinder(resolution=12, radius=1.6, height=0.12),
    position=sim_to_world(cfg.RIVAL_NEST_POS[0], cfg.RIVAL_NEST_POS[1], 0.02),
    color=rgb255(45, 20, 18),
)

# ---------------------------------------------------------------------
# Các phòng dưới hầm - vẽ bằng hàm dùng lại được (cho cả lúc khởi tạo lẫn
# lúc người chơi đào thêm phòng mới bằng công cụ)
# ---------------------------------------------------------------------
def create_room_entity(name, center, radius, rgb):
    room_ent = Entity(
        model="sphere",
        scale=radius * 2,
        position=sim_to_world(*center),
        color=rgb255(rgb[0], rgb[1], rgb[2], 215),
    )
    # QUAN TRỌNG: không gắn Text làm con của room_ent, vì tỉ lệ (scale) của
    # room_ent sẽ nhân dồn vào tỉ lệ chữ và có thể tạo ra 1 mặt phẳng chữ
    # khổng lồ che kín màn hình. Gắn thẳng vào 'scene' và tự tính vị trí.
    label_pos = sim_to_world(center[0], center[1], center[2])
    label_pos = (label_pos[0], label_pos[1] + radius + 1.2, label_pos[2])
    Text(
        parent=scene,
        text=name,
        position=label_pos,
        scale=3,
        billboard=True,
        origin=(0, 0),
        color=color.white,
    )
    return room_ent


def create_corridor_entity(a, b):
    p1 = sim_to_world(*a)
    p2 = sim_to_world(*b)
    return Entity(
        model=Mesh(vertices=[p1, p2], mode="line", thickness=6),
        color=rgb255(160, 128, 92, 230),
    )


def create_queen_visual(underground, rgb):
    """Hình kiến chúa thật thay vì chỉ là 1 quả cầu trang trí - bụng to
    đặc trưng (phần sinh sản) + đầu/ngực nhỏ hơn phía trước."""
    qx, qy, qz = underground.queen_room
    px, py, pz = sim_to_world(qx, qy, qz)
    Entity(  # bụng to
        model="sphere",
        scale=(1.9, 1.4, 2.8),
        position=(px, py + 0.2, pz + 1.3),
        color=rgb255(rgb[0], rgb[1], rgb[2], 255),
    )
    Entity(  # đầu + ngực
        model="sphere",
        scale=(1.1, 1.0, 1.3),
        position=(px, py + 0.2, pz - 1.2),
        color=rgb255(rgb[0] - 20, rgb[1] - 10, rgb[2] - 20, 255),
    )


for name, center, radius, rgb in underground_world.rooms:
    create_room_entity(name, center, radius, rgb)
for a, b in underground_world.corridors:
    create_corridor_entity(a, b)
create_queen_visual(underground_world, (150, 70, 160))

for name, center, radius, rgb in rival_underground.rooms:
    create_room_entity(name, center, radius, rgb)
for a, b in rival_underground.corridors:
    create_corridor_entity(a, b)
create_queen_visual(rival_underground, (170, 60, 60))

# ---------------------------------------------------------------------
# Địa hình: đá (chặn đường) và nước (chặn đường, màu xanh trong suốt) -
# vẽ bằng hàm dùng lại được cho cả lúc khởi tạo lẫn khi người chơi tự đặt
# thêm bằng công cụ
# ---------------------------------------------------------------------
def create_terrain_entity(terrain_type, cx, cy, radius):
    if terrain_type == cfg.TERRAIN_ROCK:
        # vài khối đá nhỏ xếp lệch nhau cho tự nhiên, thay vì 1 khối tròn đều
        rng_local = np.random.default_rng(int(cx * 1000 + cy))
        n_chunks = max(3, int(radius * 3))
        for _ in range(n_chunks):
            ox = rng_local.uniform(-radius * 0.6, radius * 0.6)
            oy = rng_local.uniform(-radius * 0.6, radius * 0.6)
            s = rng_local.uniform(0.7, 1.5)
            Entity(
                model="cube",
                scale=(s, s * rng_local.uniform(0.6, 1.1), s),
                position=sim_to_world(cx + ox, cy + oy, 0.0),
                rotation=(0, rng_local.uniform(0, 360), 0),
                color=rgb255(120, 118, 112, 255),
            )
    else:  # TERRAIN_WATER
        Entity(
            model=Cylinder(resolution=16, radius=radius, height=0.06),
            position=sim_to_world(cx, cy, 0.05),
            color=rgb255(70, 140, 200, 175),
        )


for terrain_type, cx, cy, radius in surface_world.terrain_features:
    create_terrain_entity(terrain_type, cx, cy, radius)

# ---------------------------------------------------------------------
# Thức ăn trên mặt đất (lấy mẫu thưa để không tạo quá nhiều entity)
# ---------------------------------------------------------------------
def food_color_for(gx, gy):
    ftype = int(surface_world.food_type[gx, gy])
    rgb = cfg.FOOD_TYPE_COLOR.get(ftype, (60, 150, 60))
    return rgb255(rgb[0], rgb[1], rgb[2])


food_entities = {}
FOOD_SAMPLE_STEP = 2
for gx in range(0, cfg.GRID_SIZE, FOOD_SAMPLE_STEP):
    for gy in range(0, cfg.GRID_SIZE, FOOD_SAMPLE_STEP):
        if surface_world.food[gx, gy] > 0.5:
            ent = Entity(
                model="sphere",
                scale=0.55,
                position=sim_to_world(gx, gy, 0.2),
                color=food_color_for(gx, gy),
            )
            food_entities[(gx, gy)] = ent


def ensure_food_entity(gx, gy):
    """Đảm bảo ô (gx, gy) có entity thức ăn hiển thị - tạo mới nếu chưa có,
    hoặc bật lại + cập nhật màu nếu đã có sẵn. Dùng chung cho: thức ăn lúc
    khởi tạo, thức ăn người chơi tự đặt, và thức ăn tái sinh ngẫu nhiên."""
    if (gx, gy) not in food_entities:
        food_entities[(gx, gy)] = Entity(
            model="sphere",
            scale=0.55,
            position=sim_to_world(gx, gy, 0.2),
            color=food_color_for(gx, gy),
        )
    else:
        ent = food_entities[(gx, gy)]
        ent.enabled = True
        ent.color = food_color_for(gx, gy)


def place_food_at(gx, gy, amount=8.0, food_type=None):
    """Đặt thức ăn tại 1 ô lưới cụ thể (dùng cho công cụ click chuột) -
    tạo entity hiển thị nếu ô đó chưa có sẵn. Nếu không chỉ định loại,
    chọn ngẫu nhiên theo tỉ lệ giống lúc thế giới khởi tạo."""
    gx = int(np.clip(gx, 0, cfg.GRID_SIZE - 1))
    gy = int(np.clip(gy, 0, cfg.GRID_SIZE - 1))
    if food_type is None:
        types = list(cfg.FOOD_TYPE_WEIGHTS.keys())
        weights = list(cfg.FOOD_TYPE_WEIGHTS.values())
        food_type = int(np.random.choice(types, p=weights))
    surface_world.food[gx, gy] += amount
    surface_world.food_type[gx, gy] = food_type
    ensure_food_entity(gx, gy)


def do_random_food_respawn():
    """Tái sinh 1 cụm thức ăn ngẫu nhiên MỚI trên bản đồ (khác với
    place_food_at - đây là 1 cụm nhỏ lan ra vài ô xung quanh tâm, giống lúc
    thế giới khởi tạo) và đảm bảo có entity hiển thị (trước đây bị thiếu
    bước này nên thức ăn tái sinh không hiện ra được trên màn hình)."""
    cx, cy = surface_world.respawn_random_cluster()
    r = int(round(cfg.FOOD_CLUSTER_RADIUS))
    for gx in range(max(0, cx - r), min(cfg.GRID_SIZE, cx + r + 1)):
        for gy in range(max(0, cy - r), min(cfg.GRID_SIZE, cy + r + 1)):
            ensure_food_entity(gx, gy)

# ---------------------------------------------------------------------
# Kiến - tạo sẵn 1 entity cho mỗi con, mỗi frame chỉ cập nhật vị trí/màu.
# Lính (thợ lớn) được vẽ to hơn thợ nhỏ ngay từ lúc khởi tạo entity.
# ---------------------------------------------------------------------
def make_ant_entities(colony_obj, base_color):
    entities = []
    for i in range(colony_obj.n):
        is_major = colony_obj.role[i] == cfg.ROLE_MAJOR
        scale = 0.3 * (cfg.MAJOR_SIZE_SCALE if is_major else 1.0)
        entities.append(Entity(model="sphere", scale=scale, color=base_color))
    return entities


ant_entities = make_ant_entities(colony, color.black)
ant_render_state = np.full(colony.n, -2, dtype=np.int8)  # -2 = chưa gán lần nào

COLOR_SEARCH = rgb255(25, 25, 25)
COLOR_CARRY_SURFACE = rgb255(215, 120, 30)
COLOR_UNDERGROUND = rgb255(220, 220, 220)
COLOR_CARRY_UNDERGROUND = rgb255(235, 190, 70)

# Tổ đối thủ - tông màu đỏ/nâu để phân biệt rõ với tổ chính (đen/cam)
rival_ant_entities = make_ant_entities(rival_colony, rgb255(120, 30, 25))
rival_ant_render_state = np.full(rival_colony.n, -2, dtype=np.int8)
RIVAL_COLOR_SEARCH = rgb255(120, 30, 25)
RIVAL_COLOR_CARRY_SURFACE = rgb255(230, 140, 40)
RIVAL_COLOR_UNDERGROUND = rgb255(200, 160, 155)
RIVAL_COLOR_CARRY_UNDERGROUND = rgb255(240, 170, 60)

# ---------------------------------------------------------------------
# Kẻ thù tự nhiên - hình khác biệt (bát diện) + màu đỏ để dễ nhận ra ngay
# ---------------------------------------------------------------------
enemy_entity = Entity(
    model="diamond",
    scale=1.4,
    color=rgb255(220, 30, 30),
    enabled=False,
)

# ---------------------------------------------------------------------
# Thanh công cụ can thiệp (đặt thức ăn / thả kẻ thù / đào phòng) +
# điều khiển thời gian (tạm dừng / tăng tốc)
# ---------------------------------------------------------------------
current_tool = None   # None | "food" | "enemy" | "dig"
sim_paused = False
sim_speed = 1          # 1, 2, hoặc 4 lần tốc độ mỗi khung hình
food_respawn_enabled = True   # bật/tắt tái sinh thức ăn ngẫu nhiên theo "mùa"
food_respawn_tick = 0

TOOL_BUTTON_COLOR = rgb255(40, 40, 45, 235)
TOOL_BUTTON_ACTIVE_COLOR = rgb255(70, 130, 180, 235)

tool_buttons = {}


def _set_tool(name):
    global current_tool
    current_tool = None if current_tool == name else name
    for key, btn in tool_buttons.items():
        btn.color = TOOL_BUTTON_ACTIVE_COLOR if key == current_tool else TOOL_BUTTON_COLOR


def make_tool_button(label, tool_name, x):
    btn = Button(
        text=label,
        parent=camera.ui,
        position=(x, -0.42),
        scale=(0.135, 0.06),
        color=TOOL_BUTTON_COLOR,
        text_size=0.65,
    )
    btn.on_click = Func(_set_tool, tool_name)
    tool_buttons[tool_name] = btn
    return btn


make_tool_button("Dat thuc an", "food", -0.62)
make_tool_button("Tha ke thu", "enemy", -0.465)
make_tool_button("Dao phong", "dig", -0.31)
make_tool_button("Dat da", "rock", -0.155)
make_tool_button("Dat nuoc", "water", 0.0)

pause_button = Button(
    text="Tam dung",
    parent=camera.ui,
    position=(0.30, -0.42),
    scale=(0.13, 0.06),
    color=TOOL_BUTTON_COLOR,
    text_size=0.7,
)
speed_button = Button(
    text="Toc do: x1",
    parent=camera.ui,
    position=(0.46, -0.42),
    scale=(0.15, 0.06),
    color=TOOL_BUTTON_COLOR,
    text_size=0.7,
)


def _toggle_pause():
    global sim_paused
    sim_paused = not sim_paused
    pause_button.text = "Tiep tuc" if sim_paused else "Tam dung"
    pause_button.color = TOOL_BUTTON_ACTIVE_COLOR if sim_paused else TOOL_BUTTON_COLOR


def _cycle_speed():
    global sim_speed
    sim_speed = {1: 2, 2: 4, 4: 1}[sim_speed]
    speed_button.text = f"Toc do: x{sim_speed}"


pause_button.on_click = _toggle_pause
speed_button.on_click = _cycle_speed

# Hàng nút thứ 2 (NGAY DƯỚI hàng 1, vẫn trong khung hình - trước đây đặt
# quá thấp (-0.53) nên bị cắt mất khỏi vùng nhìn thấy của camera.ui)
respawn_button = Button(
    text="Tai sinh thuc an: BAT",
    parent=camera.ui,
    position=(-0.62, -0.485),
    scale=(0.28, 0.055),
    color=TOOL_BUTTON_ACTIVE_COLOR,
    text_size=0.6,
)


def _toggle_food_respawn():
    global food_respawn_enabled
    food_respawn_enabled = not food_respawn_enabled
    respawn_button.text = f"Tai sinh thuc an: {'BAT' if food_respawn_enabled else 'TAT'}"
    respawn_button.color = TOOL_BUTTON_ACTIVE_COLOR if food_respawn_enabled else TOOL_BUTTON_COLOR


respawn_button.on_click = _toggle_food_respawn

grid_visible = True
grid_button = Button(
    text="Luoi o vuong: BAT",
    parent=camera.ui,
    position=(-0.30, -0.485),
    scale=(0.24, 0.055),
    color=TOOL_BUTTON_ACTIVE_COLOR,
    text_size=0.6,
)


def _toggle_grid():
    global grid_visible
    grid_visible = not grid_visible
    ground_grid_lines.enabled = grid_visible
    grid_button.text = f"Luoi o vuong: {'BAT' if grid_visible else 'TAT'}"
    grid_button.color = TOOL_BUTTON_ACTIVE_COLOR if grid_visible else TOOL_BUTTON_COLOR


grid_button.on_click = _toggle_grid

tool_hint = Text(
    parent=camera.ui,
    text="Chon 1 cong cu roi CLICK CHUOT TRAI len mat dat de dung",
    position=(-0.55, -0.35),
    scale=0.7,
    color=color.yellow,
)

# ---------------------------------------------------------------------
# Camera xoay quỹ đạo tự do quanh khối thế giới
# ---------------------------------------------------------------------
# Cố tình giữ pivot ở đúng gốc tọa độ (0,0,0) - giống hệt cách
# test_3d_basic.py đã chạy thành công trên máy bạn - thay vì dịch chuyển
# tâm xoay, để loại trừ khả năng lệch vị trí camera do phép xoay.
editor_cam = EditorCamera(rotation_smoothing=0)
editor_cam.rotation_x = 45   # nghiêng xuống nhiều hơn để thấy cả mặt đất lẫn hầm
CAMERA_START_DISTANCE = -80
camera.z = CAMERA_START_DISTANCE
editor_cam.target_z = CAMERA_START_DISTANCE

# ---------------------------------------------------------------------
# Bảng thống kê (HUD góc trên trái)
# ---------------------------------------------------------------------
hud = Text(
    parent=camera.ui,
    position=(-0.86, 0.47),
    scale=1.1,
    color=color.white,
    background=True,
)

frame_counter = 0
STATS_EVERY_N_FRAMES = 15


def render_colony(colony_obj, entities, color_search, color_carry_surface,
                   color_underground, color_carry_underground, last_state):
    """last_state: mảng NumPy lưu "trạng thái màu" đã gán lần trước cho mỗi
    con kiến (0=search,1=carry_surface,2=underground,3=carry_underground,
    -1=đang ẩn) - CHỈ gán lại ent.color/ent.enabled khi trạng thái thực sự
    đổi, tránh Panda3D phải cập nhật render-state thừa cho hàng trăm con
    kiến không đổi màu ở mỗi khung hình (đa số các tick, phần lớn đàn kiến
    giữ nguyên trạng thái từ tick trước)."""
    xs, ys, zs = colony_obj.x, colony_obj.y, colony_obj.z
    carrying = colony_obj.carrying
    layer = colony_obj.layer
    alive = colony_obj.alive
    for i, ent in enumerate(entities):
        if not alive[i]:
            if last_state[i] != -1:
                ent.enabled = False
                last_state[i] = -1
            continue
        ent.position = sim_to_world(xs[i], ys[i], zs[i])  # vị trí luôn đổi, phải cập nhật mỗi frame

        if layer[i] == cfg.LAYER_SURFACE:
            new_state = 1 if carrying[i] else 0
        else:
            new_state = 3 if carrying[i] else 2

        if last_state[i] != new_state:
            if last_state[i] == -1:
                ent.enabled = True
            ent.color = (color_search, color_carry_surface,
                         color_underground, color_carry_underground)[new_state]
            last_state[i] = new_state


def update():
    global frame_counter, food_respawn_tick
    if not sim_paused:
        for _ in range(sim_speed):
            colony.update()
            rival_colony.update()
            enemy.update(ALL_COLONIES)
            if food_respawn_enabled:
                food_respawn_tick += 1
                if food_respawn_tick % cfg.FOOD_RESPAWN_INTERVAL == 0:
                    do_random_food_respawn()

    render_colony(colony, ant_entities, COLOR_SEARCH, COLOR_CARRY_SURFACE,
                  COLOR_UNDERGROUND, COLOR_CARRY_UNDERGROUND, ant_render_state)
    render_colony(rival_colony, rival_ant_entities, RIVAL_COLOR_SEARCH,
                  RIVAL_COLOR_CARRY_SURFACE, RIVAL_COLOR_UNDERGROUND,
                  RIVAL_COLOR_CARRY_UNDERGROUND, rival_ant_render_state)

    enemy_entity.enabled = enemy.active
    if enemy.active:
        enemy_entity.position = sim_to_world(enemy.x, enemy.y, cfg.SURFACE_Z + 0.5)

    frame_counter += 1
    if frame_counter % STATS_EVERY_N_FRAMES == 0:
        for (gx, gy), ent in food_entities.items():
            ent.enabled = surface_world.food[gx, gy] > 0.05

        c = colony.counts()
        r = rival_colony.counts()
        canh_bao = "  *** DAN KIEN DANG DOI ***" if c["is_starving"] else ""
        khat = "  *** DAN KIEN DANG KHAT NUOC ***" if c["is_dehydrated"] else ""
        ke_thu = "  *** CO KE THU TREN MAT DAT ***" if enemy.active else ""
        hud.text = (
            f"TO CHINH - Dan so: {c['population']}/{colony.n} (linh: {c['soldiers']})   "
            f"Sinh: {c['total_births']}   Chet: {c['total_deaths']}\n"
            f"TO DOI THU - Dan so: {r['population']}/{rival_colony.n} (linh: {r['soldiers']})   "
            f"Sinh: {r['total_births']}   Chet: {r['total_deaths']}\n"
            f"Kho: {c['food_in_storage']:.0f}   Au trung: {c['food_in_nursery']:.0f}   "
            f"Nuoc: {c['water_in_storage']:.0f}   "
            f"Ke thu da giet: {enemy.total_kills} (bi linh danh bai: {enemy.total_defeated})"
            f"{canh_bao}{khat}{ke_thu}\n"
            f"Chuot phai+keo: xoay | Lan chuot: zoom | G: xuyen mat dat | Esc: thoat"
        )


def input(key):
    global ground_transparent
    if key == "escape":
        application.quit()
    elif key == "g":
        ground_transparent = not ground_transparent
        alpha = GROUND_TRANSPARENT_ALPHA if ground_transparent else GROUND_OPAQUE_ALPHA
        ground.color = rgb255(205, 178, 132, alpha)
    elif key == "left mouse down" and current_tool is not None:
        # Chỉ xử lý khi thực sự đang trỏ vào MẶT ĐẤT (không phải bấm
        # nhầm vào nút toolbar - mouse.hovered_entity sẽ là ground lúc đó)
        if mouse.hovered_entity == ground and mouse.world_point is not None:
            sim_x, sim_y, _ = world_to_sim(*mouse.world_point)
            sim_x = float(np.clip(sim_x, 1, cfg.GRID_SIZE - 2))
            sim_y = float(np.clip(sim_y, 1, cfg.GRID_SIZE - 2))

            if current_tool == "food":
                place_food_at(int(sim_x), int(sim_y))
            elif current_tool == "enemy":
                enemy.force_spawn_at(sim_x, sim_y)
            elif current_tool == "dig":
                name, center, radius, rgb = underground_world.dig_new_room(sim_x, sim_y)
                create_room_entity(name, center, radius, rgb)
                create_corridor_entity(underground_world.corridors[-1][0], center)
            elif current_tool == "rock":
                feature = surface_world.add_obstacle(
                    int(sim_x), int(sim_y), cfg.TERRAIN_ROCK, cfg.ROCK_CLUSTER_RADIUS
                )
                create_terrain_entity(*feature)
            elif current_tool == "water":
                feature = surface_world.add_obstacle(
                    int(sim_x), int(sim_y), cfg.TERRAIN_WATER, cfg.WATER_CLUSTER_RADIUS
                )
                create_terrain_entity(*feature)


app.run()
