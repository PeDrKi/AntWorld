"""HUD: biểu đồ dân số, bảng thống kê, thanh công cụ - giờ đều là các
"cửa sổ" (Panel) NỔI TRÊN màn hình mô phỏng: KÉO DI CHUYỂN được tới bất kỳ
đâu và THU GỌN được lại, để người chơi tự sắp xếp sao cho không bị che mất
khung nhìn đàn kiến (xem ui_widgets.Panel)."""
import numpy as np
import pygame

import config as cfg
from ui_widgets import Button, Panel
from render_underground import layer_name


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

    toolbar_panel = Panel(10, state.SCREEN_H - 150, 932, 104, "Dieu khien / Cong cu")
    stats_panel = Panel(8, 8, 900, 110, "Thong ke dan kien")
    graph_panel = Panel(state.SCREEN_W - 332, 54, 310, 178, "Dan so theo thoi gian")

    def make_tool_button(label, tool_name, rel_x, rel_y, w=96, h=30):
        b = Button((0, 0, w, h), label, on_click=lambda: state.set_tool(tool_name))
        b.text_tool = tool_name
        state.tool_buttons.append(b)
        state.buttons.append(b)
        b.bind_to_panel(toolbar_panel, rel_x, rel_y)
        return b

    rx = 6
    for label, tool_name in [
        ("Dat thuc an", "food"), ("Tha ke thu", "enemy"), ("Dao phong", "dig"),
        ("Dat da", "rock"), ("Dat nuoc", "water"), ("Xoa", "erase"), ("Theo doi", "follow"),
    ]:
        make_tool_button(label, tool_name, rx, 6)
        rx += 100

    pause_btn = Button((0, 0, 90, 30), "Tam dung")
    speed_btn = Button((0, 0, 90, 30), "Toc do: x1")
    pause_btn.on_click = lambda: state.toggle_pause(pause_btn)
    speed_btn.on_click = lambda: state.cycle_speed(speed_btn)
    pause_btn.bind_to_panel(toolbar_panel, rx + 10, 6)
    speed_btn.bind_to_panel(toolbar_panel, rx + 108, 6)
    state.buttons += [pause_btn, speed_btn]

    respawn_btn = Button((0, 0, 190, 26), "Tai sinh thuc an: BAT", active=True)
    grid_btn = Button((0, 0, 150, 26), "Luoi o vuong: BAT", active=True)
    graph_btn = Button((0, 0, 130, 26), "Bieu do: HIEN", active=True)
    enemy_spawn_btn = Button((0, 0, 200, 26), "Ke thu tu nhien: BAT", active=True)
    layer_up_btn = Button((0, 0, 60, 26), "Tang ^")
    layer_down_btn = Button((0, 0, 60, 26), "Tang v")

    respawn_btn.on_click = lambda: state.toggle_respawn(respawn_btn)
    grid_btn.on_click = lambda: state.toggle_grid(grid_btn)
    graph_btn.on_click = lambda: state.toggle_graph(graph_btn)
    enemy_spawn_btn.on_click = lambda: state.toggle_enemy_spawn(enemy_spawn_btn)
    layer_up_btn.on_click = lambda: (state.stop_follow(), state.change_layer(-1))
    layer_down_btn.on_click = lambda: (state.stop_follow(), state.change_layer(1))

    respawn_btn.bind_to_panel(toolbar_panel, 6, 44)
    grid_btn.bind_to_panel(toolbar_panel, 204, 44)
    graph_btn.bind_to_panel(toolbar_panel, 362, 44)
    enemy_spawn_btn.bind_to_panel(toolbar_panel, 500, 44)
    layer_up_btn.bind_to_panel(toolbar_panel, 712, 44)
    layer_down_btn.bind_to_panel(toolbar_panel, 780, 44)
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
    panel.draw_frame(surf, state.font_small)
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

    if len(state.pop_history_main) >= 2:
        pygame.draw.lines(surf, (60, 60, 65), False, to_points(state.pop_history_main), 2)
    if len(state.pop_history_rival) >= 2:
        pygame.draw.lines(surf, (220, 80, 65), False, to_points(state.pop_history_rival), 2)


# ---------------------------------------------------------------------
# Bảng thống kê (Panel nổi) + nhãn tầng hiện tại (nhỏ, cố định góc trên phải)
# ---------------------------------------------------------------------
def draw_hud(state, surf):
    colony, rival_colony, enemy = state.colony, state.rival_colony, state.enemy
    c = colony.counts()
    r = rival_colony.counts()
    canh_bao = "  *** DAN KIEN DANG DOI ***" if c["is_starving"] else ""
    khat = "  *** DAN KIEN DANG KHAT NUOC ***" if c["is_dehydrated"] else ""
    ke_thu = "  *** CO KE THU TREN MAT DAT ***" if enemy.active else ""
    # "Bị xâm chiếm" của 1 tổ = tổ ĐỐI PHƯƠNG đang có quân ở trạng thái
    # cướp phá (STATE_RAID_LOOT) - phải tra chéo sang counts() của bên kia
    main_invaded = np.any(rival_colony.alive & (rival_colony.state == cfg.STATE_RAID_LOOT))
    rival_invaded = np.any(colony.alive & (colony.state == cfg.STATE_RAID_LOOT))
    xam_chiem = ""
    if main_invaded:
        xam_chiem += "  *** TO CHINH DANG BI XAM CHIEM ***"
    if c["raiders_out"] > 0:
        xam_chiem += f"  (dang cu {c['raiders_out']} quan di xam chiem doi thu)"
    if rival_invaded:
        xam_chiem += "  *** TO DOI THU DANG BI XAM CHIEM ***"
    lines = [
        f"TO CHINH - Dan so: {c['population']} (toi da {colony.n}, linh: {c['soldiers']}, "
        f"gac: {c['guards_on_duty']}/{c['guards_total']})   Sinh: {c['total_births']}  Chet: {c['total_deaths']}",
        f"TO DOI THU - Dan so: {r['population']} (toi da {rival_colony.n}, linh: {r['soldiers']}, "
        f"gac: {r['guards_on_duty']}/{r['guards_total']})   Sinh: {r['total_births']}  Chet: {r['total_deaths']}",
        f"Kho: {c['food_in_storage']:.0f}  Nuoc: {c['water_in_storage']:.0f}  "
        f"Trung: {c['egg_count']} qua  Au trung: {c['larva_count']} con  "
        f"Nghia dia: {c['corpse_count']:.0f} xac  Da cuop duoc: {c['total_food_looted']:.0f}  "
        f"Ke thu da giet: {enemy.total_kills}"
        f"{canh_bao}{khat}{ke_thu}{xam_chiem}",
        "Ctrl+Lan chuot: doi tang | Lan chuot: zoom | Chuot phai+keo: di chuyen | Esc: thoat",
    ]
    follow_text = state.follow_status_text()
    if follow_text:
        lines.append(follow_text + "  (bam vao cho trong de ngung theo doi)")

    panel = state.stats_panel
    panel.h = max(70, 20 * len(lines) + 8)  # co gian theo so dong (vd luc dang theo doi kien)
    panel.draw_frame(surf, state.font_small)
    if not panel.collapsed:
        cx, cy = panel.content_pos()
        for i, line in enumerate(lines):
            txt = state.font_hud.render(line, True, (255, 255, 255))
            surf.blit(txt, (cx + 6, cy + 4 + i * 20))

    # --- nhãn tầng hiện tại: nhỏ, LUÔN CỐ ĐỊNH góc trên-phải (không phải
    # panel kéo được - đủ nhỏ để không thực sự che khung nhìn, và cần luôn
    # nhìn thấy ngay để biết đang xem tầng nào dù các panel khác ở đâu) ---
    name = layer_name(state.current_layer)
    label = state.font_big.render(f"Tang {state.current_layer}: {name}", True, (255, 255, 80))
    lr = label.get_rect(topright=(state.SCREEN_W - 12, 8))
    bg = pygame.Surface((lr.w + 16, lr.h + 10), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 140))
    surf.blit(bg, (lr.x - 8, lr.y - 5))
    surf.blit(label, lr)


def draw_toolbar(state, surf):
    panel = state.toolbar_panel
    panel.draw_frame(surf, state.font_small)
    if panel.collapsed:
        return
    for b in panel.children:
        b.draw(surf, state.font)

    hint = "Chon cong cu, CLICK hoac GIU+KEO chuot trai de dung (tru Dao phong/Tha ke thu/Theo doi)"
    if state.current_tool == "follow":
        hint = "Theo doi: bam TRUNG 1 con kien de camera bam theo no (tu doi tang theo no luon) - bam cho TRONG de ngung"
    elif state.current_tool in ("food", "enemy", "dig", "rock", "water") and state.current_layer != 0:
        hint = "Cong cu nay chi dung duoc o Tang 0 (Mat dat) - doi tang bang Ctrl+Lan chuot"
    cx, cy = panel.content_pos()
    txt = state.font_small.render(hint, True, (255, 230, 90))
    surf.blit(txt, (cx + 6, cy + panel.h - 22))
