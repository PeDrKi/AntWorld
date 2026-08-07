"""Kiểm tra tối giản: xem máy bạn có render 3D cơ bản bằng Ursina/Panda3D
được không, tách biệt hoàn toàn khỏi code mô phỏng kiến.

Chạy: python test_3d_basic.py

Nếu bạn thấy 1 khối lập phương đỏ + mặt sàn caro trắng-xám, xoay được bằng
cách giữ chuột phải kéo -> máy bạn render 3D bình thường, vấn đề nằm ở
code main.py (báo lại cho mình kèm nội dung màn hình console/terminal).

Nếu vẫn thấy màn hình trắng xóa ở đây -> vấn đề nằm ở driver đồ họa /
card màn hình trên máy bạn, không liên quan đến code (xem phần README
"Nếu vẫn trắng xóa" để biết cách xử lý).
"""
from ursina import *

app = Ursina(title="Test 3D co ban")
window.color = color.rgb(20, 20, 28)

Sky()  # nền bầu trời mặc định của Ursina, giúp dễ nhận biết render có hoạt động không

ground = Entity(model='plane', scale=32, texture='white_cube', texture_scale=(32, 32))
cube = Entity(model='cube', color=color.red, position=(0, 1, 0), scale=2)
sphere = Entity(model='sphere', color=color.azure, position=(4, 1, 0))

info_text = Text(
    text="Neu thay khoi do + qua cau xanh + san caro -> render OK.\n"
         "Giu CHUOT PHAI keo de xoay, lan chuot de zoom.",
    position=(-0.85, 0.45),
    background=True,
)

editor_cam = EditorCamera(rotation_smoothing=0)
editor_cam.position = (0, 0, 0)
editor_cam.rotation_x = 25
camera.z = -20
editor_cam.target_z = -20


def input(key):
    if key == 'escape':
        application.quit()


app.run()
