"""Ant World 3D - bản prototype.

Toàn bộ thế giới (mặt đất + hầm ngầm) được hiển thị như 1 khối hộp trong
suốt kiểu "bể nuôi kiến" (formicarium bằng kính) mà bạn xoay/zoom tự do.

Chạy: python main.py

Điều khiển (mặc định của Ursina EditorCamera):
  - Giữ CHUỘT PHẢI + di chuột : xoay camera quanh thế giới
  - Lăn chuột                 : zoom vào/ra
  - Giữ CHUỘT PHẢI + W/A/S/D  : bay ngang trong lúc xoay
  - Phím G                    : bật/tắt độ trong suốt của mặt đất
                                  (để nhìn xuyên xuống hầm dễ hơn)
  - Esc                       : thoát
"""
from ursina import *
import numpy as np

import config as cfg
from world import SurfaceWorld, UndergroundWorld
from ants import AntColony

app = Ursina(title="Ant World 3D", borderless=False, size=(cfg.SCREEN_W, cfg.SCREEN_H))
window.color = color.rgb(18, 18, 24)
Sky()

# ---------------------------------------------------------------------
# Ánh sáng cơ bản để khối 3D có chiều sâu, đổ bóng nhẹ
# ---------------------------------------------------------------------
DirectionalLight(rotation=(45, -45, 0), shadows=False)
AmbientLight(color=color.rgba(200, 200, 210, 0.55))

# ---------------------------------------------------------------------
# Thế giới mô phỏng (logic không đổi so với bản trước, chỉ thêm trục Z)
# ---------------------------------------------------------------------
surface_world = SurfaceWorld()
underground_world = UndergroundWorld()
colony = AntColony(cfg.NUM_ANTS, surface_world, underground_world)

CENTER = cfg.GRID_SIZE / 2.0


def sim_to_world(x, y, z):
    """Đổi tọa độ mô phỏng (x,y ngang, z sâu-âm) sang tọa độ Ursina
    (x ngang, y lên/xuống, z ngang còn lại)."""
    return (float(x) - CENTER, float(z), float(y) - CENTER)


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
        color=color.rgba(255, 255, 255, 16),
        double_sided=True,
    )


# ---------------------------------------------------------------------
# Mặt đất - có thể bấm phím G để chuyển giữa đục/trong suốt
# ---------------------------------------------------------------------
ground = Entity(
    model="plane",
    scale=(cfg.GRID_SIZE, 1, cfg.GRID_SIZE),
    position=(0, 0, 0),
    color=color.rgba(205, 178, 132, 235),
    double_sided=True,
    unlit=True,
)
GROUND_OPAQUE_ALPHA = 235
GROUND_TRANSPARENT_ALPHA = 55
ground_transparent = False

# Lỗ tổ trên mặt đất
nest_hole = Entity(
    model=Cylinder(resolution=12, radius=1.6, height=0.12),
    position=sim_to_world(cfg.NEST_POS[0], cfg.NEST_POS[1], 0.02),
    color=color.rgb(30, 22, 14),
    unlit=True,
)

# ---------------------------------------------------------------------
# Các phòng dưới hầm
# ---------------------------------------------------------------------
for name, center, radius, rgb in underground_world.rooms:
    room_ent = Entity(
        model="sphere",
        scale=radius * 2,
        position=sim_to_world(*center),
        color=color.rgba(rgb[0], rgb[1], rgb[2], 215),
        unlit=True,
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

# Hành lang nối giếng <-> các phòng (vẽ dạng đường/ống mỏng)
for a, b in underground_world.corridors:
    p1 = sim_to_world(*a)
    p2 = sim_to_world(*b)
    Entity(
        model=Mesh(vertices=[p1, p2], mode="line", thickness=6),
        color=color.rgba(160, 128, 92, 230),
        unlit=True,
    )

# ---------------------------------------------------------------------
# Thức ăn trên mặt đất (lấy mẫu thưa để không tạo quá nhiều entity)
# ---------------------------------------------------------------------
food_entities = {}
FOOD_SAMPLE_STEP = 2
for gx in range(0, cfg.GRID_SIZE, FOOD_SAMPLE_STEP):
    for gy in range(0, cfg.GRID_SIZE, FOOD_SAMPLE_STEP):
        if surface_world.food[gx, gy] > 0.5:
            ent = Entity(
                model="sphere",
                scale=0.55,
                position=sim_to_world(gx, gy, 0.2),
                color=color.rgb(60, 150, 60),
                unlit=True,
            )
            food_entities[(gx, gy)] = ent

# ---------------------------------------------------------------------
# Kiến - tạo sẵn 1 entity cho mỗi con, mỗi frame chỉ cập nhật vị trí/màu
# ---------------------------------------------------------------------
ant_entities = [
    Entity(model="sphere", scale=0.3, color=color.black, unlit=True) for _ in range(colony.n)
]

COLOR_SEARCH = color.rgb(25, 25, 25)
COLOR_CARRY_SURFACE = color.rgb(215, 120, 30)
COLOR_UNDERGROUND = color.rgb(220, 220, 220)
COLOR_CARRY_UNDERGROUND = color.rgb(235, 190, 70)

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


def update():
    global frame_counter
    colony.update()

    xs, ys, zs = colony.x, colony.y, colony.z
    carrying = colony.carrying
    layer = colony.layer

    for i, ent in enumerate(ant_entities):
        ent.position = sim_to_world(xs[i], ys[i], zs[i])
        if layer[i] == cfg.LAYER_SURFACE:
            ent.color = COLOR_CARRY_SURFACE if carrying[i] else COLOR_SEARCH
        else:
            ent.color = COLOR_CARRY_UNDERGROUND if carrying[i] else COLOR_UNDERGROUND

    frame_counter += 1
    if frame_counter % STATS_EVERY_N_FRAMES == 0:
        for (gx, gy), ent in food_entities.items():
            ent.enabled = surface_world.food[gx, gy] > 0.05

        c = colony.counts()
        hud.text = (
            f"Tim an: {c['searching']}   Dang tha ve: {c['returning']}   "
            f"Duoi ham: {c['underground']}\n"
            f"Tong thuc an da thu: {c['total_food_collected']}\n"
            f"Kho: {c['food_in_storage']}   Phong au trung: {c['food_in_nursery']}\n"
            f"Chuot phai+keo: xoay | Lan chuot: zoom | G: xuyen mat dat | Esc: thoat"
        )


def input(key):
    global ground_transparent
    if key == "escape":
        application.quit()
    elif key == "g":
        ground_transparent = not ground_transparent
        alpha = GROUND_TRANSPARENT_ALPHA if ground_transparent else GROUND_OPAQUE_ALPHA
        ground.color = color.rgba(205, 178, 132, alpha)


app.run()
