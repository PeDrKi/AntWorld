"""HUD: biểu đồ dân số, bảng thống kê, thanh công cụ - đều là các "cửa sổ"
(Panel) NỔI TRÊN màn hình mô phỏng: KÉO DI CHUYỂN được và THU GỌN được, để
người chơi tự sắp xếp sao cho không bị che mất khung nhìn đàn kiến (xem
ui_widgets.Panel).

Thanh công cụ trình bày dạng SIDEBAR (bảng cạnh) - các nút xếp DỌC thành 1
cột duy nhất, chia theo từng NHÓM có nhãn tiêu đề riêng, thay vì xếp thành
2 hàng ngang như bản trước - dễ đọc/dễ quét mắt hơn khi số lượng nút nhiều.

Bảng thống kê hiển thị ĐẦY ĐỦ số liệu cho tổ (dân số/quân số, tài nguyên,
tổn thất, phân bố chức năng)."""
import pygame

from . import config as cfg
from .ui_widgets import Button, Panel, draw_pixel_rect
from .render_underground import layer_name
from .fonts import render_cached, get_flat_alpha_surface

# --- Bảng màu dùng chung cho bảng thống kê (nhãn mờ, giá trị sáng, mỗi
# chủ đề 1 màu để mắt bắt được ngay không cần đọc kỹ từng chữ) ---
COL_LABEL = (145, 148, 158)      # nhãn (chữ nhỏ, mờ hơn giá trị)
COL_MAIN = (110, 190, 255)       # gắn với TỔ CHÍNH (khớp tông cam/đen của
                                  # kiến tổ chính trong render_surface)
COL_INVASION = (255, 140, 100)   # gắn với ĐÀN KIẾN NGOẠI LAI
COL_VALUE = (232, 232, 235)      # giá trị số liệu trung tính
COL_GOOD = (120, 230, 140)       # số liệu "tốt" (sinh, đủ tài nguyên...)
COL_BAD = (255, 110, 100)        # số liệu "xấu" (chết, mất mát...)
COL_FOOD = (225, 190, 110)       # màu kho thức ăn
COL_WATER = (110, 190, 255)      # màu nước
COL_WARN_BG = (70, 20, 20, 130)  # nền mờ phía sau dòng cảnh báo
COL_FOLLOW_BG = (18, 55, 28, 140)  # nền mờ phía sau dòng "đang theo dõi"
COL_SECTION = (150, 155, 165)    # nhãn tiêu đề nhóm trong sidebar công cụ


def build_toolbar(state):
    """Tạo 3 Panel nổi: SIDEBAR công cụ (dọc, bên phải), bảng thống kê
    (trên-trái), biểu đồ (dưới-trái). Nếu state đã có sẵn panel từ trước
    (vd đang resize cửa sổ), GIỮ NGUYÊN vị trí/trạng thái thu gọn người
    chơi đã tự sắp xếp thay vì đặt lại về mặc định."""
    old_positions = {}
    for key in ("toolbar_panel", "stats_panel", "graph_panel", "layer_map_panel", "tab_panel", "maze_panel",
                "ant_panel", "founding_panel", "event_log_panel"):
        p = getattr(state, key, None)
        if p is not None:
            old_positions[key] = (p.x, p.y, p.collapsed)

    state.buttons = []
    state.tool_buttons = []

    SIDEBAR_W = 232
    LAYER_MAP_W = 158  # dùng lại bên dưới khi tạo layer_map_panel
    toolbar_panel = Panel(state.SCREEN_W - SIDEBAR_W - 10, 8, SIDEBAR_W, 10, "Cong cu")
    # Bảng thống kê nhường 1 cột hẹp bên trái cho mini-map tầng (tạo bên
    # dưới) - dời sang phải đúng bằng bề rộng mini-map + khoảng hở, để 2
    # panel này KHÔNG đè lên nhau ở vị trí mặc định (vẫn kéo đi đâu tùy ý
    # được như mọi panel khác nếu người chơi muốn sắp xếp lại).
    stats_panel = Panel(8 + LAYER_MAP_W + 10, 8, 740, 150, "Thong tin dan kien (2 to)")
    graph_panel = Panel(8, state.SCREEN_H - 214 - 10, 310, 178, "Dan so theo thoi gian")

    # --- Xây SIDEBAR bằng 1 "con trỏ dọc" (cursor_y) - mỗi phần tử thêm
    # vào tự cộng dồn xuống dưới, không cần tính tay từng tọa độ pixel ---
    inner_w = SIDEBAR_W - 20
    cursor = {"y": 10}
    section_labels = []  # (text, rel_y) - hud vẽ riêng trong draw_toolbar

    def add_section(text):
        section_labels.append((text, cursor["y"]))
        cursor["y"] += 20

    def add_full_button(label, on_click, style, active=False, h=30, tool_name=None):
        b = Button((0, 0, inner_w, h), label, on_click=on_click, style=style, active=active)
        if tool_name is not None:
            b.text_tool = tool_name
            state.tool_buttons.append(b)
        state.buttons.append(b)
        b.bind_to_panel(toolbar_panel, 10, cursor["y"])
        cursor["y"] += h + 6
        return b

    def add_half_buttons(label_a, cb_a, style_a, label_b, cb_b, style_b, h=30):
        half_w = (inner_w - 8) / 2
        ba = Button((0, 0, half_w, h), label_a, on_click=cb_a, style=style_a)
        ba.bind_to_panel(toolbar_panel, 10, cursor["y"])
        bb = Button((0, 0, half_w, h), label_b, on_click=cb_b, style=style_b)
        bb.bind_to_panel(toolbar_panel, 10 + half_w + 8, cursor["y"])
        state.buttons += [ba, bb]
        cursor["y"] += h + 6
        return ba, bb

    add_section("CONG CU DAT / CHINH SUA")
    for label, tool_name, style in [
        ("Dat thuc an", "food", "place"), ("Tha ke thu", "enemy", "danger"),
        ("Dat da", "rock", "place"), ("Dat nuoc", "water", "place"),
        ("Xoa", "erase", "tool"), ("Theo doi", "follow", "tool"),
    ]:
        add_full_button(label, lambda t=tool_name: state.set_tool(t), style, tool_name=tool_name)

    cursor["y"] += 4
    add_section("THOI GIAN")
    pause_btn, speed_btn = add_half_buttons(
        "Tam dung", None, "time", "Toc do: x1", None, "time")
    pause_btn.on_click = lambda: state.toggle_pause(pause_btn)
    speed_btn.on_click = lambda: state.cycle_speed(speed_btn)

    cursor["y"] += 4
    add_section("LUU/TAI (Ctrl+S / Ctrl+L)")
    add_half_buttons(
        "Luu van choi", lambda: state.save_game(), "time",
        "Tai van choi", lambda: state.load_game(), "time")

    cursor["y"] += 4
    add_section("CONG TAC BAT/TAT")
    respawn_btn = add_full_button("Tai sinh thuc an: BAT", None, "toggle", active=True, h=26)
    grid_btn = add_full_button("Luoi o vuong: BAT", None, "toggle", active=True, h=26)
    graph_btn = add_full_button("Bieu do: HIEN", None, "toggle", active=True, h=26)
    enemy_spawn_btn = add_full_button("Ke thu tu nhien: BAT", None, "toggle", active=True, h=26)
    auto_visit_btn = add_full_button("Tu dong ghe xem su kien: TAT", None, "toggle", active=False, h=26)
    cruise_btn = add_full_button("Camera tu lai (ranh tay): BAT", None, "toggle", active=True, h=26)
    respawn_btn.on_click = lambda: state.toggle_respawn(respawn_btn)
    grid_btn.on_click = lambda: state.toggle_grid(grid_btn)
    graph_btn.on_click = lambda: state.toggle_graph(graph_btn)
    enemy_spawn_btn.on_click = lambda: state.toggle_enemy_spawn(enemy_spawn_btn)
    auto_visit_btn.on_click = lambda: state.toggle_auto_visit_events(auto_visit_btn)
    cruise_btn.on_click = lambda: state.toggle_cruise_enabled(cruise_btn)

    cursor["y"] += 4
    add_section("DI CHUYEN TANG")
    add_half_buttons(
        "Tang ^", lambda: (state.stop_follow(), state.change_layer(-1)), "nav",
        "Tang v", lambda: (state.stop_follow(), state.change_layer(1)), "nav")

    cursor["y"] += 6  # chỗ cho dòng gợi ý cuối cùng (vẽ trong draw_toolbar)
    toolbar_panel.h = cursor["y"] + 18

    state.toolbar_panel = toolbar_panel
    state.toolbar_section_labels = section_labels
    state.stats_panel = stats_panel
    state.graph_panel = graph_panel

    # -------------------------------------------------------------------
    # MINI-MAP TẦNG (dọc, mặc định bên TRÁI màn hình - đối diện sidebar
    # công cụ bên phải): xem TOÀN BỘ tầng cùng lúc như thanh "current
    # level" của Dwarf Fortress, thay vì chỉ đọc số tầng ở góc màn hình.
    # Tầng NÔNG nhất (mặt đất) vẽ TRÊN CÙNG, sâu nhất ở DƯỚI CÙNG - đúng
    # trực giác nhìn cắt lớp từ trên xuống. Bấm trực tiếp vào 1 ô để nhảy
    # thẳng tới tầng đó (không cần bấm Tang^/Tang v nhiều lần). Dùng chung
    # cơ chế Panel/Button có sẵn (kéo di chuyển + thu gọn được) cho nhất
    # quán với toolbar/stats/graph, dù nội dung mỗi "nút" ở đây được TỰ VẼ
    # riêng (dải màu đại diện + 2 dòng chữ) thay vì Button.draw() mặc định
    # - xem draw_layer_map() bên dưới.
    LAYER_BOX_H = 42
    LAYER_BOX_GAP = 5
    max_depth = state.max_layer_overall()
    n_layers = max_depth + 1
    # Vị trí mặc định: góc TRÊN-TRÁI (cột riêng, KHÔNG dùng chung cột với
    # bảng thống kê/biểu đồ - 2 panel đó đã tự nhường chỗ, xem stats_panel
    # ở trên) - dọc hết chiều cao cần thiết theo số tầng thực tế của ván
    # chơi, không cố định cứng.
    layer_map_panel = Panel(8, 8, LAYER_MAP_W,
                             n_layers * (LAYER_BOX_H + LAYER_BOX_GAP) + 4, "Ban do tang")
    state.layer_map_buttons = []
    for i, depth in enumerate(range(0, n_layers)):
        rel_y = 6 + i * (LAYER_BOX_H + LAYER_BOX_GAP)
        btn = Button((0, 0, LAYER_MAP_W - 20, LAYER_BOX_H), "", on_click=lambda d=depth: state.set_layer(d), style="nav")
        btn.depth = depth
        btn.swatches = _layer_swatches(state, depth)
        btn.bind_to_panel(layer_map_panel, 10, rel_y)
        state.layer_map_buttons.append(btn)
    state.layer_map_panel = layer_map_panel

    # -------------------------------------------------------------------
    # Panel chuyển TAB (luôn hiện, độc lập với tab đang xem) - "Mo phong"
    # (ván chơi chính) / "Demo me cung" (minh họa thuật toán tìm đường any-
    # angle trên visibility graph - xem maze_demo.py, world hoàn toàn tách
    # biệt khỏi ván chơi thật). Đặt mặc định ở GIỮA-DƯỚI màn hình để không
    # đụng vị trí mặc định của các panel khác ở CẢ 2 tab.
    # -------------------------------------------------------------------
    TAB_PANEL_W = 260
    tab_panel = Panel(state.SCREEN_W / 2 - TAB_PANEL_W / 2, state.SCREEN_H - 78, TAB_PANEL_W, 38, "Che do xem")
    sim_tab_btn = Button((0, 0, 118, 30), "Mo phong", style="nav")
    maze_tab_btn = Button((0, 0, 118, 30), "Demo me cung", style="nav")
    sim_tab_btn.on_click = lambda: (state.switch_tab("sim"), _sync_tab_buttons(state))
    maze_tab_btn.on_click = lambda: (state.switch_tab("maze"), _sync_tab_buttons(state))
    sim_tab_btn.bind_to_panel(tab_panel, 8, 6)
    maze_tab_btn.bind_to_panel(tab_panel, 8 + 118 + 6, 6)
    state.buttons += [sim_tab_btn, maze_tab_btn]
    state.tab_buttons = {"sim": sim_tab_btn, "maze": maze_tab_btn}
    _sync_tab_buttons(state)
    state.tab_panel = tab_panel

    # -------------------------------------------------------------------
    # Panel công cụ riêng cho tab Demo mê cung - CHỈ hiện khi active_tab
    # == "maze" (xem GameState.visible_panels()).
    # -------------------------------------------------------------------
    maze_panel = Panel(8, 8, 250, 10, "Demo me cung: tim duong")
    mcursor = {"y": 10}

    def m_add_button(label, on_click, style, h=30, active=False):
        b = Button((0, 0, 230, h), label, on_click=on_click, style=style, active=active)
        b.bind_to_panel(maze_panel, 10, mcursor["y"])
        state.buttons.append(b)
        mcursor["y"] += h + 6
        return b

    m_add_button("Me cung moi (Sinh lai)", lambda: state.maze_demo.regenerate(), "place")
    mgraph_btn = m_add_button("Hien dinh visibility graph: BAT", None, "toggle", active=True)
    mgraph_btn.on_click = lambda: _toggle_maze_flag(state, "show_graph", mgraph_btn)
    mgrid_btn = m_add_button("Luoi o vuong: BAT", None, "toggle", active=True)
    mgrid_btn.on_click = lambda: _toggle_maze_flag(state, "show_grid", mgrid_btn)

    mcursor["y"] += 6
    maze_panel.h = mcursor["y"] + 78  # + chỗ cho vài dòng giải thích ngắn (draw_maze_panel)
    state.maze_panel = maze_panel

    # -------------------------------------------------------------------
    # THẺ THÔNG TIN CON KIẾN ĐANG THEO DÕI ("Ant card") - CHỈ hiện khi
    # đang theo dõi 1 con kiến cụ thể (xem GameState.visible_panels() và
    # draw_ant_card()). Đặt mặc định GÓC DƯỚI-PHẢI (đối xứng với biểu đồ
    # dân số ở góc dưới-trái) - vị trí này gần khung nhìn con kiến đang
    # phóng to nhất mà vẫn không che sidebar công cụ bên phải.
    # -------------------------------------------------------------------
    ANT_PANEL_W = 300
    ant_panel = Panel(state.SCREEN_W - ANT_PANEL_W - 10, state.SCREEN_H - 190 - 10,
                       ANT_PANEL_W, 190, "Con kien dang theo doi")
    nav_w = (ANT_PANEL_W - 20 - 2 * 8) / 3
    ant_prev_btn = Button((0, 0, nav_w, 30), "< Con truoc", on_click=lambda: state.follow_next(-1), style="nav")
    ant_next_btn = Button((0, 0, nav_w, 30), "Con tiep >", on_click=lambda: state.follow_next(1), style="nav")
    ant_stop_btn = Button((0, 0, nav_w, 30), "Bo theo doi", on_click=lambda: state.stop_follow(), style="danger")
    ant_prev_btn.bind_to_panel(ant_panel, 10, 128)
    ant_next_btn.bind_to_panel(ant_panel, 10 + nav_w + 8, 128)
    ant_stop_btn.bind_to_panel(ant_panel, 10 + 2 * (nav_w + 8), 128)
    state.buttons += [ant_prev_btn, ant_next_btn, ant_stop_btn]
    state.ant_panel = ant_panel

    # -------------------------------------------------------------------
    # ĐIỀU KHIỂN LẬP TỔ - CHỈ hiện trong lúc chúa còn đang trên mặt đất
    # tìm chỗ/đào hang (queen_walk_active=True - xem GameState.
    # update_queen_founding() và draw_founding_controls()). Cùng vị trí
    # với ant_panel (không bao giờ hiện CÙNG LÚC - lúc chúa còn đang lập
    # tổ thì chưa có con thợ nào để theo dõi).
    # -------------------------------------------------------------------
    FOUND_PANEL_W = 300
    founding_panel = Panel(state.SCREEN_W - FOUND_PANEL_W - 10, state.SCREEN_H - 172 - 10,
                            FOUND_PANEL_W, 172, "Điều khiển lập tổ")

    def _found_row(rel_y, minus_cb, plus_cb):
        minus_btn = Button((0, 0, 28, 26), "-", on_click=minus_cb, style="nav")
        plus_btn = Button((0, 0, 28, 26), "+", on_click=plus_cb, style="nav")
        minus_btn.bind_to_panel(founding_panel, 190, rel_y)
        plus_btn.bind_to_panel(founding_panel, 190 + 28 + 6, rel_y)
        state.buttons += [minus_btn, plus_btn]

    _found_row(8, lambda: state.adjust_queen_walk_speed(-0.01), lambda: state.adjust_queen_walk_speed(0.01))
    _found_row(42, lambda: state.adjust_queen_dig_speed_mult(-0.25), lambda: state.adjust_queen_dig_speed_mult(0.25))
    _found_row(76, lambda: state.adjust_queen_wander_radius(-0.5 * cfg.ROOM_LAYOUT_SCALE),
               lambda: state.adjust_queen_wander_radius(0.5 * cfg.ROOM_LAYOUT_SCALE))
    _found_row(110, lambda: state.adjust_queen_walk_hops(-1), lambda: state.adjust_queen_walk_hops(1))
    state.founding_panel = founding_panel

    # -------------------------------------------------------------------
    # NHẬT KÝ SỰ KIỆN - LUÔN hiện (không tùy thuộc trạng thái gì, khác
    # ant_panel/founding_panel) - đặt vào khoảng trống giữa biểu đồ dân số
    # (góc dưới-trái) và ant_panel/founding_panel (góc dưới-phải).
    # -------------------------------------------------------------------
    EVENT_LOG_W = 400
    event_log_panel = Panel(8 + 310 + 12, state.SCREEN_H - 214 - 10, EVENT_LOG_W, 178, "Nhat ky su kien")
    state.EVENT_LOG_MAX_ROWS = 6
    for i in range(state.EVENT_LOG_MAX_ROWS):
        row_btn = Button((0, 0, EVENT_LOG_W - 20, 20), "", on_click=(lambda ii=i: state.jump_to_event(ii)),
                          style="default")
        row_btn.bind_to_panel(event_log_panel, 10, 8 + i * 22)
        state.buttons.append(row_btn)
    state.event_log_panel = event_log_panel

    state.panels = [toolbar_panel, stats_panel, graph_panel, layer_map_panel, tab_panel, maze_panel,
                    ant_panel, founding_panel, event_log_panel]

    for key, panel in (
        ("toolbar_panel", toolbar_panel), ("stats_panel", stats_panel),
        ("graph_panel", graph_panel), ("layer_map_panel", layer_map_panel),
        ("tab_panel", tab_panel), ("maze_panel", maze_panel), ("ant_panel", ant_panel),
        ("founding_panel", founding_panel), ("event_log_panel", event_log_panel),
    ):
        if key in old_positions:
            x, y, collapsed = old_positions[key]
            panel.collapsed = collapsed
            panel.move_to(x, y, state.SCREEN_W, state.SCREEN_H)


def _sync_tab_buttons(state):
    for name, btn in state.tab_buttons.items():
        btn.active = (state.active_tab == name)


def _toggle_maze_flag(state, attr, btn):
    val = not getattr(state.maze_demo, attr)
    setattr(state.maze_demo, attr, val)
    label = btn.text.rsplit(":", 1)[0]
    btn.text = f"{label}: {'BAT' if val else 'TAT'}"
    btn.active = val


def _layer_swatches(state, depth):
    """Danh sách (mau, ten) đại diện cho tầng `depth` - dùng bởi mini-map
    tầng (xem build_toolbar/draw_layer_map). Tầng 0 (mặt đất) không nằm
    trong world.rooms nên xử lý riêng; các tầng ngầm CHUNG NHAU (vd Kho
    thức ăn + Bể trữ nước cùng ở tầng 2) trả về NHIỀU màu - hiện dải màu
    riêng cho từng phòng để biết ngay tầng này gồm những gì mà không cần
    đọc hết chữ (chữ dài dễ bị cắt trong ô nhỏ)."""
    if depth == 0:
        return [(cfg.COLOR_GROUND_FILL, "Mat dat")]
    out = [(color, name) for (_id, name, _pos, _r, color, d) in state.underground_world.rooms if d == depth]
    return out or [((90, 90, 90), layer_name(depth))]


# ---------------------------------------------------------------------
# Mini-map tầng (dọc) - xem TOÀN BỘ tầng cùng lúc, giống thanh "current
# level" của Dwarf Fortress, thay vì chỉ đọc số tầng ở góc màn hình.
# ---------------------------------------------------------------------
def draw_layer_map(state, surf):
    panel = state.layer_map_panel
    # Cập nhật "đang xem tầng nào" mỗi khung hình TRƯỚC khi vẽ - current_layer
    # có thể đổi bất cứ lúc nào (phím tắt, lăn chuột, camera tự bám kiến),
    # không riêng gì lúc bấm vào chính mini-map này.
    for btn in state.layer_map_buttons:
        btn.active = (btn.depth == state.current_layer)

    panel.draw_frame(surf, state.font)
    if panel.collapsed:
        return
    for btn in state.layer_map_buttons:
        _draw_layer_box(state, surf, btn)


def _draw_layer_box(state, surf, btn):
    r = btn.rect
    is_current = btn.active

    # Nền: tầng ĐANG XEM sáng hẳn lên (vàng đồng, khớp tông "nav" của
    # 2 nút Tang^/Tang v trong sidebar) để không cần đọc chữ cũng biết
    # ngay đang ở đâu; các tầng khác tối, không cạnh tranh thị giác.
    if is_current:
        draw_pixel_rect(surf, r, (72, 62, 30), (225, 180, 70), border_width=2)
    else:
        draw_pixel_rect(surf, r, (30, 30, 36), (60, 60, 68), border_width=1)

    # Dải màu dọc bên trái đại diện (các) phòng thuộc tầng này - biết
    # ngay tầng này có gì mà không cần đọc hết chữ (chữ dễ bị cắt trong
    # ô nhỏ, nhất là tầng có tới 3 phòng chung như Trứng/Ấu trùng/Nhộng)
    swatches = btn.swatches
    n = len(swatches)
    seg_h = (r.h - 8) / n
    for i, (color, _name) in enumerate(swatches):
        seg = pygame.Rect(r.x + 5, int(r.y + 4 + i * seg_h), 7, max(2, int(seg_h) - 1))
        pygame.draw.rect(surf, color, seg)

    text_x = r.x + 5 + 7 + 8
    depth_label = "Mat dat" if btn.depth == 0 else f"Tang {btn.depth}"
    l1 = render_cached(state.font_small, depth_label, (255, 255, 255) if is_current else (200, 200, 205))
    surf.blit(l1, (text_x, r.y + 5))

    # Dòng 2: tên (các) phòng nối bằng "/" - CẮT BỚT nếu quá dài để không
    # tràn ra ngoài ô (ô khá hẹp, nhất là tầng có 3 phòng chung)
    names_text = "/".join(n for _c, n in swatches)
    max_w = r.w - (text_x - r.x) - 6
    while state.font_small.size(names_text)[0] > max_w and len(names_text) > 3:
        names_text = names_text[:-2]
    if names_text != "/".join(n for _c, n in swatches):
        names_text += "…"
    l2 = render_cached(state.font_small, names_text, (215, 195, 140) if is_current else (150, 150, 158))
    surf.blit(l2, (text_x, r.y + 5 + l1.get_height() + 1))

    # Mũi tên nhỏ chỉ vào tầng đang xem, nhô ra bên PHẢI khung - dấu hiệu
    # phụ để nhận ra "đang ở đây" ngay cả khi lướt mắt nhanh không đọc chữ
    if is_current:
        ax = r.right + 4
        ay = r.centery
        pygame.draw.polygon(surf, (225, 180, 70), [(ax, ay - 7), (ax + 9, ay), (ax, ay + 7)])


# ---------------------------------------------------------------------
# Biểu đồ dân số theo thời gian (Panel nổi, kéo/thu gọn được)
# ---------------------------------------------------------------------
def draw_toasts(state, surf):
    """Vẽ các thông báo nổi bật (toast) - LUÔN CỐ ĐỊNH giữa-DƯỚI màn hình,
    HOÀN TOÀN KHÔNG phụ thuộc panel nào (không bị ẩn dù panel thống kê
    đang thu gọn hay bị kéo đi đâu) - dùng cho cảnh báo sự kiện quan trọng
    (đói/khát/kẻ thù/bị xâm chiếm/tuyệt chủng) VÀ xác nhận lưu/tải ván
    chơi. Mỗi toast tự nhòe dần vào lúc xuất hiện và trước khi biến mất.

    Neo GIỮA-DƯỚI (không phải giữa-trên như trước) vì góc trên luôn có ít
    nhất 1 panel nổi (thống kê/mini-map tầng) che ngang đúng vùng giữa-
    trên - dưới màn hình trống trải hơn hẳn (chỉ có panel biểu đồ nằm
    riêng ở góc DƯỚI-TRÁI, không lấn vào vùng giữa)."""
    if not state.toasts:
        return
    y = state.CANVAS_H - 54   # đáy toast đầu tiên (mới nhất), các toast cũ
                               # hơn xếp chồng dần LÊN TRÊN từ đây
    # Lệch tâm sang phải 1 chút (không đúng giữa tuyệt đối) - né góc DƯỚI-
    # TRÁI, nơi panel biểu đồ mặc định hay nằm (8, SCREEN_H-224, rộng 310)
    # - toast dài dễ đè lên góc phải panel đó nếu căn đúng giữa màn hình.
    cx = int(state.SCREEN_W * 0.56)
    for t in state.toasts:
        age = state.frame_counter - t["created"]
        remaining = cfg.TOAST_TTL_FRAMES - age
        if age < cfg.TOAST_FADE_FRAMES:
            alpha = int(255 * age / cfg.TOAST_FADE_FRAMES)
        elif remaining < cfg.TOAST_FADE_FRAMES:
            alpha = int(255 * max(0, remaining) / cfg.TOAST_FADE_FRAMES)
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))

        text_img = render_cached(state.font, t["msg"], (245, 245, 245))
        box_w = text_img.get_width() + 34
        box_h = text_img.get_height() + 16
        box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box.fill((22, 22, 27, 235))
        pygame.draw.rect(box, t["color"], (0, 0, 6, box_h))
        pygame.draw.rect(box, (95, 95, 108), box.get_rect(), width=1)
        box.blit(text_img, (18, 8))
        box.set_alpha(alpha)
        rect = box.get_rect(midbottom=(cx, y))
        surf.blit(box, rect)
        y -= box_h + 6


def draw_graph(state, surf):
    if not state.graph_visible:
        return
    panel = state.graph_panel
    panel.draw_frame(surf, state.font)
    if panel.collapsed or len(state.pop_history_main) < 2:
        return
    cx, cy = panel.content_pos()
    cw, ch = panel.w, panel.h

    max_val = max(max(state.pop_history_main, default=1), 5)
    pad = 10
    gx0, gx1 = cx + pad, cx + cw - pad
    gy0, gy1 = cy + ch - pad, cy + 16

    def to_points(hist):
        pts = []
        for i, v in enumerate(hist):
            t = i / max(1, cfg.HISTORY_MAX_POINTS - 1)
            x = gx0 + t * (gx1 - gx0)
            y = gy0 - min(1.0, v / max_val) * (gy0 - gy1)
            pts.append((x, y))
        return pts

    legend_y = cy + 4
    pygame.draw.circle(surf, COL_MAIN, (cx + 10, legend_y + 5), 4)
    surf.blit(render_cached(state.font_small, "Dan so", COL_MAIN), (cx + 18, legend_y))

    if len(state.pop_history_main) >= 2:
        pygame.draw.lines(surf, COL_MAIN, False, to_points(state.pop_history_main), 2)


# ---------------------------------------------------------------------
# Bảng thống kê (Panel nổi) + nhãn tầng hiện tại (nhỏ, cố định góc trên phải)
# ---------------------------------------------------------------------
def _blit_row(surf, font, x, y, segments):
    """Vẽ 1 dòng gồm nhiều đoạn (text, color) NỐI TIẾP NHAU - nhãn mờ + giá
    trị sáng xen kẽ, dễ đọc hơn hẳn 1 màu trắng đồng nhất."""
    cur_x = x
    for text, color in segments:
        img = render_cached(font, text, color)
        surf.blit(img, (cur_x, y))
        cur_x += img.get_width()
    return cur_x


def _draw_progress_bar(surf, x, y, w, h, frac, fill_color, bg_color=(40, 40, 46)):
    """Thanh progress đơn giản (khung góc vuông kiểu pixel + phần lấp đầy
    theo frac 0.0-1.0) - dùng cho năng lượng dự trữ của chúa lúc lập tổ."""
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surf, bg_color, (x, y, w, h))
    if frac > 0:
        pygame.draw.rect(surf, fill_color, (x, y, max(3, int(w * frac)), h))
    pygame.draw.rect(surf, (90, 90, 100), (x, y, w, h), width=1)


def draw_hud(state, surf):
    colony, enemy, invasion = state.colony, state.enemy, state.invasion
    c = colony.counts()
    inv = invasion.counts()

    warnings = []  # (text, color)
    if c["is_starving"]:
        warnings.append(("*** DAN KIEN DANG DOI ***", COL_BAD))
    if c["is_dehydrated"]:
        warnings.append(("*** DAN KIEN DANG KHAT NUOC ***", (255, 175, 70)))
    if enemy.active:
        warnings.append(("*** CO KE THU TREN MAT DAT ***", (255, 210, 70)))
    if inv["active"]:
        warnings.append((f"*** DAN KIEN NGOAI LAI DANG XAM NHAP ({inv['raiders_left']} con) ***", COL_BAD))

    LINE_H = 22
    # 4 dòng (dân số, tài nguyên, tổn thất, phân bố chức năng) - RIÊNG lúc
    # đang lập tổ (founding_phase) chỉ tốn 2 dòng gọn hơn (xem colony_block)
    # thay vì 4 dòng đầy số "0" vô nghĩa lúc chưa có kho/ấu trùng.
    main_lines = 2 if c["founding_phase"] else 5
    n_lines = main_lines + 2 + len(warnings) + 1
    panel = state.stats_panel
    panel.h = max(90, LINE_H * n_lines + 20)
    panel.draw_frame(surf, state.font)
    if not panel.collapsed:
        cx, cy = panel.content_pos()
        LX = 10
        y = [cy + 6]  # dùng list để sửa được trong hàm lồng bên dưới

        def colony_block(label, accent, cdata, cobj):
            if cdata["founding_phase"]:
                # --- Bản GỌN dành riêng cho lúc đang lập tổ: chỉ 1 chúa
                # duy nhất, chưa có kho/ấu trùng/phân công gì để hiện -
                # thay bằng đúng 2 thứ người chơi cần theo dõi lúc này:
                # còn bao nhiêu năng lượng dự trữ, và đã đủ mấy nanitic. ---
                _blit_row(surf, state.font_hud, cx + LX, y[0], [
                    (f"{label}   ", accent),
                    ("DANG LAP TO", (230, 190, 230)),
                    ("    Tho dau (nanitic) ", COL_LABEL),
                    (f"{cdata['population']}/{cfg.FOUNDING_NANITIC_TARGET}", COL_VALUE),
                ])
                y[0] += LINE_H
                energy_frac = cdata["queen_energy"] / cfg.QUEEN_INITIAL_ENERGY if cfg.QUEEN_INITIAL_ENERGY > 0 else 0
                label_img = render_cached(state.font_hud, "Nang luong du tru cua chua ", COL_LABEL)
                surf.blit(label_img, (cx + LX + 18, y[0] + 2))
                bar_x = cx + LX + 18 + label_img.get_width()
                _draw_progress_bar(surf, bar_x, y[0] + 3, 140, LINE_H - 8, energy_frac, (200, 130, 210))
                pct_img = render_cached(state.font_hud, f" {energy_frac * 100:.0f}%", COL_VALUE)
                surf.blit(pct_img, (bar_x + 146, y[0] + 2))
                y[0] += LINE_H
                return

            _blit_row(surf, state.font_hud, cx + LX, y[0], [
                (f"{label}   ", accent),
                ("Dan so ", COL_LABEL), (f"{cdata['population']}/{cobj.n}    ", COL_VALUE),
                ("Linh ", COL_LABEL), (f"{cdata['soldiers']}    ", COL_VALUE),
                ("Gac ", COL_LABEL), (f"{cdata['guards_on_duty']}/{cdata['guards_total']}    ", COL_VALUE),
                ("Sinh ", COL_LABEL), (f"{cdata['total_births']}    ", COL_GOOD),
                ("Chet ", COL_LABEL), (f"{cdata['total_deaths']}", COL_BAD),
            ])
            y[0] += LINE_H
            _blit_row(surf, state.font_hud, cx + LX + 18, y[0], [
                ("Kho ", COL_LABEL), (f"{cdata['food_in_storage']:.0f}    ", COL_FOOD),
                ("Nuoc ", COL_LABEL), (f"{cdata['water_in_storage']:.0f}    ", COL_WATER),
                ("Trung ", COL_LABEL), (f"{cdata['egg_count']} qua    ", COL_VALUE),
                ("Au trung ", COL_LABEL), (f"{cdata['larva_count']} con    ", COL_VALUE),
                ("Nhong ", COL_LABEL), (f"{cdata['pupa_count']} ken", COL_VALUE),
            ])
            y[0] += LINE_H
            _blit_row(surf, state.font_hud, cx + LX + 18, y[0], [
                ("Nghia dia ", COL_LABEL), (f"{cdata['corpse_count']:.0f} xac", COL_VALUE),
            ])
            y[0] += LINE_H
            _blit_row(surf, state.font_hud, cx + LX + 18, y[0], [
                ("Kiem an ", COL_LABEL), (f"{cdata['foragers_total']}    ", COL_VALUE),
                ("Cham au trung ", COL_LABEL), (f"{cdata['nurses_total']}    ", (255, 175, 205)),
                ("Cham trung+chua ", COL_LABEL), (f"{cdata['attendants_total']}", (200, 150, 240)),
            ])
            y[0] += LINE_H

            # Thanh phần trăm PHÂN BỐ CHỨC NĂNG - giúp NHÌN MỘT PHÁT thấy tỉ
            # lệ (kiếm ăn nhiều hơn hẳn/nuôi non đang thiếu người...) thay vì
            # phải tự cộng nhẩm mấy con số ở dòng trên.
            segments = [
                (cdata["foragers_total"], COL_VALUE, "Kiem an"),
                (cdata["nurses_total"], (255, 175, 205), "Cham au trung"),
                (cdata["attendants_total"], (200, 150, 240), "Cham trung+chua"),
                (cdata["guards_total"], (230, 150, 90), "Linh gac"),
            ]
            total_role = max(1, sum(s[0] for s in segments))
            bar_x = cx + LX + 18
            bar_w = panel.w - 2 * LX - 18 - 16
            bar_h = LINE_H - 10
            bx = bar_x
            for count, color, _lbl in segments:
                seg_w = round(bar_w * count / total_role)
                if seg_w > 0:
                    pygame.draw.rect(surf, color, (bx, y[0] + 2, seg_w, bar_h))
                bx += seg_w
            pygame.draw.rect(surf, (90, 90, 100), (bar_x, y[0] + 2, bar_w, bar_h), width=1)
            y[0] += LINE_H

        colony_block("TO CHINH", COL_MAIN, c, colony)

        y[0] += 3
        pygame.draw.line(surf, (70, 70, 78), (cx + LX, y[0]), (cx + panel.w - LX, y[0]), 1)
        y[0] += 5

        # Kẻ thù ngoài tự nhiên + đàn kiến ngoại lai đều là thực thể DÙNG
        # CHUNG cho cả bản đồ (không thuộc/gắn với đàn nào) nên hiển thị
        # riêng, tách khỏi khối thống kê của tổ.
        _blit_row(surf, state.font_hud, cx + LX, y[0], [
            ("Ke thu tren mat dat ", COL_LABEL),
            ("CO" if enemy.active else "KHONG", (255, 210, 70) if enemy.active else COL_VALUE),
            ("    Tong so da bi kien giet ", COL_LABEL), (f"{enemy.total_kills}", (255, 150, 150)),
        ])
        y[0] += LINE_H

        if inv["active"]:
            _blit_row(surf, state.font_hud, cx + LX, y[0], [
                ("Dan ngoai lai ", COL_LABEL),
                (f"DOT {inv['wave_number'] + 1} - con {inv['raiders_left']} quan", COL_INVASION),
                ("    Da cuop ", COL_LABEL), (f"{inv['total_food_stolen']:.0f} thuc an, {inv['total_brood_stolen']} trung/au trung", (255, 210, 120)),
            ])
        else:
            ticks_left = max(0, inv["next_wave_tick"] - colony.tick_count)
            secs_left = ticks_left / cfg.FPS
            _blit_row(surf, state.font_hud, cx + LX, y[0], [
                ("Dan ngoai lai ", COL_LABEL),
                (f"dot tiep theo sau ~{secs_left:.0f}s ({inv['next_wave_size']} quan)", COL_VALUE),
            ])
        y[0] += LINE_H

        warn_bg = get_flat_alpha_surface((panel.w - 2 * LX, LINE_H - 2), COL_WARN_BG)
        for wtext, wcolor in warnings:
            surf.blit(warn_bg, (cx + LX, y[0] - 1))
            img = render_cached(state.font_hud, wtext, wcolor)
            surf.blit(img, (cx + LX + 4, y[0]))
            y[0] += LINE_H

        hint = "Ctrl+Lan chuot: doi tang | Lan chuot: zoom | Chuot phai+keo: di chuyen | Esc: thoat"
        img = render_cached(state.font_small, hint, (135, 135, 145))
        surf.blit(img, (cx + LX, y[0] + 2))

    # --- nhãn tầng hiện tại: nhỏ, LUÔN CỐ ĐỊNH góc trên-phải (không phải
    # panel kéo được - đủ nhỏ để không thực sự che khung nhìn) ---
    name = layer_name(state.current_layer)
    label = render_cached(state.font_big, f"Tang {state.current_layer}: {name}", (255, 255, 80))
    lr = label.get_rect(topright=(state.SCREEN_W - 12, 8))
    bg = get_flat_alpha_surface((lr.w + 16, lr.h + 10), (0, 0, 0, 150))
    surf.blit(bg, (lr.x - 8, lr.y - 5))
    surf.blit(label, lr)


# ---------------------------------------------------------------------
# Thẻ thông tin CON KIẾN ĐANG THEO DÕI - bản mô tả "đang làm gì" thân
# thiện dựa trên state.STATE_* (xem config.py), thay vì chỉ hiện đúng 1
# dòng số hiệu trạng thái khô khan như trước.
# ---------------------------------------------------------------------
STATE_ACTIVITY_LABELS = {
    cfg.STATE_SEARCHING: "Đang tìm thức ăn trên mặt đất",
    cfg.STATE_RETURNING: "Đang tha đồ về tổ",
    cfg.STATE_UG_TO_STORAGE: "Đang mang đồ xuống kho",
    cfg.STATE_UG_TO_SHAFT: "Đang quay lại giếng để lên mặt đất",
    cfg.STATE_DWELL: "Đang lượn quanh trong phòng",
    cfg.STATE_GUARD_DUTY: "Đang đứng gác",
    cfg.STATE_GUARD_RUSH: "Đang lao lên mặt đất nghênh chiến!",
    cfg.STATE_GUARD_RETURN: "Đang quay về sau khi giao chiến",
    cfg.STATE_NURSE_AT_STORAGE: "Đang ở kho, chờ lấy thức ăn cho ấu trùng",
    cfg.STATE_NURSE_TO_NURSERY: "Đang mang thức ăn sang phòng ấu trùng",
    cfg.STATE_NURSE_AT_NURSERY: "Đang chăm ấu trùng",
    cfg.STATE_NURSE_TO_STORAGE: "Đang quay lại kho lấy chuyến tiếp theo",
    cfg.STATE_ATTENDANT_AT_QUEEN: "Đang túc trực cạnh chúa",
    cfg.STATE_ATTENDANT_TO_EGG: "Đang di chuyển sang phòng trứng",
    cfg.STATE_ATTENDANT_AT_EGG: "Đang trông trứng",
    cfg.STATE_ATTENDANT_TO_QUEEN: "Đang quay lại phòng chúa",
    cfg.STATE_UNDERTAKER_TO_CORPSE: "Đang đi khiêng xác đồng loại",
    cfg.STATE_UNDERTAKER_TO_GRAVEYARD: "Đang mang xác về nghĩa địa",
    cfg.STATE_HAUL_APPROACH: "Đang tới chỗ con mồi lớn",
    cfg.STATE_HAUL_GRIP: "Đang chờ đồng đội cùng khiêng con mồi",
}


def _ant_role_label(colony, idx):
    if bool(colony.is_guard[idx]):
        return "Lính gác", COL_INVASION
    job = int(colony.job[idx])
    if job == cfg.JOB_NURSE:
        return "Y tá (chăm ấu trùng)", (255, 175, 205)
    if job == cfg.JOB_ATTENDANT:
        return "Hộ vệ (chăm trứng/chúa)", (200, 150, 240)
    return "Thợ kiếm ăn", COL_MAIN


def draw_ant_card(state, surf):
    """Vẽ THẺ THÔNG TIN con kiến đang theo dõi - panel riêng, chỉ hiện khi
    state.is_following() (xem GameState.visible_panels()). Cung cấp góc
    nhìn kiểu "đang ngồi ngắm 1 con kiến cụ thể": vai trò, đang làm gì,
    tuổi (quy đổi ra thời gian thực để dễ hình dung), tầng, đang mang gì -
    cùng 3 nút điều hướng CON TRƯỚC/CON TIẾP/BỎ THEO DÕI để "duyệt" qua
    từng con kiến liên tục mà không cần bấm trúng chính xác từng con nhỏ
    xíu trên màn hình."""
    if not state.is_following():
        return
    panel = state.ant_panel
    colony, idx = state.follow_colony, state.follow_idx
    panel.draw_frame(surf, state.font)
    if panel.collapsed:
        return
    cx, cy = panel.content_pos()
    LX = 10
    LINE_H = 22
    y = cy + 6

    role_label, role_color = _ant_role_label(colony, idx)
    _blit_row(surf, state.font_hud, cx + LX, y, [
        ("Vai trò: ", COL_LABEL), (role_label, role_color),
    ])
    y += LINE_H

    activity = STATE_ACTIVITY_LABELS.get(int(colony.state[idx]), "Đang di chuyển")
    activity_bg = get_flat_alpha_surface((panel.w - 2 * LX, LINE_H - 2), COL_FOLLOW_BG)
    surf.blit(activity_bg, (cx + LX, y - 1))
    img = render_cached(state.font_hud, activity, COL_GOOD)
    surf.blit(img, (cx + LX + 4, y))
    y += LINE_H

    age_secs = float(colony.age[idx]) / cfg.FPS
    age_text = f"{age_secs / 60:.1f} phút" if age_secs >= 60 else f"{age_secs:.0f} giây"
    _blit_row(surf, state.font_hud, cx + LX, y, [
        ("Tuổi ", COL_LABEL), (f"{age_text}    ", COL_VALUE),
        ("Tầng ", COL_LABEL), (f"{int(colony.depth[idx])}: {layer_name(int(colony.depth[idx]))}", COL_VALUE),
    ])
    y += LINE_H

    if bool(colony.carrying[idx]):
        ct = int(colony.carry_type[idx])
        mang = "thức ăn" if ct == 1 else "nước" if ct == 2 else "ấu trùng/xác"
        _blit_row(surf, state.font_hud, cx + LX, y, [
            ("Đang mang: ", COL_LABEL), (mang, COL_FOOD if ct == 1 else COL_WATER if ct == 2 else COL_VALUE),
        ])
    else:
        _blit_row(surf, state.font_hud, cx + LX, y, [("Đang không mang gì", COL_LABEL)])
    y += LINE_H

    hint = "Click con khác trên màn hình cũng đổi kiến theo dõi"
    img = render_cached(state.font_small, hint, (135, 135, 145))
    surf.blit(img, (cx + LX, y + 2))

    for b in panel.children:
        b.draw(surf, state.font)


def draw_cruise_indicator(state, surf):
    """Dòng chữ nhỏ NHẮC người chơi biết camera đang TỰ LÁI (không phải
    họ tự kéo) - chỉ hiện khi state.cruise_active=True (xem
    GameState.update_camera_cruise()), để không ai hoang mang tưởng
    camera bị lỗi/tự nhiên trôi đi."""
    if not state.cruise_active:
        return
    text = "🎥 Đang tự động ngắm cảnh - bấm chuột/phím bất kỳ để tự lái lại"
    img = render_cached(state.font_hud, text, (210, 205, 190))
    bg = pygame.Surface((img.get_width() + 20, img.get_height() + 12), pygame.SRCALPHA)
    bg.fill((20, 18, 15, 170))
    rect = bg.get_rect(midtop=(state.SCREEN_W // 2, 8))
    surf.blit(bg, rect)
    surf.blit(img, (rect.x + 10, rect.y + 6))


def draw_event_log(state, surf):
    """Vẽ panel Nhật ký sự kiện - LUÔN hiện (không tùy trạng thái gì).
    Liệt kê tối đa state.EVENT_LOG_MAX_ROWS mục GẦN NHẤT (mới nhất trên
    cùng), mỗi dòng kèm thời điểm (quy đổi tick -> phút:giây thực) - dòng
    NÀO CÓ GẮN VỊ TRÍ thì bấm vào sẽ đưa camera tới đó ngay (xem
    GameState.jump_to_event(), đã gắn sẵn nút click vô hình đè lên từng
    dòng - xem build_toolbar())."""
    panel = state.event_log_panel
    panel.draw_frame(surf, state.font)
    if panel.collapsed:
        return
    cx, cy = panel.content_pos()
    LX = 10
    for b in panel.children:
        b.draw(surf, state.font)
    recent = list(state.events)[::-1]
    if not recent:
        img = render_cached(state.font_small, "Chưa có sự kiện nào - hãy chờ xem điều gì xảy ra...",
                             (135, 135, 145))
        surf.blit(img, (cx + LX, cy + 10))
        return
    for i in range(min(state.EVENT_LOG_MAX_ROWS, len(recent))):
        ev = recent[i]
        secs = ev["tick"] / cfg.FPS
        tstamp = f"{int(secs // 60):02d}:{int(secs % 60):02d}"
        text = f"[{tstamp}] {ev['text']}"
        max_chars = 52
        if len(text) > max_chars:
            text = text[:max_chars - 1] + "…"
        clickable = ev["pos"] is not None
        color = ev["color"] if clickable else COL_LABEL
        img = render_cached(state.font_hud, text, color)
        surf.blit(img, (cx + LX, cy + 8 + i * 22 + 2))


def draw_founding_controls(state, surf):
    """Vẽ panel ĐIỀU KHIỂN LẬP TỔ - chỉ hiện trong lúc chúa còn đang trên
    mặt đất tìm chỗ/đào hang (state.queen_walk_active - xem
    GameState.update_queen_founding()). Cho phép chỉnh 4 tham số NGAY
    TRONG GAME (không cần sửa config.py, không cần khởi động lại):
    tốc độ đi, tốc độ đào, bán kính lượn quanh, số điểm dừng còn lại."""
    if not state.queen_walk_active:
        return
    panel = state.founding_panel
    panel.draw_frame(surf, state.font)
    if panel.collapsed:
        return
    cx, cy = panel.content_pos()
    LX = 10
    digging = state.queen_dig_timer > 0
    rows = [
        (f"Tốc độ đi: {state.queen_walk_speed:.3f} ô/tick", 8),
        (f"Tốc độ đào: {state.queen_dig_speed_mult:.2f}x", 42),
        (f"Bán kính lượn quanh: {state.queen_wander_radius:.1f} ô", 76),
        (f"Số điểm dừng còn lại: {state.queen_walk_hops_left}"
         + (" (đang đào, không áp dụng)" if digging else ""), 110),
    ]
    for text, rel_y in rows:
        img = render_cached(state.font_hud, text, COL_LABEL if digging and rel_y == 110 else COL_VALUE)
        surf.blit(img, (cx + LX, cy + rel_y + 5))

    for b in panel.children:
        b.draw(surf, state.font)

    hint = "Chỉnh được cả lúc đang đi lẫn đang đào"
    img = render_cached(state.font_small, hint, (135, 135, 145))
    surf.blit(img, (cx + LX, cy + 146))


def draw_toolbar(state, surf):
    """Vẽ SIDEBAR công cụ: khung + nhãn từng nhóm (CONG CU/THOI GIAN/CONG
    TAC/DI CHUYEN TANG) + toàn bộ nút (xếp dọc) + dòng gợi ý cuối cùng."""
    panel = state.toolbar_panel
    panel.draw_frame(surf, state.font)
    if panel.collapsed:
        return
    cx, cy = panel.content_pos()

    for text, rel_y in state.toolbar_section_labels:
        img = render_cached(state.font_small, text, COL_SECTION)
        surf.blit(img, (cx + 10, cy + rel_y))
        pygame.draw.line(
            surf, (60, 60, 68),
            (cx + 10 + img.get_width() + 8, cy + rel_y + 8),
            (cx + panel.w - 20, cy + rel_y + 8), 1,
        )

    for b in panel.children:
        b.draw(surf, state.font)

    hint = "Chon cong cu, CLICK hoac GIU+KEO chuot trai de dung"
    if state.current_tool == "follow":
        hint = "Theo doi: bam TRUNG 1 con kien de camera bam theo (tu doi tang theo) - bam cho TRONG de ngung"
    elif state.current_tool in ("food", "enemy", "rock", "water") and state.current_layer != 0:
        hint = "Cong cu nay chi dung o Tang 0 (Mat dat) - doi tang bang Ctrl+Lan chuot"
    elif state.current_tool in ("food", "enemy", "rock", "water", "erase"):
        hint = "Giu chuot trai va keo de rai lien tuc"
    words = hint.split(" ")
    lines_wrapped, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if state.font_small.size(trial)[0] > panel.w - 20:
            lines_wrapped.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines_wrapped.append(cur)
    hy = cy + panel.h - 16 * len(lines_wrapped) - 8
    for line in lines_wrapped:
        img = render_cached(state.font_small, line, (255, 230, 90))
        surf.blit(img, (cx + 10, hy))
        hy += 16


# ---------------------------------------------------------------------
# Panel chuyển tab ("Mo phong" <-> "Demo me cung") - luôn hiện, độc lập
# tab đang xem, xem GameState.switch_tab()/hud.build_toolbar().
# ---------------------------------------------------------------------
def draw_tab_panel(state, surf):
    panel = state.tab_panel
    panel.draw_frame(surf, state.font)
    if panel.collapsed:
        return
    for b in panel.children:
        b.draw(surf, state.font)


# ---------------------------------------------------------------------
# Panel công cụ tab "Demo mê cung" - xem maze_demo.py.
# ---------------------------------------------------------------------
def draw_maze_panel(state, surf):
    panel = state.maze_panel
    panel.draw_frame(surf, state.font)
    if panel.collapsed:
        return
    cx, cy = panel.content_pos()
    for b in panel.children:
        b.draw(surf, state.font)

    hint_lines = [
        "To kien (xanh duong) -> Thuc an (xanh la).",
        "Duong vang = duong di any-angle tim duoc",
        "(visibility graph + A*, xem pathfinding.py).",
        "Cham xanh nhat = dinh goc vat can duoc xet.",
        "World rieng - khong dung gi toi ban do that.",
    ]
    hy = cy + panel.h - 16 * len(hint_lines) - 10
    for line in hint_lines:
        img = render_cached(state.font_small, line, (190, 195, 205))
        surf.blit(img, (cx + 10, hy))
        hy += 16


# ---------------------------------------------------------------------
# Man hinh GAME OVER (to tuyet chung) - xem GameState._trigger_game_over()
# /restart_game() trong game_state.py. Truoc day day la "ngo cut" hoan
# toan: mo phong van chay tiep vo nghia o trang thai 0 kien, khong co
# man hinh tong ket, khong co cach nao choi lai ma khong tu dong lai
# chuong trinh - build_game_over_panel()/draw_game_over() la phan vá cho
# khoang trong do.
# ---------------------------------------------------------------------
def build_game_over_panel(state):
    """Dung 1 Panel noi (+ nut 'Choi lai tu dau') cho man hinh Game Over -
    goi 1 LAN DUY NHAT tu _trigger_game_over() ngay luc phat hien tuyet
    chung (khong tai su dung panel cu tu ván truoc, vi state da la 1 GameState
    hoan toan moi sau moi lan restart_game())."""
    w, h = 440, 250
    x = (state.SCREEN_W - w) / 2
    y = (state.SCREEN_H - (Panel.TITLE_H + h)) / 2
    panel = Panel(x, y, w, h, "To da tuyet chung")
    btn = Button(
        (0, 0, w - 40, 42), "Choi lai tu dau",
        on_click=state.restart_game, style="tool",
    )
    btn.bind_to_panel(panel, 20, h - 58)
    state.game_over_panel = panel


def draw_game_over(state, surf):
    """Ve lop phu mo den toan man hinh + panel tong ket Game Over - chi ve
    khi state.game_over=True (xem build_game_over_panel). Goi SAU CUNG
    trong render(), de nam TREN moi thu khac."""
    if not state.game_over or state.game_over_panel is None:
        return

    overlay = get_flat_alpha_surface((state.SCREEN_W, state.SCREEN_H), (0, 0, 0, 165))
    surf.blit(overlay, (0, 0))

    panel = state.game_over_panel
    panel.draw_frame(surf, state.font)
    if panel.collapsed:
        return

    cx, cy = panel.content_pos()
    title_img = render_cached(state.font_big, "TO DA TUYET CHUNG", (255, 120, 110))
    surf.blit(title_img, title_img.get_rect(midtop=(cx + panel.w / 2, cy + 6)))

    st = getattr(state, "_game_over_stats", {})
    lines = [
        f"Dan so cao nhat tung dat duoc: {st.get('peak_population', 0)}",
        f"So tick da song sot: {st.get('ticks_survived', 0)}",
        f"Tong so kien duoc sinh ra: {st.get('total_births', 0)}",
        f"Tong so kien da chet: {st.get('total_deaths', 0)}",
        f"Tong don vi thuc an thu thap: {st.get('total_food_collected', 0):.0f}",
        f"So dot xam luoc da chong do: {st.get('waves_survived', 0)}",
        f"Ke xam luoc da tieu diet: {st.get('invaders_killed', 0)}",
    ]
    ly = cy + 44
    for line in lines:
        img = render_cached(state.font_small, line, (222, 222, 228))
        surf.blit(img, (cx + 22, ly))
        ly += 21

    for b in panel.children:
        b.draw(surf, state.font)
