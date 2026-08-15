# -*- coding: utf-8 -*-
"""Tìm đường "any-angle" (đi thẳng theo MỌI góc, không bị ép ngang/dọc/chéo
như A* lưới thường) dựa trên bài báo "A Focal Any-Angle Path-finding
Algorithm Based on A* on Visibility Graphs" (Cao, Fan, Gao, Tang).

Bản đồ của game (40x40 ô, vài chục vật cản) đủ nhỏ để không cần bước rút
gọn "Candidate Vertices" (phần lõi của FA-A* trong bài báo) - ta dựng
THẲNG visibility graph đầy đủ (giống baseline "A* on Visibility Graphs"
mà bài báo dùng để so sánh) và chạy A* trên đó. Cách này giữ đúng 2 phần
cốt lõi khác của bài báo:

  1. Đỉnh của đồ thị = các GÓC LỒI của vật cản (không phải mọi ô lưới) -
     xem mục II của bài báo.
  2. Kiểm tra "tầm nhìn" (visibility/line-of-sight) giữa 2 điểm bằng
     ray-casting kiểu slab-test (tương đương thuật toán Amanatides & Woo
     mà bài báo trích dẫn ở mục III) - vector hóa toàn bộ bằng NumPy để đủ
     nhanh chạy MỖI TICK cho hàng trăm con kiến.

Vì thế đường đi tìm được LUÔN LÀ ĐƯỜNG NGẮN NHẤT thật sự (optimal), đúng
như "A* on Visibility Graphs" trong Bảng 1-5 của bài báo luôn tìm được
"true shortest path" - đánh đổi là tốc độ kém hơn FA-A* một chút khi có
RẤT NHIều vật cản, nhưng với quy mô bản đồ của game thì không đáng kể.
"""
import heapq
import math

import numpy as np

from . import config as cfg


class VisibilityPathfinder:
    """Bọc quanh 1 SurfaceWorld: trích xuất các đỉnh góc vật cản, dựng
    visibility graph TĨNH giữa các đỉnh đó (cache lại, chỉ dựng lại khi
    địa hình thay đổi - xem SurfaceWorld.terrain_version), rồi mỗi lần
    cần đường đi chỉ phải nối THÊM 2 điểm động (điểm xuất phát + đích) vào
    đồ thị tĩnh đó và chạy A*."""

    def __init__(self, surface):
        self.surface = surface
        self._vertices_version = -1
        self._edges_version = -1
        self._vertices = np.zeros((0, 2), dtype=np.float32)
        self._pinch_points = np.zeros((0, 2), dtype=np.float32)
        self._blocked_cells = np.zeros((0, 2), dtype=np.float32)
        # "Đường ghép" (seam) giữa 2 ô đá/nước NẰM CẠNH NHAU - 1 tia đi
        # DỌC ĐÚNG theo đường ranh giới chung giữa 2 ô đều bị chặn sẽ
        # không lọt vào phần "bên trong" của ô nào cả (test slab-per-ô ở
        # dưới chỉ xét nội bộ 1 ô), nên phải chặn RIÊNG các đường ghép này
        # - nếu không kiến có thể "lách" dọc theo đúng khe nối giữa 2 viên
        # đá liền kề mà không bị coi là chạm vật cản.
        self._v_seam_x = np.zeros(0, dtype=np.float32)
        self._v_seam_y0 = np.zeros(0, dtype=np.float32)
        self._h_seam_y = np.zeros(0, dtype=np.float32)
        self._h_seam_x0 = np.zeros(0, dtype=np.float32)
        self._static_edges = {}

    # ------------------------------------------------------------------
    def _rebuild_vertices_if_needed(self):
        """Chỉ trích xuất lại ĐỈNH (rẻ, không có bước O(V^2)) - dùng nội bộ
        trước khi build_static_edges(); tách riêng để có thể tái sử dụng
        nếu sau này cần 1 chế độ tìm đường không cache."""
        if self._vertices_version == self.surface.terrain_version:
            return
        self._vertices_version = self.surface.terrain_version
        self._extract_vertices()

    def _rebuild_if_needed(self):
        self._rebuild_vertices_if_needed()
        if self._edges_version == self.surface.terrain_version:
            return
        self._edges_version = self.surface.terrain_version
        self._build_static_edges()

    def _extract_vertices(self):
        """Đỉnh của visibility graph = các GÓC (điểm nguyên trên lưới) mà
        tại đó địa hình đổi từ trống sang chặn - CHỈ những góc "lồi" (nhìn
        thấy được từ vùng trống) mới hữu ích, xem Fig.3/Fig.5 bài báo."""
        n = cfg.GRID_SIZE
        blocked = self.surface.terrain != cfg.TERRAIN_EMPTY
        self._blocked_cells = np.argwhere(blocked).astype(np.float32)

        # Đường ghép dọc: 2 ô (i,j) và (i+1,j) cùng bị chặn -> đường ranh
        # giới chung của chúng (x = i+1, y từ j tới j+1) là "đặc", không
        # được đi dọc theo. Tương tự cho đường ghép ngang.
        v_seam = blocked[:-1, :] & blocked[1:, :]
        vi, vj = np.where(v_seam)
        v_seam_x = [(vi + 1).astype(np.float32)]
        v_seam_y0 = [vj.astype(np.float32)]

        h_seam = blocked[:, :-1] & blocked[:, 1:]
        hi, hj = np.where(h_seam)
        h_seam_y = [(hj + 1).astype(np.float32)]
        h_seam_x0 = [hi.astype(np.float32)]

        # Biên bản đồ CŨNG được coi là "đặc" (kiến không đi ra ngoài biên,
        # xem phần đệm padding=True ngay dưới đây) - nên 1 ô đá/nước nằm
        # SÁT biên cũng tạo ra 1 "khe nối" với chính biên đó, giống hệt
        # khe nối giữa 2 ô vật cản thường (nếu bỏ sót, đường any-angle có
        # thể "trượt" dọc đúng theo rìa bản đồ ngay sát 1 viên đá nằm sát
        # biên - phát hiện được qua thực nghiệm kiểm chứng độc lập).
        left = np.where(blocked[0, :])[0]
        v_seam_x.append(np.zeros(len(left), dtype=np.float32))
        v_seam_y0.append(left.astype(np.float32))
        right = np.where(blocked[n - 1, :])[0]
        v_seam_x.append(np.full(len(right), float(n), dtype=np.float32))
        v_seam_y0.append(right.astype(np.float32))
        bottom = np.where(blocked[:, 0])[0]
        h_seam_y.append(np.zeros(len(bottom), dtype=np.float32))
        h_seam_x0.append(bottom.astype(np.float32))
        top = np.where(blocked[:, n - 1])[0]
        h_seam_y.append(np.full(len(top), float(n), dtype=np.float32))
        h_seam_x0.append(top.astype(np.float32))

        self._v_seam_x = np.concatenate(v_seam_x)
        self._v_seam_y0 = np.concatenate(v_seam_y0)
        self._h_seam_y = np.concatenate(h_seam_y)
        self._h_seam_x0 = np.concatenate(h_seam_x0)

        # Đệm biên = "chặn" để góc ở rìa bản đồ không bị coi là góc lồi đi
        # xuyên ra ngoài bản đồ (giữ hành vi "không đi ra ngoài biên" cũ)
        padded = np.ones((n + 2, n + 2), dtype=bool)
        padded[1:-1, 1:-1] = blocked

        verts = []
        pinches = []
        for cx in range(0, n + 1):
            col_a = padded[cx, :]
            col_b = padded[cx + 1, :]
            for cy in range(0, n + 1):
                # ÉP KIỂU int TƯỜNG MINH: numpy.bool_ + numpy.bool_ trả về
                # PHÉP OR LOGIC (bão hòa ở True), KHÔNG phải phép cộng số
                # nguyên - nếu để nguyên kiểu bool, biến cnt bên dưới sẽ
                # luôn chỉ là True/False, khiến toàn bộ logic đếm số ô bị
                # chặn quanh 1 góc (0/1/2/3/4) chạy SAI hoàn toàn (không hề
                # báo lỗi vì bool hỗ trợ toán tử + một cách âm thầm) - lỗi
                # này khiến bước phát hiện "điểm kẹp chéo" (pinch point,
                # 2 vật cản chạm đúng 1 góc) không bao giờ kích hoạt được.
                a = int(col_a[cy])          # ô (cx-1, cy-1)
                b = int(col_b[cy])          # ô (cx,   cy-1)
                c = int(col_a[cy + 1])      # ô (cx-1, cy)
                d = int(col_b[cy + 1])      # ô (cx,   cy)
                cnt = a + b + c + d
                if cnt == 0 or cnt == 4:
                    continue  # hoàn toàn trống hoặc hoàn toàn bị chặn - vô dụng
                if cnt == 2 and a == d and b == c and a != b:
                    # 2 ô chéo bị chặn, 2 ô chéo còn lại trống ("kẹp chéo")
                    # - KHÔNG coi là đỉnh đi qua được (không cho "cắt góc"
                    # lách qua khe giữa 2 vật cản chạm chéo nhau, xem Fig.4
                    # bài báo "Diagonal move in between obstacles")
                    pinches.append((cx, cy))
                    continue
                verts.append((cx, cy))

        self._vertices = np.array(verts, dtype=np.float32) if verts else np.zeros((0, 2), dtype=np.float32)
        self._pinch_points = (
            np.array(pinches, dtype=np.float32) if pinches else np.zeros((0, 2), dtype=np.float32)
        )

    def _build_static_edges(self):
        verts = self._vertices
        v = len(verts)
        edges = {i: [] for i in range(v)}
        for i in range(v):
            if i + 1 >= v:
                break
            visible = self._batch_visible(verts[i], verts[i + 1:])
            js = np.where(visible)[0] + (i + 1)
            if len(js) == 0:
                continue
            dxy = verts[js] - verts[i]
            dists = np.hypot(dxy[:, 0], dxy[:, 1])
            for j, d in zip(js, dists):
                d = float(d)
                edges[i].append((int(j), d))
                edges[int(j)].append((i, d))
        self._static_edges = edges

    # ------------------------------------------------------------------
    def _batch_visible(self, p, targets):
        """Kiểm tra tầm nhìn (ray-casting/slab-test, vector hóa) từ 1 điểm
        p tới NHIỀU điểm targets cùng lúc - tương đương mục III bài báo
        (Eqs. 6-7), áp dụng cho từng ô vật cản đơn vị trong khung bao của
        đoạn thẳng."""
        m = len(targets)
        if m == 0:
            return np.zeros(0, dtype=bool)
        px, py = float(p[0]), float(p[1])
        tx = targets[:, 0].astype(np.float64)
        ty = targets[:, 1].astype(np.float64)
        dx = tx - px
        dy = ty - py

        visible = np.ones(m, dtype=bool)
        blocked_cells = self._blocked_cells
        if len(blocked_cells):
            cx = blocked_cells[:, 0].astype(np.float64)[None, :]
            cy = blocked_cells[:, 1].astype(np.float64)[None, :]
            dxb = dx[:, None]
            dyb = dy[:, None]

            with np.errstate(divide="ignore", invalid="ignore"):
                safe_dx = np.where(dxb == 0, 1.0, dxb)
                t1 = (cx - px) / safe_dx
                t2 = (cx + 1.0 - px) / safe_dx
                tminx = np.minimum(t1, t2)
                tmaxx = np.maximum(t1, t2)
                vertical = dxb == 0
                within_x = (px > cx) & (px < cx + 1.0)
                tminx = np.where(vertical, np.where(within_x, -np.inf, np.inf), tminx)
                tmaxx = np.where(vertical, np.where(within_x, np.inf, -np.inf), tmaxx)

                safe_dy = np.where(dyb == 0, 1.0, dyb)
                t3 = (cy - py) / safe_dy
                t4 = (cy + 1.0 - py) / safe_dy
                tminy = np.minimum(t3, t4)
                tmaxy = np.maximum(t3, t4)
                horizontal = dyb == 0
                within_y = (py > cy) & (py < cy + 1.0)
                tminy = np.where(horizontal, np.where(within_y, -np.inf, np.inf), tminy)
                tmaxy = np.where(horizontal, np.where(within_y, np.inf, -np.inf), tmaxy)

                tmin = np.maximum(np.maximum(tminx, tminy), 0.0)
                tmax = np.minimum(np.minimum(tmaxx, tmaxy), 1.0)
                blocked_pair = tmax > tmin + 1e-9

            visible &= ~np.any(blocked_pair, axis=1)

        pinches = self._pinch_points
        if len(pinches) and np.any(visible):
            px_p = pinches[:, 0][None, :]
            py_p = pinches[:, 1][None, :]
            dxb = dx[:, None]
            dyb = dy[:, None]
            denom = dxb * dxb + dyb * dyb
            safe_denom = np.where(denom == 0, 1.0, denom)
            t = ((px_p - px) * dxb + (py_p - py) * dyb) / safe_denom
            t = np.clip(t, 0.0, 1.0)
            footx = px + t * dxb
            footy = py + t * dyb
            dist2 = (footx - px_p) ** 2 + (footy - py_p) ** 2
            pinch_hit = np.any(dist2 < 1e-6, axis=1)
            visible &= ~pinch_hit

        # Chặn riêng các tia đi THẲNG ĐỨNG/NẰM NGANG trùng đúng 1 đường
        # ghép giữa 2 ô liền kề cùng bị chặn (xem giải thích ở _v_seam_x/
        # _h_seam_y) - chỉ có thể xảy ra khi tia đúng trục (dx=0 hoặc
        # dy=0), nên số điểm cần xét thường rất ít, vòng lặp Python nhỏ ở
        # đây không ảnh hưởng hiệu năng.
        if np.any(visible):
            vert_idx = np.where(visible & (dx == 0) & (len(self._v_seam_x) > 0))[0]
            for k in vert_idx:
                y0, y1 = (py, ty[k]) if py <= ty[k] else (ty[k], py)
                cand = self._v_seam_x == px
                if np.any(cand):
                    ys0 = self._v_seam_y0[cand]
                    overlap = np.minimum(y1, ys0 + 1.0) - np.maximum(y0, ys0)
                    if np.any(overlap > 1e-9):
                        visible[k] = False

            horiz_idx = np.where(visible & (dy == 0) & (len(self._h_seam_y) > 0))[0]
            for k in horiz_idx:
                x0, x1 = (px, tx[k]) if px <= tx[k] else (tx[k], px)
                cand = self._h_seam_y == py
                if np.any(cand):
                    xs0 = self._h_seam_x0[cand]
                    overlap = np.minimum(x1, xs0 + 1.0) - np.maximum(x0, xs0)
                    if np.any(overlap > 1e-9):
                        visible[k] = False

        return visible

    def line_of_sight(self, p, q):
        """Kiểm tra tầm nhìn giữa đúng 2 điểm (tiện dùng ngoài module).

        Tự đảm bảo dữ liệu hình học (ô vật cản/điểm kẹp chéo/đường ghép)
        đã sẵn sàng trước khi kiểm tra - KHÔNG dựa vào việc người gọi đã
        lỡ gọi find_path() trước đó hay chưa. Thiếu bước này, gọi thẳng
        line_of_sight() trên 1 VisibilityPathfinder vừa khởi tạo (chưa
        từng find_path() lần nào) sẽ luôn trả về "nhìn thấy" SAI (vì
        _blocked_cells vẫn đang rỗng từ __init__) - lỗi này chỉ bị phát
        hiện nhờ viết unit test riêng cho line_of_sight(), không hề gây
        ảnh hưởng trong game vì nơi gọi duy nhất trước giờ (find_path) đã
        luôn tự rebuild trước khi gọi hàm này."""
        self._rebuild_vertices_if_needed()
        target = np.array([[q[0], q[1]]], dtype=np.float32)
        return bool(self._batch_visible(p, target)[0])

    # ------------------------------------------------------------------
    def find_path(self, start, target):
        """Trả về danh sách điểm rẽ hướng (không kể điểm start) tạo thành
        đường đi NGẮN NHẤT any-angle từ start tới target, tránh vật cản -
        hoặc None nếu không tồn tại đường đi (bị vây kín hoàn toàn)."""
        self._rebuild_if_needed()
        n = cfg.GRID_SIZE
        sx = float(np.clip(start[0], 0, n - 1))
        sy = float(np.clip(start[1], 0, n - 1))
        tx = float(np.clip(target[0], 0, n - 1))
        ty = float(np.clip(target[1], 0, n - 1))
        start = (sx, sy)
        target = (tx, ty)

        if self.line_of_sight(start, target):
            return [target]

        verts = self._vertices
        v = len(verts)
        if v == 0:
            return None

        start_vis = self._batch_visible(start, verts)
        target_vis = self._batch_visible(target, verts)
        start_edges = np.where(start_vis)[0]
        target_edge_set = set(np.where(target_vis)[0].tolist())
        if len(start_edges) == 0:
            return None

        dxy = verts[start_edges] - np.array(start, dtype=np.float32)
        start_dists = np.hypot(dxy[:, 0], dxy[:, 1])

        def heuristic(i):
            vx, vy = verts[i]
            return math.hypot(vx - target[0], vy - target[1])

        g = {}
        parent = {}
        for idx, dist in zip(start_edges.tolist(), start_dists.tolist()):
            g[idx] = float(dist)
            parent[idx] = None

        best_total = math.inf
        best_last = None
        open_heap = []
        for idx in start_edges.tolist():
            fscore = g[idx] + heuristic(idx)
            heapq.heappush(open_heap, (fscore, idx))
            if idx in target_edge_set:
                total = g[idx] + math.hypot(verts[idx][0] - target[0], verts[idx][1] - target[1])
                if total < best_total:
                    best_total = total
                    best_last = idx

        closed = set()
        static_edges = self._static_edges
        while open_heap:
            f, u = heapq.heappop(open_heap)
            if u in closed:
                continue
            if f - 1e-6 > best_total:
                break  # không thể tìm được đường ngắn hơn best_total nữa
            closed.add(u)
            for vidx, dist in static_edges.get(u, ()):
                if vidx in closed:
                    continue
                ng = g[u] + dist
                if ng < g.get(vidx, math.inf):
                    g[vidx] = ng
                    parent[vidx] = u
                    heapq.heappush(open_heap, (ng + heuristic(vidx), vidx))
                    if vidx in target_edge_set:
                        total = ng + math.hypot(verts[vidx][0] - target[0], verts[vidx][1] - target[1])
                        if total < best_total:
                            best_total = total
                            best_last = vidx

        if best_last is None:
            return None

        chain = []
        cur = best_last
        while cur is not None:
            chain.append((float(verts[cur][0]), float(verts[cur][1])))
            cur = parent[cur]
        chain.reverse()
        chain.append(target)
        return chain
