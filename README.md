# Ant World 2D - Prototype (theo tầng)

Thế giới kiến (mặt đất + hầm ngầm với các phòng) giờ hiển thị dưới dạng
**các tầng 2D phẳng chồng lên nhau**, giống lát cắt ngang của 1 bể nuôi
kiến (formicarium) hoặc kiểu "Z-level" trong các game như Dwarf Fortress.
Bạn xem TỪNG TẦNG MỘT (nhìn thẳng từ trên xuống), và chuyển qua lại giữa
các tầng bằng cách giữ **Ctrl + lăn chuột**.

Dùng thư viện **Pygame** để dựng 2D (không còn Ursina/Panda3D).

## Dân số & sinh sản

- Mỗi đàn khởi tạo **20 con**, có thể **tự sinh sản lớn lên tới tối đa 1000
  con** (`NUM_ANTS`, `MAX_ANTS_PER_COLONY` trong `config.py`) - không còn bị
  giới hạn cứng ở đúng số khởi tạo như bản trước.
- Chúa **đẻ trứng** định kỳ (tốn thức ăn + nước từ kho) thay vì "sinh" kiến
  trực tiếp. Trứng lớn dần thành ấu trùng thật trong phòng ấu trùng, ăn
  đúng thức ăn nurse mang tới - đủ lớn mới "nở" thành 1 kiến thợ mới, và
  chỉ nở được nếu đàn CHƯA chạm trần 1000 con.

## Các phòng ngầm - thực hiện đúng chức năng

Tổ có **7 phòng chức năng**, kích thước (bán kính) khác nhau theo đúng vai
trò - kho/bể nước to nhất (chứa số lượng lớn), trứng/gác cửa/nghĩa địa nhỏ
hơn. **1 TẦNG CÓ THỂ CHỨA NHIỀU PHÒNG** (không phải 1 phòng chiếm nguyên cả
1 tầng như trước - quá phí diện tích): các phòng CÙNG CHỦ ĐỀ được gộp
chung 1 tầng, đặt lệch sang 2 bên (trái/phải) để không đè lên nhau:

- **Phòng gác cửa** (tầng 1, ngay dưới cửa hang): 1 nửa số "lính" (thợ lớn)
  đóng quân cố định ở đây, lượn quanh chờ lệnh. Hễ có kẻ thù xuất hiện đủ
  gần lỗ tổ, TOÀN BỘ lính gác lập tức lao lên mặt đất nghênh chiến; hết mối
  đe dọa thì tự rút quân về đóng lại.
- **Tầng 2 - Kho thức ăn + Bể trữ nước** (CHUNG 1 TẦNG, đặt 2 bên): kho
  hiển thị TRỰC TIẾP lượng thức ăn tồn dưới dạng đống viên màu sắc; bể nước
  hiển thị các giọt nước xanh lấp lánh - cả 2 đều theo đúng số lượng thật,
  kiến tha thức ăn/nước tự động xuống đúng phòng tương ứng dù cùng tầng.
- **Tầng 3 - Phòng trứng + Phòng ấu trùng** (CHUNG 1 TẦNG, đặt 2 bên): chúa
  đẻ trứng (tốn thức ăn+nước từ kho) - trứng ủ trong phòng trứng theo thời
  gian (không cần ăn), đủ lớn thì "chuyển" sang phòng ấu trùng ngay bên
  cạnh để lớn tiếp nhờ ăn thức ăn nurse mang tới - đủ lớn mới "nở" thành 1
  kiến thợ mới.
- **Phòng chúa** (tầng 4): có 1 con kiến chúa thật đứng giữa phòng, to hẳn
  so với thợ thường, hơi bồng bềnh nhẹ cho có sức sống.
- **Nghĩa địa** (tầng 5): mỗi kiến chết (già/đói/bị giết) để lại 1 "nắm
  xác" ở đây thay vì biến mất vô hình - xác cũ phân hủy dần theo thời gian.

Kiến khi đến phòng nào cũng **lượn lại trong phòng đó một lúc** (trạng
thái "dwell") trước khi rời đi, thay vì chỉ chạm tâm phòng rồi quay đầu -
để phòng ngầm luôn có "sự sống" thay vì chỉ thấy kiến đi trên đường nối.

## Xâm chiếm tổ đối thủ khi khan hiếm thức ăn

Khi kho thức ăn của 1 tổ CHỈ CÒN ÍT kéo dài đủ lâu (~5 giây ở tốc độ x1),
tổ đó tự động cử 1 đội (ưu tiên lính) hành quân sang **xâm chiếm tổ đối
thủ**:
- Đội quân hành quân thẳng tới lỗ tổ đối phương, giao chiến với lính phòng
  thủ của họ ngay tại đó (lính gác của bên bị xâm chiếm sẽ tự động lao lên
  nghênh chiến, có lợi thế "sân nhà").
- Nếu còn sống, chúng **cướp dần thức ăn từ kho đối thủ** rồi mang về nộp
  vào kho nhà mình như thức ăn bình thường.
- Sau 1 đợt xâm chiếm, tổ nghỉ 1 khoảng thời gian trước khi cân nhắc phát
  động đợt tiếp theo.

Đây là xung đột THẬT giữa 2 đàn (có thể gây chết chóc + mất tài nguyên cho
CẢ HAI bên), không chỉ cạnh tranh gián tiếp qua tìm thức ăn như trước.
HUD phía trên sẽ báo khi có tổ đang cử quân đi xâm chiếm hoặc đang bị xâm
chiếm.

## Cân bằng dân số - "phanh" sinh sản theo mật độ đàn

Trước đây, chúa chỉ cần đủ `EGG_FOOD_COST` là đẻ trứng tiếp - đàn cứ phình
to tới khi kho CẠN HẲN VỀ 0 mới dừng, lúc đó đã quá muộn: cả đàn rơi vào
chết đói hàng loạt CÙNG LÚC (đặc biệt nếu cả 2 tổ cùng cạn kho 1 lượt, các
đợt xâm chiếm qua lại còn làm nhau suy yếu nhanh hơn nữa) - kiểm thử mô
phỏng dài (30.000-40.000 tick) cho thấy tình trạng này có thể dẫn tới **cả
2 tổ tuyệt chủng hoàn toàn**.

Đã sửa bằng cách bắt buộc kho phải dư ra 1 khoản **dự trữ an toàn tỉ lệ
với sĩ số đàn HIỆN TẠI** (`EGG_MIN_STORAGE_BUFFER_PER_ANT` trong
`config.py`) trước khi chúa được đẻ trứng tiếp - đàn càng đông, ngưỡng an
toàn càng cao, tự nhiên hãm sinh sản lại TRƯỚC KHI kho cạn, thay vì chỉ
phản ứng SAU KHI đã cạn. Giá trị này đã được kiểm thử qua nhiều mô phỏng
dài (60.000-90.000 tick, nhiều seed ngẫu nhiên khác nhau): mức thấp
(1.5-5.0) vẫn dẫn tới sụp đổ tuyệt chủng ở ván dài; mức **8.0** loại bỏ
được kiểu sụp đổ đột ngột đó (kho không còn về 0 bất ngờ) - đổi lại, dân số
tăng chậm hơn hẳn và có thể giảm dần đều theo thời gian ở ván RẤT dài (chết
già tự nhiên nhanh hơn tốc độ sinh - không còn là sụp đổ thảm khốc, chỉ là
suy giảm từ từ).

Nếu muốn đàn lớn nhanh hơn (chấp nhận rủi ro sụp đổ cao hơn), giảm
`EGG_MIN_STORAGE_BUFFER_PER_ANT` xuống; muốn đàn ổn định lâu dài hơn nữa,
tăng lên. Cũng có thể giảm mức khốc liệt của xâm chiếm bằng cách tăng
`RAID_COOLDOWN_TICKS` hoặc giảm `RAID_ATTACKER_KILL_PROB`/
`RAID_DEFENDER_KILL_PROB`.

## Cài đặt (Windows)


```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy (từ mã nguồn - cần cài Python)

```powershell
python main.py
```

## Đóng gói thành app Windows độc lập (.exe)

Không cần mở PowerShell/gõ lệnh mỗi lần muốn chơi - có thể đóng gói thành
1 file `.exe` chạy như app Windows thật sự: có icon riêng, hiện đầy đủ nút
**thu nhỏ / phóng to / đóng** trên thanh tiêu đề (cửa sổ giờ có thể kéo
giãn/resize tự do), không hiện cửa sổ console đen, và **không cần cài
Python** trên máy chạy sau khi đã đóng gói xong.

**Bước 1 - Trên máy có Python (chỉ cần làm 1 lần):**
```powershell
pip install -r requirements.txt
pip install -r requirements-build.txt
pyinstaller AntWorld2D.spec --noconfirm
```
(hoặc chạy trực tiếp file `build_exe.bat` đi kèm - tự làm hết các bước trên)

**Bước 2:** file kết quả nằm ở `dist\AntWorld2D\AntWorld2D.exe`. Có thể
copy CẢ THƯ MỤC `dist\AntWorld2D\` sang bất kỳ máy Windows nào khác để
chạy - không cần cài Python trên máy đó. Có thể tạo shortcut ra Desktop từ
file `.exe` này như bất kỳ app Windows nào khác.

## Điều khiển

- **Giữ CTRL + LĂN CHUỘT**: chuyển qua lại giữa các tầng (lên/xuống)
- **Phím mũi tên Lên / Xuống**: cũng chuyển tầng (thay thế Ctrl+lăn chuột)
- **Lăn chuột (không giữ Ctrl)**: zoom vào/ra tầng đang xem
- **Giữ CHUỘT PHẢI + di chuột**: kéo (pan) để di chuyển góc nhìn ngang/dọc
- **Nút "Tang ^" / "Tang v"** trên thanh công cụ: chuyển tầng bằng chuột
  nếu không có bánh xe lăn
- **Kéo giãn/phóng to/thu nhỏ cửa sổ**: thoải mái như mọi app Windows khác
  - giao diện (thanh công cụ, HUD, khung nhìn) tự động co giãn theo
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
- **Đường mùi (pheromone)**: vệt xanh lam mờ trên mặt đất là đường mùi kiến
  để lại khi tha đồ về tổ (đậm/nhạt theo đúng nồng độ mùi thật - nơi nhiều
  kiến qua lại sẽ đậm hơn); vệt đỏ là mùi báo động để lại quanh kẻ thù.
- **Kiến đang làm việc**: kiến đang lượn trong 1 phòng ngầm (thay vì chỉ đi
  qua hành lang) có 1 vòng sáng vàng nhấp nháy quanh thân - phân biệt rõ
  "đang làm việc tại chỗ" với "đang di chuyển".

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

Đã tách nhỏ từ 1 file `main.py` gộp hết (từng phình to tới ~900 dòng) thành
các module riêng theo đúng vai trò, dễ đọc/bảo trì hơn:

```
--- Logic mô phỏng (không đụng tới pygame) ---
config.py             - hằng số cấu hình toàn bộ game (tầng, tốc độ, chi
                        phí sinh sản, xác suất chiến đấu...)
world.py              - SurfaceWorld (mặt đất) + UndergroundWorld (hầm
                        ngầm - mỗi phòng gắn với 1 tầng rời rạc)
ants.py               - AntColony: đàn kiến dạng mảng NumPy (di chuyển,
                        vòng đời, trứng/ấu trùng, lính gác, xâm chiếm...)
enemy.py              - kẻ thù tự nhiên trên mặt đất

--- Lớp hiển thị/điều khiển (pygame) ---
camera.py             - Camera2D: pan/zoom màn hình <-> tọa độ lưới
ui_widgets.py         - Button: nút bấm UI đơn giản
game_state.py         - GameState: gom TOÀN BỘ dữ liệu + logic điều khiển
                        (world, colony, camera, tool, toggle...) vào 1 chỗ
render_surface.py     - vẽ tầng mặt đất + draw_ants() (dùng chung mọi tầng)
render_underground.py - vẽ các tầng ngầm (từng phòng chức năng riêng biệt)
hud.py                - biểu đồ dân số, bảng thống kê, thanh công cụ
main.py               - CHỈ còn ~160 dòng: khởi tạo pygame, dựng
                        GameState, vòng lặp sự kiện gọi vào các module trên

--- Đóng gói thành app Windows (.exe) ---
assets/icon.png, icon.ico - icon app/taskbar
AntWorld2D.spec       - cấu hình PyInstaller (icon, ẩn console, gói assets)
build_exe.bat         - script tự động chạy PyInstaller trên Windows
requirements-build.txt - thư viện CHỈ cần khi đóng gói (PyInstaller)
```

Nguyên tắc tách: các module render/hud nhận `state` (đối tượng GameState)
làm tham số đầu tiên để đọc dữ liệu cần vẽ, thay vì dùng closures như bản
main.py cũ - nhờ vậy mỗi hàm có thể đọc/test độc lập mà không cần dựng cả
vòng lặp game.

## Hướng mở rộng tiếp theo (gợi ý)

- Vẽ mini-map dọc bên cạnh màn hình thể hiện toàn bộ các tầng cùng lúc
  (như thanh "current level" của Dwarf Fortress), để dễ định vị hơn là
  chỉ đọc số tầng ở góc màn hình.
- Hiệu ứng chuyển tầng mượt (fade) thay vì đổi tức thời.
- Cho phép đào nhiều phòng trên CÙNG 1 tầng (hiện tại mỗi phòng tự đào
  chiếm hẳn 1 tầng riêng để đơn giản hóa).
- Lưu/tải trạng thái thế giới bằng SQLite.
