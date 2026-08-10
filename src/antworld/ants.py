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
from . import config as cfg


class AntColony:
    def __init__(self, n_start, max_ants, surface, underground, nest_pos=None, founding=False):
        self.n = max_ants   # tổng SỐ CHỖ cấp phát sẵn trong mảng = trần dân số
        self.surface = surface
        self.underground = underground
        self.nest_pos = nest_pos if nest_pos else cfg.NEST_POS
        rng = np.random.default_rng()

        # --- Giai đoạn lập tổ (xem khối config FOUNDING_* trong config.py)
        # - khi bật, n_start PHẢI = 0 (chưa có thợ nào, chỉ có chúa - chúa
        # không phải 1 phần tử trong mảng self.alive, chỉ là khái niệm/
        # phòng). self.founding_phase=True tắt hẳn con đường đẻ trứng bằng
        # kho thức ăn (chưa có kho) và bật con đường đẻ bằng năng lượng dự
        # trữ riêng của chúa - xem _update_lifecycle().
        self.founding_phase = bool(founding)
        self.queen_energy = cfg.QUEEN_INITIAL_ENERGY if self.founding_phase else 0.0

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
        # Xâm chiếm tổ đối thủ: raid_loot_ticks = số tick đã đứng cướp phá
        # tại tổ đối thủ (để biết khi nào tự rút quân); raid_cooldown = số
        # tick còn lại trước khi CẢ ĐÀN được cân nhắc phát động đợt mới
        self.raid_loot_ticks = np.zeros(self.n, dtype=np.int16)
        self.raid_cooldown = 0
        # Dùng cho STATE_DWELL (lượn trong phòng): dwell_ticks = số tick còn
        # lại trước khi tiếp tục hành trình; next_state = trạng thái sẽ
        # chuyển sang ngay khi hết giờ lượn (đã được quyết định từ lúc vừa
        # ĐẾN phòng, ví dụ có trở thành "nurse" hay không)
        self.dwell_ticks = np.zeros(self.n, dtype=np.int16)
        self.next_state = np.zeros(self.n, dtype=np.int8)
        # Phòng CỤ THỂ (room_id, không chỉ tầng/depth) đang lượn trong đó -
        # cần thiết từ khi nhiều phòng dùng chung 1 tầng (kho+nước, trứng+
        # ấu trùng), vì chỉ biết depth không đủ để biết đang ở phòng nào
        self.dwell_room_id = np.zeros(self.n, dtype=np.int8)
        self.carrying = np.zeros(self.n, dtype=bool)
        self.carry_type = np.zeros(self.n, dtype=np.int8)     # 0=không, 1=thức ăn, 2=nước
        self.carry_amount = np.zeros(self.n, dtype=np.float32)
        # Loại thức ăn CỤ THỂ đang tha (hạt/côn trùng/mật hoa) - chỉ dùng để
        # VẼ đúng màu miếng mồi trên lưng kiến, không ảnh hưởng mô phỏng
        self.carry_food_type = np.zeros(self.n, dtype=np.int8)

        # --- Phân vai: đa số thợ nhỏ, 1 phần nhỏ là lính (thợ lớn) ---
        self.role = (rng.uniform(0, 1, self.n) < cfg.MAJOR_WORKER_RATIO).astype(np.int8)
        # --- Trong số lính, 1 nửa là "lính gác" đóng quân cố định ở phòng
        # gác cửa (xem _update_guards) - nửa còn lại vẫn tha đồ/chiến đấu
        # ngẫu nhiên như thợ thường mọi khi ---
        self.is_guard = (self.role == cfg.ROLE_MAJOR) & (
            rng.uniform(0, 1, self.n) < cfg.GUARD_SHARE_OF_MAJORS
        )

        # --- Chức năng CỐ ĐỊNH của THỢ NHỎ (job): mỗi con 1 việc suốt đời -
        # kiếm ăn/nước (FORAGER, đa số), chăm ấu trùng (NURSE) hay chăm
        # trứng+chúa (ATTENDANT) - xem JOB_* trong config.py. Lính
        # (ROLE_MAJOR) không thuộc hệ thống này nên luôn để mặc định
        # FORAGER (không ảnh hưởng gì - hành vi của lính do is_guard quyết
        # định, không tra self.job)."""
        self.job = np.full(self.n, cfg.JOB_FORAGER, dtype=np.int8)
        if n_start >= cfg.JOB_SPECIALIZATION_MIN_POPULATION:
            job_roll = rng.uniform(0, 1, self.n)
            is_minor = self.role == cfg.ROLE_MINOR
            self.job[is_minor & (job_roll < cfg.JOB_NURSE_RATIO)] = cfg.JOB_NURSE
            self.job[is_minor & (job_roll >= cfg.JOB_NURSE_RATIO) &
                     (job_roll < cfg.JOB_NURSE_RATIO + cfg.JOB_ATTENDANT_RATIO)] = cfg.JOB_ATTENDANT

        # --- Vòng đời ---
        self.alive = np.zeros(self.n, dtype=bool)
        self.alive[:n_start] = True     # chỉ n_start con đầu tiên sống ngay
                                         # từ đầu - phần còn lại là "chỗ
                                         # trống" dự phòng để đàn lớn lên
        # Tuổi ban đầu rải ngẫu nhiên để đàn không cùng già/chết 1 lượt
        self.age = rng.uniform(0, cfg.MAX_AGE_TICKS * 0.6, self.n).astype(np.float32)

        # Lính gác khởi đầu đóng quân NGAY trong phòng gác cửa, không đứng
        # lẫn trên mặt đất như thợ thường
        guard_start = np.where(self.is_guard[:n_start])[0]
        if len(guard_start) > 0:
            self.layer[guard_start] = cfg.LAYER_UNDERGROUND
            self.depth[guard_start] = cfg.DEPTH_GUARD
            self.x[guard_start] = nest_x
            self.y[guard_start] = nest_y
            self.state[guard_start] = cfg.STATE_GUARD_DUTY

        # Nurse/attendant khởi đầu cũng đóng quân NGAY tại đúng phòng của
        # mình (kho / phòng chúa) - không bao giờ đứng lẫn trên mặt đất
        nurse_start = np.where(self.job[:n_start] == cfg.JOB_NURSE)[0]
        if len(nurse_start) > 0:
            self.layer[nurse_start] = cfg.LAYER_UNDERGROUND
            self.depth[nurse_start] = underground.storage_depth
            self.x[nurse_start] = underground.storage[0]
            self.y[nurse_start] = underground.storage[1]
            self.state[nurse_start] = cfg.STATE_NURSE_AT_STORAGE

        attendant_start = np.where(self.job[:n_start] == cfg.JOB_ATTENDANT)[0]
        if len(attendant_start) > 0:
            self.layer[attendant_start] = cfg.LAYER_UNDERGROUND
            self.depth[attendant_start] = underground.queen_depth
            self.x[attendant_start] = underground.queen_room[0]
            self.y[attendant_start] = underground.queen_room[1]
            self.state[attendant_start] = cfg.STATE_ATTENDANT_AT_QUEEN
            self.dwell_ticks[attendant_start] = np.random.randint(
                cfg.ATTENDANT_SWITCH_TICKS_MIN, cfg.ATTENDANT_SWITCH_TICKS_MAX + 1, size=len(attendant_start)
            ).astype(np.int16)

        # --- Trứng (phòng trứng, ủ theo thời gian) -> Ấu trùng (phòng ấu
        # trùng, lớn nhờ ăn - xem _update_eggs / _update_larvae) ---
        self.egg_growth = np.zeros(cfg.EGG_MAX_COUNT, dtype=np.float32)
        self.egg_active = np.zeros(cfg.EGG_MAX_COUNT, dtype=bool)
        self.larva_growth = np.zeros(cfg.LARVA_MAX_COUNT, dtype=np.float32)
        self.larva_active = np.zeros(cfg.LARVA_MAX_COUNT, dtype=bool)
        self.pupa_growth = np.zeros(cfg.PUPA_MAX_COUNT, dtype=np.float32)
        self.pupa_active = np.zeros(cfg.PUPA_MAX_COUNT, dtype=bool)

        # Thống kê tích lũy
        self.total_food_collected = 0
        self.tick_count = 0

        # --- Trophallaxis (mớm thức ăn miệng-miệng) - danh sách các "khoảnh
        # khắc mớm mồi" GẦN ĐÂY để lớp hiển thị vẽ 1 dây nối ngắn/nhòe dần
        # giữa 2 con kiến (hoặc kiến-ấu trùng, kiến-chúa) đang trao đổi thức
        # ăn - đúng theo hành vi THẬT của loài kiến: KHÔNG chỉ "vác cục mồi
        # bỏ vào kho" đơn thuần, mà thức ăn còn được truyền tay/mớm trực
        # tiếp giữa các cá thể. Mỗi phần tử: (x1,y1, x2,y2, tick_tao_ra,
        # tầng) - HOÀN TOÀN chỉ để HIỂN THỊ, không ảnh hưởng gì tới số liệu
        # thức ăn/kinh tế của tổ (xem _record_trophallaxis bên dưới).
        self.trophallaxis_events = []

    # ------------------------------------------------------------------
    def update(self, enemy=None, rival=None):
        self.tick_count += 1
        self.avoid_cooldown = np.maximum(0, self.avoid_cooldown - 1).astype(np.int16)
        if self.trophallaxis_events:
            cutoff = self.tick_count - cfg.TROPHALLAXIS_TTL_TICKS
            self.trophallaxis_events = [e for e in self.trophallaxis_events if e[4] > cutoff]
        self._update_surface_ants()
        self._update_underground_ants()
        self._update_nurses()
        self._update_attendants()
        self._update_guards(enemy, rival)
        self._update_raids(rival)
        self.surface.decay_pheromone()
        population = int(np.sum(self.alive))
        if not self.founding_phase:
            # Bỏ qua theo dõi "cạn kho" trong lúc lập tổ - kho THẬT SỰ
            # chưa tồn tại (chưa có ai tha mồi về), tính như bình thường
            # sẽ báo "cạn kho" giả ngay từ tick đầu tiên (xem giải thích
            # chi tiết trong _update_lifecycle).
            self.underground.update_starvation_tracker(population)
        self.underground.consume_upkeep(population)
        self.underground.decay_graveyard()
        if self.surface.has_water_source():
            self.underground.deposit_water(cfg.WATER_BASE_INCOME_PER_TICK)
        self._update_lifecycle()
        self._update_eggs()
        self._update_larvae()
        self._update_pupae()
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

            # --- "Uống" nước tại mép nước: kiến tìm ăn đi tình cờ NGANG
            # SÁT mép nước có thể tranh thủ uống 1 ngụm mang về tổ, y hệt
            # nhặt thức ăn - chỉ xét những con VẪN CÒN đang STATE_SEARCHING
            # thật sự (tay không, chưa vừa nhặt được thức ăn ở trên) để
            # không "vừa nhặt thức ăn vừa uống nước" cùng 1 tick. Xác suất
            # nhỏ mỗi tick (WATER_PICKUP_PROB) thay vì uống ngay lập tức -
            # kiến thường lượn/né quanh mép nước khá nhiều tick liền (xem
            # _avoid_obstacles), nên qua vài chục tick gần như chắc chắn sẽ
            # có lúc "tranh thủ" uống được, không cần xác suất cao mỗi tick.
            still_searching = idx[self.state[idx] == cfg.STATE_SEARCHING]
            if len(still_searching) > 0:
                wxi = self._wrap_indices(self.x[still_searching])
                wyi = self._wrap_indices(self.y[still_searching])
                near_w = self.surface.near_water(wxi, wyi)
                if np.any(near_w):
                    candidates = still_searching[near_w]
                    rolls = np.random.uniform(0, 1, len(candidates))
                    drink_idx = candidates[rolls < cfg.WATER_PICKUP_PROB]
                    if len(drink_idx) > 0:
                        self.carrying[drink_idx] = True
                        self.carry_type[drink_idx] = 2
                        self.carry_amount[drink_idx] = cfg.WATER_CARRY_AMOUNT
                        self.state[drink_idx] = cfg.STATE_RETURNING

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
                # Chui xuống giếng: "thang máy" đưa thẳng xuống ĐÚNG tầng
                # cần tới - tha thức ăn thì xuống tầng kho, tha nước thì
                # xuống tầng bể trữ nước (2 tầng RIÊNG BIỆT) - depth đổi tức
                # thời, xuất hiện ngay tại điểm giếng (vị trí lỗ tổ) trên
                # tầng đó rồi đi bộ 2D tới phòng.
                is_water = self.carry_type[arrived] == 2
                self.layer[arrived] = cfg.LAYER_UNDERGROUND
                self.depth[arrived] = np.where(
                    is_water, self.underground.water_depth, self.underground.storage_depth
                )
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

        # --- đi tới kho HOẶC bể trữ nước (tùy đang tha thức ăn hay nước) ---
        mask = ug & (self.state == cfg.STATE_UG_TO_STORAGE)
        if np.any(mask):
            idx = np.where(mask)[0]
            is_water_carry = self.carry_type[idx] == 2
            # Mỗi kiến có thể đang hướng tới 1 trong 2 đích khác nhau (kho
            # HOẶC bể nước) - xây mảng đích riêng cho TỪNG con rồi di
            # chuyển vectorized 1 lần, thay vì tách thành 2 lệnh gọi.
            target_x = np.where(is_water_carry, self.underground.water_room[0], self.underground.storage[0])
            target_y = np.where(is_water_carry, self.underground.water_room[1], self.underground.storage[1])
            dist = self._move_towards_2d(idx, (target_x, target_y), cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                is_water = self.carry_type[arrived] == 2
                food_idx = arrived[~is_water]
                water_idx = arrived[is_water]

                if len(food_idx) > 0:
                    self.underground.deposit_to_storage(float(self.carry_amount[food_idx].sum()))
                    self.carry_amount[food_idx] = 0.0
                    self.carrying[food_idx] = False
                    self.carry_type[food_idx] = 0

                    # Trophallaxis: nếu đúng lúc có nurse đang chờ sẵn ở
                    # kho, thợ vừa về "mớm" trực tiếp cho nurse thay vì chỉ
                    # đổ vào đống chung - CHỈ là hiệu ứng hình ảnh, số liệu
                    # kho không đổi gì so với trước (nurse vẫn tự lấy hàng
                    # theo đúng chu trình riêng, xem _update_nurses).
                    nurse_present = np.where(
                        self.alive & (self.job == cfg.JOB_NURSE) & (self.state == cfg.STATE_NURSE_AT_STORAGE)
                    )[0]
                    n_pairs = min(len(food_idx), len(nurse_present))
                    for k in range(n_pairs):
                        fi, ni = food_idx[k], nurse_present[k]
                        self._record_trophallaxis(self.x[fi], self.y[fi], self.x[ni], self.y[ni], self.depth[fi])

                    # Không rời phòng ngay - LƯỢN trong kho 1 lúc (như đang
                    # sắp xếp/kiểm tra đồ) rồi quay lại mặt đất kiếm tiếp
                    # (không còn "thành nurse" ngẫu nhiên nữa - chăm ấu
                    # trùng giờ là CHỨC NĂNG CỐ ĐỊNH riêng, xem _update_nurses)
                    self._start_dwell(food_idx, cfg.STATE_UG_TO_SHAFT, room_id=0)

                if len(water_idx) > 0:
                    # Đã tới ĐÚNG bể trữ nước (không phải kho) - đổ nước vào đây
                    self.underground.deposit_water(float(self.carry_amount[water_idx].sum()))
                    self.carry_amount[water_idx] = 0.0
                    self.carry_type[water_idx] = 0
                    self.carrying[water_idx] = False
                    self._start_dwell(water_idx, cfg.STATE_UG_TO_SHAFT, room_id=3)

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
    def _start_dwell(self, idx, next_state, room_id):
        """Cho 1 nhóm kiến bắt đầu LƯỢN trong phòng CỤ THỂ (room_id) một
        khoảng thời gian ngẫu nhiên trước khi tiếp tục hành trình sang
        next_state - để phòng ngầm có hoạt động thật sự thay vì kiến chỉ
        chạm tâm phòng rồi quay đầu ngay. LƯU Ý: phải xác định ĐÚNG phòng
        cụ thể (không chỉ tầng/depth) vì từ khi nhiều phòng dùng chung 1
        tầng (kho+nước, trứng+ấu trùng), chỉ biết depth thôi không đủ để
        biết kiến đang ở phòng nào trong 2 phòng đó."""
        if len(idx) == 0:
            return
        self.state[idx] = cfg.STATE_DWELL
        self.next_state[idx] = next_state
        self.dwell_room_id[idx] = room_id
        self.dwell_ticks[idx] = np.random.randint(
            cfg.DWELL_MIN_TICKS, cfg.DWELL_MAX_TICKS + 1, size=len(idx)
        ).astype(np.int16)

    def _update_dwelling_ants(self):
        mask = self.alive & (self.state == cfg.STATE_DWELL)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        self.dwell_ticks[idx] -= 1

        # Đi lại ngẫu nhiên, chậm, quanh tâm phòng - tách riêng theo TỪNG
        # PHÒNG CỤ THỂ (room_id), KHÔNG PHẢI theo tầng (depth) - vì từ khi
        # nhiều phòng dùng chung 1 tầng, 2 phòng khác nhau có thể cùng depth
        # nhưng tâm khác nhau hẳn.
        for room_id_val in np.unique(self.dwell_room_id[idx]):
            center, radius = self.underground.room_center_and_radius_by_id(int(room_id_val))
            if center is None:
                continue
            sub = idx[self.dwell_room_id[idx] == room_id_val]
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

        # Hết giờ lượn -> tiếp tục hành trình đã định sẵn (next_state)
        done = idx[self.dwell_ticks[idx] <= 0]
        if len(done) > 0:
            self.state[done] = self.next_state[done]

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def _record_trophallaxis(self, x1, y1, x2, y2, depth):
        """Ghi lại 1 khoảnh khắc "mớm mồi" giữa (x1,y1) và (x2,y2) ở tầng
        `depth` để lớp hiển thị vẽ hiệu ứng ngắn - xem trophallaxis_events
        ở __init__. Tự giới hạn số sự kiện lưu cùng lúc để không phình bộ
        nhớ nếu vì lý do gì đó không được dọn dẹp kịp."""
        self.trophallaxis_events.append(
            (float(x1), float(y1), float(x2), float(y2), self.tick_count, int(depth))
        )
        if len(self.trophallaxis_events) > 300:
            self.trophallaxis_events = self.trophallaxis_events[-300:]

    def _wander_in_room(self, idx, center, radius):
        """Đi lại chậm, ngẫu nhiên quanh tâm 1 phòng, KHÔNG đổi trạng thái -
        dùng cho các chức năng LƯU TRÚ VÔ THỜI HẠN tại 1 phòng (nurse chờ ở
        kho, attendant túc trực cạnh chúa/trứng), khác với _start_dwell vốn
        có hẹn giờ CỐ ĐỊNH rồi tự chuyển sang trạng thái khác."""
        if len(idx) == 0:
            return
        self.theta[idx] = self.theta[idx] + np.random.uniform(-0.6, 0.6, len(idx)).astype(np.float32)
        self.x[idx] += np.cos(self.theta[idx]) * cfg.DWELL_SPEED
        self.y[idx] += np.sin(self.theta[idx]) * cfg.DWELL_SPEED
        dx = self.x[idx] - center[0]
        dy = self.y[idx] - center[1]
        dist = np.hypot(dx, dy)
        max_r = radius * cfg.ROOM_WANDER_FACTOR
        over = dist > max_r
        if np.any(over):
            safe_dist = np.where(dist[over] < 1e-6, 1.0, dist[over])
            scale = max_r / safe_dist
            self.x[idx[over]] = center[0] + dx[over] * scale
            self.y[idx[over]] = center[1] + dy[over] * scale
            self.theta[idx[over]] = np.arctan2(-dy[over], -dx[over])

    def _update_nurses(self):
        """Kiến CHUYÊN CHĂM ẤU TRÙNG (self.job == JOB_NURSE): KHÔNG BAO GIỜ
        lên mặt đất - cả đời quanh quẩn giữa Kho thức ăn và Phòng ấu trùng,
        tự lấy thức ăn từ kho (nếu kho còn) mang qua cho ấu trùng ăn, lặp
        lại vô thời hạn. Đây là CHỨC NĂNG RIÊNG, tách biệt hẳn khỏi việc
        thợ (JOB_FORAGER) tha thức ăn từ mặt đất về kho."""
        nurse_mask = self.alive & (self.job == cfg.JOB_NURSE)
        if not np.any(nurse_mask):
            return

        # --- Đang ở kho: lượn chờ, hễ kho còn đủ hàng thì lấy ngay 1 chuyến ---
        at_storage = nurse_mask & (self.state == cfg.STATE_NURSE_AT_STORAGE)
        if np.any(at_storage):
            idx = np.where(at_storage)[0]
            self._wander_in_room(idx, self.underground.storage, cfg.ROOM_RADIUS_STORAGE)
            if self.underground.food_in_nursery < cfg.NURSE_NURSERY_TARGET_STOCK:
                available = int(self.underground.food_in_storage // cfg.NURSE_TRIP_FOOD_AMOUNT)
                take_n = min(len(idx), max(0, available))
            else:
                take_n = 0  # ấu trùng đang đủ ăn - không cần lấy thêm, để
                            # dành thức ăn tích lũy trong kho (cho chúa đẻ
                            # trứng thay vì bị nurse hút hết ngay khi vừa về)
            if take_n > 0:
                go_idx = idx[:take_n]
                self.underground.food_in_storage -= take_n * cfg.NURSE_TRIP_FOOD_AMOUNT
                self.carrying[go_idx] = True
                self.carry_type[go_idx] = 1
                self.depth[go_idx] = self.underground.nursery_depth
                self.x[go_idx] = self.underground.shaft_xy[0]
                self.y[go_idx] = self.underground.shaft_xy[1]
                self.state[go_idx] = cfg.STATE_NURSE_TO_NURSERY

        # --- đang mang thức ăn sang phòng ấu trùng ---
        mask = nurse_mask & (self.state == cfg.STATE_NURSE_TO_NURSERY)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_2d(idx, self.underground.nursery, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                self.underground.deposit_to_nursery(len(arrived))
                self.carrying[arrived] = False
                self.carry_type[arrived] = 0
                # Trophallaxis: mớm cho 1 "ấu trùng" ở ngay gần đó (điểm
                # ngẫu nhiên nhỏ quanh vị trí nurse - không cần khớp chính
                # xác ấu trùng nào, chỉ để hình ảnh "đang mớm" rõ ràng)
                nx, ny = self.underground.nursery
                off_ang = np.random.uniform(0, 2 * np.pi, len(arrived))
                off_rad = np.random.uniform(0.2, 0.6, len(arrived)) * cfg.ROOM_RADIUS_NURSERY
                lx = nx + np.cos(off_ang) * off_rad
                ly = ny + np.sin(off_ang) * off_rad
                for k, a in enumerate(arrived):
                    self._record_trophallaxis(self.x[a], self.y[a], lx[k], ly[k], self.depth[a])
                self.dwell_ticks[arrived] = np.random.randint(
                    cfg.NURSE_IDLE_TICKS_MIN, cfg.NURSE_IDLE_TICKS_MAX + 1, size=len(arrived)
                ).astype(np.int16)
                self.state[arrived] = cfg.STATE_NURSE_AT_NURSERY

        # --- đang "chăm" ở phòng ấu trùng 1 lúc rồi quay lại kho ---
        mask = nurse_mask & (self.state == cfg.STATE_NURSE_AT_NURSERY)
        if np.any(mask):
            idx = np.where(mask)[0]
            self._wander_in_room(idx, self.underground.nursery, cfg.ROOM_RADIUS_NURSERY)
            self.dwell_ticks[idx] -= 1
            done = idx[self.dwell_ticks[idx] <= 0]
            if len(done) > 0:
                self.depth[done] = self.underground.storage_depth
                self.x[done] = self.underground.shaft_xy[0]
                self.y[done] = self.underground.shaft_xy[1]
                self.state[done] = cfg.STATE_NURSE_TO_STORAGE

        # --- đang quay lại kho ---
        mask = nurse_mask & (self.state == cfg.STATE_NURSE_TO_STORAGE)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_2d(idx, self.underground.storage, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                self.state[arrived] = cfg.STATE_NURSE_AT_STORAGE

    def _update_attendants(self):
        """Kiến CHUYÊN CHĂM TRỨNG + KIẾN CHÚA (self.job == JOB_ATTENDANT):
        KHÔNG BAO GIỜ lên mặt đất - túc trực cạnh chúa 1 khoảng thời gian
        rồi đổi qua túc trực cạnh trứng, lặp lại vô thời hạn (mô phỏng vừa
        hầu chúa vừa trông trứng, luân phiên giữa 2 phòng)."""
        mask_all = self.alive & (self.job == cfg.JOB_ATTENDANT)
        if not np.any(mask_all):
            return

        at_queen = mask_all & (self.state == cfg.STATE_ATTENDANT_AT_QUEEN)
        if np.any(at_queen):
            idx = np.where(at_queen)[0]
            self._wander_in_room(idx, self.underground.queen_room, cfg.ROOM_RADIUS_QUEEN)
            self.dwell_ticks[idx] -= 1
            done = idx[self.dwell_ticks[idx] <= 0]
            if len(done) > 0:
                self.depth[done] = self.underground.egg_depth
                self.x[done] = self.underground.shaft_xy[0]
                self.y[done] = self.underground.shaft_xy[1]
                self.state[done] = cfg.STATE_ATTENDANT_TO_EGG

        mask = mask_all & (self.state == cfg.STATE_ATTENDANT_TO_EGG)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_2d(idx, self.underground.egg_room, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                self.dwell_ticks[arrived] = np.random.randint(
                    cfg.ATTENDANT_SWITCH_TICKS_MIN, cfg.ATTENDANT_SWITCH_TICKS_MAX + 1, size=len(arrived)
                ).astype(np.int16)
                self.state[arrived] = cfg.STATE_ATTENDANT_AT_EGG

        at_egg = mask_all & (self.state == cfg.STATE_ATTENDANT_AT_EGG)
        if np.any(at_egg):
            idx = np.where(at_egg)[0]
            self._wander_in_room(idx, self.underground.egg_room, cfg.ROOM_RADIUS_EGG)
            self.dwell_ticks[idx] -= 1
            done = idx[self.dwell_ticks[idx] <= 0]
            if len(done) > 0:
                self.depth[done] = self.underground.queen_depth
                self.x[done] = self.underground.shaft_xy[0]
                self.y[done] = self.underground.shaft_xy[1]
                self.state[done] = cfg.STATE_ATTENDANT_TO_QUEEN

        mask = mask_all & (self.state == cfg.STATE_ATTENDANT_TO_QUEEN)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_2d(idx, self.underground.queen_room, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                # Trophallaxis: attendant vừa quay lại thì "mớm" cho chúa
                # (hình ảnh - chúa không cần "ăn" theo số liệu riêng, việc
                # đẻ trứng vẫn tiêu thụ thẳng từ kho như trước, xem
                # try_consume_for_egg trong world.py)
                qx, qy = self.underground.queen_room
                for a in arrived:
                    self._record_trophallaxis(self.x[a], self.y[a], qx, qy, self.depth[a])
                self.dwell_ticks[arrived] = np.random.randint(
                    cfg.ATTENDANT_SWITCH_TICKS_MIN, cfg.ATTENDANT_SWITCH_TICKS_MAX + 1, size=len(arrived)
                ).astype(np.int16)
                self.state[arrived] = cfg.STATE_ATTENDANT_AT_QUEEN

    # ------------------------------------------------------------------
    def _update_guards(self, enemy, rival=None):
        """Lính gác (self.is_guard): mặc định lượn vô thời hạn trong phòng
        gác cửa (STATE_GUARD_DUTY); nếu có kẻ thù TỰ NHIÊN xuất hiện đủ gần
        lỗ tổ HOẶC quân xâm chiếm của tổ đối thủ đang cướp phá ngay tại tổ
        mình, LAO LÊN mặt đất nghênh chiến (việc gây/nhận sát thương với kẻ
        thù tự nhiên đã được enemy.py tự xử lý; với quân xâm chiếm thì được
        xử lý trong _update_raids của chính tổ đối thủ - lính gác chỉ cần
        CÓ MẶT trên mặt đất gần tổ để tính là "phòng thủ"); hết mối đe dọa
        thì tự quay về đóng quân lại."""
        guard_mask = self.alive & self.is_guard
        if not np.any(guard_mask):
            return

        nest_x, nest_y = self.nest_pos
        threat_natural = enemy is not None and enemy.active and (
            (enemy.x - nest_x) ** 2 + (enemy.y - nest_y) ** 2 < cfg.GUARD_ALERT_RADIUS ** 2
        )
        threat_raid = rival is not None and np.any(rival.alive & (rival.state == cfg.STATE_RAID_LOOT))
        threat_near_nest = threat_natural or threat_raid

        # --- Đóng quân: lượn quanh phòng gác VÔ THỜI HẠN, trừ khi có báo động ---
        duty_mask = guard_mask & (self.state == cfg.STATE_GUARD_DUTY)
        if np.any(duty_mask):
            if threat_near_nest:
                rush_idx = np.where(duty_mask)[0]
                self.layer[rush_idx] = cfg.LAYER_SURFACE
                self.depth[rush_idx] = cfg.LAYER_SURFACE_DEPTH
                self.x[rush_idx] = nest_x
                self.y[rush_idx] = nest_y
                self.state[rush_idx] = cfg.STATE_GUARD_RUSH
            else:
                idx = np.where(duty_mask)[0]
                center, radius = self.underground.room_center_and_radius(cfg.DEPTH_GUARD)
                if center is not None:
                    self.theta[idx] += np.random.uniform(-0.6, 0.6, len(idx)).astype(np.float32)
                    self.x[idx] += np.cos(self.theta[idx]) * cfg.DWELL_SPEED
                    self.y[idx] += np.sin(self.theta[idx]) * cfg.DWELL_SPEED
                    dx = self.x[idx] - center[0]
                    dy = self.y[idx] - center[1]
                    dist = np.hypot(dx, dy)
                    max_r = radius * cfg.ROOM_WANDER_FACTOR
                    over = dist > max_r
                    if np.any(over):
                        safe_dist = np.where(dist[over] < 1e-6, 1.0, dist[over])
                        scale = max_r / safe_dist
                        self.x[idx[over]] = center[0] + dx[over] * scale
                        self.y[idx[over]] = center[1] + dy[over] * scale
                        self.theta[idx[over]] = np.arctan2(-dy[over], -dx[over])

        # --- Đang lao lên nghênh chiến ---
        rush_mask = guard_mask & (self.state == cfg.STATE_GUARD_RUSH)
        if np.any(rush_mask):
            idx = np.where(rush_mask)[0]
            if threat_natural:
                # Kẻ thù tự nhiên di chuyển - phải đuổi theo tận nơi
                prev_x, prev_y = self.x[idx].copy(), self.y[idx].copy()
                self._move_towards_2d(idx, (enemy.x, enemy.y), cfg.GUARD_SPEED)
                self._bounce_walls(idx)
                self._avoid_obstacles(idx, prev_x, prev_y)
            elif threat_raid:
                pass  # quân xâm chiếm tự tìm đến tổ mình - lính gác cứ đứng yên tại tổ để nghênh chiến
            else:
                self.state[idx] = cfg.STATE_GUARD_RETURN  # hết mối đe dọa - rút về

        # --- Đang rút quân về giếng để xuống lại phòng gác ---
        return_mask = guard_mask & (self.state == cfg.STATE_GUARD_RETURN)
        if np.any(return_mask):
            idx = np.where(return_mask)[0]
            prev_x, prev_y = self.x[idx].copy(), self.y[idx].copy()
            dist = self._move_towards_2d(idx, (nest_x, nest_y), cfg.GUARD_SPEED)
            self._bounce_walls(idx)
            self._avoid_obstacles(idx, prev_x, prev_y)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                self.layer[arrived] = cfg.LAYER_UNDERGROUND
                self.depth[arrived] = cfg.DEPTH_GUARD
                self.x[arrived] = self.underground.shaft_xy[0]
                self.y[arrived] = self.underground.shaft_xy[1]
                self.state[arrived] = cfg.STATE_GUARD_DUTY

    # ------------------------------------------------------------------
    def _update_raids(self, rival):
        """Khi kho CẠN KIỆT và đàn thật sự đang đói (is_starving), tổ tự
        cử 1 đội (ưu tiên lính) hành quân sang XÂM CHIẾM tổ đối thủ: giao
        chiến với lính phòng thủ của họ ngay tại tổ, cướp thức ăn mang về
        nếu còn sống. Đây là hành vi đối kháng THẬT giữa 2 đàn, khác với
        việc chỉ cạnh tranh gián tiếp qua tìm thức ăn trên mặt đất."""
        if rival is None:
            return

        self.raid_cooldown = max(0, self.raid_cooldown - 1)

        # --- Phát động đợt xâm chiếm mới nếu đang khan hiếm thức ăn ---
        if self.tick_count % cfg.RAID_CHECK_INTERVAL == 0 and self.raid_cooldown <= 0:
            if self.underground.is_food_scarce():
                eligible = np.where(
                    self.alive
                    & (self.layer == cfg.LAYER_SURFACE)
                    & (self.state == cfg.STATE_SEARCHING)
                    & (~self.carrying)
                )[0]
                if len(eligible) > 0:
                    # ưu tiên cử lính (ROLE_MAJOR) đi trước, thợ thường bù sau
                    order = np.argsort(-(self.role[eligible] == cfg.ROLE_MAJOR).astype(np.int8))
                    party = eligible[order[: cfg.RAID_PARTY_SIZE]]
                    self.state[party] = cfg.STATE_RAID_TO_ENEMY
                    self.raid_loot_ticks[party] = 0
                    self.raid_cooldown = cfg.RAID_COOLDOWN_TICKS

        # --- Đang hành quân tới tổ đối thủ ---
        mask = self.alive & (self.state == cfg.STATE_RAID_TO_ENEMY)
        if np.any(mask):
            idx = np.where(mask)[0]
            prev_x, prev_y = self.x[idx].copy(), self.y[idx].copy()
            rx, ry = rival.nest_pos
            dist = self._move_towards_2d(idx, (rx, ry), cfg.RAID_SPEED)
            self._bounce_walls(idx)
            self._avoid_obstacles(idx, prev_x, prev_y)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD * 3]
            if len(arrived) > 0:
                self.state[arrived] = cfg.STATE_RAID_LOOT

        # --- Đang giao chiến/cướp phá tại tổ đối thủ ---
        mask = self.alive & (self.state == cfg.STATE_RAID_LOOT)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        self.raid_loot_ticks[idx] += 1

        rx, ry = rival.nest_pos
        defenders = np.where(
            rival.alive
            & (rival.layer == cfg.LAYER_SURFACE)
            & ((rival.x - rx) ** 2 + (rival.y - ry) ** 2 < cfg.RAID_KILL_RADIUS ** 2)
        )[0]

        if len(defenders) > 0:
            # --- Quân xâm chiếm hạ lính phòng thủ ---
            is_def_major = rival.role[defenders] == cfg.ROLE_MAJOR
            kill_prob = np.where(
                is_def_major,
                cfg.RAID_ATTACKER_KILL_PROB * cfg.MAJOR_DEFENSE_FACTOR,
                cfg.RAID_ATTACKER_KILL_PROB,
            )
            kill_roll = np.random.uniform(0, 1, len(defenders))
            killed_defenders = defenders[kill_roll < kill_prob]
            if len(killed_defenders) > 0:
                rival.alive[killed_defenders] = False
                rival.underground.total_deaths += len(killed_defenders)
                rival.underground.add_corpse(len(killed_defenders))

            # --- Phòng thủ (lợi thế sân nhà) hạ quân xâm chiếm ---
            is_att_major = self.role[idx] == cfg.ROLE_MAJOR
            def_kill_prob = np.where(
                is_att_major,
                cfg.RAID_DEFENDER_KILL_PROB * cfg.MAJOR_DEFENSE_FACTOR,
                cfg.RAID_DEFENDER_KILL_PROB,
            )
            # Càng ít phòng thủ so với quân xâm chiếm thì tỉ lệ gây sát
            # thương ngược lại càng thấp (không đủ người để chống trả)
            def_kill_prob = def_kill_prob * min(1.0, len(defenders) / max(1, len(idx)))
            kill_roll2 = np.random.uniform(0, 1, len(idx))
            killed_mask = kill_roll2 < def_kill_prob
            killed_attackers = idx[killed_mask]
            if len(killed_attackers) > 0:
                self.alive[killed_attackers] = False
                self.underground.total_deaths += len(killed_attackers)
                self.underground.add_corpse(len(killed_attackers))
                idx = idx[~killed_mask]
                if len(idx) == 0:
                    return

        # --- Cướp thức ăn: rút dần từ kho đối thủ, chia đều quân còn sống ---
        if rival.underground.food_in_storage > 0.01:
            steal_total = min(rival.underground.food_in_storage, cfg.RAID_STEAL_PER_TICK * len(idx))
            rival.underground.food_in_storage -= steal_total
            self.underground.total_food_looted += steal_total
            per_ant = steal_total / len(idx)
            self.carry_amount[idx] += per_ant
            self.carrying[idx] = True
            self.carry_type[idx] = 1
            self.carry_food_type[idx] = cfg.FOOD_TYPE_SEED  # nhãn cho thức ăn cướp được

        # --- Rút quân: đã cướp đủ lâu, HOẶC kho đối thủ đã cạn hẳn ---
        done = idx[
            (self.raid_loot_ticks[idx] >= cfg.RAID_MAX_LOOT_TICKS)
            | (rival.underground.food_in_storage <= 0.01)
        ]
        if len(done) > 0:
            self.raid_loot_ticks[done] = 0
            looted = done[self.carrying[done]]
            empty_handed = done[~self.carrying[done]]
            if len(looted) > 0:
                self.state[looted] = cfg.STATE_RETURNING  # có mồi - về nộp kho như bình thường
            if len(empty_handed) > 0:
                self.state[empty_handed] = cfg.STATE_SEARCHING  # tay không - đi tìm ăn tiếp luôn

    # ------------------------------------------------------------------
    def _update_lifecycle(self):
        """Tăng tuổi, tính nguy cơ chết (già/đói), và xử lý sinh sản.

        LƯU Ý QUAN TRỌNG (từng là 1 lỗi tiềm ẩn khi thêm giai đoạn lập
        tổ): hàm này KHÔNG ĐƯỢC return sớm khi population=0 nữa - lúc mới
        lập tổ, đàn CHÍNH XÁC có 0 kiến (chúa không phải 1 phần tử trong
        self.alive), nhưng phần ĐẺ TRỨNG ở cuối hàm vẫn phải chạy (đẻ bằng
        năng lượng dự trữ của chúa) thì lứa thợ đầu tiên mới có cơ hội ra
        đời. Phần tăng tuổi/chết vì già-đói-khát ở trên vẫn bỏ qua an toàn
        khi không có ai sống (không có gì để tính)."""
        alive_idx = np.where(self.alive)[0]
        if len(alive_idx) > 0:
            self.age[alive_idx] += 1

            # --- Chết vì già: xác suất tăng dần sau MAX_AGE_TICKS ---
            age = self.age[alive_idx]
            over = np.clip(age - cfg.MAX_AGE_TICKS, 0, None)
            old_age_prob = np.where(
                over > 0,
                cfg.OLD_AGE_DEATH_RATE * (1.0 + over / cfg.OLD_AGE_DEATH_GROWTH),
                0.0,
            )

            # --- Chết vì đói/khát: áp dụng đều cho cả đàn khi thiếu ăn/
            # nước lâu - BỎ QUA HẲN trong lúc đang lập tổ (self.founding_
            # phase): nền kinh tế kho/nurse thức ăn chưa vận hành (chưa có
            # ai tha mồi về), nếu tính như bình thường thì is_starving()
            # gần như LUÔN True ngay từ đầu (kho=0 từ tick đầu tiên) và sẽ
            # giết ngay lứa nanitic vừa nở - trong khi rủi ro ĐÚNG của giai
            # đoạn này phải đến từ năng lượng dự trữ của chúa cạn kiệt
            # (self.queen_energy), không phải từ kho thức ăn chưa kịp có.
            if self.founding_phase:
                starve_prob = 0.0
                dehydrate_prob = 0.0
            else:
                starve_prob = cfg.STARVATION_DEATH_RATE if self.underground.is_starving() else 0.0
                dehydrate_prob = cfg.DEHYDRATION_DEATH_RATE if self.underground.is_dehydrated() else 0.0

            death_prob = 1.0 - (1.0 - old_age_prob) * (1.0 - starve_prob) * (1.0 - dehydrate_prob)
            rolls = np.random.uniform(0, 1, len(alive_idx))
            died = alive_idx[rolls < death_prob]
            if len(died) > 0:
                self.alive[died] = False
                self.underground.total_deaths += len(died)
                self.underground.add_corpse(len(died))

        # --- Đẻ trứng ---
        if self.founding_phase:
            self._update_founding_egg_laying()
        elif self.tick_count % cfg.EGG_LAY_INTERVAL == 0:
            # Chúa thử đẻ 1 trứng mới theo chu kỳ, cần đủ thức ăn + nước
            # TRONG KHO, VÀ kho phải dư ra 1 khoản dự trữ an toàn tỉ lệ với
            # sĩ số đàn hiện tại (EGG_MIN_STORAGE_BUFFER_PER_ANT) - đây là
            # "phanh" mật độ dân số: đàn càng đông, ngưỡng an toàn để đẻ
            # tiếp càng cao, tự nhiên hãm sinh sản lại TRƯỚC KHI kho cạn
            # hẳn, thay vì cứ đẻ tới khi kho về 0 rồi cả đàn chết đói hàng
            # loạt cùng lúc. Trứng được ủ trong PHÒNG TRỨNG (_update_eggs)
            # rồi mới "chuyển" qua phòng ấu trùng để lớn lên thật sự.
            free_egg_slots = np.where(~self.egg_active)[0]
            has_ant_capacity = np.any(~self.alive)
            population = len(alive_idx)
            safety_reserve = population * cfg.EGG_MIN_STORAGE_BUFFER_PER_ANT
            enough_reserve = self.underground.food_in_storage >= cfg.EGG_FOOD_COST + safety_reserve
            if len(free_egg_slots) > 0 and has_ant_capacity and enough_reserve:
                got_food = self.underground.try_consume_for_egg(
                    cfg.EGG_FOOD_COST, cfg.EGG_WATER_COST
                )
                if got_food:
                    slot = free_egg_slots[0]
                    self.egg_active[slot] = True
                    self.egg_growth[slot] = 0.0

    def _update_founding_egg_laying(self):
        """Nhánh đẻ trứng RIÊNG cho giai đoạn lập tổ - dùng NĂNG LƯỢNG DỰ
        TRỮ của chúa (self.queen_energy) thay vì kho thức ăn (chưa tồn
        tại lúc này). Chạy MỖI TICK (không theo chu kỳ EGG_LAY_INTERVAL
        như bình thường) vì tần suất đẻ ở đây phải khác hẳn - lứa đầu chỉ
        cần vài trứng là đủ, không cần nhịp đẻ liên tục dài hạn như 1 đàn
        đã ổn định. Đồng thời đây là nơi DUY NHẤT kiểm tra điều kiện
        CHUYỂN GIAO: đủ FOUNDING_NANITIC_TARGET thợ đầu tiên còn sống thì
        coi như lập tổ THÀNH CÔNG, tắt hẳn founding_phase - từ tick sau,
        _update_lifecycle() tự động quay về nhánh đẻ trứng bình thường
        (cần kho thức ăn), không cần thêm code chuyển đổi gì khác vì mọi
        nơi khác trong file này đều đọc cờ self.founding_phase trực tiếp.
        """
        # Dự trữ luôn hao mòn dần MỖI TICK, kể cả khi không đẻ trứng tick
        # này - đúng thực tế: chúa vẫn "sống" bằng mỡ/cơ cánh suốt cả giai
        # đoạn, không chỉ lúc đẻ.
        self.queen_energy = max(0.0, self.queen_energy - cfg.QUEEN_ENERGY_DECAY_PER_TICK)

        population = int(np.sum(self.alive))
        if population >= cfg.FOUNDING_NANITIC_TARGET:
            self.founding_phase = False
            return

        if self.tick_count % cfg.EGG_LAY_INTERVAL == 0:
            free_egg_slots = np.where(~self.egg_active)[0]
            has_ant_capacity = np.any(~self.alive)
            if (len(free_egg_slots) > 0 and has_ant_capacity
                    and self.queen_energy >= cfg.QUEEN_ENERGY_PER_EGG):
                self.queen_energy -= cfg.QUEEN_ENERGY_PER_EGG
                slot = free_egg_slots[0]
                self.egg_active[slot] = True
                self.egg_growth[slot] = 0.0

    def _update_eggs(self):
        """Trứng trong PHÒNG TRỨNG lớn dần theo THỜI GIAN (không cần ăn) -
        đủ lớn thì "chuyển" sang phòng ấu trùng thành 1 ấu trùng thật (nếu
        còn chỗ trống trong phòng ấu trùng; nếu chưa có chỗ, trứng chờ đã
        nở nhưng chưa chuyển được, giữ growth ở mức tối đa)."""
        active = np.where(self.egg_active)[0]
        if len(active) == 0:
            return
        self.egg_growth[active] = np.clip(
            self.egg_growth[active] + cfg.EGG_INCUBATE_PER_TICK, 0.0, 1.0
        )
        hatched = active[self.egg_growth[active] >= 1.0]
        if len(hatched) == 0:
            return
        free_larva_slots = np.where(~self.larva_active)[0]
        n_move = min(len(hatched), len(free_larva_slots))
        if n_move == 0:
            return  # trứng đã nở nhưng phòng ấu trùng đầy - chờ có chỗ trống
        move_eggs = hatched[:n_move]
        move_slots = free_larva_slots[:n_move]
        self.egg_active[move_eggs] = False
        self.egg_growth[move_eggs] = 0.0
        self.larva_active[move_slots] = True
        self.larva_growth[move_slots] = 0.0

    def _update_larvae(self):
        """Ấu trùng ĐANG CÓ trong phòng ấu trùng lớn lên dần bằng cách ăn
        thức ăn nurse mang tới (food_in_nursery) - hết thức ăn ở đó thì lớn
        rất chậm thay vì dừng hẳn. Ấu trùng đủ lớn (growth >= 1.0) KHÔNG nở
        thành kiến ngay - mà HÓA NHỘNG, "chuyển" qua phòng nhộng (nếu còn
        chỗ trống; nếu chưa có chỗ, ấu trùng chờ đã đủ lớn nhưng chưa hóa
        nhộng được, giữ growth ở mức tối đa) - xem _update_pupae để biết
        giai đoạn nhộng thật sự nở thành kiến thế nào."""
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
        free_pupa_slots = np.where(~self.pupa_active)[0]
        n_move = min(len(mature), len(free_pupa_slots))
        if n_move == 0:
            return  # đã đủ lớn nhưng phòng nhộng đầy - chờ có chỗ trống
        move_larvae = mature[:n_move]
        move_slots = free_pupa_slots[:n_move]
        self.larva_active[move_larvae] = False
        self.larva_growth[move_larvae] = 0.0
        self.pupa_active[move_slots] = True
        self.pupa_growth[move_slots] = 0.0

    def _update_pupae(self):
        """Nhộng trong PHÒNG NHỘNG "chín" dần theo THỜI GIAN (KHÔNG cần ăn
        - đúng thực tế, nhộng không ăn, chỉ nằm yên biến thái) - chín đủ
        (growth >= 1.0) mới thật sự "nở" thành 1 kiến thợ mới, NẾU còn chỗ
        trống trong đàn (chưa chạm trần max_ants) - nếu chưa có chỗ, nhộng
        chờ (growth giữ ở mức tối đa) tới khi có kiến khác chết đi, nhường
        chỗ. Đây là bước cuối cùng của vòng đời 4 giai đoạn: trứng -> ấu
        trùng -> NHỘNG -> kiến trưởng thành."""
        active = np.where(self.pupa_active)[0]
        if len(active) == 0:
            return
        self.pupa_growth[active] = np.clip(
            self.pupa_growth[active] + cfg.PUPA_MATURE_PER_TICK, 0.0, 1.0
        )
        mature = active[self.pupa_growth[active] >= 1.0]
        if len(mature) == 0:
            return
        dead_slots = np.where(~self.alive)[0]
        n_hatch = min(len(mature), len(dead_slots))
        if n_hatch == 0:
            return  # đủ chín nhưng đàn đã đầy chỗ - chờ tới khi có chỗ trống
        hatch_pupae = mature[:n_hatch]
        new_ants = dead_slots[:n_hatch]
        self.pupa_active[hatch_pupae] = False
        self.pupa_growth[hatch_pupae] = 0.0
        self._spawn_new_ants(new_ants)
        self.underground.total_births += n_hatch

    def _spawn_new_ants(self, idx):
        """Tái sử dụng các ô đã chết để tạo kiến mới. Lính gác mới thì đi
        thẳng xuống đóng quân ở phòng gác cửa; nurse/attendant mới cũng đi
        thẳng tới đúng phòng của mình (kho / phòng chúa) - CẢ HAI ĐỀU
        KHÔNG BAO GIỜ trồi lên mặt đất. Chỉ thợ kiếm ăn (JOB_FORAGER) và
        lính thường (không phải gác) mới xuất hiện ở phòng chúa, lượn 1
        lúc (mới sinh, còn quây quần quanh chúa) rồi tự đi lên mặt đất qua
        giếng."""
        self.alive[idx] = True
        self.age[idx] = 0.0
        self.carrying[idx] = False
        self.carry_type[idx] = 0
        self.carry_amount[idx] = 0.0
        self.role[idx] = (np.random.uniform(0, 1, len(idx)) < cfg.MAJOR_WORKER_RATIO).astype(np.int8)
        self.is_guard[idx] = (self.role[idx] == cfg.ROLE_MAJOR) & (
            np.random.uniform(0, 1, len(idx)) < cfg.GUARD_SHARE_OF_MAJORS
        )
        self.theta[idx] = np.random.uniform(0, 2 * np.pi, len(idx))

        # Chức năng cố định cho thợ nhỏ mới sinh (xem __init__ để biết lý
        # do có ngưỡng dân số tối thiểu mới bắt đầu chuyên môn hóa)
        self.job[idx] = cfg.JOB_FORAGER
        current_population = int(np.sum(self.alive))  # đã cộng idx (alive[idx]=True ở trên)
        if current_population >= cfg.JOB_SPECIALIZATION_MIN_POPULATION:
            job_roll = np.random.uniform(0, 1, len(idx))
            is_minor = self.role[idx] == cfg.ROLE_MINOR
            self.job[idx[is_minor & (job_roll < cfg.JOB_NURSE_RATIO)]] = cfg.JOB_NURSE
            self.job[idx[is_minor & (job_roll >= cfg.JOB_NURSE_RATIO) &
                          (job_roll < cfg.JOB_NURSE_RATIO + cfg.JOB_ATTENDANT_RATIO)]] = cfg.JOB_ATTENDANT

        guard_idx = idx[self.is_guard[idx]]
        nurse_idx = idx[self.job[idx] == cfg.JOB_NURSE]
        attendant_idx = idx[self.job[idx] == cfg.JOB_ATTENDANT]
        normal_idx = idx[(~self.is_guard[idx]) & (self.job[idx] == cfg.JOB_FORAGER)]

        if len(normal_idx) > 0:
            self.layer[normal_idx] = cfg.LAYER_UNDERGROUND
            self.depth[normal_idx] = self.underground.queen_depth
            qx, qy = self.underground.queen_room
            self.x[normal_idx] = qx
            self.y[normal_idx] = qy
            self._start_dwell(normal_idx, cfg.STATE_UG_TO_SHAFT, room_id=2)

        if len(guard_idx) > 0:
            self.layer[guard_idx] = cfg.LAYER_UNDERGROUND
            self.depth[guard_idx] = cfg.DEPTH_GUARD
            self.x[guard_idx] = self.underground.shaft_xy[0]
            self.y[guard_idx] = self.underground.shaft_xy[1]
            self.state[guard_idx] = cfg.STATE_GUARD_DUTY

        if len(nurse_idx) > 0:
            self.layer[nurse_idx] = cfg.LAYER_UNDERGROUND
            self.depth[nurse_idx] = self.underground.storage_depth
            self.x[nurse_idx] = self.underground.storage[0]
            self.y[nurse_idx] = self.underground.storage[1]
            self.state[nurse_idx] = cfg.STATE_NURSE_AT_STORAGE

        if len(attendant_idx) > 0:
            self.layer[attendant_idx] = cfg.LAYER_UNDERGROUND
            self.depth[attendant_idx] = self.underground.queen_depth
            self.x[attendant_idx] = self.underground.queen_room[0]
            self.y[attendant_idx] = self.underground.queen_room[1]
            self.state[attendant_idx] = cfg.STATE_ATTENDANT_AT_QUEEN
            self.dwell_ticks[attendant_idx] = np.random.randint(
                cfg.ATTENDANT_SWITCH_TICKS_MIN, cfg.ATTENDANT_SWITCH_TICKS_MAX + 1, size=len(attendant_idx)
            ).astype(np.int16)

    # ------------------------------------------------------------------
    def counts(self):
        """Trả về dict thống kê nhanh cho bảng UI."""
        alive = self.alive
        is_minor = self.role == cfg.ROLE_MINOR
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
            "egg_count": int(np.sum(self.egg_active)),
            "pupa_count": int(np.sum(self.pupa_active)),
            "corpse_count": self.underground.corpse_count,
            "guards_on_duty": int(np.sum(alive & self.is_guard & (self.state == cfg.STATE_GUARD_DUTY))),
            "guards_total": int(np.sum(alive & self.is_guard)),
            "total_food_looted": self.underground.total_food_looted,
            "raiders_out": int(np.sum(alive & (
                (self.state == cfg.STATE_RAID_TO_ENEMY) | (self.state == cfg.STATE_RAID_LOOT)
            ))),
            "foragers_total": int(np.sum(alive & (~self.is_guard) & (
                (self.role == cfg.ROLE_MAJOR) | (is_minor & (self.job == cfg.JOB_FORAGER))
            ))),
            "nurses_total": int(np.sum(alive & is_minor & (self.job == cfg.JOB_NURSE))),
            "attendants_total": int(np.sum(alive & is_minor & (self.job == cfg.JOB_ATTENDANT))),
        }
