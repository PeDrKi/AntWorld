"""Kẻ thù tự nhiên: xuất hiện ngẫu nhiên trên mặt đất theo chu kỳ, di
chuyển về phía những nơi có nhiều kiến (của BẤT KỲ tổ nào - nó là thiên
địch trung lập, không phân biệt tổ), và có xác suất giết kiến trong tầm
gần mỗi tick. Lính (thợ lớn) có thể gây sát thương lên kẻ thù và bị giết
khó hơn thợ thường. Sau 1 khoảng thời gian hoặc bị đánh bại sẽ rời đi.

Nếu bị lính ĐÁNH BẠI HẲN (hết máu, khác với chỉ hết giờ tự rời đi), xác nó
để lại là 1 "mồi lớn" giàu dinh dưỡng cho đàn kiến - xem carcass_*/
_spawn_carcass()/_decay_carcass() bên dưới và AntColony._update_haulers()
trong ants.py: phải có ĐỦ số kiến tập trung cùng lúc mới khiêng nổi về tổ
(cooperative transport, giống hệt cách kiến thật hợp sức khiêng con mồi to
hơn cả cơ thể chúng), không đủ người kịp thời thì xác rữa mất."""
import numpy as np
from . import config as cfg


class EnemyManager:
    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.life_left = 0
        self.health = cfg.ENEMY_MAX_HEALTH
        self.spawn_cooldown = np.random.randint(
            cfg.ENEMY_SPAWN_COOLDOWN_MIN, cfg.ENEMY_SPAWN_COOLDOWN_MAX
        )
        self.total_kills = 0
        self.total_defeated = 0  # số lần bị lính đánh bại hoàn toàn
        self.kills_this_visit = 0
        self.auto_spawn_enabled = True  # bật/tắt được từ thanh công cụ -
                                         # tắt thì KHÔNG tự xuất hiện định kỳ
                                         # nữa (nhưng con đang có mặt vẫn
                                         # sống hết vòng đời bình thường, và
                                         # công cụ "Tha ke thu" vẫn dùng được)

        # --- Xác con mồi lớn (carcass) sau khi bị đánh bại HẲN - xem
        # HAUL_* trong config.py + AntColony._update_haulers() trong
        # ants.py. Đây là XÁC (đã chết, đứng yên) sau khi self.active kết
        # thúc do bị đánh bại - ĐỘC LẬP với con kẻ thù ĐANG SỐNG (active/
        # x/y ở trên): 1 kẻ thù MỚI có thể đã xuất hiện ở nơi khác trong
        # lúc xác cũ vẫn còn đang chờ được khiêng, 2 pha không loại trừ
        # nhau. ---
        self.carcass_active = False
        self.carcass_x = 0.0
        self.carcass_y = 0.0
        self.carcass_food_value = 0.0
        self.carcass_decay_left = 0
        self.total_carcasses_hauled = 0

    def update(self, colonies):
        """colonies: danh sách các AntColony (tổ chính + tổ đối thủ nếu
        có) - kẻ thù trung lập, đe dọa TẤT CẢ các tổ như nhau."""
        self._decay_carcass()

        if not self.active:
            if not self.auto_spawn_enabled:
                return  # tắt chế độ tự sinh - không đếm ngược, không xuất hiện
            self.spawn_cooldown -= 1
            if self.spawn_cooldown <= 0:
                self._spawn()
            return

        self.life_left -= 1
        if self.life_left <= 0:
            self._despawn()
            return

        self._move_towards_prey(colonies)
        self._try_kill(colonies)

    # ------------------------------------------------------------------
    def _spawn(self):
        self.active = True
        self.x = float(np.random.uniform(4, cfg.GRID_SIZE - 4))
        self.y = float(np.random.uniform(4, cfg.GRID_SIZE - 4))
        self.theta = float(np.random.uniform(0, 2 * np.pi))
        self.life_left = cfg.ENEMY_LIFETIME_TICKS
        self.health = cfg.ENEMY_MAX_HEALTH
        self.kills_this_visit = 0

    def force_spawn_at(self, x, y):
        """Người chơi chủ động thả kẻ thù tại vị trí (x, y) chỉ định -
        dùng cho công cụ can thiệp bằng chuột."""
        self.active = True
        self.x = float(x)
        self.y = float(y)
        self.theta = float(np.random.uniform(0, 2 * np.pi))
        self.life_left = cfg.ENEMY_LIFETIME_TICKS
        self.health = cfg.ENEMY_MAX_HEALTH
        self.kills_this_visit = 0

    def _despawn(self):
        self.active = False
        self.spawn_cooldown = np.random.randint(
            cfg.ENEMY_SPAWN_COOLDOWN_MIN, cfg.ENEMY_SPAWN_COOLDOWN_MAX
        )

    def _spawn_carcass(self, x, y):
        """Kẻ thù VỪA BỊ ĐÁNH BẠI HẲN (không phải chỉ bỏ chạy hết giờ) -
        để lại xác tại đúng vị trí ngã xuống, chờ đủ kiến tới khiêng (xem
        HAUL_* trong config.py). Nếu đã có 1 xác khác CHƯA kịp khiêng
        xong (hiếm - cửa sổ HAUL_DECAY_TICKS khá ngắn so với thời gian
        đánh bại 2 kẻ thù liên tiếp), xác mới ĐÈ LÊN xác cũ - chấp nhận
        đơn giản hóa này thay vì phải quản lý nhiều xác cùng lúc."""
        self.carcass_active = True
        self.carcass_x = x
        self.carcass_y = y
        self.carcass_food_value = cfg.HAUL_TOTAL_FOOD_VALUE
        self.carcass_decay_left = cfg.HAUL_DECAY_TICKS

    def _decay_carcass(self):
        """Xác rữa dần nếu đàn kiến không gọi đủ người khiêng kịp thời -
        gọi mỗi tick (ngay đầu update(), KHÔNG phụ thuộc self.active vì
        xác tồn tại độc lập với vòng đời con kẻ thù đang sống)."""
        if not self.carcass_active:
            return
        self.carcass_decay_left -= 1
        if self.carcass_decay_left <= 0:
            self.carcass_active = False

    def _move_towards_prey(self, colonies):
        # Tìm kiến còn sống trên mặt đất (của bất kỳ tổ nào) trong bán kính
        # "nhìn thấy" để đuổi theo; nếu không có con nào gần, đi lang thang.
        best_dist2 = None
        best_dx = best_dy = 0.0
        for colony in colonies:
            on_surface = colony.alive & (colony.layer == cfg.LAYER_SURFACE)
            if not np.any(on_surface):
                continue
            dx = colony.x[on_surface] - self.x
            dy = colony.y[on_surface] - self.y
            dist2 = dx * dx + dy * dy
            i = np.argmin(dist2)
            if best_dist2 is None or dist2[i] < best_dist2:
                best_dist2 = dist2[i]
                best_dx, best_dy = dx[i], dy[i]

        found_target = best_dist2 is not None and best_dist2 < cfg.ENEMY_DETECT_RADIUS ** 2
        if found_target:
            target_theta = np.arctan2(best_dy, best_dx)
            self.theta = 0.85 * target_theta + 0.15 * self.theta
        else:
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

    def _try_kill(self, colonies):
        remaining_quota = cfg.ENEMY_MAX_KILLS_PER_VISIT - self.kills_this_visit

        for colony in colonies:
            on_surface = colony.alive & (colony.layer == cfg.LAYER_SURFACE)
            if not np.any(on_surface):
                continue
            idx = np.where(on_surface)[0]
            dist = np.hypot(colony.x[idx] - self.x, colony.y[idx] - self.y)
            near = idx[dist < cfg.ENEMY_KILL_RADIUS]
            if len(near) == 0:
                continue

            is_major = colony.role[near] == cfg.ROLE_MAJOR

            # --- Lính (thợ lớn) trong tầm gây sát thương lên kẻ thù ---
            major_near = near[is_major]
            if len(major_near) > 0:
                hits = np.random.uniform(0, 1, len(major_near)) < cfg.SOLDIER_DAMAGE_PROB
                dmg = float(np.sum(hits)) * cfg.SOLDIER_DAMAGE_PER_HIT
                if dmg > 0:
                    self.health -= dmg
                    if self.health <= 0:
                        self.total_defeated += 1
                        self._spawn_carcass(self.x, self.y)
                        self._despawn()
                        return  # kẻ thù đã bị đánh bại, dừng luôn tick này

            if remaining_quota <= 0:
                continue  # đã "no" với tổ này nhưng vẫn xét các tổ khác

            # --- Kẻ thù phản công: lính khó bị giết hơn thợ thường ---
            kill_prob = np.where(
                is_major,
                cfg.ENEMY_KILL_PROB_PER_TICK * cfg.MAJOR_DEFENSE_FACTOR,
                cfg.ENEMY_KILL_PROB_PER_TICK,
            )
            rolls = np.random.uniform(0, 1, len(near))
            killed = near[rolls < kill_prob]
            if len(killed) > remaining_quota:
                killed = killed[:remaining_quota]
            if len(killed) > 0:
                colony.alive[killed] = False
                colony.underground.total_deaths += len(killed)
                colony.underground.add_corpse(len(killed))
                self.total_kills += len(killed)
                self.kills_this_visit += len(killed)
                remaining_quota -= len(killed)

        if remaining_quota <= 0:
            self._despawn()  # đã "no", tự rời đi
