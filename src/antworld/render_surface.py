"""Vẽ TẦNG 0 (mặt đất): lưới ô vuông, địa hình, thức ăn, lỗ tổ, kẻ thù, và
kiến trên mặt đất. Cũng chứa draw_ants() - dùng chung cho CẢ mặt đất lẫn
các tầng ngầm (render_underground.py gọi lại hàm này)."""
import math

import numpy as np
import pygame

from . import config as cfg

# --- Cache surface "vòng sáng" (ring) dùng cho hiệu ứng kiến ĐANG LÀM
# VIỆC (is_working) / ĐANG ĐƯỢC THEO DÕI (follow) trong draw_ants() bên
# dưới - trước đây MỖI CON kiến thỏa điều kiện lại cấp phát 1
# pygame.Surface(..., SRCALPHA) MỚI + vẽ 1 vòng tròn MỖI KHUNG HÌNH (dù
# hiệu ứng chỉ là 1 vòng tròn viền đơn giản, nhấp nháy chậm) - giờ LƯỢNG
# TỬ HÓA (quantize) bán kính + alpha thành 1 số ít "bậc" rời rạc rồi cache
# lại, tái sử dụng surface đã vẽ sẵn thay vì tạo mới - mắt người không
# phân biệt được sai khác nhỏ do lượng tử hóa gây ra (hiệu ứng vốn đã nhấp
# nháy liên tục), nhưng tránh cấp phát bộ nhớ + vẽ lại lặp đi lặp lại.
_ring_cache = {}


def _get_ring_surface(ring_r, ring_color, ring_alpha, width):
    """Trả về 1 surface vòng tròn viền (bán kính/alpha đã lượng tử hóa) từ
    cache - xem giải thích ở khai báo _ring_cache phía trên."""
    r_q = max(2, int(round(ring_r)))
    a_q = max(0, min(255, int(round(ring_alpha / 8.0)) * 8))
    key = (r_q, ring_color, a_q, width)
    surf = _ring_cache.get(key)
    if surf is None:
        if len(_ring_cache) > 300:
            _ring_cache.clear()  # phòng hờ tràn bộ nhớ - trong thực tế chỉ
                                  # có vài chục tổ hợp (bán kính, alpha) khác
                                  # nhau xuất hiện trong 1 ván chơi bình thường
        pad = width // 2 + 1  # đủ chỗ để nét viền dày (width>1) không bị
                               # cắt xén ở rìa surface
        size = r_q * 2 + pad * 2
        center = r_q + pad
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*ring_color, a_q), (center, center), r_q, width)
        _ring_cache[key] = surf
    return surf


# Chỉ dùng sprite food.png TÙY CHỈNH của người chơi cho loại PHỔ BIẾN
# (SEED) - các loại khác (vd NECTAR) LUÔN vẽ hình vuông màu phẳng theo
# FOOD_TYPE_COLOR, KHÔNG dùng sprite dù có sẵn.
#
# Lý do: đã thử "nhuộm màu" (tint) sprite gốc theo từng loại (cả nhân màu
# trực tiếp BLEND_RGBA_MULT lẫn tách độ sáng/luminosity rồi tô lại màu
# mới) nhưng đều cho kết quả gần giống hệt màu gốc, KHÓ phân biệt bằng
# mắt trên bản đồ (đã tự kiểm bằng ảnh chụp thực tế ở cả 2 cách) - vì
# sprite pixel-art gốc thường có dải sáng/tối riêng khiến việc "nhuộm lại"
# không cho màu thuần như mong muốn. Vẽ thẳng ô màu phẳng tuy kém đẹp hơn
# sprite tùy chỉnh nhưng ĐẢM BẢO CHẮC CHẮN 2 loại thức ăn luôn phân biệt
# được ngay từ xa - đây là yêu cầu quan trọng hơn tính thẩm mỹ ở đây.
def _use_sprite_for_food_type(ftype):
    return ftype == cfg.FOOD_TYPE_SEED


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


def _draw_grid_lines_local(cache, cell):
    """Giống draw_grid_lines() nhưng vẽ vào surface CỤC BỘ của bản đồ (gốc
    tọa độ (0,0) LUÔN là góc trên-trái bản đồ, không phụ thuộc camera đang
    pan tới đâu) - dùng khi dựng _build_terrain_cache() (xem giải thích ở
    đó vì sao tách riêng thành 1 surface cache thay vì vẽ lại mỗi khung
    hình theo tọa độ màn hình như draw_grid_lines() ở trên)."""
    size = cache.get_width()
    g = 0.0
    while g <= size + 0.5:
        pygame.draw.line(cache, (0, 0, 0, 40), (g, 0), (g, size), 1)
        pygame.draw.line(cache, (0, 0, 0, 40), (0, g), (size, g), 1)
        g += cell


def _build_terrain_cache(state, cell, step, r):
    """Dựng SẴN 1 surface chứa NỀN ĐẤT + LƯỚI Ô VUÔNG + ĐÁ/NƯỚC cho toàn
    bộ bản đồ, ở đúng kích thước pixel hiện tại (phụ thuộc zoom) nhưng
    KHÔNG phụ thuộc camera đang pan tới đâu (luôn vẽ như thể góc (0,0) bản
    đồ nằm tại (0,0) surface) - để mỗi khung hình chỉ cần 1 LẦN BLIT surface
    này tại đúng vị trí camera hiện tại, thay vì lặp lại toàn bộ vòng lặp
    quét ~GRID_SIZE^2 ô + vẽ từng đường lưới MỖI KHUNG HÌNH dù địa hình
    99% thời gian KHÔNG hề đổi (chỉ đổi khi người chơi tự đặt/xóa đá/nước -
    xem terrain_version trong world.py). Được gọi lại (dựng mới) CHỈ KHI
    cache_key ở draw_surface_layer() đổi (terrain/zoom/lưới bật-tắt đổi)."""
    surface_world = state.surface_world
    size = max(1, int(round(cfg.GRID_SIZE * cell)))
    cache = pygame.Surface((size, size))
    cache.fill(cfg.COLOR_GROUND_FILL)

    if state.grid_visible and cell >= 3:
        _draw_grid_lines_local(cache, cell)

    terrain = surface_world.terrain
    rock_sprite = state.sprites.get_static("rock.png", r) if state.sprites.has("rock.png") else None
    water_sprite = state.sprites.get_static("water.png", r) if state.sprites.has("water.png") else None

    # Chỉ lặp qua các Ô THỰC SỰ có địa hình (numpy tìm sẵn bằng np.where)
    # thay vì quét python thủ công qua MỌI ô của lưới (đa số ô trống) -
    # dù bước này giờ chỉ chạy khi cache cần dựng lại (hiếm), vẫn giữ cách
    # làm nhanh nhất có thể để không giật hình ngay tại khung hình đó.
    sampled = terrain[0:cfg.GRID_SIZE:step, 0:cfg.GRID_SIZE:step]
    txi, tyi = np.where(sampled != cfg.TERRAIN_EMPTY)
    for tx, ty in zip((txi * step).tolist(), (tyi * step).tolist()):
        t = terrain[tx, ty]
        cx = (tx + 0.5) * cell
        cy = (ty + 0.5) * cell
        sprite = rock_sprite if t == cfg.TERRAIN_ROCK else water_sprite
        if sprite is not None:
            cache.blit(sprite, sprite.get_rect(center=(int(cx), int(cy))))
        else:
            color = (120, 118, 112) if t == cfg.TERRAIN_ROCK else (70, 140, 200)
            pygame.draw.rect(cache, color, (cx - r / 2, cy - r / 2, r, r))
    return cache


def _get_terrain_cache(state, cell, step, r):
    """Trả về surface nền đất+lưới+địa hình đã cache (xem
    _build_terrain_cache) - chỉ dựng lại khi 1 trong các yếu tố ảnh hưởng
    tới hình dáng của nó thực sự đổi (terrain_version tăng khi đặt/xóa đá
    nước, cell/step/r đổi khi zoom, grid_visible bật/tắt, hoặc surface_world
    bị THAY HẲN object khác - xem load_game()).

    QUAN TRỌNG: cache được lưu trên `state` (GameState), KHÔNG lưu trên
    `state.surface_world` - vì surface_world bị pickle NGUYÊN VẸN mỗi khi
    lưu ván chơi (xem GameState.save_game() trong game_state.py). Một
    pygame.Surface không pickle được (lỗi "cannot pickle
    'pygame.surface.Surface' object"), nên nếu gắn cache LÊN surface_world,
    chỉ cần người chơi vẽ ra màn hình 1 lần (luôn xảy ra) rồi bấm Lưu ván
    chơi là lưu sẽ LỖI NGAY. `state` thì không bao giờ bị pickle, nên gắn
    cache ở đây là an toàn."""
    surface_world = state.surface_world
    key = (surface_world.terrain_version, cell, step, r, state.grid_visible)
    # So sánh THEO ĐỊNH DANH object (`is`, không phải `==`/id() tái sử dụng
    # được sau khi object cũ bị garbage-collected) để chắc chắn phát hiện
    # đúng lúc load_game() thay hẳn 1 SurfaceWorld khác, ngay cả khi
    # terrain_version của object mới trùng ngẫu nhiên với object cũ.
    if getattr(state, "_terrain_cache_world", None) is not surface_world or getattr(state, "_terrain_cache_key", None) != key:
        state._terrain_cache_surf = _build_terrain_cache(state, cell, step, r)
        state._terrain_cache_key = key
        state._terrain_cache_world = surface_world
    return state._terrain_cache_surf


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
    surface_world = state.surface_world

    # --- nền đất + lưới ô vuông + đá/nước: LẤY TỪ CACHE thay vì vẽ lại
    # từ đầu mỗi khung hình - xem _build_terrain_cache()/_get_terrain_cache()
    # phía trên: 3 lớp này gộp thành ĐÚNG 1 lần blit ở đây, chỉ dựng lại
    # (chậm hơn) khi terrain/zoom/bật-tắt lưới thực sự thay đổi, chứ không
    # phải mỗi khung hình trong số 60 khung hình/giây dù bản đồ đứng yên. ---
    step = max(1, int(1 / max(cell / cfg.BASE_CELL_PX, 0.05)))
    r = max(1, int(round(cell * step)))  # LẤP ĐẦY hẳn cả ô, không chừa viền
    terrain_cache = _get_terrain_cache(state, cell, step, r)
    x0, y0 = camera.world_to_screen(0, 0, state.CENTER_X, state.CENTER_Y)
    surf.blit(terrain_cache, (int(round(x0)), int(round(y0))))

    # --- đường mùi (pheromone) - vẽ TRƯỚC thức ăn/kiến để nằm dưới, như
    # dấu vết in trên mặt đất ---
    draw_pheromone_trails(state, surf)

    # --- thức ăn (lấy mẫu thưa) - vẽ HÌNH VUÔNG Ở GIỮA từng ô lưới nhưng
    # NHỎ HƠN cả ô (chừa kẽ hở quanh), KHÁC với đá/nước ở trên (lấp đầy
    # kín cả ô) - vì thức ăn KHÔNG PHẢI vật cản, kiến vẫn đi xuyên/đi qua
    # kẽ hở quanh thức ăn bình thường, chỉ đá/nước mới thật sự chặn đường
    # (xem _avoid_obstacles trong ants.py) - kích thước nhỏ hơn giúp NHÌN
    # RA NGAY sự khác biệt này, không tưởng nhầm thức ăn cũng chặn đường
    # như đá/nước. Dùng sprite food.png tùy chỉnh nếu có.
    #
    # Thức ăn (khác đá/nước) đổi liên tục mỗi tick (kiến ăn dần) nên KHÔNG
    # cache được như trên - nhưng vẫn tránh quét python qua MỌI ô của lưới
    # (đa số trống): dùng np.where() để chỉ lấy đúng các ô có thức ăn rồi
    # tính sẵn tọa độ màn hình HÀNG LOẠT bằng numpy, thay vì gọi
    # world_to_screen() + kiểm tra food[gx,gy] cho TỪNG ô trong số tới
    # ~1600 ô mỗi khung hình. ---
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

    fxi, fyi = np.where(food[0:cfg.GRID_SIZE:fstep, 0:cfg.GRID_SIZE:fstep] > 0.5)
    if len(fxi) > 0:
        gxs = (fxi * fstep).astype(np.float32) + 0.5
        gys = (fyi * fstep).astype(np.float32) + 0.5
        fsxs, fsys = camera.world_to_screen(gxs, gys, state.CENTER_X, state.CENTER_Y)
        gx_int = (fxi * fstep)
        gy_int = (fyi * fstep)
        for i in range(len(fxi)):
            # ÉP KIỂU về float/int THƯỜNG của Python (không phải
            # numpy.float32) - pygame.draw.rect() không chấp nhận
            # numpy.float32 trong tuple rect ở 1 số phiên bản (lỗi
            # "rect argument is invalid") - lỗi này TỪNG BỊ CHE GIẤU vì
            # nhánh sprite (food_sprite is not None) luôn được chọn khi có
            # sẵn sprite food.png tùy chỉnh, chỉ lộ ra khi thêm loại thức
            # ăn KHÔNG dùng sprite (NECTAR, xem _use_sprite_for_food_type).
            sx, sy = float(fsxs[i]), float(fsys[i])
            ftype = int(food_type[gx_int[i], gy_int[i]])
            if food_sprite is not None and _use_sprite_for_food_type(ftype):
                surf.blit(food_sprite, food_sprite.get_rect(center=(int(sx), int(sy))))
            else:
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
            ring_surf = _get_ring_surface(ring_r, (255, 235, 120), ring_alpha, 2)
            surf.blit(ring_surf, ring_surf.get_rect(center=(int(sx), int(sy))))

        # --- Con kiến ĐANG ĐƯỢC CAMERA THEO DÕI: 1 vòng tròn xanh lá sáng
        # nhấp nháy RÕ RÀNG bao quanh, to hơn hẳn vòng "đang làm việc" ở
        # trên, để không thể nhầm lẫn giữa hàng chục con kiến khác ---
        if state.follow_colony is colony_obj and idx[i] == state.follow_idx:
            fpulse = 0.5 + 0.5 * math.sin(state.frame_counter * 0.2)
            fring_r = max(4, int(r * 2.6 + fpulse * r * 0.6))
            fring_surf = _get_ring_surface(fring_r, (80, 255, 120), 220, 3)
            surf.blit(fring_surf, fring_surf.get_rect(center=(int(sx), int(sy))))

        # --- Trạng thái ĐANG THA MỒI được thể hiện qua chính "hình dạng"
        # con kiến, KHÔNG đính kèm icon rời: nếu người chơi có sprite tùy
        # chỉnh thì đã tự chuyển sang file "..._carry.png" ở trên (dáng
        # ngậm mồi vẽ sẵn trong ảnh đó); nếu dùng hình vector mặc định thì
        # đổi hẳn sang `color_carry` (màu cam) khác biệt rõ với màu bình
        # thường - không vẽ thêm viên mồi/dây nối rời như bản trước (từng
        # gây cảm giác "2 khối chồng nhau trông như sai trạng thái" khi
        # phóng to, xem lịch sử sửa lỗi carry-morsel).
