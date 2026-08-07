"""Định nghĩa lớp mặt đất (surface) và lớp hầm ngầm (underground)."""
import numpy as np
import config as cfg


class SurfaceWorld:
    """Lưới mặt đất: thức ăn + pheromone dẫn đường về tổ."""

    def __init__(self, protected_nests=None):
        n = cfg.GRID_SIZE
        self.food = np.zeros((n, n), dtype=np.float32)
        self.food_type = np.zeros((n, n), dtype=np.int8)  # loại thức ăn tại mỗi ô
        self.pheromone = np.zeros((n, n), dtype=np.float32)
        self.danger_pheromone = np.zeros((n, n), dtype=np.float32)
        self.terrain = np.zeros((n, n), dtype=np.int8)  # 0=đất, 1=đá, 2=nước
        self.terrain_features = []  # [(id, loại, cx, cy, radius), ...] để vẽ 3D
        self._next_feature_id = 0
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

    def deposit_pheromone(self, xi, yi):
        """xi, yi: mảng chỉ số nguyên (đã clip trong biên)."""
        np.add.at(self.pheromone, (xi, yi), cfg.PHEROMONE_DEPOSIT)
        np.clip(self.pheromone, 0, cfg.PHEROMONE_MAX, out=self.pheromone)

    def sample_pheromone(self, xi, yi):
        return self.pheromone[xi, yi]

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
        return (int(cx), int(cy))


class UndergroundWorld:
    """Cấu trúc tổ dưới lòng đất: 1 chồng các TẦNG 2D phẳng rời rạc.

    Mỗi phòng nằm trên đúng 1 tầng (depth = số nguyên, 0 = mặt đất, càng lớn
    càng sâu). "Giếng" không còn là 1 điểm 3D riêng - nó CHÍNH LÀ vị trí lỗ
    tổ (nest_x, nest_y), hoạt động như 1 cái thang máy xuyên suốt mọi tầng:
    ở tầng nào bạn cũng thấy nó ở đúng (x, y) đó, nối tới phòng của tầng ấy
    bằng 1 đoạn hành lang phẳng trong CÙNG tầng (không có đường chéo cắt
    xuyên qua nhiều tầng như bản 3D cũ)."""

    def __init__(self, nest_pos=None, label_prefix=""):
        nest_pos = nest_pos if nest_pos else cfg.NEST_POS
        nest_x, nest_y = nest_pos
        self.nest_pos = nest_pos
        self.shaft_xy = np.array([nest_x, nest_y], dtype=np.float32)

        def offset(off_xy):
            return np.array([nest_x + off_xy[0], nest_y + off_xy[1]], dtype=np.float32)

        self.storage = offset(cfg.STORAGE_OFFSET_XY)
        self.nursery = offset(cfg.NURSERY_OFFSET_XY)
        self.queen_room = offset(cfg.QUEEN_OFFSET_XY)
        self.water_room = offset(cfg.WATER_OFFSET_XY)
        self.egg_room = offset(cfg.EGG_OFFSET_XY)
        self.guard_room = offset(cfg.GUARD_OFFSET_XY)
        self.graveyard = offset(cfg.GRAVEYARD_OFFSET_XY)
        self.pupa_room = offset(cfg.PUPA_OFFSET_XY)

        self.storage_depth = cfg.DEPTH_STORAGE
        self.nursery_depth = cfg.DEPTH_NURSERY
        self.queen_depth = cfg.DEPTH_QUEEN
        self.water_depth = cfg.DEPTH_WATER
        self.egg_depth = cfg.DEPTH_EGG
        self.guard_depth = cfg.DEPTH_GUARD
        self.graveyard_depth = cfg.DEPTH_GRAVEYARD
        self.pupa_depth = cfg.DEPTH_PUPA

        # Danh sách phòng để vẽ (id, tên, tâm(x,y), bán kính, màu gợi ý,
        # tầng) - LUÔN ĐÚNG 8 phòng GỐC/CHỨC NĂNG cố định, không đổi trong
        # suốt ván (không còn chức năng tự đào thêm phòng như bản trước).
        # Kích thước (bán kính) khác nhau theo đúng vai trò: kho/nước chứa
        # số lượng lớn nên to nhất, trứng/gác cửa/nghĩa địa/nhộng nhỏ hơn.
        self.rooms = [
            (0, f"{label_prefix}Kho thức ăn", self.storage, cfg.ROOM_RADIUS_STORAGE, (170, 130, 70), self.storage_depth),
            (1, f"{label_prefix}Ấu trùng", self.nursery, cfg.ROOM_RADIUS_NURSERY, (200, 190, 120), self.nursery_depth),
            (2, f"{label_prefix}Phòng chúa", self.queen_room, cfg.ROOM_RADIUS_QUEEN, (180, 90, 140), self.queen_depth),
            (3, f"{label_prefix}Bể trữ nước", self.water_room, cfg.ROOM_RADIUS_WATER, (70, 130, 190), self.water_depth),
            (4, f"{label_prefix}Phòng trứng", self.egg_room, cfg.ROOM_RADIUS_EGG, (235, 225, 200), self.egg_depth),
            (5, f"{label_prefix}Phòng gác cửa", self.guard_room, cfg.ROOM_RADIUS_GUARD, (120, 110, 100), self.guard_depth),
            (6, f"{label_prefix}Nghĩa địa", self.graveyard, cfg.ROOM_RADIUS_GRAVEYARD, (90, 80, 75), self.graveyard_depth),
            (7, f"{label_prefix}Phòng nhộng", self.pupa_room, cfg.ROOM_RADIUS_PUPA, (150, 130, 95), self.pupa_depth),
        ]

        # Thống kê tổ
        self.food_in_storage = 0
        self.food_in_nursery = 0
        self.water_in_storage = 0.0
        self.ticks_nursery_empty = 0   # số tick liên tiếp phòng ấu trùng rỗng
        self.ticks_water_empty = 0     # số tick liên tiếp hết nước dự trữ
        self.ticks_storage_low = 0     # số tick liên tiếp kho CHỈ CÒN ÍT
        self.total_births = 0
        self.total_deaths = 0
        self.total_food_looted = 0.0    # tổng thức ăn CƯỚP ĐƯỢC từ tổ đối
                                         # thủ qua các đợt xâm chiếm
        # Nghĩa địa: số "nắm xác" đang hiển thị (giảm dần theo thời gian -
        # xem GRAVEYARD_DECAY_PER_TICK - để không phình to vô hạn)
        self.corpse_count = 0.0

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

    def room_center_and_radius_by_id(self, room_id):
        """Tra tâm + bán kính phòng theo ĐÚNG room_id cụ thể (0=kho,
        1=ấu trùng, 2=chúa, 3=nước, 4=trứng, 5=gác cửa, 6=nghĩa địa) -
        dùng khi tầng có thể chứa NHIỀU phòng, để không bị nhầm phòng."""
        for room in self.rooms:
            if room[0] == room_id:
                return room[2], room[3]
        return None, None

    def add_corpse(self, count=1):
        """1 (hoặc nhiều) con kiến vừa chết - thêm xác vào nghĩa địa (giới
        hạn trần để không hiển thị rợp hình khi tổ chết chóc nhiều)."""
        self.corpse_count = min(cfg.GRAVEYARD_MAX_CORPSES, self.corpse_count + count)

    def decay_graveyard(self):
        """Xác cũ dần phân hủy/biến mất theo thời gian, gọi mỗi tick."""
        self.corpse_count = max(0.0, self.corpse_count - cfg.GRAVEYARD_DECAY_PER_TICK)

    def max_depth(self):
        """Tầng sâu nhất hiện có (để giới hạn phạm vi cuộn Ctrl+Scroll)."""
        return max((r[5] for r in self.rooms), default=cfg.DEPTH_GRAVEYARD)

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
        đàn. Đồng thời theo dõi RIÊNG việc kho CHỈ CÒN ÍT (chưa hẳn về 0)
        kéo dài - tín hiệu "khan hiếm" nhẹ hơn, dùng để cân nhắc phát động
        xâm chiếm tổ đối thủ (is_starving là khủng hoảng NẶNG hơn hẳn, ít
        khi xảy ra). Ngưỡng "ít" TỈ LỆ THEO DÂN SỐ (xem
        RAID_STORAGE_THRESHOLD_PER_ANT) thay vì 1 hằng số cố định, để tín
        hiệu khan hiếm vẫn có ý nghĩa dù đàn còn nhỏ hay đã lớn."""
        if self.food_in_nursery <= 0 and self.food_in_storage <= 0:
            self.ticks_nursery_empty += 1
        else:
            self.ticks_nursery_empty = 0

        if self.water_in_storage <= 0:
            self.ticks_water_empty += 1
        else:
            self.ticks_water_empty = 0

        scarce_threshold = max(
            cfg.RAID_STORAGE_THRESHOLD_MIN, population * cfg.RAID_STORAGE_THRESHOLD_PER_ANT
        )
        if self.food_in_storage < scarce_threshold:
            self.ticks_storage_low += 1
        else:
            self.ticks_storage_low = 0

    def is_food_scarce(self):
        """Kho CHỈ CÒN ÍT kéo dài đủ lâu - tín hiệu để cân nhắc xâm chiếm
        tổ đối thủ (không cần khủng hoảng nặng như is_starving)."""
        return self.ticks_storage_low > cfg.RAID_SCARCITY_GRACE_TICKS

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
