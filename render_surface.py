"""Vẽ TẦNG 0 (mặt đất): lưới ô vuông, địa hình, thức ăn, lỗ tổ, kẻ thù, và
kiến trên mặt đất. Cũng chứa draw_ants() - dùng chung cho CẢ mặt đất lẫn
các tầng ngầm (render_underground.py gọi lại hàm này)."""
import math

import numpy as np
import pygame

import config as cfg


def draw_grid_lines(state, surf):
    camera = state.camera
    cell = camera.cell_px()
    x0, y0 = camera.world_to_screen(0, 0, state.CENTER_X, state.CENTER_Y)
    map_right = x0 + cfg.GRID_SIZE * cell
    map_bottom = y0 + cfg.GRID_SIZE * cell
    step = cell
    gx = x0
    while gx <= map_right + 0.5:
        if gx >= -step:
            pygame.draw.line(
                surf, (0, 0, 0, 40), (gx, max(0, y0)),
                (gx, min(state.CANVAS_H, map_bottom)), 1
            )
        gx += step
    gy = y0
    while gy <= map_bottom + 0.5:
        if gy >= -step:
            pygame.draw.line(
                surf, (0, 0, 0, 40), (max(0, x0), gy),
                (min(state.SCREEN_W, map_right), gy), 1
            )
        gy += step


def draw_pheromone_trails(state, surf):
    """Vẽ RÕ đường mùi (pheromone) mà kiến để lại khi tha đồ về tổ - lớp
    phủ trong suốt, đậm/nhạt theo đúng nồng độ mùi thật tại từng ô. Mùi tìm
    đường (màu xanh lam) và mùi báo động/nguy hiểm (màu đỏ, để lại quanh
    kẻ thù) được vẽ tách biệt để dễ phân biệt."""
    surface_world = state.surface_world
    camera = state.camera
    cell = camera.cell_px()

    overlay = pygame.Surface((state.SCREEN_W, state.CANVAS_H), pygame.SRCALPHA)
    r = max(2, int(cell * 0.42))

    xi, yi = np.where(surface_world.pheromone > 0.05)
    if len(xi) > 0:
        vals = surface_world.pheromone[xi, yi]
        sxs, sys_ = camera.world_to_screen(xi.astype(np.float32), yi.astype(np.float32), state.CENTER_X, state.CENTER_Y)
        alphas = np.clip(vals / cfg.PHEROMONE_MAX, 0, 1) * 150
        for sx, sy, a in zip(sxs, sys_, alphas):
            pygame.draw.circle(overlay, (60, 170, 255, int(a)), (int(sx), int(sy)), r)

    dxi, dyi = np.where(surface_world.danger_pheromone > 0.1)
    if len(dxi) > 0:
        dvals = surface_world.danger_pheromone[dxi, dyi]
        dsxs, dsys = camera.world_to_screen(dxi.astype(np.float32), dyi.astype(np.float32), state.CENTER_X, state.CENTER_Y)
        dalphas = np.clip(dvals / cfg.DANGER_PHEROMONE_MAX, 0, 1) * 140
        for sx, sy, a in zip(dsxs, dsys, dalphas):
            pygame.draw.circle(overlay, (230, 50, 40, int(a)), (int(sx), int(sy)), r)

    surf.blit(overlay, (0, 0))


def draw_surface_layer(state, surf):
    camera = state.camera
    cell = camera.cell_px()
    x0, y0 = camera.world_to_screen(0, 0, state.CENTER_X, state.CENTER_Y)
    ground_rect = pygame.Rect(x0, y0, cfg.GRID_SIZE * cell, cfg.GRID_SIZE * cell)
    pygame.draw.rect(surf, cfg.COLOR_GROUND_FILL, ground_rect)

    if state.grid_visible and cell >= 3:
        draw_grid_lines(state, surf)

    surface_world = state.surface_world

    # --- địa hình: đá + nước (lấy mẫu thưa theo bước lưới cho nhanh) ---
    terrain = surface_world.terrain
    step = max(1, int(1 / max(cell / cfg.BASE_CELL_PX, 0.05)))
    for gx in range(0, cfg.GRID_SIZE, step):
        for gy in range(0, cfg.GRID_SIZE, step):
            t = terrain[gx, gy]
            if t == cfg.TERRAIN_EMPTY:
                continue
            sx, sy = camera.world_to_screen(gx, gy, state.CENTER_X, state.CENTER_Y)
            color = (120, 118, 112) if t == cfg.TERRAIN_ROCK else (70, 140, 200)
            r = max(1, int(cell * step * 0.55))
            pygame.draw.rect(surf, color, (sx - r / 2, sy - r / 2, r, r))

    # --- đường mùi (pheromone) - vẽ TRƯỚC thức ăn/kiến để nằm dưới, như
    # dấu vết in trên mặt đất ---
    draw_pheromone_trails(state, surf)

    # --- thức ăn (lấy mẫu thưa) ---
    food = surface_world.food
    food_type = surface_world.food_type
    fstep = 1 if cell > 10 else 2
    for gx in range(0, cfg.GRID_SIZE, fstep):
        for gy in range(0, cfg.GRID_SIZE, fstep):
            if food[gx, gy] > 0.5:
                ftype = int(food_type[gx, gy])
                fc = cfg.FOOD_TYPE_COLOR.get(ftype, (60, 150, 60))
                sx, sy = camera.world_to_screen(gx, gy, state.CENTER_X, state.CENTER_Y)
                r = max(2, int(cell * 0.28))
                pygame.draw.circle(surf, fc, (int(sx), int(sy)), r)

    # --- lỗ tổ 2 bên ---
    for pos, color in ((cfg.NEST_POS, (30, 22, 14)), (cfg.RIVAL_NEST_POS, (45, 20, 18))):
        sx, sy = camera.world_to_screen(pos[0], pos[1], state.CENTER_X, state.CENTER_Y)
        r = max(3, int(cell * 1.4))
        pygame.draw.circle(surf, color, (int(sx), int(sy)), r)
        pygame.draw.circle(surf, (0, 0, 0), (int(sx), int(sy)), r, 2)

    # --- kẻ thù ---
    enemy = state.enemy
    if enemy.active:
        sx, sy = camera.world_to_screen(enemy.x, enemy.y, state.CENTER_X, state.CENTER_Y)
        r = max(3, int(cell * 0.6))
        pts = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
        pygame.draw.polygon(surf, (220, 30, 30), pts)

    draw_ants(state, surf, state.colony, (25, 25, 25), (215, 120, 30))
    draw_ants(state, surf, state.rival_colony, (120, 30, 25), (230, 140, 40))


def draw_ants(state, surf, colony_obj, color_normal, color_carry, depth_filter=0):
    """Vẽ kiến thành 1 HÌNH DÁNG CON KIẾN THẬT (đầu-ngực-bụng nối theo
    đúng hướng đang di chuyển) thay vì 1 chấm tròn đơn giản - để không
    bị lẫn với các chấm khác trong phòng (thức ăn, ấu trùng, trứng, xác,
    vân sàn...). Lính (ROLE_MAJOR) có đầu to/bạnh hơn hẳn (như có hàm
    khỏe); lính gác (is_guard) có thêm 1 chấm sáng nhỏ trên bụng để
    phân biệt với lính thường ngay cả khi đứng lẫn nhau trên mặt đất."""
    mask = colony_obj.alive & (colony_obj.depth == depth_filter)
    if not np.any(mask):
        return
    camera = state.camera
    CENTER_X, CENTER_Y, CANVAS_H = state.CENTER_X, state.CENTER_Y, state.CANVAS_H
    idx = np.where(mask)[0]
    cell = camera.cell_px()
    xs, ys = colony_obj.x[idx], colony_obj.y[idx]
    thetas = colony_obj.theta[idx]
    carrying = colony_obj.carrying[idx]
    carry_type = colony_obj.carry_type[idx]
    carry_food_type = colony_obj.carry_food_type[idx]
    is_major = colony_obj.role[idx] == cfg.ROLE_MAJOR
    is_guard = colony_obj.is_guard[idx]
    is_working = colony_obj.state[idx] == cfg.STATE_DWELL
    sxs = CENTER_X + (xs - camera.cx) * cell
    sys_ = CENTER_Y + (ys - camera.cy) * cell
    for i in range(len(idx)):
        sx, sy = sxs[i], sys_[i]
        if sx < -10 or sx > state.SCREEN_W + 10 or sy < -10 or sy > CANVAS_H + 10:
            continue
        base_r = cell * 0.155
        major = bool(is_major[i])
        r = base_r * (cfg.MAJOR_SIZE_SCALE if major else 1.0)
        color = color_carry if carrying[i] else color_normal
        head_color = tuple(max(0, c - 75) for c in color)

        th = float(thetas[i])
        dirx, diry = math.cos(th), math.sin(th)
        perp_x, perp_y = -diry, dirx

        abdomen_r = max(1, int(r * 1.05))
        thorax_r = max(1, int(r * 0.6))
        head_r = max(1, int(r * (0.8 if major else 0.6)))  # lính: đầu to/bạnh hơn hẳn

        abd_x, abd_y = sx - dirx * r * 0.95, sy - diry * r * 0.95
        hd_x, hd_y = sx + dirx * r * 1.0, sy + diry * r * 1.0

        pygame.draw.circle(surf, color, (int(abd_x), int(abd_y)), abdomen_r)
        pygame.draw.circle(surf, color, (int(sx), int(sy)), thorax_r)
        pygame.draw.circle(surf, head_color, (int(hd_x), int(hd_y)), head_r)

        if is_guard[i]:  # lính gác: 1 chấm sáng nhỏ trên bụng để phân biệt
            badge_r = max(1, int(abdomen_r * 0.4))
            pygame.draw.circle(surf, (255, 225, 90), (int(abd_x), int(abd_y)), badge_r)

        # --- Đang LÀM VIỆC (STATE_DWELL - lượn trong phòng): 1 vòng sáng
        # nhấp nháy nhẹ quanh con kiến, để phân biệt rõ ràng với kiến chỉ
        # đang ĐI QUA hành lang - nhìn phát biết ngay ai đang "làm việc" ---
        if is_working[i]:
            pulse = 0.5 + 0.5 * math.sin(state.frame_counter * 0.15 + i)
            ring_r = max(2, int(r * 1.7 + pulse * r * 0.5))
            ring_alpha = int(90 + pulse * 100)
            ring_surf = pygame.Surface((ring_r * 2 + 2, ring_r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (255, 235, 120, ring_alpha), (ring_r + 1, ring_r + 1), ring_r, 2)
            surf.blit(ring_surf, (int(sx) - ring_r - 1, int(sy) - ring_r - 1))

        if r >= 2.6:  # đủ to (zoom gần) mới vẽ thêm râu, tránh rối ở xa
            ant_len = head_r * 0.9
            for side in (-1, 1):
                ax = hd_x + dirx * ant_len + perp_x * head_r * 0.5 * side
                ay = hd_y + diry * ant_len + perp_y * head_r * 0.5 * side
                pygame.draw.line(surf, head_color, (int(hd_x), int(hd_y)), (int(ax), int(ay)), 1)

        # --- Mồi tha trên lưng: 1 miếng nhỏ đúng màu loại thức ăn thật,
        # hiện rõ ràng ngay trước đầu con kiến (theo hướng đang đi) để
        # nhìn thấy NGAY nó đang tha gì về tổ, không chỉ đổi màu thân ---
        if carrying[i]:
            mx = int(hd_x + dirx * r * 1.3)
            my = int(hd_y + diry * r * 1.3)
            morsel_r = max(2, int(r * 0.85))
            if carry_type[i] == 2:  # nước - giọt xanh
                pygame.draw.circle(surf, (60, 140, 230), (mx, my), morsel_r)
                pygame.draw.circle(surf, (200, 230, 255), (mx, my), max(1, morsel_r // 2))
            else:  # thức ăn - đúng màu loại thức ăn thật đã nhặt
                fc = cfg.FOOD_TYPE_COLOR.get(int(carry_food_type[i]), (150, 115, 60))
                pygame.draw.circle(surf, fc, (mx, my), morsel_r)
            pygame.draw.circle(surf, (20, 15, 10), (mx, my), morsel_r, 1)
