"""제자(Student) 클래스가 들어 있는 파일."""

import pygame

import config


def clamp(value, low, high):
    """value를 low 이상 high 이하로 잘라서 돌려준다."""
    return max(low, min(value, high))


class Student:
    """교수가 돌보는 제자 한 명.

    체력·멘탈·지식 게이지와 지금까지 흐른 시간을 가지고 있다.
    로직은 화면 없이도 호출할 수 있도록 시간(dt)을 인자로 받는다.
    """

    def __init__(self):
        """게이지를 시작값으로 정하고 경과 시간을 0으로 둔다."""
        self.health = config.HEALTH_START
        self.mental = config.MENTAL_START
        self.knowledge = config.KNOWLEDGE_START
        self.elapsed = 0.0      # 게임 시작 후 흐른 시간(초)
        self.decay_timer = 0.0  # 다음 자연 감소까지 모아 둔 시간(초)

    # ------------------------------------------------------------
    # 게이지 값 바꾸기
    # ------------------------------------------------------------
    def change_health(self, amount):
        """체력을 amount만큼 바꾸고 0~100 안으로 맞춘다."""
        self.health = clamp(self.health + amount, config.GAUGE_MIN, config.GAUGE_MAX)

    def change_mental(self, amount):
        """멘탈을 amount만큼 바꾸고 0~100 안으로 맞춘다."""
        self.mental = clamp(self.mental + amount, config.GAUGE_MIN, config.GAUGE_MAX)

    def change_knowledge(self, amount):
        """지식을 amount만큼 바꾼다. 지식은 0 아래로 내려가지 않는다(상한 없음)."""
        self.knowledge = max(config.GAUGE_MIN, self.knowledge + amount)

    # ------------------------------------------------------------
    # 시간 흐름과 자연 감소
    # ------------------------------------------------------------
    def update(self, dt):
        """dt초만큼 시간을 흘려 게이지를 자연 감소시킨다.

        흐른 시간을 decay_timer에 모아 두었다가 1초가 찰 때마다 한 번씩 감소시킨다.
        그래서 프레임 속도와 상관없이 1초에 정확히 한 번 줄어들고,
        dt가 커서 여러 초가 한꺼번에 지나도 지난 초 수만큼 줄어든다.
        소수 덧셈 오차 때문에 1초를 놓치지 않도록 아주 작은 허용치(TIME_EPSILON)를 둔다.
        """
        self.elapsed += dt
        self.decay_timer += dt
        while self.decay_timer + config.TIME_EPSILON >= config.DECAY_INTERVAL:
            self.decay_timer -= config.DECAY_INTERVAL
            self.decay_once()

    def decay_once(self):
        """1초분 자연 감소를 한 번 적용한다: 체력 -1, 멘탈 -(멘탈 감소량)."""
        self.change_health(-config.HEALTH_DECAY_PER_SEC)
        self.change_mental(-self.get_mental_decay())

    def get_mental_decay(self):
        """1초마다 줄어드는 멘탈 양을 돌려준다.

        지금은 항상 1이다. 시험 기간 2배(-2)는 5일차에 이 메서드에서 처리한다.
        """
        return config.MENTAL_DECAY_PER_SEC

    def is_dropped_out(self):
        """체력이나 멘탈이 0이면 True(휴학 조건)를 돌려준다."""
        return self.health <= config.GAUGE_MIN or self.mental <= config.GAUGE_MIN

    # ------------------------------------------------------------
    # 행동 (3일차)
    # ------------------------------------------------------------
    def feed(self):
        """학식 먹이기: 체력을 올린다. (3일차에 구현)"""
        pass

    def rest(self):
        """쉬게 하기: 멘탈을 올리고 지식을 조금 내린다. (3일차에 구현)"""
        pass

    def study(self):
        """공부시키기: 지식을 올리고 체력·멘탈을 내린다. (3일차에 구현)"""
        pass

    # ------------------------------------------------------------
    # 그리기
    # ------------------------------------------------------------
    def draw_gauges(self, screen, font):
        """왼쪽 게이지 구역에 체력·멘탈 막대를, 정보바 오른쪽에 지식 숫자를 그린다."""
        self.draw_bar(screen, font, config.HEALTH_LABEL, self.health,
                      config.HEALTH_LABEL_Y, config.HEALTH_BAR_Y)
        self.draw_bar(screen, font, config.MENTAL_LABEL, self.mental,
                      config.MENTAL_LABEL_Y, config.MENTAL_BAR_Y)

        # 지식은 막대 없이 숫자로, 상단 정보바 오른쪽 끝에 표시
        text = font.render(f"{config.KNOWLEDGE_LABEL} {self.knowledge}",
                           True, config.COLOR_BLACK)
        text_rect = text.get_rect()
        text_rect.topright = (config.SCREEN_WIDTH - config.INFO_BAR_MARGIN,
                              config.INFO_BAR_Y)
        screen.blit(text, text_rect)

    def draw_bar(self, screen, font, label, value, label_y, bar_y):
        """라벨과 게이지 막대 하나를 그린다.

        배경(흰색)을 깔고 값 비율만큼 색을 채운 뒤 검은 테두리를 그린다.
        값이 30 미만이면 빨간색, 아니면 초록색으로 채운다.
        """
        label_text = font.render(label, True, config.COLOR_BLACK)
        screen.blit(label_text, (config.GAUGE_X, label_y))

        # 1) 막대 배경
        bar_rect = pygame.Rect(config.GAUGE_X, bar_y,
                               config.BAR_WIDTH, config.BAR_HEIGHT)
        pygame.draw.rect(screen, config.COLOR_BAR_BG, bar_rect)

        # 2) 값 비율만큼 채우기
        if value < config.LOW_GAUGE_LIMIT:
            fill_color = config.COLOR_RED
        else:
            fill_color = config.COLOR_GREEN
        fill_width = int(config.BAR_WIDTH * value / config.GAUGE_MAX)
        fill_rect = pygame.Rect(config.GAUGE_X, bar_y,
                                fill_width, config.BAR_HEIGHT)
        pygame.draw.rect(screen, fill_color, fill_rect)

        # 3) 테두리
        pygame.draw.rect(screen, config.COLOR_BLACK, bar_rect,
                         config.BAR_BORDER_WIDTH)

    def draw(self, screen):
        """제자를 화면에 그린다. (4일차에 구현)"""
        pass
