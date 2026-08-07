"""Widget UI đơn giản dùng chung cho thanh công cụ (pygame.Rect + text).

Tách riêng khỏi main.py vì đây là tiện ích UI thuần túy, không phụ thuộc
world/colony - có thể tái sử dụng cho các panel khác nếu cần.
"""
import pygame

COLOR_BTN = (40, 40, 45)
COLOR_BTN_ACTIVE = (70, 130, 180)


class Button:
    def __init__(self, rect, text, on_click=None, toggle=False, active=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.toggle = toggle
        self.active = active

    def draw(self, surf, font):
        color = COLOR_BTN_ACTIVE if self.active else COLOR_BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=5)
        pygame.draw.rect(surf, (90, 90, 100), self.rect, width=1, border_radius=5)
        label = font.render(self.text, True, (240, 240, 240))
        lr = label.get_rect(center=self.rect.center)
        surf.blit(label, lr)

    def handle_click(self, pos):
        if self.rect.collidepoint(pos):
            if self.on_click:
                self.on_click()
            return True
        return False
