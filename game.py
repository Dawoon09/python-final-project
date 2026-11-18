"""게임 전체(Game) 클래스가 들어 있는 파일."""

import sys

import pygame

import config
from student import Student


class Game:
    """메인 루프와 화면 전환(타이틀/게임/엔딩)을 맡는 클래스."""

    def __init__(self):
        """pygame을 켜고 800x600 창과 시계, 첫 상태를 준비한다."""
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.clock = pygame.time.Clock()

        self.running = True              # False가 되면 메인 루프가 끝난다
        self.state = config.STATE_TITLE  # 지금 보여 줄 화면
        self.student = Student()

    def handle_event(self, event):
        """이벤트 하나를 받아 처리한다.

        창 닫기(QUIT) 또는 ESC 키를 누르면 running을 False로 바꾼다.
        """
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.running = False

    def update(self, dt):
        """dt초만큼 게임 상태를 진행한다. (이후 단위에서 채운다)"""
        pass

    def draw(self):
        """현재 상태의 화면을 그린다. 지금은 배경색만 칠한다."""
        self.screen.fill(config.COLOR_BG)
        pygame.display.flip()

    def run(self):
        """메인 루프: 이벤트 처리 -> 업데이트 -> 그리기를 반복한다."""
        while self.running:
            # tick은 지난 프레임부터 흐른 밀리초를 돌려주므로 초로 바꾼다
            dt = self.clock.tick(config.FPS) / config.MS_PER_SECOND
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()
