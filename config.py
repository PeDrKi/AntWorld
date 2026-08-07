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
