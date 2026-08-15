# -*- coding: utf-8 -*-
"""Sinh 1 mê cung (nhiều bức tường đá dài, ngoằn ngoèo) TRỰC TIẾP vào bản
đồ THẬT (state.surface_world) đang được đàn kiến thật chơi, thay vì dựng
1 world minh họa tách biệt. Nhờ đó có thể xem đàn kiến thật tự tìm đường
xuyên mê cung bằng ĐÚNG thuật toán any-angle A* trên visibility graph
(pathfinding.py) mà cả game đang dùng - không phải 1 bản sao/mô phỏng lại.

Kích hoạt qua nút "Sinh me cung" trong toolbar (xem hud.py) hoặc gọi trực
tiếp GameState.generate_maze().
"""
from collections import deque

import numpy as np

from . import config as cfg


def _farthest_reachable_cell(blocked, start):
    """BFS 4 hướng từ `start`, trả về ô XA NHẤT (theo số bước đi) mà từ
    `start` CÓ THỂ tới được - dùng để đặt thức ăn ở điểm chắc chắn có
    đường đi thật sự xuyên mê cung tới đó (không rơi vào 1 túi bị tách
    biệt bởi tường)."""
    n = blocked.shape[0]
    visited = np.zeros_like(blocked)
    visited[start] = True
    farthest = start
    max_dist = 0
    q = deque([(start, 0)])
    while q:
        (x, y), d = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and not blocked[nx, ny] and not visited[nx, ny]:
                visited[nx, ny] = True
                nd = d + 1
                if nd > max_dist:
                    max_dist = nd
                    farthest = (nx, ny)
                q.append(((nx, ny), nd))
    return farthest, max_dist


def generate_maze_in_world(state):
    """Xóa sạch đá/nước hiện có trên bản đồ thật, rải 1 mê cung mới, rồi
    đặt 1 cụm thức ăn lớn ở ô xa tổ nhất còn liên thông được - vừa đủ để
    cả đàn phải tự tìm đường xuyên mê cung mới lấy được, đúng bằng bộ máy
    tìm đường THẬT của game (không phải bản minh họa riêng).

    Vài lựa chọn THIẾT KẾ đáng chú ý (đúc kết từ báo cáo cải tiến FA-A* và
    lần thử nghiệm tab demo tách biệt trước đó - xem lịch sử commit):

    - Dùng tường đá DÀI, ngoằn ngoèo (giống hệt cách world.py sinh tường
      đá lúc khởi tạo bản đồ) thay vì mê cung "phủ kín 100% ô" kiểu
      recursive-backtracker cổ điển. Mê cung phủ kín tạo ra HÀNG NGHÌN
      đỉnh góc vật cản, khiến bước dựng visibility graph (O(V^2), xem
      pathfinding.VisibilityPathfinder._build_static_edges) mất hàng
      chục giây mỗi lần bấm nút - không chấp nhận được. Vài chục bức
      tường dài vẫn tạo cảm giác mê cung thật (phải đi vòng) mà giữ số
      đỉnh ở mức vài trăm - build dưới 1 giây, CHỈ 1 LẦN (vì sau đó toàn
      bộ đàn kiến dùng CHUNG 1 visibility graph đã cache, đúng kịch bản
      "nhiều truy vấn trên 1 bản đồ tĩnh" mà việc cache tĩnh trong
      pathfinding.py được thiết kế để tối ưu).
    - Sau khi rải tường, XÓA đường đi (path_len=0) của MỌI con kiến đang
      có sẵn 1 đường đi dở dang - nếu không, kiến có thể tiếp tục đi nốt
      đoạn đường cũ (tính trước khi có mê cung) xuyên thẳng qua tường mới
      đặt, tới khi nào đi hết đoạn đó mới tính lại đường - trông như
      "kiến đi xuyên tường" trong vài khung hình.
    """
    surface = state.surface_world
    n = cfg.GRID_SIZE
    nest_x, nest_y = cfg.NEST_POS
    rng = np.random.default_rng()

    # --- Xóa sạch đá/nước hiện có (bán kính phủ cả bản đồ) ---
    surface.remove_features_near(nest_x, nest_y, radius=n * 2)

    # --- Rải các bức tường đá dài, ngoằn ngoèo ---
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for _ in range(cfg.MAZE_NUM_WALLS):
        x, y = int(rng.integers(1, n - 1)), int(rng.integers(1, n - 1))
        length = int(rng.integers(*cfg.MAZE_WALL_LEN_RANGE))
        dx, dy = dirs[rng.integers(0, 4)]
        for _step in range(length):
            if 0 <= x < n and 0 <= y < n:
                if np.hypot(x - nest_x, y - nest_y) > cfg.TERRAIN_SAFE_RADIUS_FROM_NEST:
                    surface.add_rock_cell(x, y)
            if rng.random() < cfg.MAZE_TURN_CHANCE:
                dx, dy = dirs[rng.integers(0, 4)]
            x, y = x + dx, y + dy
            if not (0 <= x < n and 0 <= y < n):
                break

    # --- Đặt 1 cụm thức ăn lớn ở ô xa tổ nhất còn liên thông được ---
    blocked = surface.terrain != cfg.TERRAIN_EMPTY
    start_cell = (int(nest_x), int(nest_y))
    if not blocked[start_cell]:
        far_cell, _dist = _farthest_reachable_cell(blocked, start_cell)
        state.place_food_at(far_cell[0], far_cell[1], amount=cfg.MAZE_FOOD_AMOUNT)

    # --- Kiến đang có đường đi dở dang (tính trước khi có mê cung) phải
    # bỏ, để tick sau tự tính lại đường MỚI xuyên đúng mê cung vừa rải ---
    for colony in state.ALL_COLONIES:
        if hasattr(colony, "path_len"):
            colony.path_len[:] = 0
            colony.path_idx[:] = 0
