"""Định nghĩa lớp mặt đất (surface) và lớp hầm ngầm (underground)."""
import math

import numpy as np
from . import config as cfg
from . import pathfinding


class _DirtLayer:
    """Bọc 1 tầng lưới đất (1 phần tử/ô, TERRAIN_ROCK=đất đặc chưa đào,
    TERRAIN_EMPTY=đã đào) - CHỈ để tái sử dụng NGUYÊN VisibilityPathfinder
    (pathfinding.py, vốn viết cho SurfaceWorld) cho việc tìm đường của
    kiến đào (JOB_DIGGER trong ants.py): pathfinder chỉ cần đọc đúng 2
    thuộc tính `terrain`/`terrain_version` của đối tượng truyền vào, không
    quan tâm đó là SurfaceWorld hay không."""
    __slots__ = ("terrain", "terrain_version")

    def __init__(self, size):
        self.terrain = np.full((size, size), cfg.TERRAIN_ROCK, dtype=np.int8)
        self.terrain_version = 0


class SurfaceWorld:
    """Lưới mặt đất: thức ăn + pheromone dẫn đường về tổ."""

    def __init__(self, protected_nests=None):
        n = cfg.GRID_SIZE
        self.food = np.zeros((n, n), dtype=np.float32)
        self.food_type = np.zeros((n, n), dtype=np.int8)  # loại thức ăn tại mỗi ô
        # Số tick liên tục 1 ô CÓ thức ăn mà CHƯA hết (kể từ lần gần nhất
        # được bổ sung/tái sinh) - dùng để biết khi nào thức ăn "quá hạn
        # tươi" và bắt đầu hỏng dần, xem decay_food() bên dưới + FOOD_SPOIL_*
        # trong config.py. Reset về 0 mỗi khi thức ăn Ở Ô ĐÓ được bổ sung
        # thêm (coi như "làm mới" độ tươi), và khi ô hết sạch thức ăn.
        self.food_age = np.zeros((n, n), dtype=np.float32)
        self.pheromone = np.zeros((n, n), dtype=np.float32)
        self.danger_pheromone = np.zeros((n, n), dtype=np.float32)
        self.terrain = np.zeros((n, n), dtype=np.int8)  # 0=đất, 1=đá, 2=nước
        self.terrain_features = []  # [(id, loại, cx, cy, radius), ...] để vẽ 3D
        self._next_feature_id = 0
        # Tăng mỗi khi địa hình đổi (đặt/xóa đá, nước...) - VisibilityPathfinder
        # (pathfinding.py) dùng số này để biết lúc nào cần dựng lại
        # visibility graph, thay vì dựng lại mỗi tick dù địa hình không đổi.
        self.terrain_version = 0
        # "Bản đồ nhiệt" ghi nhận nơi kiến đã đi qua gần đây, dùng để chọn
        # điểm khám phá tiếp theo ưu tiên vùng CHƯA đi (xem
        # AntColony._pick_explore_target trong ants.py) - PHỐI HỢP với
        # self.pheromone (mùi đường tha mồi): visit_heat lo phần "tỏa ra
        # khám phá vùng mới", pheromone lo phần "tuyển mộ quay lại nguồn
        # ăn đã biết" - 2 vai trò bổ sung nhau, giống 2 cơ chế thật ở kiến
        # thật (xem AntColony._sample_recruit_candidates).
        self.visit_heat = np.zeros((n, n), dtype=np.float32)
        self.protected_nests = protected_nests if protected_nests else [cfg.NEST_POS]
        self._spawn_food_clusters()
        self._spawn_terrain_obstacles()

    def _random_food_type(self, rng):
        types = list(cfg.FOOD_TYPE_WEIGHTS.keys())
        weights = list(cfg.FOOD_TYPE_WEIGHTS.values())
        return int(rng.choice(types, p=weights))

    def _spawn_food_clusters(self):
        n = cfg.GRID_SIZE
        rng = np.random.default_rng()
        for _ in range(cfg.FOOD_CLUSTERS):
            cx = rng.integers(4, n - 4)
            cy = rng.integers(4, n - 4)
            r = cfg.FOOD_CLUSTER_RADIUS
            x0, x1 = max(0, cx - r), min(n, cx + r + 1)
            y0, y1 = max(0, cy - r), min(n, cy + r + 1)
            self.food[x0:x1, y0:y1] += cfg.FOOD_PER_CLUSTER
            self.food_type[x0:x1, y0:y1] = self._random_food_type(rng)

    def _spawn_terrain_obstacles(self):
        n = cfg.GRID_SIZE
        rng = np.random.default_rng()

        def random_far_from_nests():
            for _ in range(30):  # thử tối đa 30 lần để tránh quá gần tổ
                cx = rng.integers(3, n - 3)
                cy = rng.integers(3, n - 3)
                if all(
                    np.hypot(cx - nx, cy - ny) > cfg.TERRAIN_SAFE_RADIUS_FROM_NEST
                    for nx, ny in self.protected_nests
                ):
                    return int(cx), int(cy)
            return int(cx), int(cy)  # đành chấp nhận lần thử cuối nếu quá xui

        for _ in range(cfg.NUM_ROCK_CLUSTERS):
            self._spawn_one_rock_wall(random_far_from_nests)

        for _ in range(cfg.NUM_WATER_CLUSTERS):
            cx, cy = random_far_from_nests()
            self.add_obstacle(cx, cy, cfg.TERRAIN_WATER, cfg.WATER_CLUSTER_RADIUS)

    def _spawn_one_rock_wall(self, random_far_from_nests):
        """Sinh 1 BỨC TƯỜNG đá = 1 chuỗi ô đá nối liền nhau, đặt TỪNG Ô
        MỘT bằng add_rock_cell() (không phải tô nguyên 1 khối tròn 1 lần
        như add_obstacle) - đi theo 1 hướng chính, thỉnh thoảng rẽ góc để
        không quá thẳng tắp, trông tự nhiên như 1 vách đá. Mỗi ô là 1
        feature RIÊNG trong terrain_features, nên có thể đập lẻ từng viên
        bằng công cụ xóa thay vì phải xóa nguyên cả cụm."""
        n = cfg.GRID_SIZE
        rng = np.random.default_rng()
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        x, y = random_far_from_nests()
        length = int(rng.integers(cfg.ROCK_WALL_MIN_LEN, cfg.ROCK_WALL_MAX_LEN + 1))
        dx, dy = directions[rng.integers(0, len(directions))]

        for _step in range(length):
            self.add_rock_cell(x, y)

            # Thỉnh thoảng đổi hướng - giữ tường không thẳng tắp cứng nhắc
            # nhưng vẫn đủ thẳng để trông giống 1 bức tường liền mạch.
            if rng.random() < cfg.ROCK_WALL_TURN_CHANCE:
                dx, dy = directions[rng.integers(0, len(directions))]

            nx, ny = x + dx, y + dy
            if not (0 <= nx < n and 0 <= ny < n):
                break  # chạm biên bản đồ - dừng bức tường này sớm
            if any(np.hypot(nx - px, ny - py) <= cfg.TERRAIN_SAFE_RADIUS_FROM_NEST
                   for px, py in self.protected_nests):
                break  # đi lấn vào quá gần tổ giữa chừng - dừng lại
            x, y = nx, ny

    def add_rock_cell(self, x, y):
        """Đặt ĐÚNG 1 Ô đá (khác add_obstacle() vốn tô cả 1 vùng tròn cùng
        lúc) - dùng làm từng "viên gạch" khi ghép chuỗi thành 1 bức tường
        trong _spawn_one_rock_wall(). Mỗi ô đá là 1 feature RIÊNG (bán
        kính 0.5 = đúng 1 ô), khác với add_obstacle() coi cả cụm là 1
        feature duy nhất. Tuân theo đúng thứ tự ưu tiên lớp như
        add_obstacle(): đá đè lên thức ăn (xóa thức ăn tại ô đó)."""
        n = cfg.GRID_SIZE
        x, y = int(x), int(y)
        if not (0 <= x < n and 0 <= y < n):
            return None
        self.terrain[x, y] = cfg.TERRAIN_ROCK
        self.food[x, y] = 0
        self.terrain_version += 1
        fid = self._next_feature_id
        self._next_feature_id += 1
        feature = (fid, cfg.TERRAIN_ROCK, x, y, 0.5)
        self.terrain_features.append(feature)
        return feature

    def add_obstacle(self, cx, cy, terrain_type, radius):
        """Đánh dấu 1 vùng địa hình (đá/nước) trên lưới - dùng cả lúc khởi
        tạo lẫn khi người chơi tự đặt bằng công cụ. Có THỨ TỰ ƯU TIÊN giữa
        các lớp: ĐÁ > NƯỚC > THỨC ĂN - đá luôn "đè lên trên cùng" (đặt đá
        đè lên nước hiện có thì đá thắng), NƯỚC KHÔNG BAO GIỜ đè lên đá đã
        có sẵn (giữ nguyên đá, chỉ lấp phần còn trống), và cả đá lẫn nước
        đều xóa sạch thức ăn nếu lỡ trùng vị trí (thức ăn luôn ở "lớp dưới
        cùng"). Trả về feature (kèm ID duy nhất) để main.py vẽ thêm lên
        màn hình 3D và có thể xóa sau này."""
        n = cfg.GRID_SIZE
        r = int(round(radius))
        x0, x1 = max(0, cx - r), min(n, cx + r + 1)
        y0, y1 = max(0, cy - r), min(n, cy + r + 1)
        # Vùng tròn thay vì vuông, cho tự nhiên hơn
        xs, ys = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1), indexing="ij")
        circle_mask = (xs - cx) ** 2 + (ys - cy) ** 2 <= r ** 2
        txs, tys = xs[circle_mask], ys[circle_mask]

        if terrain_type == cfg.TERRAIN_WATER:
            # Nước không được đè lên đá đã có sẵn - đá luôn ở lớp trên cùng
            allowed = self.terrain[txs, tys] != cfg.TERRAIN_ROCK
            txs, tys = txs[allowed], tys[allowed]

        self.terrain[txs, tys] = terrain_type
        # Xóa thức ăn nếu lỡ trùng vị trí (không cho thức ăn mọc trong đá/nước)
        self.food[txs, tys] = 0
        self.terrain_version += 1
        fid = self._next_feature_id
        self._next_feature_id += 1
        feature = (fid, terrain_type, int(cx), int(cy), float(radius))
        self.terrain_features.append(feature)
        return feature

    def remove_features_near(self, x, y, radius):
        """Xóa các vùng địa hình (đá/nước) có tâm nằm trong bán kính chỉ
        định quanh (x, y) - dùng cho công cụ 'Xóa'. Trả về danh sách các
        feature đã xóa (để main.py hủy entity 3D tương ứng)."""
        n = cfg.GRID_SIZE
        remaining = []
        removed = []
        for feature in self.terrain_features:
            fid, ftype, cx, cy, r = feature
            if np.hypot(cx - x, cy - y) <= radius:
                removed.append(feature)
                rr = int(round(r))
                x0, x1 = max(0, cx - rr), min(n, cx + rr + 1)
                y0, y1 = max(0, cy - rr), min(n, cy + rr + 1)
                xs, ys = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1), indexing="ij")
                mask = (xs - cx) ** 2 + (ys - cy) ** 2 <= rr ** 2
                self.terrain[xs[mask], ys[mask]] = cfg.TERRAIN_EMPTY
            else:
                remaining.append(feature)
        self.terrain_features = remaining
        if removed:
            self.terrain_version += 1
        return removed

    def clear_food_near(self, x, y, radius):
        """Xóa sạch thức ăn trong bán kính chỉ định quanh (x, y) - dùng cho
        công cụ 'Xóa'."""
        n = cfg.GRID_SIZE
        r = int(round(radius))
        x0, x1 = max(0, int(x) - r), min(n, int(x) + r + 1)
        y0, y1 = max(0, int(y) - r), min(n, int(y) + r + 1)
        xs, ys = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1), indexing="ij")
        mask = (xs - x) ** 2 + (ys - y) ** 2 <= r ** 2
        self.food[xs[mask], ys[mask]] = 0

    def is_blocked(self, xi, yi):
        """Trả về mảng bool: ô nào đang là chướng ngại vật (đá/nước)."""
        return self.terrain[xi, yi] != cfg.TERRAIN_EMPTY

    def has_water_source(self):
        """Còn ít nhất 1 ô nước nào trên bản đồ không - nếu bạn lấp hết
        nước bằng đá, tổ sẽ mất hẳn nguồn thu nước."""
        return bool(np.any(self.terrain == cfg.TERRAIN_WATER))

    def decay_pheromone(self):
        self.pheromone *= cfg.PHEROMONE_DECAY
        self.danger_pheromone *= cfg.DANGER_PHEROMONE_DECAY

    def deposit_pheromone(self, xi, yi, amount=None):
        """xi, yi: mảng chỉ số nguyên (đã clip trong biên). `amount` có
        thể là 1 số CỐ ĐỊNH (mặc định cfg.PHEROMONE_DEPOSIT) hoặc 1 MẢNG
        cùng độ dài xi/yi - dùng mảng khi muốn mùi ĐẬM HƠN cho phát hiện
        GIÀU HƠN (xem AntColony._update_returning_ants trong ants.py: để
        lại lượng tỉ lệ với carry_amount từng con), tự nhiên tạo hiệu ứng
        "tuyển mộ" kiểu kiến thật - nguồn càng giá trị thì vệt mùi dẫn tới
        đó càng đậm, càng hút nhiều kiến khác đi theo (xem
        AntColony._sample_recruit_candidates/_pick_explore_target)."""
        if amount is None:
            amount = cfg.PHEROMONE_DEPOSIT
        np.add.at(self.pheromone, (xi, yi), amount)
        np.clip(self.pheromone, 0, cfg.PHEROMONE_MAX, out=self.pheromone)

    def decay_visit(self):
        self.visit_heat *= cfg.VISIT_HEAT_DECAY

    def decay_food(self):
        """Thức ăn để LÂU không ai nhặt sẽ HỎNG dần rồi biến mất - xem
        FOOD_SPOIL_* trong config.py. Gọi 1 LẦN MỖI TICK (như
        decay_pheromone()/decay_visit() ở trên) từ AntColony.update().

        Trước đây thức ăn tồn tại vĩnh viễn cho tới khi bị ăn hết - khác
        thực tế nuôi kiến (mồi để lâu sẽ mốc/hỏng, phải dọn trước khi sinh
        hại). Ở đây food_age đếm số tick liên tục 1 ô CÒN thức ăn; qua
        ngưỡng FOOD_SPOIL_TICKS thì giá trị tự nhân dần với
        FOOD_SPOIL_RATE_PER_TICK (<1) cho tới khi dưới FOOD_MIN_VALUE thì
        coi như hỏng hẳn, xóa sạch khỏi bản đồ."""
        # LƯU Ý: dùng ngưỡng "> 1e-6" (gần như bất kỳ giá trị dương nào),
        # KHÔNG PHẢI "> 0.5" (ngưỡng dùng ở chỗ khác trong game để coi 1 ô
        # là "có thức ăn hiển thị được") - lý do: nếu dùng > 0.5 ở đây,
        # quá trình hỏng sẽ TỰ DỪNG NGAY LÚC giá trị giảm xuống dưới 0.5,
        # để lại 1 lượng "tàn dư" nhỏ (giữa 0.15 và 0.5) tồn tại VĨNH VIỄN,
        # không bao giờ đạt tới FOOD_MIN_VALUE để bị xóa hẳn - đã tự phát
        # hiện lỗi này qua kiểm thử thực tế trước khi commit.
        has_food = self.food > 1e-6
        self.food_age[has_food] += 1.0
        self.food_age[~has_food] = 0.0  # ô trống thì không có gì để tính "tuổi"

        spoiling = has_food & (self.food_age > cfg.FOOD_SPOIL_TICKS)
        if np.any(spoiling):
            self.food[spoiling] *= cfg.FOOD_SPOIL_RATE_PER_TICK
            expired = spoiling & (self.food < cfg.FOOD_MIN_VALUE)
            if np.any(expired):
                self.food[expired] = 0.0
                self.food_age[expired] = 0.0

    def deposit_visit(self, xi, yi):
        np.add.at(self.visit_heat, (xi, yi), cfg.VISIT_HEAT_DEPOSIT)
        np.clip(self.visit_heat, 0, cfg.VISIT_HEAT_MAX, out=self.visit_heat)

    def sample_visit(self, xi, yi):
        return self.visit_heat[xi, yi]

    def deposit_danger(self, x, y):
        """Phát ra mùi báo động nguy hiểm quanh vị trí (x, y) - dùng khi có
        kẻ thù đang hoạt động trên mặt đất, lan tỏa trong bán kính nhỏ."""
        n = cfg.GRID_SIZE
        r = cfg.DANGER_DEPOSIT_RADIUS
        cx, cy = int(round(x)), int(round(y))
        x0, x1 = max(0, cx - r), min(n, cx + r + 1)
        y0, y1 = max(0, cy - r), min(n, cy + r + 1)
        xs, ys = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1), indexing="ij")
        mask = (xs - cx) ** 2 + (ys - cy) ** 2 <= r ** 2
        self.danger_pheromone[xs[mask], ys[mask]] += cfg.DANGER_DEPOSIT_AMOUNT
        np.clip(self.danger_pheromone, 0, cfg.DANGER_PHEROMONE_MAX, out=self.danger_pheromone)

    def sample_danger(self, xi, yi):
        return self.danger_pheromone[xi, yi]

    def take_food(self, xi, yi, amount=1.0):
        """Trừ thức ăn tại các ô, trả về (mảng bool nơi lấy được, mảng loại
        thức ăn tại các ô đó) để tính giá trị dinh dưỡng theo loại."""
        available = self.food[xi, yi] > 0.01
        types = self.food_type[xi, yi].copy()
        self.food[xi[available], yi[available]] -= amount
        np.clip(self.food, 0, None, out=self.food)
        return available, types

    def near_water(self, xi, yi):
        """Trả về mảng bool: ô nào đang ở SÁT MÉP nước (bản thân ô hoặc 4 ô
        liền kề là nước) - dùng để kiến "uống nước" mà không cần đi vào
        hẳn trong nước (nước vẫn chặn đường như 1 chướng ngại vật)."""
        n = cfg.GRID_SIZE
        result = self.terrain[xi, yi] == cfg.TERRAIN_WATER
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxi = np.clip(xi + dx, 0, n - 1)
            nyi = np.clip(yi + dy, 0, n - 1)
            result = result | (self.terrain[nxi, nyi] == cfg.TERRAIN_WATER)
        return result

    def respawn_random_cluster(self):
        """Thêm 1 cụm thức ăn mới ở vị trí ngẫu nhiên - mô phỏng nguồn thức
        ăn xuất hiện theo mùa, KHÔNG vô hạn/tức thời như lúc khởi tạo. CHỈ
        thêm vào những ô còn TRỐNG (không phải đá/nước) - thức ăn không
        bao giờ được phép mọc đè lên địa hình đã có."""
        n = cfg.GRID_SIZE
        rng = np.random.default_rng()
        cx = rng.integers(4, n - 4)
        cy = rng.integers(4, n - 4)
        r = cfg.FOOD_CLUSTER_RADIUS
        x0, x1 = max(0, cx - r), min(n, cx + r + 1)
        y0, y1 = max(0, cy - r), min(n, cy + r + 1)
        empty_mask = self.terrain[x0:x1, y0:y1] == cfg.TERRAIN_EMPTY
        self.food[x0:x1, y0:y1][empty_mask] += cfg.FOOD_RESPAWN_AMOUNT
        self.food_type[x0:x1, y0:y1][empty_mask] = self._random_food_type(rng)
        self.food_age[x0:x1, y0:y1][empty_mask] = 0.0  # "làm mới" độ tươi
        return (int(cx), int(cy))


class UndergroundWorld:
    """Cấu trúc tổ dưới lòng đất: 1 chồng các TẦNG 2D phẳng rời rạc.

    Mỗi phòng nằm trên đúng 1 tầng (depth = số nguyên, 0 = mặt đất, càng lớn
    càng sâu). "Giếng" không còn là 1 điểm 3D riêng - nó CHÍNH LÀ vị trí lỗ
    tổ (nest_x, nest_y), hoạt động như 1 cái thang máy xuyên suốt mọi tầng:
    ở tầng nào bạn cũng thấy nó ở đúng (x, y) đó, nối tới phòng của tầng ấy
    bằng 1 đoạn hành lang phẳng trong CÙNG tầng (không có đường chéo cắt
    xuyên qua nhiều tầng như bản 3D cũ)."""

    def __init__(self, nest_pos=None, label_prefix="", progressive=False):
        """`progressive=True`: tổ bắt đầu CHỈ CÓ Phòng chúa (+ Phòng gác
        cửa, xem giải thích ở unlocked_rooms bên dưới) - các phòng khác
        "gộp chung" tạm thời vào ĐÚNG vị trí + tầng của Phòng chúa (mọi
        thứ dồn vào 1 hốc duy nhất, như tổ kiến MỚI LẬP ngoài đời thật),
        rồi TỰ TÁCH RA thành phòng riêng dần theo quy mô đàn - xem
        unlock_room() và GameState._check_room_unlocks(). `progressive=
        False` (mặc định): đủ 8 phòng ở đúng vị trí thiết kế NGAY TỪ ĐẦU -
        chỉ dùng khi KHÔNG mô phỏng quá trình lập tổ (cfg.
        FOUNDING_MODE_ENABLED=False) hoặc trong test cần 1 tổ đã ổn định
        sẵn để kiểm tra hành vi khác (không phải bản thân cơ chế lập tổ)."""
        nest_pos = nest_pos if nest_pos else cfg.NEST_POS
        nest_x, nest_y = nest_pos
        self.nest_pos = nest_pos
        self.shaft_xy = np.array([nest_x, nest_y], dtype=np.float32)
        self.progressive = progressive

        def offset(off_xy):
            return np.array([nest_x + off_xy[0], nest_y + off_xy[1]], dtype=np.float32)

        self.queen_room = offset(cfg.QUEEN_OFFSET_XY)
        self.queen_depth = cfg.DEPTH_QUEEN

        # unlocked_rooms: tập room_id đã THỰC SỰ được đào thành phòng
        # RIÊNG - progressive=True: CHỈ Phòng chúa (2) - kể cả Phòng gác
        # cửa cũng CHƯA tồn tại cho tới khi có ít nhất 1 lính đầu tiên (xem
        # GameState.ROOM_UNLOCK_SCHEDULE), đúng tinh thần "đào tới đâu có
        # chức năng tới đó, không có phòng nào sẵn trước khi cần tới nó".
        # progressive=False: mở sẵn TẤT CẢ.
        self.unlocked_rooms = set(range(8)) if not progressive else {2}

        real_offsets = {
            0: (cfg.STORAGE_OFFSET_XY, cfg.DEPTH_STORAGE),
            1: (cfg.NURSERY_OFFSET_XY, cfg.DEPTH_NURSERY),
            3: (cfg.WATER_OFFSET_XY, cfg.DEPTH_WATER),
            4: (cfg.EGG_OFFSET_XY, cfg.DEPTH_EGG),
            5: (cfg.GUARD_OFFSET_XY, cfg.DEPTH_GUARD),
            6: (cfg.GRAVEYARD_OFFSET_XY, cfg.DEPTH_GRAVEYARD),
            7: (cfg.PUPA_OFFSET_XY, cfg.DEPTH_PUPA),
        }
        self._real_offsets = real_offsets  # unlock_room() cần lại sau này

        def room_pos_depth(room_id):
            off_xy, real_depth = real_offsets[room_id]
            if room_id in self.unlocked_rooms:
                return offset(off_xy), real_depth
            # CHƯA mở - "gộp" tạm vào đúng vị trí + tầng Phòng chúa, để
            # nội dung của nó (đồ ăn/trứng/ấu trùng...) hiển thị NGAY
            # TRONG vòng tròn Phòng chúa thay vì biến mất/không có chỗ
            # chứa - xem render_underground._draw_merged_room_contents().
            return np.array(self.queen_room, dtype=np.float32, copy=True), self.queen_depth

        self.storage, self.storage_depth = room_pos_depth(0)
        self.nursery, self.nursery_depth = room_pos_depth(1)
        self.water_room, self.water_depth = room_pos_depth(3)
        self.egg_room, self.egg_depth = room_pos_depth(4)
        self.guard_room, self.guard_depth = room_pos_depth(5)
        self.graveyard, self.graveyard_depth = room_pos_depth(6)
        self.pupa_room, self.pupa_depth = room_pos_depth(7)

        # Danh sách phòng để vẽ (id, tên, tâm(x,y), bán kính, màu gợi ý,
        # tầng) - LUÔN ĐÚNG 8 phòng GỐC/CHỨC NĂNG, không đổi SỐ LƯỢNG
        # trong suốt ván (không có chức năng tự đào thêm phòng mới VƯỢT
        # QUÁ 8 phòng gốc - chỉ TÁCH DẦN 8 phòng gốc ra khỏi trạng thái
        # "gộp chung" ban đầu nếu progressive=True) - nhưng BÁN KÍNH của
        # 4 phòng gắn liền quy mô đàn (xem ROOM_GROWABLE_IDS trong
        # config.py) SẼ tự lớn dần theo dân số, xem update_room_sizes()
        # bên dưới - vì vậy mỗi phần tử là 1 LIST (có thể sửa lại phần tử
        # [3]=bán kính, [5]=tầng lúc unlock_room()), KHÔNG PHẢI tuple bất
        # biến như trước, dù cấu trúc/thứ tự các trường vẫn giữ y hệt.
        self._base_radius = {
            0: cfg.ROOM_RADIUS_STORAGE,
            1: cfg.ROOM_RADIUS_NURSERY,
            2: cfg.ROOM_RADIUS_QUEEN,
            3: cfg.ROOM_RADIUS_WATER,
            4: cfg.ROOM_RADIUS_EGG,
            5: cfg.ROOM_RADIUS_GUARD,
            6: cfg.ROOM_RADIUS_GRAVEYARD,
            7: cfg.ROOM_RADIUS_PUPA,
        }
        self.rooms = [
            [0, f"{label_prefix}Kho thức ăn", self.storage, self._base_radius[0], (170, 130, 70), self.storage_depth],
            [1, f"{label_prefix}Ấu trùng", self.nursery, self._base_radius[1], (200, 190, 120), self.nursery_depth],
            [2, f"{label_prefix}Phòng chúa", self.queen_room, self._base_radius[2], (180, 90, 140), self.queen_depth],
            [3, f"{label_prefix}Bể trữ nước", self.water_room, self._base_radius[3], (70, 130, 190), self.water_depth],
            [4, f"{label_prefix}Phòng trứng", self.egg_room, self._base_radius[4], (235, 225, 200), self.egg_depth],
            [5, f"{label_prefix}Phòng gác cửa", self.guard_room, self._base_radius[5], (120, 110, 100), self.guard_depth],
            [6, f"{label_prefix}Nghĩa địa", self.graveyard, self._base_radius[6], (90, 80, 75), self.graveyard_depth],
            [7, f"{label_prefix}Phòng nhộng", self.pupa_room, self._base_radius[7], (150, 130, 95), self.pupa_depth],
        ]
        self._room_pos_attr = {0: "storage", 1: "nursery", 3: "water_room", 4: "egg_room",
                                5: "guard_room", 6: "graveyard", 7: "pupa_room"}
        self._room_depth_attr = {0: "storage_depth", 1: "nursery_depth", 3: "water_depth", 4: "egg_depth",
                                  5: "guard_depth", 6: "graveyard_depth", 7: "pupa_depth"}

        # ===== Lưới đất THẬT (đào tới đâu mới đi/ở được tới đó) =====
        # 1 lưới riêng cho MỖI TẦNG (đủ 5 tầng đang dùng: gác cửa/kho+nước/
        # trứng+ấu trùng+nhộng/chúa/nghĩa địa) - TÁI DÙNG NGUYÊN
        # VisibilityPathfinder (pathfinding.py, vốn viết cho SurfaceWorld)
        # cho việc kiến đào (JOB_DIGGER trong ants.py) tìm đường bò tới rìa
        # đất cần đào, y hệt cách kiến trên mặt đất né đá/nước.
        all_depths = sorted({self.queen_depth} | {d for _, d in real_offsets.values()})
        self.dirt_layers = {d: _DirtLayer(cfg.GRID_SIZE) for d in all_depths}
        self.dig_pathfinders = {}      # depth -> VisibilityPathfinder (tạo khi cần, xem get_dig_pathfinder)
        self._dug_fraction_cache = {}  # (depth,cx,cy,radius) -> (terrain_version, fraction) - xem dug_fraction()
        self.dig_queue = set()         # room_id đã tới mốc dân số nhưng CHƯA đào xong tới nơi thật
        self.reserved_dig_cells = set()  # (depth,gx,gy) đang có 1 con kiến đào nhắm tới - tránh 2 con giành nhau
        self._target_radius = {}       # room_id -> bán kính "MONG MUỐN" theo dân số (xem update_room_sizes) -
                                        # room[3] (bán kính THẬT dùng để kiến đi lại) chỉ đuổi theo dần khi đào tới

        # Giếng lên mặt đất LUÔN thông suốt ở MỌI TẦNG (không phải chờ ai
        # đào - đại diện cho trục thang máy cố định, không thuộc phòng nào)
        for d in all_depths:
            self.dig_disk(d, float(nest_x), float(nest_y), cfg.SHAFT_DIG_RADIUS)

        if progressive:
            # CHỈ đào sẵn HỐC LẬP TỔ ban đầu của chúa (nhỏ) - toàn bộ phần
            # còn lại của tổ (kể cả mở to Phòng chúa sau này, xem
            # AntColony._update_founding_egg_laying) phải chờ digger ants
            # đào dần THẬT, xem ants.py.
            self.dig_disk(self.queen_depth, float(self.queen_room[0]), float(self.queen_room[1]),
                          cfg.ROOM_RADIUS_FOUNDING_CHAMBER)
        else:
            # KHÔNG mô phỏng lập tổ thật (tổ đối thủ / vài test cần 1 tổ ổn
            # định sẵn) - đào sẵn TOÀN BỘ 8 phòng ở đúng vị trí NGAY LẬP
            # TỨC, không cần digger ants nào cả.
            for room in self.rooms:
                self.dig_disk(room[5], float(room[2][0]), float(room[2][1]), float(room[3]) + 1.0)

        # Thống kê tổ
        self.food_in_storage = 0
        self.food_in_nursery = 0
        self.water_in_storage = 0.0
        self.ticks_nursery_empty = 0   # số tick liên tiếp phòng ấu trùng rỗng
        self.ticks_water_empty = 0     # số tick liên tiếp hết nước dự trữ
        self.total_births = 0
        self.total_deaths = 0
        # Nghĩa địa: số "nắm xác" đang hiển thị (giảm dần theo thời gian -
        # xem GRAVEYARD_DECAY_PER_TICK - để không phình to vô hạn)
        self.corpse_count = 0.0
        # Hàng chờ xác DƯỚI HẦM chưa ai khiêng tới nghĩa địa - mỗi phần tử
        # là [x, y, depth] (đủ để 1 nurse rảnh việc biết đi đâu lấy) - xem
        # register_corpse()/claim_next_pending_corpse() bên dưới và
        # AntColony._update_undertakers() trong ants.py. Corpse_count ở
        # trên CHỈ tăng khi xác THỰC SỰ được khiêng tới graveyard, không
        # phải ngay lúc chết.
        self.pending_corpses = []

    def unlock_room(self, room_id):
        """Tách phòng `room_id` ra khỏi trạng thái "gộp chung" (đang dùng
        tạm vị trí + tầng của Phòng chúa) sang ĐÚNG vị trí + tầng thiết kế
        riêng của nó. CHỈ nên gọi khi đã đào xong tới nơi (xem
        try_finish_unlock() - nơi gọi hàm này bình thường) - gọi hàm này
        thẳng (vd trong test) sẽ tách phòng dù đất CHƯA CHẮC đã đào tới,
        chấp nhận được cho mục đích test 1 tổ ổn định sẵn.

        Trả về True nếu VỪA MỚI tách (để bên gọi biết mà báo toast/ghi
        Nhật ký sự kiện), False nếu phòng này đã mở từ trước (gọi lại
        nhiều lần AN TOÀN, không làm gì thêm lần thứ 2 trở đi).

        Mutate vị trí NGAY TRÊN mảng numpy hiện có (self.storage[:] = ...)
        thay vì gán mảng mới, để MỌI chỗ trong ants.py đang giữ tham chiếu
        tới mảng này (self.underground.storage) tự động thấy vị trí MỚI
        ngay lập tức, không cần code nào khác phải "làm mới" lại tham
        chiếu của nó."""
        if room_id in self.unlocked_rooms or room_id not in self._real_offsets:
            return False
        self.unlocked_rooms.add(room_id)
        self.dig_queue.discard(room_id)
        off_xy, real_depth = self._real_offsets[room_id]
        nest_x, nest_y = self.nest_pos
        pos_attr = self._room_pos_attr[room_id]
        depth_attr = self._room_depth_attr[room_id]
        getattr(self, pos_attr)[:] = (nest_x + off_xy[0], nest_y + off_xy[1])
        setattr(self, depth_attr, real_depth)
        self.rooms[room_id][5] = real_depth  # center (index 2) đã tự cập nhật do cùng mảng numpy ở trên
        return True

    def request_dig(self, room_id):
        """Đưa `room_id` vào hàng chờ đào (nếu chưa mở & chưa được yêu
        cầu đào trước đó) - gọi khi đàn tới mốc dân số cần phòng này (xem
        GameState._check_room_unlocks), nhưng việc "tách phòng" THẬT
        (unlock_room) chỉ xảy ra sau khi digger ants đào xong tới đó, xem
        try_finish_unlock()."""
        if room_id in self.unlocked_rooms or room_id not in self._real_offsets:
            return
        self.dig_queue.add(room_id)

    def try_finish_unlock(self, room_id):
        """Nếu `room_id` đang trong hàng chờ đào VÀ đã đào đủ tới vị trí
        THẬT của nó (xem cfg.ROOM_DIG_UNLOCK_FRACTION) thì tách phòng luôn
        (unlock_room) và trả về True - ngược lại trả về False (vẫn đang
        đào dở, hoặc chưa hề được yêu cầu đào)."""
        if room_id not in self.dig_queue:
            return False
        off_xy, depth = self._real_offsets[room_id]
        cx = self.nest_pos[0] + off_xy[0]
        cy = self.nest_pos[1] + off_xy[1]
        radius = self._base_radius[room_id]
        if self.dug_fraction(depth, cx, cy, radius) < cfg.ROOM_DIG_UNLOCK_FRACTION:
            return False
        return self.unlock_room(room_id)

    # ------------------------------------------------------------------
    # Lưới đất THẬT - xem giải thích tổng quan ở __init__ (self.dirt_layers)
    # ------------------------------------------------------------------
    def dig_cell(self, depth, gx, gy):
        """Đào ĐÚNG 1 ô lưới (gx,gy) ở tầng `depth` - gọi từ AntColony
        (JOB_DIGGER) sau khi 1 con kiến đào xong đếm ngược tại ô đó. Trả
        về True nếu ô đó TRƯỚC ĐÓ còn là đất đặc (vừa đào THẬT, cần render
        lại/dựng lại pathfinder), False nếu ô đó đã được đào từ trước
        (gọi lại vô hại, không tăng terrain_version thêm lần nữa)."""
        layer = self.dirt_layers.get(depth)
        if layer is None:
            return False
        n = cfg.GRID_SIZE
        gx = int(np.clip(gx, 0, n - 1))
        gy = int(np.clip(gy, 0, n - 1))
        if layer.terrain[gx, gy] == cfg.TERRAIN_EMPTY:
            return False
        layer.terrain[gx, gy] = cfg.TERRAIN_EMPTY
        layer.terrain_version += 1
        return True

    def dig_disk(self, depth, cx, cy, radius):
        """Đào NGUYÊN 1 vùng tròn NGAY LẬP TỨC - CHỈ dùng cho các bước
        đào "tự động"/tường thuật (hốc lập tổ ban đầu của chúa, chúa tự mở
        rộng Phòng chúa lúc lập tổ xong, trục giếng cố định, tổ KHÔNG mô
        phỏng lập tổ thật) - KHÔNG dùng cho quá trình đào tăng dần bình
        thường (đó là việc của digger ants, xem dig_cell())."""
        layer = self.dirt_layers.get(depth)
        if layer is None or radius <= 0:
            return
        n = cfg.GRID_SIZE
        x0, x1 = max(0, int(cx - radius)), min(n, int(cx + radius) + 1)
        y0, y1 = max(0, int(cy - radius)), min(n, int(cy + radius) + 1)
        if x0 >= x1 or y0 >= y1:
            return
        xs, ys = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1), indexing="ij")
        mask = (xs - cx) ** 2 + (ys - cy) ** 2 <= radius ** 2
        region = layer.terrain[x0:x1, y0:y1]
        if np.any(mask & (region == cfg.TERRAIN_ROCK)):
            region[mask] = cfg.TERRAIN_EMPTY
            layer.terrain_version += 1

    def dug_fraction(self, depth, cx, cy, radius):
        """Tỉ lệ (0..1) diện tích hình tròn (cx,cy,radius) ở tầng `depth`
        ĐÃ được đào - dùng để biết 1 phòng đã "đủ đào" tới đâu (gate mở
        khóa phòng mới + thu hẹp bán kính THẬT của phòng đang lớn dần,
        xem try_finish_unlock()/update_room_sizes()).

        CÓ CACHE theo `terrain_version` của tầng đó: đất tại 1 tầng chỉ
        thực sự đổi khi có ô nào đó được đào xong (xem dig_cell/dig_disk,
        hiếm hơn NHIỀU so với tần suất hàm này bị gọi - mỗi khung hình từ
        check_alerts()/_check_room_unlocks()) - nên gần như luôn trúng
        cache, tránh phải tính lại toàn bộ mặt nạ hình tròn (meshgrid) mỗi
        khung hình cho những phòng đang chờ đào lâu ngày. Kết quả TRẢ VỀ
        giống hệt không có cache (chỉ nhanh hơn), không đổi hành vi gì."""
        layer = self.dirt_layers.get(depth)
        if layer is None or radius <= 0:
            return 1.0
        key = (depth, round(float(cx), 3), round(float(cy), 3), round(float(radius), 3))
        cached = self._dug_fraction_cache.get(key)
        if cached is not None and cached[0] == layer.terrain_version:
            return cached[1]
        n = cfg.GRID_SIZE
        x0, x1 = max(0, int(cx - radius)), min(n, int(cx + radius) + 1)
        y0, y1 = max(0, int(cy - radius)), min(n, int(cy + radius) + 1)
        if x0 >= x1 or y0 >= y1:
            return 1.0
        xs, ys = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1), indexing="ij")
        mask = (xs - cx) ** 2 + (ys - cy) ** 2 <= radius ** 2
        total = int(mask.sum())
        if total == 0:
            return 1.0
        dug = int(np.sum((layer.terrain[x0:x1, y0:y1] == cfg.TERRAIN_EMPTY) & mask))
        frac = dug / total
        self._dug_fraction_cache[key] = (layer.terrain_version, frac)
        return frac

    def find_frontier_cell(self, depth, cx, cy, radius, reserved=None):
        """Tìm 1 ô đất đặc GẦN TÂM (cx,cy) NHẤT mà có ÍT NHẤT 1 ô liền kề
        (4 hướng) ĐÃ ĐƯỢC ĐÀO - tức 1 ô "ở rìa" hợp lệ để đào tiếp (đảm bảo
        luôn đào LAN RA từ vùng đã có, không bao giờ tạo ra 1 hốc rời rạc
        giữa đất đặc không ai tới được).

        CỐ Ý quét TOÀN BỘ lưới của tầng này (không giới hạn trong vùng
        tròn radius quanh tâm phòng) - phòng thường nằm CÁCH XA trục giếng
        hàng chục ô, nên muốn đào TỚI được phòng, trước tiên phải đào
        XUYÊN 1 đường hầm nối từ mạng lưới đã đào (giếng/phòng khác) sang
        tới đó; giới hạn tìm kiếm trong vùng tròn phòng sẽ không bao giờ
        thấy rìa nào cả vì chưa có gì đào tới đó. Ưu tiên GẦN TÂM PHÒNG
        NHẤT khiến hướng đào tự nhiên "nhắm thẳng" về phía phòng (như đào
        đường hầm), rồi lấp dần bên trong khi đã tới nơi - việc DỪNG đào
        đúng lúc (không đào lan ra vô tận) do get_active_dig_jobs() tự
        loại phòng này khỏi danh sách việc cần làm ngay khi dug_fraction
        trong vùng tròn phòng đã đạt 100%, bất kể lưới CÒN đất đặc ở xa.
        Lưới chỉ 40x40 nên quét toàn bộ vẫn rất rẻ, không cần tối ưu thêm.
        Trả về None nếu KHÔNG còn ô đất đặc nào có thể đào tới được nữa
        (toàn bộ tầng đã đào hết, hiếm khi xảy ra)."""
        layer = self.dirt_layers.get(depth)
        if layer is None:
            return None
        terrain = layer.terrain
        solid = terrain == cfg.TERRAIN_ROCK
        dug = ~solid
        neighbor_dug = np.zeros_like(dug)
        neighbor_dug[1:, :] |= dug[:-1, :]
        neighbor_dug[:-1, :] |= dug[1:, :]
        neighbor_dug[:, 1:] |= dug[:, :-1]
        neighbor_dug[:, :-1] |= dug[:, 1:]
        frontier = solid & neighbor_dug
        if reserved:
            for (rd, rx, ry) in reserved:
                if rd == depth and 0 <= rx < frontier.shape[0] and 0 <= ry < frontier.shape[1]:
                    frontier[rx, ry] = False
        gx, gy = np.where(frontier)
        if len(gx) == 0:
            return None
        d2 = (gx - cx) ** 2 + (gy - cy) ** 2
        best = int(np.argmin(d2))
        return int(gx[best]), int(gy[best])

    def dug_neighbor_of(self, depth, gx, gy):
        """1 ô liền kề (4 hướng) ĐÃ ĐÀO của (gx,gy) - nơi kiến đào cần
        ĐỨNG để với tới đào (gx,gy) (bản thân ô đang đào thì chưa đi vào
        được). None nếu (hiếm) không có ô liền kề nào đã đào (dữ liệu
        không nhất quán - nơi gọi tự có phương án dự phòng)."""
        layer = self.dirt_layers.get(depth)
        if layer is None:
            return None
        n = cfg.GRID_SIZE
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = gx + dx, gy + dy
            if 0 <= nx < n and 0 <= ny < n and layer.terrain[nx, ny] == cfg.TERRAIN_EMPTY:
                return nx, ny
        return None

    def get_dig_pathfinder(self, depth):
        """VisibilityPathfinder (pathfinding.py) riêng cho tầng `depth`,
        tạo lười biếng lần đầu cần tới rồi cache lại - TỰ ĐỘNG dựng lại
        visibility graph mỗi khi self.dirt_layers[depth].terrain_version
        đổi (đúng cơ chế sẵn có của VisibilityPathfinder, không cần code
        gì thêm ở đây)."""
        pf = self.dig_pathfinders.get(depth)
        if pf is None:
            pf = pathfinding.VisibilityPathfinder(self.dirt_layers[depth])
            self.dig_pathfinders[depth] = pf
        return pf

    def get_active_dig_jobs(self):
        """Danh sách (room_id, depth, cx, cy, target_radius) các phòng
        ĐANG CẦN đào thêm lúc này - ưu tiên phòng MỚI đang chờ trong
        dig_queue (đào tới vị trí THẬT của nó để kịp mở khóa) trước, rồi
        mới tới các phòng ĐÃ mở đang cần MỞ RỘNG thêm theo dân số
        (ROOM_GROWABLE_IDS, xem update_room_sizes()).

        Tổ KHÔNG mô phỏng lập tổ thật (progressive=False, vd đối thủ)
        không dùng hệ thống đào này (đã đào sẵn đủ dùng từ đầu, không có
        digger ants nào) nên luôn trả về danh sách rỗng."""
        if not self.progressive:
            return []
        jobs = []
        for room_id in sorted(self.dig_queue):
            off_xy, depth = self._real_offsets[room_id]
            cx = self.nest_pos[0] + off_xy[0]
            cy = self.nest_pos[1] + off_xy[1]
            radius = self._base_radius[room_id]
            if self.dug_fraction(depth, cx, cy, radius) < 1.0:
                jobs.append((room_id, depth, float(cx), float(cy), float(radius)))
        for room in self.rooms:
            room_id = room[0]
            if room_id not in cfg.ROOM_GROWABLE_IDS or room_id not in self.unlocked_rooms:
                continue
            target = self._target_radius.get(room_id)
            if target is None:
                continue
            cx, cy = float(room[2][0]), float(room[2][1])
            depth = room[5]
            if self.dug_fraction(depth, cx, cy, target) < 1.0:
                jobs.append((room_id, depth, cx, cy, float(target)))
        return jobs

    def update_room_sizes(self, population):
        """Cập nhật bán kính CÁC PHÒNG GẮN LIỀN QUY MÔ ĐÀN (xem
        ROOM_GROWABLE_IDS trong config.py) theo dân số hiện tại - gọi mỗi
        tick từ AntColony.update(). Phòng KHÔNG nằm trong danh sách này
        giữ nguyên bán kính gốc, không đổi gì.

        `room[3]` (bán kính THẬT, mọi hành vi kiến khác đọc trực tiếp giá
        trị này) giờ CHỈ lớn theo đúng tỉ lệ đất ĐÃ ĐƯỢC ĐÀO THẬT trong
        vùng mục tiêu (self._target_radius[room_id], xem
        get_active_dig_jobs()/dug_fraction()) - dân số tăng chỉ đặt ra
        "mục tiêu mới cần đào tới", KHÔNG tự động phình to ngay, phải chờ
        digger ants đào xong (xem ants.py JOB_DIGGER) mới thực sự dùng
        được không gian đó. AN TOÀN GỌI LẶP LẠI: tính lại từ `_base_radius`
        gốc mỗi lần, không cộng dồn."""
        growth = cfg.ROOM_GROWTH_PER_SQRT_ANT * math.sqrt(max(0, population))
        for room in self.rooms:
            room_id = room[0]
            if room_id not in cfg.ROOM_GROWABLE_IDS:
                continue
            target = self._base_radius[room_id] + growth
            self._target_radius[room_id] = target
            if not self.progressive:
                # Tổ KHÔNG mô phỏng lập tổ thật (vd đối thủ) - GIỮ NGUYÊN
                # hành vi cũ: bán kính lớn NGAY theo dân số, không cần chờ
                # đào (đã đào sẵn dư ngay từ đầu ở __init__, không có
                # digger ants nào phụ trách tổ này).
                room[3] = target
                continue
            if room_id not in self.unlocked_rooms:
                continue  # chưa mở thật - chưa có gì để "lớn dần", room[3] giữ nguyên (đọc từ hốc gộp chung)
            cx, cy = float(room[2][0]), float(room[2][1])
            depth = room[5]
            frac = self.dug_fraction(depth, cx, cy, target)
            room[3] = self._base_radius[room_id] + growth * frac

    def room_center_and_radius(self, depth):
        """Tra tâm + bán kính phòng ở 1 tầng cho trước - dùng cho trường
        hợp CHỈ 1 phòng duy nhất ở tầng đó (vd phòng gác cửa). LƯU Ý: từ
        khi nhiều phòng dùng chung 1 tầng (kho+nước, trứng+ấu trùng), hàm
        này sẽ trả về phòng ĐẦU TIÊN khớp tầng - nếu tầng có thể có NHIỀU
        phòng, dùng room_center_and_radius_by_id thay vì hàm này để tránh
        nhầm phòng."""
        for room in self.rooms:
            if room[5] == depth:
                return room[2], room[3]
        return None, None

    def room_center_and_radius_by_id(self, room_id, founding_phase=False):
        """Tra tâm + bán kính phòng theo ĐÚNG room_id cụ thể (0=kho,
        1=ấu trùng, 2=chúa, 3=nước, 4=trứng, 5=gác cửa, 6=nghĩa địa) -
        dùng khi tầng có thể chứa NHIỀU phòng, để không bị nhầm phòng.

        `founding_phase`: khi True VÀ room_id=2 (Phòng chúa), trả về bán
        kính HỐC LẬP TỔ nhỏ hơn hẳn (cfg.ROOM_RADIUS_FOUNDING_CHAMBER)
        thay vì bán kính phòng chúa TRƯỞNG THÀNH đầy đủ - để kiến lượn
        trong phòng (_update_dwelling_ants) KHÔNG BAO GIỜ lượn ra ngoài
        hốc bé tí đang vẽ (nếu không thì tái diễn đúng lỗi "icon tràn ra
        ngoài phòng" từng gặp - xem lịch sử sửa lỗi carry-morsel/queen).
        Không mirror founding_phase làm state riêng trên UndergroundWorld
        để tránh lệch đồng bộ - luôn nhận từ AntColony (nơi giữ state gốc)
        qua tham số này."""
        for room in self.rooms:
            if room[0] == room_id:
                if room_id != 2 and room_id not in self.unlocked_rooms:
                    # CHƯA được đào riêng - đang "gộp chung" vào Phòng
                    # chúa (cùng VỊ TRÍ với nó) - phải dùng ĐÚNG bán kính
                    # HIỆN TẠI của Phòng chúa (không phải bán kính GỐC của
                    # chính room_id này - sẽ sai vì nó không ở vị trí
                    # riêng của mình), nếu không kiến lượn trong phòng sẽ
                    # tràn ra ngoài vòng tròn đang vẽ.
                    queen_room = next(r for r in self.rooms if r[0] == 2)
                    radius = cfg.ROOM_RADIUS_FOUNDING_CHAMBER if founding_phase else queen_room[3]
                    return room[2], radius
                radius = room[3]
                if room_id == 2 and founding_phase:
                    radius = cfg.ROOM_RADIUS_FOUNDING_CHAMBER
                return room[2], radius
        return None, None

    def add_corpse(self, count=1):
        """1 (hoặc nhiều) con kiến vừa chết - thêm xác vào nghĩa địa (giới
        hạn trần để không hiển thị rợp hình khi tổ chết chóc nhiều)."""
        self.corpse_count = min(cfg.GRAVEYARD_MAX_CORPSES, self.corpse_count + count)

    def register_corpse(self, x, y, depth):
        """1 kiến vừa chết DƯỚI HẦM tại (x, y, depth) - xếp vào hàng chờ
        để 1 nurse rảnh việc tự đi khiêng tới nghĩa địa (xem
        AntColony._update_undertakers() trong ants.py), KHÔNG cộng ngay
        vào corpse_count (khác add_corpse() ở trên, dùng cho xác chết TRÊN
        MẶT ĐẤT - không ai thu hồi được).

        Nếu hàng chờ đã đầy (MAX_PENDING_CORPSES - trường hợp hiếm, chết
        quá nhanh so với tốc độ khiêng), xác dư ra coi như bị bỏ lại,
        cộng thẳng vào nghĩa địa qua add_corpse() thay vì xếp hàng vô hạn."""
        if len(self.pending_corpses) < cfg.MAX_PENDING_CORPSES:
            self.pending_corpses.append([float(x), float(y), int(depth)])
        else:
            self.add_corpse(1)

    def claim_next_pending_corpse(self):
        """Lấy ra (và XÓA khỏi hàng chờ) xác CŨ NHẤT đang chờ - dùng khi 1
        nurse vừa được phân công đi khiêng, đảm bảo không có 2 nurse cùng
        lao tới khiêng CHUNG 1 xác. Trả về None nếu hàng chờ đang rỗng."""
        if not self.pending_corpses:
            return None
        return self.pending_corpses.pop(0)

    def decay_graveyard(self):
        """Xác cũ dần phân hủy/biến mất theo thời gian, gọi mỗi tick."""
        self.corpse_count = max(0.0, self.corpse_count - cfg.GRAVEYARD_DECAY_PER_TICK)

    def max_depth(self):
        """Tầng sâu nhất hiện có THẬT SỰ (chỉ tính phòng ĐÃ ĐƯỢC ĐÀO
        RIÊNG - xem unlocked_rooms) - để giới hạn phạm vi cuộn Ctrl+Scroll
        đúng với thực tế ván đang chơi, không cho cuộn xuống những tầng
        chưa hề tồn tại."""
        depths = [r[5] for r in self.rooms if r[0] in self.unlocked_rooms]
        return max(depths, default=0)

    def deposit_to_storage(self, amount):
        self.food_in_storage += float(amount)

    def deposit_water(self, amount):
        self.water_in_storage += float(amount)

    def deposit_to_nursery(self, count):
        self.food_in_nursery += int(count)
        self.food_in_storage = max(0, self.food_in_storage - int(count))

    def update_starvation_tracker(self, population=0):
        """Gọi mỗi tick (kèm sĩ số đàn HIỆN TẠI): theo dõi xem TOÀN BỘ
        nguồn thức ăn (cả kho lẫn phòng ấu trùng) và nguồn nước có đang cạn
        kiệt kéo dài không - dùng để tính nguy cơ chết đói/chết khát cho cả
        đàn."""
        if self.food_in_nursery <= 0 and self.food_in_storage <= 0:
            self.ticks_nursery_empty += 1
        else:
            self.ticks_nursery_empty = 0

        if self.water_in_storage <= 0:
            self.ticks_water_empty += 1
        else:
            self.ticks_water_empty = 0

    def consume_upkeep(self, population):
        """Mỗi kiến còn sống tiêu hao 1 lượng nhỏ thức ăn VÀ nước từ kho
        mỗi tick để duy trì sự sống - khiến tài nguyên thực sự có thể cạn
        nếu đàn quá đông so với khả năng kiếm ăn/lấy nước. (Thức ăn trong
        phòng ấu trùng được TIÊU THỤ RIÊNG bởi từng ấu trùng đang lớn - xem
        AntColony._update_larvae() ở ants.py - nên không xử lý ở đây.)"""
        food_cost = population * cfg.UPKEEP_FOOD_PER_ANT_PER_TICK
        water_cost = population * cfg.WATER_UPKEEP_PER_ANT_PER_TICK
        self.food_in_storage = max(0.0, self.food_in_storage - food_cost)
        self.water_in_storage = max(0.0, self.water_in_storage - water_cost)

    def is_starving(self):
        return self.ticks_nursery_empty > cfg.STARVATION_GRACE_TICKS

    def is_dehydrated(self):
        return self.ticks_water_empty > cfg.WATER_STARVATION_GRACE_TICKS

    def try_consume_for_egg(self, food_cost, water_cost):
        """Trừ thức ăn VÀ nước trong kho để chúa đẻ 1 trứng mới. Trả về
        True nếu đủ CẢ HAI (tài nguyên có hạn -> không phải lúc nào cũng đẻ
        được, thiếu nước cũng chặn y như thiếu thức ăn)."""
        if self.food_in_storage >= food_cost and self.water_in_storage >= water_cost:
            self.food_in_storage -= food_cost
            self.water_in_storage -= water_cost
            return True
        return False
