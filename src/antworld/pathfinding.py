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


def _merge_blocked_rectangles(blocked):
    """Gộp các ô vật cản liền kề thành các HÌNH CHỮ NHẬT lớn nhất có thể
    (thuật toán "mở rộng dọc theo cột lặp lại" kinh điển cho bài toán gộp
    ô lưới nhị phân) - trả về mảng (R,4) mỗi hàng [x0,x1,y0,y1] (vùng che
    phủ x∈[x0,x1), y∈[y0,y1)). Union các hình chữ nhật này LUÔN bằng
    chính xác tập ô vật cản gốc (không thừa/thiếu 1 ô nào) - đây là bước
    TỐI ƯU HIỆU NĂNG THUẦN TÚY (giảm số "vật cản" phải quét khi kiểm tra
    tầm nhìn, xem _extract_vertices), không thay đổi kết quả hình học."""
    n = blocked.shape[0]
    rects = []
    open_rects = {}  # (x0,x1) -> y_bat_dau, cho hinh dang duoc "keo dai" tu hang truoc
    for y in range(n):
        col = blocked[:, y]
        row_intervals = []
        x = 0
        while x < n:
            if col[x]:
                x0 = x
                while x < n and col[x]:
                    x += 1
                row_intervals.append((x0, x))
            else:
                x += 1
        row_set = set(row_intervals)
        for key in list(open_rects.keys()):
            if key not in row_set:
                y0 = open_rects.pop(key)
                rects.append((key[0], key[1], y0, y))
        for key in row_intervals:
            if key not in open_rects:
                open_rects[key] = y
    for key, y0 in open_rects.items():
        rects.append((key[0], key[1], y0, n))
    if not rects:
        return np.zeros((0, 4), dtype=np.float32)
    return np.array(rects, dtype=np.float32)


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
        self._blocked_rects = np.zeros((0, 4), dtype=np.float32)
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
        # Heuristic ALT (A*, Landmarks, Triangle inequality) - xem
        # _build_landmarks(). (V, k): khoảng cách NGẮN NHẤT THẬT SỰ từ mỗi
        # đỉnh tới từng mốc, dùng để tăng tốc tìm đường trong mê cung (nơi
        # đường chim bay là heuristic quá yếu).
        self._landmark_dist = np.zeros((0, 0), dtype=np.float64)

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
        self._build_landmarks()

    def _extract_vertices(self):
        """Đỉnh của visibility graph = các GÓC (điểm nguyên trên lưới) mà
        tại đó địa hình đổi từ trống sang chặn - CHỈ những góc "lồi" (nhìn
        thấy được từ vùng trống) mới hữu ích, xem Fig.3/Fig.5 bài báo."""
        n = cfg.GRID_SIZE
        blocked = self.surface.terrain != cfg.TERRAIN_EMPTY
        # Gộp các ô vật cản liền kề thành HÌNH CHỮ NHẬT lớn (thay vì giữ
        # từng ô 1x1 riêng lẻ) trước khi dùng cho phép kiểm tra tầm nhìn -
        # xem _merge_blocked_rectangles(). Với vài bức tường đá rời rạc
        # kiểu game gốc, số ô 1x1 vốn đã nhỏ (~100-300) nên bước này không
        # tạo khác biệt gì; nhưng với MÊ CUNG dạng lưới (maze_generator.py,
        # tường chỉ dày 1 ô nhưng có tới ~600+ ô rời rạc), việc gộp thành
        # ~100-200 hình chữ nhật giảm thẳng số "ô vật cản" mà mỗi lần kiểm
        # tra tầm nhìn phải quét qua - đo thực tế giảm thời gian mỗi truy
        # vấn tìm đường từ ~50-80ms xuống dưới 5ms trên mê cung ~650 đỉnh.
        self._blocked_rects = _merge_blocked_rectangles(blocked)

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
    def _dijkstra_all(self, source_idx):
        """Khoảng cách NGẮN NHẤT THẬT SỰ (đi qua các cạnh của visibility
        graph tĩnh, không phải đường chim bay) từ đỉnh source_idx tới MỌI
        đỉnh khác - dùng làm dữ liệu nền cho heuristic ALT bên dưới."""
        v = len(self._vertices)
        dist = np.full(v, np.inf, dtype=np.float64)
        dist[source_idx] = 0.0
        visited = np.zeros(v, dtype=bool)
        heap = [(0.0, source_idx)]
        edges = self._static_edges
        while heap:
            d, u = heapq.heappop(heap)
            if visited[u]:
                continue
            visited[u] = True
            for w, cost in edges.get(u, ()):
                nd = d + cost
                if nd < dist[w]:
                    dist[w] = nd
                    heapq.heappush(heap, (nd, w))
        return dist

    def _build_landmarks(self):
        """Heuristic ALT (A*, Landmarks, Triangle inequality - Goldberg &
        Harrelson 2005): đường chim bay (Euclidean) là heuristic ĐÚNG
        (không bao giờ ước lượng thừa - vẫn đảm bảo A* ra đường ngắn nhất
        thật) nhưng RẤT YẾU trong mê cung ngoằn ngoèo, vì 2 điểm có thể
        rất gần theo đường chim bay nhưng phải đi vòng RẤT xa mới tới được
        (bị tường chắn) - khiến A* phải mở rộng gần hết đồ thị mỗi lần tìm
        đường (đo thực tế: ~50ms/truy vấn trong mê cung ~650 đỉnh, quá
        chậm khi hàng chục kiến cùng cần đường mới mỗi tick).

        ALT khắc phục bằng cách chọn sẵn vài đỉnh "mốc" (landmark), tính
        trước khoảng cách NGẮN NHẤT THẬT SỰ (Dijkstra trên chính visibility
        graph, không phải đường chim bay) từ mỗi mốc tới MỌI đỉnh khác - 1
        LẦN mỗi khi địa hình đổi (giống hệt cách static_edges được cache,
        xem _rebuild_if_needed). Với 2 điểm bất kỳ p, q và 1 mốc L, bất
        đẳng thức tam giác cho |d(p,L) - d(q,L)| <= d(p,q) LUÔN đúng với d
        là khoảng cách NGẮN NHẤT thật (không phải đường chim bay) - nên
        đây vẫn là 1 heuristic HỢP LỆ (không overestimate, A* vẫn tìm đúng
        đường ngắn nhất), chỉ là CHẶT hơn hẳn Euclidean vì đã "biết trước"
        hình dạng mê cung qua các mốc, thay vì giả định không gian trống.

        Mốc được chọn bằng "farthest-point sampling": mốc đầu là đỉnh xa
        đỉnh 0 nhất (theo đường thật), mỗi mốc tiếp theo là đỉnh xa TẤT CẢ
        mốc đã chọn nhất - giúp các mốc trải khắp bản đồ thay vì dồn 1 góc.
        """
        v = len(self._vertices)
        k = min(cfg.PATH_NUM_LANDMARKS, v)
        if k == 0:
            self._landmark_dist = np.zeros((0, v), dtype=np.float64)
            return
        d0 = self._dijkstra_all(0)
        first = int(np.argmax(np.nan_to_num(d0, nan=-1.0, posinf=-1.0)))
        dists = [self._dijkstra_all(first)]
        for _ in range(k - 1):
            min_to_set = np.min(np.stack(dists), axis=0)
            safe = np.nan_to_num(min_to_set, nan=-1.0, posinf=-1.0)
            nxt = int(np.argmax(safe))
            if not np.isfinite(min_to_set[nxt]) and len(dists) > 1:
                break  # đồ thị rời rạc (nhiều mảng tách biệt) - đủ mốc rồi
            dists.append(self._dijkstra_all(nxt))
        # (V, k) thay vì (k, V) để heuristic() bên dưới đọc theo HÀNG (mỗi
        # đỉnh 1 hàng liên tục trong bộ nhớ) - nhanh hơn khi gọi hàng nghìn
        # lần/truy vấn tìm đường.
        self._landmark_dist = np.stack(dists, axis=1)

    # ------------------------------------------------------------------
    def _batch_visible(self, p, targets):
        """Kiểm tra tầm nhìn (ray-casting/slab-test, vector hóa) từ 1 điểm
        p tới NHIỀU điểm targets cùng lúc - tương đương mục III bài báo
        (Eqs. 6-7), áp dụng cho từng HÌNH CHỮ NHẬT vật cản (đã gộp từ các
        ô liền kề, xem _merge_blocked_rectangles) trong khung bao của
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
        rects = self._blocked_rects
        if len(rects):
            rx0 = rects[:, 0].astype(np.float64)[None, :]
            rx1 = rects[:, 1].astype(np.float64)[None, :]
            ry0 = rects[:, 2].astype(np.float64)[None, :]
            ry1 = rects[:, 3].astype(np.float64)[None, :]
            dxb = dx[:, None]
            dyb = dy[:, None]

            with np.errstate(divide="ignore", invalid="ignore"):
                safe_dx = np.where(dxb == 0, 1.0, dxb)
                t1 = (rx0 - px) / safe_dx
                t2 = (rx1 - px) / safe_dx
                tminx = np.minimum(t1, t2)
                tmaxx = np.maximum(t1, t2)
                vertical = dxb == 0
                within_x = (px > rx0) & (px < rx1)
                tminx = np.where(vertical, np.where(within_x, -np.inf, np.inf), tminx)
                tmaxx = np.where(vertical, np.where(within_x, np.inf, -np.inf), tmaxx)

                safe_dy = np.where(dyb == 0, 1.0, dyb)
                t3 = (ry0 - py) / safe_dy
                t4 = (ry1 - py) / safe_dy
                tminy = np.minimum(t3, t4)
                tmaxy = np.maximum(t3, t4)
                horizontal = dyb == 0
                within_y = (py > ry0) & (py < ry1)
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
        # dy=0). Vector hóa TOÀN BỘ bằng NumPy (không vòng lặp Python theo
        # từng đỉnh): với bản đồ vật cản ĐẶT NGẪU NHIÊN/RỜI RẠC, số đỉnh
        # trùng trục với 1 điểm truy vấn gần như luôn là 0 nên vòng lặp cũ
        # (dù có) không ảnh hưởng gì; nhưng với MÊ CUNG dạng lưới đều (xem
        # maze_generator.py), toạ độ đỉnh lặp lại theo chu kỳ cố định nên
        # RẤT NHIỀU đỉnh có thể trùng trục cùng lúc - vòng lặp Python khi
        # đó lặp lại hàng trăm lần MỖI TRUY VẤN, từng đo được chiếm hầu
        # hết thời gian tìm đường (~50ms/truy vấn, gây giật hình rõ rệt
        # khi nhiều kiến cùng cần đường mới 1 lúc).
        if np.any(visible):
            if len(self._v_seam_x):
                seam_here = self._v_seam_x == px
                if np.any(seam_here):
                    ys0 = self._v_seam_y0[seam_here]
                    vert_idx = np.where(visible & (dx == 0))[0]
                    if len(vert_idx):
                        py_arr = np.full(len(vert_idx), py)
                        ty_arr = ty[vert_idx]
                        y0 = np.minimum(py_arr, ty_arr)[:, None]
                        y1 = np.maximum(py_arr, ty_arr)[:, None]
                        overlap = np.minimum(y1, ys0[None, :] + 1.0) - np.maximum(y0, ys0[None, :])
                        blocked_here = np.any(overlap > 1e-9, axis=1)
                        visible[vert_idx[blocked_here]] = False

            if len(self._h_seam_y):
                seam_here = self._h_seam_y == py
                if np.any(seam_here):
                    xs0 = self._h_seam_x0[seam_here]
                    horiz_idx = np.where(visible & (dy == 0))[0]
                    if len(horiz_idx):
                        px_arr = np.full(len(horiz_idx), px)
                        tx_arr = tx[horiz_idx]
                        x0 = np.minimum(px_arr, tx_arr)[:, None]
                        x1 = np.maximum(px_arr, tx_arr)[:, None]
                        overlap = np.minimum(x1, xs0[None, :] + 1.0) - np.maximum(x0, xs0[None, :])
                        blocked_here = np.any(overlap > 1e-9, axis=1)
                        visible[horiz_idx[blocked_here]] = False

        return visible

    def line_of_sight(self, p, q):
        """Kiểm tra tầm nhìn giữa đúng 2 điểm (tiện dùng ngoài module).

        Tự đảm bảo dữ liệu hình học (ô vật cản/điểm kẹp chéo/đường ghép)
        đã sẵn sàng trước khi kiểm tra - KHÔNG dựa vào việc người gọi đã
        lỡ gọi find_path() trước đó hay chưa. Thiếu bước này, gọi thẳng
        line_of_sight() trên 1 VisibilityPathfinder vừa khởi tạo (chưa
        từng find_path() lần nào) sẽ luôn trả về "nhìn thấy" SAI (vì
        _blocked_rects vẫn đang rỗng từ __init__) - lỗi này chỉ bị phát
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
        target_vis_idx = np.where(target_vis)[0]
        target_edge_set = set(target_vis_idx.tolist())
        if len(start_edges) == 0:
            return None

        dxy = verts[start_edges] - np.array(start, dtype=np.float32)
        start_dists = np.hypot(dxy[:, 0], dxy[:, 1])

        # --- Khoảng cách CHÍNH XÁC (không phải đường chim bay) từ target
        # tới từng mốc - xem docstring _build_landmarks(). target không
        # phải là 1 đỉnh có sẵn trong đồ thị, nhưng MỌI đường từ target
        # vào đồ thị đều phải đi qua 1 trong các đỉnh "nhìn thấy" nó, nên
        # lấy min qua các đỉnh đó cho ra khoảng cách THẬT (không phải cận
        # trên gần đúng) - vẫn giữ đúng tính chất "không overestimate" của
        # heuristic ALT.
        landmark_dist = self._landmark_dist
        num_landmarks = landmark_dist.shape[1] if landmark_dist.size else 0
        landmark_to_target = np.full(num_landmarks, np.inf)
        if num_landmarks and len(target_vis_idx):
            dxy_t = verts[target_vis_idx] - np.array(target, dtype=np.float32)
            entry_dist = np.hypot(dxy_t[:, 0], dxy_t[:, 1])
            candidate = landmark_dist[target_vis_idx] + entry_dist[:, None]
            landmark_to_target = np.min(candidate, axis=0)

        def heuristic(i):
            vx, vy = verts[i]
            best = math.hypot(vx - target[0], vy - target[1])
            if num_landmarks:
                row = landmark_dist[i]
                for lk in range(num_landmarks):
                    lt = landmark_to_target[lk]
                    if math.isfinite(lt) and math.isfinite(row[lk]):
                        d = abs(row[lk] - lt)
                        if d > best:
                            best = d
            return best

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
