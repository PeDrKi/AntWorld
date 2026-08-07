"""HUD: biểu đồ dân số, bảng thống kê góc trên trái, thanh công cụ dưới
màn hình - cùng với hàm dựng (build) và nối (wire) các nút bấm vào GameState."""
import numpy as np
import pygame

import config as cfg
from ui_widgets import Button
from render_underground import layer_name


def build_toolbar(state):
    """Tạo toàn bộ nút bấm của thanh công cụ và nối callback vào state.
    Điền kết quả vào state.buttons / state.tool_buttons."""
    row1_y = cfg.SCREEN_H - cfg.TOOLBAR_H + 6
    row2_y = row1_y + 38

    def make_tool_button(label, tool_name, x, y, w=108, h=30):
        b = Button((x, y, w, h), label, on_click=lambda: state.set_tool(tool_name))
        b.text_tool = tool_name
        state.tool_buttons.append(b)
        state.buttons.append(b)
        return b

    x = 10
    for label, tool_name in [
        ("Dat thuc an", "food"), ("Tha ke thu", "enemy"), ("Dao phong", "dig"),
        ("Dat da", "rock"), ("Dat nuoc", "water"), ("Xoa", "erase"),
    ]:
        make_tool_button(label, tool_name, x, row1_y)
        x += 114

    pause_btn = Button((x + 10, row1_y, 90, 30), "Tam dung")
    speed_btn = Button((x + 108, row1_y, 90, 30), "Toc do: x1")
    pause_btn.on_click = lambda: state.toggle_pause(pause_btn)
    speed_btn.on_click = lambda: state.cycle_speed(speed_btn)
    state.buttons += [pause_btn, speed_btn]

    respawn_btn = Button((10, row2_y, 190, 26), "Tai sinh thuc an: BAT", active=True)
    grid_btn = Button((208, row2_y, 150, 26), "Luoi o vuong: BAT", active=True)
    graph_btn = Button((366, row2_y, 130, 26), "Bieu do: HIEN", active=True)
    enemy_spawn_btn = Button((504, row2_y, 200, 26), "Ke thu tu nhien: BAT", active=True)
    layer_up_btn = Button((cfg.SCREEN_W - 150, row2_y, 60, 26), "Tang ^")
    layer_down_btn = Button((cfg.SCREEN_W - 84, row2_y, 60, 26), "Tang v")

    respawn_btn.on_click = lambda: state.toggle_respawn(respawn_btn)
    grid_btn.on_click = lambda: state.toggle_grid(grid_btn)
    graph_btn.on_click = lambda: state.toggle_graph(graph_btn)
    enemy_spawn_btn.on_click = lambda: state.toggle_enemy_spawn(enemy_spawn_btn)
    layer_up_btn.on_click = lambda: state.change_layer(-1)
    layer_down_btn.on_click = lambda: state.change_layer(1)
    state.buttons += [respawn_btn, grid_btn, graph_btn, enemy_spawn_btn, layer_up_btn, layer_down_btn]


# ---------------------------------------------------------------------
# Biểu đồ dân số theo thời gian (panel góc phải trên)
# ---------------------------------------------------------------------
def draw_graph(state, surf):
    if not state.graph_visible or len(state.pop_history_main) < 2:
        return
    panel_x = cfg.SCREEN_W - cfg.GRAPH_PANEL_W - 12
    panel_y = 12
    panel = pygame.Rect(panel_x, panel_y, cfg.GRAPH_PANEL_W, cfg.GRAPH_PANEL_H)
    s = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
    s.fill((0, 0, 0, 130))
    surf.blit(s, panel.topleft)
    title = state.font_small.render("Dan so theo thoi gian", True, (255, 255, 255))
    surf.blit(title, (panel_x + 8, panel_y + 6))

    max_val = max(max(state.pop_history_main, default=1), max(state.pop_history_rival, default=1), 5)
    pad = 10
    gx0, gx1 = panel_x + pad, panel_x + panel.w - pad
    gy0, gy1 = panel_y + panel.h - pad, panel_y + 26

    def to_points(hist):
        pts = []
        for i, v in enumerate(hist):
            t = i / max(1, cfg.HISTORY_MAX_POINTS - 1)
            x = gx0 + t * (gx1 - gx0)
            y = gy0 - min(1.0, v / max_val) * (gy0 - gy1)
            pts.append((x, y))
        return pts

    if len(state.pop_history_main) >= 2:
        pygame.draw.lines(surf, (30, 30, 30), False, to_points(state.pop_history_main), 2)
    if len(state.pop_history_rival) >= 2:
        pygame.draw.lines(surf, (200, 60, 50), False, to_points(state.pop_history_rival), 2)


# ---------------------------------------------------------------------
# HUD (góc trên trái) + nhãn tầng hiện tại (góc trên phải)
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
    panel = pygame.Surface((900, 20 * len(lines) + 10), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 140))
    surf.blit(panel, (8, 8))
    for i, line in enumerate(lines):
        txt = state.font_hud.render(line, True, (255, 255, 255))
        surf.blit(txt, (14, 12 + i * 20))

    # --- nhãn tầng hiện tại, to, dễ thấy ---
    name = layer_name(state.current_layer)
    label = state.font_big.render(f"Tang {state.current_layer}: {name}", True, (255, 255, 80))
    lr = label.get_rect(topright=(cfg.SCREEN_W - 12, 8))
    bg = pygame.Surface((lr.w + 16, lr.h + 10), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 140))
    surf.blit(bg, (lr.x - 8, lr.y - 5))
    surf.blit(label, lr)


def draw_toolbar(state, surf):
    pygame.draw.rect(surf, (22, 22, 26), (0, cfg.SCREEN_H - cfg.TOOLBAR_H, cfg.SCREEN_W, cfg.TOOLBAR_H))
    for b in state.buttons:
        b.draw(surf, state.font)
    hint = "Chon cong cu, CLICK hoac GIU+KEO chuot trai de dung (tru Dao phong/Tha ke thu)"
    if state.current_tool in ("food", "enemy", "dig", "rock", "water") and state.current_layer != 0:
        hint = "Cong cu nay chi dung duoc o Tang 0 (Mat dat) - doi tang bang Ctrl+Lan chuot"
    txt = state.font_small.render(hint, True, (255, 230, 90))
    surf.blit(txt, (10, cfg.SCREEN_H - 18))
