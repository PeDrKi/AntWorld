# Ant World 2D - Prototype (theo tầng)

Thế giới kiến (mặt đất + hầm ngầm với các phòng) giờ hiển thị dưới dạng
**các tầng 2D phẳng chồng lên nhau**, giống lát cắt ngang của 1 bể nuôi
kiến (formicarium) hoặc kiểu "Z-level" trong các game như Dwarf Fortress.
Bạn xem TỪNG TẦNG MỘT (nhìn thẳng từ trên xuống), và chuyển qua lại giữa
các tầng bằng cách giữ **Ctrl + lăn chuột**.

Dùng thư viện **Pygame** để dựng 2D (không còn Ursina/Panda3D).

## Dân số & sinh sản

- Mỗi đàn khởi tạo **10 con**, có thể **tự sinh sản lớn lên tới tối đa 200
  con** (`NUM_ANTS`, `MAX_ANTS_PER_COLONY` trong `config.py`) - không còn bị
  giới hạn cứng ở đúng số khởi tạo như bản trước.
- Chúa **đẻ trứng** định kỳ (tốn thức ăn + nước từ kho) thay vì "sinh" kiến
  trực tiếp. Trứng lớn dần thành ấu trùng thật trong phòng ấu trùng, ăn
  đúng thức ăn nurse mang tới - đủ lớn mới "nở" thành 1 kiến thợ mới, và
  chỉ nở được nếu đàn CHƯA chạm trần 200 con.

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

**Bước 1 - Trên máy có Python (chỉ cần làm 1 lần), chạy TỪ THƯ MỤC GỐC dự án:**
```powershell
pip install -r requirements.txt
pip install -r requirements-build.txt
pyinstaller packaging\AntWorld2D.spec --noconfirm
```
(hoặc double-click trực tiếp file `packaging\build_exe.bat` đi kèm - tự
chuyển về thư mục gốc dự án và làm hết các bước trên, có thể chạy từ bất
kỳ đâu)

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

- **"Dat thuc an" / "Tha ke thu" / "Dat da" / "Dat nuoc"**: CHỈ dùng được
  khi đang xem **Tầng 0 (Mặt đất)** vì đây là thao tác đặt trên mặt đất
  nhìn từ trên xuống. Nếu chọn công cụ này ở tầng khác, dòng gợi ý dưới
  màn hình sẽ nhắc bạn quay về Tầng 0.
- **"Xoa"**: dùng được ở MỌI tầng - xóa đúng nội dung của tầng đang xem
  (mặt đất: thức ăn/đá/nước/kiến trên mặt đất; tầng ngầm: phòng tự đào ở
  đúng tầng đó + kiến đang ở tầng đó).
- **"Theo doi"**: bấm rồi click vào 1 con kiến để camera tự bám theo nó
  (kể cả khi nó đổi tầng); di chuyển/zoom camera thủ công sẽ tự hủy theo dõi.
- **"Sinh me cung (xoa da/nuoc cu)"**: xóa sạch đá/nước/thức ăn hiện có
  trên bản đồ, rải 1 **mê cung chuẩn** (perfect maze - mọi ô liên thông,
  đúng 1 đường duy nhất giữa 2 ô bất kỳ, neo theo đúng vị trí tổ để tổ
  không bao giờ bị "nhốt" trong tường) cùng vài cụm thức ăn NHỎ rải rác ở
  các ngóc ngách xa nhau trong mê cung, để xem đàn kiến THẬT tự tìm đường
  xuyên mê cung bằng đúng thuật toán any-angle A* trên visibility graph
  (`pathfinding.py`) - xem `maze_generator.py`. Cấu hình mặc định (hành
  lang 2 ô, tường 1 ô, ~170 phòng) build đồ thị tìm đường trong khoảng
  1-2.5 giây SAU khi sinh mê cung (chỉ 1 lần, không lặp lại mỗi tick) -
  `pathfinding.py` gộp các ô vật cản liền kề thành hình chữ nhật lớn và
  dùng heuristic ALT (landmarks) thay vì đường chim bay thuần túy để giữ
  mỗi lần tìm đường sau đó chỉ còn vài mili-giây dù mê cung dày đặc.
  **Lưu ý**: thao tác này xóa cả nước hiện có và nước KHÔNG tự tái sinh
  (khác thức ăn), nên tổ sẽ mất nguồn thu nước cho tới khi bạn tự đặt lại
  bằng "Dat nuoc".
- **"Tam dung" / "Toc do xN"**: điều khiển thời gian mô phỏng.
- **"Luu van choi" / "Tai van choi"** (hoặc Ctrl+S / Ctrl+L): lưu/tải lại ván chơi.
- **"Tai sinh thuc an: BAT/TAT"**: bật/tắt việc thức ăn mới tự xuất hiện
  ngẫu nhiên theo chu kỳ.
- **"Luoi o vuong: BAT/TAT"**: bật/tắt lưới ô vuông tham chiếu.
- **"Bieu do: HIEN/AN"**: bật/tắt biểu đồ dân số theo thời gian (góc dưới-trái).
- **"Ke thu tu nhien: BAT/TAT"**: bật/tắt việc kẻ thù tự nhiên xuất hiện
  ngẫu nhiên trên mặt đất.
- **"Tang ^" / "Tang v"**: chuyển tầng bằng nút (tương đương lăn chuột/Ctrl+lăn chuột).

## Cấu trúc dự án

Dự án dùng **"src layout"** tiêu chuẩn của Python: code game nằm gọn
trong 1 package (`src/antworld/`), tách biệt với công cụ độc lập
(`tools/`), asset (`assets/`), test (`tests/`) và cấu hình đóng gói
(`packaging/`) - mỗi thứ 1 thư mục riêng thay vì gộp chung ~25 file ở
thư mục gốc như bản trước:

```
AntWorld2D/
├── main.py                 - launcher mỏng ở gốc: "python main.py" vẫn
│                             chạy game như cũ, chỉ trỏ vào src/antworld/
├── pyproject.toml          - khai báo package (cho phép "pip install -e ."
│                             nếu muốn import antworld từ nơi khác)
├── requirements.txt / requirements-build.txt
├── run_tests.py            - chạy toàn bộ test bằng 1 lệnh
├── conftest.py             - giúp pytest tìm thấy src/ và tools/
│
├── src/antworld/           - PACKAGE CHÍNH của game (mọi import nội bộ
│   │                         dùng import tương đối, vd "from . import config")
│   ├── __init__.py
│   ├── __main__.py         - khởi tạo pygame, dựng GameState, vòng lặp
│   │                         sự kiện gọi vào các module dưới (từng là
│   │                         main.py ở bản cũ)
│   │
│   │   --- Logic mô phỏng (không đụng tới pygame) ---
│   ├── config.py            - hằng số cấu hình toàn bộ game (tầng, tốc
│   │                         độ, chi phí sinh sản, xác suất chiến đấu...)
│   ├── world.py              - SurfaceWorld (mặt đất) + UndergroundWorld
│   │                         (hầm ngầm - mỗi phòng gắn 1 tầng rời rạc)
│   ├── ants.py                - AntColony: đàn kiến dạng mảng NumPy (di
│   │                         chuyển, vòng đời, trứng/ấu trùng, lính gác...)
│   ├── pathfinding.py          - VisibilityPathfinder: tìm đường any-angle
│   │                         (ngắn nhất thật, không "răng cưa") cho kiến
│   │                         trên mặt đất - A* trên visibility graph dựng
│   │                         từ góc lồi vật cản, cache theo terrain_version
│   │                         để nhiều kiến dùng chung 1 lần dựng đồ thị
│   ├── maze_generator.py       - rải 1 mê cung (tường đá dài ngoằn ngoèo)
│   │                         trực tiếp vào bản đồ đang chơi (nút "Sinh me
│   │                         cung" trong toolbar) để xem đàn kiến thật tự
│   │                         tìm đường xuyên mê cung bằng pathfinding.py
│   ├── enemy.py                - kẻ thù tự nhiên trên mặt đất
│   ├── invasion.py              - đàn kiến xâm lược đột kích theo chu kỳ
│   │                         (cướp thức ăn/ấu trùng, leo thang độ khó)
│   │
│   │   --- Lớp hiển thị/điều khiển (pygame) ---
│   ├── camera.py                - Camera2D: pan/zoom màn hình <-> lưới
│   ├── ui_widgets.py             - Button: nút bấm UI đơn giản
│   ├── game_state.py              - GameState: gom TOÀN BỘ dữ liệu + logic
│   │                         điều khiển (world, colony, camera, tool...)
│   ├── render_surface.py           - vẽ tầng mặt đất + draw_ants() (dùng
│   │                         chung mọi tầng)
│   ├── render_underground.py        - vẽ các tầng ngầm (từng phòng riêng)
│   ├── hud.py                        - biểu đồ dân số, bảng thống kê,
│   │                         thanh công cụ
│   ├── fonts.py                      - nạp font TrueType riêng (từ
│   │                         assets/fonts/*.ttf ở gốc dự án) thay vì
│   │                         SysFont, đảm bảo chữ tiếng Việt hiển thị
│   │                         đúng kể cả bản .exe đã đóng gói
│   ├── sprite_manager.py              - nạp sprite PNG người chơi tự thêm
│   └── sprite_data.py                  - dữ liệu bảng màu + sprite mẫu,
│                             dùng chung với tools/pixel_editor.py
│
├── tools/                  - công cụ ĐỘC LẬP với game, không nằm trong
│   │                         package antworld (nhưng dùng chung fonts.py
│   │                         + sprite_data.py của package đó)
│   ├── pixel_editor.py      - công cụ vẽ pixel art cho sprite (Pygame):
│   │                         bút/tẩy (3 cỡ), đổ màu, hút màu, đường
│   │                         thẳng, hình chữ nhật (viền/đặc), đối xứng
│   │                         ngang+dọc, thanh trượt R/G/B, màu vừa dùng,
│   │                         xem hoạt ảnh (tự ghép cặp sprite mang đồ)
│   └── pixel_studio_web/
│       └── antworld_pixel_studio.html  - bản web (HTML/JS thuần, không
│                             cần Python) của cùng công cụ trên
│
├── assets/                 - dùng chung cho game + 2 công cụ trên
│   ├── fonts/               - font TrueType đóng gói sẵn (SIL OFL 1.1)
│   ├── sprites/              - PNG sprite (nền trong suốt)
│   ├── icon.ico / icon.png    - icon app/taskbar
│
├── tests/                  - test tự động (unittest), xem mục riêng bên
│   │                         dưới
│   └── test_*.py
│
└── packaging/               - mọi thứ liên quan đóng gói .exe, tách khỏi
    │                         code nguồn cho gọn
    ├── AntWorld2D.spec        - cấu hình PyInstaller (icon, ẩn console,
    │                         gói assets/ - đường dẫn tự quy về thư mục
    │                         gốc dự án dù spec nằm trong packaging/)
    └── build_exe.bat            - script chạy PyInstaller trên Windows,
                                tự cd về thư mục gốc trước khi build
```

Nguyên tắc tách module: các hàm render/hud nhận `state` (đối tượng
GameState) làm tham số đầu tiên để đọc dữ liệu cần vẽ, thay vì dùng
closures như bản gộp cũ - nhờ vậy mỗi hàm có thể đọc/test độc lập mà
không cần dựng cả vòng lặp game. Việc chuyển sang src layout ở trên chỉ
đổi VỊ TRÍ file và cách import nội bộ (`import config as cfg` ->
`from . import config as cfg`); không đổi hành vi hay tên biến/hàm nào -
`python main.py`, `python run_tests.py`, và cách vẽ sprite trong
`tools/pixel_editor.py` vẫn hệt như trước.

## Hướng mở rộng tiếp theo (gợi ý)

- Vẽ mini-map dọc bên cạnh màn hình thể hiện toàn bộ các tầng cùng lúc
  (như thanh "current level" của Dwarf Fortress), để dễ định vị hơn là
  chỉ đọc số tầng ở góc màn hình.
- Hiệu ứng chuyển tầng mượt (fade) thay vì đổi tức thời.
- Cho phép đào nhiều phòng trên CÙNG 1 tầng (hiện tại mỗi phòng tự đào
  chiếm hẳn 1 tầng riêng để đơn giản hóa).
- Lưu/tải trạng thái thế giới bằng SQLite.

## Test tự động

Thư mục `tests/` chứa bộ test tự động (dùng `unittest` có sẵn trong
Python, không cần cài thêm gì). Chạy toàn bộ bằng 1 trong 2 cách:

```
python run_tests.py
# hoặc (pytest, nếu đã cài):
python -m pytest tests -v
# hoặc (unittest thuần, cần thêm -t . để nhận đúng package tests/ nằm
# trong project dùng src layout - thiếu -t . sẽ báo lỗi "No module named
# antworld" vì khi đó tests/ bị coi là top-level thay vì gói con):
python -m unittest discover -s tests -t . -v
```

Nội dung bao trùm:

- `test_config_consistency.py` - kiểm tra `config.py` tự nhất quán, và
  **README này không lệch số liệu thật trong config.py** (đúng loại lỗi
  đã từng xảy ra: README ghi 20/1000 con trong khi code là 10/200 con) -
  nếu sau này đổi `NUM_ANTS`/`MAX_ANTS_PER_COLONY` mà quên lướt lại
  README, test này sẽ báo đỏ ngay.
- `test_world.py` - `SurfaceWorld`/`UndergroundWorld` sinh ra hợp lệ,
  không NaN/giá trị âm phi lý.
- `test_ants.py` - chạy mô phỏng đàn kiến ~1500 tick, kiểm tra không
  NaN/inf trong vị trí, dân số không bao giờ vượt trần
  `MAX_ANTS_PER_COLONY`. Đây là loại lỗi khó bắt bằng mắt vì thường chỉ
  lộ ra sau rất nhiều tick.
- `test_pathfinding.py` - `VisibilityPathfinder` (any-angle A* trên
  visibility graph, xem `pathfinding.py`): line-of-sight qua khe nối giữa
  2 ô vật cản liền kề/sát biên bản đồ, điểm kẹp chéo không bị cắt xuyên,
  và kiểm chứng thống kê trên nhiều bản đồ ngẫu nhiên rằng KHÔNG đường đi
  nào thực sự xuyên vật cản - đây chính là 2 lỗi hình học tinh vi từng bị
  phát hiện qua kiểm thử thủ công (không phải bộ test tự động) trước khi
  file này tồn tại.
- `test_invasion.py` - `InvasionManager` (đàn kiến xâm lược đột kích theo
  chu kỳ, xem `invasion.py`).
- `test_fonts.py` - file font `.ttf` tồn tại và load được, chữ tiếng
  Việt có dấu render không lỗi (phòng lỗi font tái diễn).
- `test_pixel_editor.py` - logic vẽ/đối xứng ngang-dọc/đổ màu/undo-redo
  trong `pixel_editor.py`.
- `test_game_state.py` - smoke test tích hợp: dựng `GameState` thật
  (tải sprite/font/world/2 đàn) rồi chạy vài trăm tick, đảm bảo các
  module ghép lại với nhau không crash.

Bộ test tự set `SDL_VIDEODRIVER=dummy` (qua `tests/__init__.py`) nên
chạy được cả trên máy không có màn hình (SSH, CI...), không cần mở cửa
sổ game thật.

## Hành vi kiến "thật" hơn - chuyển động + animation

Trước đây kiến bẻ hướng TỨC THỜI mỗi khi đổi waypoint (trông "dán mắt"
máy móc), chân/râu (khi vẽ vector) chạy animation VÔ ĐIỀU KIỆN theo thời
gian dù kiến có đang đứng yên hay không, và ảnh sprite tùy chỉnh (nếu có)
chỉ là 1 khung tĩnh xoay cứng theo hướng. Đã cải thiện cả 3 mặt:

- **Xoay đầu mượt dần** (`MAX_TURN_RATE_PER_TICK` trong `config.py`):
  kiến giờ xoay thân DẦN về hướng mới (~0.15s để quay 180° ở 60 FPS x1)
  thay vì bật thẳng góc mới ngay lập tức.
- **Dừng dò đường bằng râu** (`ANTENNA_PAUSE_*`): kiến đang tự do khám
  phá/mang mồi về thỉnh thoảng khựng lại vài trăm mili-giây, lắc đầu nhẹ
  ngẫu nhiên rồi đi tiếp - giống hành vi thật, KHÔNG áp dụng cho lính gác
  lao lên nghênh chiến hay thợ khiêng mồi lớn (vẫn phản ứng ngay).
- **Pha bước chân/animation gắn với quãng đường di chuyển THẬT**
  (`AntColony.anim_phase`/`InvasionManager.anim_phase`, xem
  `ANIM_PHASE_DISTANCE_SCALE`): kiến đứng yên thì chân/khung sprite cũng
  đứng yên; kiến di chuyển càng nhanh (vd. lính gác lao lên) thì bước
  chân càng nhanh tương ứng - không còn "chân lướt như trượt băng" hay
  "đi tại chỗ" khi đứng im.
- **Chân có khớp gối** (2 đoạn: đùi + ống chân, chỉ áp dụng khi vẽ vector
  - tức lúc KHÔNG có ảnh sprite tùy chỉnh) thay vì 1 đường thẳng cứng, và
  **râu ngoe nguẩy độc lập** với bước chân (luôn động đậy kể cả lúc đứng
  yên hẳn).
- **Ảnh sprite hỗ trợ bộ khung đi bộ (walk cycle) tùy chọn**: đặt thêm
  các file `..._walk0.png .. _walk3.png` (xem quy ước đầy đủ trong
  docstring `sprite_manager.py`) để kiến có dáng đi bộ thật thay vì 1
  khung tĩnh xoay cứng - game tự chọn đúng khung theo pha bước chân thật
  ở trên. Đã có sẵn bộ khung này cho `ant_worker_main(_carry)` và
  `ant_invader(_carry)` trong `assets/sprites/`.

## Hành động/thao tác thực tế hơn (ngoài chuyển động)

- **Lính gác chạm râu kiểm tra đồng đội ra vào cửa tổ** (nestmate
  recognition - `GUARD_INSPECT_*`, `_update_guard_inspections()`): lính
  đang trực ngẫu nhiên "chạm râu" bất kỳ ai đi ngang trạm gác (quanh giếng
  lên mặt đất, đúng tầng phòng gác) - hiệu ứng đường nối màu xanh nhạt,
  phân biệt với mớm mồi (vàng). Thuần túy hình ảnh, không chặn đường ai.
- **Cắn giữ mồi trước khi tha đi** (`BITE_GRIP_PAUSE_TICKS`): vừa nhặt
  được mồi, kiến khựng lại một chút (mượn cơ chế "dừng dò đường" có sẵn)
  kèm animation hàm (mandible) mở-khép, thay vì mồi tự dính lên lưng ngay.
  Cùng animation áp dụng khi đang gồng giữ mồi lớn chờ đồng đội
  (`STATE_HAUL_GRIP`).
- **Chăm sóc lẫn nhau thật sự** (`GROOM_*`, `_update_grooming()`): ngoài
  hiệu ứng lấp lánh ngẫu nhiên có sẵn giữa các kiến rảnh rỗi đứng gần
  nhau, giờ có thêm cơ chế TỪNG CẶP cụ thể thực sự ghép đôi chăm sóc nhau
  trong ~0.8s (có thời lượng, có thời gian nghỉ giữa các lần), vẽ nổi bật
  hơn hẳn (đường nối xanh lá nhạt).
- **Hấp hối trước khi chết** (`DYING_DURATION_TICKS`): kiến chết vì
  già/đói/khát không biến mất/thành xác NGAY LẬP TỨC nữa - đứng khựng lại
  run rẩy tại chỗ ~0.67s, thân xám dần, rồi mới thực sự chết và đăng ký
  xác. Chết vì GIAO CHIẾN vẫn tức thời như cũ (đúng thực tế - bị cắn chết
  là chết ngay).

