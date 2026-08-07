"""Quản lý toàn bộ đàn kiến bằng mảng NumPy (vectorized), tránh vòng lặp
Python từng con -- cần thiết để giữ khung hình mượt khi có nhiều kiến.

Bản 2D theo TẦNG: mỗi con kiến có vị trí ngang (x, y) trên ĐÚNG 1 tầng tại
1 thời điểm (self.depth = số nguyên, 0 = mặt đất). Kiến chỉ di chuyển 2D
trong phạm vi tầng hiện tại; khi "xuống/lên" giữa các tầng (qua giếng ở vị
trí lỗ tổ), depth đổi tức thời như đi thang máy, giống bản 3D cũ chỉ khác
là không còn nội suy độ sâu liên tục giữa 2 tầng.

Bản có vòng đời + sinh sản THẬT: đàn khởi tạo với n_start con, nhưng mảng
NumPy được cấp phát sẵn cho TỐI ĐA max_ants con (self.n) - dùng dead_slots
(bao gồm cả các "chỗ trống" chưa từng dùng tới) để đàn có thể LỚN LÊN dần
qua sinh sản, tới khi chạm trần max_ants. Chúa không sinh kiến trực tiếp -
chúa chỉ đẻ trứng (tốn thức ăn từ kho); trứng lớn dần thành ấu trùng THẬT
SỰ trong phòng ấu trùng (ăn đúng thức ăn nurse mang tới), và chỉ "nở" thành
1 kiến thợ mới khi đủ lớn (xem _update_larvae)."""
import numpy as np
import config as cfg


class AntColony:
    def __init__(self, n_start, max_ants, surface, underground, nest_pos=None):
        self.n = max_ants   # tổng SỐ CHỖ cấp phát sẵn trong mảng = trần dân số
        self.surface = surface
        self.underground = underground
        self.nest_pos = nest_pos if nest_pos else cfg.NEST_POS
        rng = np.random.default_rng()

        nest_x, nest_y = self.nest_pos
        # Vị trí ban đầu: rải quanh cửa tổ trên mặt đất (kể cả các "chỗ
        # trống" chưa dùng tới - không quan trọng vì alive=False, sẽ được
        # gán lại vị trí đúng lúc thật sự "nở" thành kiến ở phòng chúa)
        self.x = nest_x + rng.normal(0, 2.0, self.n).astype(np.float32)
        self.y = nest_y + rng.normal(0, 2.0, self.n).astype(np.float32)
        # depth: TẦNG hiện tại đang đứng (0 = mặt đất, 1=kho, 2=ấu trùng,
        # 3=chúa, 4+=phòng tự đào) - dùng để main.py biết vẽ con kiến này
        # lên đúng tầng nào đang xem.
        self.depth = np.zeros(self.n, dtype=np.int16)
        np.clip(self.x, 0, cfg.GRID_SIZE - 1, out=self.x)
        np.clip(self.y, 0, cfg.GRID_SIZE - 1, out=self.y)

        self.theta = rng.uniform(0, 2 * np.pi, self.n).astype(np.float32)
        self.layer = np.zeros(self.n, dtype=np.int8)          # 0=mặt đất, 1=dưới hầm (nhị phân, dùng cho state machine)
        self.state = np.zeros(self.n, dtype=np.int8)          # STATE_SEARCHING
        # Né vật cản kiểu "bám tường": avoid_cooldown = số tick còn lại đang
        # trong pha né (được làm mới mỗi lần vẫn còn chạm vật cản); avoid_side
        # = hướng né đã khóa (-1/+1, giữ nguyên trong suốt pha né, không đổi
        # ngẫu nhiên mỗi tick) - xem _avoid_obstacles()
        self.avoid_cooldown = np.zeros(self.n, dtype=np.int16)
        self.avoid_side = np.ones(self.n, dtype=np.float32)
        # Dùng cho STATE_DWELL (lượn trong phòng): dwell_ticks = số tick còn
        # lại trước khi tiếp tục hành trình; next_state = trạng thái sẽ
        # chuyển sang ngay khi hết giờ lượn (đã được quyết định từ lúc vừa
        # ĐẾN phòng, ví dụ có trở thành "nurse" hay không)
        self.dwell_ticks = np.zeros(self.n, dtype=np.int16)
        self.next_state = np.zeros(self.n, dtype=np.int8)
        self.carrying = np.zeros(self.n, dtype=bool)
        self.carry_type = np.zeros(self.n, dtype=np.int8)     # 0=không, 1=thức ăn, 2=nước
        self.carry_amount = np.zeros(self.n, dtype=np.float32)
        # Loại thức ăn CỤ THỂ đang tha (hạt/côn trùng/mật hoa) - chỉ dùng để
        # VẼ đúng màu miếng mồi trên lưng kiến, không ảnh hưởng mô phỏng
        self.carry_food_type = np.zeros(self.n, dtype=np.int8)

        # --- Phân vai: đa số thợ nhỏ, 1 phần nhỏ là lính (thợ lớn) ---
        self.role = (rng.uniform(0, 1, self.n) < cfg.MAJOR_WORKER_RATIO).astype(np.int8)

        # --- Vòng đời ---
        self.alive = np.zeros(self.n, dtype=bool)
        self.alive[:n_start] = True     # chỉ n_start con đầu tiên sống ngay
                                         # từ đầu - phần còn lại là "chỗ
                                         # trống" dự phòng để đàn lớn lên
        # Tuổi ban đầu rải ngẫu nhiên để đàn không cùng già/chết 1 lượt
        self.age = rng.uniform(0, cfg.MAX_AGE_TICKS * 0.6, self.n).astype(np.float32)

        # --- Trứng / ấu trùng (phòng ấu trùng NUÔI THẬT, xem _update_larvae) ---
        self.larva_growth = np.zeros(cfg.LARVA_MAX_COUNT, dtype=np.float32)
        self.larva_active = np.zeros(cfg.LARVA_MAX_COUNT, dtype=bool)

        # Thống kê tích lũy
        self.total_food_collected = 0
        self.tick_count = 0

    # ------------------------------------------------------------------
    def update(self):
        self.tick_count += 1
        self.avoid_cooldown = np.maximum(0, self.avoid_cooldown - 1).astype(np.int16)
        self._update_surface_ants()
        self._update_underground_ants()
        self.surface.decay_pheromone()
        self.underground.update_starvation_tracker()
        self.underground.consume_upkeep(int(np.sum(self.alive)))
        if self.surface.has_water_source():
            self.underground.deposit_water(cfg.WATER_BASE_INCOME_PER_TICK)
        self._update_lifecycle()
        self._update_larvae()
        # LƯU Ý: việc tái sinh thức ăn ngẫu nhiên KHÔNG còn nằm ở đây nữa -
        # đã chuyển sang main.py để có thể bật/tắt bằng nút trên thanh công
        # cụ, và để tránh 2 tổ (chính + đối thủ) cùng kích hoạt trùng lặp
        # khi cả 2 đều gọi update() mỗi khung hình.

    # ------------------------------------------------------------------
    def _wrap_indices(self, arr):
        return np.clip(arr.astype(np.int32), 0, cfg.GRID_SIZE - 1)

    def _update_surface_ants(self):
        on_surface = self.alive & (self.layer == cfg.LAYER_SURFACE)
        if not np.any(on_surface):
            return

        searching = on_surface & (self.state == cfg.STATE_SEARCHING)
        returning = on_surface & (self.state == cfg.STATE_RETURNING)

        # --- Kiến đang tìm ăn: dò pheromone 3 hướng rồi lệch theta ---
        if np.any(searching):
            idx = np.where(searching)[0]
            theta = self.theta[idx]
            x, y = self.x[idx], self.y[idx]
            prev_x, prev_y = x.copy(), y.copy()

            def sense(offset):
                sx = x + np.cos(theta + offset) * cfg.SENSE_DIST
                sy = y + np.sin(theta + offset) * cfg.SENSE_DIST
                xi = self._wrap_indices(sx)
                yi = self._wrap_indices(sy)
                return self.surface.sample_pheromone(xi, yi)

            def sense_danger(offset):
                sx = x + np.cos(theta + offset) * cfg.SENSE_DIST
                sy = y + np.sin(theta + offset) * cfg.SENSE_DIST
                xi = self._wrap_indices(sx)
                yi = self._wrap_indices(sy)
                return self.surface.sample_danger(xi, yi)

            left = sense(-cfg.SENSE_ANGLE)
            center = sense(0.0)
            right = sense(cfg.SENSE_ANGLE)

            bias = np.zeros_like(theta)
            bias = np.where(left > center, bias - cfg.SENSE_ANGLE, bias)
            bias = np.where(right > np.maximum(left, center), bias + cfg.SENSE_ANGLE, bias)

            # --- Né tránh mùi báo động nguy hiểm (kẻ thù) - hướng NGƯỢC
            # lại phía có mùi báo động đậm hơn, độc lập với việc tìm ăn ---
            d_left = sense_danger(-cfg.SENSE_ANGLE)
            d_center = sense_danger(0.0)
            d_right = sense_danger(cfg.SENSE_ANGLE)
            danger_bias = np.zeros_like(theta)
            danger_bias = np.where(d_left > d_center, danger_bias + cfg.SENSE_ANGLE, danger_bias)
            danger_bias = np.where(d_right > np.maximum(d_left, d_center), danger_bias - cfg.SENSE_ANGLE, danger_bias)
            danger_present = np.maximum(d_left, np.maximum(d_center, d_right)) > cfg.DANGER_PRESENCE_THRESHOLD
            bias = bias + np.where(danger_present, danger_bias * cfg.DANGER_AVOID_WEIGHT, 0.0)

            noise = np.random.uniform(-cfg.TURN_NOISE, cfg.TURN_NOISE, len(idx)).astype(np.float32)
            # Đang né vật cản -> giảm hẳn lực kéo theo mùi, để có thời gian
            # thật sự trượt ra khỏi rìa vật cản thay vì bị kéo lại ngay
            avoiding = self.avoid_cooldown[idx] > 0
            bias_scale = np.where(avoiding, cfg.SEARCH_BIAS_SUPPRESS_FACTOR, 1.0).astype(np.float32)
            self.theta[idx] = theta + bias * 0.5 * bias_scale + noise

            self.x[idx] += np.cos(self.theta[idx]) * cfg.ANT_SPEED
            self.y[idx] += np.sin(self.theta[idx]) * cfg.ANT_SPEED
            self._bounce_walls(idx)
            self._avoid_obstacles(idx, prev_x, prev_y)

            # Kiểm tra ô có thức ăn không -> nhặt (giá trị tùy loại thức ăn)
            xi = self._wrap_indices(self.x[idx])
            yi = self._wrap_indices(self.y[idx])
            got_food, food_types = self.surface.take_food(xi, yi, amount=1.0)
            got_idx = idx[got_food]
            if len(got_idx) > 0:
                values = np.array(
                    [cfg.FOOD_TYPE_VALUE[t] for t in food_types[got_food]],
                    dtype=np.float32,
                )
                self.carrying[got_idx] = True
                self.carry_type[got_idx] = 1
                self.carry_amount[got_idx] = values
                self.carry_food_type[got_idx] = food_types[got_food]
                self.state[got_idx] = cfg.STATE_RETURNING
                self.total_food_collected += len(got_idx)

        # --- Kiến đang tha thức ăn về tổ ---
        if np.any(returning):
            idx = np.where(returning)[0]
            x, y = self.x[idx], self.y[idx]
            prev_x, prev_y = x.copy(), y.copy()
            nest_x, nest_y = self.nest_pos
            to_nest_theta = np.arctan2(nest_y - y, nest_x - x)
            # Đang né vật cản -> gần như bỏ qua lực hút thẳng về tổ 1 lúc,
            # để thật sự trượt dọc rìa vật cản ra ngoài trước khi lại lao
            # thẳng về tổ - nếu không, hướng về tổ (trọng số 0.75) sẽ kéo
            # kiến quay lại đúng chỗ vừa bị chặn ngay tick sau, gây kẹt cứng
            avoiding = self.avoid_cooldown[idx] > 0
            nest_weight = np.where(avoiding, cfg.RETURN_NEST_WEIGHT_AVOIDING, 0.75).astype(np.float32)
            self.theta[idx] = (1.0 - nest_weight) * self.theta[idx] + nest_weight * to_nest_theta

            self.x[idx] += np.cos(self.theta[idx]) * cfg.ANT_SPEED
            self.y[idx] += np.sin(self.theta[idx]) * cfg.ANT_SPEED
            self._bounce_walls(idx)
            self._avoid_obstacles(idx, prev_x, prev_y)

            # Không củng cố dấu vết pheromone tại chỗ đang né - nếu không,
            # đúng điểm kẹt cạnh vật cản sẽ liên tục được "tô đậm" mùi,
            # càng kéo thêm nhiều kiến tìm ăn khác lao vào đúng chỗ kẹt đó
            not_avoiding = idx[self.avoid_cooldown[idx] == 0]
            if len(not_avoiding) > 0:
                xi = self._wrap_indices(self.x[not_avoiding])
                yi = self._wrap_indices(self.y[not_avoiding])
                self.surface.deposit_pheromone(xi, yi)

            dist = np.hypot(self.x[idx] - nest_x, self.y[idx] - nest_y)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                # Chui xuống giếng: "thang máy" đưa thẳng xuống tầng kho -
                # depth đổi tức thời, xuất hiện ngay tại điểm giếng (vị trí
                # lỗ tổ) trên tầng kho rồi đi bộ 2D tới phòng kho.
                self.layer[arrived] = cfg.LAYER_UNDERGROUND
                self.depth[arrived] = self.underground.storage_depth
                self.x[arrived] = self.underground.shaft_xy[0]
                self.y[arrived] = self.underground.shaft_xy[1]
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

    def _avoid_obstacles(self, idx, prev_x, prev_y):
        """Kiến không đi xuyên qua được đá/nước - nếu ô mới là chướng ngại
        vật, lùi lại vị trí cũ và né sang MỘT bên đã khóa sẵn (trái HOẶC
        phải, gần vuông góc với hướng đang đi) để TRƯỢT DỌC rìa vật cản ra
        ngoài, giống kiến thật đi vòng quanh chướng ngại vật - thay vì random
        lại hướng né mỗi tick (dễ khiến kiến dội qua dội lại tại chỗ). Hướng
        né được "khóa" trong suốt cả pha né (xem avoid_side/avoid_cooldown),
        và pha né được LÀM MỚI mỗi lần vẫn còn bị chặn, nên vật cản càng to
        thì kiến càng có nhiều thời gian trượt vòng qua trước khi bị mùi
        pheromone/hướng về tổ kéo trở lại."""
        xi = self._wrap_indices(self.x[idx])
        yi = self._wrap_indices(self.y[idx])
        blocked = self.surface.is_blocked(xi, yi)
        if not np.any(blocked):
            return
        blocked_idx = idx[blocked]
        self.x[blocked_idx] = prev_x[blocked]
        self.y[blocked_idx] = prev_y[blocked]

        n_blocked = len(blocked_idx)
        fresh = self.avoid_cooldown[blocked_idx] <= 0
        # Lần đầu chạm vật cản (chưa trong pha né) -> tung đồng xu chọn 1
        # bên rồi KHÓA lại; đã đang né rồi thì giữ nguyên bên cũ (không đổi
        # ngẫu nhiên giữa chừng, tránh dội qua dội lại)
        if np.any(fresh):
            new_side = np.random.choice([-1.0, 1.0], size=int(np.sum(fresh))).astype(np.float32)
            self.avoid_side[blocked_idx[fresh]] = new_side
        side = self.avoid_side[blocked_idx]
        self.theta[blocked_idx] += side * cfg.AVOID_TURN_ANGLE
        # Làm mới (refresh) pha né mỗi khi vẫn còn bị chặn
        self.avoid_cooldown[blocked_idx] = cfg.AVOID_COOLDOWN_TICKS

    # ------------------------------------------------------------------
    def _move_towards_2d(self, idx, target_xy, speed):
        """Di chuyển theo đường thẳng 2D (trong CÙNG 1 tầng) tới đích.
        Trả về khoảng cách còn lại. Không còn chiều sâu liên tục - việc
        đổi tầng (depth) diễn ra tức thời tại các điểm chuyển trạng thái
        (giống bước vào/ra khỏi thang máy), không phải trong hàm này."""
        x, y = self.x[idx], self.y[idx]
        tx, ty = target_xy
        dx, dy = tx - x, ty - y
        dist = np.sqrt(dx * dx + dy * dy)
        safe_dist = np.where(dist < 1e-6, 1.0, dist)  # tránh chia 0
        step = np.minimum(speed, dist)  # không đi vượt quá đích trong 1 tick
        self.x[idx] = x + dx / safe_dist * step
        self.y[idx] = y + dy / safe_dist * step
        self.theta[idx] = np.arctan2(dy, dx)
        return dist

    def _update_underground_ants(self):
        ug = self.alive & (self.layer == cfg.LAYER_UNDERGROUND)
        if not np.any(ug):
            return

        # --- đi tới kho ---
        mask = ug & (self.state == cfg.STATE_UG_TO_STORAGE)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_2d(idx, self.underground.storage, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                is_water = self.carry_type[arrived] == 2
                food_idx = arrived[~is_water]
                water_idx = arrived[is_water]

                if len(food_idx) > 0:
                    self.underground.deposit_to_storage(float(self.carry_amount[food_idx].sum()))
                    self.carry_amount[food_idx] = 0.0
                    self.carrying[food_idx] = False
                    rng_vals = np.random.uniform(0, 1, len(food_idx))
                    become_nurse = food_idx[rng_vals < cfg.NURSE_PROBABILITY]
                    go_back = food_idx[rng_vals >= cfg.NURSE_PROBABILITY]
                    self.carrying[become_nurse] = True
                    self.carry_type[become_nurse] = 1
                    self.carry_type[go_back] = 0
                    # Không rời phòng ngay - LƯỢN trong kho 1 lúc (như đang
                    # sắp xếp/kiểm tra đồ) rồi mới quyết định đi đâu tiếp.
                    self._start_dwell(become_nurse, cfg.STATE_UG_TO_NURSERY)
                    self._start_dwell(go_back, cfg.STATE_UG_TO_SHAFT)

                if len(water_idx) > 0:
                    self.underground.deposit_water(float(self.carry_amount[water_idx].sum()))
                    self.carry_amount[water_idx] = 0.0
                    self.carry_type[water_idx] = 0
                    self.carrying[water_idx] = False
                    self._start_dwell(water_idx, cfg.STATE_UG_TO_SHAFT)

        # --- nurse mang đồ tới phòng ấu trùng ---
        mask = ug & (self.state == cfg.STATE_UG_TO_NURSERY)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_2d(idx, self.underground.nursery, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                self.underground.deposit_to_nursery(len(arrived))
                self.carrying[arrived] = False
                self.carry_type[arrived] = 0
                # Lượn trong phòng ấu trùng 1 lúc (đang chăm ấu trùng) rồi mới về
                self._start_dwell(arrived, cfg.STATE_UG_TO_SHAFT)

        # --- quay lại giếng (vị trí lỗ tổ, TRÊN TẦNG HIỆN TẠI) để lên mặt đất ---
        mask = ug & (self.state == cfg.STATE_UG_TO_SHAFT)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_2d(idx, self.underground.shaft_xy, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                self.layer[arrived] = cfg.LAYER_SURFACE
                self.depth[arrived] = cfg.LAYER_SURFACE_DEPTH
                self.x[arrived] = self.nest_pos[0]
                self.y[arrived] = self.nest_pos[1]
                self.state[arrived] = cfg.STATE_SEARCHING
                self.theta[arrived] = np.random.uniform(0, 2 * np.pi, len(arrived))

        self._update_dwelling_ants()

    # ------------------------------------------------------------------
    def _start_dwell(self, idx, next_state):
        """Cho 1 nhóm kiến bắt đầu LƯỢN trong phòng hiện tại (self.depth
        của chúng) một khoảng thời gian ngẫu nhiên trước khi tiếp tục hành
        trình sang next_state - để phòng ngầm có hoạt động thật sự thay vì
        kiến chỉ chạm tâm phòng rồi quay đầu ngay."""
        if len(idx) == 0:
            return
        self.state[idx] = cfg.STATE_DWELL
        self.next_state[idx] = next_state
        self.dwell_ticks[idx] = np.random.randint(
            cfg.DWELL_MIN_TICKS, cfg.DWELL_MAX_TICKS + 1, size=len(idx)
        ).astype(np.int16)

    def _room_center_and_radius(self, depth):
        if depth == self.underground.storage_depth:
            return self.underground.storage, cfg.ROOM_RADIUS
        if depth == self.underground.nursery_depth:
            return self.underground.nursery, cfg.ROOM_RADIUS
        if depth == self.underground.queen_depth:
            return self.underground.queen_room, cfg.ROOM_RADIUS * 1.1
        return None, None

    def _update_dwelling_ants(self):
        mask = self.alive & (self.state == cfg.STATE_DWELL)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        self.dwell_ticks[idx] -= 1

        # Đi lại ngẫu nhiên, chậm, quanh tâm phòng - tách riêng theo từng
        # loại phòng (kho / ấu trùng / phòng chúa) vì mỗi phòng ở 1 tầng
        # (depth) và có tâm khác nhau.
        for depth_val in np.unique(self.depth[idx]):
            center, radius = self._room_center_and_radius(int(depth_val))
            if center is None:
                continue
            sub = idx[self.depth[idx] == depth_val]
            self.theta[sub] += np.random.uniform(-0.6, 0.6, len(sub)).astype(np.float32)
            self.x[sub] += np.cos(self.theta[sub]) * cfg.DWELL_SPEED
            self.y[sub] += np.sin(self.theta[sub]) * cfg.DWELL_SPEED

            dx = self.x[sub] - center[0]
            dy = self.y[sub] - center[1]
            dist = np.hypot(dx, dy)
            max_r = radius * cfg.ROOM_WANDER_FACTOR
            over = dist > max_r
            if np.any(over):
                safe_dist = np.where(dist[over] < 1e-6, 1.0, dist[over])
                scale = max_r / safe_dist
                self.x[sub[over]] = center[0] + dx[over] * scale
                self.y[sub[over]] = center[1] + dy[over] * scale
                self.theta[sub[over]] = np.arctan2(-dy[over], -dx[over])  # bật ngược lại vào trong phòng

        # Hết giờ lượn -> tiếp tục hành trình. Nếu điểm đến kế tiếp là phòng
        # ấu trùng (khác tầng với kho), cần "đi thang máy" (đổi depth) trước
        # khi tiếp tục đi bộ 2D; các trường hợp còn lại (về giếng) tiếp tục
        # ngay từ vị trí đang lượn tới, không cần dịch chuyển tức thời.
        done = idx[self.dwell_ticks[idx] <= 0]
        if len(done) > 0:
            to_nursery = done[self.next_state[done] == cfg.STATE_UG_TO_NURSERY]
            others = done[self.next_state[done] != cfg.STATE_UG_TO_NURSERY]
            if len(to_nursery) > 0:
                self.depth[to_nursery] = self.underground.nursery_depth
                self.x[to_nursery] = self.underground.shaft_xy[0]
                self.y[to_nursery] = self.underground.shaft_xy[1]
                self.state[to_nursery] = cfg.STATE_UG_TO_NURSERY
            if len(others) > 0:
                self.state[others] = self.next_state[others]

    # ------------------------------------------------------------------
    def _update_lifecycle(self):
        """Tăng tuổi, tính nguy cơ chết (già/đói), và xử lý sinh sản."""
        alive_idx = np.where(self.alive)[0]
        if len(alive_idx) == 0:
            return
        self.age[alive_idx] += 1

        # --- Chết vì già: xác suất tăng dần sau MAX_AGE_TICKS ---
        age = self.age[alive_idx]
        over = np.clip(age - cfg.MAX_AGE_TICKS, 0, None)
        old_age_prob = np.where(
            over > 0,
            cfg.OLD_AGE_DEATH_RATE * (1.0 + over / cfg.OLD_AGE_DEATH_GROWTH),
            0.0,
        )

        # --- Chết vì đói: áp dụng đều cho cả đàn khi ấu trùng thiếu ăn lâu ---
        starving = self.underground.is_starving()
        starve_prob = cfg.STARVATION_DEATH_RATE if starving else 0.0

        # --- Chết vì khát: áp dụng đều cho cả đàn khi hết nước dự trữ lâu ---
        dehydrated = self.underground.is_dehydrated()
        dehydrate_prob = cfg.DEHYDRATION_DEATH_RATE if dehydrated else 0.0

        death_prob = 1.0 - (1.0 - old_age_prob) * (1.0 - starve_prob) * (1.0 - dehydrate_prob)
        rolls = np.random.uniform(0, 1, len(alive_idx))
        died = alive_idx[rolls < death_prob]
        if len(died) > 0:
            self.alive[died] = False
            self.underground.total_deaths += len(died)

        # --- Đẻ trứng: chúa thử đẻ 1 trứng mới theo chu kỳ, cần đủ thức ăn
        # + nước TRONG KHO. Trứng KHÔNG lập tức thành kiến - nó được chuyển
        # qua _update_larvae() để lớn lên thật sự trong phòng ấu trùng. ---
        if self.tick_count % cfg.EGG_LAY_INTERVAL == 0:
            free_larva_slots = np.where(~self.larva_active)[0]
            has_ant_capacity = np.any(~self.alive)
            if len(free_larva_slots) > 0 and has_ant_capacity:
                got_food = self.underground.try_consume_for_egg(
                    cfg.EGG_FOOD_COST, cfg.EGG_WATER_COST
                )
                if got_food:
                    slot = free_larva_slots[0]
                    self.larva_active[slot] = True
                    self.larva_growth[slot] = 0.0

    def _update_larvae(self):
        """Ấu trùng ĐANG CÓ trong phòng ấu trùng lớn lên dần bằng cách ăn
        thức ăn nurse mang tới (food_in_nursery) - hết thức ăn ở đó thì lớn
        rất chậm thay vì dừng hẳn. Ấu trùng đủ lớn (growth >= 1.0) sẽ "nở"
        thành 1 kiến thợ mới, NẾU còn chỗ trống trong đàn (chưa chạm trần
        max_ants) - nếu chưa có chỗ, ấu trùng chờ (growth giữ ở mức tối đa)
        tới khi có kiến khác chết đi, nhường chỗ."""
        active = np.where(self.larva_active)[0]
        if len(active) == 0:
            return

        has_food = self.underground.food_in_nursery > 0
        growth_rate = cfg.LARVA_GROWTH_PER_TICK * (1.0 if has_food else cfg.LARVA_GROWTH_STARVED_FACTOR)
        self.larva_growth[active] = np.clip(self.larva_growth[active] + growth_rate, 0.0, 1.0)
        if has_food:
            eaten = cfg.LARVA_FOOD_PER_TICK * len(active)
            self.underground.food_in_nursery = max(0.0, self.underground.food_in_nursery - eaten)

        mature = active[self.larva_growth[active] >= 1.0]
        if len(mature) == 0:
            return
        dead_slots = np.where(~self.alive)[0]
        n_hatch = min(len(mature), len(dead_slots))
        if n_hatch == 0:
            return  # đủ lớn nhưng đàn đã đầy chỗ - chờ tới khi có chỗ trống
        hatch_larvae = mature[:n_hatch]
        new_ants = dead_slots[:n_hatch]
        self.larva_active[hatch_larvae] = False
        self.larva_growth[hatch_larvae] = 0.0
        self._spawn_new_ants(new_ants)
        self.underground.total_births += n_hatch

    def _spawn_new_ants(self, idx):
        """Tái sử dụng các ô đã chết để tạo kiến mới, xuất hiện tại phòng
        chúa, lượn 1 lúc (mới sinh, còn quây quần quanh chúa) rồi tự đi lên
        mặt đất qua giếng."""
        self.alive[idx] = True
        self.age[idx] = 0.0
        self.layer[idx] = cfg.LAYER_UNDERGROUND
        self.depth[idx] = self.underground.queen_depth
        self.carrying[idx] = False
        self.carry_type[idx] = 0
        self.carry_amount[idx] = 0.0
        self.role[idx] = (np.random.uniform(0, 1, len(idx)) < cfg.MAJOR_WORKER_RATIO).astype(np.int8)
        qx, qy = self.underground.queen_room
        self.x[idx] = qx
        self.y[idx] = qy
        self.theta[idx] = np.random.uniform(0, 2 * np.pi, len(idx))
        self._start_dwell(idx, cfg.STATE_UG_TO_SHAFT)

    # ------------------------------------------------------------------
    def counts(self):
        """Trả về dict thống kê nhanh cho bảng UI."""
        alive = self.alive
        return {
            "population": int(np.sum(alive)),
            "soldiers": int(np.sum(alive & (self.role == cfg.ROLE_MAJOR))),
            "searching": int(np.sum(alive & (self.layer == 0) & (self.state == cfg.STATE_SEARCHING))),
            "returning": int(np.sum(alive & (self.layer == 0) & (self.state == cfg.STATE_RETURNING))),
            "underground": int(np.sum(alive & (self.layer == 1))),
            "total_food_collected": self.total_food_collected,
            "food_in_storage": self.underground.food_in_storage,
            "food_in_nursery": self.underground.food_in_nursery,
            "water_in_storage": self.underground.water_in_storage,
            "total_births": self.underground.total_births,
            "total_deaths": self.underground.total_deaths,
            "is_starving": self.underground.is_starving(),
            "is_dehydrated": self.underground.is_dehydrated(),
            "larva_count": int(np.sum(self.larva_active)),
        }
