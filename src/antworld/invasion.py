"""Đàn kiến NGOẠI LAI - xuất hiện theo đợt từ rìa bản đồ (KHÔNG có tổ/nhà
riêng, không sinh sản, không kiếm ăn tự nhiên như 1 đàn thật), kéo về tổ
của người chơi để CƯỚP PHÁ rồi rút lui - thay cho việc nuôi song song 1 tổ
đối thủ cố định như bản trước.

Vòng đời 1 đợt xâm nhập:
    xuất hiện rìa bản đồ -> hành quân tới lỗ tổ -> giao chiến với lính gác
    (nếu có) ngay tại cửa hang -> nếu vượt qua, chia quân xuống hầm cướp
    phá kho thức ăn VÀ phòng trứng/ấu trùng -> rút lui mang theo chiến
    lợi phẩm (hoặc bị đánh bại hoàn toàn nếu lính gác đủ mạnh).

Tần suất VÀ quy mô mỗi đợt tăng dần theo thời gian (xem _schedule_next_wave)
- càng chơi lâu, tổ càng lớn thì áp lực phòng thủ càng cao, đúng tinh thần
"phải liên tục đầu tư vào lính gác" thay vì có thể lơ là sau khi đã ổn định.

Cấu trúc mảng dữ liệu (numpy, cấp phát sẵn cfg.INVASION_MAX_SWARM_SIZE chỗ)
CỐ TÌNH đặt tên trùng với các field mà render_surface.draw_ants() cần đọc
(alive, x, y, theta, carrying, role, is_guard, job, is_nanitic, state,
depth) - để có thể truyền thẳng đối tượng InvasionManager vào draw_ants()
y hệt như 1 AntColony thật, tái dùng toàn bộ code vẽ kiến (xoay hướng,
đổi sprite lúc tha mồi, cỡ lính to hơn thợ...) mà không phải viết lại."""
import numpy as np
from . import config as cfg

# --- Trạng thái riêng của quân xâm nhập (khác hẳn STATE_* của AntColony -
# 1 đàn xâm nhập không có kho/ấu trùng/vòng đời riêng nên không dùng chung
# bộ trạng thái đó) ---
INV_APPROACH = 0         # trên mặt đất, đang hành quân tới lỗ tổ
INV_FIGHT_ENTRANCE = 1   # đang giao chiến với lính gác ngay tại cửa hang
INV_DESCEND = 2          # đã vượt qua cửa hang, đang di chuyển xuống mục
                          # tiêu dưới hầm (kho HOẶC phòng trứng/ấu trùng)
INV_RAID_STORAGE = 3     # đang cướp phá kho thức ăn
INV_RAID_BROOD = 4       # đang cướp phá phòng trứng/ấu trùng
INV_RETREAT_UG = 5       # đang rút lui, còn dưới hầm, hướng về giếng
INV_RETREAT_SURFACE = 6  # đã lên mặt đất, đang chạy ra khỏi bản đồ


class InvasionManager:
    def __init__(self):
        n = cfg.INVASION_MAX_SWARM_SIZE
        self.alive = np.zeros(n, dtype=bool)
        self.x = np.zeros(n, dtype=np.float32)
        self.y = np.zeros(n, dtype=np.float32)
        self.theta = np.zeros(n, dtype=np.float32)
        self.layer = np.zeros(n, dtype=np.int8)   # 0=mặt đất, 1=dưới hầm
        self.depth = np.zeros(n, dtype=np.int8)   # khớp quy ước DEPTH_* của AntColony
        self.state = np.zeros(n, dtype=np.int8)
        self.carrying = np.zeros(n, dtype=bool)
        self.target_room = np.zeros(n, dtype=np.int8)  # room_id đang nhắm tới (0=kho, 1=au trung, 4=trung)
        self.loot_ticks = np.zeros(n, dtype=np.int32)
        # Các field còn lại CHỈ để tương thích draw_ants() - quân xâm nhập
        # không phân vai/chức năng thật như 1 đàn thật, nhưng vẫn cần các
        # mảng này tồn tại (toàn bộ False/0, trừ role: ngẫu nhiên 1 phần
        # "to con" hơn cho có sự đa dạng, xem _spawn_wave).
        self.role = np.zeros(n, dtype=np.int8)
        self.is_guard = np.zeros(n, dtype=bool)
        self.job = np.zeros(n, dtype=np.int8)
        self.is_nanitic = np.zeros(n, dtype=bool)
        # Pha bước chân/animation - cùng cơ chế với AntColony.anim_phase
        # (tăng theo quãng đường DI CHUYỂN THẬT mỗi tick, xem update() bên
        # dưới), để quân xâm lược cũng có dáng đi/sprite đúng nhịp thay vì
        # chạy vô điều kiện theo frame_counter toàn cục.
        self.anim_phase = np.zeros(n, dtype=np.float32)

        self.active = False          # đang có đợt nào diễn ra không (để HUD/toast biết)
        self.auto_spawn_enabled = True  # BẬT/TẮT bằng nút trên thanh công cụ
                                         # (xem GameState.toggle_invasion_spawn) -
                                         # TẮT thì KHÔNG BAO GIỜ có đợt xâm
                                         # nhập mới nào xuất hiện nữa, đợt
                                         # đang diễn ra (nếu có) vẫn tiếp
                                         # tục cho hết như bình thường.
        self.wave_number = 0
        self.entrance_fight_ticks = 0
        self.tick_count = 0
        self.total_food_stolen = 0.0
        self.total_brood_stolen = 0
        self.total_invaders_killed = 0
        self.total_guards_killed_by_invasion = 0
        self.next_wave_tick = cfg.INVASION_FIRST_WAVE_TICK
        self.next_wave_interval = cfg.INVASION_BASE_INTERVAL_TICKS
        self.next_wave_size = cfg.INVASION_BASE_SWARM_SIZE
        self.spawn_edge_xy = (0.0, 0.0)   # nơi đợt hiện tại xuất hiện - lưu
                                           # lại để rút lui đúng hướng cũ

        # --- Đường hành quân THẬT của cả đợt (tính 1 LẦN cho cả wave lúc
        # vừa xuất hiện, dùng chung cho MỌI quân trong đợt vì tất cả đều
        # xuất phát gần cùng 1 điểm và cùng nhắm 1 đích - lỗ tổ) - xem
        # _spawn_wave()/_follow_wave_path(). Trước đây quân xâm lược đi
        # THẲNG 1 đường kẻ tới lỗ tổ, XUYÊN QUA đá/nước như không hề tồn
        # tại - nghĩa là xây tường đá phòng thủ (dù kỹ thuật đặt được)
        # KHÔNG HỀ có tác dụng cản đường xâm lược, chỉ cản được kiến nhà
        # mình đi kiếm ăn. Giờ quân xâm lược dùng CHUNG hệ thống
        # visibility-graph pathfinding với kiến thật (colony.pathfinder),
        # nên phải né đá/nước y hệt kiến nhà - biến việc xây tường đá
        # quanh tổ thành 1 chiến thuật phòng thủ THẬT SỰ có tác dụng (bịt
        # bớt hướng tiếp cận, ép địch đi vòng, kéo dài thời gian tiếp cận
        # để lính gác có thêm thời gian phản ứng/tăng viện).
        self.wave_path_x = np.zeros(cfg.PATH_MAX_WAYPOINTS, dtype=np.float32)
        self.wave_path_y = np.zeros(cfg.PATH_MAX_WAYPOINTS, dtype=np.float32)
        self.wave_path_len = 0
        self.path_idx = np.zeros(n, dtype=np.int16)      # ~ tiến vào tổ
        self.retreat_path_idx = np.zeros(n, dtype=np.int16)  # ~ rút lui ra

        # Animation: nhấp nháy/rung khi đang giao chiến tại cửa hang - xem
        # cfg.HIT_FLASH_DURATION_TICKS, decay trong update() bên dưới.
        self.combat_flash_ticks = np.zeros(n, dtype=np.int16)

    # ------------------------------------------------------------------
    def update(self, colony):
        """colony: AntColony của người chơi (mục tiêu DUY NHẤT - không còn
        khái niệm 2 tổ đối xứng như raid cũ)."""
        self.tick_count += 1
        self.combat_flash_ticks = np.maximum(0, self.combat_flash_ticks - 1).astype(np.int16)

        if not self.active:
            if self.auto_spawn_enabled and cfg.INVASION_ENABLED and self.tick_count >= self.next_wave_tick:
                self._spawn_wave(colony)
            return

        prev_x = self.x.copy()
        prev_y = self.y.copy()

        self._update_approach(colony)
        self._update_fight_entrance(colony)
        self._update_descend(colony)
        self._update_raid_storage(colony)
        self._update_raid_brood(colony)
        self._update_retreat_ug(colony)
        self._update_retreat_surface(colony)

        # Xem giải thích cơ chế trong AntColony.update() - pha bước chân
        # gắn với quãng đường DI CHUYỂN THẬT trong tick này.
        moved_dist = np.hypot(self.x - prev_x, self.y - prev_y)
        self.anim_phase = (
            self.anim_phase + moved_dist * cfg.ANIM_PHASE_DISTANCE_SCALE
        ).astype(np.float32) % (2 * np.pi)

        if not np.any(self.alive):
            self.active = False
            self._schedule_next_wave()

    # ------------------------------------------------------------------
    def _schedule_next_wave(self):
        """Đợt SAU sẽ đông hơn VÀ tới sớm hơn - áp lực tăng dần theo thời
        gian, đúng yêu cầu thiết kế (không cố định mãi mãi)."""
        self.wave_number += 1
        self.next_wave_interval = max(
            cfg.INVASION_INTERVAL_MIN_TICKS,
            self.next_wave_interval - cfg.INVASION_INTERVAL_DECAY_PER_WAVE,
        )
        self.next_wave_tick = self.tick_count + self.next_wave_interval
        self.next_wave_size = min(
            cfg.INVASION_MAX_SWARM_SIZE,
            int(round(self.next_wave_size + cfg.INVASION_SWARM_GROWTH_PER_WAVE)),
        )

    def _spawn_wave(self, colony):
        n = min(self.next_wave_size, cfg.INVASION_MAX_SWARM_SIZE)
        self.alive[:n] = True
        self.alive[n:] = False

        # Xuất hiện ở 1 ĐIỂM ngẫu nhiên trên rìa bản đồ (không phải từ 1 tổ
        # nào cả) - cả đợt tụ tập gần điểm đó rồi cùng hành quân vào.
        edge = np.random.randint(0, 4)
        g = cfg.GRID_SIZE
        if edge == 0:
            ex, ey = np.random.uniform(0, g), 0.0
        elif edge == 1:
            ex, ey = np.random.uniform(0, g), float(g)
        elif edge == 2:
            ex, ey = 0.0, np.random.uniform(0, g)
        else:
            ex, ey = float(g), np.random.uniform(0, g)
        self.spawn_edge_xy = (ex, ey)

        idx = np.where(self.alive)[0]
        jitter = np.random.uniform(-1.5, 1.5, (len(idx), 2))
        self.x[idx] = ex + jitter[:, 0]
        self.y[idx] = ey + jitter[:, 1]
        self.theta[idx] = 0.0
        self.layer[idx] = cfg.LAYER_SURFACE
        self.depth[idx] = cfg.LAYER_SURFACE_DEPTH
        self.state[idx] = INV_APPROACH
        self.carrying[idx] = False
        self.loot_ticks[idx] = 0
        # 1 phần "to con" hơn (ROLE_MAJOR) cho có đa dạng hình ảnh + khớp
        # công thức sát thương (dùng chung MAJOR_DEFENSE_FACTOR như raid cũ)
        self.role[idx] = (np.random.uniform(0, 1, len(idx)) < 0.35).astype(np.int8)
        self.is_guard[idx] = False
        self.job[idx] = cfg.JOB_FORAGER
        self.is_nanitic[idx] = False
        # Chia mục tiêu: ~55% đánh kho, ~45% đánh trứng/ấu trùng - cả 2 mục
        # tiêu đều bị đánh CÙNG 1 đợt (không phải chọn ngẫu nhiên 1 trong 2
        # cho CẢ đợt) để luôn có cả 2 loại thiệt hại mỗi lần bị xâm nhập.
        to_storage = np.random.uniform(0, 1, len(idx)) < 0.55
        self.target_room[idx[to_storage]] = 0  # Kho thức ăn
        brood_idx = idx[~to_storage]
        # Trong nhóm đánh brood, chia tiếp ngẫu nhiên giữa phòng trứng (4)
        # và phòng ấu trùng (1) - cướp/phá CẢ HAI loại như yêu cầu.
        to_egg = np.random.uniform(0, 1, len(brood_idx)) < 0.5
        self.target_room[brood_idx[to_egg]] = 4
        self.target_room[brood_idx[~to_egg]] = 1

        # Tính SẴN 1 đường hành quân THẬT (né đá/nước, xem giải thích ở
        # __init__) dùng chung cho cả đợt - dùng ĐÚNG pathfinder của đàn
        # kiến nhà (colony.pathfinder) để bảo đảm né vật cản NHẤT QUÁN
        # với cách kiến nhà tự đi lại, không cần dựng thêm 1 bộ pathfinder
        # riêng tốn bộ nhớ. Nếu vì lý do nào đó không tìm được đường (vd
        # tổ bị vây kín hoàn toàn bởi đá - trường hợp hiếm, người chơi tự
        # dựng "pháo đài" quá kín), rơi về đi thẳng như bản cũ
        # (wave_path_len=0 báo cho _update_approach biết mà dùng
        # _move_towards như trước).
        path = colony.pathfinder.find_path(self.spawn_edge_xy, colony.nest_pos)
        if path:
            path = path[: cfg.PATH_MAX_WAYPOINTS]
            for k, (wx, wy) in enumerate(path):
                self.wave_path_x[k] = wx
                self.wave_path_y[k] = wy
            self.wave_path_len = len(path)
        else:
            self.wave_path_len = 0
        self.path_idx[idx] = 0
        self.retreat_path_idx[idx] = 0

        self.active = True
        self.entrance_fight_ticks = 0

    def force_spawn_wave(self, colony, size=None):
        """Người chơi/test chủ động phát động 1 đợt ngay lập tức."""
        if size is not None:
            self.next_wave_size = size
        self._spawn_wave(colony)

    # ------------------------------------------------------------------
    def _move_towards(self, idx, target_xy, speed):
        tx, ty = target_xy
        dx = tx - self.x[idx]
        dy = ty - self.y[idx]
        dist = np.hypot(dx, dy)
        self.theta[idx] = np.arctan2(dy, dx)
        step = np.minimum(dist, speed)
        safe = np.where(dist < 1e-6, 1.0, dist)
        self.x[idx] += dx / safe * step
        self.y[idx] += dy / safe * step
        return dist

    def _follow_wave_path(self, idx, speed):
        """Di chuyển theo đường hành quân THẬT của cả đợt (self.wave_path_*
        - xem __init__/_spawn_wave), NÉ đá/nước thay vì xuyên thẳng qua.
        Mỗi quân tự tiến theo waypoint hiện tại của RIÊNG nó (self.path_idx)
        trong cùng 1 danh sách waypoint dùng chung cho cả đợt - vector hóa
        toàn bộ (numpy fancy indexing) giống hệt kỹ thuật
        AntColony._follow_paths() trong ants.py.

        Trả về khoảng cách THỰC TỚI ĐÍCH CUỐI CÙNG (lỗ tổ, không phải tới
        waypoint hiện tại) - để nơi gọi biết khi nào THẬT SỰ đã tới nơi."""
        last = max(self.wave_path_len - 1, 0)
        cur_wp = np.clip(self.path_idx[idx], 0, last).astype(np.int64)
        tx = self.wave_path_x[cur_wp]
        ty = self.wave_path_y[cur_wp]
        dx = tx - self.x[idx]
        dy = ty - self.y[idx]
        dist_wp = np.hypot(dx, dy)
        self.theta[idx] = np.arctan2(dy, dx)
        step = np.minimum(dist_wp, speed)
        safe = np.where(dist_wp < 1e-6, 1.0, dist_wp)
        self.x[idx] += dx / safe * step
        self.y[idx] += dy / safe * step

        not_last = cur_wp < last
        reached_wp = (dist_wp < cfg.WAYPOINT_ARRIVE_THRESHOLD) & not_last
        if np.any(reached_wp):
            ridx = idx[reached_wp]
            self.path_idx[ridx] = (self.path_idx[ridx] + 1).astype(np.int16)

        gx, gy = self.wave_path_x[last], self.wave_path_y[last]
        return np.hypot(gx - self.x[idx], gy - self.y[idx])

    def _follow_wave_path_reverse(self, idx, speed):
        """Giống _follow_wave_path() nhưng đi NGƯỢC LẠI (từ tổ ra rìa bản
        đồ) - dùng cho lúc RÚT LUI (INV_RETREAT_SURFACE), tự dùng
        self.retreat_path_idx riêng (không đụng self.path_idx của lượt
        tiến vào) để cùng 1 quân có thể tiến-rồi-lui trong cùng 1 đợt mà
        không cần tính lại đường lần 2."""
        last = max(self.wave_path_len - 1, 0)
        cur_wp = np.clip(last - self.retreat_path_idx[idx], 0, last).astype(np.int64)
        tx = self.wave_path_x[cur_wp]
        ty = self.wave_path_y[cur_wp]
        dx = tx - self.x[idx]
        dy = ty - self.y[idx]
        dist_wp = np.hypot(dx, dy)
        self.theta[idx] = np.arctan2(dy, dx)
        step = np.minimum(dist_wp, speed)
        safe = np.where(dist_wp < 1e-6, 1.0, dist_wp)
        self.x[idx] += dx / safe * step
        self.y[idx] += dy / safe * step

        not_last = cur_wp > 0
        reached_wp = (dist_wp < cfg.WAYPOINT_ARRIVE_THRESHOLD) & not_last
        if np.any(reached_wp):
            ridx = idx[reached_wp]
            self.retreat_path_idx[ridx] = (self.retreat_path_idx[ridx] + 1).astype(np.int16)

        gx, gy = self.wave_path_x[0], self.wave_path_y[0]
        return np.hypot(gx - self.x[idx], gy - self.y[idx])

    def _update_approach(self, colony):
        mask = self.alive & (self.state == INV_APPROACH)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        if self.wave_path_len > 1:
            dist = self._follow_wave_path(idx, cfg.INVASION_SPEED)
        else:
            nx, ny = colony.nest_pos
            dist = self._move_towards(idx, (nx, ny), cfg.INVASION_SPEED)
        arrived = idx[dist < cfg.ARRIVE_THRESHOLD * 3]
        if len(arrived) == 0:
            return
        defenders = self._find_defenders(colony)
        if len(defenders) > 0:
            self.state[arrived] = INV_FIGHT_ENTRANCE
        else:
            self.state[arrived] = INV_DESCEND

    def _find_defenders(self, colony):
        nx, ny = colony.nest_pos
        return np.where(
            colony.alive & colony.is_guard
            & (colony.layer == cfg.LAYER_SURFACE)
            & ((colony.x - nx) ** 2 + (colony.y - ny) ** 2 < cfg.GUARD_ALERT_RADIUS ** 2)
        )[0]

    def _update_fight_entrance(self, colony):
        mask = self.alive & (self.state == INV_FIGHT_ENTRANCE)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        self.entrance_fight_ticks += 1
        defenders = self._find_defenders(colony)

        # Hiệu ứng: MỌI quân đang tham chiến (cả 2 phe) nhấp nháy/rung nhẹ
        # trong lúc giao tranh đang diễn ra - xem draw_ants() trong
        # render_surface.py - để trận đánh trông "có va chạm" thay vì 2
        # đám đứng yên lặng lẽ rồi bỗng dưng vài con biến mất.
        self.combat_flash_ticks[idx] = cfg.HIT_FLASH_DURATION_TICKS
        if len(defenders) > 0:
            colony.combat_flash_ticks[defenders] = cfg.HIT_FLASH_DURATION_TICKS

        if len(defenders) > 0:
            is_def_major = colony.role[defenders] == cfg.ROLE_MAJOR
            kill_prob = np.where(
                is_def_major,
                cfg.INVASION_ATTACKER_KILL_PROB * cfg.MAJOR_DEFENSE_FACTOR,
                cfg.INVASION_ATTACKER_KILL_PROB,
            )
            killed_defenders = defenders[np.random.uniform(0, 1, len(defenders)) < kill_prob]
            if len(killed_defenders) > 0:
                colony.alive[killed_defenders] = False
                colony.underground.total_deaths += len(killed_defenders)
                colony.underground.add_corpse(len(killed_defenders))
                self.total_guards_killed_by_invasion += len(killed_defenders)

            is_att_major = self.role[idx] == cfg.ROLE_MAJOR
            def_kill_prob = np.where(
                is_att_major,
                cfg.INVASION_DEFENDER_KILL_PROB * cfg.MAJOR_DEFENSE_FACTOR,
                cfg.INVASION_DEFENDER_KILL_PROB,
            )
            def_kill_prob = def_kill_prob * min(1.0, len(defenders) / max(1, len(idx)))
            killed_mask = np.random.uniform(0, 1, len(idx)) < def_kill_prob
            killed_att = idx[killed_mask]
            if len(killed_att) > 0:
                self.alive[killed_att] = False
                self.total_invaders_killed += len(killed_att)
                idx = idx[~killed_mask]

        if len(idx) == 0:
            return  # cả nhóm này đã bị hạ hết ngay tại cửa hang

        # Vượt qua nếu: hết lính gác phòng thủ, HOẶC đã giao chiến đủ lâu
        # (tránh kẹt vô hạn nếu tỉ lệ sát thương 2 bên xấp xỉ nhau)
        if len(defenders) == 0 or self.entrance_fight_ticks > cfg.INVASION_ENTRANCE_FIGHT_TICKS:
            self.state[idx] = INV_DESCEND

    def _room_target(self, colony, room_id):
        center, radius = colony.underground.room_center_and_radius_by_id(room_id)
        if center is None:
            return colony.nest_pos, 1.0
        return center, radius

    def _update_descend(self, colony):
        mask = self.alive & (self.state == INV_DESCEND)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        # Chuyển hẳn xuống hầm ngay lúc bắt đầu di chuyển (giống cách 1 con
        # kiến thật "biến mất" xuống giếng) - hành lang dưới hầm không vẽ
        # chi tiết từng đoạn nên chỉ cần đổi layer rồi lượn thẳng tới phòng
        # mục tiêu bằng khoảng cách logic, không cần mô phỏng đường đi.
        self.layer[idx] = cfg.LAYER_UNDERGROUND
        for room_id in (0, 1, 4):
            sub = idx[self.target_room[idx] == room_id]
            if len(sub) == 0:
                continue
            center, _radius = self._room_target(colony, room_id)
            self.depth[sub] = room_id_to_depth(colony, room_id)
            dist = self._move_towards(sub, center, cfg.INVASION_UG_SPEED)
            arrived = sub[dist < cfg.ARRIVE_THRESHOLD * 2]
            if len(arrived) > 0:
                self.loot_ticks[arrived] = 0
                if room_id == 0:
                    self.state[arrived] = INV_RAID_STORAGE
                else:
                    self.state[arrived] = INV_RAID_BROOD

    def _update_raid_storage(self, colony):
        mask = self.alive & (self.state == INV_RAID_STORAGE)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        self.loot_ticks[idx] += 1

        ug = colony.underground
        if ug.food_in_storage > 0.01:
            steal = min(ug.food_in_storage, cfg.INVASION_FOOD_STEAL_PER_TICK * len(idx))
            ug.food_in_storage -= steal
            self.total_food_stolen += steal
            self.carrying[idx] = True

        done = idx[
            (self.loot_ticks[idx] >= cfg.INVASION_MAX_LOOT_TICKS)
            | (ug.food_in_storage <= 0.01)
        ]
        if len(done) > 0:
            self.state[done] = INV_RETREAT_UG

    def _update_raid_brood(self, colony):
        mask = self.alive & (self.state == INV_RAID_BROOD)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        self.loot_ticks[idx] += 1

        # Cứ mỗi INVASION_EGG_STEAL_INTERVAL / INVASION_LARVA_STEAL_INTERVAL
        # tick thì 1 quân (luân phiên theo loot_ticks của từng con, không
        # đồng loạt) bắt được 1 quả trứng/1 con ấu trùng, nếu còn.
        egg_hitters = idx[(self.loot_ticks[idx] % cfg.INVASION_EGG_STEAL_INTERVAL) == 0]
        for _ in egg_hitters:
            active = np.where(colony.egg_active)[0]
            if len(active) == 0:
                break
            victim = active[np.random.randint(0, len(active))]
            colony.egg_active[victim] = False
            colony.egg_growth[victim] = 0.0
            self.total_brood_stolen += 1
            self.carrying[egg_hitters] = True

        larva_hitters = idx[(self.loot_ticks[idx] % cfg.INVASION_LARVA_STEAL_INTERVAL) == 0]
        for _ in larva_hitters:
            active = np.where(colony.larva_active)[0]
            if len(active) == 0:
                break
            victim = active[np.random.randint(0, len(active))]
            colony.larva_active[victim] = False
            colony.larva_growth[victim] = 0.0
            self.total_brood_stolen += 1
            self.carrying[larva_hitters] = True

        done = idx[self.loot_ticks[idx] >= cfg.INVASION_MAX_LOOT_TICKS]
        if len(done) > 0:
            self.state[done] = INV_RETREAT_UG

    def _update_retreat_ug(self, colony):
        mask = self.alive & (self.state == INV_RETREAT_UG)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        shaft = (float(colony.underground.shaft_xy[0]), float(colony.underground.shaft_xy[1]))
        dist = self._move_towards(idx, shaft, cfg.INVASION_UG_SPEED)
        arrived = idx[dist < cfg.ARRIVE_THRESHOLD * 2]
        if len(arrived) > 0:
            self.layer[arrived] = cfg.LAYER_SURFACE
            self.depth[arrived] = cfg.LAYER_SURFACE_DEPTH
            nx, ny = colony.nest_pos
            self.x[arrived] = nx
            self.y[arrived] = ny
            self.state[arrived] = INV_RETREAT_SURFACE

    def _update_retreat_surface(self, colony):
        mask = self.alive & (self.state == INV_RETREAT_SURFACE)
        if not np.any(mask):
            return
        idx = np.where(mask)[0]
        if self.wave_path_len > 1:
            dist = self._follow_wave_path_reverse(idx, cfg.INVASION_RETREAT_SPEED)
        else:
            dist = self._move_towards(idx, self.spawn_edge_xy, cfg.INVASION_RETREAT_SPEED)
        gone = idx[dist < cfg.ARRIVE_THRESHOLD * 3]
        if len(gone) > 0:
            self.alive[gone] = False

    # ------------------------------------------------------------------
    def counts(self):
        return {
            "active": self.active,
            "wave_number": self.wave_number,
            "raiders_left": int(np.sum(self.alive)),
            "next_wave_tick": self.next_wave_tick,
            "next_wave_size": self.next_wave_size,
            "total_food_stolen": self.total_food_stolen,
            "total_brood_stolen": self.total_brood_stolen,
            "total_invaders_killed": self.total_invaders_killed,
        }


def room_id_to_depth(colony, room_id):
    for (rid, _name, _pos, _r, _color, depth) in colony.underground.rooms:
        if rid == room_id:
            return depth
    return cfg.LAYER_SURFACE_DEPTH
