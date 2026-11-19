"""게임 전체(Game) 클래스가 들어 있는 파일."""

import json
import random
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

# 대화창(선택지형 이벤트)에서 키 -> 선택지 번호 (키 1: 첫 번째, 키 2: 두 번째)
CHOICE_KEYS = {
    pygame.K_1: config.CHOICE_FIRST,
    pygame.K_2: config.CHOICE_SECOND,
}


class Game:
    """메인 루프와 화면 전환(타이틀/게임/엔딩), 시간 관리(행동 쿨타임 포함), 기록 저장을 맡는 클래스."""

    def __init__(self, record_path=None, seed=None):
        """pygame을 켜고 800x600 창과 시계, 글꼴, 버튼 3개, 첫 화면(타이틀)을 준비한다.

        record_path는 최고 기록 파일 경로다. 주지 않으면 config.RECORD_PATH
        (exe 옆 또는 main.py 옆의 record.json)를 쓴다. 테스트에서는 임시 폴더 경로를 넘긴다.
        시작할 때 이 파일에서 최고 기록을 불러온다.
        seed는 랜덤 이벤트용 난수 생성기의 시드다. 같은 시드면 같은 이벤트가 나온다
        (테스트에서 고정). None이면 매번 다르게 나온다.
        """
        if record_path is None:
            record_path = config.RECORD_PATH
        self.record_path = record_path   # 최고 기록 파일(record.json) 경로
        self.rng = random.Random(seed)   # 랜덤 이벤트 전용 난수 생성기 (다른 곳에는 쓰지 않는다)
        pygame.init()
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
        self.title_font = pygame.font.SysFont(config.FONT_NAME, config.TITLE_FONT_SIZE)
        self.backdrop = self.make_backdrop()  # 도트 무늬 배경(한 번만 그려 둔다)
        self.popup_font = pygame.font.SysFont(config.FONT_NAME, config.POPUP_FONT_SIZE,
                                              bold=config.POPUP_FONT_BOLD)
        self.event_font = pygame.font.SysFont(config.FONT_NAME, config.EVENT_FONT_SIZE)
        self.mouse_pos = None             # 마지막 마우스 위치(MOUSEMOTION). None이면 아직 모름
        self.blink_time = config.ZERO_TIME  # 안내 문구 깜빡임 시계(모든 화면에서 흐른다)

        self.running = True             # False가 되면 메인 루프가 끝난다
        self.best_record = self.load_best_record()  # 최고 기록(지식). 타이틀에 표시
        self.buttons = self.make_buttons()
        self.choice_buttons = self.make_choice_buttons()  # 대화창 선택 버튼 2개
        self.reset_round()
        self.state = config.START_STATE  # 처음 보여 줄 화면(타이틀)

    def reset_round(self):
        """한 판에 쓰는 값을 모두 처음으로 되돌린다: 새 제자, 쿨타임 0, 엔딩 없음, 연출 비움.

        제자를 새로 만들므로 특성·외형·연계 플래그·이벤트 기록도 함께 초기화된다.
        떠 있던 대화창(current_event)과 자동형 알림도 비운다.
        """
        self.student = Student()
        self.cooldown = config.ZERO_TIME  # 남은 쿨타임(초). 0이면 행동할 수 있다
        self.ending = None                # 엔딩 이름. 엔딩 전에는 None
        self.current_event = None         # 대화창에 떠 있는 선택지형 이벤트. 없으면 None
        self.clear_effects()

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
        게임 화면에 남아 있던 파티클·팝업·눌림·점프 연출과 이벤트 알림·대화창은 비운다.
        """
        self.ending = ending
        self.state = config.STATE_ENDING
        self.current_event = None
        self.update_best_record(self.student.knowledge)
        self.clear_effects()

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

    def make_choice_buttons(self):
        """대화창의 선택 버튼 2개를 리스트로 만든다. 글자는 이벤트가 뜰 때 채운다."""
        return [Button(config.CHOICE_BUTTON_X, y, config.CHOICE_BUTTON_WIDTH,
                       config.CHOICE_BUTTON_HEIGHT, "")
                for y in config.CHOICE_BUTTON_YS]

    def is_cooling_down(self):
        """쿨타임 중이면 True를 돌려준다(소수 오차는 TIME_EPSILON 만큼 허용)."""
        return self.cooldown > config.TIME_EPSILON

    def do_action(self, name):
        """행동 name(feed/rest/study)을 실행하고 쿨타임 1초를 시작한다.

        게임 화면이 아니거나 쿨타임 중이면 아무것도 하지 않는다.
        실행했으면 True, 무시했으면 False를 돌려준다. 세 행동이 쿨타임 하나를 함께 쓴다.
        행동으로 체력이나 멘탈이 0이 되면 그 즉시 휴학 엔딩으로 바꾼다.
        실제로 실행됐을 때만 연출(눌림·파티클·팝업·점프·게이지 애니메이션)을 시작한다.
        휴학으로 끝나면 end_game이 연출을 다시 비운다.
        휴학이 아니면 랜덤 이벤트를 판정한다(roll_event). 대화창이 떠 있는 동안에는
        상태가 게임 화면이 아니므로 행동이 무시된다.
        """
        if self.state != config.STATE_PLAYING or self.is_cooling_down():
            return False
        before = self.get_gauge_values()
        if name == config.ACTION_FEED:
            self.student.feed()
        elif name == config.ACTION_REST:
            self.student.rest()
        elif name == config.ACTION_STUDY:
            self.student.study()
        else:
            return False
        self.cooldown = config.ACTION_COOLDOWN
        self.start_action_effects(name, before)
        if not self.check_ending():
            self.roll_event()
        return True

    # ------------------------------------------------------------
    # 랜덤 이벤트 (기획서 9절, jeja-spec 14절)
    # ------------------------------------------------------------
    def roll_event(self):
        """행동 직후 이벤트가 뜰지 정하고, 뜨면 시작한다. 뜬 이벤트(dict) 또는 None을 돌려준다.

        그 학년 이벤트 수가 최대(5)면 뜨지 않는다. 최소 보장 조건이면 반드시 뜨고,
        아니면 rng.random() < EVENT_CHANCE(25%)일 때 뜬다.
        """
        if not self.student.can_have_event():
            return None
        if not (self.student.needs_guaranteed_event()
                or self.rng.random() < config.EVENT_CHANCE):
            return None
        event = self.pick_event()
        self.start_event(event)
        return event

    def get_event_candidates(self):
        """지금 나올 수 있는 (선택지형 후보 목록, 자동형 후보 목록)을 돌려준다.

        학년 조건·연계 조건을 만족하고, 선택지형은 이번 판에 아직 안 나온 것만 모은다.
        """
        choices = [event for event in config.CHOICE_EVENTS if self.student.can_see_event(event)]
        autos = [event for event in config.AUTO_EVENTS if self.student.can_see_event(event)]
        return choices, autos

    def pick_event(self):
        """후보 중 이벤트 하나를 골라 돌려준다.

        선택지형 후보가 있으면 EVENT_CHOICE_RATIO(50%) 확률로 선택지형, 아니면 자동형에서 고른다.
        같은 종류 안에서는 rng.choice로 하나를 고른다.
        """
        choices, autos = self.get_event_candidates()
        if choices and self.rng.random() < config.EVENT_CHOICE_RATIO:
            return self.rng.choice(choices)
        return self.rng.choice(autos)

    def start_event(self, event):
        """이벤트 event를 시작하고 그 학년 이벤트 수를 하나 늘린다.

        - 자동형: 효과를 바로 적용하고 알림 배너(2초)와 수치 팝업을 띄운 뒤 휴학을 판정한다.
        - 선택지형: 한 판 1회로 기록하고, 선택 버튼 글자를 채운 뒤 대화 상태로 바꾼다(게임 정지).
        """
        self.student.count_event()
        if event[config.EVENT_KIND] == config.EVENT_KIND_AUTO:
            before = self.get_gauge_values()
            self.student.apply_effects(event[config.EVENT_EFFECTS])
            self.notice = {"text": config.EVENT_NOTICE_TEXT.format(event[config.EVENT_TITLE]),
                           "timer": config.EVENT_NOTICE_TIME}
            self.start_gauge_effects(before, len(self.popups))
            self.check_ending()
            return
        self.student.mark_event_seen(event[config.EVENT_ID])
        self.current_event = event
        options = event[config.EVENT_OPTIONS]
        for number, (button, option) in enumerate(zip(self.choice_buttons, options),
                                                  config.CHOICE_NUMBER_START):
            button.text = config.CHOICE_BUTTON_TEXT.format(number, option[config.OPTION_TEXT])
        self.state = config.STATE_EVENT

    def choose_option(self, index):
        """대화창에서 index번째(0 또는 1) 선택지를 고른다.

        효과·특성·외형·연계 플래그를 적용하고 수치 팝업을 띄운 뒤 게임을 다시 흐르게 한다.
        그 결과 체력·멘탈이 0이면 바로 휴학 엔딩이다.
        대화창이 떠 있지 않으면 아무것도 하지 않는다. 골랐으면 True, 아니면 False를 돌려준다.
        """
        if self.state != config.STATE_EVENT or self.current_event is None:
            return False
        option = self.current_event[config.EVENT_OPTIONS][index]
        before = self.get_gauge_values()
        self.student.apply_option(option)
        self.current_event = None
        self.state = config.STATE_PLAYING
        self.start_gauge_effects(before, len(self.popups))
        self.check_ending()
        return True

    def handle_event(self, event):
        """이벤트 하나를 받아 처리한다.

        - 창 닫기(QUIT) 또는 ESC: 모든 화면에서 running을 False로 바꾼다.
        - 타이틀 화면에서 Enter: 새 판 시작.
        - 엔딩 화면에서 R: 새 판 시작.
        - 게임 화면에서 마우스 왼쪽 클릭이 버튼 위면, 또는 1/2/3 키면 그 행동을 한다.
        - 마우스 이동(MOUSEMOTION): 버튼 호버 표시에 쓸 마우스 위치를 기억한다.
        - 마우스가 창 밖으로 나감(WINDOWLEAVE): 마우스 위치를 잊어 호버 표시를 끈다.
        - 대화창(선택지형 이벤트)이 떠 있으면 키 1/2 또는 선택 버튼 클릭으로 선택지를 고른다.
          이때 행동 키(3 포함)·행동 버튼은 무시한다.
        다른 화면의 Enter/R, 다른 키는 무시한다. 쿨타임 중이면 do_action이 입력을 무시한다.
        """
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
        elif event.type == pygame.WINDOWLEAVE:
            self.mouse_pos = None
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
        elif self.state == config.STATE_EVENT:
            if event.type == pygame.KEYDOWN and event.key in CHOICE_KEYS:
                self.choose_option(CHOICE_KEYS[event.key])
            elif (event.type == pygame.MOUSEBUTTONDOWN
                  and event.button == pygame.BUTTON_LEFT):
                for index, button in enumerate(self.choice_buttons):
                    if button.is_clicked(event.pos):
                        self.choose_option(index)
                        break

    def update(self, dt):
        """dt초만큼 게임 상태를 진행한다.

        게임 화면일 때만 제자의 시간을 흘려 게이지를 자연 감소시키고,
        남은 쿨타임도 dt만큼 줄인다(0 아래로는 내려가지 않음).
        그다음 엔딩을 확인한다: 자연 감소로 체력·멘탈이 0이 되었으면 휴학,
        아니면 240초가 되었을 때 졸업. 그래서 240초 시점에 0이 겹치면 휴학이 먼저다.
        타이틀·엔딩 화면과 대화창(선택지형 이벤트)이 떠 있는 동안에는
        시간·게이지·쿨타임이 흐르지 않는다(게임 정지).
        마지막으로 화면 연출 시계를 진행한다(update_effects, 게임 결과에는 영향 없음).
        """
        if self.state == config.STATE_PLAYING:
            self.student.update(dt)
            self.cooldown = max(config.ZERO_TIME, self.cooldown - dt)
            self.check_ending()
        self.update_effects(dt)

    # ------------------------------------------------------------
    # 화면 연출 E1~E6 (보기만 바꾸며 게이지·쿨타임·학년·엔딩에는 영향이 없다)
    # ------------------------------------------------------------
    def clear_effects(self):
        """파티클·팝업·버튼 눌림·점프·숨쉬기·게이지 애니메이션·이벤트 알림을 모두 처음 상태로 비운다.

        새 판 시작(reset_round)과 엔딩 진입(end_game)에서 부른다.
        """
        self.notice = None         # 자동형 이벤트 알림 {"text": 글자, "timer": 남은 시간}. 없으면 None
        self.particles = []        # 파티클 dict 리스트 (E2)
        self.popups = []           # 수치 팝업 dict 리스트 (E3)
        self.press_timers = {}     # {행동 이름: 버튼이 눌린 채 남은 시간(초)} (E1)
        self.jump_timer = config.ZERO_TIME   # 점프 남은 시간(초) (E5)
        self.breath_time = config.ZERO_TIME  # 숨쉬기 시계(초) (E5)
        # E4: 표시값 = 실제 값 + gauge_lag. 행동 직후에는 "바뀌기 전 값" 쪽에 있다가
        # gauge_lag_speed(1초에 줄어드는 양)로 0까지 줄어든다. 새 판에서는 0(표시값 = 실제 값)
        self.gauge_lag = {name: config.ZERO_TIME for name in config.GAUGE_NAMES}
        self.gauge_lag_speed = {name: config.ZERO_TIME for name in config.GAUGE_NAMES}

    def get_gauge_values(self):
        """지금 체력·멘탈·지식 값을 {속성 이름: 값} 사전으로 돌려준다(행동 전후 비교용)."""
        return {name: getattr(self.student, name) for name, _ in config.POPUP_GAUGES}

    def get_shown_gauge(self, name):
        """게이지 name(health/mental)의 막대 표시값(E4)을 돌려준다: 실제 값 + 남은 차이.

        값을 직접 바꿔도(테스트 등) 남은 차이가 0이면 표시값은 곧바로 실제 값이다.
        """
        return getattr(self.student, name) + self.gauge_lag[name]

    def start_action_effects(self, name, before):
        """행동 name이 실제로 실행된 직후 연출을 시작한다.

        before는 행동 전 게이지 값 사전이다. 버튼 눌림, 제자 점프, 파티클을 시작하고,
        실제로 바뀐 양(clamp 반영)으로 수치 팝업과 게이지 애니메이션을 만든다.
        """
        self.press_timers[name] = config.BUTTON_PRESS_TIME
        self.jump_timer = config.JUMP_TIME
        self.spawn_particles(name)
        self.start_gauge_effects(before)

    def start_gauge_effects(self, before, skip_rows=config.NO_OFFSET):
        """게이지가 before에서 지금 값으로 바뀐 만큼 수치 팝업(E3)과 게이지 애니메이션(E4)을 시작한다.

        행동과 이벤트(자동형 효과, 선택지 결과)가 함께 쓴다. 변화가 0인 게이지는 팝업을 띄우지 않는다.
        skip_rows는 머리 위에서 비워 둘 팝업 줄 수다. 이벤트는 이미 떠 있는 팝업 수를 넘겨
        행동 팝업 위에 쌓는다(글자가 겹치지 않게).
        """
        after = self.get_gauge_values()
        changes = [(label, after[key] - before[key]) for key, label in config.POPUP_GAUGES
                   if after[key] != before[key]]
        self.spawn_popups(changes, skip_rows)
        for key in config.GAUGE_NAMES:
            # 막대는 바뀌기 전 길이에서 출발해 GAUGE_ANIM_TIME 동안 새 길이로 간다
            self.gauge_lag[key] += before[key] - after[key]
            self.gauge_lag_speed[key] = abs(self.gauge_lag[key]) / config.GAUGE_ANIM_TIME

    def spawn_particles(self, name):
        """행동 name의 도트 파티클 PARTICLE_COUNT개를 제자 얼굴 가장자리 근처에 만든다.

        random 대신 config의 방향·속도·수명·모양 표를 번호 순서대로 돌려 써서
        같은 입력이면 언제나 같은 자리에 같은 파티클이 나온다.
        """
        radius = self.student.get_radius()
        kinds = config.PARTICLE_KINDS[name]
        for index in range(config.PARTICLE_COUNT):
            dx, dy = config.PARTICLE_DIRECTIONS[index % len(config.PARTICLE_DIRECTIONS)]
            speed = config.PARTICLE_SPEEDS[index % len(config.PARTICLE_SPEEDS)]
            sprite, colors = kinds[index % len(kinds)]
            start = radius * config.PARTICLE_START_RATIO
            self.particles.append({
                "x": config.STUDENT_CENTER_X + dx * start,
                "y": config.STUDENT_CENTER_Y + dy * start,
                "vx": dx * speed,
                "vy": dy * speed - config.PARTICLE_RISE_SPEED,
                "age": config.ZERO_TIME,
                "life": config.PARTICLE_LIFETIMES[index % len(config.PARTICLE_LIFETIMES)],
                "sprite": sprite,
                "colors": colors,
            })

    def spawn_popups(self, changes, skip_rows=config.NO_OFFSET):
        """(라벨, 변화량) 목록으로 수치 팝업을 만든다. 변화가 0인 게이지는 이미 빠져 있다.

        팝업은 제자 머리 위(점프·숨쉬기 최고점보다 위)에 세로로 겹치지 않게 쌓는다.
        목록 순서(체력, 멘탈, 지식)대로 위에서 아래로 놓인다.
        skip_rows는 머리 위에서 비워 둘 줄 수다(이미 떠 있는 팝업 위에 쌓을 때 쓴다).
        """
        head_top = (config.STUDENT_CENTER_Y - self.student.get_radius()
                    - config.JUMP_HEIGHT - config.BREATH_HEIGHT)
        lowest_y = head_top - config.POPUP_HEAD_GAP - config.POPUP_LINE_HEIGHT // config.HALF
        # 아래 줄부터 거꾸로 놓는다: 목록의 마지막 항목이 머리 바로 위(rows_below = 0)
        for rows_below, (label, amount) in enumerate(reversed(changes)):
            if amount > config.NO_CHANGE:
                color = config.COLOR_POPUP_UP
            else:
                color = config.COLOR_POPUP_DOWN
            self.popups.append({
                "text": config.POPUP_TEXT.format(label, amount),
                "color": color,
                "y": lowest_y - (rows_below + skip_rows) * config.POPUP_LINE_HEIGHT,
                "age": config.ZERO_TIME,
            })

    def update_effects(self, dt):
        """연출용 시계를 dt초만큼 진행한다.

        깜빡임 시계는 모든 화면에서 흐른다. 나머지(눌림·점프·숨쉬기·파티클·팝업·
        게이지 애니메이션·자동형 알림)는 게임 화면과 대화창 화면에서만 흐른다.
        (대화창 중에도 연출만 마저 흐르고, 게임 시간·게이지·쿨타임은 update에서 멈춘다.)
        게임 결과 값은 건드리지 않는다.
        """
        self.blink_time += dt
        if self.state not in (config.STATE_PLAYING, config.STATE_EVENT):
            return
        if self.notice is not None:
            self.notice["timer"] -= dt
            if self.notice["timer"] <= config.TIME_EPSILON:
                self.notice = None
        self.breath_time += dt
        self.jump_timer = max(config.ZERO_TIME, self.jump_timer - dt)
        for name in self.press_timers:
            self.press_timers[name] = max(config.ZERO_TIME, self.press_timers[name] - dt)
        for particle in self.particles:
            particle["age"] += dt
        self.particles = [p for p in self.particles if p["age"] < p["life"]]
        for popup in self.popups:
            popup["age"] += dt
        self.popups = [p for p in self.popups if p["age"] < config.POPUP_TIME]
        for name in config.GAUGE_NAMES:
            step = self.gauge_lag_speed[name] * dt
            if abs(self.gauge_lag[name]) <= step:
                self.gauge_lag[name] = config.ZERO_TIME
            elif self.gauge_lag[name] > config.ZERO_TIME:
                self.gauge_lag[name] -= step
            else:
                self.gauge_lag[name] += step

    def get_student_lift(self):
        """제자가 지금 위로 뜬 높이(픽셀) = 점프 높이 + 숨쉬기 높이. PIXEL_SIZE 단위로 끊는다.

        - 점프: 남은 시간으로 진행률 p(0~1)를 구해 포물선 4 x p x (1-p) (가운데에서 최고 8px).
        - 숨쉬기: 1.5초 주기 삼각파(0 -> 1 -> 0) x 4px. math(sin) 대신 삼각파를 쓴다.
        """
        jump = config.ZERO_TIME
        if self.jump_timer > config.TIME_EPSILON:
            progress = config.FULL_RATIO - self.jump_timer / config.JUMP_TIME
            jump = (config.JUMP_HEIGHT * config.JUMP_CURVE
                    * progress * (config.FULL_RATIO - progress))
        half = config.BREATH_PERIOD / config.HALF
        phase = self.breath_time % config.BREATH_PERIOD
        breath = config.BREATH_HEIGHT * (config.FULL_RATIO - abs(phase - half) / half)
        return self.snap_to_pixel(jump) + self.snap_to_pixel(breath)

    def snap_to_pixel(self, value):
        """픽셀 값 value를 가장 가까운 PIXEL_SIZE 배수(정수)로 맞춘다(도트 계단 느낌)."""
        return round(value / config.PIXEL_SIZE) * config.PIXEL_SIZE

    def is_blink_on(self):
        """안내 문구 깜빡임이 "켜진" 차례면 True. BLINK_INTERVAL(0.5초)마다 바뀐다."""
        return int(self.blink_time / config.BLINK_INTERVAL) % config.HALF == config.BLINK_SHOW

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
        elif self.state == config.STATE_EVENT:
            self.draw_playing()
            self.draw_event_dialog()
        elif self.state == config.STATE_ENDING:
            self.draw_ending()
        pygame.display.flip()

    def draw_event_notice(self):
        """(임시, D단위에서 다듬음) 자동형 이벤트 알림 배너를 무대 위쪽에 그린다."""
        inner = draw_pixel_box(self.screen, config.EVENT_NOTICE_RECT, config.COLOR_YELLOW,
                               config.COLOR_YELLOW_LIGHT, config.COLOR_YELLOW_DARK,
                               drop=config.COLOR_DROP)
        text = render_text(self.font, self.notice["text"])
        rect = text.get_rect()
        rect.center = inner.center
        self.screen.blit(text, rect)

    def draw_event_dialog(self):
        """(임시, D단위에서 다듬음) 선택지형 이벤트 대화창: 도트 상자, 제목, 상황 한 줄, 선택 버튼 2개."""
        if self.current_event is None:
            return
        draw_pixel_box(self.screen, config.EVENT_DIALOG_RECT, config.COLOR_BG,
                       config.COLOR_PANEL_LIGHT, config.COLOR_PANEL_SHADOW,
                       drop=config.COLOR_DROP)
        for font, text, center_y in (
                (self.font, self.current_event[config.EVENT_TITLE], config.EVENT_DIALOG_TITLE_Y),
                (self.event_font, self.current_event[config.EVENT_TEXT],
                 config.EVENT_DIALOG_TEXT_Y)):
            surface = render_text(font, text)
            rect = surface.get_rect()
            rect.center = (config.EVENT_DIALOG_CENTER_X, center_y)
            self.screen.blit(surface, rect)
        for button in self.choice_buttons:
            hovered = self.mouse_pos is not None and button.is_clicked(self.mouse_pos)
            button.draw(self.screen, self.event_font, False, hovered)

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
        """키 안내 문구(예: "Enter를 눌러 시작") 앞에 작은 도트 화살표를 붙여 그린다.

        E6 깜빡임: 0.5초마다 화살표가 보였다 숨었다 하고, 숨은 차례에는 글자 색이
        살짝 옅어진다. 글자 자체는 늘 보여서 읽기 불편하지 않다.
        """
        if not self.is_blink_on():
            self.draw_text_center(self.font, text, center_y, config.COLOR_HINT_DIM)
            return
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
        self.student.draw_gauges(self.screen, self.font,
                                 self.get_shown_gauge(config.GAUGE_HEALTH),
                                 self.get_shown_gauge(config.GAUGE_MENTAL))
        self.student.draw(self.screen, self.get_student_lift())
        self.draw_stage_effects()
        if self.notice is not None:
            self.draw_event_notice()
        self.draw_buttons()

    def draw_stage_effects(self):
        """제자 무대 안에 파티클(E2)과 수치 팝업(E3)을 그린다.

        무대 패널 안쪽으로 그리기 영역을 잘라(set_clip) 두어서 파티클·팝업이
        패널 밖(버튼·상태 패널 쪽)으로 넘쳐 보이지 않게 한다.
        """
        stage = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH,
                            config.PANEL_HEIGHT)
        self.screen.set_clip(stage.inflate(-config.BOX_INSET, -config.BOX_INSET))
        for particle in self.particles:
            self.draw_particle(particle)
        for popup in self.popups:
            self.draw_popup(popup)
        self.screen.set_clip(None)

    def draw_particle(self, particle):
        """파티클 하나를 지금 나이(age)에 맞는 자리에 도트 스프라이트로 찍는다.

        자리 = 시작 자리 + 속도 x 나이 (위로 떠오르는 속도 포함). 도트 칸에 맞춰 끊는다.
        수명의 PARTICLE_SHRINK_RATIO가 지나면 칸 크기를 반으로 줄여 작아지며 사라진다.
        """
        age = particle["age"]
        cell = config.PIXEL_SIZE
        if age >= particle["life"] * config.PARTICLE_SHRINK_RATIO:
            cell = config.PIXEL_SIZE // config.HALF
        width, height = sprite_size(particle["sprite"], cell)
        center_x = particle["x"] + particle["vx"] * age
        center_y = particle["y"] + particle["vy"] * age
        left = self.snap_to_pixel(center_x - width / config.HALF)
        top = self.snap_to_pixel(center_y - height / config.HALF)
        draw_sprite(self.screen, particle["sprite"], left, top, cell, particle["colors"])

    def draw_popup(self, popup):
        """수치 팝업 하나("체력 +20")를 떠오른 높이에 굵은 글씨 + 남색 1px 그림자로 그린다.

        POPUP_BLINK_START가 지나면 POPUP_BLINK_STEP마다 보였다 숨었다 하며 사라진다.
        """
        age = popup["age"]
        if age >= config.POPUP_BLINK_START:
            step = int((age - config.POPUP_BLINK_START) / config.POPUP_BLINK_STEP)
            if step % config.HALF == config.BLINK_HIDE:
                return
        center = (config.STUDENT_CENTER_X, round(popup["y"] - config.POPUP_RISE_SPEED * age))
        outline = render_text(self.popup_font, popup["text"], config.COLOR_OUTLINE)
        rect = outline.get_rect()
        rect.center = center
        for dx, dy in config.POPUP_OUTLINE_OFFSETS:
            self.screen.blit(outline, rect.move(dx, dy))
        self.screen.blit(render_text(self.popup_font, popup["text"], popup["color"]), rect)

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
        """행동 버튼 3개와 그 아래 "누른 뒤 1초 동안 회색 (쿨타임)" 안내 문구를 그린다.

        E1: 마우스가 올라간 버튼은 밝게, 방금 실행된 버튼은 눌린 자리(4px 아래)에,
        쿨타임 중이면 세 버튼 모두 회색 + 1초에 걸쳐 차오르는 진행 막대를 그린다.
        """
        cooling_down = self.is_cooling_down()
        progress = None
        if cooling_down:
            progress = config.FULL_RATIO - self.cooldown / config.ACTION_COOLDOWN
        for name, button in self.buttons.items():
            hovered = self.mouse_pos is not None and button.is_clicked(self.mouse_pos)
            offset = config.NO_OFFSET
            if self.press_timers.get(name, config.ZERO_TIME) > config.TIME_EPSILON:
                offset = config.BUTTON_PRESS_OFFSET
            button.draw(self.screen, self.font, cooling_down, hovered, offset, progress)

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
