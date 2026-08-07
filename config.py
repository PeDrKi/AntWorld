"""Cấu hình chung cho mô phỏng thế giới kiến (bản 3D)."""

# ----- Kích thước bản đồ (mặt phẳng ngang X/Y) -----
GRID_SIZE = 50              # số ô mỗi chiều - giảm so với bản 2D để khối 3D
                            # không quá to, vẫn đủ chi tiết khi xoay/zoom
BASE_CELL_PX = 10           # (giữ lại, không dùng trong bản 3D nhưng vài chỗ tham chiếu)

# ----- Cửa sổ -----
SCREEN_W, SCREEN_H = 1280, 800
FPS = 60

# ----- Trục Z (độ sâu, 0 = mặt đất, càng âm càng sâu) -----
SURFACE_Z = 0.0
SHAFT_TOP_Z = -0.6          # miệng giếng, ngay dưới mặt đất
ROOM_Z_STORAGE = -6.0       # tầng nông nhất - kho gần cửa để tha đồ nhanh
ROOM_Z_NURSERY = -11.0      # tầng giữa - ấu trùng cần được bảo vệ hơn kho
ROOM_Z_QUEEN = -17.0        # tầng sâu nhất - chúa được bảo vệ kỹ nhất
WORLD_DEPTH = 20.0          # độ sâu tối đa của khối hộp hiển thị (để vẽ khung kính)

# ----- Kiến -----
NUM_ANTS = 100              # bản 3D vẽ từng con bằng 1 mesh riêng nên đặt vừa
                            # phải để giữ khung hình mượt; có thể tăng dần và
                            # theo dõi FPS hiển thị góc màn hình
ANT_SPEED = 0.14            # số ô di chuyển mỗi tick (mặt phẳng ngang)
UG_SPEED = 0.22             # tốc độ di chuyển trong hầm (đường thẳng 3D nên
                            # nhanh hơn 1 chút để không mất quá lâu xuống sâu)
TURN_NOISE = 0.35           # độ nhiễu góc quay mỗi tick (radian)
SENSE_DIST = 1.6            # khoảng cách "ngửi" pheromone phía trước
SENSE_ANGLE = 0.6           # góc lệch 2 bên khi ngửi pheromone

# ----- Pheromone (mùi dẫn đường về tổ khi tha thức ăn) -----
PHEROMONE_DECAY = 0.985     # mỗi tick pheromone giảm còn 98.5%
PHEROMONE_DEPOSIT = 1.0     # lượng mùi để lại mỗi tick khi đang tha đồ
PHEROMONE_MAX = 8.0

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
                                        # KHÔNG THỂ SINH SẢN (xem BIRTH_WATER_COST
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
NUM_RIVAL_ANTS = 100        # CÙNG quy mô với tổ chính - đã kiểm thử thấy
                            # nếu ít quân hơn, tổ đối thủ gần như luôn thua
                            # cuộc cạnh tranh thức ăn (đàn đông hơn có diện
                            # bao phủ tìm kiếm lớn hơn, chiếm thức ăn trước)
ROOM_RADIUS = 2.6

# Xác suất 1 con kiến sau khi giao thức ăn ở kho sẽ trở thành "nurse"
# (mang thức ăn tiếp sang phòng ấu trùng) thay vì quay lại mặt đất ngay
NURSE_PROBABILITY = 0.35

# ----- Trạng thái kiến (state machine) -----
STATE_SEARCHING = 0        # trên mặt đất, đang tìm thức ăn
STATE_RETURNING = 1        # trên mặt đất, đang tha thức ăn về tổ
STATE_UG_TO_STORAGE = 2    # dưới hầm, đang đi tới kho
STATE_UG_TO_NURSERY = 3    # dưới hầm, nurse đang mang đồ tới phòng ấu trùng
STATE_UG_TO_SHAFT = 4      # dưới hầm, đang quay lại giếng để lên mặt đất

LAYER_SURFACE = 0
LAYER_UNDERGROUND = 1

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

# ----- Sinh sản (chúa cần thức ăn để sinh kiến mới) -----
BIRTH_CHECK_INTERVAL = 60   # cứ mỗi bấy nhiêu tick (~1 giây ở 60 FPS), chúa
                            # thử sinh 1 lứa kiến mới
BIRTH_FOOD_COST = 4          # số đơn vị thức ăn (lấy từ kho) cần cho 1 kiến mới
BIRTH_WATER_COST = 2          # số đơn vị nước cần thêm cho 1 kiến mới - nếu
                              # thiếu nước, chúa KHÔNG sinh được dù đủ thức ăn
BIRTH_BATCH_SIZE = 2         # số kiến sinh ra mỗi lần (nếu đủ thức ăn) -
                            # đặt đủ cao để bù được tốc độ chết già/chết đói
                            # trong điều kiện bình thường (không có kẻ thù)

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
NURSERY_CONSUMPTION_PER_TICK = 0.10  # ấu trùng tiêu thụ dần thức ăn trong
                             # phòng ấu trùng để lớn lên - QUAN TRỌNG: nếu
                             # không có cơ chế này, thức ăn đưa vào phòng ấu
                             # trùng sẽ tích lũy vĩnh viễn không dùng đến,
                             # dần rút cạn toàn bộ tài nguyên khả dụng của tổ
UPKEEP_FOOD_PER_ANT_PER_TICK = 0.0004  # mỗi kiến còn sống tiêu hao 1 lượng
                             # nhỏ thức ăn từ kho mỗi tick để duy trì sự sống
                             # (không chỉ dùng thức ăn để sinh sản) - nếu đàn
                             # quá đông mà không đủ kiến đi kiếm ăn, kho sẽ cạn
