"""Kẻ thù tự nhiên: xuất hiện ngẫu nhiên trên mặt đất theo chu kỳ, di
chuyển về phía những nơi có nhiều kiến, và có xác suất giết kiến trong
tầm gần mỗi tick. Sau 1 khoảng thời gian sẽ tự rời đi (mô phỏng 1 lần
"đột kích" của thiên địch, không phải mối đe dọa thường trực)."""
import numpy as np
import config as cfg


class EnemyManager:
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.life_left = 0
        self.spawn_cooldown = np.random.randint(
            cfg.ENEMY_SPAWN_COOLDOWN_MIN, cfg.ENEMY_SPAWN_COOLDOWN_MAX
        )
        self.total_kills = 0
        self.kills_this_visit = 0

    def update(self, colony):
        if not self.active:
            self.spawn_cooldown -= 1
            if self.spawn_cooldown <= 0:
                self._spawn()
            return

        self.life_left -= 1
        if self.life_left <= 0:
            self._despawn()
            return

        self._move_towards_prey(colony)
        self._try_kill(colony)

    # ------------------------------------------------------------------
    def _spawn(self):
        self.active = True
        self.x = float(np.random.uniform(4, cfg.GRID_SIZE - 4))
        self.y = float(np.random.uniform(4, cfg.GRID_SIZE - 4))
        self.theta = float(np.random.uniform(0, 2 * np.pi))
        self.life_left = cfg.ENEMY_LIFETIME_TICKS
        self.kills_this_visit = 0

    def force_spawn_at(self, x, y):
        """Người chơi chủ động thả kẻ thù tại vị trí (x, y) chỉ định -
        dùng cho công cụ can thiệp bằng chuột."""
        self.active = True
        self.x = float(x)
        self.y = float(y)
        self.theta = float(np.random.uniform(0, 2 * np.pi))
        self.life_left = cfg.ENEMY_LIFETIME_TICKS
        self.kills_this_visit = 0

    def _despawn(self):
        self.active = False
        self.spawn_cooldown = np.random.randint(
            cfg.ENEMY_SPAWN_COOLDOWN_MIN, cfg.ENEMY_SPAWN_COOLDOWN_MAX
        )

    def _move_towards_prey(self, colony):
        # Tìm kiến còn sống trên mặt đất trong bán kính "nhìn thấy" để đuổi
        # theo; nếu không có con nào gần, đi lang thang ngẫu nhiên (không
        # phải thợ săn toàn năng biết vị trí mọi con kiến trên bản đồ).
        on_surface = colony.alive & (colony.layer == cfg.LAYER_SURFACE)
        found_target = False
        if np.any(on_surface):
            dx = colony.x[on_surface] - self.x
            dy = colony.y[on_surface] - self.y
            dist2 = dx * dx + dy * dy
            nearest = np.argmin(dist2)
            if dist2[nearest] < cfg.ENEMY_DETECT_RADIUS ** 2:
                target_theta = np.arctan2(dy[nearest], dx[nearest])
                # trộn nhẹ để chuyển hướng mượt, không "dính" tuyệt đối
                self.theta = 0.85 * target_theta + 0.15 * self.theta
                found_target = True

        if not found_target:
            self.theta += np.random.uniform(-cfg.ENEMY_TURN_NOISE, cfg.ENEMY_TURN_NOISE)

        self.x += np.cos(self.theta) * cfg.ENEMY_SPEED
        self.y += np.sin(self.theta) * cfg.ENEMY_SPEED
        n = cfg.GRID_SIZE - 1
        if self.x < 0 or self.x > n:
            self.theta = np.pi - self.theta
        if self.y < 0 or self.y > n:
            self.theta = -self.theta
        self.x = float(np.clip(self.x, 0, n))
        self.y = float(np.clip(self.y, 0, n))

    def _try_kill(self, colony):
        on_surface = colony.alive & (colony.layer == cfg.LAYER_SURFACE)
        if not np.any(on_surface):
            return
        idx = np.where(on_surface)[0]
        dist = np.hypot(colony.x[idx] - self.x, colony.y[idx] - self.y)
        near = idx[dist < cfg.ENEMY_KILL_RADIUS]
        if len(near) == 0:
            return
        remaining_quota = cfg.ENEMY_MAX_KILLS_PER_VISIT - self.kills_this_visit
        if remaining_quota <= 0:
            self._despawn()  # đã "no", tự rời đi
            return
        rolls = np.random.uniform(0, 1, len(near))
        killed = near[rolls < cfg.ENEMY_KILL_PROB_PER_TICK]
        if len(killed) > remaining_quota:
            killed = killed[:remaining_quota]
        if len(killed) > 0:
            colony.alive[killed] = False
            colony.underground.total_deaths += len(killed)
            self.total_kills += len(killed)
            self.kills_this_visit += len(killed)
