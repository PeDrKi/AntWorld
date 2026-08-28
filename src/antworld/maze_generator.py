# -*- coding: utf-8 -*-
"""Sinh 1 MÊ CUNG CHUẨN ("perfect maze" - mọi ô đều liên thông, đúng 1
đường duy nhất giữa 2 ô bất kỳ, không có phòng mở/vòng lặp).

Module này CHỈ chứa các hàm THUẦN TÚY (nhận mảng numpy, trả về mảng numpy)
- KHÔNG đụng tới state.surface_world/state.colony thật. Trước đây module
này từng có thêm hàm generate_maze_in_world() rải thẳng mê cung vào bản
đồ đang chơi (nút "Sinh me cung" trong toolbar chính) - đã bỏ vì đó là
thao tác PHÁ HỦY không thể hoàn tác (xóa sạch đá/nước/thức ăn đã đặt,
nước mất vĩnh viễn) và từng gây ra hàng loạt lỗi tinh vi khi va chạm với
trạng thái đàn kiến SỐNG (kiến bị nhốt trong tường mới đặt, đường đi cũ
bị cắt cụt...). Xem maze_demo.py (tab "Demo mê cung", world hoàn toàn
tách biệt, không rủi ro gì tới ván chơi thật) - dùng lại đúng các hàm ở
đây.
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
      phần lớn bằng 2 tối ưu ở pathfinding.py (không đổi kết quả hình học,
      chỉ đổi tốc độ):
        1. Gộp các ô vật cản liền kề thành hình chữ nhật lớn trước khi
           kiểm tra tầm nhìn (VisibilityPathfinder._merge_blocked_
           rectangles) - giảm thẳng số "vật cản" cần quét mỗi lần kiểm
           tra, vì tường 1 ô dày tạo ra RẤT NHIỀU ô rời rạc.
        2. Heuristic ALT (Landmarks - VisibilityPathfinder._build_
           landmarks) thay cho đường chim bay thuần túy - đường chim bay
           là heuristic quá YẾU trong mê cung (2 điểm gần theo đường
           thẳng có thể phải đi vòng rất xa), khiến A* phải mở rộng gần
           hết đồ thị mỗi lần tìm đường.
      Ở mật độ DÀY NHẤT (hành lang = tường = 1 ô, MAZE_PASSAGE_WIDTH=
      MAZE_WALL_WIDTH=1 - mê cung "chuẩn" nhất), số đỉnh visibility graph
      vẫn lên tới ~1400, khiến bước dựng đồ thị lần đầu (O(V^2), CHỈ 1 LẦN
      mỗi khi bấm "mê cung mới") mất khoảng 9-14 GIÂY ĐỨNG HÌNH THẬT SỰ -
      đây là giới hạn hiện tại của thuật toán, không phải lỗi. Xem
      MAZE_PASSAGE_WIDTH/MAZE_WALL_WIDTH trong config.py để đánh đổi lại
      (rộng hơn = nhanh hơn nhiều nhưng thưa hơn/ít khúc quanh hơn).
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
# 2. Chọn điểm trên mê cung (BFS + farthest-point sampling)
# ============================================================
def bfs_distances(blocked, start):
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


def farthest_point(blocked, start):
    """Ô XA `start` nhất (theo số bước đi 4 hướng) mà từ `start` CÓ THỂ
    tới được - dùng đặt đích/thức ăn, đảm bảo LUÔN có đường đi thật sự."""
    dist = bfs_distances(blocked, start)
    return max(dist, key=dist.get)


def scatter_points(dist, count, rng):
    """Chọn `count` ô CÀNG TRẢI ĐỀU khắp mê cung càng tốt (farthest-point
    sampling): điểm đầu tiên là ô xa tổ nhất; mỗi điểm tiếp theo là ô có
    khoảng cách TỐI THIỂU tới các điểm đã chọn LỚN NHẤT - đảm bảo các
    điểm nằm rải rác khắp các ngóc ngách mê cung, không dồn cụm 1 chỗ."""
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
