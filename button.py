"""행동 버튼(Button) 클래스가 들어 있는 파일."""

import pygame


class Button:
    """화면에 보이는 행동 버튼 하나.

    위치·크기와 버튼 글자를 가지고, 클릭 판정과 쿨타임 표시를 맡는다.
    """

    def __init__(self, x, y, width, height, text):
        """버튼의 위치(x, y), 크기(width, height), 글자(text)를 저장한다."""
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text

    def is_clicked(self, pos):
        """마우스 위치 pos가 버튼 안이면 True를 돌려준다. (3일차에 구현)"""
        pass

    def draw(self, screen, font, cooling_down):
        """버튼을 그린다. 쿨타임 중이면 회색으로 그린다. (3일차에 구현)"""
        pass
