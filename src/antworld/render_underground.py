"""Vẽ CÁC TẦNG NGẦM (gác cửa, kho, bể nước, trứng, ấu trùng, chúa, nghĩa
địa, phòng tự đào): sàn phòng, nội dung riêng của từng phòng chức năng, và
kiến đang ở tầng đó (dùng lại draw_ants từ render_surface)."""
import math

import numpy as np
import pygame

from . import config as cfg
from .render_surface import draw_ants
from .fonts import render_cached


def layer_name(state, depth):
    """Tên tầng THEO ĐÚNG TRẠNG THÁI THẬT của ván đang chơi - KHÔNG dùng
    bảng tên cố định theo hằng số DEPTH_* nữa (trước đây làm vậy, dẫn tới
    lỗi hiện SẴN tên "Kho thức ăn"/"Phòng trứng"... cho những tầng CHƯA
    HỀ ĐƯỢC ĐÀO). Với hệ thống "đào tới đâu có chức năng tới đó" (xem
    UndergroundWorld.unlock_room()), 1 tầng CÓ THỂ chưa có phòng nào thật
    sự tồn tại ở đó (còn đang gộp chung vào Phòng chúa) - trường hợp đó
    trả về "(chưa đào)" thay vì đoán bừa tên phòng."""
    if depth == 0:
        return "Mặt đất"
    uworld = state.underground_world
    names = [name.strip() for (room_id, name, _pos, _r, _color, d) in uworld.rooms
             if d == depth and room_id in uworld.unlocked_rooms]
    return "/".join(names) if names else "(chưa đào)"


def _blob_points(cx, cy, base_r, seed_key, n_points=28, irregularity=0.22):
    """Tạo đường viền HÌNH DẠNG TỰ NHIÊN như 1 khoang hang động thật (lồi
    lõm mềm mại), KHÔNG PHẢI hình tròn hoàn hảo - dùng vài họa ba sin biên
    độ/pha ngẫu nhiên nhưng CỐ ĐỊNH theo seed_key (mỗi phòng 1 hình dạng
    riêng, KHÔNG đổi giữa các khung hình, vì seed_key giống nhau mỗi lần
    gọi lại cho đúng phòng đó). Trộn vài tần số khác nhau (2-5) để đường
    viền mượt, không bị gai nhọn như nhiễu ngẫu nhiên thuần túy."""
    rng_local = np.random.RandomState(seed_key * 911 + 41)
    n_harmonics = 4
    amps = rng_local.uniform(0.3, 1.0, n_harmonics)
    amps = amps / amps.sum() * irregularity
    freqs = np.arange(2, 2 + n_harmonics)
    phases = rng_local.uniform(0, 2 * np.pi, n_harmonics)
    angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    radius_mult = np.ones(n_points)
    for a, f, p in zip(amps, freqs, phases):
        radius_mult = radius_mult + a * np.sin(angles * f + p)
    return [
        (cx + math.cos(a) * base_r * rm, cy + math.sin(a) * base_r * rm)
        for a, rm in zip(angles, radius_mult)
    ]


def draw_room_floor(surf, cx, cy, r_px, room_rgb, seed_key):
    """Vẽ 1 phòng ngầm như 1 KHU VỰC SÀN thật sự (không phải hình tròn
    trang trí) - có viền tường đất bo tròn + lớp sàn sáng hơn bên trong,
    để mắt nhận ra ngay đây là không gian kiến có thể đi lại/hoạt động
    bên trong, khác hẳn đường hành lang mảnh. HÌNH DẠNG là 1 khoang hang
    động TỰ NHIÊN (lồi lõm nhẹ, xem _blob_points) - KHÔNG phải hình tròn
    hoàn hảo, mỗi phòng 1 dáng riêng (nhưng cố định, không "nhũn" theo
    thời gian) để trông sống động và tự nhiên hơn hẳn."""
    wall_color = tuple(max(0, c - 60) for c in room_rgb)
    floor_color = tuple(min(255, c + 45) for c in room_rgb)
    wall_pts = _blob_points(cx, cy, r_px + max(2, int(r_px * 0.12)), seed_key)
    floor_pts = _blob_points(cx, cy, r_px, seed_key)
    inner_pts = _blob_points(cx, cy, max(1, int(r_px * 0.78)), seed_key)
    pygame.draw.polygon(surf, wall_color, wall_pts)
    pygame.draw.polygon(surf, floor_color, floor_pts)
    pygame.draw.polygon(surf, room_rgb, inner_pts)
    pygame.draw.polygon(surf, (0, 0, 0), wall_pts, 2)


def _grid_positions(n, cx, cy, r_px, icon_r, group_size=5):
    """Sắp xếp n icon thành LƯỚI GỌN GÀNG (hàng-cột đều đặn) quanh tâm
    (cx, cy), THAY VÌ rải ngẫu nhiên như trước - để có thể ĐẾM BẰNG MẮT
    THƯỜNG dễ dàng. Cứ mỗi `group_size` icon liên tiếp trong 1 hàng thì
    cách thêm 1 khoảng nhỏ (giống cách đếm "5 que 1 bó") để nhìn phát biết
    ngay số lượng gần đúng mà không cần đếm từng cái một.

    Trả về (positions, icon_r_dung) - icon_r_dung có thể NHỎ HƠN icon_r
    truyền vào: hàm tự kiểm tra xem khối lưới (rộng LẪN cao) có vừa trong
    đường kính khả dụng của phòng hay không; nếu số icon quá nhiều khiến
    khối lưới tràn ra (dễ xảy ra khi kho gần đầy VÀ ENTITY_SPRITE_SCALE
    lớn - icon to hơn nhưng số hàng cần thiết không đổi), tự động THU NHỎ
    TOÀN BỘ icon (giữ đều kích thước với nhau) cho tới khi vừa khít, thay
    vì để icon tràn ra ngoài viền phòng. Nơi gọi PHẢI dùng icon_r trả về
    này để vẽ, không dùng icon_r ban đầu truyền vào nữa."""
    if n <= 0:
        return [], icon_r

    # Vùng khả dụng bên trong phòng để xếp icon - hình VUÔNG nội tiếp gần
    # đúng bên trong hình tròn bán kính r_px, chừa biên an toàn (phòng vẽ
    # dạng "khối u" méo mó chứ không tròn tuyệt đối - xem _blob_points).
    usable = r_px * 1.3

    def layout_metrics(radius):
        spacing = radius * 2.3
        group_gap = radius * 1.15
        per_row = max(1, int(usable / spacing))
        n_rows = math.ceil(n / per_row)
        # Bề rộng thật của 1 hàng ĐẦY ĐỦ (per_row icon, cộng khoảng cách
        # nhóm mỗi group_size icon) - dùng để kiểm tra tràn ngang
        cols_in_full_row = min(n, per_row)
        row_w = (cols_in_full_row - 1) * spacing + (cols_in_full_row // group_size) * group_gap if cols_in_full_row > 0 else 0
        col_h = (n_rows - 1) * spacing
        return spacing, group_gap, per_row, row_w, col_h

    radius = icon_r
    spacing, group_gap, per_row, row_w, col_h = layout_metrics(radius)
    # Hệ số thu nhỏ cần thiết để CẢ bề rộng lẫn chiều cao khối lưới đều
    # nằm trong `usable` - lấy hệ số NHỎ HƠN (khắt khe hơn) trong 2 chiều.
    shrink = min(usable / row_w if row_w > 0 else 1.0, usable / col_h if col_h > 0 else 1.0, 1.0)
    if shrink < 1.0:
        radius = max(1.0, radius * shrink)
        spacing, group_gap, per_row, row_w, col_h = layout_metrics(radius)

    positions = []
    for i in range(n):
        row = i // per_row
        col = i % per_row
        x = col * spacing + (col // group_size) * group_gap
        y = row * spacing
        positions.append((x, y))
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    off_x = cx - (min(xs) + max(xs)) / 2
    off_y = cy - (min(ys) + max(ys)) / 2
    return [(x + off_x, y + off_y) for x, y in positions], radius


def draw_storage_pile(state, surf, cx, cy, r_px, amount, seed_key):
    """Kho thức ăn KHÔNG chỉ là 1 con số - vẽ luôn số thức ăn ĐANG LƯU
    TRỮ THẬT SỰ dưới dạng các viên thức ăn xếp THÀNH LƯỚI GỌN GÀNG (không
    rải ngẫu nhiên - xem _grid_positions) để đếm bằng mắt thường dễ dàng,
    số hàng/cột tăng theo lượng tồn kho hiện tại (1 icon = ĐÚNG 1 đơn vị
    thức ăn - xem STORAGE_FOOD_PER_ICON). TÁI DÙNG sprite food.png tùy
    chỉnh nếu có (đúng loại thức ăn thật đang dùng trên mặt đất), không
    thì vẽ viên tròn màu như trước - chỉ ngả sáng/tối nhẹ ngẫu nhiên giữa
    các viên để đống trông có khối thay vì phẳng lì 1 màu tuyệt đối."""
    n_icons = int(np.clip(amount / cfg.STORAGE_FOOD_PER_ICON, 0, cfg.STORAGE_MAX_ICONS))
    if n_icons <= 0:
        return
    r = max(2, int(r_px * 0.085 * cfg.ENTITY_SPRITE_SCALE))
    positions, r = _grid_positions(n_icons, cx, cy, r_px, r)
    r = max(2, int(r))
    sprite = state.sprites.get_static("food.png", r * 2) if state.sprites.has("food.png") else None
    rng_local = np.random.RandomState(seed_key * 733 + 5)
    shade_jitter = rng_local.uniform(-22, 22, n_icons)
    base = cfg.FOOD_TYPE_COLOR[cfg.FOOD_TYPE_SEED]
    for i, (px, py) in enumerate(positions):
        px, py = int(px), int(py)
        if sprite is not None:
            surf.blit(sprite, sprite.get_rect(center=(px, py)))
            continue
        j = shade_jitter[i]
        color = tuple(int(np.clip(c + j, 20, 255)) for c in base)
        pygame.draw.circle(surf, (35, 25, 15), (px, py), r + 1)  # viền tối cho nổi khối
        pygame.draw.circle(surf, color, (px, py), r)
        hi = max(1, int(r * 0.4))
        pygame.draw.circle(surf, (255, 255, 230), (px - r // 3, py - r // 3), hi)  # điểm sáng


def draw_pupae(state, surf, cx, cy, r_px, colony_obj, seed_key):
    """Phòng nhộng THẬT SỰ có nhộng bên trong - mỗi nhộng là 1 CÁI KÉN hình
    bầu dục (tơ bọc quanh, màu vàng nhạt/nâu đất đặc trưng), KHÁC HẲN dáng
    ấu trùng (mập tròn, trắng nhợt) hay trứng (chấm nhỏ trắng ngà) - càng
    gần "nở" (growth cao) kén càng đậm màu hơn, đúng thực tế (kén nhộng
    sậm màu dần khi kiến trưởng thành bên trong sắp hoàn thiện). Dùng
    sprite pupa.png tùy chỉnh nếu người chơi đã cung cấp."""
    active_idx = np.where(colony_obj.pupa_active)[0]
    if len(active_idx) == 0:
        return
    rng_local = np.random.RandomState(seed_key * 419 + 13)
    ang = rng_local.uniform(0, 2 * np.pi, cfg.PUPA_MAX_COUNT)
    rad = np.sqrt(rng_local.uniform(0, 1, cfg.PUPA_MAX_COUNT)) * r_px * 0.62
    tilt = rng_local.uniform(-0.5, 0.5, cfg.PUPA_MAX_COUNT)
    sprite_size = max(4, int(r_px * 0.28 * cfg.ENTITY_SPRITE_SCALE))
    sprite = state.sprites.get_static("pupa.png", sprite_size) if state.sprites.has("pupa.png") else None
    for i in active_idx:
        dx = int(math.cos(ang[i]) * rad[i])
        dy = int(math.sin(ang[i]) * rad[i])
        px, py = cx + dx, cy + dy
        if sprite is not None:
            rotated = pygame.transform.rotate(sprite, math.degrees(tilt[i]))
            surf.blit(rotated, rotated.get_rect(center=(px, py)))
            continue
        growth = float(colony_obj.pupa_growth[i])
        w = max(4, int(r_px * 0.13))
        h = max(3, int(r_px * 0.085))
        # Màu kén đậm dần theo growth: vàng rơm nhạt lúc mới hóa nhộng ->
        # nâu vàng đậm lúc sắp nở
        shade = 0.55 + 0.45 * growth
        color = (int(215 * shade + 40 * (1 - shade)), int(180 * shade + 40 * (1 - shade)), int(110 * shade + 30 * (1 - shade)))
        cocoon = pygame.Surface((w * 2 + 4, h * 2 + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(cocoon, (60, 45, 25), (0, 0, w * 2 + 4, h * 2 + 4))
        pygame.draw.ellipse(cocoon, color, (2, 2, w * 2, h * 2))
        # 2 sợi tơ mảnh ngang thân kén cho ra dáng "bọc kén" thật
        pygame.draw.line(cocoon, (60, 45, 25), (w * 0.5, h * 0.4), (w * 0.5, h * 1.6), 1)
        pygame.draw.line(cocoon, (60, 45, 25), (w * 1.5, h * 0.4), (w * 1.5, h * 1.6), 1)
        rotated = pygame.transform.rotate(cocoon, math.degrees(tilt[i]))
        rect = rotated.get_rect(center=(px, py))
        surf.blit(rotated, rect)


def draw_larvae(state, surf, cx, cy, r_px, colony_obj, seed_key):
    """Phòng ấu trùng THẬT SỰ có ấu trùng bên trong - mỗi con LỚN DẦN RÕ
    RỆT theo growth (0..1), qua 3 "tuổi lột xác" (instar) hình dáng khác
    hẳn nhau, đúng thực tế ấu trùng kiến là 1 con sâu nhỏ cong hình chữ C,
    càng lớn càng CONG NHIỀU HƠN và LỘ RÕ ĐỐT THÂN (segment) hơn - không
    chỉ đơn thuần phóng to 1 hình bầu dục như trước:
    - Tuổi 1 (growth thấp): bé tí, gần như thẳng, chỉ 2 đốt mờ - trông như
      1 hạt gạo nhỏ trắng nhợt.
    - Tuổi 2 (growth giữa): to hơn rõ, cong nhẹ, 3-4 đốt thấy được.
    - Tuổi 3 (growth cao, sắp hóa nhộng): to nhất, cong hẳn thành hình chữ
      C rõ nét với 5 đốt, ngả vàng đậm - đúng ấu trùng SẮP KÉN.
    Dùng sprite larva.png tùy chỉnh nếu có (chỉ scale kích thước theo
    growth, không vẽ đốt/độ cong - vì đó là ảnh tĩnh do người chơi cung
    cấp)."""
    active_idx = np.where(colony_obj.larva_active)[0]
    if len(active_idx) == 0:
        return
    rng_local = np.random.RandomState(seed_key * 331 + 7)
    ang = rng_local.uniform(0, 2 * np.pi, cfg.LARVA_MAX_COUNT)
    rad = np.sqrt(rng_local.uniform(0, 1, cfg.LARVA_MAX_COUNT)) * r_px * 0.68
    body_ang = rng_local.uniform(0, 2 * np.pi, cfg.LARVA_MAX_COUNT)  # hướng "nằm" của từng con - cố định, không đổi mỗi khung hình
    has_sprite = state.sprites.has("larva.png")
    for i in active_idx:
        growth = float(colony_obj.larva_growth[i])
        dx = int(math.cos(ang[i]) * rad[i])
        dy = int(math.sin(ang[i]) * rad[i])
        px, py = cx + dx, cy + dy
        size = max(3, int(r_px * (0.055 + 0.15 * growth) * cfg.ENTITY_SPRITE_SCALE))
        if has_sprite:
            sprite = state.sprites.get_static("larva.png", size * 2)
            surf.blit(sprite, sprite.get_rect(center=(px, py)))
            continue
        shade = int(250 - growth * 75)
        color = (shade, shade, max(120, shade - 70))
        outline = (60, 55, 25)
        n_segments = 2 + round(growth * 3)  # 2 đốt (mới nở) -> 5 đốt (sắp hóa nhộng)
        curl = growth * 1.7  # radian - gần như thẳng lúc bé, cong hẳn chữ C lúc lớn
        seg_r0 = max(1.5, size * 0.32)
        for s in range(n_segments):
            t = s / max(1, n_segments - 1)  # 0 (đầu) -> 1 (đuôi)
            a = body_ang[i] + curl * t
            dist = size * 0.9 * t
            sx = px + math.cos(a) * dist
            sy = py + math.sin(a) * dist
            seg_r = max(1.5, seg_r0 * (1.0 - 0.28 * t))  # đốt đuôi nhỏ hơn đốt đầu
            pygame.draw.circle(surf, outline, (int(sx), int(sy)), int(seg_r) + 1)
            pygame.draw.circle(surf, color, (int(sx), int(sy)), int(seg_r))


def draw_queen(state, surf, cx, cy, r_px, room_rgb, frame_counter):
    """Phòng chúa THẬT SỰ có 1 con kiến chúa - to hẳn so với thợ
    thường, đứng yên giữa phòng (chỉ hơi bồng bềnh nhẹ cho có sức
    sống), với bụng (gaster) to đặc trưng để đẻ trứng. Dùng sprite
    queen.png tùy chỉnh nếu người chơi đã cung cấp."""
    bob = math.sin(frame_counter * 0.03) * r_px * 0.03
    qy = cy + bob
    if state.sprites.has("queen.png"):
        # Trần 1.6*r_px (= 80% đường kính phòng) dù ENTITY_SPRITE_SCALE lớn
        # cỡ nào - PHẢI luôn chừa biên quanh chúa cho lính hộ vệ đứng cạnh,
        # không được to gần bằng/hơn cả đường kính phòng (từng xảy ra ở
        # ENTITY_SPRITE_SCALE cao: 1.3*r_px*1.6 = 2.08*r_px, VƯỢT cả đường
        # kính 2*r_px, khiến chúa tràn hẳn ra ngoài viền phòng).
        size = min(int(r_px * 1.3 * cfg.ENTITY_SPRITE_SCALE), int(r_px * 1.6))
        size = max(6, size)
        sprite = state.sprites.get_static("queen.png", size)
        surf.blit(sprite, sprite.get_rect(center=(int(cx), int(qy))))
        return
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


def draw_water_drops(state, surf, cx, cy, r_px, amount, seed_key):
    """Bể trữ nước KHÔNG chỉ là 1 con số - vẽ luôn lượng nước ĐANG TRỮ
    THẬT SỰ dưới dạng các giọt nước xanh lấp lánh xếp THÀNH LƯỚI GỌN GÀNG
    (không rải ngẫu nhiên - xem _grid_positions) để đếm bằng mắt thường dễ
    dàng, to/nhỏ theo lượng nước tồn hiện tại. TÁI DÙNG sprite water.png
    tùy chỉnh nếu có, không thì vẽ giọt nước tròn màu như trước."""
    n_icons = int(np.clip(amount / cfg.WATER_PER_ICON, 0, cfg.WATER_MAX_ICONS))
    if n_icons <= 0:
        return
    r = max(3, int(r_px * 0.09 * cfg.ENTITY_SPRITE_SCALE))
    positions, r = _grid_positions(n_icons, cx, cy, r_px, r)
    r = max(3, int(r))
    sprite = state.sprites.get_static("water.png", r * 2) if state.sprites.has("water.png") else None
    for px, py in positions:
        px, py = int(px), int(py)
        if sprite is not None:
            surf.blit(sprite, sprite.get_rect(center=(px, py)))
            continue
        pygame.draw.circle(surf, (20, 60, 100), (px, py), r + 1)
        pygame.draw.circle(surf, (60, 150, 230), (px, py), r)
        hi = max(1, int(r * 0.45))
        pygame.draw.circle(surf, (220, 240, 255), (px - r // 3, py - r // 3), hi)


def draw_eggs(state, surf, cx, cy, r_px, colony_obj, seed_key):
    """Phòng trứng THẬT SỰ có trứng bên trong - trứng LỚN DẦN RÕ RỆT và
    ĐỔI DÁNG theo growth (0..1), đúng thực tế: trứng vừa đẻ gần như tròn
    tăm tăm trắng đục, càng gần nở càng NẢY DÀI RA thành hình bầu dục thon
    (thay vì chỉ phóng to đều 1 tỉ lệ cố định như trước) và ngả trong hơn/
    sáng hơn 1 chút (sắp nở). Dùng sprite egg.png tùy chỉnh nếu người chơi
    đã cung cấp (chỉ scale kích thước theo growth, không đổi tỉ lệ dáng -
    vì đó là ảnh tĩnh do người chơi cung cấp)."""
    active_idx = np.where(colony_obj.egg_active)[0]
    if len(active_idx) == 0:
        return
    rng_local = np.random.RandomState(seed_key * 421 + 3)
    ang = rng_local.uniform(0, 2 * np.pi, cfg.EGG_MAX_COUNT)
    rad = np.sqrt(rng_local.uniform(0, 1, cfg.EGG_MAX_COUNT)) * r_px * 0.65
    has_sprite = state.sprites.has("egg.png")
    for i in active_idx:
        growth = float(colony_obj.egg_growth[i])
        dx = int(math.cos(ang[i]) * rad[i])
        dy = int(math.sin(ang[i]) * rad[i])
        size = max(2, int(r_px * (0.032 + 0.06 * growth) * cfg.ENTITY_SPRITE_SCALE))
        if has_sprite:
            sprite = state.sprites.get_static("egg.png", size * 2)
            surf.blit(sprite, sprite.get_rect(center=(cx + dx, cy + dy)))
            continue
        # aspect: gần tròn (1.0) lúc mới đẻ -> bầu dục thon (1.7) lúc sắp nở
        aspect = 1.0 + 0.7 * growth
        w = size
        h = size * aspect
        shade = int(232 + 20 * growth)  # sáng dần lên 1 chút khi sắp nở
        color = (shade, shade, min(250, shade + 8))
        pygame.draw.ellipse(surf, (150, 145, 120), (cx + dx - w - 1, cy + dy - h - 1, w * 2 + 2, h * 2 + 2))
        pygame.draw.ellipse(surf, color, (cx + dx - w, cy + dy - h, w * 2, h * 2))


def draw_graveyard(state, surf, cx, cy, r_px, corpse_count, seed_key):
    """Nghĩa địa - mỗi kiến chết để lại 1 'nắm xác' nhỏ ở đây, mờ dần
    theo thời gian (phân hủy) thay vì kiến biến mất vô hình. Dùng sprite
    corpse.png tùy chỉnh nếu người chơi đã cung cấp."""
    n_icons = int(np.clip(corpse_count, 0, cfg.GRAVEYARD_MAX_CORPSES))
    if n_icons <= 0:
        return
    rng_local = np.random.RandomState(seed_key * 857 + 29)
    ang = rng_local.uniform(0, 2 * np.pi, n_icons)
    rad = np.sqrt(rng_local.uniform(0, 1, n_icons)) * r_px * 0.7
    tilt = rng_local.uniform(0, 360, n_icons)
    size = max(2, int(r_px * 0.09 * cfg.ENTITY_SPRITE_SCALE))
    sprite = state.sprites.get_static("corpse.png", size * 2) if state.sprites.has("corpse.png") else None
    for i in range(n_icons):
        dx = int(math.cos(ang[i]) * rad[i])
        dy = int(math.sin(ang[i]) * rad[i])
        px, py = cx + dx, cy + dy
        if sprite is not None:
            rotated = pygame.transform.rotate(sprite, float(tilt[i]))
            surf.blit(rotated, rotated.get_rect(center=(px, py)))
            continue
        pygame.draw.line(surf, (60, 50, 45), (px - size, py - size), (px + size, py + size), 2)
        pygame.draw.line(surf, (60, 50, 45), (px - size, py + size), (px + size, py - size), 2)
        pygame.draw.circle(surf, (45, 38, 34), (px, py), size)


def draw_trophallaxis(state, surf, colony_obj, depth):
    """Vẽ các khoảnh khắc MỚM MỒI (trophallaxis) GẦN ĐÂY: 1 dây nối ngắn
    sáng màu + 2 chấm nhỏ ở 2 đầu, NHÒE DẦN (tối màu dần) rồi tự biến mất
    - mô phỏng khoảnh khắc 2 cá thể (thợ-nurse, nurse-ấu trùng, attendant-
    chúa) trao đổi thức ăn miệng-miệng, đúng hành vi xã hội ĐẶC TRƯNG NHẤT
    của loài kiến thật - không chỉ đơn thuần "vác cục mồi bỏ vào kho"."""
    if not colony_obj.trophallaxis_events:
        return
    camera = state.camera
    tick_now = colony_obj.tick_count
    ttl = cfg.TROPHALLAXIS_TTL_TICKS
    for x1, y1, x2, y2, tick_created, ev_depth in colony_obj.trophallaxis_events:
        if ev_depth != depth:
            continue
        age = tick_now - tick_created
        if age < 0 or age > ttl:
            continue
        t = 1.0 - age / ttl  # 1.0 = vừa xảy ra, 0.0 = sắp biến mất
        brightness = 0.3 + 0.7 * t
        col = tuple(int(c * brightness) for c in (255, 235, 180))
        sx1, sy1 = camera.world_to_screen(x1, y1, state.CENTER_X, state.CENTER_Y)
        sx2, sy2 = camera.world_to_screen(x2, y2, state.CENTER_X, state.CENTER_Y)
        pygame.draw.line(surf, col, (int(sx1), int(sy1)), (int(sx2), int(sy2)), 2)
        dot_r = max(2, int(2 + 2 * t))
        pygame.draw.circle(surf, col, (int(sx1), int(sy1)), dot_r)
        pygame.draw.circle(surf, col, (int(sx2), int(sy2)), dot_r)


def draw_underground_grid_lines(state, surf):
    """Lưới ô vuông NỀN cho tầng ngầm - KHÔNG dùng chung với lưới mặt đất
    (mặt đất cố định theo đúng kích thước bản đồ cfg.GRID_SIZE, vốn không
    liên quan gì tới vị trí/kích thước các phòng dưới hầm). Hầm không phải
    lưới ô vuông thật (phòng là các "khối u" tự do, không neo theo ô lưới
    rời rạc như mặt đất) - lưới này CHỈ mang tính tham chiếu thị giác (cảm
    nhận khoảng cách/tỉ lệ), nên phải tự tính
    vùng bao BAO TRỌN mọi phòng (kể cả bán kính phòng, không chỉ tâm) rồi
    mới vẽ - nếu không, khi ROOM_LAYOUT_SCALE lớn, phòng sẽ tràn ra ngoài
    hẳn vùng lưới (đã từng xảy ra khi lưới bị "đóng cứng" theo kích thước
    bản đồ mặt đất)."""
    camera = state.camera
    cell = camera.cell_px()

    xs, ys = [], []
    uworld = state.underground_world
    for (_id, _name, center, radius, _color, _depth) in uworld.rooms:
        xs.append(float(center[0]) - float(radius))
        xs.append(float(center[0]) + float(radius))
        ys.append(float(center[1]) - float(radius))
        ys.append(float(center[1]) + float(radius))
    xs.append(float(uworld.shaft_xy[0]))
    ys.append(float(uworld.shaft_xy[1]))
    if not xs:
        return
    pad = 2.0  # đơn vị lưới - chừa biên ngoài phòng ngoài cùng
    min_x, max_x = min(xs) - pad, max(xs) + pad
    min_y, max_y = min(ys) - pad, max(ys) + pad

    x0, y0 = camera.world_to_screen(min_x, min_y, state.CENTER_X, state.CENTER_Y)
    x1, y1 = camera.world_to_screen(max_x, max_y, state.CENTER_X, state.CENTER_Y)
    step = cell
    gx = x0
    while gx <= x1 + 0.5:
        if gx >= -step:
            pygame.draw.line(surf, (0, 0, 0, 40), (gx, max(0, y0)), (gx, min(state.CANVAS_H, y1)), 1)
        gx += step
    gy = y0
    while gy <= y1 + 0.5:
        if gy >= -step:
            pygame.draw.line(surf, (0, 0, 0, 40), (max(0, x0), gy), (min(state.SCREEN_W, x1), gy), 1)
        gy += step


def draw_ant_social_fx(state, surf, colony_obj, depth_filter):
    """Hiệu ứng THUẦN HIỂN THỊ (không đụng gì tới mô phỏng, không thêm
    state mới vào AntColony - tính lại HOÀN TOÀN mỗi khung hình từ vị
    trí/trạng thái hiện tại):
    1) Dấu NGHỈ NGƠI - chấm tròn mờ nhấp nháy phía trên các con đang
       STATE_DWELL (rảnh rỗi, lượn quanh phòng) - đúng thực tế đàn kiến
       không phải lúc nào cũng hoạt động hết công suất. Chỉ khoảng 1/3 số
       con rảnh được đánh dấu mỗi lúc (thay phiên theo frame_counter),
       tạo cảm giác "thay nhau nghỉ" thay vì đứng y hệt nhau.
    2) Lấp lánh CHẢI CHUỐT (grooming) - 2 con RẢNH RỖI đứng rất gần nhau
       (cfg.GROOMING_DISTANCE) thỉnh thoảng có 1 tia sáng nhỏ giữa 2 con -
       hành vi xã hội phổ biến ở loài kiến thật, khác với mớm mồi
       (xem draw_trophallaxis - đó là TRAO ĐỔI THỨC ĂN, còn đây là LÀM
       SẠCH lẫn nhau, không liên quan thức ăn)."""
    mask = colony_obj.alive & (colony_obj.depth == depth_filter) & (colony_obj.state == cfg.STATE_DWELL)
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return
    camera = state.camera
    cell = camera.cell_px()
    xs, ys = colony_obj.x[idx], colony_obj.y[idx]
    phase = state.frame_counter // 20

    for i, real_i in enumerate(idx):
        if (int(real_i) + phase) % 3 != 0:
            continue
        sx = state.CENTER_X + (xs[i] - camera.cx) * cell
        sy = state.CENTER_Y + (ys[i] - camera.cy) * cell
        if sx < -10 or sx > state.SCREEN_W + 10 or sy < -10 or sy > state.CANVAS_H + 10:
            continue
        r = max(2, int(cell * 0.09))
        pulse = 0.5 + 0.5 * math.sin((state.frame_counter + int(real_i) * 7) * 0.05)
        shade = int(120 + 70 * pulse)
        pygame.draw.circle(surf, (shade, shade, shade), (int(sx), int(sy - cell * 0.32)), r, 1)

    if len(idx) >= 2:
        pts = np.stack([xs, ys], axis=1)
        diff = pts[:, None, :] - pts[None, :, :]
        dist2 = np.sum(diff * diff, axis=2)
        thresh2 = cfg.GROOMING_DISTANCE ** 2
        n = len(idx)
        for a in range(n):
            for b in range(a + 1, n):
                if dist2[a, b] > thresh2:
                    continue
                pair_key = int(idx[a]) * 7919 + int(idx[b])
                if (pair_key + phase) % 5 != 0:
                    continue
                sx1 = state.CENTER_X + (xs[a] - camera.cx) * cell
                sy1 = state.CENTER_Y + (ys[a] - camera.cy) * cell
                sx2 = state.CENTER_X + (xs[b] - camera.cx) * cell
                sy2 = state.CENTER_Y + (ys[b] - camera.cy) * cell
                mx, my = (sx1 + sx2) / 2, (sy1 + sy2) / 2
                if mx < -10 or mx > state.SCREEN_W + 10 or my < -10 or my > state.CANVAS_H + 10:
                    continue
                spark_r = max(2, int(cell * 0.07))
                pygame.draw.circle(surf, (255, 245, 200), (int(mx), int(my)), spark_r)

    # --- Chăm sóc lẫn nhau THẬT SỰ (allogrooming có trạng thái/thời
    # lượng hẳn hoi - xem cfg.GROOM_*/AntColony._update_grooming()), KHÁC
    # với tia lấp lánh "gần nhau ngẫu nhiên" ở trên (vốn chỉ là hiệu ứng
    # trang trí không trạng thái) - đây là 1 CẶP CỤ THỂ đang thực sự chăm
    # sóc nhau trong 1 khoảng thời gian, vẽ đậm/rõ hơn hẳn để phân biệt. ---
    groom_ticks_arr = getattr(colony_obj, "groom_ticks", None)
    groom_partner_arr = getattr(colony_obj, "groom_partner", None)
    if groom_ticks_arr is not None and groom_partner_arr is not None:
        active = np.where(mask & (groom_ticks_arr > 0))[0]
        for a in active.tolist():
            b = int(groom_partner_arr[a])
            if b < 0 or b < a:
                continue  # vẽ 1 lần/cặp (bỏ qua chiều ngược lại)
            if not (colony_obj.alive[b] and colony_obj.depth[b] == depth_filter):
                continue
            sx1, sy1 = camera.world_to_screen(float(colony_obj.x[a]), float(colony_obj.y[a]), state.CENTER_X, state.CENTER_Y)
            sx2, sy2 = camera.world_to_screen(float(colony_obj.x[b]), float(colony_obj.y[b]), state.CENTER_X, state.CENTER_Y)
            pulse = 0.5 + 0.5 * math.sin(state.frame_counter * 0.3 + a)
            col = (int(150 + 60 * pulse), int(220 + 30 * pulse), int(140 + 60 * pulse))
            pygame.draw.line(surf, col, (int(sx1), int(sy1)), (int(sx2), int(sy2)), 1)
            mx, my = (sx1 + sx2) / 2, (sy1 + sy2) / 2
            pygame.draw.circle(surf, col, (int(mx), int(my)), max(2, int(cell * 0.08)))


def draw_guard_inspections(state, surf, colony_obj, depth):
    """Vẽ các khoảnh khắc lính gác CHẠM RÂU kiểm tra đồng đội ra vào cửa tổ
    GẦN ĐÂY (xem cfg.GUARD_INSPECT_*/AntColony._update_guard_inspections())
    - cùng cơ chế nhòe dần như draw_trophallaxis nhưng màu XANH NHẠT để
    phân biệt rõ đây là NHẬN DIỆN (nestmate recognition), không phải trao
    đổi thức ăn."""
    events = getattr(colony_obj, "inspection_events", None)
    if not events:
        return
    camera = state.camera
    tick_now = colony_obj.tick_count
    ttl = cfg.GUARD_INSPECT_TTL_TICKS
    for x1, y1, x2, y2, tick_created, ev_depth in events:
        if ev_depth != depth:
            continue
        age = tick_now - tick_created
        if age < 0 or age > ttl:
            continue
        t = 1.0 - age / ttl
        brightness = 0.3 + 0.7 * t
        col = tuple(int(c * brightness) for c in (150, 200, 255))
        sx1, sy1 = camera.world_to_screen(x1, y1, state.CENTER_X, state.CENTER_Y)
        sx2, sy2 = camera.world_to_screen(x2, y2, state.CENTER_X, state.CENTER_Y)
        pygame.draw.line(surf, col, (int(sx1), int(sy1)), (int(sx2), int(sy2)), 1)
        dot_r = max(2, int(2 + 2 * t))
        pygame.draw.circle(surf, col, (int(sx1), int(sy1)), dot_r)
        pygame.draw.circle(surf, col, (int(sx2), int(sy2)), dot_r)


def _draw_merged_room_contents(state, surf, uworld, colony_obj, cx, cy, r_px, depth):
    """Các phòng CHƯA được đào thành phòng riêng (room_id không nằm trong
    uworld.unlocked_rooms - xem UndergroundWorld.unlock_room()) vẫn cần
    HIỂN THỊ đúng nội dung thực tế của chúng (thức ăn/trứng/ấu trùng/nước/
    xác/nhộng - dữ liệu vẫn tồn tại và tăng giảm bình thường, chỉ là CHƯA
    CÓ PHÒNG RIÊNG để chứa) - vẽ GỘP hết vào bên trong vòng tròn Phòng
    chúa đang mở (cx, cy, r_px), mỗi loại dùng 1 seed_key riêng để vị trí
    rải rác không trùng hệt nhau."""
    for room in uworld.rooms:
        room_id, _name, _center, _radius, _color, room_depth = room
        if room_id == 2 or room_id in uworld.unlocked_rooms or room_depth != depth:
            continue
        seed_key = room_id * 10 + 3  # lệch seed so với lúc phòng đó tự vẽ riêng (room_id*10)
        if room_id == 0:
            draw_storage_pile(state, surf, cx, cy, r_px, uworld.food_in_storage, seed_key)
        elif room_id == 1:
            draw_larvae(state, surf, cx, cy, r_px, colony_obj, seed_key)
        elif room_id == 3:
            draw_water_drops(state, surf, cx, cy, r_px, uworld.water_in_storage, seed_key)
        elif room_id == 4:
            draw_eggs(state, surf, cx, cy, r_px, colony_obj, seed_key)
        elif room_id == 6:
            draw_graveyard(state, surf, cx, cy, r_px, uworld.corpse_count, seed_key)
        elif room_id == 7:
            draw_pupae(state, surf, cx, cy, r_px, colony_obj, seed_key)


def draw_underground_layer(state, surf, depth):
    camera = state.camera
    pygame.draw.rect(surf, cfg.COLOR_BG_UNDERGROUND, (0, 0, state.SCREEN_W, state.CANVAS_H))
    cell = camera.cell_px()
    if state.grid_visible and cell >= 3:
        draw_underground_grid_lines(state, surf)

    uworld, colony_obj = state.underground_world, state.colony
    # giếng (thang máy) - chỉ hiện nếu có phòng ĐÃ MỞ (unlocked_rooms) ở
    # tầng này - phòng còn "gộp chung" vào Phòng chúa (chưa unlock) không
    # tính, kẻo hiện giếng dẫn xuống 1 tầng trống trơn chưa hề tồn tại.
    has_room_here = any(r[5] == depth for r in uworld.rooms if r[0] in uworld.unlocked_rooms)
    if has_room_here:
        sx, sy = camera.world_to_screen(float(uworld.shaft_xy[0]), float(uworld.shaft_xy[1]), state.CENTER_X, state.CENTER_Y)
        r = max(3, int(cell * 0.8))
        pygame.draw.circle(surf, cfg.COLOR_SHAFT, (int(sx), int(sy)), r)
        pygame.draw.circle(surf, (90, 90, 90), (int(sx), int(sy)), r, 1)

    for room in uworld.rooms:
        room_id, name, center, radius, room_rgb, room_depth = room
        if room_id not in uworld.unlocked_rooms:
            # CHƯA được đào thành phòng RIÊNG - "gộp chung" tạm vào Phòng
            # chúa (xem UndergroundWorld.unlock_room()) - KHÔNG vẽ như 1
            # phòng độc lập ở đây (sẽ chồng lấn lên đúng vị trí Phòng
            # chúa) - nội dung của nó (đồ ăn/trứng/ấu trùng...) được vẽ
            # GỘP vào bên trong vòng tròn Phòng chúa, xem
            # _draw_merged_room_contents() gọi bên dưới, ngay sau khi vẽ
            # xong Phòng chúa.
            continue
        if room_depth != depth:
            continue
        if room_id == 2 and colony_obj.founding_phase:
            # Đang lập tổ: vẽ HỐC LẬP TỔ nhỏ (chưa phải "Phòng chúa"
            # đầy đủ) - xem giải thích chi tiết ở ROOM_RADIUS_FOUNDING_
            # CHAMBER trong config.py. Bán kính "chuẩn" (radius, biến
            # cục bộ ở trên) chỉ dùng lại NGAY SAU khi lập tổ xong -
            # không cần code chuyển đổi gì thêm, tick sau founding_phase
            # tắt là round-trip qua đây tự động dùng radius gốc.
            radius = cfg.ROOM_RADIUS_FOUNDING_CHAMBER
        cx, cy = camera.world_to_screen(float(center[0]), float(center[1]), state.CENTER_X, state.CENTER_Y)
        # hành lang nối giếng <-> phòng (cùng tầng) - vẽ TRƯỚC, mảnh
        # và mờ hơn, để rõ ràng đây chỉ là đường DI CHUYỂN, không
        # phải nơi kiến "ở lại hoạt động"
        sx, sy = camera.world_to_screen(float(uworld.shaft_xy[0]), float(uworld.shaft_xy[1]), state.CENTER_X, state.CENTER_Y)
        pygame.draw.line(surf, (95, 85, 78), (int(sx), int(sy)), (int(cx), int(cy)), max(1, int(cell * 0.09)))

        r_px = max(10, int(radius * cell))
        seed_key = room_id * 10
        draw_room_floor(surf, int(cx), int(cy), r_px, room_rgb, seed_key)

        # --- mỗi phòng THỰC SỰ làm đúng chức năng của nó ---
        if room_id == 0:  # Kho thức ăn: vẽ đống thức ăn tồn kho thật
            draw_storage_pile(state, surf, int(cx), int(cy), r_px, uworld.food_in_storage, seed_key)
        elif room_id == 1:  # Phòng ấu trùng: vẽ các ấu trùng đang lớn thật
            draw_larvae(state, surf, int(cx), int(cy), r_px, colony_obj, seed_key)
        elif room_id == 2:  # Phòng chúa: vẽ 1 con kiến chúa thật
            draw_queen(state, surf, int(cx), int(cy), r_px, room_rgb, state.frame_counter)
            _draw_merged_room_contents(state, surf, uworld, colony_obj, int(cx), int(cy), r_px, depth)
        elif room_id == 3:  # Bể trữ nước: vẽ các giọt nước tồn trữ thật
            draw_water_drops(state, surf, int(cx), int(cy), r_px, uworld.water_in_storage, seed_key)
        elif room_id == 4:  # Phòng trứng: vẽ các trứng đang ủ thật
            draw_eggs(state, surf, int(cx), int(cy), r_px, colony_obj, seed_key)
        elif room_id == 6:  # Nghĩa địa: vẽ các nắm xác thật
            draw_graveyard(state, surf, int(cx), int(cy), r_px, uworld.corpse_count, seed_key)
        elif room_id == 7:  # Phòng nhộng: vẽ các kén nhộng đang biến thái thật
            draw_pupae(state, surf, int(cx), int(cy), r_px, colony_obj, seed_key)
        # room_id == 5 (Phòng gác cửa): không cần vẽ thêm gì đặc biệt
        # - lính gác đóng quân ở đây đã tự hiện ra qua draw_ants() bên
        # dưới (vì depth của họ = DEPTH_GUARD), giống như trong bất kỳ
        # phòng nào khác.

        label = render_cached(state.font_small, name, (235, 235, 235))
        surf.blit(label, label.get_rect(center=(cx, cy - r_px - 12)))

    # Màu kiến dưới hầm GẦN GIỐNG HỆT màu thật trên mặt đất (chỉ nhỉnh sáng
    # hơn 1 chút để vẫn có hình khối trên nền hành lang rất tối) - trước
    # đây dùng hẳn 1 bộ màu khác (xám trắng) khiến cùng 1 con kiến trông
    # như đổi loài giữa 2 khu vực. Viền sáng (underground=True) đã đủ để
    # nổi trên nền tối, không cần đổi màu thân nữa.
    draw_ants(state, surf, state.colony, (45, 40, 36), (215, 120, 30), depth_filter=depth, underground=True)
    draw_ants(state, surf, state.invasion, (80, 15, 15), (150, 40, 20), depth_filter=depth, underground=True)
    draw_ant_social_fx(state, surf, state.colony, depth)
    draw_trophallaxis(state, surf, state.colony, depth)
    draw_guard_inspections(state, surf, state.colony, depth)
