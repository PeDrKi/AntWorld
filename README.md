# Ant World 2D - Prototype (theo tầng)

Thế giới kiến (mặt đất + hầm ngầm với các phòng) giờ hiển thị dưới dạng
**các tầng 2D phẳng chồng lên nhau**, giống lát cắt ngang của 1 bể nuôi
kiến (formicarium) hoặc kiểu "Z-level" trong các game như Dwarf Fortress.
Bạn xem TỪNG TẦNG MỘT (nhìn thẳng từ trên xuống), và chuyển qua lại giữa
các tầng bằng cách giữ **Ctrl + lăn chuột**.

Dùng thư viện **Pygame** để dựng 2D (không còn Ursina/Panda3D).

## Cài đặt (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy

```powershell
python main.py
```

## Điều khiển

- **Giữ CTRL + LĂN CHUỘT**: chuyển qua lại giữa các tầng (lên/xuống)
- **Phím mũi tên Lên / Xuống**: cũng chuyển tầng (thay thế Ctrl+lăn chuột)
- **Lăn chuột (không giữ Ctrl)**: zoom vào/ra tầng đang xem
- **Giữ CHUỘT PHẢI + di chuột**: kéo (pan) để di chuyển góc nhìn ngang/dọc
- **Nút "Tang ^" / "Tang v"** trên thanh công cụ: chuyển tầng bằng chuột
  nếu không có bánh xe lăn
- **Esc**: thoát

## Cấu trúc các tầng

- **Tầng 0 - Mặt đất**: thức ăn, đá, nước, lỗ tổ 2 bên, kiến đang tìm ăn
  hoặc tha đồ về tổ, kẻ thù tự nhiên.
- **Tầng 1 - Kho thức ăn**, **Tầng 2 - Ấu trùng**, **Tầng 3 - Phòng chúa**:
  mỗi phòng nằm trên đúng 1 tầng riêng. "Giếng" (thang máy) hiện tại vị trí
  lỗ tổ trên mọi tầng có phòng, nối tới phòng bằng 1 đoạn hành lang ngắn
  trong CÙNG tầng.
- **Tầng 4 trở đi**: các phòng do người chơi tự đào bằng công cụ "Dao
  phong" - mỗi phòng đào thêm chiếm 1 tầng mới, sâu hơn tầng trước.

Kiến "đi thang máy" tức thời giữa các tầng khi lên/xuống giếng (không còn
bay theo đường chéo 3D xuyên qua nhiều tầng cùng lúc như bản 3D cũ) - vì
vậy tại 1 thời điểm, 1 con kiến CHỈ hiện diện trên ĐÚNG 1 tầng.

## Cách đọc mô phỏng

- Kiến màu đen/xám = đang tìm ăn hoặc di chuyển không mang gì; màu cam/vàng
  = đang tha thức ăn.
- Tổ đối thủ dùng tông màu đỏ/nâu để phân biệt với tổ chính (đen/cam).
- Nhãn tầng hiện tại luôn hiện ở góc trên phải màn hình.

## Thanh công cụ

- **"Dat thuc an" / "Tha ke thu" / "Dao phong" / "Dat da" / "Dat nuoc"**:
  CHỈ dùng được khi đang xem **Tầng 0 (Mặt đất)** vì đây là thao tác đặt
  trên mặt đất nhìn từ trên xuống. Nếu chọn công cụ này ở tầng khác, dòng
  gợi ý dưới màn hình sẽ nhắc bạn quay về Tầng 0.
- **"Xoa"**: dùng được ở MỌI tầng - xóa đúng nội dung của tầng đang xem
  (mặt đất: thức ăn/đá/nước/kiến trên mặt đất; tầng ngầm: phòng tự đào ở
  đúng tầng đó + kiến đang ở tầng đó).
- **"Tam dung" / "Toc do xN"**: điều khiển thời gian mô phỏng.
- **"Tai sinh thuc an: BAT/TAT"**: bật/tắt việc thức ăn mới tự xuất hiện
  ngẫu nhiên theo chu kỳ.
- **"Luoi o vuong"**: bật/tắt lưới ô vuông tham chiếu.
- **"Bieu do"**: bật/tắt biểu đồ dân số theo thời gian (góc trên phải).

## Cấu trúc file

```
config.py    - hằng số: quy mô, tốc độ, số tầng (LAYER_SURFACE_DEPTH,
               DEPTH_STORAGE, DEPTH_NURSERY, DEPTH_QUEEN, ...)
world.py     - SurfaceWorld (mặt đất, không đổi) và UndergroundWorld
               (hầm ngầm - giờ mỗi phòng gắn với 1 tầng rời rạc thay vì
               tọa độ z liên tục)
ants.py      - AntColony: đàn kiến dạng mảng NumPy, di chuyển 2D trong
               PHẠM VI 1 TẦNG; đổi tầng tức thời tại các điểm chuyển
               trạng thái (giống bước vào/ra thang máy)
enemy.py     - kẻ thù tự nhiên trên mặt đất (không đổi)
main.py      - dựng cảnh bằng Pygame: camera 2D (pan/zoom), vẽ từng tầng,
               thanh công cụ, biểu đồ, vòng lặp update()
```

## Hướng mở rộng tiếp theo (gợi ý)

- Vẽ mini-map dọc bên cạnh màn hình thể hiện toàn bộ các tầng cùng lúc
  (như thanh "current level" của Dwarf Fortress), để dễ định vị hơn là
  chỉ đọc số tầng ở góc màn hình.
- Hiệu ứng chuyển tầng mượt (fade) thay vì đổi tức thời.
- Cho phép đào nhiều phòng trên CÙNG 1 tầng (hiện tại mỗi phòng tự đào
  chiếm hẳn 1 tầng riêng để đơn giản hóa).
- Lưu/tải trạng thái thế giới bằng SQLite.
