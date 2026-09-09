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
TURN_NOISE = 0.6             # độ nhiễu góc quay mỗi tick (radian) khi
                             # "lượn tại chỗ" (DWELL, đóng quân... - xem
                             # AntColony._update_underground_ants/_update_guards).
                             # KHÔNG dùng cho việc tìm đường trên mặt đất
                             # (xem PATH_* bên dưới, dùng pathfinding.py thật)

DYING_DURATION_TICKS = 40    # (~0.67s ở 60 FPS) kiến già/đói/khát không
                             # BIẾN MẤT NGAY khi "trúng số" chết - đứng
                             # khựng lại run rẩy TRONG bấy nhiêu tick rồi
                             # mới thực sự chết hẳn (thành xác/bị dọn), mô
                             # phỏng cảnh hấp hối thật thay vì "bụp" 1 cái
                             # biến mất. CHỈ áp dụng cho chết già/đói/khát
                             # (_update_lifecycle) - chết vì GIAO CHIẾN vẫn
                             # tức thời như cũ (đúng thực tế: bị cắn chết
                             # là chết ngay, không hấp hối).
DYING_TREMBLE_JITTER = 0.55  # (radian) biên độ run rẩy góc quay ngẫu nhiên
                             # mỗi tick trong lúc hấp hối (KHÔNG dịch
                             # chuyển vị trí, chỉ xoay run - xem render)

MAX_TURN_RATE_PER_TICK = 0.35  # (radian) góc quay đầu TỐI ĐA mỗi tick khi
                             # đang bám đường đi thật (_follow_paths/
                             # _move_towards_2d) - trước đây kiến BẺ ĐẦU
                             # TỨC THỜI (arctan2 thẳng) mỗi khi đổi waypoint,
                             # trông "dán mắt" máy móc; giờ đầu xoay DẦN về
                             # hướng mới (khoảng 0.15s để quay 180 độ ở 60
                             # FPS x1), giống côn trùng thật xoay thân trước
                             # khi đổi hướng thay vì bật ngay lập tức.

# ----- Hành vi "dò đường bằng râu" (antenna tapping) - kiến thật khi bò
# hay dừng khựng lại vài trăm mili-giây, ngoáy đầu/râu dò xét trước khi đi
# tiếp, KHÔNG đi liên tục đều đều như robot. Chỉ áp dụng cho kiến đang tự
# do khám phá/quay về (KHÔNG áp dụng cho lính gác lao lên nghênh chiến hay
# thợ khiêng mồi lớn - những tình huống cần phản ứng ngay, xem các lời gọi
# _follow_paths(..., allow_pause=...) trong ants.py). -----
ANTENNA_PAUSE_PROB = 0.004    # xác suất BẮT ĐẦU 1 lần dừng mỗi tick đang đi
                             # (kiến thật) - trung bình ~4-5 giây/lần ở 60 FPS
ANTENNA_PAUSE_MIN_TICKS = 8   # (~0.13s ở 60 FPS)
ANTENNA_PAUSE_MAX_TICKS = 24  # (~0.4s ở 60 FPS)
ANTENNA_TAP_JITTER = 0.18    # (radian) đầu lắc nhẹ ngẫu nhiên mỗi tick
                             # trong lúc đang dừng dò đường

# ----- Animation - trước đây kiến chỉ là 3 hình tròn TRƯỢT cứng theo vị
# trí (chỉ xoay hướng qua get_rotated, không có dáng đi/phản hồi hành động
# nào) - xem render_surface.py draw_ants()/_leg_wiggle_offsets() để biết
# cách dùng các hằng số dưới đây. -----
ANT_LEG_ANIM_SPEED = 0.9     # (chỉ còn dùng làm HỆ SỐ NHÂN THÊM cho pha
                             # chân - xem ANIM_PHASE_DISTANCE_SCALE bên
                             # dưới; bản thân chân giờ đã gắn với quãng
                             # đường DI CHUYỂN THẬT của từng con, không còn
                             # chạy vô điều kiện theo frame_counter toàn cục
                             # nữa - kiến đứng yên thì chân cũng đứng yên)
ANIM_PHASE_DISTANCE_SCALE = 10.0  # số radian pha đi/chân tăng thêm mỗi 1
                             # ô khoảng cách DI CHUYỂN THẬT trong 1 tick
                             # (xem AntColony.anim_phase/InvasionManager.
                             # anim_phase, cập nhật cuối update()) - quy đổi
                             # quãng đường thành nhịp bước chân, để bước
                             # chân nhanh/chậm ĐÚNG theo tốc độ thật đang đi
                             # (kiến lính gác lao nhanh thì bước chân cũng
                             # nhanh hơn kiến đi thường, không còn "phi
                             # nhanh mà chân lướt như trượt băng" nữa)
ANT_LEG_MIN_RADIUS_PX = 1.8  # chỉ vẽ chân khi kiến đủ to trên màn hình
                             # (zoom đủ gần) - xa hơn thì chân chỉ còn 1
                             # chấm vô nghĩa, bỏ qua để đỡ tốn vẽ
ANT_ANTENNA_WIGGLE_SPEED = 0.22  # tốc độ ngoe nguẩy ĐỘC LẬP của râu (không
                             # phụ thuộc bước chân) - râu kiến thật luôn
                             # động đậy dò xét ngay cả khi đứng yên hẳn
ANT_ANTENNA_WIGGLE_AMOUNT = 0.35  # (radian) biên độ ngoe nguẩy của râu

# ----- Lính gác "chạm râu" kiểm tra đồng đội ra vào cửa tổ (nestmate
# recognition) - kiến thật LUÔN chạm râu nhận diện mùi tổ của bất kỳ con
# nào đi ngang qua trạm gác, không chỉ đứng canh vô tri. Thuần túy HIỆU
# ỨNG HÌNH ẢNH (không chặn đường/không có "kiến lạ" trong game), xem
# AntColony._update_guard_inspections(). -----
GUARD_INSPECT_RADIUS = 1.1     # bán kính (quanh giếng lên mặt đất, ở đúng
                             # tầng phòng gác) tính là "đi ngang trạm gác"
GUARD_INSPECT_PROB = 0.05    # xác suất kiểm tra mỗi tick khi hội đủ điều
                             # kiện (1 lính gác rảnh + 1 con khác ở gần)
GUARD_INSPECT_COOLDOWN_TICKS = 90   # (~1.5s) 1 con không bị kiểm tra lại
                             # ngay sau khi vừa được kiểm tra
GUARD_INSPECT_TTL_TICKS = 18  # hiệu ứng chạm râu hiển thị bao lâu

# ----- Cắn giữ mồi trước khi tha đi - kiến thật CẮN/NGOẠM vào thức ăn để
# lấy đà và giữ chắc trước khi kéo lê đi, không phải cứ chạm vào là mồi tự
# dính lên lưng. Áp dụng khi thợ (1 mình) vừa tìm thấy mồi VÀ trong lúc cả
# nhóm đang gồng giữ con mồi lớn chờ đủ đồng đội (STATE_HAUL_GRIP - xem
# ants.py/render_surface.py). -----
BITE_GRIP_PAUSE_TICKS = 14   # (~0.23s) đứng khựng "cắn giữ" mồi tại chỗ
                             # trước khi thực sự bắt đầu tha đi

# ----- Chăm sóc lẫn nhau (allogrooming) giữa các kiến đang rảnh rỗi dưới
# hầm (STATE_DWELL) - hành vi xã hội phổ biến thật của loài kiến, không
# liên quan tới việc cho ăn (khác trophallaxis). Thuần túy hình ảnh. -----
GROOM_RADIUS = 0.9            # khoảng cách để 2 con rảnh rỗi coi là "đủ gần"
GROOM_PROB = 0.008            # xác suất bắt đầu mỗi tick khi đủ gần + rảnh
GROOM_DURATION_TICKS = 50     # (~0.8s) thời lượng 1 lượt chăm sóc
GROOM_COOLDOWN_TICKS = 200    # (~3.3s) nghỉ trước khi có thể chăm sóc tiếp

BOUNCE_DURATION_TICKS = 14   # độ dài hiệu ứng "nảy lên" khi nhặt/giao đồ
                             # (thức ăn, nước, xác, mồi lớn) - xem các chỗ
                             # gán self.bounce_ticks trong ants.py
BOUNCE_HEIGHT_FACTOR = 1.1   # chiều cao cú nảy = bấy nhiêu lần bán kính
                             # thân kiến trên màn hình

HIT_FLASH_DURATION_TICKS = 10  # độ dài hiệu ứng nhấp nháy/rung khi vừa
                             # đánh trúng hoặc đang giao chiến - xem
                             # EnemyManager.hit_flash_ticks (kẻ thù trúng
                             # đòn) và AntColony/InvasionManager.
                             # combat_flash_ticks (đang giao chiến ở cửa tổ)
HIT_SHAKE_PX = 2.0           # biên độ rung (dịch vị trí vẽ ngẫu nhiên mỗi
                             # khung hình) khi đang trong hiệu ứng va chạm

# ----- Tìm đường (pathfinding.py): kiến trên mặt đất (SEARCHING/RETURNING)
# và lính gác rút về tổ giờ đi theo ĐƯỜNG ĐI TÍNH SẴN (any-angle, ngắn
# nhất, dựng từ visibility graph các góc vật cản) thay vì "dò mùi + né vật
# cản kiểu bám tường" như trước - xem AntColony._follow_paths/_assign_new_path.
PATH_MAX_WAYPOINTS = 250    # số điểm rẽ hướng tối đa lưu cho 1 đường đi -
                            # với bản đồ chỉ có vài bức tường đá rời rạc
                            # thì hiếm khi vượt quá vài điểm, NHƯNG mê
                            # cung dày đặc nhất (hành lang/tường đều 1 ô -
                            # xem MAZE_PASSAGE_WIDTH/MAZE_WALL_WIDTH) có
                            # thể cần TỚI 130+ điểm rẽ cho 1 đường đi dài
                            # ngoằn ngoèo - đo thực tế trên nhiều mê cung
                            # mặc định (max quan sát: 131/120 mẫu). Nếu để
                            # thấp hơn mức này, đường đi bị CẮT CỤT giữa
                            # chừng (path[:PATH_MAX_WAYPOINTS] trong
                            # AntColony._assign_new_path) khiến kiến dừng
                            # lại ở 1 điểm rẽ TRUNG GIAN không phải đích
                            # thật, thường ngay sát góc vật cản - từng gây
                            # ra hiện tượng kiến trông như "đứng yên/kẹt"
                            # gần tường dù về mặt hình học không hề xuyên
                            # tường. Mảng path_x/path_y cấp phát theo giá
                            # trị này cho MỖI con kiến (xem AntColony.
                            # __init__) nên tăng lên không tốn kém gì đáng
                            # kể (vài trăm KB dù đủ 200 kiến).
PATH_REPLAN_BUDGET_PER_TICK = 40   # số lần tính đường đi MỚI tối đa cho
                            # phép mỗi tick (dùng chung cho cả tìm ăn, tha
                            # mồi về tổ, lính gác rút quân) - tránh giật
                            # khung hình khi rất nhiều kiến cùng cần đường
                            # đi mới trong 1 tick (vd lúc mới khởi động);
                            # kiến chưa tới lượt sẽ đứng yên, thử lại tick sau
WAYPOINT_ARRIVE_THRESHOLD = 0.22   # coi là "đã tới" 1 điểm rẽ hướng khi
                            # còn cách chừng này - nhỏ hơn ARRIVE_THRESHOLD
                            # (mốc tới ĐÍCH CUỐI, vd cửa tổ) để bo góc sát
                            # hơn, giảm nguy cơ "cắt góc" đâm vào vật cản
PATH_NUM_LANDMARKS = 6      # số "mốc" cho heuristic ALT (xem
                            # VisibilityPathfinder._build_landmarks) - CHỈ
                            # ảnh hưởng tốc độ tìm đường (mốc nhiều hơn =
                            # heuristic chặt hơn = ít đỉnh phải xét hơn mỗi
                            # truy vấn, đổi lại tốn thêm vài lần Dijkstra
                            # MỖI KHI địa hình đổi - không phải mỗi tick).
                            # Đường đi trả về LUÔN NGẮN NHẤT THẬT SỰ dù đặt
                            # giá trị nào (ALT là heuristic hợp lệ, không
                            # đánh đổi độ chính xác lấy tốc độ).
EXPLORE_TARGET_SAMPLES = 12  # số điểm ứng viên ngẫu nhiên xét mỗi lần 1
                            # kiến SEARCHING cần chọn điểm khám phá mới
EXPLORE_DANGER_WEIGHT = 4.0  # trọng số né mùi báo động nguy hiểm khi CHỌN
                            # điểm khám phá (thay cho việc né bằng cách bẻ
                            # lái từng tick như cơ chế pheromone cũ)

# ----- Sinh me cung THAT (maze_generator.py, nut "Sinh me cung" trong
# toolbar) - rai truc tiep vao ban do dang choi, dan kien that tu tim
# duong xuyen bang dung pathfinding.py. "Perfect maze" (spanning tree
# tren luoi o logic - moi o lien thong, dung 1 duong duy nhat giua 2 o
# bat ky) chu KHONG con la vai tuong da roi rac nhu ban truoc, xem
# docstring generate_perfect_maze(). MAZE_PASSAGE_WIDTH/MAZE_WALL_WIDTH
# CANG NHO thi me cung CANG DAY nhung build CANG CHAM (chi phi O(V^2)) -
# 2 gia tri mac dinh duoi day da do dac de giu build duoi ~2 giay. -----
MAZE_PASSAGE_WIDTH = 1         # do rong hanh lang (so o)
MAZE_WALL_WIDTH = 1            # do day tuong giua 2 hanh lang (so o)

# ----- Né vật cản (đá/nước): "bám tường" thay vì dội ngẫu nhiên -----
# Dùng cho lính gác đuổi kẻ thù trên mặt đất (_update_guards/STATE_GUARD_RUSH,
# mục tiêu đổi liên tục theo vị trí kẻ thù nên không hợp để tính trước 1
# đường any-angle như pathfinding.py) - kiến tìm ăn/tha mồi về tổ giờ đi
# theo đường tính sẵn (xem PATH_* ở trên) nên KHÔNG còn dùng cơ chế né này.
# "Khóa" 1 hướng né cố định (trái HOẶC phải, không đổi ngẫu nhiên mỗi lần)
# trong suốt cả pha né, để TRƯỢT DỌC rìa vật cản ra ngoài thay vì dội qua
# dội lại ngay tại chỗ va chạm.
AVOID_COOLDOWN_TICKS = 25    # số tick "khóa hướng né" mỗi lần chạm vật cản
                             # (được LÀM MỚI lại mỗi lần vẫn còn bị chặn, nên
                             # vật cản càng to thì kiến càng có nhiều thời
                             # gian trượt vòng qua trước khi bị kéo lại)
AVOID_TURN_ANGLE = 1.35      # góc né khi vừa chạm vật cản (~77 độ, gần vuông
                             # góc với hướng đang đi - để TRƯỢT DỌC theo rìa
                             # thay vì chỉ hơi chếch)

# ----- Pheromone (mùi dẫn đường về tổ khi tha thức ăn) - dùng để VẼ vệt
# mùi trực quan (xem render_surface.py) VÀ để TUYỂN MỘ (recruitment):
# khi 1 kiến khác đang tìm ăn cần chọn điểm khám phá mới, nó có 1 xác
# suất được "hút" theo vệt mùi thay vì tự dò ngẫu nhiên (xem
# AntColony._sample_recruit_candidates/_pick_explore_target) - giống cách
# đàn kiến thật ùa nhanh vào 1 nguồn ăn giàu vừa được đồng loại tìm thấy,
# thay vì mỗi con tự mò mẫm độc lập. Lượng mùi để lại tỉ lệ với GIÁ TRỊ
# đang tha (xem AntColony._update_returning_ants) nên nguồn càng giàu thì
# càng "ồn ào", càng tuyển được nhiều kiến khác. -----
PHEROMONE_DECAY = 0.985     # mỗi tick pheromone giảm còn 98.5%
PHEROMONE_DEPOSIT = 1.0     # lượng mùi CƠ SỞ để lại mỗi tick khi đang tha đồ
                            # (nhân thêm với carry_amount - xem
                            # _update_returning_ants - nên đồ giá trị cao
                            # hơn để lại vệt đậm hơn hẳn đồ giá trị thấp)
PHEROMONE_MAX = 8.0
PHEROMONE_RECRUIT_PROB = 0.35   # xác suất 1 kiến SEARCHING vừa cần điểm
                                # khám phá mới chọn ĐI THEO vệt mùi (nếu có
                                # vệt đáng kể) thay vì tự dò ngẫu nhiên -
                                # đây chính là "tuyển mộ" kiểu kiến thật
PHEROMONE_RECRUIT_MIN_TOTAL = 15.0  # tổng lượng mùi tối thiểu trên TOÀN
                                # bản đồ mới coi là "có vệt đáng theo" -
                                # tránh vài vệt mùi lẻ tẻ, rất mờ (còn sót
                                # lại lúc mới có 1-2 kiến tha ít ỏi) cũng
                                # kích hoạt tuyển mộ ồ ạt không đáng
PHEROMONE_RECRUIT_NEST_EXCLUDE_RADIUS = 6  # loại hẳn vùng trong bán kính
                                # này quanh cửa tổ ra khỏi phân phối tuyển
                                # mộ - MỌI kiến tha đồ về đều hội tụ qua
                                # đây bất kể tìm thấy ăn ở đâu, nên đây
                                # luôn là nơi đậm mùi NHẤT dù không nói
                                # lên gì về vị trí thức ăn thật; nếu không
                                # loại trừ, tuyển mộ sẽ hút nhầm kiến về
                                # quanh tổ thay vì ra đúng chỗ có ăn

# ----- "Bản đồ nhiệt" nơi kiến đã ghé qua gần đây - THAY vai trò dẫn
# hướng tìm ăn mà pheromone từng đảm nhiệm: khi 1 kiến đang tìm ăn (SEARCHING)
# cần chọn điểm khám phá mới, nó ưu tiên vùng CÒN Ít NHIỆT (chưa ai mới đi
# qua) để đàn tự nhiên tỏa ra phủ khắp bản đồ thay vì dẫm chân lên nhau,
# rồi mới tính đường đi NGẮN NHẤT any-angle (pathfinding.py) tới đó -
# xem AntColony._pick_explore_target.
VISIT_HEAT_DEPOSIT = 0.5    # lượng "nhiệt" để lại mỗi tick tại ô đang đứng
VISIT_HEAT_DECAY = 0.995    # mỗi tick nhiệt giảm còn 99.5% (tan chậm hơn
                            # pheromone nhiều - cần "nhớ" vùng đã đi qua đủ
                            # lâu để đàn thực sự tỏa ra khắp bản đồ)
VISIT_HEAT_MAX = 20.0

# ----- Pheromone báo động (khi có kẻ thù trên mặt đất) -----
DANGER_PHEROMONE_DECAY = 0.85   # giảm RẤT nhanh - chỉ còn tác dụng ngay
                                # sát nơi kẻ thù vừa xuất hiện, tan trong
                                # vài chục tick chứ không lan rộng/tồn lâu
DANGER_DEPOSIT_AMOUNT = 3.0     # lượng mùi báo động kẻ thù để lại mỗi tick
DANGER_DEPOSIT_RADIUS = 2        # bán kính lan tỏa quanh vị trí kẻ thù -
                                # hẹp, không phủ kín cả khu vực quanh tổ
DANGER_PHEROMONE_MAX = 10.0

# ----- Thức ăn trên mặt đất (2 LOẠI: "hạt" phổ biến, giá trị thường +
# "mật hoa" HIẾM hơn nhưng GIÁ TRỊ CAO hơn hẳn - tha 1 lần mật hoa gần
# bằng cả 3 lần hạt, nên đáng để kiến "ưu tiên" quay lại đúng cụm mật hoa
# đã tìm thấy thay vì cụm hạt bình thường gần đó. Đây CHÍNH LÀ chỗ phối
# hợp với cơ chế TUYỂN MỘ theo mùi (xem AntColony._sample_recruit_candidates
# trong ants.py + deposit_pheromone trong world.py): nguồn càng giá trị
# cao thì vệt mùi dẫn tới đó càng đậm (lượng mùi để lại TỈ LỆ với
# carry_amount), nên mật hoa tự nhiên "hút" được nhiều kiến khác hơn hạt -
# giống hệt cách đàn kiến thật ưu tiên khai thác nguồn ăn giàu năng lượng.
# Trước đây (bản cũ) game chỉ có 1 loại hạt duy nhất, không có sự khác
# biệt nào giữa các cụm thức ăn. -----
FOOD_CLUSTERS = 16          # ĐÃ GIẢM từ 26 - bản trước phủ tới ~28% diện
                             # tích bản đồ ngay lúc khởi tạo (mỗi cụm là 1
                             # khối ĐẶC 5x5 ô, không phải rải thưa), khiến
                             # thức ăn cảm giác vô hạn ngay từ đầu ván -
                             # giảm SỐ LƯỢNG cụm (không giảm độ đậm mỗi
                             # cụm, xem FOOD_PER_CLUSTER) để bản đồ thoáng
                             # hơn, mỗi cụm tìm được vẫn đáng công (đậm),
                             # nhưng phải đi xa hơn/tìm nhiều hơn mới đủ ăn
FOOD_CLUSTER_RADIUS = 2

FOOD_TYPE_SEED = 0      # hạt - loại PHỔ BIẾN, giá trị thường
FOOD_TYPE_NECTAR = 1    # mật hoa/quả mọng - HIẾM hơn hẳn, giá trị CAO hơn

FOOD_TYPE_VALUE = {
    FOOD_TYPE_SEED: 1.0,    # mỗi lần nhặt = 1.0 đơn vị (mốc chuẩn)
    FOOD_TYPE_NECTAR: 3.0,  # gấp 3 hạt thường - cùng thang giá trị với
                            # WATER_CARRY_AMOUNT (=3.0) để không lệch pha
                            # so với kinh tế nước đã có sẵn trong game
}
FOOD_TYPE_COLOR = {
    FOOD_TYPE_SEED: (150, 115, 60),      # nâu hạt
    FOOD_TYPE_NECTAR: (230, 190, 60),    # vàng óng mật hoa - đủ khác màu
                                          # nâu hạt VÀ màu cam của đàn xâm
                                          # lược (255,140,100) để không
                                          # nhầm lẫn khi nhìn thoáng qua
}
# Tỉ lệ xuất hiện mỗi loại khi 1 cụm thức ăn mới sinh ra (phải cộng lại =
# 1.0) - mật hoa HIẾM hơn hẳn hạt, đúng tinh thần "nguồn giàu thì khan
# hiếm" (nếu phổ biến như hạt thì mất hết ý nghĩa "đáng tuyển mộ tới").
FOOD_TYPE_WEIGHTS = {
    FOOD_TYPE_SEED: 0.78,
    FOOD_TYPE_NECTAR: 0.22,
}
FOOD_PER_CLUSTER = 6.0  # số "đơn vị" thức ăn (không phải giá trị dinh dưỡng)

# ----- Thức ăn HỎNG theo thời gian nếu không được nhặt - xem
# SurfaceWorld.decay_food() trong world.py. Trước đây thức ăn để bao lâu
# trên bản đồ cũng không mất giá trị, chỉ biến mất khi bị ăn hết - khác
# hẳn thực tế nuôi kiến: mồi/thức ăn để lâu (dế chết, giọt mật khô) sẽ
# mốc/hỏng, người nuôi phải dọn đi trước khi sinh ruồi giấm/ve hại. Ở đây
# đơn giản hóa thành: quá hạn "tươi" mà chưa được nhặt hết -> giá trị TỰ
# GIẢM DẦN rồi biến mất hẳn, đồng thời đổi màu ngả xám/mốc để BÁO TRƯỚC
# cho người chơi thấy (xem render_surface.py) - không có kiến nào phải đi
# "dọn mốc" (khác hẳn xác chết - đó là việc CỐ Ý thêm task lao động qua
# necrophoresis; ở đây thức ăn mốc chỉ đơn giản là lãng phí, mất luôn).
FOOD_SPOIL_TICKS = 1800        # thức ăn "tươi" được ngần này tick (~30
                                # giây ở tốc độ x1) trước khi bắt đầu hỏng
FOOD_SPOIL_RATE_PER_TICK = 0.996  # sau ngưỡng trên, mỗi tick còn lại
                                # bấy nhiêu % giá trị (giảm dần, không mất
                                # NGAY LẬP TỨC - người chơi vẫn có 1 "cửa
                                # sổ" để kịp thấy và tận dụng nốt)
FOOD_MIN_VALUE = 0.15          # giá trị dưới mức này coi như hỏng HẲN,
                                # biến mất khỏi bản đồ (kiến không nhặt
                                # được phần thức ăn "vụn mốc" còn sót lại)

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
# near_water() trong world.py, dùng trong _update_surface_ants ants.py -
# near_water() coi Ô ĐANG ĐỨNG hoặc 1 trong 4 ô liền kề là nước thì tính
# là "sát mép", không có bán kính tùy chỉnh riêng).
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
# tuyệt đối). Các cặp phòng CHUNG TẦNG (kho/nước, trứng/ấu trùng) được đặt
# lệch hẳn sang 2 bên (trái/phải) để không đè lên nhau khi vẽ. LƯU Ý LỊCH
# SỬ: hướng lệch góc của GUARD_OFFSET_XY (thay vì thẳng trục dọc đơn giản)
# là di sản từ thời còn 2 tổ (tổ đối thủ LẬT GƯƠNG offset của tổ chính,
# cần tránh 2 phòng gác cửa của 2 tổ chồng lên nhau) - từ khi bỏ tổ đối
# thủ cố định (xem khối "Đàn kiến ngoại lai" ở trên), ràng buộc đó không
# còn nhưng giữ nguyên giá trị vì vẫn hoạt động tốt, không cần đổi lại.
GUARD_OFFSET_XY = (-3 * ROOM_LAYOUT_SCALE, -4 * ROOM_LAYOUT_SCALE)   # ngay dưới cửa hang - gần lỗ tổ nhất
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

# ----- Khiêng mồi lớn theo nhóm (cooperative transport) - xem giải thích
# đầy đủ ở STATE_HAUL_APPROACH/STATE_HAUL_GRIP trong phần STATE_* phía
# trên. -----
HAUL_MIN_ANTS = 4             # số kiến TỐI THIỂU phải có mặt CÙNG LÚC tại
                              # xác mới đủ sức khiêng về - ít hơn thì phải
                              # đứng chờ thêm đồng đội tới
HAUL_MAX_HAULERS = 7          # trần số kiến được phép cùng lúc lao tới 1
                              # xác (gồm cả đang tới lẫn đang đứng chờ) -
                              # tránh gọi quá nhiều kiến bỏ dở việc kiếm ăn
                              # bình thường chỉ vì 1 xác duy nhất
HAUL_TARGET_PROB = 0.5        # xác suất 1 kiến TÌM ĂN vừa cần chọn điểm
                              # đến mới sẽ CHỌN ĐI khiêng xác (nếu còn chỗ,
                              # xem HAUL_MAX_HAULERS) thay vì dò ngẫu nhiên
                              # như bình thường - xác thú lớn dễ thấy/dễ
                              # ngửi mùi hơn hẳn 1 miếng mồi thường, nên
                              # xác suất để ý cao hơn hẳn tuyển mộ qua mùi
                              # thông thường (PHEROMONE_RECRUIT_PROB)
HAUL_DECAY_TICKS = 900        # xác chỉ "tươi" trong ngần này tick (~15
                              # giây ở tốc độ x1) - không gọi đủ người kịp
                              # thời thì coi như xác đã rữa/bị loài khác
                              # tranh mất, biến mất luôn - thúc đẩy phản
                              # ứng nhanh, giống áp lực thời gian thật khi
                              # có xác mồi ngoài bãi
HAUL_TOTAL_FOOD_VALUE = 24.0   # tổng giá trị dinh dưỡng CẢ XÁC đem lại
                              # (~24 lần giá trị 1 đơn vị hạt thường) -
                              # chia đều cho toàn bộ nhóm khiêng lúc xuất
                              # phát (nhóm càng đông, mỗi con mang về càng
                              # ít - nhưng về nhanh hơn vì tha nhẹ hơn)

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
JOB_DIGGER = 3               # đào đất mở rộng/xây phòng mới - xem
                             # AntColony._update_diggers(), MAX_CONCURRENT_
                             # DIGGERS + DIG_* bên dưới, và UndergroundWorld.
                             # dirt_layers/get_active_dig_jobs() trong world.py
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

GROOMING_DISTANCE = 0.3     # 2 con kiến RẢNH RỖI (STATE_DWELL) đứng cách
                             # nhau trong bán kính này (đơn vị ô mô phỏng)
                             # thì THỈNH THOẢNG được vẽ lấp lánh "chải
                             # chuốt" (grooming) - xem
                             # render_underground.draw_ant_social_fx().
                             # Hiệu ứng THUẦN HIỂN THỊ, tính lại mỗi khung
                             # hình từ vị trí hiện tại - KHÔNG lưu state gì
                             # mới vào AntColony, không ảnh hưởng mô phỏng.

# ----- Đàn kiến ngoại lai (xâm nhập theo đợt, không có tổ cố định) -----
# Thay vì nuôi song song 1 tổ đối thủ tồn tại vĩnh viễn, bản đồ giờ chỉ có
# ĐÚNG 1 tổ (của người chơi). Thỉnh thoảng 1 đàn kiến LẠ (không có tổ/nhà
# riêng - xuất hiện từ rìa bản đồ, không phải sinh ra từ đâu cả) sẽ kéo về
# tổ của người chơi để CƯỚP PHÁ: cướp thức ăn trong kho VÀ tấn công/cướp
# trứng+ấu trùng, rồi rút lui mang theo những gì cướp được (hoặc bị đánh
# bại hoàn toàn nếu lính gác đủ mạnh). Xem invasion.py (InvasionManager).
INVASION_ENABLED = True
INVASION_FIRST_WAVE_TICK = 4800   # đợt đầu tiên chỉ tới sau bấy nhiêu tick
                            # (~80s ở tốc độ x1) - ĐÃ TĂNG so với thử nghiệm
                            # đầu (2400): 1 tổ mới lập/còn rất nhỏ (5-10
                            # con, CHƯA CÓ lính gác) gần như không có khả
                            # năng chống đỡ đợt đầu nếu tới quá sớm - kiểm
                            # thử thực nghiệm cho thấy với mốc 2400, đàn bị
                            # xóa sổ dần đều tới tuyệt chủng hoàn toàn dù
                            # không cần người chơi làm gì (so sánh: tắt hẳn
                            # invasion thì đàn TỰ PHÁT TRIỂN khỏe mạnh từ
                            # 6 lên tới 25-29 con trong cùng khoảng thời
                            # gian) - dời đợt đầu ra xa hơn để đàn có cơ hội
                            # tự nhiên có vài lính gác trước khi bị thử thách.
INVASION_BASE_INTERVAL_TICKS = 4800  # khoảng cách GIỮA 2 đợt lúc đầu ván
                            # (~80s ở tốc độ x1) - tăng cùng tỉ lệ với mốc
                            # đợt đầu ở trên
INVASION_INTERVAL_MIN_TICKS = 1500   # khoảng cách TỐI THIỂU giữa 2 đợt dù
                            # đàn đã phát triển rất lâu (không dồn dập vô
                            # hạn - vẫn phải có khoảng thở)
INVASION_INTERVAL_DECAY_PER_WAVE = 100  # mỗi đợt trôi qua, khoảng cách tới
                            # đợt SAU rút ngắn thêm bấy nhiêu tick (tăng
                            # tần suất dần theo thời gian, xem
                            # InvasionManager._schedule_next_wave)
INVASION_BASE_SWARM_SIZE = 2     # số quân đợt ĐẦU TIÊN - CỐ TÌNH rất nhẹ
                            # (giảm từ 4 xuống 2): đợt đầu tiên đóng vai trò
                            # "cảnh báo/dạy người chơi", không phải thử
                            # thách sinh tử ngay khi đàn còn chưa kịp có
                            # lính gác nào
INVASION_MAX_SWARM_SIZE = 24     # trần số quân dù đàn đã phát triển rất lâu
INVASION_SWARM_GROWTH_PER_WAVE = 1.15  # mỗi đợt sau đông hơn đợt trước bấy
                            # nhiêu lần (giảm từ 1.6 xuống 1.15 - tăng dần
                            # CHẬM VÀ ĐỀU hơn hẳn, để người chơi có đủ thời
                            # gian đầu tư thêm lính gác theo kịp áp lực,
                            # thay vì áp lực vọt lên quá nhanh)
INVASION_SPEED = 0.17             # tốc độ hành quân trên mặt đất
INVASION_UG_SPEED = 0.05          # tốc độ di chuyển dưới hầm (chậm hơn mặt
                            # đất - hành lang chật, phải len lỏi)
INVASION_ENTRANCE_FIGHT_TICKS = 260  # tối đa giao chiến với lính gác ở cửa
                            # hang bấy nhiêu tick trước khi TỰ ĐỘNG coi là
                            # đã vượt qua (tránh kẹt vô hạn nếu 2 bên hòa)
INVASION_ATTACKER_KILL_PROB = 0.016   # xác suất/tick 1 quân xâm nhập hạ
                            # được 1 lính gác (nhân MAJOR_DEFENSE_FACTOR
                            # nếu lính gác là ROLE_MAJOR, như raid cũ)
INVASION_DEFENDER_KILL_PROB = 0.032   # lính gác có lợi thế sân nhà, xác
                            # suất hạ quân xâm nhập/tick cao hơn hẳn (tăng
                            # từ 0.024 - ĐẦU TƯ VÀO LÍNH GÁC phải thực sự
                            # đáng giá: có phòng thủ phải cản được hầu hết
                            # 1 đợt xâm nhập cỡ vừa, không chỉ làm chậm lại)
INVASION_FOOD_STEAL_PER_TICK = 3.0    # mỗi tick còn cướp phá kho thì rút
                            # được bấy nhiêu thức ăn (chia đều số quân)
INVASION_EGG_STEAL_INTERVAL = 90      # cứ mỗi bấy nhiêu tick còn cướp phá ở
                            # phòng trứng/ấu trùng, bắt/phá 1 quả trứng
                            # (tăng từ 45 - giảm bớt tốc độ tàn phá brood,
                            # từng đủ sức xóa sổ TOÀN BỘ trứng/ấu trùng của
                            # 1 đàn nhỏ chỉ trong 1 đợt duy nhất)
INVASION_LARVA_STEAL_INTERVAL = 110   # ...và 1 con ấu trùng (ấu trùng "đắt"
                            # hơn trứng nên bắt chậm hơn 1 chút)
INVASION_MAX_LOOT_TICKS = 140         # tối đa cướp phá 1 phòng bấy nhiêu
                            # tick trước khi tự rút (giảm từ 200 - hạn chế
                            # tổng thiệt hại tối đa mỗi lượt cướp phá)
INVASION_RETREAT_SPEED = 0.20         # rút lui nhanh hơn lúc tiến quân (vội
                            # chạy khi đã cướp được đồ / bị đánh lui)

# ----- (Đã bỏ tổ đối thủ cố định - xem khối "Đàn kiến ngoại lai" ở trên) -----
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

# ----- Tổ MỞ RỘNG theo dân số - xem UndergroundWorld.update_room_sizes()
# trong world.py: trước đây kích thước MỌI phòng CỐ ĐỊNH suốt ván bất kể
# đàn 10 con hay 200 con, khác hẳn thực tế nuôi kiến (người nuôi phải
# chuyển đàn sang tổ lớn hơn khi đàn đông lên, nếu không đàn chật chội).
# CHỈ 4 phòng gắn liền trực tiếp với QUY MÔ đàn mới "phình" ra theo dân
# số (Kho/Ấu trùng/Bể nước/Trứng - nơi chứa TÀI NGUYÊN & CON NON, càng
# đông đàn càng cần nhiều); Phòng gác cửa/Nghĩa địa/Phòng nhộng/Phòng
# chúa GIỮ NGUYÊN kích thước cố định như trước (không liên quan trực
# tiếp tới "cần chứa được bao nhiêu", hoặc đã có cơ chế riêng - phòng chúa
# đã tự lớn dần lúc lập tổ xong, xem ROOM_RADIUS_FOUNDING_CHAMBER).
#
# Công thức dùng CĂN BẬC HAI của dân số (không phải tỉ lệ thuận) để tăng
# CHẬM DẦN theo quy mô - đàn 200 con không làm phòng to gấp 20 lần đàn 10
# con, chỉ to hơn hợp lý (~gấp 1.6-2 lần bán kính gốc ở dân số tối đa),
# giống cách 1 tổ ong/kiến thật không "nở" tuyến tính vô hạn theo số cá
# thể mà có xu hướng bão hòa dần.
ROOM_GROWTH_PER_SQRT_ANT = 0.4     # mỗi đơn vị sqrt(dân_số) cộng thêm
                                    # bấy nhiêu vào bán kính phòng (đơn vị
                                    # ô lưới) - xem ROOM_GROWABLE_IDS
ROOM_GROWABLE_IDS = (0, 1, 3, 4)   # id các phòng ĐƯỢC mở rộng: 0=Kho thức
                                    # ăn, 1=Ấu trùng, 3=Bể trữ nước,
                                    # 4=Phòng trứng (khớp room_id trong
                                    # UndergroundWorld.rooms)

# ===== Đào đất THẬT (JOB_DIGGER, xem AntColony._update_diggers() +
# UndergroundWorld.dirt_layers trong world.py) - phòng mới/mở rộng phòng
# cũ giờ không còn "hiện ra" tức thời khi đạt mốc dân số nữa, mà phải chờ
# 1-vài kiến đào chuyên trách BÒ TỚI RÌA và đào THẬT từng ô lưới, có thể
# THEO DÕI TRỰC TIẾP quá trình này (xem render_underground.draw_dirt_grid).
SHAFT_DIG_RADIUS = 1.2       # trục giếng lên mặt đất LUÔN thông ở mọi tầng
                             # (không phải chờ đào - đại diện thang máy cố định)
DIG_TICKS_PER_CELL = 45      # (~0.75s ở 60 FPS) thời gian đào XONG 1 ô đất
MAX_CONCURRENT_DIGGERS = 3   # tối đa bấy nhiêu thợ đang đào CÙNG LÚC (đủ
                             # để thấy rõ tiến độ mà không rút cạn lực
                             # lượng kiếm ăn/chăm sóc - xem _rebalance_labor)
ROOM_DIG_UNLOCK_FRACTION = 0.8  # phòng MỚI (chưa từng mở) cần đào đủ bấy
                             # nhiêu % diện tích thiết kế mới coi là "xong"
                             # để chính thức tách khỏi Phòng chúa (không
                             # cần 100% tuyệt đối vì rìa hình tròn/lưới ô
                             # vuông không bao giờ khớp tuyệt đối)

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
STATE_RAID_TO_ENEMY = 9    # (không còn dùng - từng là "đội xâm chiếm hành
                            # quân sang tổ đối thủ", đã bỏ khi chuyển sang
                            # cơ chế đàn kiến ngoại lai - giữ số hiệu để
                            # không xáo trộn các state khác)
STATE_RAID_LOOT = 10       # (không còn dùng - lý do như trên)

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

# ----- Necrophoresis (thợ mai táng) - xem AntColony._update_undertakers()
# trong ants.py: kiến chết DƯỚI HẦM để lại 1 XÁC THẬT tại đúng vị trí vừa
# chết, chờ 1 nurse đang rảnh việc tự nguyện đi khiêng về Nghĩa địa (chỉ
# lúc đó self.underground.corpse_count mới thực sự tăng) - khác hẳn bản
# cũ coi cái chết là 1 con số trừu tượng, tự động "biến" thành xác ở nghĩa
# địa ngay lập tức không ai phải đi lấy. Kiến chết TRÊN MẶT ĐẤT (già/đói
# lúc đang kiếm ăn, hoặc bị địch giết) vẫn dùng add_corpse() tức thời như
# cũ - coi như "hi sinh tại trận, không thu hồi được xác", giống thực tế
# đàn kiến cũng không phải lúc nào cũng lấy lại được xác đồng đội chết ở
# xa ngoài mặt trận.
STATE_UNDERTAKER_TO_CORPSE = 19     # đang đi tới vị trí xác để khiêng
STATE_UNDERTAKER_TO_GRAVEYARD = 20  # đang khiêng xác về Nghĩa địa

# ----- Khiêng mồi lớn theo nhóm (cooperative transport) - xem
# EnemyManager._spawn_carcass()/decay_carcass() trong enemy.py +
# AntColony._update_haulers() trong ants.py: khi lính gác ĐÁNH BẠI HẲN 1
# kẻ thù tự nhiên (khác với chỉ đuổi nó bỏ chạy), xác nó để lại là 1 "mồi
# lớn" giàu dinh dưỡng NHƯNG quá nặng để 1 mình 1 con kiến tha nổi - phải
# có ĐỦ số kiến tập trung tại đó CÙNG LÚC mới đủ sức khiêng về, giống hệt
# cách kiến thật hợp sức khiêng con mồi to hơn cả cơ thể chúng (cooperative
# transport) - trước đây kẻ thù bị đánh bại chỉ biến mất, không để lại gì.
STATE_HAUL_APPROACH = 21   # đang trên đường tới xác con mồi lớn
STATE_HAUL_GRIP = 22       # đã tới nơi, đang ĐỨNG CHỜ đủ đồng đội mới cùng khiêng

STATE_DIGGER_TRAVEL = 23  # đang bò tới rìa đất cần đào (xem JOB_DIGGER)
STATE_DIGGER_DIGGING = 24  # đang đứng đào 1 ô đất cụ thể (đếm ngược DIG_TICKS_PER_CELL)
STATE_DIGGER_IDLE = 25    # vừa được giao JOB_DIGGER HOẶC vừa đào xong 1 ô,
                          # đang chờ _update_diggers() gán việc kế tiếp -
                          # CỐ Ý KHÔNG dùng STATE_DWELL (dù ý nghĩa gần
                          # giống "đang rảnh"): STATE_DWELL có 1 hàm xử lý
                          # CHUNG riêng (_update_dwelling_ants, đọc
                          # dwell_room_id/dwell_ticks/next_state) áp dụng
                          # cho MỌI kiến đang ở state đó bất kể job - dùng
                          # nhầm sẽ khiến digger bị hàm đó "cuỗm mất" và
                          # lôi đi lượn/rời hầm ngoài ý muốn trước khi kịp
                          # nhận việc đào mới.

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
EGG_MIN_STORAGE_BUFFER_PER_ANT = 0.0  # kho phải dư ra >= (dân số hiện tại
                             # x số này) NGOÀI EGG_FOOD_COST thì mới được
                             # đẻ trứng tiếp. ĐÃ GIẢM VỀ 0 sau 2 lần thử
                             # giảm dần (8.0 -> 1.5 -> 0.3) vẫn CHƯA đủ:
                             # ngay cả 0.3 thỉnh thoảng vẫn khiến sinh sản
                             # đóng băng hàng chục nghìn tick đúng lúc đàn
                             # cần thay thế gấp lứa sáng lập đang chết già
                             # đồng loạt (cùng tuổi vì cùng nở 1 đợt lúc
                             # lập tổ) - dẫn tới "vách đá nhân khẩu học":
                             # dân số rơi tự do quanh mốc MAX_AGE_TICKS vì
                             # không kịp có lứa kế cận. Đã có
                             # MAX_ANTS_PER_COLONY làm TRẦN CỨNG chặn tăng
                             # trưởng vô hạn rồi, không cần thêm "phanh
                             # mềm" theo dân số ở đây nữa - giờ chỉ cần đủ
                             # EGG_FOOD_COST (+ nước) là đẻ được, giống hệt
                             # logic đẻ trứng LÚC LẬP TỔ (dùng năng lượng
                             # riêng của chúa, không bị chặn theo dân số).
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

# =======================================================================
# GIAI ĐOẠN LẬP TỔ (founding) - TÙY CHỌN, mặc định TẮT để không đổi trải
# nghiệm chơi hiện có. Mô phỏng đúng thực tế: 1 ván bắt đầu từ ĐÚNG 1 kiến
# chúa (population=0 trong AntColony - chúa không phải 1 "con kiến" trong
# mảng self.alive, chỉ là 1 khái niệm/phòng), tự đẻ lứa trứng đầu tiên
# bằng NĂNG LƯỢNG DỰ TRỮ RIÊNG (mỡ + cơ cánh tiêu hao dần - đúng sinh học
# thật, chúa KHÔNG ăn gì suốt giai đoạn này), không cần kho thức ăn (vì
# chưa có ai tha mồi về). Khi đủ NANITIC_TARGET thợ đầu tiên nở ra, coi
# như lập tổ THÀNH CÔNG, chuyển hẳn sang luật chơi bình thường (đẻ trứng
# lại cần kho thức ăn như cũ).
# =======================================================================
FOUNDING_MODE_ENABLED = True  # BẬT MẶC ĐỊNH - đúng thực tế: mọi ván LUÔN
                             # bắt đầu từ 1 kiến chúa tự đi tìm chỗ rồi
                             # đào hang lập tổ (xem QUEEN_WALK_* ngay dưới
                             # đây) - KHÔNG có tổ nào "đã có sẵn thợ/đã có
                             # sẵn phòng ốc chức năng" ngay từ đầu như
                             # trước. Game chỉ có ĐÚNG 1 tổ (của người
                             # chơi) - "quân xâm nhập" (xem invasion.py)
                             # là toán cướp phá KHÔNG có tổ/nhà riêng, nên
                             # quy tắc "đào tới đâu, có chức năng tới đó"
                             # này áp dụng cho TOÀN BỘ tổ đang tồn tại
                             # trong game, không có ngoại lệ nào.
QUEEN_WALK_SPEED = 0.045       # ô/tick MẶC ĐỊNH - CHẬM hơn hẳn ANT_SPEED
                             # (0.14) vì chúa đang "dò dẫm" tìm chỗ tốt để
                             # đào hang, không vội vã như thợ kiếm ăn.
                             # Chỉnh được TRONG GAME lúc đang lập tổ (xem
                             # panel "Điều khiển lập tổ" trong hud.py) -
                             # 2 hằng số MIN/MAX dưới đây là giới hạn của
                             # thanh trượt đó.
QUEEN_WALK_SPEED_MIN = 0.015
QUEEN_WALK_SPEED_MAX = 0.18
QUEEN_WALK_HOPS_MIN = 3         # đi qua ÍT NHẤT bấy nhiêu điểm dừng ngẫu
QUEEN_WALK_HOPS_MAX = 6         # nhiên (nhiều nhất) trước khi CHỌN chỗ
                             # cuối cùng và bắt đầu đào - tạo cảm giác
                             # chúa đang "cân nhắc" thay vì đào ngay tại
                             # chỗ hạ cánh. Số điểm dừng CÒN LẠI cũng chỉnh
                             # được trong game bằng nút +/- (giới hạn
                             # QUEEN_WALK_HOPS_STEP_MIN/MAX bên dưới).
QUEEN_WALK_HOPS_STEP_MIN = 0
QUEEN_WALK_HOPS_STEP_MAX = 15
QUEEN_WALK_RADIUS = 3.5 * ROOM_LAYOUT_SCALE  # bán kính lượn quanh vị trí
                             # lỗ tổ (NEST_POS) khi tìm chỗ MẶC ĐỊNH - đủ
                             # gần để người chơi luôn thấy chúa trong
                             # khung hình. Cũng chỉnh được trong game.
QUEEN_WALK_RADIUS_MIN = 1.0 * ROOM_LAYOUT_SCALE
QUEEN_WALK_RADIUS_MAX = 8.0 * ROOM_LAYOUT_SCALE
QUEEN_DIG_TICKS = 200           # ~3.3 giây ở 60 FPS MẶC ĐỊNH - khoảng dừng
                             # "đang đào xuống" trước khi chuyển hẳn vào
                             # lòng đất (camera tự động đưa xuống Phòng
                             # chúa). TỐC ĐỘ đào thực tế = QUEEN_DIG_TICKS
                             # / queen_dig_speed_mult (chỉnh được trong
                             # game, xem GameState.queen_dig_speed_mult) -
                             # mult=1.0 (mặc định) đúng bằng QUEEN_DIG_TICKS
                             # tick, mult=2.0 thì NHANH GẤP ĐÔI, v.v.
QUEEN_DIG_SPEED_MULT_MIN = 0.25
QUEEN_DIG_SPEED_MULT_MAX = 4.0
QUEEN_INITIAL_ENERGY = 600.0   # dự trữ ban đầu - đủ dùng THOẢI MÁI ở tốc
                             # độ tiêu hao mặc định bên dưới (không thiết
                             # kế để dễ "thua ngay từ đầu" - đây là mảng
                             # thêm chiều sâu/thực tế, không phải thử
                             # thách khó chính của game)
QUEEN_ENERGY_DECAY_PER_TICK = 0.3  # tiêu hao dự trữ mỗi tick - CẢ KHI
                             # không đẻ trứng (mô phỏng chúa vẫn "sống"
                             # bằng dự trữ suốt giai đoạn tự nhốt)
QUEEN_ENERGY_PER_EGG = 40.0    # tốn bấy nhiêu dự trữ mỗi trứng lúc ĐANG
                             # lập tổ - so sánh với EGG_FOOD_COST (tốn
                             # KHO) áp dụng sau khi lập tổ xong
FOUNDING_NANITIC_TARGET = 4    # đủ bấy nhiêu thợ đầu tiên (nanitic - thợ
                             # lứa đầu, nhỏ con hơn hẳn do mẹ ít tài
                             # nguyên nuôi, đúng thực tế) thì lập tổ xong
ROOM_RADIUS_FOUNDING_CHAMBER = 1.6 * ROOM_LAYOUT_SCALE  # bán kính HỐC LẬP
                             # TỔ - nhỏ hơn hẳn "Phòng chúa" trưởng thành
                             # (ROOM_RADIUS_QUEEN, gấp gần 5 lần) - đúng
                             # thực tế: chúa mới chỉ tự đào 1 hốc bé tí vừa
                             # đủ chỗ, phòng ĐẦY ĐỦ chỉ hình thành SAU khi
                             # có thợ thật sự đào rộng ra. Tự "nở to" thành
                             # ROOM_RADIUS_QUEEN ngay khi lập tổ xong (xem
                             # room_center_and_radius_by_id trong world.py
                             # và render_underground.py - áp dụng bán kính
                             # này CHỈ trong lúc founding_phase còn True).
NANITIC_SIZE_SCALE = 0.68      # nanitic nhỏ hơn thợ thường bao nhiêu lần
                             # khi vẽ (áp dụng NHÂN THÊM vào MAJOR_SIZE_SCALE
                             # nếu 1 nanitic hiếm khi rơi vào role lính -
                             # dù hiếm, lính "nanitic" vẫn phải nhỏ hơn
                             # lính thường cùng tỉ lệ này, không phải to
                             # bằng lính bình thường)

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
ENEMY_MIN_COLONY_POPULATION = 15  # tổ phải có ÍT NHẤT bấy nhiêu thợ mới
                                 # bắt đầu bị kẻ thù tự nhiên để ý tới (xem
                                 # enemy.py update()) - 1 tổ CÒN NON (vừa
                                 # lập tổ xong, quần thể còn quá nhỏ để tự
                                 # vệ hay chịu nổi thương vong) gần như
                                 # KHÔNG có khả năng phục hồi nếu liên tục
                                 # bị tấn công đều đặn mỗi 500-1200 tick
                                 # ngay từ những phút đầu tiên - đây từng
                                 # là nguyên nhân chính khiến tổ mới lập
                                 # gần như luôn tuyệt chủng dù thức ăn/nước
                                 # dự trữ vẫn còn dư. Không áp dụng cho
                                 # ENEMY_MAX_KILLS_PER_VISIT bên dưới -
                                 # ngưỡng đó vẫn có tác dụng SAU KHI tổ đã
                                 # vượt qua mốc này.
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
# TỪNG chỉnh: mỗi lần tái sinh thêm tối đa (2*FOOD_CLUSTER_RADIUS+1)^2 =
# 25 ô x 5.0 đơn vị/ô = 125 đơn vị, cứ mỗi 350 tick (~5.8 giây ở tốc độ
# x1) - tức trung bình ~21 đơn vị/giây, tương đương ~21 LẦN NHẶT MỒI THƯỜNG
# MỖI GIÂY chỉ riêng từ tái sinh (chưa tính lượng khởi tạo ban đầu) - QUÁ
# NHIỀU VÀ QUÁ NHANH, khiến thức ăn gần như vô hạn, kiến không bao giờ
# thực sự khan hiếm. Đã GIẢM cả 2 chiều: khoảng cách giữa 2 lần tái sinh
# XA hơn hẳn (350 -> 900 tick, ~15 giây) VÀ lượng mỗi lần ÍT hơn hẳn (5.0
# -> 2.0 đơn vị/ô) - tổng hợp lại giảm tốc độ tái sinh khoảng ~6.4 lần so
# với trước, để thức ăn còn cảm giác "hạn chế, phải đi tìm" thay vì rải
# đều khắp nơi liên tục.
FOOD_RESPAWN_INTERVAL = 900  # cứ mỗi bấy nhiêu tick, có 1 cụm thức ăn mới
                             # xuất hiện ngẫu nhiên (mô phỏng thức ăn theo mùa)
FOOD_RESPAWN_AMOUNT = 2.0    # lượng thức ăn của cụm mới mỗi lần tái sinh
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
COLOR_GROUND_FILL = (205, 178, 132)
COLOR_SHAFT = (25, 18, 12)

# Lưới đất THẬT (xem UndergroundWorld.dirt_layers/render_underground.
# draw_dirt_grid) - ô CHƯA đào tô màu đất, chấm lấm tấm cho có kết cấu,
# viền sáng hơn cho ô đang Ở RÌA (sát vùng đã đào) để dễ theo dõi tiến độ.
COLOR_DIRT_SOLID = (58, 44, 34)
COLOR_DIRT_SPECK = (40, 30, 23)
COLOR_DIRT_FRONTIER = (110, 90, 60)

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

# Nghĩa địa/phòng rác: xác kiến chết DƯỚI HẦM được 1 nurse rảnh việc THẬT
# SỰ khiêng tới đây (xem STATE_UNDERTAKER_TO_CORPSE/TO_GRAVEYARD ở trên +
# AntColony._update_undertakers() trong ants.py) rồi mới tính là 1 "nắm
# xác" - kiến chết TRÊN MẶT ĐẤT (già/đói lúc kiếm ăn, hoặc bị địch giết)
# thì tính ngay lập tức, coi như hi sinh tại trận không thu hồi được xác.
# Xác cũ dần phân hủy/biến mất để nghĩa địa không phình to vô hạn.
GRAVEYARD_MAX_CORPSES = 60       # trần số "nắm xác" hiển thị cùng lúc
GRAVEYARD_DECAY_PER_TICK = 0.0008  # tốc độ phân hủy (xác cũ dần biến mất
                             # sau khoảng vài chục giây, không phải tức thời)
MAX_PENDING_CORPSES = 12    # trần số xác DƯỚI HẦM đang chờ được khiêng
                             # cùng lúc (KHÁC với GRAVEYARD_MAX_CORPSES ở
                             # trên - đây là hàng chờ TRƯỚC khi tới nghĩa
                             # địa) - phòng hờ trường hợp chết quá nhanh so
                             # với tốc độ khiêng (vd dịch bệnh/đói kém toàn
                             # đàn) khiến hàng chờ phình to vô hạn; xác dư
                             # ra ngoài trần này coi như bị bỏ lại, tính
                             # thẳng vào nghĩa địa qua add_corpse() luôn
                             # thay vì xếp hàng mãi không ai khiêng nổi.
UNDERTAKER_CHECK_INTERVAL = 20  # cứ mỗi ngần này tick mới thử phân công 1
                             # nurse rảnh đi khiêng xác (không cần kiểm
                             # tra MỖI tick - xác không "biến mất" ngay
                             # nếu chưa ai tới, không gấp)

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

# ----- Camera "TỰ LÁI" (chế độ ngắm cảnh kiểu screensaver) - xem
# GameState.update_camera_cruise()/touch_activity(): sau 1 khoảng KHÔNG
# thao tác gì (chuột/phím), camera tự nhẹ nhàng lượn qua từng phòng của
# tổ để "mời" người chơi ngồi ngắm mà không cần tự lái - CHỈ kích hoạt
# lúc THỰC SỰ rảnh tay (không đang theo dõi 1 con kiến, không đang giữa
# cảnh chúa lập tổ - 2 cái đó đã tự có camera riêng) và DỪNG NGAY lập
# tức, trả quyền lại cho người chơi, chỉ với 1 cái chạm chuột/phím bất kỳ. -----
CRUISE_IDLE_TICKS = 20 * FPS    # ~20 giây không thao tác gì thì bắt đầu
                             # tự lái
CRUISE_HOLD_TICKS = 8 * FPS     # dừng lại ngắm mỗi phòng khoảng bấy
                             # nhiêu tick (~8 giây) trước khi lượn sang
                             # phòng kế tiếp
CRUISE_CAMERA_SMOOTH = 0.02     # lượn CHẬM RÃI, êm hơn hẳn lúc theo dõi
                             # 1 con kiến (FOLLOW_CAMERA_SMOOTH=0.15) -
                             # đúng tinh thần "ngồi ngắm" nhàn tản, không
                             # vội vã

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
