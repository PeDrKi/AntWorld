"""Định nghĩa lớp mặt đất (surface) và lớp hầm ngầm (underground)."""
import numpy as np
import config as cfg


class SurfaceWorld:
    """Lưới mặt đất: thức ăn + pheromone dẫn đường về tổ."""

    def __init__(self):
        n = cfg.GRID_SIZE
        self.food = np.zeros((n, n), dtype=np.float32)
        self.pheromone = np.zeros((n, n), dtype=np.float32)
        self._spawn_food_clusters()

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

    def decay_pheromone(self):
        self.pheromone *= cfg.PHEROMONE_DECAY

    def deposit_pheromone(self, xi, yi):
        """xi, yi: mảng chỉ số nguyên (đã clip trong biên)."""
        np.add.at(self.pheromone, (xi, yi), cfg.PHEROMONE_DEPOSIT)
        np.clip(self.pheromone, 0, cfg.PHEROMONE_MAX, out=self.pheromone)

    def sample_pheromone(self, xi, yi):
        return self.pheromone[xi, yi]

    def take_food(self, xi, yi, amount=1.0):
        """Trừ thức ăn tại các ô, trả về mảng bool nơi thực sự lấy được."""
        available = self.food[xi, yi] > 0.01
        self.food[xi[available], yi[available]] -= amount
        np.clip(self.food, 0, None, out=self.food)
        return available


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

    def deposit_to_storage(self, count):
        self.food_in_storage += int(count)

    def deposit_to_nursery(self, count):
        self.food_in_nursery += int(count)
        self.food_in_storage = max(0, self.food_in_storage - int(count))
