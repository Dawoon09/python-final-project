"""행동 버튼(Button) 클래스와 도트(픽셀) 그리기 도우미 함수가 들어 있는 파일."""

import pygame

import config


# ----------------------------------------------------------------
# 도트 그리기 도우미 (모듈 함수)
# ----------------------------------------------------------------
def draw_cut_rect(screen, color, rect):
    """네 모서리를 도트 1칸씩 깎은(계단형) 사각형을 한 가지 색으로 칠한다."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(screen, color, rect.inflate(-config.BOX_INSET, config.NO_OFFSET))
    pygame.draw.rect(screen, color, rect.inflate(config.NO_OFFSET, -config.BOX_INSET))


def draw_pixel_box(screen, rect, fill, light=None, shadow=None, drop=None,
                   outline=config.COLOR_OUTLINE):
    """계단형 모서리 도트 상자를 그린다."""
    rect = pygame.Rect(rect)
    if drop is not None:
        draw_cut_rect(screen, drop, rect.move(config.NO_OFFSET, config.PIXEL_SIZE))
    draw_cut_rect(screen, outline, rect)
    inner = rect.inflate(-config.BOX_INSET, -config.BOX_INSET)
    pygame.draw.rect(screen, fill, inner)
    if light is not None:
        pygame.draw.rect(screen, light,
                         (inner.left, inner.top, inner.width, config.PIXEL_SIZE))
    if shadow is not None:
        pygame.draw.rect(screen, shadow,
                         (inner.left, inner.bottom - config.PIXEL_SIZE,
                          inner.width, config.PIXEL_SIZE))
    return inner


def draw_sprite(screen, grid, x, y, cell, colors):
    """문자열 격자 스프라이트를 (x, y)부터 칸 크기 cell로 찍는다."""
    for row_index, row in enumerate(grid):
        for col_index, char in enumerate(row):
            color = colors.get(char)
            if color is None:
                continue
            pygame.draw.rect(screen, color,
                             (x + col_index * cell, y + row_index * cell, cell, cell))


def sprite_size(grid, cell):
    """스프라이트 grid를 칸 크기 cell로 찍었을 때의 (가로, 세로) 픽셀 크기를 돌려준다."""
    return len(grid[config.FIRST_ROW]) * cell, len(grid) * cell


def render_text(font, text, color=config.COLOR_TEXT):
    """글자를 도트 느낌이 나도록 안티에일리어싱 없이(antialias=False) 그린 Surface를 돌려준다."""
    return font.render(text, False, color)


def draw_progress_bar(screen, inner, progress):
    """사각형 inner 맨 아래에 진행 막대(자동 행동·입력 대기)를 도트 단위로 그린다."""
    track = pygame.Rect(inner.left, inner.bottom - config.COOLDOWN_BAR_HEIGHT,
                        inner.width, config.COOLDOWN_BAR_HEIGHT)
    pygame.draw.rect(screen, config.COLOR_COOLDOWN_TRACK, track)
    cells = int(track.width * progress) // config.PIXEL_SIZE
    pygame.draw.rect(screen, config.COLOR_COOLDOWN_FILL,
                     (track.left, track.top, cells * config.PIXEL_SIZE, track.height))


# ----------------------------------------------------------------
# Button 클래스
# ----------------------------------------------------------------
class Button:
    """화면에 보이는 버튼 하나(일과표 방침 버튼, 대화창 선택 버튼)."""

    def __init__(self, x, y, width, height, text):
        """버튼의 위치(x, y), 크기(width, height), 글자(text)를 저장한다."""
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text

    def is_clicked(self, pos):
        """마우스 위치 pos가 버튼 안이면 True, 밖이면 False를 돌려준다."""
        return bool(self.rect.collidepoint(pos))

    def get_colors(self, cooling_down):
        """버튼 색 묶음 (몸통, 위 하이라이트, 아래 그림자, 글자)을 돌려준다."""
        if cooling_down:
            return (config.COLOR_GRAY, config.COLOR_GRAY_LIGHT,
                    config.COLOR_GRAY_DARK, config.COLOR_BUTTON_TEXT_COOL)
        return (config.COLOR_BUTTON, config.COLOR_BUTTON_LIGHT,
                config.COLOR_BUTTON_DARK, config.COLOR_BUTTON_TEXT)

    def draw(self, screen, font, cooling_down, hovered=False, press_offset=config.NO_OFFSET,
             cooldown_progress=None, selected=False):
        """버튼을 도트 상자로 그린다."""
        fill, light, shadow, text_color = self.get_colors(cooling_down)
        if selected and not cooling_down:
            fill = config.COLOR_POLICY_SELECTED
            light = config.COLOR_POLICY_SELECTED_LIGHT
            shadow = config.COLOR_POLICY_SELECTED_DARK
        elif hovered and not cooling_down:
            fill = config.COLOR_BUTTON_BRIGHT
        # 받침은 원래 자리에, 몸통은 press_offset 만큼 내려서 그린다
        draw_cut_rect(screen, config.COLOR_OUTLINE,
                      self.rect.move(config.NO_OFFSET, config.PIXEL_SIZE))
        body = self.rect.move(config.NO_OFFSET, press_offset)
        inner = draw_pixel_box(screen, body, fill, light, shadow)
        text = render_text(font, self.text, text_color)
        text_rect = text.get_rect()
        text_rect.center = inner.center
        screen.blit(text, text_rect)
        if cooldown_progress is not None:
            draw_progress_bar(screen, inner, cooldown_progress)
