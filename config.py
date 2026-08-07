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
ROOM_Z_STORAGE = -8.0
ROOM_Z_NURSERY = -8.0
ROOM_Z_QUEEN = -15.0
WORLD_DEPTH = 20.0          # độ sâu tối đa của khối hộp hiển thị (để vẽ khung kính)

# ----- Kiến -----
NUM_ANTS = 600              # bản 3D vẽ từng con bằng 1 mesh riêng nên đặt vừa
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

# ----- Thức ăn trên mặt đất -----
FOOD_CLUSTERS = 18
FOOD_PER_CLUSTER = 6.0
FOOD_CLUSTER_RADIUS = 2

# ----- Tổ kiến -----
NEST_POS = (GRID_SIZE // 2, GRID_SIZE // 2)   # vị trí lỗ tổ trên mặt đất & giếng hầm
NEST_RADIUS = 1.2

# Vị trí các phòng dưới hầm: (x, y, z) - x,y cùng hệ tọa độ lưới với mặt đất,
# z là độ sâu (âm = xuống sâu), để khi nhìn 3D các phòng thật sự nằm dưới
# lỗ tổ ở các tầng sâu khác nhau như tổ kiến thật.
ROOM_STORAGE = (NEST_POS[0] - 7, NEST_POS[1] + 5, ROOM_Z_STORAGE)
ROOM_NURSERY = (NEST_POS[0] + 7, NEST_POS[1] + 5, ROOM_Z_NURSERY)
ROOM_QUEEN   = (NEST_POS[0], NEST_POS[1] + 9, ROOM_Z_QUEEN)
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
FOOD_RESPAWN_INTERVAL = 600  # cứ mỗi bấy nhiêu tick, có 1 cụm thức ăn mới
                             # xuất hiện ngẫu nhiên (mô phỏng thức ăn theo mùa)
FOOD_RESPAWN_AMOUNT = 5.0    # lượng thức ăn của cụm mới mỗi lần tái sinh
UPKEEP_FOOD_PER_ANT_PER_TICK = 0.0004  # mỗi kiến còn sống tiêu hao 1 lượng
                             # nhỏ thức ăn từ kho mỗi tick để duy trì sự sống
                             # (không chỉ dùng thức ăn để sinh sản) - nếu đàn
                             # quá đông mà không đủ kiến đi kiếm ăn, kho sẽ cạn
