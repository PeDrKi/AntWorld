"""HUD: biểu đồ dân số, bảng thống kê, thanh công cụ - đều là các "cửa sổ"
(Panel) NỔI TRÊN màn hình mô phỏng: KÉO DI CHUYỂN được và THU GỌN được, để
người chơi tự sắp xếp sao cho không bị che mất khung nhìn đàn kiến (xem
ui_widgets.Panel). Bố cục/màu sắc được thiết kế để DỄ ĐỌC: mỗi nhóm chức
năng 1 màu riêng, nhãn/giá trị tách màu rõ, các dòng số liệu chia nhỏ theo
chủ đề thay vì dồn hết vào 1 dòng dài."""
import numpy as np
import pygame

import config as cfg
from ui_widgets import Button, Panel
from render_underground import layer_name

# --- Bảng màu dùng chung cho bảng thống kê (nhãn mờ, giá trị sáng, mỗi
# chủ đề 1 màu để mắt bắt được ngay không cần đọc kỹ từng chữ) ---
COL_LABEL = (145, 148, 158)      # nhãn (chữ nhỏ, mờ hơn giá trị)
COL_MAIN = (110, 190, 255)       # gắn với TỔ CHÍNH (khớp tông cam/đen của
                                  # kiến tổ chính trong render_surface)
COL_RIVAL = (255, 140, 100)      # gắn với TỔ ĐỐI THỦ
COL_VALUE = (232, 232, 235)      # giá trị số liệu trung tính
COL_GOOD = (120, 230, 140)       # số liệu "tốt" (sinh, đủ tài nguyên...)
COL_BAD = (255, 110, 100)        # số liệu "xấu" (chết, mất mát...)
COL_FOOD = (225, 190, 110)       # màu kho thức ăn
COL_WATER = (110, 190, 255)      # màu nước
COL_WARN_BG = (70, 20, 20, 130)  # nền mờ phía sau dòng cảnh báo
COL_FOLLOW_BG = (18, 55, 28, 140)  # nền mờ phía sau dòng "đang theo dõi"


def build_toolbar(state):
    """Tạo 3 Panel nổi (thanh công cụ / bảng thống kê / biểu đồ) và toàn bộ
    nút bấm bên trong thanh công cụ, nối callback vào state. Nếu state đã
    có sẵn panel từ trước (vd đang resize cửa sổ), GIỮ NGUYÊN vị trí/trạng
    thái thu gọn người chơi đã tự sắp xếp thay vì đặt lại về mặc định."""
    old_positions = {}
    for key in ("toolbar_panel", "stats_panel", "graph_panel"):
        p = getattr(state, key, None)
        if p is not None:
            old_positions[key] = (p.x, p.y, p.collapsed)

    state.buttons = []
    state.tool_buttons = []

    toolbar_panel = Panel(10, state.SCREEN_H - 150, 950, 104, "Dieu khien / Cong cu")
    stats_panel = Panel(8, 8, 940, 150, "Thong tin dan kien")
    graph_panel = Panel(state.SCREEN_W - 332, 54, 310, 178, "Dan so theo thoi gian")

    def make_tool_button(label, tool_name, rel_x, rel_y, style, w=96, h=30):
        b = Button((0, 0, w, h), label, on_click=lambda: state.set_tool(tool_name), style=style)
        b.text_tool = tool_name
        state.tool_buttons.append(b)
        state.buttons.append(b)
        b.bind_to_panel(toolbar_panel, rel_x, rel_y)
        return b

    rx = 6
    for label, tool_name, style in [
        ("Dat thuc an", "food", "place"), ("Tha ke thu", "enemy", "danger"),
        ("Dao phong", "dig", "place"), ("Dat da", "rock", "place"),
        ("Dat nuoc", "water", "place"), ("Xoa", "erase", "tool"),
        ("Theo doi", "follow", "tool"),
    ]:
        make_tool_button(label, tool_name, rx, 6, style)
        rx += 100

    pause_btn = Button((0, 0, 90, 30), "Tam dung", style="time")
    speed_btn = Button((0, 0, 90, 30), "Toc do: x1", style="time")
    pause_btn.on_click = lambda: state.toggle_pause(pause_btn)
    speed_btn.on_click = lambda: state.cycle_speed(speed_btn)
    pause_btn.bind_to_panel(toolbar_panel, rx + 14, 6)
    speed_btn.bind_to_panel(toolbar_panel, rx + 112, 6)
    state.buttons += [pause_btn, speed_btn]

    respawn_btn = Button((0, 0, 190, 26), "Tai sinh thuc an: BAT", active=True, style="toggle")
    grid_btn = Button((0, 0, 150, 26), "Luoi o vuong: BAT", active=True, style="toggle")
    graph_btn = Button((0, 0, 130, 26), "Bieu do: HIEN", active=True, style="toggle")
    enemy_spawn_btn = Button((0, 0, 200, 26), "Ke thu tu nhien: BAT", active=True, style="toggle")
    layer_up_btn = Button((0, 0, 60, 26), "Tang ^", style="nav")
    layer_down_btn = Button((0, 0, 60, 26), "Tang v", style="nav")

    respawn_btn.on_click = lambda: state.toggle_respawn(respawn_btn)
    grid_btn.on_click = lambda: state.toggle_grid(grid_btn)
    graph_btn.on_click = lambda: state.toggle_graph(graph_btn)
    enemy_spawn_btn.on_click = lambda: state.toggle_enemy_spawn(enemy_spawn_btn)
    layer_up_btn.on_click = lambda: (state.stop_follow(), state.change_layer(-1))
    layer_down_btn.on_click = lambda: (state.stop_follow(), state.change_layer(1))

    respawn_btn.bind_to_panel(toolbar_panel, 6, 46)
    grid_btn.bind_to_panel(toolbar_panel, 204, 46)
    graph_btn.bind_to_panel(toolbar_panel, 362, 46)
    enemy_spawn_btn.bind_to_panel(toolbar_panel, 500, 46)
    layer_up_btn.bind_to_panel(toolbar_panel, 724, 46)
    layer_down_btn.bind_to_panel(toolbar_panel, 792, 46)
    state.buttons += [respawn_btn, grid_btn, graph_btn, enemy_spawn_btn, layer_up_btn, layer_down_btn]

    state.toolbar_panel = toolbar_panel
    state.stats_panel = stats_panel
    state.graph_panel = graph_panel
    state.panels = [toolbar_panel, stats_panel, graph_panel]

    for key, panel in (("toolbar_panel", toolbar_panel), ("stats_panel", stats_panel), ("graph_panel", graph_panel)):
        if key in old_positions:
            x, y, collapsed = old_positions[key]
            panel.collapsed = collapsed
            panel.move_to(x, y, state.SCREEN_W, state.SCREEN_H)


# ---------------------------------------------------------------------
# Biểu đồ dân số theo thời gian (Panel nổi, kéo/thu gọn được)
# ---------------------------------------------------------------------
def draw_graph(state, surf):
    if not state.graph_visible:
        return
    panel = state.graph_panel
    panel.draw_frame(surf, state.font)
    if panel.collapsed or len(state.pop_history_main) < 2:
        return
    cx, cy = panel.content_pos()
    cw, ch = panel.w, panel.h

    max_val = max(max(state.pop_history_main, default=1), max(state.pop_history_rival, default=1), 5)
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

    # Chú giải màu (2 chấm nhỏ + nhãn) để không cần đoán đường nào là tổ nào
    legend_y = cy + 4
    pygame.draw.circle(surf, COL_MAIN, (cx + 10, legend_y + 5), 4)
    surf.blit(state.font_small.render("To chinh", True, COL_MAIN), (cx + 18, legend_y))
    pygame.draw.circle(surf, COL_RIVAL, (cx + 110, legend_y + 5), 4)
    surf.blit(state.font_small.render("Doi thu", True, COL_RIVAL), (cx + 118, legend_y))

    if len(state.pop_history_main) >= 2:
        pygame.draw.lines(surf, COL_MAIN, False, to_points(state.pop_history_main), 2)
    if len(state.pop_history_rival) >= 2:
        pygame.draw.lines(surf, COL_RIVAL, False, to_points(state.pop_history_rival), 2)


# ---------------------------------------------------------------------
# Bảng thống kê (Panel nổi) + nhãn tầng hiện tại (nhỏ, cố định góc trên phải)
# ---------------------------------------------------------------------
def _blit_row(surf, font, x, y, segments):
    """Vẽ 1 dòng gồm nhiều đoạn (text, color) NỐI TIẾP NHAU trên cùng 1
    dòng - dùng để nhãn mờ + giá trị sáng xen kẽ, dễ đọc hơn hẳn 1 màu
    trắng đồng nhất cho tất cả (không phân biệt được đâu là nhãn/giá trị)."""
    cur_x = x
    for text, color in segments:
        img = font.render(text, True, color)
        surf.blit(img, (cur_x, y))
        cur_x += img.get_width()
    return cur_x


def draw_hud(state, surf):
    colony, rival_colony, enemy = state.colony, state.rival_colony, state.enemy
    c = colony.counts()
    r = rival_colony.counts()

    main_invaded = np.any(rival_colony.alive & (rival_colony.state == cfg.STATE_RAID_LOOT))
    rival_invaded = np.any(colony.alive & (colony.state == cfg.STATE_RAID_LOOT))

    warnings = []  # (text, color)
    if c["is_starving"]:
        warnings.append(("*** DAN KIEN TO CHINH DANG DOI ***", COL_BAD))
    if c["is_dehydrated"]:
        warnings.append(("*** DAN KIEN TO CHINH DANG KHAT NUOC ***", (255, 175, 70)))
    if enemy.active:
        warnings.append(("*** CO KE THU TREN MAT DAT ***", (255, 210, 70)))
    if main_invaded:
        warnings.append(("*** TO CHINH DANG BI XAM CHIEM! ***", COL_BAD))
    if rival_invaded:
        warnings.append(("*** TO DOI THU DANG BI XAM CHIEM! ***", (255, 165, 90)))
    if c["raiders_out"] > 0:
        warnings.append((f"Dang cu {c['raiders_out']} quan xam chiem to doi thu", (255, 220, 120)))

    follow_text = state.follow_status_text()

    LINE_H = 22
    n_lines = 4 + len(warnings) + (1 if follow_text else 0) + 1  # +1 dong huong dan cuoi
    panel = state.stats_panel
    panel.h = max(90, LINE_H * n_lines + 14)
    panel.draw_frame(surf, state.font)
    if not panel.collapsed:
        cx, cy = panel.content_pos()
        LX = 10
        y = cy + 6

        # Dòng 1: TỔ CHÍNH
        _blit_row(surf, state.font_hud, cx + LX, y, [
            ("TO CHINH   ", COL_MAIN),
            ("Dan so ", COL_LABEL), (f"{c['population']}/{colony.n}    ", COL_VALUE),
            ("Linh ", COL_LABEL), (f"{c['soldiers']}    ", COL_VALUE),
            ("Gac ", COL_LABEL), (f"{c['guards_on_duty']}/{c['guards_total']}    ", COL_VALUE),
            ("Sinh ", COL_LABEL), (f"{c['total_births']}    ", COL_GOOD),
            ("Chet ", COL_LABEL), (f"{c['total_deaths']}", COL_BAD),
        ])
        y += LINE_H

        # Dòng 2: TỔ ĐỐI THỦ (cùng cấu trúc, đổi màu để so sánh nhanh)
        _blit_row(surf, state.font_hud, cx + LX, y, [
            ("TO DOI THU ", COL_RIVAL),
            ("Dan so ", COL_LABEL), (f"{r['population']}/{rival_colony.n}    ", COL_VALUE),
            ("Linh ", COL_LABEL), (f"{r['soldiers']}    ", COL_VALUE),
            ("Gac ", COL_LABEL), (f"{r['guards_on_duty']}/{r['guards_total']}    ", COL_VALUE),
            ("Sinh ", COL_LABEL), (f"{r['total_births']}    ", COL_GOOD),
            ("Chet ", COL_LABEL), (f"{r['total_deaths']}", COL_BAD),
        ])
        y += LINE_H + 4
        pygame.draw.line(surf, (70, 70, 78), (cx + LX, y - 2), (cx + panel.w - LX, y - 2), 1)

        # Dòng 3: Tài nguyên của TỔ CHÍNH (kho/nước/trứng/ấu trùng)
        _blit_row(surf, state.font_hud, cx + LX, y, [
            ("Kho ", COL_LABEL), (f"{c['food_in_storage']:.0f}    ", COL_FOOD),
            ("Nuoc ", COL_LABEL), (f"{c['water_in_storage']:.0f}    ", COL_WATER),
            ("Trung ", COL_LABEL), (f"{c['egg_count']} qua    ", COL_VALUE),
            ("Au trung ", COL_LABEL), (f"{c['larva_count']} con", COL_VALUE),
        ])
        y += LINE_H

        # Dòng 4: Số liệu xung đột (nghĩa địa/cướp được/kẻ thù bị giết)
        _blit_row(surf, state.font_hud, cx + LX, y, [
            ("Nghia dia ", COL_LABEL), (f"{c['corpse_count']:.0f} xac    ", COL_VALUE),
            ("Da cuop duoc ", COL_LABEL), (f"{c['total_food_looted']:.0f}    ", (255, 210, 120)),
            ("Ke thu da bi giet ", COL_LABEL), (f"{enemy.total_kills}", (255, 150, 150)),
        ])
        y += LINE_H

        for wtext, wcolor in warnings:
            bg = pygame.Surface((panel.w - 2 * LX, LINE_H - 2), pygame.SRCALPHA)
            bg.fill(COL_WARN_BG)
            surf.blit(bg, (cx + LX, y - 1))
            img = state.font_hud.render(wtext, True, wcolor)
            surf.blit(img, (cx + LX + 4, y))
            y += LINE_H

        if follow_text:
            bg = pygame.Surface((panel.w - 2 * LX, LINE_H - 2), pygame.SRCALPHA)
            bg.fill(COL_FOLLOW_BG)
            surf.blit(bg, (cx + LX, y - 1))
            img = state.font_hud.render(follow_text + "  - bam cho trong de ngung", True, COL_GOOD)
            surf.blit(img, (cx + LX + 4, y))
            y += LINE_H

        hint = "Ctrl+Lan chuot: doi tang | Lan chuot: zoom | Chuot phai+keo: di chuyen | Esc: thoat"
        img = state.font_small.render(hint, True, (135, 135, 145))
        surf.blit(img, (cx + LX, y + 2))

    # --- nhãn tầng hiện tại: nhỏ, LUÔN CỐ ĐỊNH góc trên-phải (không phải
    # panel kéo được - đủ nhỏ để không thực sự che khung nhìn, và cần luôn
    # nhìn thấy ngay để biết đang xem tầng nào dù các panel khác ở đâu) ---
    name = layer_name(state.current_layer)
    label = state.font_big.render(f"Tang {state.current_layer}: {name}", True, (255, 255, 80))
    lr = label.get_rect(topright=(state.SCREEN_W - 12, 8))
    bg = pygame.Surface((lr.w + 16, lr.h + 10), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 150))
    surf.blit(bg, (lr.x - 8, lr.y - 5))
    surf.blit(label, lr)


def draw_toolbar(state, surf):
    panel = state.toolbar_panel
    panel.draw_frame(surf, state.font)
    if panel.collapsed:
        return
    for b in panel.children:
        b.draw(surf, state.font)

    cx, cy = panel.content_pos()
    # Đường phân cách dọc giữa các NHÓM chức năng, để mắt tách nhóm nhanh
    # hơn nữa (ngoài việc đã phân biệt bằng màu) - "dat/dao/tha" | "xoa/
    # theo doi" | "thoi gian" ở hàng 1; "cong tac BAT-TAT" | "doi tang" ở
    # hàng 2.
    for rel_x in (504, 704):
        xline = cx + rel_x
        pygame.draw.line(surf, (75, 75, 85), (xline, cy + 4), (xline, cy + 38), 1)
    xline2 = cx + 712
    pygame.draw.line(surf, (75, 75, 85), (xline2, cy + 44), (xline2, cy + 72), 1)

    hint = "Chon cong cu, CLICK hoac GIU+KEO chuot trai de dung (tru Dao phong/Tha ke thu/Theo doi)"
    if state.current_tool == "follow":
        hint = "Theo doi: bam TRUNG 1 con kien de camera bam theo no (tu doi tang theo no luon) - bam cho TRONG de ngung"
    elif state.current_tool in ("food", "enemy", "dig", "rock", "water") and state.current_layer != 0:
        hint = "Cong cu nay chi dung duoc o Tang 0 (Mat dat) - doi tang bang Ctrl+Lan chuot"
    txt = state.font_small.render(hint, True, (255, 230, 90))
    surf.blit(txt, (cx + 6, cy + panel.h - 22))
