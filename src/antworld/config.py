"""Cấu hình chung cho mô phỏng thế giới kiến (bản 2D - từng lớp/tầng)."""

# ----- Kích thước bản đồ (mặt phẳng ngang X/Y, dùng chung cho MỌI tầng) -----
GRID_SIZE = 40               # đã giảm 20% so với bản trước (50 -> 40)
BASE_CELL_PX = 16           # kích thước 1 ô lưới tính bằng pixel ở mức zoom 1x

# ----- Cửa sổ -----
SCREEN_W, SCREEN_H = 1280, 800   # kích thước cửa sổ MẶC ĐỊNH lúc mở app -
                                 # cửa sổ giờ CÓ THỂ THAY ĐỔI KÍCH THƯỚC/
                                 # phóng to/thu nhỏ (RESIZABLE), đây chỉ là
                                 # kích thước khởi đầu
MIN_WINDOW_W, MIN_WINDOW_H = 950, 650  # không cho kéo nhỏ hơn mức này -
                                 # tránh vỡ layout thanh công cụ
FPS = 60

# ----- Độ sâu = TẦNG rời rạc (0 = mặt đất, số càng lớn càng sâu) -----
# Thay vì 1 khối 3D duy nhất, thế giới giờ là 1 chồng các tầng 2D phẳng,
# giống lát cắt ngang của bể nuôi kiến - mỗi tầng là 1 bản đồ (x, y) riêng.
# Giữ CTRL + lăn chuột để chuyển qua lại giữa các tầng.
#
# LƯU Ý: 1 TẦNG CÓ THỂ CHỨA NHIỀU PHÒNG (không phải 1 phòng/1 tầng như bản
# trước) - 1 phòng chiếm cả 1 tầng chỉ để chứa vài chấm tài nguyên là quá
# phí diện tích. Các phòng CÙNG CHỨC NĂNG/CHỦ ĐỀ được gộp chung 1 tầng, đặt
# lệch tâm nhau (xem *_OFFSET_XY) để không đè lên nhau khi vẽ:
#   - Kho thức ăn + Bể trữ nước: cùng là nơi TRỮ ĐỒ mang về, gộp 1 tầng
#   - Phòng trứng + Phòng ấu trùng: cùng là nơi CHĂM CON NON, gộp 1 tầng
# Thứ tự tầng đi từ NÔNG -> SÂU: gác cửa ngay dưới cửa hang -> kho+nước gần
# cửa để tha đồ nhanh -> trứng+ấu trùng ở giữa (cần được bảo vệ) -> phòng
# chúa sâu nhất (quan trọng nhất) -> nghĩa địa tách hẳn ra 1 góc riêng.
LAYER_SURFACE_DEPTH = 0     # tầng 0 LUÔN LUÔN là mặt đất
DEPTH_GUARD = 1             # phòng gác cửa - ngay dưới cửa hang, tuyến
                            # phòng thủ đầu tiên trước khi vào sâu hơn
DEPTH_STORAGE = 2           # kho thức ăn - CHUNG TẦNG với bể trữ nước
DEPTH_WATER = 2             # bể trữ nước - CHUNG TẦNG với kho thức ăn
DEPTH_EGG = 3               # phòng trứng - CHUNG TẦNG với phòng ấu trùng/nhộng
DEPTH_NURSERY = 3           # phòng ấu trùng - CHUNG TẦNG với phòng trứng/nhộng
DEPTH_PUPA = 3              # phòng nhộng - CHUNG TẦNG với phòng trứng/ấu trùng
                            # (3 giai đoạn đầu vòng đời quây quần 1 tầng,
                            # đều cần được bảo vệ như nhau)
DEPTH_QUEEN = 4             # phòng chúa - sâu nhất, được bảo vệ kỹ nhất
DEPTH_GRAVEYARD = 5         # nghĩa địa/phòng rác - tách riêng 1 góc, cũng
                            # là TẦNG SÂU NHẤT của tổ (chỉ có 6 tầng cố
                            # định: 0 mặt đất + 5 tầng ngầm - không còn
                            # chức năng tự đào thêm tầng như bản trước)

# ----- Kiến -----
NUM_ANTS = 10                # số kiến KHỞI TẠO (không còn là giới hạn tối đa -
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

# ----- Thức ăn trên mặt đất (1 LOẠI DUY NHẤT - đơn giản hóa: trước đây có
# 3 loại khác màu/giá trị (hạt/côn trùng/mật hoa), nay chỉ còn 1 loại, 1
# màu, để mỗi đơn vị thức ăn đều "nặng" như nhau - cũng giúp số liệu kho
# thức ăn khớp CHÍNH XÁC 1:1 với số lần kiến thực sự mang thức ăn về, thay
# vì lẫn lộn nhiều giá trị khác nhau) -----
FOOD_CLUSTERS = 26           # tăng so với bản 1 tổ vì giờ có thêm tổ đối
                             # thủ cùng cạnh tranh nguồn thức ăn này
FOOD_CLUSTER_RADIUS = 2

FOOD_TYPE_SEED = 0     # loại thức ăn DUY NHẤT

FOOD_TYPE_VALUE = {
    FOOD_TYPE_SEED: 1.0,   # mỗi lần nhặt = đúng 1.0 đơn vị (không còn lẫn
                           # nhiều giá trị khác nhau như bản 3 loại trước)
}
FOOD_TYPE_COLOR = {
    FOOD_TYPE_SEED: (150, 115, 60),     # màu nâu hạt - MÀU DUY NHẤT
}
# Tỉ lệ xuất hiện mỗi loại khi 1 cụm thức ăn mới sinh ra (phải cộng lại =
# 1.0) - chỉ còn 1 loại nên luôn = 1.0, giữ lại cấu trúc dict để phần code
# còn lại (chọn loại theo trọng số) không cần sửa gì thêm.
FOOD_TYPE_WEIGHTS = {
    FOOD_TYPE_SEED: 1.0,
}
FOOD_PER_CLUSTER = 6.0  # số "đơn vị" thức ăn (không phải giá trị dinh dưỡng)

# ----- Địa hình (chướng ngại vật trên mặt đất) -----
TERRAIN_EMPTY = 0
TERRAIN_ROCK = 1
TERRAIN_WATER = 2

NUM_ROCK_CLUSTERS = 4        # số BỨC TƯỜNG đá rải ngẫu nhiên lúc khởi tạo -
                             # vừa phải để không cản trở quá mức việc tìm ăn
                             # (mỗi bức tường = 1 chuỗi ô đá nối liền nhau,
                             # xem _spawn_one_rock_wall() trong world.py -
                             # KHÔNG còn là khối tròn đặc như trước; công cụ
                             # đặt đá thủ công trong game cũng đặt từng ô 1
                             # qua add_rock_cell(), xem game_state.py)
ROCK_WALL_MIN_LEN = 4        # độ dài NGẮN NHẤT 1 bức tường đá (số ô)
ROCK_WALL_MAX_LEN = 10       # độ dài DÀI NHẤT 1 bức tường đá (số ô)
ROCK_WALL_TURN_CHANCE = 0.25  # xác suất đổi hướng đi mỗi ô - thấp để tường
                             # đi khá thẳng (giống vách đá thật), không quá
                             # 0 để tránh mọi bức tường đều là 1 đường thẳng
                             # tắp nhàm chán
NUM_WATER_CLUSTERS = 4       # số vũng nước rải ngẫu nhiên lúc khởi tạo
WATER_CLUSTER_RADIUS = 2.4
TERRAIN_SAFE_RADIUS_FROM_NEST = 6  # không đặt địa hình quá gần lỗ tổ

# ----- Nước: KHÔNG CHỈ là chướng ngại vật mà còn là tài nguyên sống còn -----
# Kiến không đi được VÀO nước (vẫn chặn đường như trước), nhưng nếu đang
# tìm ăn mà tình cờ đi sát MÉP nước, có thể tranh thủ "uống" 1 ngụm mang
# về tổ - y hệt việc nhặt thức ăn, chỉ khác là không tiêu hao tài nguyên
# trên bản đồ (nước không "cạn" khi kiến uống). Đây là NGUỒN THU NƯỚC
# CHỦ ĐỘNG thật sự (xem WATER_PICKUP_PROB/WATER_CARRY_AMOUNT và
# near_water() trong world.py, dùng trong _update_surface_ants ants.py).
WATER_COLLECT_RADIUS = 2.0     # khoảng cách tới mép nước để có thể "uống"
                               # (near_water() coi ô sát cạnh 1 ô nước là
                               # đủ gần - xem world.py)
WATER_PICKUP_PROB = 0.05       # xác suất "uống" thành công MỖI TICK khi
                               # đang ở sát mép nước (không phải lúc nào
                               # cũng dừng lại ngay tick đầu tiên chạm mép -
                               # để hành vi tự nhiên hơn, giống lúc kiến
                               # còn đang né/lượn quanh vật cản nước)
WATER_CARRY_AMOUNT = 3.0       # lượng nước mang về mỗi lần "uống" thành công
ERASE_RADIUS = 3.0             # bán kính xóa vật thể (thức ăn/đá/nước)
                               # quanh điểm click của công cụ "Xóa"

# ----- Biểu đồ lịch sử dân số theo thời gian -----
HISTORY_SAMPLE_INTERVAL = 200   # cứ mỗi bấy nhiêu tick lấy mẫu 1 lần
HISTORY_MAX_POINTS = 150        # giữ tối đa bấy nhiêu điểm gần nhất (cũ hơn
                                # sẽ bị loại bỏ dần - tránh phình bộ nhớ)
WATER_BASE_INCOME_PER_TICK = 0.03  # nguồn thu "nền" RẤT NHỎ, tự động cộng
                               # mỗi tick MIỄN LÀ còn ít nhất 1 vũng nước
                               # trên bản đồ (đại diện cho hơi ẩm/độ ẩm nền,
                               # không phải kiến chủ động lấy) - CHỦ YẾU
                               # nguồn nước giờ đến từ việc kiến THẬT SỰ ghé
                               # qua mép nước và "uống" mang về (xem
                               # WATER_PICKUP_PROB/WATER_CARRY_AMOUNT ở
                               # trên) - trước đây hằng số này để cao (0.45)
                               # khiến kho nước tăng KHÔNG GIỚI HẠN theo
                               # thời gian bất kể dân số (đã kiểm chứng: sau
                               # 25.000 tick lên tới hàng nghìn), nay hạ hẳn
                               # xuống để nước phụ thuộc THẬT vào hành vi
                               # đàn kiến - nếu bạn lấp hết nước bằng đá
                               # hoặc nước cạn sạch, nguồn thu nền này = 0
                               # (nhưng nguồn thu chủ động cũng mất theo vì
                               # không còn mép nước nào để uống)
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

# Hệ số phóng to TOÀN BỘ bố cục hầm (bán kính từng phòng LẪN khoảng cách
# giữa chúng) - tăng ở ĐÚNG 1 chỗ này để phòng to lên rõ rệt mà không cần
# sửa từng offset/bán kính riêng lẻ. QUAN TRỌNG: phải nhân vào CẢ offset
# vị trí (ROOM_*_OFFSET_XY bên dưới) chứ không chỉ bán kính - vì 1 vài cặp
# phòng chung tầng (Ấu trùng/Phòng nhộng) vốn đã đặt khá sát nhau, nếu chỉ
# phóng to bán kính mà giữ nguyên khoảng cách thì chúng sẽ ĐÈ LÊN NHAU khi
# vẽ. Nhân đồng thời cả 2 = phóng to nguyên bố cục như zoom bản vẽ, mọi
# khoảng hở giữa các phòng vẫn giữ ĐÚNG TỈ LỆ như trước, không bao giờ chồng.
# (1.35 -> 2.025 = tăng thêm 50% so với bản trước đó, đã kiểm tra kỹ bằng
# script tính khoảng hở nhỏ nhất giữa MỌI cặp phòng cùng tầng - kể cả giữa
# 2 tổ - trước khi áp dụng, xem GUARD_OFFSET_XY bên dưới để biết vì sao
# phải đổi hướng đặt Phòng gác cửa cùng lúc.)
ROOM_LAYOUT_SCALE = 2.025

# Vị trí các phòng dưới hầm tính THEO OFFSET so với lỗ tổ (không phải tọa độ
# tuyệt đối) - để có thể dùng chung công thức này cho cả tổ đối thủ đặt ở
# nơi khác trên bản đồ. Các cặp phòng CHUNG TẦNG (kho/nước, trứng/ấu trùng)
# được đặt lệch hẳn sang 2 bên (trái/phải) để không đè lên nhau khi vẽ.
# world.UndergroundWorld nhận thêm tham số `mirror` (+1 cho tổ chính, -1
# cho tổ đối thủ) LẬT NGƯỢC dấu các offset này khi dựng hầm đối thủ - để
# hầm 2 tổ luôn "xòe ra" 2 hướng ngược nhau thay vì cùng hướng, tránh đè
# lên nhau khi ROOM_LAYOUT_SCALE lớn (2 tổ vốn đặt khá gần nhau trên bản
# đồ - xem RIVAL_NEST_POS).
GUARD_OFFSET_XY = (-3 * ROOM_LAYOUT_SCALE, -4 * ROOM_LAYOUT_SCALE)   # ngay dưới cửa hang - gần lỗ tổ nhất.
                                # CỐ Ý đặt LỆCH GÓC (không thẳng trục dọc
                                # như "(0, 3)" hồi trước) - vì hướng thẳng
                                # trục cũ, sau khi LẬT GƯƠNG cho tổ đối
                                # thủ, có 1 giá trị ROOM_LAYOUT_SCALE khiến
                                # 2 phòng gác cửa của 2 tổ tiến THẲNG VÀO
                                # NHAU (khoảng cách chỉ phụ thuộc 1 trục,
                                # dễ bị triệt tiêu) - lệch góc đảm bảo
                                # khoảng cách LUÔN tăng dần theo scale, hết
                                # hẳn kiểu "vùng chồng lấn" đó (đã kiểm tra
                                # bằng script dò nhiều hướng/độ lớn khác
                                # nhau, chọn hướng có khoảng hở lớn nhất).
STORAGE_OFFSET_XY = (-6 * ROOM_LAYOUT_SCALE, -2 * ROOM_LAYOUT_SCALE)   # cùng tầng với bể nước - đặt bên TRÁI
WATER_OFFSET_XY = (6 * ROOM_LAYOUT_SCALE, -2 * ROOM_LAYOUT_SCALE)      # cùng tầng với kho - đặt bên PHẢI
EGG_OFFSET_XY = (-5 * ROOM_LAYOUT_SCALE, -6 * ROOM_LAYOUT_SCALE)       # cùng tầng với ấu trùng/nhộng - đặt bên TRÁI
NURSERY_OFFSET_XY = (5 * ROOM_LAYOUT_SCALE, -6 * ROOM_LAYOUT_SCALE)    # cùng tầng với trứng/nhộng - đặt bên PHẢI
PUPA_OFFSET_XY = (0, -2 * ROOM_LAYOUT_SCALE)       # cùng tầng với trứng/ấu trùng - đặt Ở GIỮA,
                                # gần cửa hang hơn để không chồng lên 2
                                # phòng kia (đều ở y=-6, đã kiểm tra khoảng
                                # cách bằng số liệu để không chạm viền nhau)
QUEEN_OFFSET_XY = (0, -9 * ROOM_LAYOUT_SCALE)      # tầng riêng, sâu nhất
GRAVEYARD_OFFSET_XY = (0, 7 * ROOM_LAYOUT_SCALE)   # tầng riêng, tách hẳn 1 góc

# ----- Phân vai kiến (caste) -----
ROLE_MINOR = 0    # thợ nhỏ - đa số, lo tìm ăn/chăm ấu trùng
ROLE_MAJOR = 1    # thợ lớn/lính - ít hơn nhưng khỏe hơn, chuyên bảo vệ tổ
MAJOR_WORKER_RATIO = 0.15   # tỉ lệ lính trong đàn
MAJOR_SIZE_SCALE = 1.7      # lính to hơn thợ thường bao nhiêu lần khi vẽ

# ----- Kích thước hiển thị (chỉ ảnh hưởng NHÌN THẤY, không đụng tới mô
# phỏng/va chạm/khoảng cách thật) -----
# Nhân thêm vào kích thước VẼ RA của kiến, trứng, ấu trùng, nhộng, chúa,
# thức ăn, kẻ thù, lỗ tổ, xác kiến, đống dự trữ trong hầm... để dễ theo
# dõi hơn khi nhìn màn hình (đàn kiến đông, icon quá nhỏ khó phân biệt).
# 1.0 = kích thước gốc trước khi tăng. Không áp dụng cho đá/nước trên mặt
# đất (đã lấp đầy trọn 1 ô lưới - phóng thêm sẽ đè lên ô bên cạnh) và
# không áp dụng cho bán kính phòng dưới hầm (ROOM_RADIUS - đó là kích
# thước cả căn phòng, tăng lên sẽ đổi bố cục bản đồ hầm chứ không chỉ
# icon bên trong).
ENTITY_SPRITE_SCALE = 1.6

MAJOR_DEFENSE_FACTOR = 0.3  # xác suất lính bị kẻ thù giết = bấy nhiêu lần
                            # so với thợ thường (lính "trâu" hơn nhiều)
SOLDIER_DAMAGE_PROB = 0.05  # xác suất 1 lính gây sát thương lên kẻ thù/tick
                            # khi ở trong tầm giao chiến
SOLDIER_DAMAGE_PER_HIT = 1.0
ENEMY_MAX_HEALTH = 9.0      # kẻ thù có máu - lính có thể đánh bại nó thay vì
                            # chỉ chờ nó tự rời đi

# ----- Phòng gác cửa: 1 phần lính đóng quân cố định dưới hầm, lao lên mặt
# đất chiến đấu ngay khi có kẻ thù xuất hiện gần tổ, xong việc rút về ----- 
GUARD_SHARE_OF_MAJORS = 0.5   # trong số lính (ROLE_MAJOR), bấy nhiêu % là
                            # "lính gác" đóng quân cố định (còn lại vẫn đi
                            # tha thức ăn/chiến đấu ngẫu nhiên như thường)
GUARD_ALERT_RADIUS = 16     # kẻ thù vào trong bán kính này (tính từ lỗ tổ)
                            # thì lính gác lao lên mặt đất nghênh chiến
GUARD_SPEED = 0.22          # lính gác lao lên nhanh hơn tốc độ đi thường

# ----- Chức năng riêng biệt của THỢ NHỎ (ROLE_MINOR) - mỗi con MỘT chức
# năng CỐ ĐỊNH suốt đời (gán lúc sinh ra, không đổi), để đàn kiến trông
# thật sự có PHÂN CÔNG LAO ĐỘNG rõ ràng thay vì ai cũng làm mọi việc:
#   - JOB_FORAGER : ra mặt đất kiếm thức ăn + lấy nước mang về (đa số)
#   - JOB_NURSE   : KHÔNG BAO GIỜ lên mặt đất - cả đời quanh quẩn giữa Kho
#                   thức ăn và Phòng ấu trùng, tự lấy thức ăn mang qua cho
#                   ấu trùng ăn (xem _update_nurses trong ants.py)
#   - JOB_ATTENDANT: KHÔNG BAO GIỜ lên mặt đất - túc trực luân phiên giữa
#                   Phòng chúa và Phòng trứng, hầu chúa + trông trứng (xem
#                   _update_attendants trong ants.py)
# Lính (ROLE_MAJOR) KHÔNG thuộc hệ thống này - lính hoặc là "lính gác"
# (is_guard, đã có sẵn cơ chế riêng) hoặc vẫn tha đồ/chiến đấu như thợ
# thường, không chăm ấu trùng/trứng/chúa (đúng theo đúng đặc tính CANH GÁC
# là trách nhiệm chính của lính).
JOB_FORAGER = 0
JOB_NURSE = 1
JOB_ATTENDANT = 2
JOB_NURSE_RATIO = 0.10       # trong số thợ nhỏ, bấy nhiêu % chuyên chăm ấu trùng
JOB_ATTENDANT_RATIO = 0.06   # ... bấy nhiêu % chuyên chăm trứng + chúa
                             # (phần còn lại ~84% là JOB_FORAGER - ĐÃ KIỂM
                             # THỬ: để tỉ lệ nurse/attendant cao (22%/13%)
                             # làm giảm gần 1/3 lực lượng kiếm ăn so với
                             # trước (khi mọi thợ đều kiếm ăn), khiến kho
                             # không bao giờ tích lũy đủ để chúa đẻ trứng
                             # -> CẢ ĐÀN TUYỆT CHỦNG dần. Tỉ lệ thấp hơn vẫn
                             # đủ để thấy rõ có kiến chuyên trách 2 việc
                             # này, mà không bóp nghẹt kinh tế cả đàn.
JOB_SPECIALIZATION_MIN_POPULATION = 25  # đàn phải đạt ÍT NHẤT bấy nhiêu con
                             # thì thợ mới bắt đầu CÓ chuyên môn (nurse/
                             # attendant) - dưới mức này, MỌI thợ nhỏ đều
                             # là forager (đúng thực tế: 1 đàn kiến mới lập
                             # chỉ có vài thợ đa năng, ai cũng phải ra ngoài
                             # kiếm ăn, chưa đủ người để "cắt cử" ai đó ở
                             # nhà chuyên trách - đã kiểm thử: nếu chuyên
                             # môn hóa ngay từ đầu lúc đàn còn 10 con, rủi
                             # ro tuyệt chủng giai đoạn đầu rất cao vì mất
                             # luôn 1-2 thợ kiếm ăn ngay khi đàn còn quá yếu)

NURSE_TRIP_FOOD_AMOUNT = 1   # mỗi chuyến nurse mang bấy nhiêu đơn vị thức
                             # ăn từ kho qua phòng ấu trùng (chỉ đi khi kho
                             # còn đủ - nếu kho cạn, nurse đứng chờ tại kho
                             # thay vì đi tay không)
NURSE_NURSERY_TARGET_STOCK = 12.0  # nurse CHỈ đi lấy thêm 1 chuyến nếu
                             # phòng ấu trùng đang có ÍT HƠN mức tồn kho
                             # này - nếu không giới hạn, nurse sẽ hút sạch
                             # MỌI thức ăn vừa về kho ngay lập tức (đã kiểm
                             # chứng: gây tuyệt chủng thật, vì kho không
                             # bao giờ kịp tích lũy đủ để chúa đẻ trứng -
                             # xem EGG_MIN_STORAGE_BUFFER_PER_ANT). Ngưỡng
                             # này khiến nurse chỉ lấy thêm khi ấu trùng
                             # THỰC SỰ cần (nhu cầu quyết định nguồn cung),
                             # không phải cứ kho có là lấy ngay.
NURSE_IDLE_TICKS_MIN, NURSE_IDLE_TICKS_MAX = 50, 130  # nurse "chăm" ở
                             # phòng ấu trùng bao lâu mỗi chuyến trước khi
                             # quay lại kho lấy chuyến tiếp theo
ATTENDANT_SWITCH_TICKS_MIN, ATTENDANT_SWITCH_TICKS_MAX = 160, 420  # attendant
                             # túc trực ở 1 phòng (chúa/trứng) bao lâu
                             # trước khi đổi sang phòng kia

TROPHALLAXIS_TTL_TICKS = 22  # 1 "khoảnh khắc mớm mồi" (xem
                             # trophallaxis_events trong ants.py) hiển thị
                             # trong bấy nhiêu tick rồi tự biến mất (nhòe
                             # dần) - ngắn, chỉ là 1 điểm nhấn thoáng qua
                             # chứ không phải hiệu ứng thường trực

# ----- Xâm chiếm/phá tổ đối thủ khi khan hiếm thức ăn -----
# Khi kho CẠN KIỆT và đàn đang thật sự đói (không chỉ tạm thời ít), tổ sẽ tự
# cử 1 đội (ưu tiên lính) hành quân sang XÂM CHIẾM tổ đối thủ: giao chiến
# với lính phòng thủ của họ ngay tại tổ, và cướp thức ăn mang về nếu còn
# sống. Đây là hành vi ĐỐI KHÁNG THẬT giữa 2 đàn, không phải chỉ cạnh tranh
# gián tiếp qua tìm thức ăn như trước.
# NGƯỠNG "khan hiếm" giờ TỈ LỆ THEO SĨ SỐ ĐÀN HIỆN TẠI (giống tinh thần
# EGG_MIN_STORAGE_BUFFER_PER_ANT ở trên) thay vì 1 hằng số cố định như bản
# trước - lý do: hằng số cố định (15) gần như không bao giờ đạt tới nữa chỉ
# sau vài nghìn tick đầu ván (kho tăng vượt xa mức 15 rất nhanh rồi cứ thế
# tăng dần suốt ván, đàn 100-300 con vẫn có kho hàng nghìn) - đã kiểm thử
# thực nghiệm: với hằng số cố định, xâm chiếm CHỈ xảy ra đúng 1 lần lúc mới
# vào ván (kho = 0 lúc khởi tạo), sau đó KHÔNG BAO GIỜ lặp lại nữa. Đặt tỉ
# lệ theo dân số (gần bằng EGG_MIN_STORAGE_BUFFER_PER_ANT) khiến ngưỡng
# "khan hiếm" bám sát mức kho mà đàn thực tế duy trì khi đang tăng trưởng
# gần hết công suất kiếm ăn - tức là xâm chiếm có thể xảy ra LẶP LẠI tự
# nhiên trong lối chơi mặc định mỗi khi đàn tăng dân nhanh hơn khả năng
# kiếm ăn thực tế, không chỉ đúng 1 lần lúc đầu ván.
RAID_STORAGE_THRESHOLD_PER_ANT = 2.0  # kho dưới (dân số hiện tại x số
                            # này) coi là "ít" (xem ticks_storage_low/
                            # is_food_scarce trong world.py) - ĐÃ KIỂM THỬ
                            # thực nghiệm nhiều mức: 10.0 khiến 2 tổ liên
                            # tục xâm chiếm nhau không dứt, cả 2 bị kẹt ở
                            # dân số rất thấp (~10-20 con) suốt ván, không
                            # bao giờ lớn lên nổi; 2.0 tạo ra xâm chiếm
                            # THẬT trong giai đoạn đầu ván (khi đàn còn nhỏ/
                            # yếu, kho chưa kịp tích lũy) nhưng KHÔNG còn
                            # xảy ra nữa 1 khi đàn đã phát triển ổn định -
                            # giống nhịp độ 1 game thật: đầu ván rủi ro
                            # cạnh tranh cao, càng về sau càng an toàn hơn.
RAID_STORAGE_THRESHOLD_MIN = 15  # sàn TỐI THIỂU (áp dụng cả khi đàn còn
                            # rất nhỏ lúc mới vào ván, để không phát động
                            # xâm chiếm chỉ vì kho vài đơn vị lúc mới sinh)
RAID_SCARCITY_GRACE_TICKS = 300  # kho phải LIÊN TỤC ở mức thấp bấy nhiêu
                            # tick (~5 giây ở tốc độ x1) mới coi là khan
                            # hiếm THẬT SỰ (tránh phát động chỉ vì 1 khoảnh
                            # khắc kho tạm thời thấp)
RAID_CHECK_INTERVAL = 90     # cứ mỗi bấy nhiêu tick, kiểm tra 1 lần có nên
                            # phát động đợt xâm chiếm mới không
RAID_PARTY_SIZE = 6          # số kiến (ưu tiên lính) cử đi mỗi đợt xâm chiếm
RAID_COOLDOWN_TICKS = 900     # sau 1 đợt phát động, nghỉ bấy nhiêu tick mới
                            # cân nhắc phát động đợt tiếp theo
RAID_SPEED = 0.16            # tốc độ hành quân sang tổ đối thủ
RAID_KILL_RADIUS = 3.5       # phạm vi quanh tổ đối thủ được coi là "chiến
                            # trường" - phòng thủ của họ trong phạm vi này
                            # mới bị lôi vào giao chiến
RAID_ATTACKER_KILL_PROB = 0.015  # xác suất/tick 1 kiến xâm chiếm hạ được 1
                            # lính phòng thủ (nhân đôi nếu phòng thủ không
                            # phải lính - xem MAJOR_DEFENSE_FACTOR áp dụng
                            # cho phe phòng thủ)
RAID_DEFENDER_KILL_PROB = 0.02   # phòng thủ có lợi thế sân nhà nên xác suất
                            # hạ được quân xâm chiếm/tick cao hơn 1 chút
RAID_STEAL_PER_TICK = 3.0    # mỗi tick còn đứng cướp phá thì rút được bấy
                            # nhiêu thức ăn từ kho đối thủ (chia đều số
                            # quân xâm chiếm còn sống)
RAID_MAX_LOOT_TICKS = 220    # tối đa đứng cướp phá bấy nhiêu tick trước khi
                            # tự rút quân về (dù kho đối thủ chưa cạn hẳn)

# ----- Tổ kiến đối thủ (cạnh tranh tài nguyên trên cùng bản đồ) -----
RIVAL_NEST_POS = (11, 29)   # lệch khỏi trung tâm nhưng KHÔNG ở góc bản đồ,
                            # để không bị bất lợi hình học (diện tích kiếm
                            # ăn khả dụng thấp hơn hẳn tổ chính ở giữa) -
                            # tỉ lệ tương đương (14,36) trên bản đồ 50 ô cũ
NUM_RIVAL_ANTS = 10          # CÙNG quy mô khởi tạo với tổ chính - đàn nào
                            # sinh sản/kiếm ăn tốt hơn sẽ tự lớn nhanh hơn
MAX_ANTS_PER_COLONY = 200   # giới hạn TỐI ĐA quy mô 1 đàn (bộ nhớ cấp phát
                            # sẵn cho mảng NumPy) - đàn khởi tạo NUM_ANTS con,
                            # rồi tự sinh sản lớn lên dần tới tối đa số này
                            # nếu đủ thức ăn/nước/không gian ấu trùng
ROOM_RADIUS = 3.4 * ROOM_LAYOUT_SCALE            # bán kính MẶC ĐỊNH (dùng cho phòng tự đào)
# Mỗi phòng CHỨC NĂNG khác nhau có kích thước khác nhau cho hợp lý: kho +
# bể nước chứa số lượng lớn nên to nhất; phòng chúa đủ rộng; ấu trùng vừa
# phải; trứng/gác cửa/nghĩa địa nhỏ hơn vì bản chất chỉ chứa ít "vật thể".
ROOM_RADIUS_STORAGE = ROOM_RADIUS * 1.3
ROOM_RADIUS_WATER = ROOM_RADIUS * 1.25
ROOM_RADIUS_NURSERY = ROOM_RADIUS * 1.05
ROOM_RADIUS_QUEEN = ROOM_RADIUS * 1.15
ROOM_RADIUS_EGG = ROOM_RADIUS * 0.75
ROOM_RADIUS_PUPA = ROOM_RADIUS * 0.6
ROOM_RADIUS_GUARD = ROOM_RADIUS * 0.9
ROOM_RADIUS_GRAVEYARD = ROOM_RADIUS * 0.8

# ----- Trạng thái kiến (state machine) -----
STATE_SEARCHING = 0        # trên mặt đất, đang tìm thức ăn
STATE_RETURNING = 1        # trên mặt đất, đang tha thức ăn về tổ
STATE_UG_TO_STORAGE = 2    # dưới hầm, đang đi tới kho
STATE_UG_TO_NURSERY = 3    # (không còn dùng - giữ số hiệu để không xáo trộn
                           # các hằng số khác; xem STATE_NURSE_* bên dưới)
STATE_UG_TO_SHAFT = 4      # dưới hầm, đang quay lại giếng để lên mặt đất
STATE_DWELL = 5            # dưới hầm, đang LƯỢN/HOẠT ĐỘNG trong phạm vi 1
                           # phòng (kho/ấu trùng/phòng chúa) 1 lúc trước khi
                           # rời đi - để phòng ngầm có "sự sống" thật sự
                           # thay vì kiến chỉ chạm tâm phòng rồi quay đầu
STATE_GUARD_DUTY = 6       # lính gác đang đóng quân, lượn trong phòng gác
                           # (vô thời hạn, chỉ rời đi khi có báo động)
STATE_GUARD_RUSH = 7       # lính gác đang lao lên mặt đất nghênh chiến
STATE_GUARD_RETURN = 8     # lính gác xong việc, đang quay về giếng để
                           # xuống lại phòng gác
STATE_RAID_TO_ENEMY = 9    # đội xâm chiếm đang hành quân sang tổ đối thủ
STATE_RAID_LOOT = 10       # đang giao chiến/cướp phá tại tổ đối thủ

# --- Vòng lặp RIÊNG của JOB_NURSE (không bao giờ lên mặt đất) ---
STATE_NURSE_AT_STORAGE = 11   # đang ở kho, chờ/lượn, sẵn sàng lấy chuyến kế
STATE_NURSE_TO_NURSERY = 12   # đang mang thức ăn từ kho sang phòng ấu trùng
STATE_NURSE_AT_NURSERY = 13   # đang "chăm" ở phòng ấu trùng 1 lúc
STATE_NURSE_TO_STORAGE = 14   # đang quay lại kho để lấy chuyến tiếp theo

# --- Vòng lặp RIÊNG của JOB_ATTENDANT (không bao giờ lên mặt đất) ---
STATE_ATTENDANT_AT_QUEEN = 15   # đang túc trực cạnh chúa
STATE_ATTENDANT_TO_EGG = 16     # đang di chuyển sang phòng trứng
STATE_ATTENDANT_AT_EGG = 17     # đang túc trực trông trứng
STATE_ATTENDANT_TO_QUEEN = 18   # đang quay lại phòng chúa

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

# ----- Trứng -> Ấu trùng -> Nhộng -> Kiến trưởng thành: ĐỦ 4 GIAI ĐOẠN
# BIẾN THÁI HOÀN TOÀN đúng vòng đời thật của loài kiến (holometabolous),
# mỗi giai đoạn 1 PHÒNG RIÊNG BIỆT. Chúa không "sinh" kiến trực tiếp - chúa
# chỉ ĐẺ TRỨNG (tốn thức ăn+nước từ kho). Trứng được ủ trong PHÒNG TRỨNG
# riêng (chỉ cần thời gian, KHÔNG cần ăn) - nở xong "chuyển" qua PHÒNG ẤU
# TRÙNG để lớn lên thật sự bằng thức ăn nurse mang tới (food_in_nursery) -
# hết thức ăn ở đó thì lớn rất chậm. Ấu trùng lớn đủ (growth >= 1.0) KHÔNG
# nở thành kiến ngay - mà "hóa nhộng", chuyển qua PHÒNG NHỘNG, nằm yên
# BIẾN THÁI trong 1 khoảng thời gian (giống trứng: chỉ cần thời gian,
# KHÔNG cần ăn - đúng thực tế, nhộng không ăn) - xong mới thật sự "nở"
# thành 1 kiến thợ mới đi ra ngoài.
EGG_LAY_INTERVAL = 70        # cứ mỗi bấy nhiêu tick, chúa thử đẻ 1 trứng mới
EGG_FOOD_COST = 4            # thức ăn (lấy từ KHO) chúa cần để đẻ 1 trứng
EGG_WATER_COST = 2           # nước cần thêm để đẻ 1 trứng - thiếu nước thì
                             # KHÔNG đẻ được dù đủ thức ăn
# "PHANH" mật độ dân số - ĐÂY LÀ MẢNH GHÉP QUAN TRỌNG CÒN THIẾU trước đây:
# nếu chỉ cần đủ EGG_FOOD_COST là đẻ được, đàn sẽ cứ phình to tới khi kho
# CẠN HẲN VỀ 0 mới dừng - lúc đó đã quá muộn, cả đàn rơi vào chết đói hàng
# loạt cùng lúc (đặc biệt nguy hiểm khi CẢ HAI tổ cùng cạn kho 1 lượt, kéo
# theo các đợt xâm chiếm qua lại làm nhau suy yếu nhanh hơn nữa). Bằng cách
# bắt buộc kho phải dư ra 1 khoản DỰ TRỮ AN TOÀN tỉ lệ với sĩ số đàn HIỆN
# TẠI (không phải hằng số cố định), việc đẻ trứng sẽ tự động CHẬM LẠI dần
# khi đàn tiệm cận mức tối đa mà tốc độ kiếm ăn thực tế có thể nuôi nổi -
# giữ dân số ổn định quanh 1 mức bền vững thay vì phình to rồi sụp đổ.
EGG_MIN_STORAGE_BUFFER_PER_ANT = 8.0  # kho phải dư ra >= (dân số hiện tại
                             # x số này) NGOÀI EGG_FOOD_COST thì mới được
                             # đẻ trứng tiếp - đàn càng đông, ngưỡng an toàn
                             # càng cao, tự nhiên hãm tốc độ sinh sản lại.
                             # Giá trị này đã được KIỂM THỬ THỰC NGHIỆM qua
                             # nhiều mô phỏng dài (60.000-90.000 tick, nhiều
                             # seed khác nhau): thấp hơn (1.5-5.0) vẫn dẫn
                             # tới sụp đổ tuyệt chủng đồng loạt ở ván dài;
                             # mức 8.0 loại bỏ được kiểu sụp đổ đó (kho
                             # không còn về 0 đột ngột), đổi lại tốc độ
                             # tăng dân số chậm hơn hẳn.
EGG_MAX_COUNT = 30           # số trứng tối đa cùng lúc trong phòng trứng
EGG_INCUBATE_PER_TICK = 0.006  # tốc độ ủ trứng mỗi tick (KHÔNG phụ thuộc
                             # thức ăn - trứng chỉ cần thời gian) - nở
                             # nhanh hơn hẳn tốc độ lớn của ấu trùng vì đây
                             # chỉ là giai đoạn ủ, chưa cần nuôi ăn

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

PUPA_MAX_COUNT = 30          # số nhộng tối đa cùng lúc trong phòng nhộng
PUPA_MATURE_PER_TICK = 0.004  # tốc độ "chín" mỗi tick (KHÔNG phụ thuộc thức
                             # ăn - đúng thực tế, NHỘNG KHÔNG ĂN, chỉ cần đủ
                             # thời gian biến thái) - nhanh hơn ấu trùng (vốn
                             # phải chờ đủ thức ăn mới lớn) nhưng chậm hơn
                             # trứng (trứng chỉ cần "nở vỏ", nhộng cần biến
                             # thái toàn bộ cơ thể nên lâu hơn 1 chút)

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

# Hiệu ứng chuyển tầng: MỖI LẦN đổi current_layer (phím Lên/Xuống,
# Ctrl+lăn chuột, hoặc camera tự động bám theo kiến đi xuyên tầng) - màn
# hình chớp NHANH sang đen rồi mờ dần hiện lại tầng mới, thay vì cắt cảnh
# tức thời gây giật. Chỉ áp dụng cho phần KHUNG NHÌN MÔ PHỎNG (mặt đất/
# hầm) - thanh công cụ/HUD/panel nổi vẽ ĐÈ LÊN SAU nên không bị tối theo,
# vẫn bấm được bình thường trong lúc đang chuyển tầng. Xem
# GameState.change_layer() / update_follow_camera() (nơi bắt đầu hiệu
# ứng) và render() trong __main__.py (nơi vẽ lớp phủ đen mờ dần).
LAYER_FADE_TICKS = 14        # tổng số khung hình mờ dần (~0.23s ở 60 FPS)

# Màu nền riêng cho từng loại tầng, để luôn biết đang xem tầng nào dù có
# nhìn lướt qua HUD hay không
COLOR_BG_SURFACE = (74, 58, 40)
COLOR_BG_UNDERGROUND = (32, 27, 24)
COLOR_GRID_LINE = (0, 0, 0, 40)
COLOR_GROUND_FILL = (205, 178, 132)
COLOR_SHAFT = (25, 18, 12)

# LƯU Ý: TOOLBAR_H / GRAPH_PANEL_W / GRAPH_PANEL_H (hằng số kích thước cố
# định của thanh công cụ/biểu đồ) đã được XÓA - từ khi thanh công cụ, bảng
# thống kê, biểu đồ trở thành các Panel NỔI kéo/thu gọn được (xem
# ui_widgets.Panel + hud.build_toolbar), kích thước mặc định của chúng
# được định nghĩa trực tiếp ngay trong hud.build_toolbar() thay vì ở đây.

# Kho thức ăn: hiển thị thức ăn ĐANG LƯU TRỮ THẬT SỰ dưới dạng 1 đống nhỏ
# các "viên" thức ăn rải trong phòng, thay vì chỉ 1 con số vô hình
STORAGE_FOOD_PER_ICON = 1        # 1 icon = ĐÚNG 1 đơn vị thức ăn (khớp 1:1
                             # với số thức ăn kiến THỰC SỰ đã mang về - y
                             # hệt cách nghĩa địa đã làm với xác kiến, xem
                             # GRAVEYARD_MAX_CORPSES/add_corpse trong
                             # world.py: 1 "nắm xác" = đúng 1 kiến đã chết.
                             # Trước đây hằng số này = 8, nghĩa là phải
                             # tích lũy đủ 8 đơn vị mới hiện thêm 1 icon -
                             # khiến đống thức ăn trông "ít hơn hẳn" so với
                             # số liệu kho thực tế, không khớp với cảm giác
                             # trực quan "kiến vừa mang về 1 miếng thì kho
                             # phải hiện thêm đúng 1 viên")
STORAGE_MAX_ICONS = 40           # trần số icon vẽ (tránh rợp hình khi kho đầy)

# Bể trữ nước: tương tự kho thức ăn nhưng vẽ dạng giọt nước lấp lánh
WATER_PER_ICON = 40               # bấy nhiêu đơn vị nước = 1 giọt hiển thị
WATER_MAX_ICONS = 40

# Kiến chúa: to hơn hẳn thợ thường, luôn đứng yên (bob nhẹ) giữa phòng chúa
QUEEN_BODY_SCALE = 3.2

# Nghĩa địa/phòng rác: mỗi kiến chết được "chuyển" vào đây thành 1 nắm xác
# nhỏ - KHÔNG mô phỏng chi tiết việc kiến khác tha xác đi (ngoài phạm vi
# game này), chỉ cần đủ để phòng có ý nghĩa và có thể NHÌN THẤY hậu quả của
# chết chóc thay vì kiến biến mất vô hình. Xác cũ dần phân hủy/biến mất để
# nghĩa địa không phình to vô hạn.
GRAVEYARD_MAX_CORPSES = 60       # trần số "nắm xác" hiển thị cùng lúc
GRAVEYARD_DECAY_PER_TICK = 0.0008  # tốc độ phân hủy (xác cũ dần biến mất
                             # sau khoảng vài chục giây, không phải tức thời)

# ----- Camera theo dõi 1 con kiến cụ thể (chọn công cụ "Theo dõi" rồi bấm
# vào 1 con kiến bất kỳ, thuộc tổ nào cũng được) -----
FOLLOW_PICK_RADIUS = 1.6     # bấm chuột cách con kiến bao xa (đơn vị ô mô
                             # phỏng) vẫn còn tính là "chọn trúng" nó - đủ
                             # rộng để không cần bấm chính xác tuyệt đối
                             # từng pixel, nhất là lúc đang zoom xa
FOLLOW_CAMERA_SMOOTH = 0.15  # camera đuổi theo kiến mượt dần mỗi khung hình
                             # (0-1: càng lớn càng "dí sát", 1.0 = dính
                             # cứng luôn vào đúng vị trí kiến không có độ trễ)
FOLLOW_AUTO_ZOOM = 2.4       # khi BẮT ĐẦU theo dõi 1 con kiến, tự phóng to
                             # lên mức này (nếu đang zoom xa hơn mức này) để
                             # nhìn rõ "từng chút một" ngay lập tức - nếu
                             # đang zoom gần hơn mức này rồi thì giữ nguyên,
                             # không tự thu nhỏ lại

# ----- Lưu / tải ván chơi -----
SAVE_FILE_NAME = "antworld_savegame.pkl"  # lưu ngay cạnh main.py (1 slot
                             # duy nhất - lưu đè lần sau, đơn giản dễ dùng)

# ----- Thông báo nổi bật (toast) - hiện GÓC TRÊN màn hình, LUÔN NHÌN THẤY
# bất kể panel thống kê đang thu gọn/kéo đi đâu, tự biến mất sau vài giây -
# dùng cho cả xác nhận lưu/tải LẪN cảnh báo sự kiện quan trọng (đói, khát,
# kẻ thù xuất hiện, bị xâm chiếm, tuyệt chủng...) -----
TOAST_TTL_FRAMES = 260       # 1 thông báo hiện khoảng bấy nhiêu khung hình
                             # (~4.3 giây ở 60 FPS) rồi tự nhòe biến mất
TOAST_FADE_FRAMES = 40       # bấy nhiêu khung hình cuối cùng dùng để nhòe dần
TOAST_MAX_VISIBLE = 6        # tối đa bấy nhiêu thông báo xếp chồng cùng lúc
                             # (thông báo cũ nhất bị đẩy ra nếu vượt quá)
