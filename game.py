"""게임 전체(Game) 클래스가 들어 있는 파일."""

import json
import sys

import pygame

import config
from button import Button, draw_pixel_box, draw_sprite, render_text, sprite_size
from student import Student

# 키보드 단축키 -> 행동 이름 (기획서 조작키: 1/2/3)
ACTION_KEYS = {
    pygame.K_1: config.ACTION_FEED,
    pygame.K_2: config.ACTION_REST,
    pygame.K_3: config.ACTION_STUDY,
}


class Game:
    """메인 루프와 화면 전환(타이틀/게임/엔딩), 시간 관리(행동 쿨타임 포함), 기록 저장을 맡는 클래스."""

    def __init__(self, record_path=None):
        """pygame을 켜고 800x600 창과 시계, 글꼴, 버튼 3개, 첫 화면(타이틀)을 준비한다.

        record_path는 최고 기록 파일 경로다. 주지 않으면 config.RECORD_PATH
        (exe 옆 또는 main.py 옆의 record.json)를 쓴다. 테스트에서는 임시 폴더 경로를 넘긴다.
        시작할 때 이 파일에서 최고 기록을 불러온다.
        """
        if record_path is None:
            record_path = config.RECORD_PATH
        self.record_path = record_path   # 최고 기록 파일(record.json) 경로
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
        self.title_font = pygame.font.SysFont(config.FONT_NAME, config.TITLE_FONT_SIZE)
        self.backdrop = self.make_backdrop()  # 도트 무늬 배경(한 번만 그려 둔다)

        self.running = True              # False가 되면 메인 루프가 끝난다
        self.best_record = self.load_best_record()  # 최고 기록(지식). 타이틀에 표시
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
        """엔딩 이름 ending을 저장하고 엔딩 화면으로 바꾼다.

        휴학·졸업 모두 여기를 지나간다. 이번 판 누적 지식이 최고 기록보다 크면
        최고 기록을 바꾸고 record.json에 저장한다.
        """
        self.ending = ending
        self.state = config.STATE_ENDING
        self.update_best_record(self.student.knowledge)

    # ------------------------------------------------------------
    # 최고 기록 (record.json)
    # ------------------------------------------------------------
    def load_best_record(self):
        """record.json에서 최고 기록(지식)을 읽어 돌려준다.

        파일이 없거나, 읽을 수 없거나, JSON이 깨졌거나, 형식이 틀리면
        (사전이 아님, 키 없음, 정수가 아님, 음수) 0을 돌려준다. 어떤 경우에도 멈추지 않는다.
        """
        try:
            with open(self.record_path, encoding=config.RECORD_ENCODING) as file:
                data = json.load(file)
        except (OSError, ValueError):
            # OSError: 파일 없음·권한 없음 등 / ValueError: JSON 깨짐·글자 깨짐
            return config.BEST_RECORD_START
        if not isinstance(data, dict):
            return config.BEST_RECORD_START
        value = data.get(config.RECORD_KEY)
        # bool(True/False)도 int의 한 종류라서 따로 빼 준다
        if not isinstance(value, int) or isinstance(value, bool):
            return config.BEST_RECORD_START
        if value < config.BEST_RECORD_START:
            return config.BEST_RECORD_START
        return value

    def save_best_record(self):
        """지금 최고 기록을 record.json에 {"best_knowledge": 값} 형태로 저장한다.

        저장에 실패하면(폴더 권한 없음 등) False를 돌려주고 게임은 그대로 계속한다.
        성공하면 True를 돌려준다.
        """
        data = {config.RECORD_KEY: self.best_record}
        try:
            with open(self.record_path, "w", encoding=config.RECORD_ENCODING) as file:
                json.dump(data, file)
        except OSError:
            return False
        return True

    def update_best_record(self, knowledge):
        """knowledge가 최고 기록보다 크면 최고 기록을 바꾸고 파일에 저장한다.

        바뀌었으면 True, 같거나 작아서 그대로면 False를 돌려준다.
        """
        if knowledge <= self.best_record:
            return False
        self.best_record = knowledge
        self.save_best_record()
        return True

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
    # 그리기 (도트 스타일)
    # ------------------------------------------------------------
    def make_backdrop(self):
        """창 전체 배경을 한 번만 그려 둔 Surface를 만들어 돌려준다.

        크림색 바탕에 일정 간격으로 아주 연한 도트를 찍어 은은한 무늬를 만든다.
        매 프레임 도트를 다시 찍지 않고 이 Surface를 통째로 붙인다.
        """
        backdrop = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        backdrop.fill(config.COLOR_BACKDROP)
        for x in range(config.BACKDROP_DOT_START, config.SCREEN_WIDTH,
                       config.BACKDROP_DOT_STEP):
            for y in range(config.BACKDROP_DOT_START, config.SCREEN_HEIGHT,
                           config.BACKDROP_DOT_STEP):
                pygame.draw.rect(backdrop, config.COLOR_BACKDROP_DOT,
                                 (x, y, config.PIXEL_SIZE, config.PIXEL_SIZE))
        return backdrop

    def draw(self):
        """현재 상태(타이틀/게임/엔딩)의 화면을 그린다."""
        self.screen.blit(self.backdrop, config.ORIGIN)
        if self.state == config.STATE_TITLE:
            self.draw_title()
        elif self.state == config.STATE_PLAYING:
            self.draw_playing()
        elif self.state == config.STATE_ENDING:
            self.draw_ending()
        pygame.display.flip()

    def draw_panel(self, rect):
        """크림색 도트 패널(계단 모서리, 남색 외곽선, 아래 그림자)을 그리고 안쪽 사각형을 돌려준다."""
        return draw_pixel_box(self.screen, rect, config.COLOR_BG,
                              config.COLOR_PANEL_LIGHT, config.COLOR_PANEL_SHADOW,
                              drop=config.COLOR_DROP)

    def draw_text_center(self, font, text, center_y, color=config.COLOR_TEXT):
        """글자 text를 화면 가운데(가로)에, 세로 가운데가 center_y가 되게 그리고 사각형을 돌려준다."""
        surface = render_text(font, text, color)
        rect = surface.get_rect()
        rect.center = (config.SCREEN_CENTER_X, center_y)
        self.screen.blit(surface, rect)
        return rect

    def draw_big_text(self, text, center_y):
        """큰 제목 글자를 살구색 그림자 글자와 겹쳐 화면 가운데에 그린다(레트로 느낌)."""
        shadow = render_text(self.title_font, text, config.COLOR_TITLE_SHADOW)
        rect = shadow.get_rect()
        rect.center = (config.SCREEN_CENTER_X + config.TITLE_SHADOW_OFFSET,
                       center_y + config.TITLE_SHADOW_OFFSET)
        self.screen.blit(shadow, rect)
        self.draw_text_center(self.title_font, text, center_y)

    def draw_badge(self, text, center_y, fill, light):
        """글자 하나를 감싸는 작은 도트 배지(상자)를 화면 가운데에 그린다."""
        surface = render_text(self.font, text)
        rect = surface.get_rect()
        box = pygame.Rect(config.ORIGIN, (rect.width + config.BADGE_PADDING_X * config.HALF,
                                          config.BADGE_HEIGHT))
        box.center = (config.SCREEN_CENTER_X, center_y)
        inner = draw_pixel_box(self.screen, box, fill, light, drop=config.COLOR_DROP)
        rect.center = inner.center
        self.screen.blit(surface, rect)

    def draw_key_hint(self, text, center_y):
        """키 안내 문구(예: "Enter를 눌러 시작") 앞에 작은 도트 화살표를 붙여 그린다."""
        rect = self.draw_text_center(self.font, text, center_y)
        arrow_width, arrow_height = sprite_size(config.ARROW_SPRITE, config.PIXEL_SIZE)
        draw_sprite(self.screen, config.ARROW_SPRITE,
                    rect.left - config.HINT_ARROW_GAP - arrow_width,
                    center_y - arrow_height // config.HALF,
                    config.PIXEL_SIZE, {config.SPRITE_INK: config.COLOR_PINK_DARK})

    def draw_stars(self, stars):
        """장식용 반짝이 별들을 (x, y, 색) 목록대로 찍는다."""
        for x, y, color in stars:
            draw_sprite(self.screen, config.STAR_SPRITE, x, y, config.PIXEL_SIZE,
                        {config.SPRITE_INK: color})

    def draw_title(self):
        """타이틀 화면: 패널, 큰 제목, 도트 장식 줄·별, 최고 기록 배지, "Enter를 눌러 시작"."""
        self.draw_panel(config.MENU_PANEL_RECT)
        self.draw_stars(config.TITLE_STARS)
        self.draw_big_text(config.TITLE_TEXT, config.TITLE_TEXT_Y)
        self.draw_dot_line(config.TITLE_LINE_Y)
        self.draw_badge(config.BEST_RECORD_TEXT.format(self.best_record),
                        config.BEST_RECORD_Y, config.COLOR_PINK_LIGHT, config.COLOR_WHITE)
        self.draw_key_hint(config.START_HINT_TEXT, config.START_HINT_Y)

    def draw_dot_line(self, y):
        """제목 아래에 여러 색 도트를 한 칸씩 띄워 늘어놓은 장식 줄을 그린다(화면 가운데 정렬)."""
        step = config.PIXEL_SIZE * config.HALF
        start_x = config.SCREEN_CENTER_X - (config.TITLE_LINE_DOTS * step) // config.HALF
        for index in range(config.TITLE_LINE_DOTS):
            color = config.TITLE_LINE_COLORS[index % len(config.TITLE_LINE_COLORS)]
            pygame.draw.rect(self.screen, color,
                             (start_x + index * step, y, config.PIXEL_SIZE, config.PIXEL_SIZE))

    def draw_playing(self):
        """게임 화면: 상단 정보바, (시험 기간이면) 노란 배너, 상태 패널(게이지), 제자 무대, 버튼."""
        self.draw_info_bar()
        if self.student.is_exam_period():
            self.draw_exam_banner()
        self.draw_panel((config.STATUS_PANEL_X, config.PANEL_Y,
                         config.STATUS_PANEL_WIDTH, config.PANEL_HEIGHT))
        self.draw_panel((config.STAGE_X, config.PANEL_Y,
                         config.STAGE_WIDTH, config.PANEL_HEIGHT))
        self.student.draw_gauges(self.screen, self.font)
        self.student.draw(self.screen)
        self.draw_buttons()

    def draw_ending(self):
        """엔딩 화면: 패널, 엔딩 이름, (졸업) 학사모와 별 / (휴학) 비구름, 누적 지식 배지, "R을 눌러 다시 하기"."""
        self.draw_panel(config.MENU_PANEL_RECT)
        self.draw_big_text(self.ending, config.ENDING_NAME_Y)
        if self.ending == config.ENDING_LEAVE:
            self.draw_center_sprite(config.CLOUD_SPRITE, config.CLOUD_TOP_Y,
                                    config.CLOUD_PIXEL, config.CLOUD_COLORS)
        else:
            self.draw_stars(config.ENDING_STARS)
            self.draw_graduation_cap()
        self.draw_badge(config.ENDING_KNOWLEDGE_TEXT.format(self.student.knowledge),
                        config.ENDING_KNOWLEDGE_Y, config.COLOR_MINT_LIGHT, config.COLOR_WHITE)
        self.draw_key_hint(config.RESTART_HINT_TEXT, config.RESTART_HINT_Y)

    def draw_center_sprite(self, grid, top, cell, colors):
        """스프라이트 grid를 화면 가운데(가로)에, 위쪽 y가 top이 되게 칸 크기 cell로 찍는다."""
        width, _ = sprite_size(grid, cell)
        draw_sprite(self.screen, grid, config.SCREEN_CENTER_X - width // config.HALF, top,
                    cell, colors)

    def draw_graduation_cap(self):
        """도트 학사모(납작한 마름모 윗판 + 띠 + 금색 술)를 화면 가운데 위쪽에 찍는다."""
        self.draw_center_sprite(config.CAP_SPRITE, config.CAP_TOP_Y,
                                config.CAP_PIXEL, config.CAP_COLORS)

    def draw_exam_banner(self):
        """정보바 바로 아래에 노란 도트 배너와 문구, 양옆 느낌표를 그린다(패널 위)."""
        banner = pygame.Rect(config.EXAM_BANNER_X, config.EXAM_BANNER_Y,
                             config.EXAM_BANNER_WIDTH, config.EXAM_BANNER_HEIGHT)
        inner = draw_pixel_box(self.screen, banner, config.COLOR_YELLOW,
                               config.COLOR_YELLOW_LIGHT, config.COLOR_YELLOW_DARK,
                               drop=config.COLOR_DROP)
        text = render_text(self.font, config.EXAM_BANNER_TEXT)
        text_rect = text.get_rect()
        text_rect.center = inner.center
        self.screen.blit(text, text_rect)

        icon_width, icon_height = sprite_size(config.EXCLAIM_SPRITE, config.PIXEL_SIZE)
        icon_y = inner.centery - icon_height // config.HALF
        ink = {config.SPRITE_INK: config.COLOR_OUTLINE}
        draw_sprite(self.screen, config.EXCLAIM_SPRITE,
                    banner.left + config.EXAM_ICON_MARGIN, icon_y, config.PIXEL_SIZE, ink)
        draw_sprite(self.screen, config.EXCLAIM_SPRITE,
                    banner.right - config.EXAM_ICON_MARGIN - icon_width, icon_y,
                    config.PIXEL_SIZE, ink)

    def draw_info_bar(self):
        """상단 정보바를 그린다.

        민트색 도트 상자 위에 왼쪽 "N학년", 가운데 "남은 시간 N초"(현재 학년 남은 시간),
        오른쪽 "지식 N"을 쓴다.
        """
        box = pygame.Rect(config.INFO_BOX_X, config.INFO_BOX_Y,
                          config.INFO_BOX_WIDTH, config.INFO_BOX_HEIGHT)
        draw_pixel_box(self.screen, box, config.COLOR_INFO_BAR,
                       config.COLOR_MINT_LIGHT, config.COLOR_MINT_DARK,
                       drop=config.COLOR_DROP)

        grade = render_text(self.font, config.GRADE_TEXT.format(self.student.get_grade()))
        grade_rect = grade.get_rect()
        grade_rect.midleft = (config.INFO_BAR_MARGIN, config.INFO_TEXT_CENTER_Y)
        self.screen.blit(grade, grade_rect)

        time_left = render_text(
            self.font, config.TIME_LEFT_TEXT.format(self.student.get_grade_time_left()))
        time_rect = time_left.get_rect()
        time_rect.center = (config.INFO_TIME_X, config.INFO_TEXT_CENTER_Y)
        self.screen.blit(time_left, time_rect)

        knowledge = render_text(
            self.font,
            config.KNOWLEDGE_TEXT.format(config.KNOWLEDGE_LABEL, self.student.knowledge))
        knowledge_rect = knowledge.get_rect()
        knowledge_rect.midright = (config.SCREEN_WIDTH - config.INFO_BAR_MARGIN,
                                   config.INFO_TEXT_CENTER_Y)
        self.screen.blit(knowledge, knowledge_rect)

    def draw_buttons(self):
        """행동 버튼 3개와 그 아래 "누른 뒤 1초 동안 회색 (쿨타임)" 안내 문구를 그린다."""
        cooling_down = self.is_cooling_down()
        for button in self.buttons.values():
            button.draw(self.screen, self.font, cooling_down)

        hint = render_text(self.font, config.COOLDOWN_HINT_TEXT, config.COLOR_TEXT_SOFT)
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
