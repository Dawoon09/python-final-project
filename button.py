"""행동 버튼(Button) 클래스와 도트(픽셀) 그리기 도우미 함수가 들어 있는 파일.

클래스는 Student, Button, Game 3개만 쓰기로 했으므로, 여러 화면 요소가 함께 쓰는
도트 그리기 도우미는 새 파일을 만들지 않고 이 파일의 모듈 함수로 둔다.
(Student와 Game은 `from button import ...`로 가져다 쓴다.)

도트 1칸 = config.PIXEL_SIZE x config.PIXEL_SIZE 사각형이다.
"""

import pygame

import config


# ----------------------------------------------------------------
# 도트 그리기 도우미 (모듈 함수)
# ----------------------------------------------------------------
def draw_cut_rect(screen, color, rect):
    """네 모서리를 도트 1칸씩 깎은(계단형) 사각형을 한 가지 색으로 칠한다.

    가로로 긴 사각형(좌우 1칸 안쪽)과 세로로 긴 사각형(위아래 1칸 안쪽)을 겹쳐
    그리면 모서리 1칸만 비어서 도트 게임의 둥근 상자 모양이 된다.
    """
    rect = pygame.Rect(rect)
    pygame.draw.rect(screen, color, rect.inflate(-config.BOX_INSET, config.NO_OFFSET))
    pygame.draw.rect(screen, color, rect.inflate(config.NO_OFFSET, -config.BOX_INSET))


def draw_pixel_box(screen, rect, fill, light=None, shadow=None, drop=None,
                   outline=config.COLOR_OUTLINE):
    """계단형 모서리 도트 상자를 그린다.

    - drop: 상자 아래로 도트 1칸 내려 그리는 그림자 색(없으면 생략)
    - outline: 바깥 테두리(도트 1칸) 색
    - fill: 안쪽 색. 안쪽 사각형은 rect에서 사방으로 도트 1칸씩 들어간 곳이다.
    - light / shadow: 안쪽 맨 위 줄(밝은 색) / 맨 아래 줄(어두운 색). 입체감용, 없으면 생략
    안쪽 사각형(pygame.Rect)을 돌려주므로 그 안에 글자나 막대를 그릴 수 있다.
    """
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
    """문자열 격자 스프라이트를 (x, y)부터 칸 크기 cell로 찍는다.

    grid는 문자열 리스트(한 줄 = 한 행)이고, 글자 하나가 도트 한 칸이다.
    colors는 {글자: 색} 사전이며, 사전에 없는 글자(예: ".")는 투명으로 보고 건너뛴다.
    """
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
    """사각형 inner 맨 아래에 진행 막대(자동 행동·입력 대기)를 도트 단위로 그린다.

    회색 홈 위에 하늘색이 왼쪽부터 progress(0~1) 비율만큼 찬다.
    길이는 PIXEL_SIZE 단위로 끊어서 한 칸씩 차오르는 도트 느낌을 낸다.
    (Button 클래스의 메서드를 늘리지 않으려고 모듈 함수로 둔다.)
    """
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
    """화면에 보이는 버튼 하나(일과표 방침 버튼, 대화창 선택 버튼).

    위치·크기와 버튼 글자를 가지고, 클릭 판정과 그리기(회색·호버·선택 강조·진행 막대)를 맡는다.
    시간과 방침 자체는 Game이 관리하고, 버튼은 그리기 때 보여 줄 상태만 받는다.
    """

    def __init__(self, x, y, width, height, text):
        """버튼의 위치(x, y), 크기(width, height), 글자(text)를 저장한다."""
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text

    def is_clicked(self, pos):
        """마우스 위치 pos가 버튼 안이면 True, 밖이면 False를 돌려준다."""
        return bool(self.rect.collidepoint(pos))

    def get_colors(self, cooling_down):
        """버튼 색 묶음 (몸통, 위 하이라이트, 아래 그림자, 글자)을 돌려준다.

        평소에는 하늘색 계열, 회색 차례(cooling_down=True, 대화창 입력 대기 중)면 회색 계열이다.
        """
        if cooling_down:
            return (config.COLOR_GRAY, config.COLOR_GRAY_LIGHT,
                    config.COLOR_GRAY_DARK, config.COLOR_BUTTON_TEXT_COOL)
        return (config.COLOR_BUTTON, config.COLOR_BUTTON_LIGHT,
                config.COLOR_BUTTON_DARK, config.COLOR_BUTTON_TEXT)

    def draw(self, screen, font, cooling_down, hovered=False, press_offset=config.NO_OFFSET,
             cooldown_progress=None, selected=False):
        """버튼을 도트 상자로 그린다.

        버튼 아래에 남색 받침(도트 1칸)을 깔고, 계단형 모서리 + 남색 외곽선 +
        위 하이라이트 / 아래 그림자 줄로 입체감을 준 뒤 가운데에 글자를 쓴다.
        cooling_down이 True(대화창 입력 대기 중)면 몸통이 회색 계열로 바뀐다.
        - hovered: 마우스가 버튼 위에 있으면 True. 회색이 아닐 때만 몸통을 밝은 색으로 칠한다.
        - press_offset: 버튼 몸통을 아래로 내려 그릴 거리(픽셀). 받침은 제자리에 있으므로
          4픽셀 내려가면 받침 위에 딱 붙어 "눌린" 것처럼 보인다.
        - cooldown_progress: 0~1. 주어지면 버튼 안쪽 맨 아래에 진행 막대를 그린다
          (대화창 선택 버튼의 입력 대기 표시에 쓴다).
        - selected: 지금 고른 일과표 방침 버튼이면 True. 몸통을 노랑 계열로 밝게 강조한다
          (반투명 없이 색만 바꾼다). 호버보다 우선한다.
        """
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
