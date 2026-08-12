"""Vẽ TẦNG 0 (mặt đất): lưới ô vuông, địa hình, thức ăn, lỗ tổ, kẻ thù, và
kiến trên mặt đất. Cũng chứa draw_ants() - dùng chung cho CẢ mặt đất lẫn
các tầng ngầm (render_underground.py gọi lại hàm này)."""
import math

import numpy as np
import pygame

from . import config as cfg


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

    # --- địa hình: đá + nước (lấy mẫu thưa theo bước lưới cho nhanh) -
    # vẽ Ở GIỮA từng Ô LƯỚI (gx+0.5, gy+0.5), KHÔNG phải tại điểm giao 2
    # đường lưới (gx, gy) - để trông như 1 viên gạch/tường nằm gọn TRONG 1
    # ô, thay vì bị 4 đường lưới cắt ngang qua giữa. Dùng sprite tùy chỉnh
    # (rock.png/water.png) nếu người chơi đã cung cấp, không thì vẽ vuông
    # màu như trước. ---
    terrain = surface_world.terrain
    step = max(1, int(1 / max(cell / cfg.BASE_CELL_PX, 0.05)))
    r = max(1, int(round(cell * step)))  # LẤP ĐẦY hẳn cả ô, không chừa viền
    rock_sprite = state.sprites.get_static("rock.png", r) if state.sprites.has("rock.png") else None
    water_sprite = state.sprites.get_static("water.png", r) if state.sprites.has("water.png") else None
    for gx in range(0, cfg.GRID_SIZE, step):
        for gy in range(0, cfg.GRID_SIZE, step):
            t = terrain[gx, gy]
            if t == cfg.TERRAIN_EMPTY:
                continue
            sx, sy = camera.world_to_screen(gx + 0.5, gy + 0.5, state.CENTER_X, state.CENTER_Y)
            sprite = rock_sprite if t == cfg.TERRAIN_ROCK else water_sprite
            if sprite is not None:
                surf.blit(sprite, sprite.get_rect(center=(int(sx), int(sy))))
            else:
                color = (120, 118, 112) if t == cfg.TERRAIN_ROCK else (70, 140, 200)
                pygame.draw.rect(surf, color, (sx - r / 2, sy - r / 2, r, r))

    # --- đường mùi (pheromone) - vẽ TRƯỚC thức ăn/kiến để nằm dưới, như
    # dấu vết in trên mặt đất ---
    draw_pheromone_trails(state, surf)

    # --- thức ăn (lấy mẫu thưa) - vẽ HÌNH VUÔNG Ở GIỮA từng ô lưới nhưng
    # NHỎ HƠN cả ô (chừa kẽ hở quanh), KHÁC với đá/nước ở trên (lấp đầy
    # kín cả ô) - vì thức ăn KHÔNG PHẢI vật cản, kiến vẫn đi xuyên/đi qua
    # kẽ hở quanh thức ăn bình thường, chỉ đá/nước mới thật sự chặn đường
    # (xem _avoid_obstacles trong ants.py) - kích thước nhỏ hơn giúp NHÌN
    # RA NGAY sự khác biệt này, không tưởng nhầm thức ăn cũng chặn đường
    # như đá/nước. Dùng sprite food.png tùy chỉnh nếu có. ---
    food = surface_world.food
    food_type = surface_world.food_type
    fstep = 1 if cell > 10 else 2
    # Giới hạn trần ở 82% kích thước ô lưới dù ENTITY_SPRITE_SCALE lớn cỡ
    # nào - PHẢI luôn nhỏ hơn rõ rệt so với đá/nước (vốn lấp ĐẦY TRỌN 1 ô,
    # xem r = cell * step ở trên) để người chơi còn phân biệt được "thức
    # ăn đi xuyên qua được" khác với "đá/nước chặn đường" chỉ bằng mắt.
    food_size = min(int(cell * fstep * 0.55 * cfg.ENTITY_SPRITE_SCALE), int(cell * fstep * 0.82))
    food_size = max(3, food_size)
    food_sprite = state.sprites.get_static("food.png", food_size) if state.sprites.has("food.png") else None
    for gx in range(0, cfg.GRID_SIZE, fstep):
        for gy in range(0, cfg.GRID_SIZE, fstep):
            if food[gx, gy] > 0.5:
                sx, sy = camera.world_to_screen(gx + 0.5, gy + 0.5, state.CENTER_X, state.CENTER_Y)
                if food_sprite is not None:
                    surf.blit(food_sprite, food_sprite.get_rect(center=(int(sx), int(sy))))
                else:
                    ftype = int(food_type[gx, gy])
                    fc = cfg.FOOD_TYPE_COLOR.get(ftype, (60, 150, 60))
                    pygame.draw.rect(surf, fc, (sx - food_size / 2, sy - food_size / 2, food_size, food_size))

    # --- lỗ tổ - dùng sprite nest_main.png tùy chỉnh nếu có, không thì vẽ
    # vòng tròn màu như trước ---
    sx, sy = camera.world_to_screen(cfg.NEST_POS[0], cfg.NEST_POS[1], state.CENTER_X, state.CENTER_Y)
    r = max(3, int(cell * 1.4 * cfg.ENTITY_SPRITE_SCALE))
    if state.sprites.has("nest_main.png"):
        sprite = state.sprites.get_static("nest_main.png", r * 2)
        surf.blit(sprite, sprite.get_rect(center=(int(sx), int(sy))))
    else:
        pygame.draw.circle(surf, (30, 22, 14), (int(sx), int(sy)), r)
        pygame.draw.circle(surf, (0, 0, 0), (int(sx), int(sy)), r, 2)

    # --- kẻ thù - dùng sprite enemy.png tùy chỉnh nếu có (tự xoay theo
    # đúng hướng di chuyển thật, giống kiến), không thì vẽ hình thoi đỏ ---
    enemy = state.enemy
    if enemy.active:
        sx, sy = camera.world_to_screen(enemy.x, enemy.y, state.CENTER_X, state.CENTER_Y)
        r = max(3, int(cell * 0.6 * cfg.ENTITY_SPRITE_SCALE))
        if state.sprites.has("enemy.png"):
            sprite = state.sprites.get_rotated("enemy.png", r * 2, float(enemy.theta))
            surf.blit(sprite, sprite.get_rect(center=(int(sx), int(sy))))
        else:
            pts = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
            pygame.draw.polygon(surf, (220, 30, 30), pts)

    draw_ants(state, surf, state.colony, (25, 25, 25), (215, 120, 30))
    draw_ants(state, surf, state.invasion, (80, 15, 15), (150, 40, 20))


def draw_ants(state, surf, colony_obj, color_normal, color_carry, depth_filter=0, underground=False):
    """Vẽ kiến thành 1 HÌNH DÁNG CON KIẾN THẬT (đầu-ngực-bụng nối theo
    đúng hướng đang di chuyển) thay vì 1 chấm tròn đơn giản - để không
    bị lẫn với các chấm khác trong phòng (thức ăn, ấu trùng, trứng, xác,
    vân sàn...). Lính (ROLE_MAJOR) có đầu to/bạnh hơn hẳn (như có hàm
    khỏe). Mỗi CHỨC NĂNG của thợ nhỏ có 1 chấm huy hiệu màu riêng trên
    bụng để phân biệt ngay cả khi đứng lẫn nhau: lính gác = vàng, chuyên
    chăm ấu trùng (nurse) = hồng, chuyên chăm trứng+chúa (attendant) =
    tím - thợ kiếm ăn (forager, đa số) không có huy hiệu.

    `underground=True`: vẽ thêm 1 VIỀN SÁNG MỎNG quanh thân để vẫn nhìn rõ
    trong hành lang rất tối, THAY VÌ đổi hẳn sang màu khác hẳn (trước đây
    dưới hầm dùng cả bộ màu xám trắng riêng, khiến cùng 1 con kiến trông
    như đổi loài giữa mặt đất và dưới hầm - gây cảm giác "đổi màu loạn").
    Giờ màu thân dưới hầm GẦN GIỐNG màu thật trên mặt đất, chỉ viền thêm
    cho nổi lên nền hành lang tối."""
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
    is_major = colony_obj.role[idx] == cfg.ROLE_MAJOR
    is_guard = colony_obj.is_guard[idx]
    job = colony_obj.job[idx]
    is_nanitic = colony_obj.is_nanitic[idx]
    is_working = colony_obj.state[idx] == cfg.STATE_DWELL
    sxs = CENTER_X + (xs - camera.cx) * cell
    sys_ = CENTER_Y + (ys - camera.cy) * cell

    # Tên sprite TÙY CHỌN cho đàn này (ant_worker_main*/ant_invader*) - xem
    # sprite_manager.py. None nếu colony_obj không xác định (an toàn phòng
    # hờ) - khi đó luôn vẽ vector như cũ.
    if colony_obj is state.colony:
        sprite_prefix = "ant_worker_main"
    elif colony_obj is state.invasion:
        sprite_prefix = "ant_invader"
    else:
        sprite_prefix = None

    for i in range(len(idx)):
        sx, sy = sxs[i], sys_[i]
        if sx < -10 or sx > state.SCREEN_W + 10 or sy < -10 or sy > CANVAS_H + 10:
            continue
        base_r = cell * 0.155 * cfg.ENTITY_SPRITE_SCALE
        major = bool(is_major[i])
        r = base_r * (cfg.MAJOR_SIZE_SCALE if major else 1.0)
        if is_nanitic[i]:
            # Thợ lứa đầu (lập tổ) - nhỏ con hơn hẳn, xem NANITIC_SIZE_SCALE
            r *= cfg.NANITIC_SIZE_SCALE
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

        # --- Ảnh sprite tùy chỉnh (nếu người chơi đã cung cấp) THAY THẾ
        # phần vẽ vector thân/đầu/râu bên dưới - mọi lớp phủ khác (huy
        # hiệu, vòng sáng, mồi tha) vẫn vẽ đè lên như cũ dù dùng sprite hay
        # vector, để không mất chức năng nào khi chuyển sang ảnh tùy chỉnh.
        sprite_img = None
        if sprite_prefix is not None:
            sname = sprite_prefix + ("_carry.png" if carrying[i] else ".png")
            if state.sprites.has(sname):
                size_px = max(4, int(r * 3.6))
                sprite_img = state.sprites.get_rotated(sname, size_px, th)

        if sprite_img is not None:
            rect = sprite_img.get_rect(center=(int(sx), int(sy)))
            surf.blit(sprite_img, rect)
        else:
            if underground:
                # Viền sáng mỏng quanh cả 3 đốt thân để vẫn nổi rõ trên nền
                # hành lang rất tối, KHÔNG cần đổi hẳn màu thân (giữ đúng màu
                # thật của loài, chỉ mượn thêm viền để dễ nhìn trong bóng tối)
                rim = (150, 140, 125)
                pygame.draw.circle(surf, rim, (int(abd_x), int(abd_y)), abdomen_r + 1)
                pygame.draw.circle(surf, rim, (int(sx), int(sy)), thorax_r + 1)
                pygame.draw.circle(surf, rim, (int(hd_x), int(hd_y)), head_r + 1)

            pygame.draw.circle(surf, color, (int(abd_x), int(abd_y)), abdomen_r)
            pygame.draw.circle(surf, color, (int(sx), int(sy)), thorax_r)
            pygame.draw.circle(surf, head_color, (int(hd_x), int(hd_y)), head_r)

            if r >= 2.6:  # đủ to (zoom gần) mới vẽ thêm râu, tránh rối ở xa
                ant_len = head_r * 0.9
                for side in (-1, 1):
                    ax = hd_x + dirx * ant_len + perp_x * head_r * 0.5 * side
                    ay = hd_y + diry * ant_len + perp_y * head_r * 0.5 * side
                    pygame.draw.line(surf, head_color, (int(hd_x), int(hd_y)), (int(ax), int(ay)), 1)

        if is_guard[i]:  # lính gác: 1 chấm sáng nhỏ trên bụng để phân biệt
            badge_r = max(1, int(abdomen_r * 0.4))
            pygame.draw.circle(surf, (255, 225, 90), (int(abd_x), int(abd_y)), badge_r)
        elif job[i] == cfg.JOB_NURSE:  # chuyên chăm ấu trùng: chấm hồng
            badge_r = max(1, int(abdomen_r * 0.4))
            pygame.draw.circle(surf, (255, 175, 205), (int(abd_x), int(abd_y)), badge_r)
        elif job[i] == cfg.JOB_ATTENDANT:  # chuyên chăm trứng+chúa: chấm tím
            badge_r = max(1, int(abdomen_r * 0.4))
            pygame.draw.circle(surf, (200, 150, 240), (int(abd_x), int(abd_y)), badge_r)

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

        # --- Con kiến ĐANG ĐƯỢC CAMERA THEO DÕI: 1 vòng tròn xanh lá sáng
        # nhấp nháy RÕ RÀNG bao quanh, to hơn hẳn vòng "đang làm việc" ở
        # trên, để không thể nhầm lẫn giữa hàng chục con kiến khác ---
        if state.follow_colony is colony_obj and idx[i] == state.follow_idx:
            fpulse = 0.5 + 0.5 * math.sin(state.frame_counter * 0.2)
            fring_r = max(4, int(r * 2.6 + fpulse * r * 0.6))
            fring_surf = pygame.Surface((fring_r * 2 + 4, fring_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(
                fring_surf, (80, 255, 120, 220), (fring_r + 2, fring_r + 2), fring_r, 3
            )
            surf.blit(fring_surf, (int(sx) - fring_r - 2, int(sy) - fring_r - 2))

        # --- Trạng thái ĐANG THA MỒI được thể hiện qua chính "hình dạng"
        # con kiến, KHÔNG đính kèm icon rời: nếu người chơi có sprite tùy
        # chỉnh thì đã tự chuyển sang file "..._carry.png" ở trên (dáng
        # ngậm mồi vẽ sẵn trong ảnh đó); nếu dùng hình vector mặc định thì
        # đổi hẳn sang `color_carry` (màu cam) khác biệt rõ với màu bình
        # thường - không vẽ thêm viên mồi/dây nối rời như bản trước (từng
        # gây cảm giác "2 khối chồng nhau trông như sai trạng thái" khi
        # phóng to, xem lịch sử sửa lỗi carry-morsel).
