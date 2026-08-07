"""HUD: biểu đồ dân số, bảng thống kê, thanh công cụ - đều là các "cửa sổ"
(Panel) NỔI TRÊN màn hình mô phỏng: KÉO DI CHUYỂN được và THU GỌN được, để
người chơi tự sắp xếp sao cho không bị che mất khung nhìn đàn kiến (xem
ui_widgets.Panel).

Thanh công cụ trình bày dạng SIDEBAR (bảng cạnh) - các nút xếp DỌC thành 1
cột duy nhất, chia theo từng NHÓM có nhãn tiêu đề riêng, thay vì xếp thành
2 hàng ngang như bản trước - dễ đọc/dễ quét mắt hơn khi số lượng nút nhiều.

Bảng thống kê hiển thị ĐẦY ĐỦ số liệu cho CẢ 2 TỔ (chính lẫn đối thủ) với
cấu trúc HOÀN TOÀN GIỐNG NHAU (dân số/quân số, tài nguyên, tổn thất) để so
sánh trực tiếp 2 tổ, thay vì trước đây chỉ tổ chính có đủ số liệu tài
nguyên/tổn thất còn tổ đối thủ chỉ có mỗi dòng dân số."""
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
COL_SECTION = (150, 155, 165)    # nhãn tiêu đề nhóm trong sidebar công cụ


def build_toolbar(state):
    """Tạo 3 Panel nổi: SIDEBAR công cụ (dọc, bên phải), bảng thống kê
    (trên-trái), biểu đồ (dưới-trái). Nếu state đã có sẵn panel từ trước
    (vd đang resize cửa sổ), GIỮ NGUYÊN vị trí/trạng thái thu gọn người
    chơi đã tự sắp xếp thay vì đặt lại về mặc định."""
    old_positions = {}
    for key in ("toolbar_panel", "stats_panel", "graph_panel"):
        p = getattr(state, key, None)
        if p is not None:
            old_positions[key] = (p.x, p.y, p.collapsed)

    state.buttons = []
    state.tool_buttons = []

    SIDEBAR_W = 232
    toolbar_panel = Panel(state.SCREEN_W - SIDEBAR_W - 10, 8, SIDEBAR_W, 10, "Cong cu")
    stats_panel = Panel(8, 8, 700, 150, "Thong tin dan kien (2 to)")
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
    add_section("CONG TAC BAT/TAT")
    respawn_btn = add_full_button("Tai sinh thuc an: BAT", None, "toggle", active=True, h=26)
    grid_btn = add_full_button("Luoi o vuong: BAT", None, "toggle", active=True, h=26)
    graph_btn = add_full_button("Bieu do: HIEN", None, "toggle", active=True, h=26)
    enemy_spawn_btn = add_full_button("Ke thu tu nhien: BAT", None, "toggle", active=True, h=26)
    respawn_btn.on_click = lambda: state.toggle_respawn(respawn_btn)
    grid_btn.on_click = lambda: state.toggle_grid(grid_btn)
    graph_btn.on_click = lambda: state.toggle_graph(graph_btn)
    enemy_spawn_btn.on_click = lambda: state.toggle_enemy_spawn(enemy_spawn_btn)

    cursor["y"] += 4
    add_section("DI CHUYEN TANG")
    layer_up_btn, layer_down_btn = add_half_buttons(
        "Tang ^", lambda: (state.stop_follow(), state.change_layer(-1)), "nav",
        "Tang v", lambda: (state.stop_follow(), state.change_layer(1)), "nav")

    cursor["y"] += 6  # chỗ cho dòng gợi ý cuối cùng (vẽ trong draw_toolbar)
    toolbar_panel.h = cursor["y"] + 18

    state.toolbar_panel = toolbar_panel
    state.toolbar_section_labels = section_labels
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
    """Vẽ 1 dòng gồm nhiều đoạn (text, color) NỐI TIẾP NHAU - nhãn mờ + giá
    trị sáng xen kẽ, dễ đọc hơn hẳn 1 màu trắng đồng nhất."""
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
    if r["is_starving"]:
        warnings.append(("*** DAN KIEN TO DOI THU DANG DOI ***", COL_BAD))
    if r["is_dehydrated"]:
        warnings.append(("*** DAN KIEN TO DOI THU DANG KHAT NUOC ***", (255, 175, 70)))
    if enemy.active:
        warnings.append(("*** CO KE THU TREN MAT DAT ***", (255, 210, 70)))
    if main_invaded:
        warnings.append(("*** TO CHINH DANG BI XAM CHIEM! ***", COL_BAD))
    if rival_invaded:
        warnings.append(("*** TO DOI THU DANG BI XAM CHIEM! ***", (255, 165, 90)))
    if c["raiders_out"] > 0:
        warnings.append((f"To chinh dang cu {c['raiders_out']} quan di xam chiem", (255, 220, 120)))
    if r["raiders_out"] > 0:
        warnings.append((f"To doi thu dang cu {r['raiders_out']} quan di xam chiem", (255, 220, 120)))

    follow_text = state.follow_status_text()

    LINE_H = 22
    # 3 dong/to (dan so, tai nguyen, ton that) x 2 to + 1 dong ke thu chung
    n_lines = 3 + 3 + 1 + len(warnings) + (1 if follow_text else 0) + 1
    panel = state.stats_panel
    panel.h = max(90, LINE_H * n_lines + 20)
    panel.draw_frame(surf, state.font)
    if not panel.collapsed:
        cx, cy = panel.content_pos()
        LX = 10
        y = [cy + 6]  # dùng list để sửa được trong hàm lồng bên dưới

        def colony_block(label, accent, cdata, cobj):
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
                ("Au trung ", COL_LABEL), (f"{cdata['larva_count']} con", COL_VALUE),
            ])
            y[0] += LINE_H
            _blit_row(surf, state.font_hud, cx + LX + 18, y[0], [
                ("Nghia dia ", COL_LABEL), (f"{cdata['corpse_count']:.0f} xac    ", COL_VALUE),
                ("Da cuop duoc ", COL_LABEL), (f"{cdata['total_food_looted']:.0f}", (255, 210, 120)),
            ])
            y[0] += LINE_H

        colony_block("TO CHINH", COL_MAIN, c, colony)
        y[0] += 3
        pygame.draw.line(surf, (70, 70, 78), (cx + LX, y[0]), (cx + panel.w - LX, y[0]), 1)
        y[0] += 5
        colony_block("TO DOI THU", COL_RIVAL, r, rival_colony)

        y[0] += 3
        pygame.draw.line(surf, (70, 70, 78), (cx + LX, y[0]), (cx + panel.w - LX, y[0]), 1)
        y[0] += 5

        # Kẻ thù ngoài tự nhiên là 1 thực thể DUY NHẤT DÙNG CHUNG cho cả
        # bản đồ (không thuộc riêng tổ nào) nên hiển thị 1 dòng riêng
        _blit_row(surf, state.font_hud, cx + LX, y[0], [
            ("Ke thu tren mat dat ", COL_LABEL),
            ("CO" if enemy.active else "KHONG", (255, 210, 70) if enemy.active else COL_VALUE),
            ("    Tong so da bi kien giet ", COL_LABEL), (f"{enemy.total_kills}", (255, 150, 150)),
        ])
        y[0] += LINE_H

        for wtext, wcolor in warnings:
            bg = pygame.Surface((panel.w - 2 * LX, LINE_H - 2), pygame.SRCALPHA)
            bg.fill(COL_WARN_BG)
            surf.blit(bg, (cx + LX, y[0] - 1))
            img = state.font_hud.render(wtext, True, wcolor)
            surf.blit(img, (cx + LX + 4, y[0]))
            y[0] += LINE_H

        if follow_text:
            bg = pygame.Surface((panel.w - 2 * LX, LINE_H - 2), pygame.SRCALPHA)
            bg.fill(COL_FOLLOW_BG)
            surf.blit(bg, (cx + LX, y[0] - 1))
            img = state.font_hud.render(follow_text, True, COL_GOOD)
            surf.blit(img, (cx + LX + 4, y[0]))
            y[0] += LINE_H

        hint = "Ctrl+Lan chuot: doi tang | Lan chuot: zoom | Chuot phai+keo: di chuyen | Esc: thoat"
        img = state.font_small.render(hint, True, (135, 135, 145))
        surf.blit(img, (cx + LX, y[0] + 2))

    # --- nhãn tầng hiện tại: nhỏ, LUÔN CỐ ĐỊNH góc trên-phải (không phải
    # panel kéo được - đủ nhỏ để không thực sự che khung nhìn) ---
    name = layer_name(state.current_layer)
    label = state.font_big.render(f"Tang {state.current_layer}: {name}", True, (255, 255, 80))
    lr = label.get_rect(topright=(state.SCREEN_W - 12, 8))
    bg = pygame.Surface((lr.w + 16, lr.h + 10), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 150))
    surf.blit(bg, (lr.x - 8, lr.y - 5))
    surf.blit(label, lr)


def draw_toolbar(state, surf):
    """Vẽ SIDEBAR công cụ: khung + nhãn từng nhóm (CONG CU/THOI GIAN/CONG
    TAC/DI CHUYEN TANG) + toàn bộ nút (xếp dọc) + dòng gợi ý cuối cùng."""
    panel = state.toolbar_panel
    panel.draw_frame(surf, state.font)
    if panel.collapsed:
        return
    cx, cy = panel.content_pos()

    for text, rel_y in state.toolbar_section_labels:
        img = state.font_small.render(text, True, COL_SECTION)
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
        img = state.font_small.render(line, True, (255, 230, 90))
        surf.blit(img, (cx + 10, hy))
        hy += 16
