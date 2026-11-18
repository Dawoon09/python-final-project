"""행동 버튼(Button) 클래스가 들어 있는 파일."""

import pygame

import config


class Button:
    """화면에 보이는 행동 버튼 하나.

    위치·크기와 버튼 글자를 가지고, 클릭 판정과 쿨타임 표시를 맡는다.
    쿨타임 시간 자체는 Game이 관리하고, 버튼은 그리기 때 "지금 쿨타임 중인지"만 받는다.
    """

    def __init__(self, x, y, width, height, text):
        """버튼의 위치(x, y), 크기(width, height), 글자(text)를 저장한다."""
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text

    def is_clicked(self, pos):
        """마우스 위치 pos가 버튼 안이면 True, 밖이면 False를 돌려준다."""
        return bool(self.rect.collidepoint(pos))

    def draw(self, screen, font, cooling_down):
        """버튼을 그린다.

        평소에는 파란색, 쿨타임 중(cooling_down=True)이면 회색으로 칠하고
        검은 테두리와 가운데 흰 글자를 그린다.
        """
        if cooling_down:
            color = config.COLOR_GRAY
        else:
            color = config.COLOR_BUTTON
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, config.COLOR_BLACK, self.rect,
                         config.BUTTON_BORDER_WIDTH)

        text = font.render(self.text, True, config.COLOR_BUTTON_TEXT)
        text_rect = text.get_rect()
        text_rect.center = self.rect.center
        screen.blit(text, text_rect)
