"""SpriteManager: cho phép game dùng ẢNH PIXEL ART TÙY CHỈNH (do người chơi
tự vẽ, ví dụ bằng công cụ AntWorld Pixel Studio) THAY CHO hình vẽ vector
mặc định - nhưng HOÀN TOÀN TÙY CHỌN: nếu không tìm thấy file ảnh nào, game
vẫn chạy y hệt như trước (vẽ vector), không có gì bị hỏng cả.

Cách dùng: đặt file PNG (nền trong suốt) vào thư mục assets/sprites/, đặt
ĐÚNG TÊN theo quy ước bên dưới. Lúc chạy, mỗi khi cần vẽ 1 đối tượng, code
vẽ sẽ hỏi SpriteManager "có ảnh cho cái này không" - có thì dùng ảnh, không
thì tự vẽ vector như trước (xem gọi has()/get_static()/get_rotated() trong
render_surface.py và render_underground.py).

QUY ƯỚC TÊN FILE (đặt trong assets/sprites/, đuôi .png, nền trong suốt):
    ant_worker_main.png        - kiến tổ chính, bình thường (không tha mồi)
    ant_worker_main_carry.png  - kiến tổ chính, đang tha mồi
    ant_worker_rival.png       - kiến tổ đối thủ, bình thường
    ant_worker_rival_carry.png - kiến tổ đối thủ, đang tha mồi
    food.png                   - 1 miếng thức ăn (dùng CẢ trên mặt đất LẪN
                                  trong đống thức ăn ở kho dưới hầm)
    rock.png                   - 1 ô đá (vật cản)
    water.png                  - 1 ô nước (dùng CẢ vật cản trên mặt đất
                                  LẪN giọt nước trong bể trữ dưới hầm)
    egg.png                    - 1 quả trứng
    larva.png                  - 1 ấu trùng
    pupa.png                   - 1 kén nhộng
    queen.png                  - kiến chúa
    enemy.png                  - kẻ thù tự nhiên trên mặt đất
    nest_main.png               - lỗ tổ CHÍNH trên mặt đất
    nest_rival.png              - lỗ tổ ĐỐI THỦ trên mặt đất
    corpse.png                  - 1 "nắm xác" trong nghĩa địa

Ảnh kiến (ant_worker_*) và kẻ thù (enemy.png) sẽ được TỰ ĐỘNG XOAY theo
đúng hướng di chuyển thật của từng con (vẽ ảnh gốc quay đầu sang PHẢI,
code sẽ tự xoay góc còn lại) - không cần bạn tự vẽ nhiều hướng khác nhau.
"""
import os
import pygame

# Số bước góc xoay được CACHE SẴN cho mỗi ảnh kiến (24 bước = mỗi bước 15°)
# - xoay pygame khá tốn, cache theo bước rời rạc thay vì xoay lại mỗi khung
# hình cho mỗi con kiến giúp nhanh hơn NHIỀU khi có hàng trăm con cùng lúc,
# đổi lại hướng xoay không mượt tuyệt đối 100% mà "nhảy" từng 15° một -
# mắt thường gần như không nhận ra khác biệt này.
ROTATION_STEPS = 24


class SpriteManager:
    def __init__(self, sprites_dir):
        self.dir = sprites_dir
        self._raw_cache = {}   # filename -> Surface gốc đã convert_alpha (hoặc None nếu không có file)
        self._render_cache = {}  # (filename, size_px, step) -> Surface đã scale/xoay sẵn

    def _load_raw(self, filename):
        if filename in self._raw_cache:
            return self._raw_cache[filename]
        img = None
        path = os.path.join(self.dir, filename)
        if os.path.isfile(path):
            try:
                img = pygame.image.load(path).convert_alpha()
            except Exception:
                img = None  # file lỗi/hỏng -> coi như không có, tự vẽ vector như thường
        self._raw_cache[filename] = img
        return img

    def has(self, filename):
        """Có ảnh sẵn sàng dùng cho tên file này không (đã tồn tại + đọc được)."""
        return self._load_raw(filename) is not None

    def get_static(self, filename, size_px):
        """Ảnh KHÔNG xoay (thức ăn/đá/nước/trứng/ấu trùng/nhộng/chúa), đã co
        giãn đúng kích thước hiển thị `size_px` (hình vuông), có cache.

        Dùng `pygame.transform.scale` (nearest-neighbor, KHÔNG nội suy màu)
        thay vì `smoothscale` (nội suy bilinear) - vì sprite là ẢNH PIXEL
        ART độ phân giải rất thấp (16x16, 8x8...) vẽ bằng pixel_editor.py.
        smoothscale làm mờ nhòe ranh giới giữa các pixel khi phóng to (đúng
        thứ pixel art KHÔNG muốn - mất luôn cái "nét vuông vức" đặc trưng),
        còn scale giữ nguyên từng pixel gốc thành 1 khối vuông sắc cạnh khi
        phóng to, đúng phong cách pixel art.
        """
        raw = self._load_raw(filename)
        if raw is None:
            return None
        size_px = max(1, int(size_px))
        key = (filename, size_px, -1)
        cached = self._render_cache.get(key)
        if cached is None:
            cached = pygame.transform.scale(raw, (size_px, size_px))
            self._render_cache[key] = cached
        return cached

    def get_rotated(self, filename, size_px, angle_rad):
        """Ảnh kiến ĐÃ XOAY đúng hướng di chuyển (angle_rad: 0 = hướng sang
        phải, dương = ngược chiều kim đồng hồ, khớp hệ trục pygame/atan2
        đang dùng trong ants.py), đã co giãn đúng kích thước, có cache theo
        bước góc rời rạc (xem ROTATION_STEPS)."""
        raw = self._load_raw(filename)
        if raw is None:
            return None
        size_px = max(1, int(size_px))
        import math
        step = int(round((angle_rad % (2 * math.pi)) / (2 * math.pi) * ROTATION_STEPS)) % ROTATION_STEPS
        key = (filename, size_px, step)
        cached = self._render_cache.get(key)
        if cached is None:
            # Phóng to bằng "scale" (nearest-neighbor) TRƯỚC khi xoay, y hệt
            # lý do trong get_static() ở trên - giữ pixel art sắc nét thay
            # vì mờ nhòe. Phóng lên gấp đôi kích thước hiển thị thật rồi mới
            # xoay + thu lại đúng size_px giúp cạnh xoay đỡ răng cưa hơn so
            # với xoay thẳng trên ảnh nhỏ xíu (rotate() của pygame có nội
            # suy nhẹ ở các góc không tròn 90 độ, phóng to sẵn giảm bớt độ
            # "vỡ hạt" do nội suy đó gây ra).
            base = pygame.transform.scale(raw, (size_px * 2, size_px * 2))
            # pygame xoay NGƯỢC CHIỀU KIM ĐỒNG HỒ theo độ dương -> đổi dấu vì
            # angle_rad ở đây dùng quy ước toán học thường (atan2), độ xoay
            # cần truyền vào pygame.transform.rotate là độ, chiều dương =
            # ngược kim đồng hồ - trùng quy ước toán học nên KHÔNG cần đổi dấu
            deg = step * (360.0 / ROTATION_STEPS)
            rotated = pygame.transform.rotate(base, deg)
            # Thu lại đúng size_px (nearest-neighbor) - xoay xong ảnh to hơn
            # do rotate() tự nới khung chứa vừa đủ góc xoay, cần crop về
            # đúng tâm rồi resize về kích thước hiển thị thật.
            rect = rotated.get_rect()
            crop_size = min(rect.width, rect.height)
            crop_rect = pygame.Rect(0, 0, crop_size, crop_size)
            crop_rect.center = rect.center
            cropped = rotated.subsurface(crop_rect).copy()
            cached = pygame.transform.scale(cropped, (size_px, size_px))
            self._render_cache[key] = cached
        return cached

    def reload(self):
        """Xóa sạch cache - dùng khi người chơi vừa thêm/đổi file ảnh trong
        lúc game đang chạy, muốn áp dụng ngay không cần khởi động lại."""
        self._raw_cache.clear()
        self._render_cache.clear()
