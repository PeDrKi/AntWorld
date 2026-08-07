"""Cấu hình chung cho mô phỏng thế giới kiến (bản 2D - từng lớp/tầng)."""

# ----- Kích thước bản đồ (mặt phẳng ngang X/Y, dùng chung cho MỌI tầng) -----
GRID_SIZE = 50
BASE_CELL_PX = 16           # kích thước 1 ô lưới tính bằng pixel ở mức zoom 1x

# ----- Cửa sổ -----
SCREEN_W, SCREEN_H = 1280, 800
FPS = 60

# ----- Độ sâu = TẦNG rời rạc (0 = mặt đất, số càng lớn càng sâu) -----
# Thay vì 1 khối 3D duy nhất, thế giới giờ là 1 chồng các tầng 2D phẳng,
# giống lát cắt ngang của bể nuôi kiến - mỗi tầng là 1 bản đồ (x, y) riêng.
# Giữ CTRL + lăn chuột để chuyển qua lại giữa các tầng.
LAYER_SURFACE_DEPTH = 0     # tầng 0 LUÔN LUÔN là mặt đất
DEPTH_STORAGE = 1           # tầng nông nhất dưới hầm - kho gần cửa
DEPTH_NURSERY = 2           # tầng giữa - ấu trùng
DEPTH_QUEEN = 3             # tầng sâu nhất - phòng chúa
DUG_ROOM_FIRST_DEPTH = 4    # phòng đầu tiên người chơi tự đào -> tầng 4,
                            # phòng đào tiếp theo -> tầng 5, 6, ... (mỗi
                            # phòng tự đào chiếm 1 tầng riêng, càng đào
                            # thêm càng "xuống sâu" thêm 1 tầng mới)

# ----- Kiến -----
NUM_ANTS = 20               # số kiến KHỞI TẠO (không còn là giới hạn tối đa -
                            # đàn có thể lớn lên qua sinh sản, xem MAX_ANTS_PER_COLONY)
                            # phải để giữ khung hình mượt; có thể tăng dần và
                            # theo dõi FPS hiển thị góc màn hình
ANT_SPEED = 0.14            # số ô di chuyển mỗi tick (mặt phẳng ngang)
UG_SPEED = 0.22             # tốc độ di chuyển trong hầm (đường thẳng 3D nên
                            # nhanh hơn 1 chút để không mất quá lâu xuống sâu)
TURN_NOISE = 0.35           # độ nhiễu góc quay mỗi tick (radian)
SENSE_DIST = 1.6            # khoảng cách "ngửi" pheromone phía trước
SENSE_ANGLE = 0.6           # góc lệch 2 bên khi ngửi pheromone

# ----- Né vật cản (đá/nước): "bám tường" thay vì dội ngẫu nhiên -----
# LƯU Ý: nếu chỉ xoay 1 góc ngẫu nhiên rồi lập tức để mùi pheromone/hướng
# về tổ kéo lại như cũ, kiến sẽ dội qua dội lại NGAY TẠI rìa vật cản (kẹt
# thành từng cụm dài bám sát đá/nước) vì lực kéo về pheromone/tổ mạnh hơn
# nhiều so với góc né. Cách khắc phục: khi né, kiến "khóa" 1 hướng né cố
# định (trái HOẶC phải, không đổi ngẫu nhiên mỗi lần) và tạm thời GIẢM HẲN
# lực kéo về pheromone/tổ trong vài chục tick để có thời gian trượt dọc
# theo rìa vật cản ra ngoài, giống kiến thật đi vòng quanh chướng ngại vật.
AVOID_COOLDOWN_TICKS = 25    # số tick "khóa hướng né" mỗi lần chạm vật cản
                             # (được LÀM MỚI lại mỗi lần vẫn còn bị chặn, nên
                             # vật cản càng to thì kiến càng có nhiều thời
                             # gian trượt vòng qua trước khi bị kéo lại)
AVOID_TURN_ANGLE = 1.35      # góc né khi vừa chạm vật cản (~77 độ, gần vuông
                             # góc với hướng đang đi - để TRƯỢT DỌC theo rìa
                             # thay vì chỉ hơi chếch)
SEARCH_BIAS_SUPPRESS_FACTOR = 0.1   # trong lúc đang né, lực kéo theo mùi
                             # pheromone khi tìm ăn bị giảm còn bấy nhiêu %
RETURN_NEST_WEIGHT_AVOIDING = 0.08  # trong lúc đang né, tỉ trọng "hướng
                             # thẳng về tổ" mỗi tick giảm xuống bấy nhiêu
                             # (bình thường là 0.75 - xem _update_surface_ants)

# ----- Pheromone (mùi dẫn đường về tổ khi tha thức ăn) -----
PHEROMONE_DECAY = 0.985     # mỗi tick pheromone giảm còn 98.5%
PHEROMONE_DEPOSIT = 1.0     # lượng mùi để lại mỗi tick khi đang tha đồ
PHEROMONE_MAX = 8.0

# ----- Pheromone báo động (khi có kẻ thù trên mặt đất) -----
DANGER_PHEROMONE_DECAY = 0.85   # giảm RẤT nhanh - chỉ còn tác dụng ngay
                                # sát nơi kẻ thù vừa xuất hiện, tan trong
                                # vài chục tick chứ không lan rộng/tồn lâu
DANGER_DEPOSIT_AMOUNT = 3.0     # lượng mùi báo động kẻ thù để lại mỗi tick
DANGER_DEPOSIT_RADIUS = 2        # bán kính lan tỏa quanh vị trí kẻ thù -
                                # hẹp, không phủ kín cả khu vực quanh tổ
DANGER_PHEROMONE_MAX = 10.0
DANGER_PRESENCE_THRESHOLD = 1.5  # chỉ né khi mùi đủ đậm (gần kẻ thù thật
                                # sự), tránh phản ứng thái quá với dấu vết
                                # mờ nhạt còn sót lại
DANGER_AVOID_WEIGHT = 0.4        # trọng số né tránh - NHẸ, chỉ là 1 xu
                                # hướng lệch thêm, không lấn át hẳn hành vi
                                # tìm ăn bình thường (đã kiểm thử: đặt cao
                                # hơn nhiều sẽ làm tê liệt việc tìm ăn khi
                                # kẻ thù ở gần tổ, gây sụp đổ dân số)

# ----- Thức ăn trên mặt đất (đa dạng loại) -----
FOOD_CLUSTERS = 26           # tăng so với bản 1 tổ vì giờ có thêm tổ đối
                             # thủ cùng cạnh tranh nguồn thức ăn này
FOOD_CLUSTER_RADIUS = 2

# 3 loại thức ăn khác nhau về màu sắc và giá trị dinh dưỡng mỗi lần nhặt
FOOD_TYPE_SEED = 0     # Hạt - phổ biến, giá trị thường
FOOD_TYPE_INSECT = 1   # Côn trùng - hiếm hơn, giá trị dinh dưỡng cao (đạm)
FOOD_TYPE_NECTAR = 2   # Mật hoa - khá phổ biến, giá trị vừa phải

FOOD_TYPE_VALUE = {
    FOOD_TYPE_SEED: 1.0,
    FOOD_TYPE_INSECT: 2.2,
    FOOD_TYPE_NECTAR: 1.4,
}
FOOD_TYPE_COLOR = {
    FOOD_TYPE_SEED: (150, 115, 60),     # nâu hạt
    FOOD_TYPE_INSECT: (150, 40, 40),    # đỏ sẫm
    FOOD_TYPE_NECTAR: (230, 195, 50),   # vàng mật
}
# Tỉ lệ xuất hiện mỗi loại khi 1 cụm thức ăn mới sinh ra (phải cộng lại = 1.0)
FOOD_TYPE_WEIGHTS = {
    FOOD_TYPE_SEED: 0.55,
    FOOD_TYPE_INSECT: 0.20,
    FOOD_TYPE_NECTAR: 0.25,
}
FOOD_PER_CLUSTER = 6.0  # số "đơn vị" thức ăn (không phải giá trị dinh dưỡng)

# ----- Địa hình (chướng ngại vật trên mặt đất) -----
TERRAIN_EMPTY = 0
TERRAIN_ROCK = 1
TERRAIN_WATER = 2

NUM_ROCK_CLUSTERS = 4        # số cụm đá rải ngẫu nhiên lúc khởi tạo - vừa
                             # phải để không cản trở quá mức việc tìm ăn
ROCK_CLUSTER_RADIUS = 1.4
NUM_WATER_CLUSTERS = 4       # số vũng nước rải ngẫu nhiên lúc khởi tạo
WATER_CLUSTER_RADIUS = 2.4
TERRAIN_SAFE_RADIUS_FROM_NEST = 6  # không đặt địa hình quá gần lỗ tổ

# ----- Nước: KHÔNG CHỈ là chướng ngại vật mà còn là tài nguyên sống còn -----
# Kiến không đi được VÀO nước (vẫn chặn đường như trước), nhưng nếu đứng
# đủ GẦN mép nước có thể "uống" mang về - đàn kiến cần nước như cần ăn.
WATER_COLLECT_RADIUS = 2.0     # khoảng cách tới mép nước để có thể "uống"
ERASE_RADIUS = 3.0             # bán kính xóa vật thể (thức ăn/đá/nước)
                               # quanh điểm click của công cụ "Xóa"

# ----- Biểu đồ lịch sử dân số theo thời gian -----
HISTORY_SAMPLE_INTERVAL = 200   # cứ mỗi bấy nhiêu tick lấy mẫu 1 lần
HISTORY_MAX_POINTS = 150        # giữ tối đa bấy nhiêu điểm gần nhất (cũ hơn
                                # sẽ bị loại bỏ dần - tránh phình bộ nhớ)
WATER_BASE_INCOME_PER_TICK = 0.45  # tổ tự động thu được bấy nhiêu nước mỗi
                               # tick MIỄN LÀ còn ít nhất 1 vũng nước trên
                               # bản đồ (đại diện cho việc kiến đi lấy nước
                               # thường xuyên) - nếu bạn lấp hết nước bằng
                               # đá hoặc nước cạn sạch, nguồn thu này = 0
WATER_UPKEEP_PER_ANT_PER_TICK = 0.00035  # mỗi kiến còn sống tiêu hao nước
                                        # mỗi tick để duy trì sự sống
WATER_STARVATION_GRACE_TICKS = 600     # số tick được phép hết nước dự trữ
                                        # trước khi bắt đầu tính chết khát
DEHYDRATION_DEATH_RATE = 0.0003        # xác suất chết PHỤ THÊM mỗi tick khi
                                        # thiếu nước kéo dài - CỐ Ý đặt THẤP:
                                        # hậu quả CHÍNH của thiếu nước là
                                        # KHÔNG THỂ ĐẺ TRỨNG (xem EGG_WATER_COST
                                        # bên dưới), tránh vòng xoáy chết
                                        # chóc tự gia tăng khi ít kiến hơn
                                        # đồng nghĩa ít kiến đi lấy nước hơn

# ----- Tổ kiến (chính - của người chơi) -----
NEST_POS = (GRID_SIZE // 2, GRID_SIZE // 2)   # vị trí lỗ tổ trên mặt đất & giếng hầm
NEST_RADIUS = 1.2

# Vị trí các phòng dưới hầm tính THEO OFFSET so với lỗ tổ (không phải tọa độ
# tuyệt đối) - để có thể dùng chung công thức này cho cả tổ đối thủ đặt ở
# nơi khác trên bản đồ. z là độ sâu tuyệt đối (không đổi theo vị trí ngang).
STORAGE_OFFSET_XY = (-7, 5)
NURSERY_OFFSET_XY = (7, 5)
QUEEN_OFFSET_XY = (0, 9)

# ----- Phân vai kiến (caste) -----
ROLE_MINOR = 0    # thợ nhỏ - đa số, lo tìm ăn/chăm ấu trùng
ROLE_MAJOR = 1    # thợ lớn/lính - ít hơn nhưng khỏe hơn, chuyên bảo vệ tổ
MAJOR_WORKER_RATIO = 0.15   # tỉ lệ lính trong đàn
MAJOR_SIZE_SCALE = 1.7      # lính to hơn thợ thường bao nhiêu lần khi vẽ
MAJOR_DEFENSE_FACTOR = 0.3  # xác suất lính bị kẻ thù giết = bấy nhiêu lần
                            # so với thợ thường (lính "trâu" hơn nhiều)
SOLDIER_DAMAGE_PROB = 0.05  # xác suất 1 lính gây sát thương lên kẻ thù/tick
                            # khi ở trong tầm giao chiến
SOLDIER_DAMAGE_PER_HIT = 1.0
ENEMY_MAX_HEALTH = 9.0      # kẻ thù có máu - lính có thể đánh bại nó thay vì
                            # chỉ chờ nó tự rời đi

# ----- Tổ kiến đối thủ (cạnh tranh tài nguyên trên cùng bản đồ) -----
RIVAL_NEST_POS = (14, 36)   # lệch khỏi trung tâm nhưng KHÔNG ở góc bản đồ,
                            # để không bị bất lợi hình học (diện tích kiếm
                            # ăn khả dụng thấp hơn hẳn tổ chính ở giữa)
NUM_RIVAL_ANTS = 20         # CÙNG quy mô khởi tạo với tổ chính - đàn nào
                            # sinh sản/kiếm ăn tốt hơn sẽ tự lớn nhanh hơn
MAX_ANTS_PER_COLONY = 1000  # giới hạn TỐI ĐA quy mô 1 đàn (bộ nhớ cấp phát
                            # sẵn cho mảng NumPy) - đàn khởi tạo NUM_ANTS con,
                            # rồi tự sinh sản lớn lên dần tới tối đa số này
                            # nếu đủ thức ăn/nước/không gian ấu trùng
ROOM_RADIUS = 3.4

# Xác suất 1 con kiến sau khi giao thức ăn ở kho sẽ trở thành "nurse"
# (mang thức ăn tiếp sang phòng ấu trùng) thay vì quay lại mặt đất ngay
NURSE_PROBABILITY = 0.35

# ----- Trạng thái kiến (state machine) -----
STATE_SEARCHING = 0        # trên mặt đất, đang tìm thức ăn
STATE_RETURNING = 1        # trên mặt đất, đang tha thức ăn về tổ
STATE_UG_TO_STORAGE = 2    # dưới hầm, đang đi tới kho
STATE_UG_TO_NURSERY = 3    # dưới hầm, nurse đang mang đồ tới phòng ấu trùng
STATE_UG_TO_SHAFT = 4      # dưới hầm, đang quay lại giếng để lên mặt đất
STATE_DWELL = 5            # dưới hầm, đang LƯỢN/HOẠT ĐỘNG trong phạm vi 1
                           # phòng (kho/ấu trùng/phòng chúa) 1 lúc trước khi
                           # rời đi - để phòng ngầm có "sự sống" thật sự
                           # thay vì kiến chỉ chạm tâm phòng rồi quay đầu

# Kiến "lượn" trong phòng bao lâu trước khi tiếp tục hành trình (tick mô
# phỏng), và di chuyển nhẹ/chậm ra sao trong lúc đó
DWELL_MIN_TICKS = 40
DWELL_MAX_TICKS = 140
DWELL_SPEED = 0.045         # chậm hơn nhiều so với UG_SPEED - dáng "làm việc"
ROOM_WANDER_FACTOR = 0.82   # chỉ lượn trong phạm vi bấy nhiêu % bán kính
                            # phòng, để không đi lấn ra ngoài rìa hiển thị

LAYER_SURFACE = 0     # dùng cho self.layer của kiến: 0 = đang ở mặt đất
LAYER_UNDERGROUND = 1 # 1 = đang ở dưới hầm (bất kể đang ở tầng ngầm nào -
                      # tầng ngầm CỤ THỂ được lưu riêng ở self.depth, xem ants.py)

ARRIVE_THRESHOLD = 0.6     # khoảng cách coi là "đã đến nơi"

# =======================================================================
# YẾU TỐ BẤT LỢI CHO ĐÀN KIẾN (vòng đời, kẻ thù, tài nguyên có hạn)
# =======================================================================

# ----- Vòng đời & cái chết tự nhiên -----
MAX_AGE_TICKS = 20000       # tuổi thọ "trung bình" (~5-6 phút ở 60 FPS) -
                            # qua mốc này bắt đầu có nguy cơ chết già, tăng
                            # dần theo thời gian (không chết đột ngột hàng loạt)
OLD_AGE_DEATH_RATE = 0.0004 # xác suất chết mỗi tick khi vừa qua MAX_AGE_TICKS
OLD_AGE_DEATH_GROWTH = 8000 # càng già hơn mốc này, xác suất chết càng tăng
                            # nhanh (chia tuổi dư ra cho số này để tính hệ số)
STARVATION_DEATH_RATE = 0.0015  # xác suất chết PHỤ THÊM mỗi tick cho MỌI
                                 # kiến khi phòng ấu trùng hết thức ăn kéo dài
STARVATION_GRACE_TICKS = 400    # số tick phòng ấu trùng được phép "rỗng"
                                 # trước khi bắt đầu tính chết đói

# ----- Trứng & ấu trùng: PHÒNG ẤU TRÙNG THẬT SỰ NUÔI ẤU TRÙNG -----
# Chúa không "sinh" kiến trực tiếp nữa - chúa chỉ ĐẺ TRỨNG (tốn thức ăn từ
# kho); trứng/ấu trùng sau đó lớn lên DẦN trong phòng ấu trùng, ăn đúng chỗ
# thức ăn mà các "nurse" mang tới (food_in_nursery) - hết thức ăn ở đó thì
# lớn rất chậm. Ấu trùng lớn đủ (growth >= 1.0) mới thật sự "nở" thành 1
# kiến thợ mới đi ra ngoài.
EGG_LAY_INTERVAL = 70        # cứ mỗi bấy nhiêu tick, chúa thử đẻ 1 trứng mới
EGG_FOOD_COST = 4            # thức ăn (lấy từ KHO) chúa cần để đẻ 1 trứng
EGG_WATER_COST = 2           # nước cần thêm để đẻ 1 trứng - thiếu nước thì
                             # KHÔNG đẻ được dù đủ thức ăn
LARVA_MAX_COUNT = 40         # số ấu trùng tối đa cùng lúc trong 1 phòng ấu
                             # trùng (giới hạn không gian + hiệu năng hiển thị)
LARVA_GROWTH_PER_TICK = 0.0025      # tốc độ lớn lên mỗi tick khi ĐỦ thức ăn
                             # trong phòng ấu trùng (growth đi từ 0 -> 1)
LARVA_GROWTH_STARVED_FACTOR = 0.15  # lớn chậm hơn nhiều (không phải bằng 0,
                             # để tránh bế tắc hoàn toàn) khi phòng ấu trùng
                             # đang HẾT thức ăn dự trữ
LARVA_FOOD_PER_TICK = 0.02   # MỖI ấu trùng đang lớn tiêu thụ bấy nhiêu thức
                             # ăn trong phòng ấu trùng mỗi tick - đây chính là
                             # nơi thức ăn nurse mang vào THỰC SỰ được dùng
                             # đến, thay vì chỉ là số liệu suông

# ----- Kẻ thù tự nhiên (đe dọa trên mặt đất) -----
ENEMY_SPAWN_COOLDOWN_MIN = 500   # số tick tối thiểu giữa 2 lần kẻ thù xuất hiện
ENEMY_SPAWN_COOLDOWN_MAX = 1200
ENEMY_LIFETIME_TICKS = 900       # kẻ thù tự rời đi sau bấy nhiêu tick
ENEMY_SPEED = 0.20
ENEMY_DETECT_RADIUS = 14         # chỉ đuổi theo kiến trong bán kính này;
                                 # ngoài tầm thì đi lang thang ngẫu nhiên
                                 # (không phải "thợ săn toàn năng" biết hết bản đồ)
ENEMY_KILL_RADIUS = 1.3
ENEMY_KILL_PROB_PER_TICK = 0.01  # xác suất giết 1 con kiến trong tầm/tick
ENEMY_MAX_KILLS_PER_VISIT = 5    # kẻ thù "no" và tự rời đi sau khi giết đủ
                                 # số này - tránh 1 lần xuất hiện xóa sổ cả đàn
ENEMY_TURN_NOISE = 0.5

# ----- Cạnh tranh tài nguyên: thức ăn có hạn, tái sinh chậm theo "mùa" -----
FOOD_RESPAWN_INTERVAL = 350  # cứ mỗi bấy nhiêu tick, có 1 cụm thức ăn mới
                             # xuất hiện ngẫu nhiên (mô phỏng thức ăn theo mùa) -
                             # tăng tần suất so với bản 1 tổ vì giờ có 2 tổ
                             # cùng cạnh tranh chung nguồn thức ăn này
FOOD_RESPAWN_AMOUNT = 5.0    # lượng thức ăn của cụm mới mỗi lần tái sinh
# LƯU Ý: thức ăn trong phòng ấu trùng (food_in_nursery) giờ được TIÊU THỤ
# THẬT SỰ bởi từng ấu trùng đang lớn (xem LARVA_FOOD_PER_TICK ở trên), nên
# không cần thêm 1 cơ chế "rút cạn" chung chung nữa.
UPKEEP_FOOD_PER_ANT_PER_TICK = 0.0004  # mỗi kiến còn sống tiêu hao 1 lượng
                             # nhỏ thức ăn từ kho mỗi tick để duy trì sự sống
                             # (không chỉ dùng thức ăn để sinh sản) - nếu đàn
                             # quá đông mà không đủ kiến đi kiếm ăn, kho sẽ cạn

# =======================================================================
# HIỂN THỊ 2D (pygame) - camera pan/zoom + màu sắc từng tầng
# =======================================================================
MIN_ZOOM = 0.35
MAX_ZOOM = 3.5
ZOOM_STEP = 1.12             # mỗi nấc lăn chuột (không giữ Ctrl) nhân/chia zoom bấy nhiêu

# Màu nền riêng cho từng loại tầng, để luôn biết đang xem tầng nào dù có
# nhìn lướt qua HUD hay không
COLOR_BG_SURFACE = (74, 58, 40)
COLOR_BG_UNDERGROUND = (32, 27, 24)
COLOR_GRID_LINE = (0, 0, 0, 40)
COLOR_GROUND_FILL = (205, 178, 132)
COLOR_SHAFT = (25, 18, 12)

TOOLBAR_H = 88               # chiều cao thanh công cụ dưới màn hình (pixel)
GRAPH_PANEL_W, GRAPH_PANEL_H = 300, 170

# Kho thức ăn: hiển thị thức ăn ĐANG LƯU TRỮ THẬT SỰ dưới dạng 1 đống nhỏ
# các "viên" thức ăn rải trong phòng, thay vì chỉ 1 con số vô hình
STORAGE_FOOD_PER_ICON = 8        # bấy nhiêu đơn vị thức ăn = 1 icon hiển thị
STORAGE_MAX_ICONS = 40           # trần số icon vẽ (tránh rợp hình khi kho đầy)

# Kiến chúa: to hơn hẳn thợ thường, luôn đứng yên (bob nhẹ) giữa phòng chúa
QUEEN_BODY_SCALE = 3.2
