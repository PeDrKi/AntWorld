"""Quản lý toàn bộ đàn kiến bằng mảng NumPy (vectorized), tránh vòng lặp
Python từng con -- cần thiết để giữ khung hình mượt khi có nhiều kiến.

Bản 3D: mỗi con kiến có vị trí đầy đủ (x, y, z). Trên mặt đất z luôn bằng
SURFACE_Z (kiến đi trên 1 mặt phẳng). Khi xuống hầm, z thay đổi liên tục
theo đường thẳng 3D tới từng phòng - đây là điểm khác biệt chính so với
bản 2D (nơi "tầng" chỉ là 1 layer rời rạc)."""
import numpy as np
import config as cfg


class AntColony:
    def __init__(self, n_ants, surface, underground):
        self.n = n_ants
        self.surface = surface
        self.underground = underground
        rng = np.random.default_rng()

        nest_x, nest_y = cfg.NEST_POS
        # Vị trí ban đầu: rải quanh cửa tổ trên mặt đất
        self.x = nest_x + rng.normal(0, 2.0, n_ants).astype(np.float32)
        self.y = nest_y + rng.normal(0, 2.0, n_ants).astype(np.float32)
        self.z = np.full(n_ants, cfg.SURFACE_Z, dtype=np.float32)
        np.clip(self.x, 0, cfg.GRID_SIZE - 1, out=self.x)
        np.clip(self.y, 0, cfg.GRID_SIZE - 1, out=self.y)

        self.theta = rng.uniform(0, 2 * np.pi, n_ants).astype(np.float32)
        self.layer = np.zeros(n_ants, dtype=np.int8)          # 0 = mặt đất
        self.state = np.zeros(n_ants, dtype=np.int8)          # STATE_SEARCHING
        self.carrying = np.zeros(n_ants, dtype=bool)

        # Thống kê tích lũy
        self.total_food_collected = 0

    # ------------------------------------------------------------------
    def update(self):
        self._update_surface_ants()
        self._update_underground_ants()
        self.surface.decay_pheromone()

    # ------------------------------------------------------------------
    def _wrap_indices(self, arr):
        return np.clip(arr.astype(np.int32), 0, cfg.GRID_SIZE - 1)

    def _update_surface_ants(self):
        on_surface = self.layer == cfg.LAYER_SURFACE
        if not np.any(on_surface):
            return

        searching = on_surface & (self.state == cfg.STATE_SEARCHING)
        returning = on_surface & (self.state == cfg.STATE_RETURNING)

        # --- Kiến đang tìm ăn: dò pheromone 3 hướng rồi lệch theta ---
        if np.any(searching):
            idx = np.where(searching)[0]
            theta = self.theta[idx]
            x, y = self.x[idx], self.y[idx]

            def sense(offset):
                sx = x + np.cos(theta + offset) * cfg.SENSE_DIST
                sy = y + np.sin(theta + offset) * cfg.SENSE_DIST
                xi = self._wrap_indices(sx)
                yi = self._wrap_indices(sy)
                return self.surface.sample_pheromone(xi, yi)

            left = sense(-cfg.SENSE_ANGLE)
            center = sense(0.0)
            right = sense(cfg.SENSE_ANGLE)

            bias = np.zeros_like(theta)
            bias = np.where(left > center, bias - cfg.SENSE_ANGLE, bias)
            bias = np.where(right > np.maximum(left, center), bias + cfg.SENSE_ANGLE, bias)

            noise = np.random.uniform(-cfg.TURN_NOISE, cfg.TURN_NOISE, len(idx)).astype(np.float32)
            self.theta[idx] = theta + bias * 0.5 + noise

            self.x[idx] += np.cos(self.theta[idx]) * cfg.ANT_SPEED
            self.y[idx] += np.sin(self.theta[idx]) * cfg.ANT_SPEED
            self._bounce_walls(idx)

            # Kiểm tra ô có thức ăn không -> nhặt
            xi = self._wrap_indices(self.x[idx])
            yi = self._wrap_indices(self.y[idx])
            got_food = self.surface.take_food(xi, yi, amount=1.0)
            got_idx = idx[got_food]
            if len(got_idx) > 0:
                self.carrying[got_idx] = True
                self.state[got_idx] = cfg.STATE_RETURNING
                self.total_food_collected += len(got_idx)

        # --- Kiến đang tha thức ăn về tổ ---
        if np.any(returning):
            idx = np.where(returning)[0]
            x, y = self.x[idx], self.y[idx]
            nest_x, nest_y = cfg.NEST_POS
            to_nest_theta = np.arctan2(nest_y - y, nest_x - x)
            self.theta[idx] = 0.25 * self.theta[idx] + 0.75 * to_nest_theta

            self.x[idx] += np.cos(self.theta[idx]) * cfg.ANT_SPEED
            self.y[idx] += np.sin(self.theta[idx]) * cfg.ANT_SPEED
            self._bounce_walls(idx)

            xi = self._wrap_indices(self.x[idx])
            yi = self._wrap_indices(self.y[idx])
            self.surface.deposit_pheromone(xi, yi)

            dist = np.hypot(self.x[idx] - nest_x, self.y[idx] - nest_y)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                # Chui xuống giếng: bắt đầu hành trình 3D xuống hầm
                self.layer[arrived] = cfg.LAYER_UNDERGROUND
                self.x[arrived] = self.underground.shaft[0]
                self.y[arrived] = self.underground.shaft[1]
                self.z[arrived] = cfg.SHAFT_TOP_Z
                self.state[arrived] = cfg.STATE_UG_TO_STORAGE

    def _bounce_walls(self, idx):
        n = cfg.GRID_SIZE - 1
        x, y = self.x[idx], self.y[idx]
        hit_x = (x < 0) | (x > n)
        hit_y = (y < 0) | (y > n)
        self.theta[idx[hit_x]] = np.pi - self.theta[idx[hit_x]]
        self.theta[idx[hit_y]] = -self.theta[idx[hit_y]]
        np.clip(self.x, 0, n, out=self.x)
        np.clip(self.y, 0, n, out=self.y)

    # ------------------------------------------------------------------
    def _move_towards_3d(self, idx, target_xyz, speed):
        """Di chuyển theo đường thẳng 3D tới đích. Trả về khoảng cách còn lại."""
        x, y, z = self.x[idx], self.y[idx], self.z[idx]
        tx, ty, tz = target_xyz
        dx, dy, dz = tx - x, ty - y, tz - z
        dist = np.sqrt(dx * dx + dy * dy + dz * dz)
        safe_dist = np.where(dist < 1e-6, 1.0, dist)  # tránh chia 0
        step = np.minimum(speed, dist)  # không đi vượt quá đích trong 1 tick
        self.x[idx] = x + dx / safe_dist * step
        self.y[idx] = y + dy / safe_dist * step
        self.z[idx] = z + dz / safe_dist * step
        # cập nhật góc quay (theta) chỉ theo mặt phẳng ngang, để nếu kiến
        # trồi lên mặt đất thì hướng nhìn vẫn hợp lý
        self.theta[idx] = np.arctan2(dy, dx)
        return dist

    def _update_underground_ants(self):
        ug = self.layer == cfg.LAYER_UNDERGROUND
        if not np.any(ug):
            return

        # --- đi tới kho ---
        mask = ug & (self.state == cfg.STATE_UG_TO_STORAGE)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_3d(idx, self.underground.storage, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                self.underground.deposit_to_storage(len(arrived))
                self.carrying[arrived] = False
                rng_vals = np.random.uniform(0, 1, len(arrived))
                become_nurse = arrived[rng_vals < cfg.NURSE_PROBABILITY]
                go_back = arrived[rng_vals >= cfg.NURSE_PROBABILITY]
                self.state[become_nurse] = cfg.STATE_UG_TO_NURSERY
                self.carrying[become_nurse] = True
                self.state[go_back] = cfg.STATE_UG_TO_SHAFT

        # --- nurse mang đồ tới phòng ấu trùng ---
        mask = ug & (self.state == cfg.STATE_UG_TO_NURSERY)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_3d(idx, self.underground.nursery, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                self.underground.deposit_to_nursery(len(arrived))
                self.carrying[arrived] = False
                self.state[arrived] = cfg.STATE_UG_TO_SHAFT

        # --- quay lại giếng để lên mặt đất ---
        mask = ug & (self.state == cfg.STATE_UG_TO_SHAFT)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_3d(idx, self.underground.shaft, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                self.layer[arrived] = cfg.LAYER_SURFACE
                self.x[arrived] = cfg.NEST_POS[0]
                self.y[arrived] = cfg.NEST_POS[1]
                self.z[arrived] = cfg.SURFACE_Z
                self.state[arrived] = cfg.STATE_SEARCHING
                self.theta[arrived] = np.random.uniform(0, 2 * np.pi, len(arrived))

    # ------------------------------------------------------------------
    def counts(self):
        """Trả về dict thống kê nhanh cho bảng UI."""
        return {
            "searching": int(np.sum((self.layer == 0) & (self.state == cfg.STATE_SEARCHING))),
            "returning": int(np.sum((self.layer == 0) & (self.state == cfg.STATE_RETURNING))),
            "underground": int(np.sum(self.layer == 1)),
            "total_food_collected": self.total_food_collected,
            "food_in_storage": self.underground.food_in_storage,
            "food_in_nursery": self.underground.food_in_nursery,
        }
