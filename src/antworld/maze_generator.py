# -*- coding: utf-8 -*-
"""Sinh 1 MÊ CUNG CHUẨN ("perfect maze" - mọi ô đều liên thông, đúng 1
đường duy nhất giữa 2 ô bất kỳ, không có phòng mở/vòng lặp) TRỰC TIẾP vào
bản đồ THẬT (state.surface_world) đang được đàn kiến thật chơi, thay vì
dựng 1 world minh họa tách biệt. Nhờ đó có thể xem đàn kiến thật tự tìm
đường xuyên mê cung bằng ĐÚNG thuật toán any-angle A* trên visibility
graph (pathfinding.py) mà cả game đang dùng - không phải 1 bản sao/mô
phỏng lại.

Kích hoạt qua nút "Sinh me cung" trong toolbar (xem hud.py) hoặc gọi trực
tiếp GameState.generate_maze().
"""
from collections import deque

import numpy as np

from . import config as cfg


# ============================================================
# 1. Sinh mê cung chuẩn (recursive backtracker), NEO theo vị trí tổ
# ============================================================
def _valid_cell_offsets(nest_c, n, passage, wall, pitch, margin):
    """Danh sách số nguyên c sao cho 1 ô mê cung (rộng `passage`, tâm lệch
    c*pitch so với tổ theo 1 trục) vẫn nằm gọn trong bản đồ (chừa `margin`
    ô làm viền). c=0 LUÔN hợp lệ và chính là ô CHỨA vị trí tổ - đảm bảo tổ
    không bao giờ rơi vào giữa 1 bức tường."""
    half = passage // 2

    def origin(c):
        return nest_c - half + c * pitch

    offsets = []
    c = 0
    while origin(c) + passage <= n - margin:
        offsets.append(c)
        c += 1
    c = -1
    while origin(c) >= margin:
        offsets.append(c)
        c -= 1
    return sorted(offsets), origin


def generate_perfect_maze(n, nest_x, nest_y, rng,
                           passage=None, wall=None, margin=1):
    """Trả về (blocked, num_cells): mảng bool (n,n) và số ô mê cung.

    Vài lựa chọn THIẾT KẾ đáng chú ý:

    - "Perfect maze" đúng nghĩa (recursive backtracker - cây khung phủ
      kín/spanning tree trên lưới ô logic) tạo ra RẤT NHIỀU góc rẽ - ban
      đầu điều này khiến chi phí dựng visibility graph tĩnh (O(V^2) kiểm
      tra tầm nhìn) tăng vọt VÀ mỗi lần tìm đường sau đó cũng chậm hẳn (đo
      thực tế ban đầu: ~50-80ms/truy vấn trong mê cung ~650 đỉnh, đủ để
      cả tick giật hình nếu nhiều kiến cùng cần đường mới). Đã khắc phục
      bằng 2 tối ưu ở pathfinding.py (không đổi kết quả hình học, chỉ đổi
      tốc độ):
        1. Gộp các ô vật cản liền kề thành hình chữ nhật lớn trước khi
           kiểm tra tầm nhìn (VisibilityPathfinder._merge_blocked_
           rectangles) - giảm thẳng số "vật cản" cần quét mỗi lần kiểm
           tra, vì tường 1 ô dày tạo ra RẤT NHIỀU ô rời rạc.
        2. Heuristic ALT (Landmarks - VisibilityPathfinder._build_
           landmarks) thay cho đường chim bay thuần túy - đường chim bay
           là heuristic quá YẾU trong mê cung (2 điểm gần theo đường
           thẳng có thể phải đi vòng rất xa), khiến A* phải mở rộng gần
           hết đồ thị mỗi lần tìm đường.
      Nhờ 2 tối ưu trên, mê cung có thể dùng hành lang hẹp (2 ô) và tường
      mỏng (1 ô) - đúng "mê cung" hơn hẳn - mà build vẫn dưới ~2.5 giây và
      mỗi truy vấn sau đó chỉ còn vài ms. Xem MAZE_PASSAGE_WIDTH/
      MAZE_WALL_WIDTH trong config.py nếu muốn tinh chỉnh lại đánh đổi
      này (hẹp hơn nữa = nhiều khúc quanh hơn nhưng build chậm hơn NHIỀU
      vì chi phí vẫn là O(V^2), không tuyến tính - vd hành lang 1 ô mất
      trên 15 giây để build).
    - Lưới ô mê cung được NEO theo đúng vị trí tổ (ô logic đầu tiên luôn
      là ô CHỨA tổ, xem _valid_cell_offsets) thay vì neo theo góc bản đồ -
      nếu không, tổ có thể vô tình rơi đúng vào 1 dải tường và bị "nhốt"
      ngay từ đầu tùy theo GRID_SIZE/passage/wall cụ thể.
    """
    passage = passage or cfg.MAZE_PASSAGE_WIDTH
    wall = wall or cfg.MAZE_WALL_WIDTH
    pitch = passage + wall

    xs, origin_x = _valid_cell_offsets(nest_x, n, passage, wall, pitch, margin)
    ys, origin_y = _valid_cell_offsets(nest_y, n, passage, wall, pitch, margin)
    ix0, iy0 = xs.index(0), ys.index(0)
    cols_x, cols_y = len(xs), len(ys)

    blocked = np.ones((n, n), dtype=bool)
    visited = np.zeros((cols_x, cols_y), dtype=bool)

    def cell_rect(ix, iy):
        return origin_x(xs[ix]), origin_y(ys[iy])

    def carve_cell(ix, iy):
        ox, oy = cell_rect(ix, iy)
        blocked[ox:ox + passage, oy:oy + passage] = False

    def carve_passage(ix, iy, nix, niy):
        ox, oy = cell_rect(ix, iy)
        nox, noy = cell_rect(nix, niy)
        if ox == nox:  # 2 ô liền kề theo trục Y
            y0, y1 = (oy, noy) if oy < noy else (noy, oy)
            blocked[ox:ox + passage, y0 + passage:y1] = False
        else:  # liền kề theo trục X
            x0, x1 = (ox, nox) if ox < nox else (nox, ox)
            blocked[x0 + passage:x1, oy:oy + passage] = False

    stack = [(ix0, iy0)]
    visited[ix0, iy0] = True
    carve_cell(ix0, iy0)
    while stack:
        ix, iy = stack[-1]
        options = [
            (ix + dx, iy + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= ix + dx < cols_x and 0 <= iy + dy < cols_y and not visited[ix + dx, iy + dy]
        ]
        if not options:
            stack.pop()
            continue
        nix, niy = options[rng.integers(0, len(options))]
        visited[nix, niy] = True
        carve_cell(nix, niy)
        carve_passage(ix, iy, nix, niy)
        stack.append((nix, niy))

    return blocked, cols_x * cols_y


# ============================================================
# 2. Rải nhiều cụm thức ăn NHỎ, trải khắp mê cung (thay vì 1 cụm to)
# ============================================================
def _bfs_distances(blocked, start):
    """BFS 4 hướng từ `start` - trả về dict {(x,y): số bước} cho MỌI ô
    liên thông tới được (không có trong dict nghĩa là không tới được)."""
    n = blocked.shape[0]
    dist = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        d = dist[(x, y)]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and not blocked[nx, ny] and (nx, ny) not in dist:
                dist[(nx, ny)] = d + 1
                q.append((nx, ny))
    return dist


def _scatter_points(dist, count, rng):
    """Chọn `count` ô CÀNG TRẢI ĐỀU khắp mê cung càng tốt (farthest-point
    sampling): điểm đầu tiên là ô xa tổ nhất; mỗi điểm tiếp theo là ô có
    khoảng cách TỐI THIỂU tới các điểm đã chọn LỚN NHẤT - đảm bảo các cụm
    thức ăn nằm rải rác khắp các ngóc ngách mê cung, không dồn cụm 1 chỗ."""
    candidates = [c for c, d in dist.items() if d > 0]
    if not candidates:
        return []
    rng.shuffle(candidates)
    picked = [max(candidates, key=lambda c: dist[c])]
    for _ in range(min(count, len(candidates)) - 1):
        best_cell, best_score = None, -1.0
        for c in candidates:
            if c in picked:
                continue
            score = min((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 for p in picked)
            if score > best_score:
                best_score, best_cell = score, c
        if best_cell is None:
            break
        picked.append(best_cell)
    return picked


# ============================================================
# 3. Lắp ráp: rải vào bản đồ thật + reset đường đi đàn kiến
# ============================================================
def generate_maze_in_world(state):
    """Xóa sạch đá/nước hiện có trên bản đồ thật, rải 1 perfect maze mới
    (neo theo vị trí tổ), rồi rải vài cụm thức ăn NHỎ ở các góc CÀNG TRẢI
    ĐỀU khắp mê cung càng tốt - để cả đàn phải tự tìm đường xuyên nhiều
    ngóc ngách khác nhau mới lấy được hết, đúng bằng bộ máy tìm đường
    THẬT của game (không phải bản minh họa riêng).

    Kiến đang có đường đi dở dang (tính trước khi có mê cung) bị hủy
    (path_len=0) - nếu không, kiến có thể tiếp tục đi nốt đoạn đường cũ
    xuyên thẳng qua tường mới đặt, tới khi nào đi hết đoạn đó mới tính lại
    - trông như "kiến đi xuyên tường" trong vài khung hình.
    """
    surface = state.surface_world
    n = cfg.GRID_SIZE
    nest_x, nest_y = int(cfg.NEST_POS[0]), int(cfg.NEST_POS[1])
    rng = np.random.default_rng()

    # --- Xóa sạch đá/nước hiện có (bán kính phủ cả bản đồ) VÀ thức ăn cũ
    # (các cụm thức ăn có sẵn từ lúc khởi tạo bản đồ) - nếu không, thức ăn
    # cũ còn sót lại sẽ trộn lẫn với các cụm nhỏ rải rác mới rải bên dưới,
    # không còn đúng ý "vài cụm nhỏ, rải khắp mê cung" nữa ---
    surface.remove_features_near(nest_x, nest_y, radius=n * 2)
    surface.food[:, :] = 0
    surface.food_type[:, :] = 0

    # --- Sinh perfect maze, neo theo đúng vị trí tổ ---
    blocked, _num_cells = generate_perfect_maze(n, nest_x, nest_y, rng)
    xs, ys = np.where(blocked)
    for x, y in zip(xs.tolist(), ys.tolist()):
        surface.add_rock_cell(x, y)

    # --- Rải vài cụm thức ăn nhỏ, trải đều khắp mê cung ---
    dist = _bfs_distances(blocked, (nest_x, nest_y))
    points = _scatter_points(dist, cfg.MAZE_FOOD_PILES, rng)
    for (fx, fy) in points:
        state.place_food_at(fx, fy, amount=cfg.MAZE_FOOD_AMOUNT_PER_PILE)

    # --- Kiến đang có đường đi dở dang phải bỏ, tick sau tự tính lại
    # đường MỚI xuyên đúng mê cung vừa rải ---
    for colony in state.ALL_COLONIES:
        if hasattr(colony, "path_len"):
            colony.path_len[:] = 0
            colony.path_idx[:] = 0

        # --- Kiến đang đứng ĐÚNG vào ô VỪA biến thành tường (đã tồn tại
        # từ trước khi sinh mê cung, vị trí không liên quan gì tới mê cung
        # mới) phải được đưa ra chỗ trống NGAY - nếu không, kiến đó bị
        # "nhốt" vĩnh viễn trong đá (hoàn toàn cô lập, không nhìn thấy đỉnh
        # visibility graph nào), và mỗi tick vẫn cứ THỬ tìm đường mới rồi
        # thất bại - chi phí tính toán đó vẫn mất dù không lộ ra ngoài
        # (kiến trông như chỉ đứng yên), gây giật hình kéo dài mà không rõ
        # nguyên nhân. Đưa thẳng về đúng vị trí tổ (luôn đảm bảo trống).
        on_surface = colony.alive & (colony.layer == cfg.LAYER_SURFACE)
        if np.any(on_surface):
            idx = np.where(on_surface)[0]
            xi = np.clip(colony.x[idx].astype(np.int64), 0, n - 1)
            yi = np.clip(colony.y[idx].astype(np.int64), 0, n - 1)
            trapped = blocked[xi, yi]
            if np.any(trapped):
                stuck_idx = idx[trapped]
                colony.x[stuck_idx] = nest_x + 0.5
                colony.y[stuck_idx] = nest_y + 0.5
