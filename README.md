# Ant World 3D - Prototype

Toàn bộ thế giới kiến (mặt đất + hầm ngầm với các phòng) hiển thị như
**1 khối hộp trong suốt duy nhất** (kiểu bể nuôi kiến bằng kính), bạn xoay
và zoom tự do bằng chuột để nhìn từ mọi góc, kể cả nhìn xuyên từ trên
xuống các phòng sâu dưới đất.

Dùng engine **Ursina** (xây trên nền **Panda3D**) để dựng 3D.
## Chạy

```powershell
python main.py
```
## Điều khiển

- **Giữ CHUỘT PHẢI + di chuột**: xoay camera quanh khối thế giới
- **Lăn chuột**: zoom vào/ra
- **Giữ CHUỘT PHẢI + W/A/S/D**: bay ngang trong lúc đang xoay
- **Phím G**: bật/tắt độ trong suốt của mặt đất, để nhìn xuyên xuống hầm
  dễ hơn mà không cần xoay góc nhìn từ dưới lên
- **Esc**: thoát

## Cách đọc mô phỏng

- Khối kính mờ bao quanh toàn bộ thế giới, mặt đất màu nâu nhạt nằm ở giữa.
- Kiến màu đen/xám = đang tìm ăn hoặc di chuyển không mang gì; màu cam/vàng
  = đang tha thức ăn.
- Dưới mặt đất là 3 quả cầu màu: **Kho thức ăn**, **Ấu trùng**, **Phòng
  chúa** - nối với giếng (hình trụ đen ngay dưới lỗ tổ) bằng các đường hầm.
  Kiến tha đồ xuống giếng sẽ tự bay thẳng theo đường 3D tới kho, sau đó một
  phần thành "nurse" mang tiếp sang phòng ấu trùng.

## ⚠️ Lưu ý quan trọng về hiệu năng

Bản demo này được viết và kiểm thử trong môi trường không có card đồ họa
thật (chỉ render bằng phần mềm), nên **không thể đo FPS thực tế ở đây**.
Phần logic mô phỏng (NumPy) đã được xác nhận chạy rất nhẹ (~100+ lần/giây
ngay cả khi phải cập nhật vị trí 600 con kiến mỗi khung hình), nhưng tốc độ
hiển thị (FPS) thực sự phụ thuộc vào GPU trên máy bạn.

Khi chạy trên Windows, nếu FPS thấp hơn mong đợi, thử theo thứ tự:

1. **Giảm số kiến** trong `config.py` (`NUM_ANTS`), ví dụ xuống 300.
2. Trong `main.py`, tăng `FOOD_SAMPLE_STEP` (hiện là 2) để giảm số ô thức
   ăn được vẽ.
3. Đóng bớt ứng dụng khác đang dùng GPU.

## Cấu trúc file

```
config.py    - hằng số: quy mô, tốc độ, vị trí phòng (x, y, z)
world.py     - SurfaceWorld (mặt đất) và UndergroundWorld (hầm ngầm, tọa độ 3D)
ants.py      - AntColony: đàn kiến dạng mảng NumPy, di chuyển 3D thật (x,y,z)
main.py      - dựng cảnh Ursina/Panda3D, camera xoay quỹ đạo, vòng lặp update()
```