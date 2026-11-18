"""게임 전체(Game) 클래스가 들어 있는 파일."""

import sys

import pygame

import config
from button import Button
from student import Student

# 키보드 단축키 -> 행동 이름 (기획서 조작키: 1/2/3)
ACTION_KEYS = {
    pygame.K_1: config.ACTION_FEED,
    pygame.K_2: config.ACTION_REST,
    pygame.K_3: config.ACTION_STUDY,
}


class Game:
    """메인 루프와 화면 전환(타이틀/게임/엔딩), 시간 관리(행동 쿨타임 포함)를 맡는 클래스."""

    def __init__(self):
        """pygame을 켜고 800x600 창과 시계, 글꼴, 버튼 3개, 첫 화면(타이틀)을 준비한다."""
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
        self.title_font = pygame.font.SysFont(config.FONT_NAME, config.TITLE_FONT_SIZE)

        self.running = True              # False가 되면 메인 루프가 끝난다
        # 최고 기록(지식). record.json 저장·불러오기는 6일차에 붙인다.
        self.best_record = config.BEST_RECORD_START
        self.buttons = self.make_buttons()
        self.reset_round()
        self.state = config.START_STATE  # 처음 보여 줄 화면(타이틀)

    def reset_round(self):
        """한 판에 쓰는 값을 모두 처음으로 되돌린다: 새 제자, 쿨타임 0, 엔딩 없음."""
        self.student = Student()
        self.cooldown = config.ZERO_TIME  # 남은 쿨타임(초). 0이면 행동할 수 있다
        self.ending = None                # 엔딩 이름. 엔딩 전에는 None

    def start_new_game(self):
        """새 판을 시작한다: 모든 값을 초기화하고 바로 게임 화면으로 간다.

        타이틀에서 Enter, 엔딩에서 R을 누르면 이 메서드가 불린다.
        """
        self.reset_round()
        self.state = config.STATE_PLAYING

    def end_game(self, ending):
        """엔딩 이름 ending을 저장하고 엔딩 화면으로 바꾼다."""
        self.ending = ending
        self.state = config.STATE_ENDING

    def check_ending(self):
        """제자 상태를 보고 엔딩이 났으면 엔딩 화면으로 바꾼다.

        휴학(체력·멘탈 0)이 졸업(240초)보다 먼저다. 판정은 Student.get_ending이 한다.
        엔딩이 났으면 True, 아니면 False를 돌려준다.
        """
        ending = self.student.get_ending()
        if ending is None:
            return False
        self.end_game(ending)
        return True

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

        게임 화면이 아니거나 쿨타임 중이면 아무것도 하지 않는다.
        실행했으면 True, 무시했으면 False를 돌려준다. 세 행동이 쿨타임 하나를 함께 쓴다.
        행동으로 체력이나 멘탈이 0이 되면 그 즉시 휴학 엔딩으로 바꾼다.
        """
        if self.state != config.STATE_PLAYING or self.is_cooling_down():
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
        self.check_ending()
        return True

    def handle_event(self, event):
        """이벤트 하나를 받아 처리한다.

        - 창 닫기(QUIT) 또는 ESC: 모든 화면에서 running을 False로 바꾼다.
        - 타이틀 화면에서 Enter: 새 판 시작.
        - 엔딩 화면에서 R: 새 판 시작.
        - 게임 화면에서 마우스 왼쪽 클릭이 버튼 위면, 또는 1/2/3 키면 그 행동을 한다.
        다른 화면의 Enter/R, 다른 키는 무시한다. 쿨타임 중이면 do_action이 입력을 무시한다.
        """
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.running = False
        elif self.state == config.STATE_TITLE:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self.start_new_game()
        elif self.state == config.STATE_ENDING:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.start_new_game()
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
        그다음 엔딩을 확인한다: 자연 감소로 체력·멘탈이 0이 되었으면 휴학,
        아니면 240초가 되었을 때 졸업. 그래서 240초 시점에 0이 겹치면 휴학이 먼저다.
        타이틀·엔딩 화면에서는 시간·게이지·쿨타임이 흐르지 않는다.
        """
        if self.state == config.STATE_PLAYING:
            self.student.update(dt)
            self.cooldown = max(config.ZERO_TIME, self.cooldown - dt)
            self.check_ending()

    # ------------------------------------------------------------
    # 그리기
    # ------------------------------------------------------------
    def draw(self):
        """현재 상태(타이틀/게임/엔딩)의 화면을 그린다."""
        self.screen.fill(config.COLOR_BG)
        if self.state == config.STATE_TITLE:
            self.draw_title()
        elif self.state == config.STATE_PLAYING:
            self.draw_playing()
        elif self.state == config.STATE_ENDING:
            self.draw_ending()
        pygame.display.flip()

    def draw_text_center(self, font, text, center_y):
        """글자 text를 화면 가운데(가로)에, 세로 가운데가 center_y가 되게 그린다."""
        surface = font.render(text, True, config.COLOR_BLACK)
        rect = surface.get_rect()
        rect.center = (config.SCREEN_CENTER_X, center_y)
        self.screen.blit(surface, rect)

    def draw_title(self):
        """타이틀 화면: 게임 제목, 제목 아래 장식 선, 최고 기록, "Enter를 눌러 시작"."""
        self.draw_text_center(self.title_font, config.TITLE_TEXT, config.TITLE_TEXT_Y)
        pygame.draw.line(self.screen, config.COLOR_BLACK,
                         (config.SCREEN_CENTER_X - config.TITLE_LINE_HALF, config.TITLE_LINE_Y),
                         (config.SCREEN_CENTER_X + config.TITLE_LINE_HALF, config.TITLE_LINE_Y),
                         config.TITLE_LINE_WIDTH)
        self.draw_text_center(self.font, config.BEST_RECORD_TEXT.format(self.best_record),
                              config.BEST_RECORD_Y)
        self.draw_text_center(self.font, config.START_HINT_TEXT, config.START_HINT_Y)

    def draw_playing(self):
        """게임 화면: 상단 정보바, (시험 기간이면) 노란 배너, 게이지 막대, 제자 얼굴, 버튼."""
        self.draw_info_bar()
        if self.student.is_exam_period():
            self.draw_exam_banner()
        self.student.draw_gauges(self.screen, self.font)
        self.student.draw(self.screen)
        self.draw_buttons()

    def draw_ending(self):
        """엔딩 화면: 엔딩 이름, 졸업이면 학사모, 누적 지식, "R을 눌러 다시 하기"."""
        self.draw_text_center(self.title_font, self.ending, config.ENDING_NAME_Y)
        if self.ending != config.ENDING_LEAVE:
            self.draw_graduation_cap()
        self.draw_text_center(
            self.font, config.ENDING_KNOWLEDGE_TEXT.format(self.student.knowledge),
            config.ENDING_KNOWLEDGE_Y)
        self.draw_text_center(self.font, config.RESTART_HINT_TEXT, config.RESTART_HINT_Y)

    def draw_graduation_cap(self):
        """학사모를 사각형·원·선으로 그린다.

        몸체(사각형) 위에 납작한 판(사각형)을 얹고, 판 가운데 단추(원)에서
        술(선)이 오른쪽으로 뻗었다가 아래로 늘어지며 끝에 매듭(원)이 달린다.
        """
        cx = config.CAP_CENTER_X
        body = pygame.Rect(config.ORIGIN, (config.CAP_BODY_WIDTH, config.CAP_BODY_HEIGHT))
        body.midtop = (cx, config.CAP_BODY_Y)
        pygame.draw.rect(self.screen, config.COLOR_CAP, body)

        board = pygame.Rect(config.ORIGIN, (config.CAP_BOARD_WIDTH, config.CAP_BOARD_HEIGHT))
        board.midtop = (cx, config.CAP_BOARD_Y)
        pygame.draw.rect(self.screen, config.COLOR_CAP, board)

        button_pos = board.center
        tassel_x = cx + config.CAP_TASSEL_END_X
        tassel_corner = (tassel_x, board.centery)
        tassel_end = (tassel_x, board.centery + config.CAP_TASSEL_DROP)
        pygame.draw.line(self.screen, config.COLOR_TASSEL, button_pos, tassel_corner,
                         config.CAP_TASSEL_WIDTH)
        pygame.draw.line(self.screen, config.COLOR_TASSEL, tassel_corner, tassel_end,
                         config.CAP_TASSEL_WIDTH)
        pygame.draw.circle(self.screen, config.COLOR_TASSEL, button_pos,
                           config.CAP_BUTTON_RADIUS)
        pygame.draw.circle(self.screen, config.COLOR_TASSEL, tassel_end,
                           config.CAP_TASSEL_END_RADIUS)

    def draw_exam_banner(self):
        """정보바 바로 아래에 노란 시험 기간 배너와 문구를 그린다(게이지 구역 위)."""
        banner = pygame.Rect(config.EXAM_BANNER_X, config.EXAM_BANNER_Y,
                             config.EXAM_BANNER_WIDTH, config.EXAM_BANNER_HEIGHT)
        pygame.draw.rect(self.screen, config.COLOR_YELLOW, banner)
        pygame.draw.rect(self.screen, config.COLOR_BLACK, banner,
                         config.EXAM_BANNER_BORDER_WIDTH)
        text = self.font.render(config.EXAM_BANNER_TEXT, True, config.COLOR_BLACK)
        text_rect = text.get_rect()
        text_rect.center = banner.center
        self.screen.blit(text, text_rect)

    def draw_info_bar(self):
        """상단 정보바를 그린다.

        배경 사각형 위에 왼쪽 "N학년", 가운데 "남은 시간 N초"(현재 학년 남은 시간),
        오른쪽 "지식 N"을 쓴다.
        """
        bar_rect = pygame.Rect(config.ORIGIN,
                               (config.SCREEN_WIDTH, config.INFO_BAR_HEIGHT))
        pygame.draw.rect(self.screen, config.COLOR_INFO_BAR, bar_rect)

        grade = self.font.render(config.GRADE_TEXT.format(self.student.get_grade()),
                                 True, config.COLOR_BLACK)
        grade_rect = grade.get_rect()
        grade_rect.topleft = (config.INFO_BAR_MARGIN, config.INFO_BAR_Y)
        self.screen.blit(grade, grade_rect)

        time_left = self.font.render(
            config.TIME_LEFT_TEXT.format(self.student.get_grade_time_left()),
            True, config.COLOR_BLACK)
        time_rect = time_left.get_rect()
        time_rect.midtop = (config.INFO_TIME_X, config.INFO_BAR_Y)
        self.screen.blit(time_left, time_rect)

        knowledge = self.font.render(
            config.KNOWLEDGE_TEXT.format(config.KNOWLEDGE_LABEL, self.student.knowledge),
            True, config.COLOR_BLACK)
        knowledge_rect = knowledge.get_rect()
        knowledge_rect.topright = (config.SCREEN_WIDTH - config.INFO_BAR_MARGIN,
                                   config.INFO_BAR_Y)
        self.screen.blit(knowledge, knowledge_rect)

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
