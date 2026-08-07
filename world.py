"""Định nghĩa lớp mặt đất (surface) và lớp hầm ngầm (underground)."""
import numpy as np
import config as cfg


class SurfaceWorld:
    """Lưới mặt đất: thức ăn + pheromone dẫn đường về tổ."""

    def __init__(self):
        n = cfg.GRID_SIZE
        self.food = np.zeros((n, n), dtype=np.float32)
        self.food_type = np.zeros((n, n), dtype=np.int8)  # loại thức ăn tại mỗi ô
        self.pheromone = np.zeros((n, n), dtype=np.float32)
        self.terrain = np.zeros((n, n), dtype=np.int8)  # 0=đất, 1=đá, 2=nước
        self.terrain_features = []  # [(loại, cx, cy, radius), ...] để vẽ 3D
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
        nest_x, nest_y = cfg.NEST_POS

        def random_far_from_nest():
            for _ in range(30):  # thử tối đa 30 lần để tránh quá gần tổ
                cx = rng.integers(3, n - 3)
                cy = rng.integers(3, n - 3)
                if np.hypot(cx - nest_x, cy - nest_y) > cfg.TERRAIN_SAFE_RADIUS_FROM_NEST:
                    return int(cx), int(cy)
            return int(cx), int(cy)  # đành chấp nhận lần thử cuối nếu quá xui

        for _ in range(cfg.NUM_ROCK_CLUSTERS):
            cx, cy = random_far_from_nest()
            self.add_obstacle(cx, cy, cfg.TERRAIN_ROCK, cfg.ROCK_CLUSTER_RADIUS)

        for _ in range(cfg.NUM_WATER_CLUSTERS):
            cx, cy = random_far_from_nest()
            self.add_obstacle(cx, cy, cfg.TERRAIN_WATER, cfg.WATER_CLUSTER_RADIUS)

    def add_obstacle(self, cx, cy, terrain_type, radius):
        """Đánh dấu 1 vùng địa hình (đá/nước) trên lưới - dùng cả lúc khởi
        tạo lẫn khi người chơi tự đặt bằng công cụ. Trả về feature để
        main.py vẽ thêm lên màn hình 3D."""
        n = cfg.GRID_SIZE
        r = int(round(radius))
        x0, x1 = max(0, cx - r), min(n, cx + r + 1)
        y0, y1 = max(0, cy - r), min(n, cy + r + 1)
        # Vùng tròn thay vì vuông, cho tự nhiên hơn
        xs, ys = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1), indexing="ij")
        mask = (xs - cx) ** 2 + (ys - cy) ** 2 <= r ** 2
        self.terrain[xs[mask], ys[mask]] = terrain_type
        # Xóa thức ăn nếu lỡ trùng vị trí (không cho thức ăn mọc trong đá/nước)
        self.food[xs[mask], ys[mask]] = 0
        feature = (terrain_type, int(cx), int(cy), float(radius))
        self.terrain_features.append(feature)
        return feature

    def is_blocked(self, xi, yi):
        """Trả về mảng bool: ô nào đang là chướng ngại vật (đá/nước)."""
        return self.terrain[xi, yi] != cfg.TERRAIN_EMPTY

    def has_water_source(self):
        """Còn ít nhất 1 ô nước nào trên bản đồ không - nếu bạn lấp hết
        nước bằng đá, tổ sẽ mất hẳn nguồn thu nước."""
        return bool(np.any(self.terrain == cfg.TERRAIN_WATER))

    def decay_pheromone(self):
        self.pheromone *= cfg.PHEROMONE_DECAY

    def deposit_pheromone(self, xi, yi):
        """xi, yi: mảng chỉ số nguyên (đã clip trong biên)."""
        np.add.at(self.pheromone, (xi, yi), cfg.PHEROMONE_DEPOSIT)
        np.clip(self.pheromone, 0, cfg.PHEROMONE_MAX, out=self.pheromone)

    def sample_pheromone(self, xi, yi):
        return self.pheromone[xi, yi]

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
        ăn xuất hiện theo mùa, KHÔNG vô hạn/tức thời như lúc khởi tạo."""
        n = cfg.GRID_SIZE
        rng = np.random.default_rng()
        cx = rng.integers(4, n - 4)
        cy = rng.integers(4, n - 4)
        r = cfg.FOOD_CLUSTER_RADIUS
        x0, x1 = max(0, cx - r), min(n, cx + r + 1)
        y0, y1 = max(0, cy - r), min(n, cy + r + 1)
        self.food[x0:x1, y0:y1] += cfg.FOOD_RESPAWN_AMOUNT
        self.food_type[x0:x1, y0:y1] = self._random_food_type(rng)
        return (int(cx), int(cy))


class UndergroundWorld:
    """Cấu trúc tổ dưới lòng đất (3D): giếng + các phòng nối bằng hành lang.

    Mọi tọa độ ở đây là (x, y, z) với z là độ sâu (0 = mặt đất, âm = sâu hơn).
    """

    def __init__(self):
        shaft_x, shaft_y = cfg.NEST_POS
        self.shaft = np.array([shaft_x, shaft_y, cfg.SHAFT_TOP_Z], dtype=np.float32)
        self.storage = np.array(cfg.ROOM_STORAGE, dtype=np.float32)
        self.nursery = np.array(cfg.ROOM_NURSERY, dtype=np.float32)
        self.queen_room = np.array(cfg.ROOM_QUEEN, dtype=np.float32)

        # Danh sách phòng để vẽ (tên, tâm, bán kính, màu gợi ý)
        self.rooms = [
            ("Kho thức ăn", self.storage, cfg.ROOM_RADIUS, (170, 130, 70)),
            ("Ấu trùng", self.nursery, cfg.ROOM_RADIUS, (200, 190, 120)),
            ("Phòng chúa", self.queen_room, cfg.ROOM_RADIUS * 1.1, (180, 90, 140)),
        ]
        # Hành lang nối giếng <-> từng phòng, và kho <-> phòng chúa
        self.corridors = [
            (self.shaft, self.storage),
            (self.shaft, self.nursery),
            (self.storage, self.queen_room),
        ]

        # Thống kê tổ
        self.food_in_storage = 0
        self.food_in_nursery = 0
        self.water_in_storage = 0.0
        self.ticks_nursery_empty = 0   # số tick liên tiếp phòng ấu trùng rỗng
        self.ticks_water_empty = 0     # số tick liên tiếp hết nước dự trữ
        self.total_births = 0
        self.total_deaths = 0

    def deposit_to_storage(self, amount):
        self.food_in_storage += float(amount)

    def deposit_water(self, amount):
        self.water_in_storage += float(amount)

    def deposit_to_nursery(self, count):
        self.food_in_nursery += int(count)
        self.food_in_storage = max(0, self.food_in_storage - int(count))

    def update_starvation_tracker(self):
        """Gọi mỗi tick: theo dõi xem TOÀN BỘ nguồn thức ăn (cả kho lẫn
        phòng ấu trùng) và nguồn nước có đang cạn kiệt kéo dài không - dùng
        để tính nguy cơ chết đói/chết khát cho cả đàn."""
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
        nếu đàn quá đông so với khả năng kiếm ăn/lấy nước."""
        food_cost = population * cfg.UPKEEP_FOOD_PER_ANT_PER_TICK
        water_cost = population * cfg.WATER_UPKEEP_PER_ANT_PER_TICK
        self.food_in_storage = max(0.0, self.food_in_storage - food_cost)
        self.water_in_storage = max(0.0, self.water_in_storage - water_cost)
        # Ấu trùng tiêu thụ dần thức ăn trong phòng để lớn lên - nếu không,
        # thức ăn ở đây sẽ tích lũy vĩnh viễn, dần rút cạn tài nguyên tổ
        self.food_in_nursery = max(0.0, self.food_in_nursery - cfg.NURSERY_CONSUMPTION_PER_TICK)

    def is_starving(self):
        return self.ticks_nursery_empty > cfg.STARVATION_GRACE_TICKS

    def is_dehydrated(self):
        return self.ticks_water_empty > cfg.WATER_STARVATION_GRACE_TICKS

    def try_consume_for_birth(self, food_cost, water_cost):
        """Trừ thức ăn VÀ nước trong kho để sinh 1 lứa kiến mới. Trả về
        True nếu đủ CẢ HAI (tài nguyên có hạn -> không phải lúc nào cũng
        sinh được, thiếu nước cũng chặn sinh sản y như thiếu thức ăn)."""
        if self.food_in_storage >= food_cost and self.water_in_storage >= water_cost:
            self.food_in_storage -= food_cost
            self.water_in_storage -= water_cost
            return True
        return False

    def dig_new_room(self, x, y):
        """Đào 1 phòng mới do người chơi chỉ định vị trí (x, y) trên mặt
        đất - độ sâu tự động tăng dần theo số phòng đã đào, nối hành lang
        tới phòng/giếng gần nhất. Trả về (name, center, radius, rgb) vừa
        tạo để main.py vẽ thêm lên màn hình 3D."""
        dug_count = len(self.rooms) - 3  # 3 phòng gốc: kho, ấu trùng, chúa
        depth = -6.0 - dug_count * 3.0
        depth = max(depth, -cfg.WORLD_DEPTH + 2.0)  # không đào vượt đáy khối kính
        center = np.array([x, y, depth], dtype=np.float32)

        # Nối tới phòng/giếng gần nhất (theo khoảng cách ngang x,y)
        candidates = [self.shaft] + [r[1] for r in self.rooms]
        dists = [np.hypot(c[0] - x, c[1] - y) for c in candidates]
        nearest = candidates[int(np.argmin(dists))]

        name = f"Phong dao #{dug_count + 1}"
        rgb = (140, 150, 175)
        radius = cfg.ROOM_RADIUS * 0.8
        self.rooms.append((name, center, radius, rgb))
        self.corridors.append((nearest, center))
        return name, center, radius, rgb
