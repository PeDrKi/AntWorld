THƯ MỤC SPRITE TÙY CHỈNH - AntWorld
=====================================

Bỏ file PNG (nền trong suốt) vào ĐÚNG thư mục này, ĐÚNG TÊN dưới đây, để
game tự động dùng ảnh của bạn thay cho hình vẽ vector mặc định. Không cần
sửa code, không cần khởi động lại app - chỉ cần bỏ file vào rồi mở lại
ván chơi (hoặc bấm nút "Tải lại sprite" nếu có trong bản bạn đang dùng).

Có thể vẽ bằng công cụ đi kèm: AntWorld Pixel Studio (antworld_pixel_studio.html)
- các preset trong đó đã đặt ĐÚNG SẴN tên này, xuất PNG là dùng được luôn,
không cần đổi tên gì thêm.

TÊN FILE CHÍNH XÁC (không dấu, chữ thường, đúng đuôi .png):
-------------------------------------------------------------
  ant_worker_main.png          kiến tổ CHÍNH, lúc bình thường
  ant_worker_main_carry.png    kiến tổ CHÍNH, lúc đang tha mồi
  ant_worker_rival.png         kiến tổ ĐỐI THỦ, lúc bình thường
  ant_worker_rival_carry.png   kiến tổ ĐỐI THỦ, lúc đang tha mồi
  food.png                     1 miếng thức ăn (dùng CẢ trên mặt đất LẪN
                                trong đống thức ăn ở kho dưới hầm)
  rock.png                     1 ô đá (vật cản)
  water.png                    1 ô nước (dùng CẢ vật cản trên mặt đất LẪN
                                giọt nước trong bể trữ dưới hầm)
  egg.png                      1 quả trứng
  larva.png                    1 ấu trùng
  pupa.png                     1 kén nhộng
  queen.png                    kiến chúa
  enemy.png                    kẻ thù tự nhiên trên mặt đất
  nest_main.png                lỗ tổ CHÍNH trên mặt đất
  nest_rival.png               lỗ tổ ĐỐI THỦ trên mặt đất
  corpse.png                   1 "nắm xác" trong nghĩa địa

LƯU Ý VỀ ẢNH KẺ THÙ (enemy.png):
- Cũng vẽ ĐẦU QUAY SANG PHẢI và cũng được TỰ ĐỘNG XOAY theo hướng di
  chuyển thật, giống hệt ảnh kiến.

LƯU Ý VỀ ẢNH KIẾN (ant_worker_*.png):
- Vẽ con kiến với ĐẦU QUAY SANG PHẢI. Game sẽ TỰ ĐỘNG XOAY ảnh theo đúng
  hướng di chuyển thật của từng con - không cần vẽ nhiều hướng khác nhau.
- Huy hiệu vai trò (lính gác=vàng, chăm ấu trùng=hồng, chăm trứng+chúa=
  tím) vẫn được VẼ ĐÈ LÊN TRÊN ảnh của bạn tự động - không cần tự vẽ
  huy hiệu vào ảnh.

KHÔNG BẮT BUỘC PHẢI CÓ ĐỦ:
- Thiếu file nào, đối tượng đó vẫn hiển thị bằng hình vẽ vector mặc định
  như trước - không có gì bị lỗi/hỏng. Bạn có thể làm từng cái một.

Khuyến nghị kích thước vẽ: kiến/trứng/thức ăn/đá/nước ~16x16px, ấu trùng/
nhộng ~12x12px, kiến chúa ~24x24px - nhưng thực ra vẽ kích thước nào cũng
được, game sẽ tự co giãn cho vừa.
