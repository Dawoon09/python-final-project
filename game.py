"""게임 전체(Game) 클래스가 들어 있는 파일."""

import sys

import pygame

import config
from button import Button
from student import Student

# 키보드 단축키 -> 행동 이름 (윗줄 숫자키와 숫자패드 모두 허용)
ACTION_KEYS = {
    pygame.K_1: config.ACTION_FEED,
    pygame.K_2: config.ACTION_REST,
    pygame.K_3: config.ACTION_STUDY,
    pygame.K_KP1: config.ACTION_FEED,
    pygame.K_KP2: config.ACTION_REST,
    pygame.K_KP3: config.ACTION_STUDY,
}


class Game:
    """메인 루프와 화면 전환(타이틀/게임/엔딩), 시간 관리(행동 쿨타임 포함)를 맡는 클래스."""

    def __init__(self):
        """pygame을 켜고 800x600 창과 시계, 첫 상태, 버튼 3개를 준비한다."""
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)

        self.running = True              # False가 되면 메인 루프가 끝난다
        # 지금 보여 줄 화면. 2일차에는 타이틀이 없어 임시로 게임 화면에서 시작한다.
        # (config.START_STATE 를 5일차에 STATE_TITLE 로 바꾸면 된다)
        self.state = config.START_STATE
        self.student = Student()
        self.cooldown = 0.0              # 남은 쿨타임(초). 0이면 행동할 수 있다
        self.buttons = self.make_buttons()

    def make_buttons(self):
        """화면 아래쪽에 가로로 놓인 행동 버튼 3개를 {행동 이름: Button} 사전으로 만든다."""
        items = [
            (config.ACTION_FEED, config.FEED_BUTTON_TEXT),
            (config.ACTION_REST, config.REST_BUTTON_TEXT),
            (config.ACTION_STUDY, config.STUDY_BUTTON_TEXT),
        ]
        buttons = {}
        for index, (name, text) in enumerate(items):
            x = config.BUTTON_START_X + index * (config.BUTTON_WIDTH + config.BUTTON_GAP)
            buttons[name] = Button(x, config.BUTTON_Y,
                                   config.BUTTON_WIDTH, config.BUTTON_HEIGHT, text)
        return buttons

    def is_cooling_down(self):
        """쿨타임 중이면 True를 돌려준다(소수 오차는 TIME_EPSILON 만큼 허용)."""
        return self.cooldown > config.TIME_EPSILON

    def do_action(self, name):
        """행동 name(feed/rest/study)을 실행하고 쿨타임 1초를 시작한다.

        쿨타임 중이면 아무것도 하지 않는다. 실행했으면 True, 무시했으면 False를 돌려준다.
        세 행동이 쿨타임 하나를 함께 쓴다.
        """
        if self.is_cooling_down():
            return False
        if name == config.ACTION_FEED:
            self.student.feed()
        elif name == config.ACTION_REST:
            self.student.rest()
        elif name == config.ACTION_STUDY:
            self.student.study()
        else:
            return False
        self.cooldown = config.ACTION_COOLDOWN
        return True

    def handle_event(self, event):
        """이벤트 하나를 받아 처리한다.

        - 창 닫기(QUIT) 또는 ESC: running을 False로 바꾼다.
        - 게임 화면에서 마우스 왼쪽 클릭이 버튼 위면 그 버튼의 행동을 한다.
        - 게임 화면에서 1/2/3 키(숫자패드 포함)도 같은 행동을 한다.
        쿨타임 중이면 do_action이 입력을 무시한다.
        """
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.running = False
        elif self.state == config.STATE_PLAYING:
            if event.type == pygame.KEYDOWN and event.key in ACTION_KEYS:
                self.do_action(ACTION_KEYS[event.key])
            elif (event.type == pygame.MOUSEBUTTONDOWN
                  and event.button == pygame.BUTTON_LEFT):
                for name, button in self.buttons.items():
                    if button.is_clicked(event.pos):
                        self.do_action(name)
                        break

    def update(self, dt):
        """dt초만큼 게임 상태를 진행한다.

        게임 화면일 때만 제자의 시간을 흘려 게이지를 자연 감소시키고,
        남은 쿨타임도 dt만큼 줄인다(0 아래로는 내려가지 않음).
        """
        if self.state == config.STATE_PLAYING:
            self.student.update(dt)
            self.cooldown = max(0.0, self.cooldown - dt)

    def draw(self):
        """현재 상태의 화면을 그린다.

        배경을 칠하고, 게임 화면이면 제자의 게이지(체력·멘탈 막대, 지식 숫자),
        행동 버튼 3개(쿨타임 중이면 회색)와 쿨타임 안내 문구를 그린다.
        """
        self.screen.fill(config.COLOR_BG)
        if self.state == config.STATE_PLAYING:
            self.student.draw_gauges(self.screen, self.font)
            self.draw_buttons()
        pygame.display.flip()

    def draw_buttons(self):
        """행동 버튼 3개와 그 아래 "누른 뒤 1초 동안 회색 (쿨타임)" 안내 문구를 그린다."""
        cooling_down = self.is_cooling_down()
        for button in self.buttons.values():
            button.draw(self.screen, self.font, cooling_down)

        hint = self.font.render(config.COOLDOWN_HINT_TEXT, True, config.COLOR_BLACK)
        hint_rect = hint.get_rect()
        hint_rect.midtop = (config.COOLDOWN_HINT_X, config.COOLDOWN_HINT_Y)
        self.screen.blit(hint, hint_rect)

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
