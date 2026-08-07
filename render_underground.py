"""Vẽ CÁC TẦNG NGẦM (gác cửa, kho, bể nước, trứng, ấu trùng, chúa, nghĩa
địa, phòng tự đào): sàn phòng, nội dung riêng của từng phòng chức năng, và
kiến đang ở tầng đó (dùng lại draw_ants từ render_surface)."""
import math

import numpy as np
import pygame

import config as cfg
from render_surface import draw_ants


def layer_name(depth):
    if depth == 0:
        return "Mat dat"
    if depth == cfg.DEPTH_GUARD:
        return "Phong gac cua"
    if depth == cfg.DEPTH_STORAGE:
        return "Kho thuc an"
    if depth == cfg.DEPTH_WATER:
        return "Be tru nuoc"
    if depth == cfg.DEPTH_EGG:
        return "Phong trung"
    if depth == cfg.DEPTH_NURSERY:
        return "Au trung"
    if depth == cfg.DEPTH_QUEEN:
        return "Phong chua"
    if depth == cfg.DEPTH_GRAVEYARD:
        return "Nghia dia"
    return f"Phong dao (tang {depth})"


def draw_room_floor(surf, cx, cy, r_px, room_rgb, seed_key):
    """Vẽ 1 phòng ngầm như 1 KHU VỰC SÀN thật sự (không phải hình tròn
    trang trí) - có viền tường đất bo tròn + lớp sàn sáng hơn bên trong,
    để mắt nhận ra ngay đây là không gian kiến có thể đi lại/hoạt động
    bên trong, khác hẳn đường hành lang mảnh. (Không còn vẽ thêm các chấm
    "vân sàn" ngẫu nhiên như bản trước - dễ bị nhầm với thức ăn/ấu trùng/
    xác kiến khi nhìn nhanh.)"""
    wall_color = tuple(max(0, c - 60) for c in room_rgb)
    floor_color = tuple(min(255, c + 45) for c in room_rgb)
    pygame.draw.circle(surf, wall_color, (cx, cy), r_px + max(2, int(r_px * 0.12)))
    pygame.draw.circle(surf, floor_color, (cx, cy), r_px)
    pygame.draw.circle(surf, room_rgb, (cx, cy), max(1, int(r_px * 0.78)))
    pygame.draw.circle(surf, (0, 0, 0), (cx, cy), r_px + max(2, int(r_px * 0.12)), 2)


def draw_storage_pile(surf, cx, cy, r_px, amount, seed_key):
    """Kho thức ăn KHÔNG chỉ là 1 con số - vẽ luôn số thức ăn ĐANG LƯU
    TRỮ THẬT SỰ dưới dạng 1 đống nhỏ các viên thức ăn rải trong phòng,
    đống to/nhỏ tùy theo lượng tồn kho hiện tại (1 icon = ĐÚNG 1 đơn vị
    thức ăn - xem STORAGE_FOOD_PER_ICON). Tất cả viên đều dùng chung 1 MÀU
    THỨC ĂN DUY NHẤT (khớp với FOOD_TYPE_COLOR - chỉ còn 1 loại thức ăn),
    chỉ ngả sáng/tối nhẹ ngẫu nhiên giữa các viên để đống trông có khối
    thay vì phẳng lì 1 màu tuyệt đối - màu CỐ Ý chọn sáng/rực hơn hẳn màu
    sàn đất để không bị lẫn với sàn phòng."""
    n_icons = int(np.clip(amount / cfg.STORAGE_FOOD_PER_ICON, 0, cfg.STORAGE_MAX_ICONS))
    if n_icons <= 0:
        return
    rng_local = np.random.RandomState(seed_key * 733 + 5)
    ang = rng_local.uniform(0, 2 * np.pi, n_icons)
    rad = np.sqrt(rng_local.uniform(0, 1, n_icons)) * r_px * 0.72
    shade_jitter = rng_local.uniform(-22, 22, n_icons)
    base = cfg.FOOD_TYPE_COLOR[cfg.FOOD_TYPE_SEED]
    for i in range(n_icons):
        dx = int(math.cos(ang[i]) * rad[i])
        dy = int(math.sin(ang[i]) * rad[i])
        r = max(2, int(r_px * 0.085))
        px, py = cx + dx, cy + dy
        j = shade_jitter[i]
        color = tuple(int(np.clip(c + j, 20, 255)) for c in base)
        pygame.draw.circle(surf, (35, 25, 15), (px, py), r + 1)  # viền tối cho nổi khối
        pygame.draw.circle(surf, color, (px, py), r)
        hi = max(1, int(r * 0.4))
        pygame.draw.circle(surf, (255, 255, 230), (px - r // 3, py - r // 3), hi)  # điểm sáng


def draw_larvae(surf, cx, cy, r_px, colony_obj, seed_key):
    """Phòng ấu trùng THẬT SỰ có ấu trùng bên trong - mỗi ấu trùng lớn
    dần theo growth (0..1): bé + trắng nhợt lúc mới đẻ, to + ngả vàng
    khi sắp nở thành kiến mới."""
    active_idx = np.where(colony_obj.larva_active)[0]
    if len(active_idx) == 0:
        return
    rng_local = np.random.RandomState(seed_key * 331 + 7)
    ang = rng_local.uniform(0, 2 * np.pi, cfg.LARVA_MAX_COUNT)
    rad = np.sqrt(rng_local.uniform(0, 1, cfg.LARVA_MAX_COUNT)) * r_px * 0.68
    for i in active_idx:
        growth = float(colony_obj.larva_growth[i])
        dx = int(math.cos(ang[i]) * rad[i])
        dy = int(math.sin(ang[i]) * rad[i])
        size = max(3, int(r_px * (0.07 + 0.11 * growth)))
        shade = int(248 - growth * 60)
        color = (shade, shade, max(140, shade - 55))
        pygame.draw.ellipse(surf, (60, 55, 25), (cx + dx - size - 1, cy + dy - size * 0.7 - 1, size * 2 + 2, size * 1.4 + 2))
        pygame.draw.ellipse(surf, color, (cx + dx - size, cy + dy - size * 0.7, size * 2, size * 1.4))


def draw_queen(surf, cx, cy, r_px, room_rgb, frame_counter):
    """Phòng chúa THẬT SỰ có 1 con kiến chúa - to hẳn so với thợ
    thường, đứng yên giữa phòng (chỉ hơi bồng bềnh nhẹ cho có sức
    sống), với bụng (gaster) to đặc trưng để đẻ trứng."""
    bob = math.sin(frame_counter * 0.03) * r_px * 0.03
    qy = cy + bob
    body_color = tuple(max(0, c - 40) for c in room_rgb)
    gaster_w, gaster_h = r_px * 0.95, r_px * 0.62
    pygame.draw.ellipse(surf, body_color, (cx - gaster_w * 0.15, qy - gaster_h / 2, gaster_w, gaster_h))
    thorax_r = max(3, int(r_px * 0.22))
    pygame.draw.circle(surf, body_color, (int(cx - gaster_w * 0.35), int(qy)), thorax_r)
    head_r = max(3, int(r_px * 0.16))
    head_x, head_y = cx - gaster_w * 0.55, qy
    pygame.draw.circle(surf, body_color, (int(head_x), int(head_y)), head_r)
    for sign in (-1, 1):
        end = (head_x - head_r * 1.3, head_y + sign * head_r * 1.1)
        pygame.draw.line(surf, (20, 20, 20), (head_x - head_r * 0.3, head_y), end, 2)
    pygame.draw.ellipse(surf, (0, 0, 0), (cx - gaster_w * 0.15, qy - gaster_h / 2, gaster_w, gaster_h), 2)


def draw_water_drops(surf, cx, cy, r_px, amount, seed_key):
    """Bể trữ nước KHÔNG chỉ là 1 con số - vẽ luôn lượng nước ĐANG TRỮ
    THẬT SỰ dưới dạng các giọt nước xanh lấp lánh rải trong bể, to/nhỏ
    theo lượng nước tồn hiện tại."""
    n_icons = int(np.clip(amount / cfg.WATER_PER_ICON, 0, cfg.WATER_MAX_ICONS))
    if n_icons <= 0:
        return
    rng_local = np.random.RandomState(seed_key * 611 + 17)
    ang = rng_local.uniform(0, 2 * np.pi, n_icons)
    rad = np.sqrt(rng_local.uniform(0, 1, n_icons)) * r_px * 0.72
    for i in range(n_icons):
        dx = int(math.cos(ang[i]) * rad[i])
        dy = int(math.sin(ang[i]) * rad[i])
        r = max(3, int(r_px * 0.13))
        px, py = cx + dx, cy + dy
        pygame.draw.circle(surf, (20, 60, 100), (px, py), r + 1)
        pygame.draw.circle(surf, (60, 150, 230), (px, py), r)
        hi = max(1, int(r * 0.45))
        pygame.draw.circle(surf, (220, 240, 255), (px - r // 3, py - r // 3), hi)


def draw_eggs(surf, cx, cy, r_px, colony_obj, seed_key):
    """Phòng trứng THẬT SỰ có trứng bên trong - trứng nhỏ, trắng ngà,
    hơi to dần khi sắp nở (chuyển sang phòng ấu trùng)."""
    active_idx = np.where(colony_obj.egg_active)[0]
    if len(active_idx) == 0:
        return
    rng_local = np.random.RandomState(seed_key * 421 + 3)
    ang = rng_local.uniform(0, 2 * np.pi, cfg.EGG_MAX_COUNT)
    rad = np.sqrt(rng_local.uniform(0, 1, cfg.EGG_MAX_COUNT)) * r_px * 0.65
    for i in active_idx:
        growth = float(colony_obj.egg_growth[i])
        dx = int(math.cos(ang[i]) * rad[i])
        dy = int(math.sin(ang[i]) * rad[i])
        size = max(2, int(r_px * (0.045 + 0.035 * growth)))
        color = (250, 248, 235)
        pygame.draw.ellipse(surf, (150, 145, 120), (cx + dx - size - 1, cy + dy - size * 1.2 - 1, size * 2 + 2, size * 2.4 + 2))
        pygame.draw.ellipse(surf, color, (cx + dx - size, cy + dy - size * 1.2, size * 2, size * 2.4))


def draw_graveyard(surf, cx, cy, r_px, corpse_count, seed_key):
    """Nghĩa địa - mỗi kiến chết để lại 1 'nắm xác' nhỏ ở đây, mờ dần
    theo thời gian (phân hủy) thay vì kiến biến mất vô hình."""
    n_icons = int(np.clip(corpse_count, 0, cfg.GRAVEYARD_MAX_CORPSES))
    if n_icons <= 0:
        return
    rng_local = np.random.RandomState(seed_key * 857 + 29)
    ang = rng_local.uniform(0, 2 * np.pi, n_icons)
    rad = np.sqrt(rng_local.uniform(0, 1, n_icons)) * r_px * 0.7
    for i in range(n_icons):
        dx = int(math.cos(ang[i]) * rad[i])
        dy = int(math.sin(ang[i]) * rad[i])
        px, py = cx + dx, cy + dy
        size = max(2, int(r_px * 0.09))
        pygame.draw.line(surf, (60, 50, 45), (px - size, py - size), (px + size, py + size), 2)
        pygame.draw.line(surf, (60, 50, 45), (px - size, py + size), (px + size, py - size), 2)
        pygame.draw.circle(surf, (45, 38, 34), (px, py), size)


def draw_underground_layer(state, surf, depth):
    camera = state.camera
    pygame.draw.rect(surf, cfg.COLOR_BG_UNDERGROUND, (0, 0, state.SCREEN_W, state.CANVAS_H))
    cell = camera.cell_px()
    if state.grid_visible and cell >= 3:
        from render_surface import draw_grid_lines
        draw_grid_lines(state, surf)

    for colony_idx, (uworld, colony_obj, base_rgb) in enumerate((
        (state.underground_world, state.colony, (0, 200, 255)),
        (state.rival_underground, state.rival_colony, (255, 120, 90)),
    )):
        # giếng (thang máy) - chỉ hiện nếu tổ này CÓ phòng ở tầng này
        has_room_here = any(r[5] == depth for r in uworld.rooms)
        if has_room_here:
            sx, sy = camera.world_to_screen(float(uworld.shaft_xy[0]), float(uworld.shaft_xy[1]), state.CENTER_X, state.CENTER_Y)
            r = max(3, int(cell * 0.8))
            pygame.draw.circle(surf, cfg.COLOR_SHAFT, (int(sx), int(sy)), r)
            pygame.draw.circle(surf, (90, 90, 90), (int(sx), int(sy)), r, 1)

        for room in uworld.rooms:
            room_id, name, center, radius, room_rgb, room_depth = room
            if room_depth != depth:
                continue
            cx, cy = camera.world_to_screen(float(center[0]), float(center[1]), state.CENTER_X, state.CENTER_Y)
            # hành lang nối giếng <-> phòng (cùng tầng) - vẽ TRƯỚC, mảnh
            # và mờ hơn, để rõ ràng đây chỉ là đường DI CHUYỂN, không
            # phải nơi kiến "ở lại hoạt động"
            sx, sy = camera.world_to_screen(float(uworld.shaft_xy[0]), float(uworld.shaft_xy[1]), state.CENTER_X, state.CENTER_Y)
            pygame.draw.line(surf, (95, 85, 78), (int(sx), int(sy)), (int(cx), int(cy)), max(1, int(cell * 0.09)))

            r_px = max(10, int(radius * cell))
            seed_key = room_id * 10 + colony_idx
            draw_room_floor(surf, int(cx), int(cy), r_px, room_rgb, seed_key)

            # --- mỗi phòng THỰC SỰ làm đúng chức năng của nó ---
            if room_id == 0:  # Kho thức ăn: vẽ đống thức ăn tồn kho thật
                draw_storage_pile(surf, int(cx), int(cy), r_px, uworld.food_in_storage, seed_key)
            elif room_id == 1:  # Phòng ấu trùng: vẽ các ấu trùng đang lớn thật
                draw_larvae(surf, int(cx), int(cy), r_px, colony_obj, seed_key)
            elif room_id == 2:  # Phòng chúa: vẽ 1 con kiến chúa thật
                draw_queen(surf, int(cx), int(cy), r_px, room_rgb, state.frame_counter)
            elif room_id == 3:  # Bể trữ nước: vẽ các giọt nước tồn trữ thật
                draw_water_drops(surf, int(cx), int(cy), r_px, uworld.water_in_storage, seed_key)
            elif room_id == 4:  # Phòng trứng: vẽ các trứng đang ủ thật
                draw_eggs(surf, int(cx), int(cy), r_px, colony_obj, seed_key)
            elif room_id == 6:  # Nghĩa địa: vẽ các nắm xác thật
                draw_graveyard(surf, int(cx), int(cy), r_px, uworld.corpse_count, seed_key)
            # room_id == 5 (Phòng gác cửa): không cần vẽ thêm gì đặc biệt
            # - lính gác đóng quân ở đây đã tự hiện ra qua draw_ants() bên
            # dưới (vì depth của họ = DEPTH_GUARD), giống như trong bất kỳ
            # phòng nào khác.

            label = state.font_small.render(name, True, (235, 235, 235))
            surf.blit(label, label.get_rect(center=(cx, cy - r_px - 12)))

    # Màu kiến dưới hầm GẦN GIỐNG HỆT màu thật trên mặt đất (chỉ nhỉnh sáng
    # hơn 1 chút để vẫn có hình khối trên nền hành lang rất tối) - trước
    # đây dùng hẳn 1 bộ màu khác (xám trắng) khiến cùng 1 con kiến trông
    # như đổi loài giữa 2 khu vực. Viền sáng (underground=True) đã đủ để
    # nổi trên nền tối, không cần đổi màu thân nữa.
    draw_ants(state, surf, state.colony, (45, 40, 36), (215, 120, 30), depth_filter=depth, underground=True)
    draw_ants(state, surf, state.rival_colony, (110, 40, 33), (230, 140, 40), depth_filter=depth, underground=True)
