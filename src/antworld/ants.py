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
from . import pathfinding


def _turn_limited(current, target, max_delta):
    """Trả về góc mới sau khi xoay từ `current` về `target`, nhưng KHÔNG
    xoay quá `max_delta` radian trong lần gọi này (dùng mỗi tick) - mô
    phỏng việc côn trùng thật XOAY THÂN DẦN trước khi đổi hướng, thay vì
    bật thẳng sang hướng mới ngay lập tức (arctan2 trực tiếp) như trước.
    Vector hóa (numpy), xử lý đúng vòng lặp góc (wrap quanh ±pi)."""
    diff = (target - current + np.pi) % (2 * np.pi) - np.pi
    diff = np.clip(diff, -max_delta, max_delta)
    return current + diff


class AntColony:
    def __init__(self, n_start, max_ants, surface, underground, nest_pos=None, founding=False):
        self.n = max_ants   # tổng SỐ CHỖ cấp phát sẵn trong mảng = trần dân số
        self.surface = surface
        self.underground = underground
        self.nest_pos = nest_pos if nest_pos else cfg.NEST_POS
        rng = np.random.default_rng()
        # Mặt nạ (mask) các ô ĐỦ XA cửa tổ, dùng riêng cho tuyển mộ theo
        # mùi (xem _sample_recruit_candidates) - dựng 1 LẦN DUY NHẤT (lazy,
        # xem _get_recruit_mask) vì nest_pos cố định suốt ván, không cần
        # tính lại mỗi lần gọi.
        self._recruit_mask = None

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

        # --- Necrophoresis (thợ mai táng) - xem STATE_UNDERTAKER_TO_CORPSE
        # /TO_GRAVEYARD trong config.py + _update_undertakers() bên dưới:
        # tọa độ (x,y) của XÁC mà ant này ĐANG ĐƯỢC PHÂN CÔNG đi khiêng -
        # cần lưu RIÊNG cho từng con (không dùng biến chung) vì nhiều
        # nurse có thể cùng lúc đang khiêng NHIỀU xác khác nhau.
        self.undertaker_target_x = np.zeros(self.n, dtype=np.float32)
        self.undertaker_target_y = np.zeros(self.n, dtype=np.float32)

        # --- Animation: hiệu ứng tạm thời (đếm ngược mỗi tick, xem
        # decay ở đầu update() bên dưới) - KHÔNG ảnh hưởng gì tới mô
        # phỏng/logic, chỉ đọc bởi render_surface.py để vẽ hiệu ứng. ---
        self.bounce_ticks = np.zeros(self.n, dtype=np.int16)         # nảy lên khi nhặt/giao đồ
        self.combat_flash_ticks = np.zeros(self.n, dtype=np.int16)   # nhấp nháy/rung khi giao chiến
        # "Dừng dò đường bằng râu" (antenna tapping) - xem cfg.ANTENNA_PAUSE_*
        # + _follow_paths(allow_pause=True): số tick còn lại đang đứng khựng
        # lại (không tịnh tiến) để "ngoáy đầu" trước khi đi tiếp.
        self.pause_ticks = np.zeros(self.n, dtype=np.int16)
        # Pha bước chân/animation (radian), TĂNG THEO QUÃNG ĐƯỜNG DI CHUYỂN
        # THẬT mỗi tick (xem cuối update()) - KHÔNG chạy theo frame_counter
        # toàn cục vô điều kiện như animation cũ, nên kiến đứng yên (đang
        # dừng dò đường, đang xếp hàng chờ...) thì chân/sprite đi bộ cũng
        # đứng yên theo, còn kiến đang lao nhanh (lính gác) thì bước chân
        # cũng nhanh hơn tương ứng - xem render_surface.draw_ants().
        self.anim_phase = np.zeros(self.n, dtype=np.float32)

        # --- Hấp hối trước khi chết thật (chết già/đói/khát - xem
        # cfg.DYING_DURATION_TICKS + _update_lifecycle/_finalize_dying) -
        # KHÔNG áp dụng cho chết vì giao chiến (vẫn tức thời như cũ).
        # dying_ticks>0: con này đang hấp hối, ĐỨNG YÊN tại đúng vị trí
        # dying_x/dying_y (chụp lại đúng lúc bắt đầu hấp hối) - layer/depth
        # cũng chụp lại để lúc chết THẬT vẫn đăng ký xác đúng chỗ dù trong
        # lúc hấp hối có bị hệ thống khác lỡ đổi layer/depth.
        self.dying_ticks = np.zeros(self.n, dtype=np.int16)
        self.dying_x = np.zeros(self.n, dtype=np.float32)
        self.dying_y = np.zeros(self.n, dtype=np.float32)
        self.dying_layer = np.zeros(self.n, dtype=np.int8)
        self.dying_depth = np.zeros(self.n, dtype=np.int16)

        # --- Lính gác chạm râu kiểm tra đồng đội ra vào cửa tổ (nestmate
        # recognition) - xem cfg.GUARD_INSPECT_*/_update_guard_inspections().
        # Thuần túy hiệu ứng hình ảnh, giống cơ chế trophallaxis_events.
        self.inspect_cooldown = np.zeros(self.n, dtype=np.int16)
        self.inspection_events = []

        # --- Cắn giữ mồi trước khi tha đi (xem cfg.BITE_GRIP_PAUSE_TICKS) -
        # đếm ngược HIỂN THỊ animation "ngoạm/cắn" ở render_surface.py; việc
        # ĐỨNG YÊN trong lúc này mượn lại cơ chế pause_ticks có sẵn (xem nơi
        # gán ở _update_searching_ants).
        self.bite_ticks = np.zeros(self.n, dtype=np.int16)

        # --- Chăm sóc lẫn nhau (allogrooming) giữa kiến rảnh rỗi dưới hầm -
        # xem cfg.GROOM_*/_update_grooming(). groom_partner=-1 nghĩa là
        # không đang chăm sóc ai.
        self.groom_ticks = np.zeros(self.n, dtype=np.int16)
        self.groom_partner = np.full(self.n, -1, dtype=np.int32)
        self.groom_cooldown = np.zeros(self.n, dtype=np.int16)

        # --- Tìm đường trên mặt đất (pathfinding.py): mỗi kiến giữ sẵn 1
        # "hàng đợi" điểm rẽ hướng (waypoint) của đường đi any-angle NGẮN
        # NHẤT đang đi theo (tới điểm khám phá ngẫu nhiên nếu đang
        # SEARCHING, hoặc tới cửa tổ nếu đang RETURNING/lính gác rút quân)
        # - xem _assign_new_path/_follow_paths. path_len=0 nghĩa là CHƯA
        # có đường đi (cần tính đường mới, xem PATH_REPLAN_BUDGET_PER_TICK
        # trong update() để tránh giật khung hình khi quá nhiều kiến cùng
        # cần đường mới 1 lúc).
        self.path_x = np.zeros((self.n, cfg.PATH_MAX_WAYPOINTS), dtype=np.float32)
        self.path_y = np.zeros((self.n, cfg.PATH_MAX_WAYPOINTS), dtype=np.float32)
        self.path_len = np.zeros(self.n, dtype=np.int16)
        self.path_idx = np.zeros(self.n, dtype=np.int16)
        self.pathfinder = pathfinding.VisibilityPathfinder(surface)
        self._path_budget = 0

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
        # Kiến "nanitic" - thợ SINH RA TRONG LÚC ĐANG LẬP TỔ (founding_phase
        # còn True lúc nở), nhỏ con hơn hẳn thợ bình thường vì chúa ít tài
        # nguyên nuôi lúc đầu (đúng thực tế) - đánh dấu VĨNH VIỄN lúc sinh
        # ra (không "lớn lên" thành cỡ thường sau này, đúng sinh học thật:
        # kích thước 1 con kiến cố định suốt đời kể từ lúc rời kén). Xem
        # _spawn_new_ants() (nơi gắn cờ) và render_surface.py (nơi áp dụng
        # NANITIC_SIZE_SCALE khi vẽ).
        self.is_nanitic = np.zeros(self.n, dtype=bool)
        self.is_nanitic[:n_start] = False  # đàn khởi đầu KHÔNG TÍNH (chỉ
                                         # áp dụng cho thợ MỚI NỞ qua đường
                                         # ống trứng->ấu trùng->nhộng, xem
                                         # _spawn_new_ants)
        # Tuổi ban đầu rải ngẫu nhiên để đàn không cùng già/chết 1 lượt
        self.age = rng.uniform(0, cfg.MAX_AGE_TICKS * 0.6, self.n).astype(np.float32)

        # Lính gác khởi đầu đóng quân NGAY trong phòng gác cửa, không đứng
        # lẫn trên mặt đất như thợ thường
        guard_start = np.where(self.is_guard[:n_start])[0]
        if len(guard_start) > 0:
            self.layer[guard_start] = cfg.LAYER_UNDERGROUND
            self.depth[guard_start] = underground.guard_depth
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
    def update(self, enemy=None, invasion=None):
        self.tick_count += 1
        self.avoid_cooldown = np.maximum(0, self.avoid_cooldown - 1).astype(np.int16)
        self.bounce_ticks = np.maximum(0, self.bounce_ticks - 1).astype(np.int16)
        self.combat_flash_ticks = np.maximum(0, self.combat_flash_ticks - 1).astype(np.int16)
        self.pause_ticks = np.maximum(0, self.pause_ticks - 1).astype(np.int16)
        self.inspect_cooldown = np.maximum(0, self.inspect_cooldown - 1).astype(np.int16)
        self.bite_ticks = np.maximum(0, self.bite_ticks - 1).astype(np.int16)
        self._path_budget = cfg.PATH_REPLAN_BUDGET_PER_TICK

        # --- Hoàn tất cái chết THẬT cho những con vừa hấp hối xong (xem
        # cfg.DYING_DURATION_TICKS/__init__) - phải làm SỚM trong update(),
        # trước khi các hệ thống khác (giao việc, tuần tra...) coi chúng là
        # "còn sống bình thường" trong tick này. ---
        was_dying = self.dying_ticks > 0
        self.dying_ticks = np.maximum(0, self.dying_ticks - 1).astype(np.int16)
        newly_dead = np.where(was_dying & (self.dying_ticks == 0))[0]
        if len(newly_dead) > 0:
            self.alive[newly_dead] = False
            self.underground.total_deaths += len(newly_dead)
            died_ug = newly_dead[self.dying_layer[newly_dead] == cfg.LAYER_UNDERGROUND]
            died_surface = newly_dead[self.dying_layer[newly_dead] == cfg.LAYER_SURFACE]
            for i in died_ug.tolist():
                self.underground.register_corpse(
                    float(self.dying_x[i]), float(self.dying_y[i]), int(self.dying_depth[i])
                )
            if len(died_surface) > 0:
                self.underground.add_corpse(len(died_surface))

        # Chụp lại vị trí ĐẦU tick để cuối tick tính quãng đường DI CHUYỂN
        # THẬT của từng con (xem cfg.ANIM_PHASE_DISTANCE_SCALE) - dùng để
        # cập nhật pha bước chân/animation đúng theo tốc độ thật, thay vì
        # chạy vô điều kiện theo thời gian như animation cũ.
        prev_x = self.x.copy()
        prev_y = self.y.copy()
        if self.trophallaxis_events:
            cutoff = self.tick_count - cfg.TROPHALLAXIS_TTL_TICKS
            self.trophallaxis_events = [e for e in self.trophallaxis_events if e[4] > cutoff]
        if self.inspection_events:
            cutoff = self.tick_count - cfg.GUARD_INSPECT_TTL_TICKS
            self.inspection_events = [e for e in self.inspection_events if e[4] > cutoff]
        self._update_surface_ants(enemy)
        self._update_underground_ants()
        self._update_nurses()
        self._update_undertakers()
        self._update_attendants()
        self._update_guards(enemy, invasion)
        self._update_guard_inspections()
        self._update_grooming()
        self._update_haulers(enemy)
        self.surface.decay_pheromone()
        self.surface.decay_visit()
        self.surface.decay_food()
        # Kiến đang HẤP HỐI phải đứng YÊN TUYỆT ĐỐI bất kể các hệ thống ở
        # trên vừa lỡ di chuyển/gán việc gì cho nó trong tick này - phục
        # hồi đúng vị trí lúc bắt đầu hấp hối, chỉ cho phép RUN RẨY góc
        # quay (không tịnh tiến) để trông như đang giãy giụa/kiệt sức chứ
        # không phải tượng đứng im cứng nhắc.
        dying_now = np.where(self.dying_ticks > 0)[0]
        if len(dying_now) > 0:
            self.x[dying_now] = self.dying_x[dying_now]
            self.y[dying_now] = self.dying_y[dying_now]
            self.theta[dying_now] += np.random.uniform(
                -cfg.DYING_TREMBLE_JITTER, cfg.DYING_TREMBLE_JITTER, len(dying_now)
            ).astype(np.float32)
        population = int(np.sum(self.alive))
        # Tổ MỞ RỘNG theo dân số (xem UndergroundWorld.update_room_sizes)
        # - trước đây kích thước phòng CỐ ĐỊNH suốt ván, không phản ánh
        # việc đàn đông lên cần nhiều không gian hơn, khác hẳn thực tế
        # nuôi kiến (phải chuyển đàn sang tổ lớn hơn khi đàn phát triển).
        self.underground.update_room_sizes(population)
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
        if not self.founding_phase:
            self._rebalance_labor()
        # LƯU Ý: việc tái sinh thức ăn ngẫu nhiên KHÔNG còn nằm ở đây nữa -
        # đã chuyển sang main.py để có thể bật/tắt bằng nút trên thanh công
        # cụ, và để tránh 2 tổ (chính + đối thủ) cùng kích hoạt trùng lặp
        # khi cả 2 đều gọi update() mỗi khung hình.

        # Cập nhật pha bước chân/animation THEO QUÃNG ĐƯỜNG DI CHUYỂN THẬT
        # trong tick này (xem giải thích ở đầu update() + cfg.ANIM_PHASE_
        # DISTANCE_SCALE) - con nào không nhúc nhích (đứng yên/đang dừng dò
        # đường) thì pha không đổi, chân/sprite đi bộ đứng yên theo.
        moved_dist = np.hypot(self.x - prev_x, self.y - prev_y)
        self.anim_phase = (
            self.anim_phase + moved_dist * cfg.ANIM_PHASE_DISTANCE_SCALE
        ).astype(np.float32) % (2 * np.pi)

    def _rebalance_labor(self):
        """AN TOÀN phân công lại lao động khi đàn THIẾU HẲN 1 vai trò
        thiết yếu - đúng thực tế đàn kiến có khả năng ĐIỀU CHỈNH LINH
        HOẠT phân công lao động theo nhu cầu (task allocation plasticity),
        không cố định vai trò suốt đời ngay từ lúc nở. Có 3 mức ưu tiên,
        xét THEO ĐÚNG THỨ TỰ này mỗi lần gọi (chỉ làm 1 việc/lần gọi, chờ
        lần sau đánh giá lại):

        1) KHÔNG BAO GIỜ để 0 thợ kiếm ăn khi đàn còn ít nhất 2 con - đây
           là lỗi NGHIÊM TRỌNG NHẤT: hết người kiếm ăn = kho không còn
           nguồn thu = từ từ chết đói toàn đàn dù trước đó vẫn ổn. Rút 1
           y tá/hộ vệ (đang dư so với nhu cầu) về lại kiếm ăn.
        2) Nếu CÒN DƯ ít nhất 3 thợ kiếm ăn mà 0 y tá dù đang có ấu trùng
           cần ăn - lứa nanitic đầu tiên (thường chỉ 4 con) có xác suất
           NGẪU NHIÊN ra được y tá là RẤT THẤP (JOB_NURSE_RATIO=10% trong
           số thợ nhỏ). Không có y tá => ấu trùng ứ đọng mãi, không bao
           giờ hóa nhộng thành thợ mới => đàn chỉ có thể co lại dần vì
           chết già => TUYỆT CHỦNG dù thức ăn dư thừa.
        3) Tương tự với hộ vệ (chăm trứng + chúa, JOB_ATTENDANT_RATIO=6%).
        """
        if self.tick_count % 200 != 0:
            return
        is_minor = self.role == cfg.ROLE_MINOR
        alive_minor = self.alive & is_minor
        n_foragers = int(np.sum(alive_minor & (self.job == cfg.JOB_FORAGER)))
        n_nurses = int(np.sum(alive_minor & (self.job == cfg.JOB_NURSE)))
        n_attendants = int(np.sum(alive_minor & (self.job == cfg.JOB_ATTENDANT)))
        n_larvae = int(np.sum(self.larva_active))
        population = int(np.sum(self.alive))

        if n_foragers == 0 and population >= 1:
            spare = np.where(alive_minor & (self.job != cfg.JOB_FORAGER))[0]
            if len(spare) > 0:
                pick = spare[0]
                self.job[pick] = cfg.JOB_FORAGER
                self.layer[pick] = cfg.LAYER_SURFACE
                self.depth[pick] = cfg.LAYER_SURFACE_DEPTH
                self.x[pick] = self.nest_pos[0]
                self.y[pick] = self.nest_pos[1]
                self.state[pick] = cfg.STATE_SEARCHING
                self.theta[pick] = np.random.uniform(0, 2 * np.pi)
                return  # 1 viec/lan goi - danh gia lai vao lan sau

        forager_pool = list(np.where(alive_minor & (self.job == cfg.JOB_FORAGER) & (~self.carrying))[0])
        # Chỉ "rút quân" khi còn DƯ ÍT NHẤT 3 thợ kiếm ăn - không bao giờ
        # rút tới mức đàn hết sạch người đi tìm thức ăn.
        if len(forager_pool) >= 3 and n_nurses == 0 and n_larvae > 0:
            pick = forager_pool.pop()
            self.job[pick] = cfg.JOB_NURSE
            self.layer[pick] = cfg.LAYER_UNDERGROUND
            self.depth[pick] = self.underground.storage_depth
            self.x[pick], self.y[pick] = self.underground.storage[0], self.underground.storage[1]
            self.state[pick] = cfg.STATE_NURSE_AT_STORAGE

        if len(forager_pool) >= 3 and n_attendants == 0 and population >= 5:
            pick = forager_pool.pop()
            self.job[pick] = cfg.JOB_ATTENDANT
            self.layer[pick] = cfg.LAYER_UNDERGROUND
            self.depth[pick] = self.underground.queen_depth
            self.x[pick], self.y[pick] = self.underground.queen_room[0], self.underground.queen_room[1]
            self.state[pick] = cfg.STATE_ATTENDANT_AT_QUEEN
            self.dwell_ticks[pick] = np.random.randint(
                cfg.ATTENDANT_SWITCH_TICKS_MIN, cfg.ATTENDANT_SWITCH_TICKS_MAX + 1
            )

    # ------------------------------------------------------------------
    def _wrap_indices(self, arr):
        return np.clip(arr.astype(np.int32), 0, cfg.GRID_SIZE - 1)

    def _update_surface_ants(self, enemy=None):
        on_surface = self.alive & (self.layer == cfg.LAYER_SURFACE)
        if not np.any(on_surface):
            return

        searching = on_surface & (self.state == cfg.STATE_SEARCHING)
        returning = on_surface & (self.state == cfg.STATE_RETURNING)

        if np.any(searching):
            self._update_searching_ants(np.where(searching)[0], enemy)
        if np.any(returning):
            self._update_returning_ants(np.where(returning)[0])

    # ------------------------------------------------------------------
    def _assign_new_path(self, i, start_xy, target_xy):
        """Tính đường đi any-angle NGẮN NHẤT (visibility graph + A*, xem
        pathfinding.py) cho ĐÚNG 1 con kiến (chỉ số i) và lưu vào hàng đợi
        waypoint của nó. Trả về True nếu tìm được đường (dù rất hiếm khi
        thất bại - chỉ khi kiến/đích bị vây kín hoàn toàn bởi vật cản)."""
        path = self.pathfinder.find_path(start_xy, target_xy)
        if not path:
            return False
        path = path[: cfg.PATH_MAX_WAYPOINTS]
        length = len(path)
        for k, (wx, wy) in enumerate(path):
            self.path_x[i, k] = wx
            self.path_y[i, k] = wy
        self.path_len[i] = length
        self.path_idx[i] = 0
        return True

    def _follow_paths(self, idx, speed, allow_pause=False):
        """Di chuyển hàng loạt (vector hóa) các kiến trong idx theo waypoint
        HIỆN TẠI của đường đi đã tính sẵn - khi tới đủ gần 1 waypoint thì tự
        chuyển sang waypoint kế tiếp; tới waypoint CUỐI (đích) thì xóa path
        (path_len=0) để nơi gọi hàm này biết mà xử lý tiếp (nhặt đồ, xuống
        hầm, chọn điểm khám phá mới...).

        `allow_pause=True`: bật hành vi "dừng dò đường bằng râu" (xem
        cfg.ANTENNA_PAUSE_*) - CHỈ dùng cho kiến đang tự do khám
        phá/quay về, KHÔNG dùng cho lính gác lao lên nghênh chiến hay thợ
        khiêng mồi lớn (cần phản ứng ngay, không được khựng lại giữa
        chừng)."""
        if allow_pause:
            paused_mask = self.pause_ticks[idx] > 0
            if np.any(paused_mask):
                pidx = idx[paused_mask]
                # Đứng khựng lại: KHÔNG tịnh tiến, chỉ lắc đầu nhẹ ngẫu
                # nhiên mỗi tick như đang "ngoáy râu" dò xét xung quanh.
                self.theta[pidx] += np.random.uniform(
                    -cfg.ANTENNA_TAP_JITTER, cfg.ANTENNA_TAP_JITTER, len(pidx)
                ).astype(np.float32)
            moving_idx = idx[~paused_mask]
            if len(moving_idx) > 0:
                roll = np.random.random(len(moving_idx)) < cfg.ANTENNA_PAUSE_PROB
                if np.any(roll):
                    newly = moving_idx[roll]
                    self.pause_ticks[newly] = np.random.randint(
                        cfg.ANTENNA_PAUSE_MIN_TICKS,
                        cfg.ANTENNA_PAUSE_MAX_TICKS + 1,
                        size=len(newly),
                    ).astype(np.int16)
            idx = moving_idx
            if len(idx) == 0:
                return

        cur_wp = self.path_idx[idx].astype(np.int64)
        tx = self.path_x[idx, cur_wp]
        ty = self.path_y[idx, cur_wp]
        x, y = self.x[idx], self.y[idx]
        dx, dy = tx - x, ty - y
        dist = np.sqrt(dx * dx + dy * dy)
        safe_dist = np.where(dist < 1e-6, 1.0, dist)
        step = np.minimum(speed, dist)
        self.x[idx] = x + dx / safe_dist * step
        self.y[idx] = y + dy / safe_dist * step
        moved = dist > 1e-6
        if np.any(moved):
            target_theta = np.arctan2(dy[moved], dx[moved])
            self.theta[idx[moved]] = _turn_limited(
                self.theta[idx[moved]], target_theta, cfg.MAX_TURN_RATE_PER_TICK
            )

        reached = dist < cfg.WAYPOINT_ARRIVE_THRESHOLD
        if np.any(reached):
            ridx = idx[reached]
            nxt = (self.path_idx[ridx] + 1).astype(np.int16)
            finished = nxt >= self.path_len[ridx]
            self.path_idx[ridx] = np.where(finished, self.path_idx[ridx], nxt).astype(np.int16)
            done_idx = ridx[finished]
            if len(done_idx) > 0:
                self.path_len[done_idx] = 0
                self.path_idx[done_idx] = 0

    def _get_recruit_mask(self):
        """Mặt nạ bool (GRID_SIZE x GRID_SIZE): True ở các ô ĐỦ XA cửa tổ.
        Lý do cần loại trừ hẳn vùng quanh tổ khi tuyển mộ: MỌI kiến tha đồ
        về, bất kể tìm thấy ăn ở hướng nào, đều hội tụ đi qua đúng cửa tổ
        ở đoạn CUỐI hành trình - nên vùng gần cửa tổ luôn là nơi ĐẬM MÙI
        NHẤT trên bản đồ dù chẳng nói lên gì về vị trí thức ăn thật sự,
        chỉ là "điểm chụm" của mọi con đường. Nếu tính cả vùng này, tuyển
        mộ sẽ chủ yếu hút kiến quay lại LOANH QUANH GẦN TỔ (phản tác dụng
        - đã tự đo bằng kịch bản 1 cụm thức ăn ở xa: bật tuyển mộ mà không
        loại trừ vùng này khiến kiếm ăn CHẬM hơn hẳn, không nhanh hơn),
        thay vì hướng ra đúng đoạn xa của vệt mùi - nơi thực sự dẫn tới
        nguồn ăn."""
        if self._recruit_mask is None:
            n = cfg.GRID_SIZE
            nx, ny = self.nest_pos
            xs, ys = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
            dist = np.hypot(xs - nx, ys - ny)
            self._recruit_mask = dist > cfg.PHEROMONE_RECRUIT_NEST_EXCLUDE_RADIUS
        return self._recruit_mask

    def _sample_recruit_candidates(self, k):
        """TUYỂN MỘ theo mùi (pheromone) - lấy sẵn 1 lô tối đa `k` điểm
        đích ứng viên bốc ngẫu nhiên CÓ TRỌNG SỐ theo độ đậm mùi hiện tại
        trên bản đồ (ô càng đậm mùi càng dễ được chọn), CHỈ XÉT các ô ĐỦ
        XA cửa tổ (xem _get_recruit_mask - loại hẳn "điểm chụm" gần tổ ra
        khỏi phân phối, nếu không tuyển mộ sẽ hút nhầm kiến về quanh tổ
        thay vì ra chỗ có ăn) - dùng cho các kiến SEARCHING đang cần điểm
        khám phá mới, xem _update_searching_ants(). Đây là cơ chế "tuyển
        mộ đồng loạt" (recruitment) thật của kiến: khi 1 con tìm ra nguồn
        ăn và để lại vệt mùi trên đường tha về, các con khác có xu hướng
        bị hút theo vệt đó thay vì tự dò ngẫu nhiên độc lập, giúp cả đàn
        hội tụ nhanh về nguồn ăn giàu vừa được phát hiện.

        Trả về None nếu tổng lượng mùi (đã loại vùng gần tổ) còn quá thấp
        (chưa có vệt nào đáng theo - xem PHEROMONE_RECRUIT_MIN_TOTAL), để
        nơi gọi tự động rơi về dò ngẫu nhiên như bình thường.

        Tính 1 LẦN cho cả lô kiến cần đích trong tick này (không phải
        từng con gọi lại từ đầu) để tránh lặp lại chi phí dựng phân phối
        xác suất trên toàn bộ GRID_SIZE^2 ô nhiều lần không cần thiết."""
        pher = self.surface.pheromone
        mask = self._get_recruit_mask()
        n = cfg.GRID_SIZE
        flat_pher = pher.ravel()
        idx_pool = np.nonzero(mask.ravel())[0]
        weights = flat_pher[idx_pool]
        total = float(weights.sum())
        if total < cfg.PHEROMONE_RECRUIT_MIN_TOTAL:
            return None
        probs = weights / total
        count = min(int(k), 64)
        chosen = np.random.choice(idx_pool, size=count, p=probs)
        gx = (chosen // n).astype(np.float32)
        gy = (chosen % n).astype(np.float32)
        # Rung nhẹ +-0.5 ô quanh tâm ô được bốc trúng - tránh CẢ LOẠT kiến
        # cùng nhắm chết vào đúng 1 điểm pixel giống hệt nhau (trông giả
        # tạo/máy móc), vẫn giữ đúng khu vực đang có mùi đậm.
        gx = np.clip(gx + np.random.uniform(-0.5, 0.5, count), 0, n - 1)
        gy = np.clip(gy + np.random.uniform(-0.5, 0.5, count), 0, n - 1)
        return gx, gy

    def _pick_explore_target(self, x, y):
        """Chọn 1 điểm khám phá MỚI (dò ngẫu nhiên độc lập, không theo mùi
        - xem _sample_recruit_candidates() để biết nhánh "tuyển mộ" bổ
        sung ở _update_searching_ants) cho kiến đang SEARCHING - ưu tiên
        vùng CÒN Ít NHIỆT (visit_heat thấp, xem SurfaceWorld.visit_heat)
        để đàn tự nhiên tỏa ra phủ khắp bản đồ thay vì dẫm chân lên nhau,
        đồng thời tránh vùng có mùi báo động nguy hiểm đậm (kẻ thù ở gần)."""
        n = cfg.GRID_SIZE
        k = cfg.EXPLORE_TARGET_SAMPLES
        cxs = np.random.uniform(0, n - 1, k).astype(np.float32)
        cys = np.random.uniform(0, n - 1, k).astype(np.float32)
        cxi = self._wrap_indices(cxs)
        cyi = self._wrap_indices(cys)
        free = ~self.surface.is_blocked(cxi, cyi)
        if not np.any(free):
            return None, None
        cxs, cys, cxi, cyi = cxs[free], cys[free], cxi[free], cyi[free]
        heat = self.surface.sample_visit(cxi, cyi)
        danger = self.surface.sample_danger(cxi, cyi)
        dist_from_here = np.hypot(cxs - x, cys - y)
        # điểm càng gần vừa đi qua (nhiệt cao)/càng nguy hiểm thì càng bị
        # "trừ điểm"; cộng thêm chút ưu tiên đi xa hơn 1 chút mỗi lần thay
        # vì loanh quanh 1 chỗ
        score = heat + danger * cfg.EXPLORE_DANGER_WEIGHT - 0.1 * np.minimum(dist_from_here, 10.0)
        best = int(np.argmin(score))
        return float(cxs[best]), float(cys[best])

    def _count_active_haulers(self):
        """Số kiến ĐANG THAM GIA khiêng mồi lớn (đang tới HOẶC đang đứng
        chờ tại xác) - dùng để giới hạn không cho quá nhiều kiến bỏ dở
        việc kiếm ăn bình thường chỉ vì 1 xác (xem HAUL_MAX_HAULERS)."""
        return int(np.sum(self.alive & np.isin(
            self.state, (cfg.STATE_HAUL_APPROACH, cfg.STATE_HAUL_GRIP)
        )))

    def _update_searching_ants(self, idx, enemy=None):
        need_target = idx[self.path_len[idx] == 0]
        if len(need_target) > 0:
            # TUYỂN MỘ (xem _sample_recruit_candidates): tính SẴN 1 lô ứng
            # viên theo mùi 1 LẦN cho cả nhóm cần đích trong tick này -
            # None nếu bản đồ chưa có vệt mùi nào đáng theo, khi đó MỌI
            # con trong nhóm rơi về dò ngẫu nhiên như trước (không tốn
            # thêm chi phí gì so với bản cũ).
            recruit = self._sample_recruit_candidates(len(need_target))
            # Khiêng mồi lớn (xem HAUL_* trong config.py + _update_haulers
            # bên dưới): nếu đang có xác kẻ thù vừa bị đánh bại chờ khiêng
            # VÀ chưa đủ đông người tới, 1 số kiến TÌM ĂN sẽ chọn đi tới
            # đó thay vì dò ngẫu nhiên/theo mùi như thường lệ - kiểm tra
            # 1 LẦN ở đây (không phải từng con), cờ này tự tắt giữa chừng
            # vòng lặp ngay khi vừa đủ HAUL_MAX_HAULERS (xem bên dưới).
            haul_open = (
                enemy is not None and enemy.carcass_active
                and self._count_active_haulers() < cfg.HAUL_MAX_HAULERS
            )
            ri = 0
            for i in need_target:
                if self._path_budget <= 0:
                    break
                tx = ty = None
                go_haul = False
                if haul_open and np.random.random() < cfg.HAUL_TARGET_PROB:
                    tx, ty = enemy.carcass_x, enemy.carcass_y
                    go_haul = True
                elif recruit is not None and np.random.random() < cfg.PHEROMONE_RECRUIT_PROB:
                    rgx, rgy = recruit
                    tx, ty = float(rgx[ri % len(rgx)]), float(rgy[ri % len(rgy)])
                    ri += 1
                    if self.surface.is_blocked(int(tx), int(ty)):
                        tx = ty = None  # trúng đúng ô đá/nước - bỏ qua, dò
                                         # ngẫu nhiên như bình thường thay vì
                                         # cố nhắm 1 đích không tới được
                if tx is None:
                    tx, ty = self._pick_explore_target(self.x[i], self.y[i])
                    go_haul = False
                if tx is None:
                    continue
                if self._assign_new_path(i, (self.x[i], self.y[i]), (tx, ty)):
                    self._path_budget -= 1
                    if go_haul:
                        self.state[i] = cfg.STATE_HAUL_APPROACH
                        if self._count_active_haulers() >= cfg.HAUL_MAX_HAULERS:
                            haul_open = False  # vua du nguoi - ngung goi
                                                # them ke tu day trong vong
                                                # lap nay

        active = idx[self.path_len[idx] > 0]
        if len(active) == 0:
            return
        self._follow_paths(active, cfg.ANT_SPEED, allow_pause=True)

        xi = self._wrap_indices(self.x[active])
        yi = self._wrap_indices(self.y[active])
        self.surface.deposit_visit(xi, yi)

        # Kiểm tra ô có thức ăn không -> nhặt (giá trị tùy loại thức ăn)
        got_food, food_types = self.surface.take_food(xi, yi, amount=1.0)
        got_idx = active[got_food]
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
            self.bounce_ticks[got_idx] = cfg.BOUNCE_DURATION_TICKS
            # Cắn giữ mồi trước khi tha đi (xem cfg.BITE_GRIP_PAUSE_TICKS):
            # đứng khựng lại "ngoạm chặt" 1 chút (mượn cơ chế pause_ticks
            # đã có, sẽ tự lắc đầu nhẹ trong lúc này) trước khi thực sự
            # bắt đầu kéo đi - bite_ticks riêng chỉ để render vẽ animation
            # mandible, không ảnh hưởng gì tới việc đứng yên.
            self.pause_ticks[got_idx] = cfg.BITE_GRIP_PAUSE_TICKS
            self.bite_ticks[got_idx] = cfg.BITE_GRIP_PAUSE_TICKS
            # Vừa nhặt được mồi -> hủy đường khám phá dở dang, tick sau sẽ
            # tự tính đường mới thẳng về tổ (xem _update_returning_ants)
            self.path_len[got_idx] = 0
            self.path_idx[got_idx] = 0

        # --- "Uống" nước tại mép nước: kiến tìm ăn đi tình cờ NGANG SÁT
        # mép nước có thể tranh thủ uống 1 ngụm mang về tổ, y hệt nhặt
        # thức ăn - chỉ xét những con VẪN CÒN đang STATE_SEARCHING thật sự
        # (tay không, chưa vừa nhặt được thức ăn ở trên). Xác suất nhỏ mỗi
        # tick (WATER_PICKUP_PROB) thay vì uống ngay lập tức.
        still_searching = active[~got_food]
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
                    self.path_len[drink_idx] = 0
                    self.path_idx[drink_idx] = 0
                    self.bounce_ticks[drink_idx] = cfg.BOUNCE_DURATION_TICKS

    def _update_returning_ants(self, idx):
        nest_x, nest_y = self.nest_pos
        need_path = idx[self.path_len[idx] == 0]
        if len(need_path) > 0:
            for i in need_path:
                if self._path_budget <= 0:
                    break
                if self._assign_new_path(i, (self.x[i], self.y[i]), (nest_x, nest_y)):
                    self._path_budget -= 1

        active = idx[self.path_len[idx] > 0]
        if len(active) == 0:
            return
        self._follow_paths(active, cfg.ANT_SPEED, allow_pause=True)

        # Để lại vệt mùi pheromone dọc đường - dùng để VẼ trực quan
        # (render_surface.py) VÀ để TUYỂN MỘ các kiến khác đang tìm ăn
        # (xem _sample_recruit_candidates) - lượng để lại TỈ LỆ với giá
        # trị đang tha (self.carry_amount): tìm được nguồn ăn càng giàu
        # thì vệt mùi dẫn tới đó càng đậm, càng hút được nhiều đồng đội
        # khác, đúng cơ chế tuyển mộ của kiến thật.
        xi = self._wrap_indices(self.x[active])
        yi = self._wrap_indices(self.y[active])
        pher_amount = cfg.PHEROMONE_DEPOSIT * np.clip(self.carry_amount[active], 0.3, None)
        self.surface.deposit_pheromone(xi, yi, pher_amount)
        self.surface.deposit_visit(xi, yi)

        dist = np.hypot(self.x[active] - nest_x, self.y[active] - nest_y)
        arrived = active[dist < cfg.ARRIVE_THRESHOLD]
        if len(arrived) > 0:
            # Chui xuống giếng: "thang máy" đưa thẳng xuống ĐÚNG tầng cần
            # tới - tha thức ăn thì xuống tầng kho, tha nước thì xuống tầng
            # bể trữ nước (2 tầng RIÊNG BIỆT) - depth đổi tức thời, xuất
            # hiện ngay tại điểm giếng (vị trí lỗ tổ) trên tầng đó rồi đi bộ
            # 2D tới phòng.
            is_water = self.carry_type[arrived] == 2
            self.layer[arrived] = cfg.LAYER_UNDERGROUND
            self.depth[arrived] = np.where(
                is_water, self.underground.water_depth, self.underground.storage_depth
            )
            self.x[arrived] = self.underground.shaft_xy[0]
            self.y[arrived] = self.underground.shaft_xy[1]
            self.state[arrived] = cfg.STATE_UG_TO_STORAGE
            self.path_len[arrived] = 0
            self.path_idx[arrived] = 0

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
        target_theta = np.arctan2(dy, dx)
        self.theta[idx] = _turn_limited(self.theta[idx], target_theta, cfg.MAX_TURN_RATE_PER_TICK)
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
                    self.bounce_ticks[food_idx] = cfg.BOUNCE_DURATION_TICKS

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
                    self.bounce_ticks[water_idx] = cfg.BOUNCE_DURATION_TICKS
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
            center, radius = self.underground.room_center_and_radius_by_id(
                int(room_id_val), founding_phase=self.founding_phase
            )
            if center is None:
                continue
            sub = idx[self.dwell_room_id[idx] == room_id_val]
            self.theta[sub] += np.random.uniform(-cfg.TURN_NOISE, cfg.TURN_NOISE, len(sub)).astype(np.float32)
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
        self.theta[idx] = self.theta[idx] + np.random.uniform(-cfg.TURN_NOISE, cfg.TURN_NOISE, len(idx)).astype(np.float32)
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

    def _update_undertakers(self):
        """Necrophoresis (thợ mai táng) - kiến NURSE đang RẢNH VIỆC (ở kho,
        chưa có chuyến thức ăn nào để lấy) tình nguyện tạm gác việc, đi
        khiêng 1 xác đồng đội vừa chết dưới hầm (self.underground.
        pending_corpses - xem register_corpse trong world.py) về Nghĩa
        địa, rồi tự quay lại công việc bình thường. Đây là hành vi CÓ THẬT
        ở kiến ngoài đời (undertaker ants): xác không tự "biến mất" một
        cách trừu tượng, phải có 1 con kiến thực sự tới khiêng.

        Chỉ kiểm tra ĐỊNH KỲ (UNDERTAKER_CHECK_INTERVAL) việc PHÂN CÔNG
        MỚI - xác không "cấp bách" tới mức phải phản ứng ngay lập tức.
        LƯU Ý: throttle này CHỈ áp dụng cho bước tìm-nurse-rảnh-để-phân-
        công; bước DI CHUYỂN của các nurse ĐANG TRÊN ĐƯỜNG (đã được phân
        công từ trước) vẫn phải chạy MỌI TICK như bình thường - nhốt cả 2
        chung 1 điều kiện early-return từng là 1 lỗi thực tế đã gặp: khiến
        nurse đang khiêng xác chỉ nhích 1 tick trong mỗi 20 tick, mất gấp
        20 LẦN thời gian di chuyển thật sự cần."""
        if self.tick_count % cfg.UNDERTAKER_CHECK_INTERVAL == 0 and self.underground.pending_corpses:
            idle_mask = self.alive & (self.job == cfg.JOB_NURSE) & (self.state == cfg.STATE_NURSE_AT_STORAGE)
            idle_idx = np.where(idle_mask)[0]
            if len(idle_idx) > 0:
                n_needed = min(len(idle_idx), len(self.underground.pending_corpses))
                chosen = np.random.choice(idle_idx, size=n_needed, replace=False)
                for i in chosen:
                    corpse = self.underground.claim_next_pending_corpse()
                    if corpse is None:
                        break
                    cx, cy, cdepth = corpse
                    self.undertaker_target_x[i] = cx
                    self.undertaker_target_y[i] = cy
                    self.depth[i] = cdepth
                    self.x[i] = self.underground.shaft_xy[0]
                    self.y[i] = self.underground.shaft_xy[1]
                    self.state[i] = cfg.STATE_UNDERTAKER_TO_CORPSE

        # --- đang đi tới vị trí xác ---
        mask = self.alive & (self.state == cfg.STATE_UNDERTAKER_TO_CORPSE)
        if np.any(mask):
            idx = np.where(mask)[0]
            tx, ty = self.undertaker_target_x[idx], self.undertaker_target_y[idx]
            dx, dy = tx - self.x[idx], ty - self.y[idx]
            dist = np.hypot(dx, dy)
            self.theta[idx] = np.arctan2(dy, dx)
            step = np.minimum(dist, cfg.UG_SPEED)
            safe = np.where(dist < 1e-6, 1.0, dist)
            self.x[idx] += dx / safe * step
            self.y[idx] += dy / safe * step
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                # Nhặt xác lên - "tha" nó (dùng lại đúng cờ carrying như
                # tha thức ăn/nước, để tự động đổi màu/sprite khi vẽ,
                # không cần thêm 1 kiểu vẽ riêng cho việc này) rồi lên
                # đường mang tới Nghĩa địa.
                self.carrying[arrived] = True
                self.depth[arrived] = self.underground.graveyard_depth
                self.x[arrived] = self.underground.shaft_xy[0]
                self.y[arrived] = self.underground.shaft_xy[1]
                self.state[arrived] = cfg.STATE_UNDERTAKER_TO_GRAVEYARD
                self.bounce_ticks[arrived] = cfg.BOUNCE_DURATION_TICKS

        # --- đang khiêng xác về Nghĩa địa ---
        mask = self.alive & (self.state == cfg.STATE_UNDERTAKER_TO_GRAVEYARD)
        if np.any(mask):
            idx = np.where(mask)[0]
            dist = self._move_towards_2d(idx, self.underground.graveyard, cfg.UG_SPEED)
            arrived = idx[dist < cfg.ARRIVE_THRESHOLD]
            if len(arrived) > 0:
                self.underground.add_corpse(len(arrived))
                self.carrying[arrived] = False
                self.depth[arrived] = self.underground.storage_depth
                self.x[arrived] = self.underground.shaft_xy[0]
                self.y[arrived] = self.underground.shaft_xy[1]
                self.state[arrived] = cfg.STATE_NURSE_AT_STORAGE
                self.bounce_ticks[arrived] = cfg.BOUNCE_DURATION_TICKS

    def _update_guard_inspections(self):
        """Lính gác đang trực (STATE_GUARD_DUTY) CHẠM RÂU kiểm tra bất kỳ
        đồng đội nào đi ngang qua trạm gác (quanh giếng lên mặt đất, ở
        đúng tầng phòng gác) - hành vi nhận diện mùi tổ (nestmate
        recognition) THẬT của loài kiến, không phải đứng canh vô tri.
        Thuần túy hiệu ứng hình ảnh (self.inspection_events, vẽ giống
        trophallaxis nhưng màu khác ở render_underground.py) - game không
        có khái niệm "kiến lạ" nên không chặn đường ai cả."""
        guards_on_duty = np.where(self.alive & self.is_guard & (self.state == cfg.STATE_GUARD_DUTY))[0]
        if len(guards_on_duty) == 0:
            return
        shaft = self.underground.shaft_xy
        guard_depth = self.underground.guard_depth
        # Ứng viên bị kiểm tra: bất kỳ con nào KHÔNG PHẢI lính đang trực,
        # đang ở đúng tầng phòng gác, còn sống hẳn (không đang hấp hối),
        # và không vừa được kiểm tra gần đây.
        passersby = np.where(
            self.alive
            & (self.dying_ticks == 0)
            & (self.depth == guard_depth)
            & ~(self.is_guard & (self.state == cfg.STATE_GUARD_DUTY))
            & (self.inspect_cooldown == 0)
        )[0]
        if len(passersby) == 0:
            return
        dx = self.x[passersby] - shaft[0]
        dy = self.y[passersby] - shaft[1]
        near = passersby[(dx * dx + dy * dy) <= cfg.GUARD_INSPECT_RADIUS ** 2]
        if len(near) == 0:
            return
        roll = np.random.random(len(near)) < cfg.GUARD_INSPECT_PROB
        chosen = near[roll]
        if len(chosen) == 0:
            return
        guard_pick = np.random.choice(guards_on_duty, size=len(chosen))
        self.inspect_cooldown[chosen] = cfg.GUARD_INSPECT_COOLDOWN_TICKS
        tick_now = self.tick_count
        for gi, pi in zip(guard_pick.tolist(), chosen.tolist()):
            self.inspection_events.append((
                float(self.x[gi]), float(self.y[gi]),
                float(self.x[pi]), float(self.y[pi]),
                tick_now, int(self.depth[pi]),
            ))
        if len(self.inspection_events) > 300:
            self.inspection_events = self.inspection_events[-300:]

    def _update_grooming(self):
        """Chăm sóc lẫn nhau (allogrooming) giữa các kiến đang RẢNH RỖI
        dưới hầm (STATE_DWELL) - hành vi xã hội phổ biến thật của loài
        kiến, KHÁC trophallaxis (không phải cho ăn, chỉ là chải chuốt/làm
        sạch cho nhau). Thuần túy hiệu ứng hình ảnh - trong lúc chăm sóc,
        2 con vẫn cứ "lượn" bình thường (không tự đứng yên), render sẽ tự
        vẽ 1 đường nối ngắn giữa 2 con khi chúng đủ gần."""
        ending = np.where(self.groom_ticks == 1)[0]
        if len(ending) > 0:
            self.groom_cooldown[ending] = cfg.GROOM_COOLDOWN_TICKS
            self.groom_partner[ending] = -1
        self.groom_ticks = np.maximum(0, self.groom_ticks - 1).astype(np.int16)
        self.groom_cooldown = np.maximum(0, self.groom_cooldown - 1).astype(np.int16)

        free = np.where(
            self.alive & (self.dying_ticks == 0) & (self.state == cfg.STATE_DWELL)
            & (self.groom_ticks == 0) & (self.groom_cooldown == 0)
        )[0]
        if len(free) < 2:
            return
        # So khoảng cách từng cặp - O(k^2) với k = số kiến RẢNH RỖI, luôn
        # rất nhỏ so với tổng đàn (đa số đang làm việc/tuần tra) nên chấp
        # nhận được, không cần cây không gian (KD-tree) cho việc này.
        xs, ys, ds = self.x[free], self.y[free], self.depth[free]
        dx = xs[:, None] - xs[None, :]
        dy = ys[:, None] - ys[None, :]
        same_depth = ds[:, None] == ds[None, :]
        close = same_depth & (dx * dx + dy * dy <= cfg.GROOM_RADIUS ** 2)
        np.fill_diagonal(close, False)
        pairs = np.argwhere(close)
        if len(pairs) == 0:
            return
        used = set()
        for a_local, b_local in pairs:
            a, b = int(free[a_local]), int(free[b_local])
            if a in used or b in used:
                continue
            if np.random.random() >= cfg.GROOM_PROB:
                continue
            used.add(a)
            used.add(b)
            self.groom_ticks[a] = cfg.GROOM_DURATION_TICKS
            self.groom_ticks[b] = cfg.GROOM_DURATION_TICKS
            self.groom_partner[a] = b
            self.groom_partner[b] = a

    def _update_haulers(self, enemy):
        """Khiêng mồi lớn theo nhóm (cooperative transport) - xem HAUL_*
        trong config.py + EnemyManager._spawn_carcass()/_decay_carcass()
        trong enemy.py. Các kiến ở STATE_HAUL_APPROACH (đang trên đường
        tới xác, được _update_searching_ants() điều tới) tự đi theo path
        đã tính; tới nơi thì đứng CHỜ (STATE_HAUL_GRIP) - đủ HAUL_MIN_ANTS
        con cùng chờ thì CẢ NHÓM đồng loạt chuyển sang khiêng về tổ (tái
        sử dụng NGUYÊN VẸN STATE_RETURNING có sẵn, y hệt tha thức ăn
        thường - chỉ khác carry_amount lớn hơn hẳn, chia đều cho cả
        nhóm). Nếu xác RỮA MẤT (hết HAUL_DECAY_TICKS) trước khi gom đủ
        người, mọi kiến đang tới/đang chờ đều BỎ CUỘC, quay lại dò tìm ăn
        bình thường."""
        if enemy is None:
            return
        hauling = self.alive & np.isin(self.state, (cfg.STATE_HAUL_APPROACH, cfg.STATE_HAUL_GRIP))
        if not np.any(hauling):
            return

        if not enemy.carcass_active:
            # Xác đã rữa mất trước khi kịp gom đủ người - moi kien dang
            # tham gia deu bo cuoc, quay lai dam kien tim an binh thuong
            # (mat het tien do da di, phai dò tim dich moi tu dau)
            idx = np.where(hauling)[0]
            self.state[idx] = cfg.STATE_SEARCHING
            self.path_len[idx] = 0
            self.path_idx[idx] = 0
            return

        # --- đang trên đường tới xác ---
        approach_mask = self.alive & (self.state == cfg.STATE_HAUL_APPROACH)
        if np.any(approach_mask):
            idx = np.where(approach_mask)[0]
            active = idx[self.path_len[idx] > 0]
            if len(active) > 0:
                self._follow_paths(active, cfg.ANT_SPEED)
            # path_len chỉ về 0 khi vừa đi hết waypoint CUỐI (đúng vị trí
            # xác) - xem _follow_paths(); ăn chắc bằng cách CHỈ xét những
            # con vừa được _follow_paths() xử lý ở trên (active), tránh
            # nhầm với 1 con lỡ chưa từng có path hợp lệ (không nên xảy ra
            # vì chỉ vào state này sau khi _assign_new_path thành công,
            # nhưng phòng hờ vẫn hơn).
            arrived = active[self.path_len[active] == 0]
            if len(arrived) > 0:
                self.state[arrived] = cfg.STATE_HAUL_GRIP

        # --- đủ người thì cùng khiêng về, chưa đủ thì tiếp tục đứng chờ ---
        grip_idx = np.where(self.alive & (self.state == cfg.STATE_HAUL_GRIP))[0]
        if len(grip_idx) >= cfg.HAUL_MIN_ANTS:
            per_ant = enemy.carcass_food_value / len(grip_idx)
            self.carrying[grip_idx] = True
            self.carry_type[grip_idx] = 1
            self.carry_amount[grip_idx] = per_ant
            self.state[grip_idx] = cfg.STATE_RETURNING
            self.path_len[grip_idx] = 0
            self.path_idx[grip_idx] = 0
            self.total_food_collected += len(grip_idx)
            self.bounce_ticks[grip_idx] = cfg.BOUNCE_DURATION_TICKS
            enemy.carcass_active = False
            enemy.total_carcasses_hauled += 1

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
    def _update_guards(self, enemy, invasion=None):
        """Lính gác (self.is_guard): mặc định lượn vô thời hạn trong phòng
        gác cửa (STATE_GUARD_DUTY); nếu có kẻ thù TỰ NHIÊN xuất hiện đủ gần
        lỗ tổ HOẶC đàn kiến NGOẠI LAI đang tiến/đánh ngay tại cửa hang, LAO
        LÊN mặt đất nghênh chiến (việc giao chiến với đàn ngoại lai được xử
        lý trong InvasionManager - lính gác chỉ cần CÓ MẶT trên mặt đất gần
        tổ để tính là "phòng thủ"); hết mối đe dọa thì tự quay về đóng quân
        lại."""
        guard_mask = self.alive & self.is_guard
        if not np.any(guard_mask):
            return

        nest_x, nest_y = self.nest_pos
        threat_natural = enemy is not None and enemy.active and (
            (enemy.x - nest_x) ** 2 + (enemy.y - nest_y) ** 2 < cfg.GUARD_ALERT_RADIUS ** 2
        )
        threat_invasion = invasion is not None and invasion.active and np.any(
            invasion.alive & (invasion.layer == cfg.LAYER_SURFACE)
            & ((invasion.x - nest_x) ** 2 + (invasion.y - nest_y) ** 2 < cfg.GUARD_ALERT_RADIUS ** 2)
        )
        threat_near_nest = threat_natural or threat_invasion

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
                center, radius = self.underground.room_center_and_radius_by_id(
                    5, founding_phase=self.founding_phase
                )
                if center is not None:
                    self.theta[idx] += np.random.uniform(-cfg.TURN_NOISE, cfg.TURN_NOISE, len(idx)).astype(np.float32)
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
            elif threat_invasion:
                pass  # đàn ngoại lai tự tìm đến tổ - lính gác đứng yên tại tổ để nghênh chiến
            else:
                self.state[idx] = cfg.STATE_GUARD_RETURN  # hết mối đe dọa - rút về

        # --- Đang rút quân về giếng để xuống lại phòng gác ---
        return_mask = guard_mask & (self.state == cfg.STATE_GUARD_RETURN)
        if np.any(return_mask):
            idx = np.where(return_mask)[0]
            need_path = idx[self.path_len[idx] == 0]
            for i in need_path:
                if self._path_budget <= 0:
                    break
                if self._assign_new_path(i, (self.x[i], self.y[i]), (nest_x, nest_y)):
                    self._path_budget -= 1
            active = idx[self.path_len[idx] > 0]
            if len(active) > 0:
                self._follow_paths(active, cfg.GUARD_SPEED)
                dist = np.hypot(self.x[active] - nest_x, self.y[active] - nest_y)
                arrived = active[dist < cfg.ARRIVE_THRESHOLD]
                if len(arrived) > 0:
                    self.layer[arrived] = cfg.LAYER_UNDERGROUND
                    self.depth[arrived] = self.underground.guard_depth
                    self.x[arrived] = self.underground.shaft_xy[0]
                    self.y[arrived] = self.underground.shaft_xy[1]
                    self.state[arrived] = cfg.STATE_GUARD_DUTY
                    self.path_len[arrived] = 0
                    self.path_idx[arrived] = 0

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
            died = died[self.dying_ticks[died] == 0]  # đang hấp hối rồi thì bỏ qua, không "trúng số" chồng thêm lần nữa
            if len(died) > 0:
                # KHÔNG chết ngay - chuyển sang trạng thái HẤP HỐI (xem
                # cfg.DYING_DURATION_TICKS/update()): đứng khựng lại run
                # rẩy tại chỗ trong 1 khoảng ngắn rồi mới thực sự chết hẳn
                # (finalize ở đầu update() của tick kế tiếp), thay vì biến
                # mất/thành xác NGAY LẬP TỨC như trước - mô phỏng cảnh hấp
                # hối vì già/đói/khát thật, khác hẳn chết vì giao chiến
                # (vẫn tức thời, xem enemy.py/invasion.py/game_state.py).
                self.dying_ticks[died] = cfg.DYING_DURATION_TICKS
                self.dying_x[died] = self.x[died]
                self.dying_y[died] = self.y[died]
                self.dying_layer[died] = self.layer[died]
                self.dying_depth[died] = self.depth[died]

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
        # Nếu ĐANG lập tổ lúc lứa này nở, đánh dấu nanitic (nhỏ con hơn hẳn
        # - xem giải thích đầy đủ ở chỗ khai báo self.is_nanitic)
        self.is_nanitic[idx] = self.founding_phase
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
            self.depth[guard_idx] = self.underground.guard_depth
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
            "foragers_total": int(np.sum(alive & (~self.is_guard) & (
                (self.role == cfg.ROLE_MAJOR) | (is_minor & (self.job == cfg.JOB_FORAGER))
            ))),
            "nurses_total": int(np.sum(alive & is_minor & (self.job == cfg.JOB_NURSE))),
            "attendants_total": int(np.sum(alive & is_minor & (self.job == cfg.JOB_ATTENDANT))),
            "founding_phase": self.founding_phase,
            "queen_energy": self.queen_energy,
        }
