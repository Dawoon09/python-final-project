"""게임 전체(Game) 클래스가 들어 있는 파일."""

import json
import random
import sys

import pygame

import config
from button import (Button, draw_pixel_box, draw_progress_bar, draw_sprite, render_text,
                    sprite_size)
from student import Student

# 키보드 단축키 -> 일과표 방침 이름 (기획서 10절 조작키: 1/2/3)
POLICY_KEYS = {
    pygame.K_1: config.POLICY_STUDY_FOCUS,
    pygame.K_2: config.POLICY_BALANCED,
    pygame.K_3: config.POLICY_REST_FOCUS,
}

# 대화창(선택지형 이벤트)에서 키 -> 선택지 번호 (키 1: 첫 번째, 키 2: 두 번째)
CHOICE_KEYS = {
    pygame.K_1: config.CHOICE_FIRST,
    pygame.K_2: config.CHOICE_SECOND,
}

# 업그레이드 패널에서 고른 줄을 움직이는 키 -> 움직이는 방향(위 -1, 아래 +1)
PANEL_MOVE_KEYS = {
    pygame.K_UP: -config.UPGRADE_CURSOR_STEP,
    pygame.K_DOWN: config.UPGRADE_CURSOR_STEP,
}
# 업그레이드 패널에서 고른 항목을 사는 키 (Enter, 숫자판 Enter)
PANEL_BUY_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)


def format_time(seconds):
    """게임 시간 seconds(초)를 "3분 12초" 같은 글자로 바꿔 돌려준다(소수는 버린다).

    1분이 안 되면 "0분 45초"처럼 0분도 쓴다. 경과 시간과 졸업까지 걸린 시간에 쓴다.
    """
    minutes, rest = divmod(int(seconds + config.TIME_EPSILON), config.SECONDS_PER_MINUTE)
    return config.TIME_TEXT.format(minutes, rest)


def to_count(value):
    """record.json에서 읽은 값 value가 0 이상의 정수면 그대로, 아니면 0을 돌려준다.

    bool(True/False)도 int의 한 종류라서 따로 뺀다. 소수·문자열·음수·None은 모두 0이다.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        return config.BEST_RECORD_START
    if value < config.BEST_RECORD_START:
        return config.BEST_RECORD_START
    return value


class Game:
    """메인 루프와 화면 전환(타이틀/게임/엔딩), 시간 관리(자동 행동 시계 포함),
    일과표 방침, 기록 저장을 맡는 클래스."""

    def __init__(self, record_path=None, seed=None):
        """pygame을 켜고 800x600 창과 시계, 글꼴, 방침 버튼 3개, 첫 화면(타이틀)을 준비한다.

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
        # 긴 엔딩 이름("대학원 12년차 수료")용 조금 작은 큰 글씨
        self.ending_font = pygame.font.SysFont(config.FONT_NAME, config.ENDING_LONG_FONT_SIZE)
        self.backdrop = self.make_backdrop()  # 도트 무늬 배경(한 번만 그려 둔다)
        self.popup_font = pygame.font.SysFont(config.FONT_NAME, config.POPUP_FONT_SIZE,
                                              bold=config.POPUP_FONT_BOLD)
        self.event_font = pygame.font.SysFont(config.FONT_NAME, config.EVENT_FONT_SIZE)
        self.small_font = pygame.font.SysFont(config.FONT_NAME, config.SMALL_FONT_SIZE)
        self.notice_font = pygame.font.SysFont(config.FONT_NAME, config.EVENT_NOTICE_FONT_SIZE)
        self.mouse_pos = None            # 마지막 마우스 위치(MOUSEMOTION). None이면 아직 모름
        self.blink_time = config.ZERO_TIME  # 안내 문구 깜빡임 시계(모든 화면에서 흐른다)

        self.running = True             # False가 되면 메인 루프가 끝난다
        # record.json에서 최고 기록(best_record)·연구비(money)·명성(fame)·업그레이드 레벨(upgrades)을 읽는다
        self.load_record()
        self.graduation_bonus = config.MONEY_START  # 이번 판 졸업 보너스(엔딩 화면 표시용)
        self.upgrade_panel_open = False    # 업그레이드 패널이 열려 있으면 True
        self.upgrade_cursor = config.UPGRADE_CURSOR_START  # 패널에서 고른 줄 번호(↑↓)
        self.buttons = self.make_buttons()
        self.choice_buttons = self.make_choice_buttons()  # 대화창 선택 버튼 2개
        # [업그레이드 U] 버튼: 게임 화면용, 엔딩 화면용(가운데 패널 아래)
        self.upgrade_button = Button(config.UPGRADE_BUTTON_X, config.UPGRADE_BUTTON_Y,
                                     config.BUTTON_WIDTH, config.BUTTON_HEIGHT,
                                     config.UPGRADE_BUTTON_TEXT)
        self.ending_upgrade_button = Button(config.UPGRADE_BUTTON_X, config.UPGRADE_BUTTON_ENDING_Y,
                                            config.BUTTON_WIDTH, config.BUTTON_HEIGHT,
                                            config.UPGRADE_BUTTON_TEXT)
        # 무대 배경(J단위): 장소·계절·시설·그늘 단계가 바뀔 때만 다시 그리는 배경 그림과 그 열쇠
        self.scenery = None
        self.scenery_key = None
        # 해·달·행동 소품은 모양이 바뀌지 않으므로 처음에 한 번만 그려 둔다
        self.sky_objects = {
            config.TIME_DAY: self.make_sprite_surface(config.SUN_SPRITE, config.SUN_COLORS),
            config.TIME_EVENING: self.make_sprite_surface(config.SUN_SPRITE,
                                                          config.EVENING_SUN_COLORS),
            config.TIME_NIGHT: self.make_sprite_surface(config.MOON_SPRITE, config.MOON_COLORS),
        }
        self.prop_surfaces = {name: self.make_sprite_surface(grid, config.PROP_COLORS)
                              for name, grid in config.PROP_SPRITES.items()}
        self.reset_round()
        self.state = config.START_STATE  # 처음 보여 줄 화면(타이틀)

    def reset_round(self):
        """한 판에 쓰는 값을 모두 처음으로 되돌린다: 새 제자, 엔딩 없음, 연출 비움.

        일과표 방침은 시작값(균형)으로, 자동 행동 시계는 2초(첫 행동은 시작 2초 뒤)로,
        마지막 행동(last_action)은 None으로 돌린다.
        제자를 새로 만들므로 특성·외형·연계 플래그·이벤트 기록도 함께 초기화된다.
        떠 있던 대화창(current_event)과 자동형 알림도 비운다.
        """
        self.student = Student(self.upgrades)  # 업그레이드 사전을 함께 쓴다(산 효과가 바로 적용)
        self.policy = config.POLICY_START   # 일과표 방침 이름. 시작값은 균형
        self.auto_timer = self.get_auto_interval()  # 다음 자동 행동까지 남은 시간(초)
        self.graduation_bonus = config.MONEY_START
        self.last_action = None             # 마지막으로 실행된 행동 이름. 아직 없으면 None
        self.ending = None                # 엔딩 이름. 엔딩 전에는 None
        self.current_event = None         # 대화창에 떠 있는 선택지형 이벤트. 없으면 None
        self.clear_effects()

    def start_new_game(self):
        """새 판을 시작한다: 모든 값을 초기화하고 바로 게임 화면으로 간다.

        타이틀에서 Enter, 엔딩에서 R을 누르면 이 메서드가 불린다.
        """
        self.reset_round()
        self.state = config.STATE_PLAYING

    # ------------------------------------------------------------
    # 졸업 후: 환생과 대학원 (기획서 10절, I단위)
    # ------------------------------------------------------------
    @property
    def grad_year(self):
        """대학원 년차(0이면 학부, n이면 대학원 n년차). 값은 제자(Student)가 가지고 있다.

        제자 한 명이 학부 -> 대학원으로 이어지므로 년차도 제자에게 두고,
        Game에서는 game.grad_year로 읽고 쓸 수 있게 이어 준다.
        """
        return self.student.grad_year

    @grad_year.setter
    def grad_year(self, value):
        """대학원 년차를 value로 바꾼다(제자의 grad_year를 바꾼다)."""
        self.student.grad_year = value

    def is_graduation_ending(self):
        """지금 엔딩이 학부 졸업(수석·무사·아슬아슬)이면 True. 이때만 C로 대학원에 갈 수 있다."""
        return (self.state == config.STATE_ENDING and self.grad_year == config.GRAD_YEAR_UNDERGRAD
                and self.ending in config.GRADUATION_BONUS)

    def is_grad_school_ending(self):
        """지금 엔딩이 "대학원 n년차 수료"면 True."""
        return self.state == config.STATE_ENDING and self.grad_year > config.GRAD_YEAR_UNDERGRAD

    def can_reincarnate(self):
        """지금 엔딩에서 환생(명성 +1)할 수 있으면 True: 학부 졸업 또는 대학원 수료 엔딩.

        휴학 엔딩은 졸업하지 않았으므로 False(R은 그냥 다시 하기).
        """
        return self.is_graduation_ending() or self.is_grad_school_ending()

    def reincarnate(self):
        """환생: 명성 +1 하고 record.json에 저장한 뒤, 새 신입생으로 처음부터 시작한다.

        업그레이드 레벨과 연구비는 그대로 남는다(새 판에도 효과 유지).
        엔딩 화면에서 R을 눌렀을 때 졸업·대학원 수료 엔딩이면 이 메서드가 불린다.
        """
        self.fame += config.FAME_STEP
        self.save_record()
        self.start_new_game()

    def enter_grad_school(self):
        """대학원 진학: 졸업한 같은 제자로 "대학원 1년차"를 이어서 시작한다.

        게이지·특성·외형·지식·연계 플래그는 그대로 두고, 게임 화면으로 돌아간다.
        60초 주기 시계(경과 시간)는 졸업한 시각에서 이어서 흐른다(기획서 11절).
        자동 행동 시계는 2초(간격)부터 다시 잰다. 학부 졸업 엔딩이 아니면 아무것도 하지 않는다.
        들어갔으면 True, 아니면 False를 돌려준다.
        """
        if not self.student.enter_grad_school():
            return False
        self.ending = None
        self.graduation_bonus = config.MONEY_START
        self.current_event = None
        self.auto_timer = self.get_auto_interval()
        self.clear_effects()
        self.state = config.STATE_PLAYING
        self.check_promotion()   # 졸업할 때 이미 1년차 목표를 넘었으면 바로 오른다
        return True

    def end_game(self, ending):
        """엔딩 이름 ending을 저장하고 엔딩 화면으로 바꾼다.

        휴학·졸업·대학원 수료 모두 여기를 지나간다. 졸업이면 졸업 보너스(수석 200 / 무사 100 /
        아슬아슬 50 x 명성 배수, 내림)를 연구비에 더한다. 휴학·대학원 수료면 보너스는 없다.
        이번 판 누적 지식이 최고 기록보다 크면 최고 기록을 바꾸고, 판이 끝났으므로
        연구비·명성·업그레이드와 함께 record.json에 저장한다.
        게임 화면에 남아 있던 파티클·팝업·눌림·점프 연출과 이벤트 알림·대화창은 비운다.
        """
        self.ending = ending
        self.state = config.STATE_ENDING
        self.current_event = None
        self.graduation_bonus = config.MONEY_START
        if ending in config.GRADUATION_BONUS:
            self.graduation_bonus = self.floor_money(config.GRADUATION_BONUS[ending]
                                                     * self.get_money_multiplier())
            self.money += self.graduation_bonus
        self.update_best_record(self.student.knowledge)
        self.save_record()
        self.clear_effects()

    # ------------------------------------------------------------
    # 기록 (record.json): 최고 기록·연구비·명성·업그레이드 레벨
    # ------------------------------------------------------------
    def read_record_file(self):
        """record.json을 읽어 {"best_knowledge", "money", "fame", "upgrades"} 사전으로 돌려준다.

        값마다 따로 검사해서 0 이상의 정수가 아니면 0으로 본다. 업그레이드 레벨은
        모든 id를 채우고, 0~최대 레벨 밖이거나 정수가 아니면 0으로 본다.
        예전 형식({"best_knowledge": n})은 연구비·명성·업그레이드를 0으로 본다.
        파일이 없거나, 읽을 수 없거나, JSON이 깨졌거나, 사전이 아니면 모두 0이다.
        어떤 경우에도 멈추지 않는다. 화면 속 값(self.money 등)은 바꾸지 않는다.
        """
        try:
            with open(self.record_path, encoding=config.RECORD_ENCODING) as file:
                data = json.load(file)
        except (OSError, ValueError):
            # OSError: 파일 없음·권한 없음 등 / ValueError: JSON 깨짐·글자 깨짐
            data = {}
        if not isinstance(data, dict):
            data = {}
        saved_upgrades = data.get(config.RECORD_UPGRADES_KEY)
        if not isinstance(saved_upgrades, dict):
            saved_upgrades = {}
        upgrades = {}
        for upgrade_id in config.UPGRADE_IDS:
            level = to_count(saved_upgrades.get(upgrade_id))
            if level > config.UPGRADES_BY_ID[upgrade_id][config.UPGRADE_MAX_LEVEL]:
                level = config.LEVEL_START
            upgrades[upgrade_id] = level
        return {
            config.RECORD_KEY: to_count(data.get(config.RECORD_KEY)),
            config.RECORD_MONEY_KEY: to_count(data.get(config.RECORD_MONEY_KEY)),
            config.RECORD_FAME_KEY: to_count(data.get(config.RECORD_FAME_KEY)),
            config.RECORD_UPGRADES_KEY: upgrades,
        }

    def load_record(self):
        """record.json에서 최고 기록·연구비·명성·업그레이드 레벨을 읽어 Game에 넣는다.

        읽은 사전(read_record_file 결과)을 돌려준다. 이미 제자가 있으면
        제자도 새 업그레이드 사전을 함께 쓰도록 바꿔 준다.
        """
        data = self.read_record_file()
        self.best_record = data[config.RECORD_KEY]     # 최고 기록(지식). 타이틀에 표시
        self.money = data[config.RECORD_MONEY_KEY]     # 연구비
        self.fame = data[config.RECORD_FAME_KEY]       # 명성 (I단위에서 환생으로 오른다)
        self.upgrades = data[config.RECORD_UPGRADES_KEY]  # {업그레이드 id: 레벨}
        if hasattr(self, "student"):
            self.student.upgrades = self.upgrades
        return data

    def save_record(self):
        """최고 기록·연구비·명성·업그레이드 레벨을 record.json에 저장한다.

        형식: {"best_knowledge": n, "money": n, "fame": n, "upgrades": {id: 레벨, ...}}.
        저장에 실패하면(폴더 권한 없음 등) False를 돌려주고 게임은 그대로 계속한다.
        성공하면 True를 돌려준다.
        """
        data = {
            config.RECORD_KEY: self.best_record,
            config.RECORD_MONEY_KEY: self.money,
            config.RECORD_FAME_KEY: self.fame,
            config.RECORD_UPGRADES_KEY: dict(self.upgrades),
        }
        try:
            with open(self.record_path, "w", encoding=config.RECORD_ENCODING) as file:
                json.dump(data, file)
        except OSError:
            return False
        return True

    def load_best_record(self):
        """record.json의 최고 기록(지식)만 읽어 돌려준다(예전 이름, 0 이상 정수가 아니면 0)."""
        return self.read_record_file()[config.RECORD_KEY]

    def save_best_record(self):
        """예전 이름. save_record와 같다(최고 기록과 함께 연구비·명성·업그레이드도 저장)."""
        return self.save_record()

    def update_best_record(self, knowledge):
        """knowledge가 최고 기록보다 크면 최고 기록을 바꾸고 파일에 저장한다.

        바뀌었으면 True, 같거나 작아서 그대로면 False를 돌려준다.
        """
        if knowledge <= self.best_record:
            return False
        self.best_record = knowledge
        self.save_best_record()
        return True

    def check_promotion(self):
        """누적 지식으로 진급·졸업·대학원 년차 오름을 판정하고, 오른 횟수(진급 수)를 돌려준다.

        지식이 바뀔 때마다(자동 행동·자동형 이벤트·선택지 직후) 부른다(기획서 11절).
        판정은 Student.promote가 한다. 학년은 내려가지 않고, 한 번에 여러 목표를 넘으면
        그만큼 오른다. 졸업(4학년에서 1100 이상)은 졸업 시각만 적고 진급 수에는 넣지 않는다.
        엔딩 화면으로 바꾸는 일은 check_ending이 한다(그래서 휴학이 졸업보다 먼저다).
        올랐으면 진급 알림("3학년 진급!" / "대학원 2년차!")을 2초 띄운다.
        """
        count = self.student.promote()
        if count > config.PROMOTION_COUNT_START:
            if self.student.is_in_grad_school():
                text = config.GRAD_PROMOTION_TEXT.format(self.grad_year)
            else:
                text = config.PROMOTION_TEXT.format(self.student.get_grade())
            self.promotion_notice = {"text": text, "timer": config.EVENT_NOTICE_TIME,
                                     "good": True}
        return count

    def check_ending(self):
        """제자 상태를 보고 엔딩이 났으면 엔딩 화면으로 바꾼다.

        휴학(체력·멘탈 0)이 졸업(4학년에서 누적 지식 1100 이상)보다 먼저다.
        판정은 Student.get_ending이 한다. 엔딩이 났으면 True, 아니면 False를 돌려준다.
        """
        ending = self.student.get_ending()
        if ending is None:
            return False
        self.end_game(ending)
        return True

    def make_buttons(self):
        """화면 아래쪽 왼편에 가로로 놓인 일과표 방침 버튼 3개를 {방침 이름: Button} 사전으로 만든다.

        순서는 공부 위주 [1], 균형 [2], 휴식 위주 [3]. 오른편은 업그레이드 버튼 자리로 비워 둔다.
        """
        buttons = {}
        for index, name in enumerate(config.POLICY_ORDER):
            x = config.BUTTON_START_X + index * (config.BUTTON_WIDTH + config.BUTTON_GAP)
            buttons[name] = Button(x, config.BUTTON_Y, config.BUTTON_WIDTH,
                                   config.BUTTON_HEIGHT, config.POLICIES[name][config.POLICY_TEXT])
        return buttons

    def make_choice_buttons(self):
        """대화창의 선택 버튼 2개를 리스트로 만든다. 글자는 이벤트가 뜰 때 채운다."""
        return [Button(config.CHOICE_BUTTON_X, y, config.CHOICE_BUTTON_WIDTH,
                       config.CHOICE_BUTTON_HEIGHT, "")
                for y in config.CHOICE_BUTTON_YS]

    # ------------------------------------------------------------
    # 일과표 방침과 자동 행동 (기획서 10절, G단위)
    # ------------------------------------------------------------
    def set_policy(self, name):
        """일과표 방침을 name(study_focus/balanced/rest_focus)으로 바꾼다.

        모르는 이름이면 바꾸지 않는다. 바꿨으면 True, 아니면 False를 돌려준다.
        고른 버튼은 잠깐 눌린 모양(E1)이 된다. 다음 자동 행동부터 새 방침을 따른다.
        """
        if name not in config.POLICIES:
            return False
        self.policy = name
        self.press_timers[name] = config.BUTTON_PRESS_TIME
        return True

    def choose_auto_action(self):
        """지금 방침으로 제자가 스스로 고를 행동 이름(feed/rest/study)을 돌려준다.

        체력이나 멘탈이 방침의 회복 기준 미만이면 둘 중 낮은 쪽을 회복한다:
        체력이 멘탈보다 낮거나 같으면 학식(feed), 멘탈이 더 낮으면 휴식(rest).
        둘 다 기준 이상이면 공부(study)한다.
        """
        threshold = config.POLICIES[self.policy][config.POLICY_THRESHOLD]
        health = self.student.health
        mental = self.student.mental
        if health < threshold or mental < threshold:
            if health <= mental:
                return config.ACTION_FEED
            return config.ACTION_REST
        return config.ACTION_STUDY

    def do_action(self, name):
        """행동 name(feed/rest/study)을 바로 실행한다(쿨타임 없음).

        게임 화면(STATE_PLAYING)이 아니거나 모르는 행동 이름이면 아무것도 하지 않는다.
        실행했으면 True, 무시했으면 False를 돌려준다. 실행하면 last_action에 이름을 남긴다.
        공부는 지금 방침의 지식 배수·소모 배수를 적용한다(학식·휴식은 방침과 상관없다).
        행동 뒤 진급·졸업을 판정하고(check_promotion), 체력이나 멘탈이 0이 되면
        그 즉시 휴학 엔딩, 졸업 목표를 넘었으면 졸업 엔딩으로 바꾼다(휴학이 먼저).
        실제로 실행됐을 때만 연출(파티클·팝업·점프·게이지 애니메이션)을 시작한다.
        엔딩으로 끝나면 end_game이 연출을 다시 비운다.
        엔딩이 아니면 랜덤 이벤트를 판정한다(roll_event). 대화창이 떠 있는 동안에는
        상태가 게임 화면이 아니므로 행동이 무시된다.
        보통은 update의 자동 행동 시계가 2초마다 부른다.
        """
        if self.state != config.STATE_PLAYING:
            return False
        before = self.get_gauge_values()
        if name == config.ACTION_FEED:
            self.student.feed()
        elif name == config.ACTION_REST:
            self.student.rest()
        elif name == config.ACTION_STUDY:
            policy = config.POLICIES[self.policy]
            self.student.study(policy[config.POLICY_KNOWLEDGE_RATIO],
                               policy[config.POLICY_COST_RATIO])
        else:
            return False
        self.last_action = name
        self.earn_knowledge_money(before[config.GAUGE_KNOWLEDGE])
        self.start_action_effects(name, before)
        self.check_promotion()
        if not self.check_ending():
            self.roll_event()
        return True

    def get_auto_interval(self):
        """자동 행동 간격(초)을 돌려준다: 2.0 - 0.2 x 시간 관리 레벨 (최대 5레벨이면 1.0)."""
        bonus = self.student.get_upgrade_bonus(config.UPGRADE_TIME)
        return round(config.AUTO_ACTION_INTERVAL - bonus, config.GAUGE_DECIMALS)

    def get_event_chance(self):
        """자동 행동 직후 이벤트가 뜰 확률: 0.25 + 0.05 x 행운 부적 레벨 (최대 0.40)."""
        bonus = self.student.get_upgrade_bonus(config.UPGRADE_CHARM)
        return round(config.EVENT_CHANCE + bonus, config.GAUGE_DECIMALS)

    # ------------------------------------------------------------
    # 연구비와 업그레이드 (기획서 10절, H단위)
    # ------------------------------------------------------------
    def floor_money(self, value):
        """연구비 계산 결과 value를 내림해 정수로 돌려준다(소수 오차를 MONEY_EPSILON 만큼 봐준다)."""
        return int(value + config.MONEY_EPSILON)

    def get_grad_money_multiplier(self):
        """대학원 연구비 배수 = 1 + 1.0 x 대학원 년차 를 돌려준다(학부는 1)."""
        return config.NO_RATIO + config.GRAD_MONEY_BONUS * self.grad_year

    def get_money_multiplier(self):
        """연구비 획득 배수 = (1 + 0.1 x 명성) x 대학원 배수 를 돌려준다."""
        fame_ratio = config.NO_RATIO + config.FAME_MONEY_BONUS * self.fame
        return fame_ratio * self.get_grad_money_multiplier()

    def earn_knowledge_money(self, knowledge_before):
        """지식이 knowledge_before에서 지금 값으로 오른 만큼 연구비를 쌓고, 쌓은 양을 돌려준다.

        연구비 += 내림(오른 양 x 연구비 배수). 지식이 그대로거나 줄었으면 0이다
        (지식이 줄어도 연구비는 줄지 않는다). 자동 행동·자동형 이벤트·선택지가 함께 쓴다.
        """
        gain = self.student.knowledge - knowledge_before
        if gain <= config.NO_CHANGE:
            return config.MONEY_START
        earned = self.floor_money(gain * self.get_money_multiplier())
        self.money += earned
        return earned

    def get_upgrade_cost(self, upgrade_id):
        """업그레이드 upgrade_id의 다음 레벨 가격 = 내림(기본 가격 x 2.0 ^ 지금 레벨)을 돌려준다.

        최고 레벨이어도 같은 식으로 계산한 값을 돌려준다(살 수 있는지는 can_buy_upgrade가 본다).
        """
        upgrade = config.UPGRADES_BY_ID[upgrade_id]
        level = self.upgrades[upgrade_id]
        return self.floor_money(upgrade[config.UPGRADE_BASE_COST]
                                * config.UPGRADE_COST_GROWTH ** level)

    def is_upgrade_maxed(self, upgrade_id):
        """업그레이드 upgrade_id가 최고 레벨이면 True."""
        max_level = config.UPGRADES_BY_ID[upgrade_id][config.UPGRADE_MAX_LEVEL]
        return self.upgrades[upgrade_id] >= max_level

    def can_buy_upgrade(self, upgrade_id):
        """업그레이드 upgrade_id를 지금 살 수 있으면 True.

        모르는 id, 최고 레벨, 연구비가 가격보다 적으면 False다.
        """
        if upgrade_id not in config.UPGRADES_BY_ID:
            return False
        if self.is_upgrade_maxed(upgrade_id):
            return False
        return self.money >= self.get_upgrade_cost(upgrade_id)

    def buy_upgrade(self, upgrade_id):
        """업그레이드 upgrade_id를 한 레벨 산다. 샀으면 True, 살 수 없으면 False.

        연구비에서 가격을 빼고 레벨을 1 올린다. 업그레이드 사전은 제자와 함께 쓰므로
        효과는 바로 적용된다. 시간 관리를 사면 남은 자동 행동 시간이 새 간격보다 길지 않게 줄인다.
        산 뒤 record.json에 저장한다.
        """
        if not self.can_buy_upgrade(upgrade_id):
            return False
        self.money -= self.get_upgrade_cost(upgrade_id)
        self.upgrades[upgrade_id] += config.LEVEL_STEP
        self.auto_timer = min(self.auto_timer, self.get_auto_interval())
        self.save_record()
        return True

    def toggle_upgrade_panel(self):
        """업그레이드 패널을 열거나 닫는다. 게임 화면·엔딩 화면에서만 된다.

        타이틀과 선택지형 대화창이 떠 있을 때는 바꾸지 않는다. 바꿨으면 True를 돌려준다.
        """
        if self.state not in (config.STATE_PLAYING, config.STATE_ENDING):
            return False
        self.upgrade_panel_open = not self.upgrade_panel_open
        return True

    def get_upgrade_row_rect(self, index):
        """업그레이드 패널의 index번째 항목 줄 사각형(클릭 판정·그리기용)을 돌려준다."""
        return pygame.Rect(config.UPGRADE_ROW_X,
                           config.UPGRADE_ROW_TOP + index * config.UPGRADE_ROW_STEP,
                           config.UPGRADE_ROW_WIDTH, config.UPGRADE_ROW_HEIGHT)

    def get_shown_upgrade_button(self):
        """지금 화면에 보이는 [업그레이드 U] 버튼을 돌려준다(엔딩이면 엔딩용, 아니면 게임용)."""
        if self.state == config.STATE_ENDING:
            return self.ending_upgrade_button
        return self.upgrade_button

    def handle_upgrade_input(self, event):
        """게임·엔딩 화면에서 업그레이드 관련 입력을 처리한다. 처리했으면 True를 돌려준다.

        - U 키 또는 [업그레이드 U] 버튼 클릭: 패널 열기/닫기
        - 패널이 열려 있을 때: ↑/↓로 줄 고르기, Enter로 고른 항목 사기,
          항목 줄 클릭으로 그 항목 고르고 사기
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_u:
                return self.toggle_upgrade_panel()
            if not self.upgrade_panel_open:
                return False
            if event.key in PANEL_MOVE_KEYS:
                self.upgrade_cursor = ((self.upgrade_cursor + PANEL_MOVE_KEYS[event.key])
                                       % len(config.UPGRADE_IDS))
                return True
            if event.key in PANEL_BUY_KEYS:
                self.buy_upgrade(config.UPGRADE_IDS[self.upgrade_cursor])
                return True
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_LEFT:
            if self.get_shown_upgrade_button().is_clicked(event.pos):
                return self.toggle_upgrade_panel()
            if not self.upgrade_panel_open:
                return False
            for index, upgrade_id in enumerate(config.UPGRADE_IDS):
                if self.get_upgrade_row_rect(index).collidepoint(event.pos):
                    self.upgrade_cursor = index
                    self.buy_upgrade(upgrade_id)
                    return True
        return False

    # ------------------------------------------------------------
    # 랜덤 이벤트 (기획서 9절, jeja-spec 14절)
    # ------------------------------------------------------------
    def roll_event(self):
        """자동 행동 직후 이벤트가 뜰지 정하고, 뜨면 시작한다. 뜬 이벤트(dict) 또는 None을 돌려준다.

        그 학년 이벤트 수가 최대(5)면 뜨지 않는다. 최소 보장 조건이면 반드시 뜬다(간격 예외).
        아니면 직전 이벤트 이후 게임 시간이 최소 간격(8초) 이상 지났고
        rng.random() < EVENT_CHANCE(25%)일 때 뜬다. 간격이 안 찼으면 난수를 뽑지 않는다.
        """
        if not self.student.can_have_event():
            return None
        if not self.student.needs_guaranteed_event():
            if not self.student.is_event_gap_passed():
                return None
            if self.rng.random() >= self.get_event_chance():
                return None
        event = self.pick_event()
        self.start_event(event)
        return event

    def get_event_candidates(self):
        """지금 나올 수 있는 (선택지형 후보 목록, 자동형 후보 목록)을 돌려준다.

        학년 조건·연계 조건을 만족하고, 선택지형은 이번 판에 아직 안 나온 것만 모은다.
        장학금 제도 업그레이드를 샀으면 자동형 후보에 "장학금을 받았다"가 더해진다.
        """
        auto_table = list(config.AUTO_EVENTS)
        if self.upgrades[config.UPGRADE_SCHOLARSHIP] > config.LEVEL_START:
            auto_table.append(config.SCHOLARSHIP_EVENT)
        choices = [event for event in config.CHOICE_EVENTS if self.student.can_see_event(event)]
        autos = [event for event in auto_table if self.student.can_see_event(event)]
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

        - 자동형: 효과를 바로 적용하고 알림(2초)과 수치 팝업을 띄운 뒤 진급·졸업과 휴학을 판정한다.
          알림 색은 효과 합의 부호로 정한다(0 이상이면 좋은 일, 음수면 나쁜 일).
        - 선택지형: 한 판 1회로 기록하고, 선택 버튼 글자를 채운 뒤 대화 상태로 바꾼다(게임 정지).
          대화창 시계(dialog_time)를 0부터 다시 잰다(입력 대기·등장 연출용).
        """
        self.student.count_event()
        if event[config.EVENT_KIND] == config.EVENT_KIND_AUTO:
            before = self.get_gauge_values()
            effects = event[config.EVENT_EFFECTS]
            self.student.apply_effects(effects)
            self.earn_knowledge_money(before[config.GAUGE_KNOWLEDGE])
            # 장학금: 연구비 +30 x 학년 (명성 배수 없이 그대로)
            scholarship = (event.get(config.EVENT_MONEY_PER_GRADE, config.MONEY_START)
                           * self.student.get_grade())
            self.money += scholarship
            self.notice = {"text": config.EVENT_NOTICE_TEXT.format(event[config.EVENT_TITLE]),
                           "timer": config.EVENT_NOTICE_TIME,
                           "good": sum(effects.values()) >= config.NO_CHANGE}
            self.start_gauge_effects(before, for_event=True)
            if scholarship > config.MONEY_START:
                self.spawn_event_popups([(config.MONEY_LABEL, scholarship)])
            self.check_promotion()
            self.check_ending()
            return
        self.student.mark_event_seen(event[config.EVENT_ID])
        self.current_event = event
        self.dialog_time = config.ZERO_TIME
        options = event[config.EVENT_OPTIONS]
        for number, (button, option) in enumerate(zip(self.choice_buttons, options),
                                                  config.CHOICE_NUMBER_START):
            button.text = config.CHOICE_BUTTON_TEXT.format(number, option[config.OPTION_TEXT])
        self.state = config.STATE_EVENT

    def is_dialog_ready(self):
        """대화창이 뜬 뒤 입력 대기 시간(EVENT_INPUT_DELAY, 0.3초)이 지났으면 True.

        그 전에는 선택 입력(키·클릭)을 무시한다. 행동 키를 연타하다가
        같은 키가 그대로 선택으로 들어가는 것을 막기 위해서다.
        """
        return self.dialog_time + config.TIME_EPSILON >= config.EVENT_INPUT_DELAY

    def choose_option(self, index):
        """대화창에서 index번째(0 또는 1) 선택지를 고른다.

        효과·특성·외형·연계 플래그를 적용하고 수치 팝업을 띄운 뒤 게임을 다시 흐르게 한다.
        그 결과로 진급·졸업을 판정하고, 체력·멘탈이 0이면 바로 휴학 엔딩이다(휴학이 졸업보다 먼저).
        대화창이 떠 있지 않거나, 뜬 지 아직 입력 대기 시간(0.3초)이 안 지났으면
        아무것도 하지 않는다. 골랐으면 True, 아니면 False를 돌려준다.
        """
        if self.state != config.STATE_EVENT or self.current_event is None:
            return False
        if not self.is_dialog_ready():
            return False
        option = self.current_event[config.EVENT_OPTIONS][index]
        before = self.get_gauge_values()
        self.student.apply_option(option)
        self.earn_knowledge_money(before[config.GAUGE_KNOWLEDGE])
        self.current_event = None
        self.state = config.STATE_PLAYING
        self.start_gauge_effects(before, for_event=True)
        self.check_promotion()
        self.check_ending()
        return True

    def handle_event(self, event):
        """이벤트 하나를 받아 처리한다.

        - 창 닫기(QUIT) 또는 ESC: 모든 화면에서 running을 False로 바꾼다.
        - 타이틀 화면에서 Enter: 새 판 시작.
        - 엔딩 화면에서 R: 졸업·대학원 수료 엔딩이면 환생(reincarnate, 명성 +1),
          휴학 엔딩이면 그냥 새 판 시작(명성 그대로).
        - 졸업 엔딩 화면에서 C: 대학원 진학(enter_grad_school).
        - 게임 화면에서 1/2/3 키 또는 방침 버튼 클릭: 일과표 방침을 바꾼다
          (1 공부 위주, 2 균형, 3 휴식 위주). 행동은 제자가 스스로 한다.
        - 마우스 이동(MOUSEMOTION): 버튼 호버 표시에 쓸 마우스 위치를 기억한다.
        - 마우스가 창 밖으로 나감(WINDOWLEAVE): 마우스 위치를 잊어 호버 표시를 끈다.
        - 대화창(선택지형 이벤트)이 떠 있으면 키 1/2 또는 선택 버튼 클릭으로 선택지를 고른다.
          이때 방침 키(3 포함)·방침 버튼·업그레이드 입력은 무시한다.
        - 게임·엔딩 화면에서 U 키 또는 [업그레이드 U] 버튼: 업그레이드 패널 열기/닫기.
          패널이 열려 있으면 ↑/↓·Enter·항목 클릭으로 업그레이드를 산다(handle_upgrade_input).
          게임 화면에서는 패널이 열려 있어도 1/2/3 방침 키와 방침 버튼이 그대로 동작한다.
        다른 화면의 Enter/R, 다른 키는 무시한다.
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
            if self.handle_upgrade_input(event):
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                if self.can_reincarnate():
                    self.reincarnate()
                else:
                    self.start_new_game()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                if self.is_graduation_ending():
                    self.enter_grad_school()
        elif self.state == config.STATE_PLAYING:
            if self.handle_upgrade_input(event):
                return
            if event.type == pygame.KEYDOWN and event.key in POLICY_KEYS:
                self.set_policy(POLICY_KEYS[event.key])
            elif (event.type == pygame.MOUSEBUTTONDOWN
                  and event.button == pygame.BUTTON_LEFT):
                for name, button in self.buttons.items():
                    if button.is_clicked(event.pos):
                        self.set_policy(name)
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
        자동 행동 시계(auto_timer)도 dt만큼 줄인다. 시계가 0이 되면 지금 방침으로
        행동을 골라(choose_auto_action) 실행하고(do_action) 시계를 다시 2초로 채운다.
        dt가 커서 자동 행동 시각을 여러 번 지나가면, 행동 시각마다 끊어서 차례대로 처리한다
        (행동 시각까지 시간을 흘림 -> 엔딩 확인 -> 행동 -> 남은 시간 계속).
        엔딩 확인: 자연 감소로 체력·멘탈이 0이 되었으면 휴학(대학원이면 "대학원 n년차 수료")이다.
        판에 시간 제한이 없으므로(기획서 11절) 시간이 지났다고 졸업하지는 않는다. 졸업은
        지식이 바뀔 때 check_promotion이 판정한다(여기서도 한 번 더 확인해 둔다).
        엔딩이 나면 그 시각의 자동 행동은 하지 않는다.
        타이틀·엔딩 화면과 대화창(선택지형 이벤트)이 떠 있는 동안에는
        시간·게이지·자동 행동 시계가 흐르지 않는다(게임 정지). 자동 행동 직후
        대화창이 뜨면 이번 dt의 남은 시간도 흘리지 않는다.
        마지막으로 화면 연출 시계를 진행한다(update_effects, 게임 결과에는 영향 없음).
        """
        remaining = dt
        while self.state == config.STATE_PLAYING:
            step = min(remaining, self.auto_timer)
            self.student.update(step)
            self.auto_timer -= step
            remaining -= step
            self.check_promotion()
            if self.check_ending():
                break
            if self.auto_timer > config.TIME_EPSILON:
                break   # 이번 dt 안에는 더 할 자동 행동이 없다
            self.auto_timer = self.get_auto_interval()
            self.do_action(self.choose_auto_action())
        self.update_effects(dt)

    # ------------------------------------------------------------
    # 화면 연출 E1~E6 (보기만 바꾸며 게이지·자동 행동 시계·학년·엔딩에는 영향이 없다)
    # ------------------------------------------------------------
    def clear_effects(self):
        """파티클·팝업·버튼 눌림·점프·숨쉬기·게이지 애니메이션·이벤트 알림을 모두 처음 상태로 비운다.

        새 판 시작(reset_round)과 엔딩 진입(end_game)에서 부른다.
        """
        # 자동형 이벤트 알림 {"text": 글자, "timer": 남은 시간, "good": 좋은 일이면 True}. 없으면 None
        self.notice = None
        # 진급 알림 {"text": "2학년 진급!", "timer": 남은 시간, "good": True}. 없으면 None
        self.promotion_notice = None
        self.dialog_time = config.ZERO_TIME  # 대화창이 뜬 뒤 흐른 시간(초): 입력 대기·등장 연출용
        self.particles = []        # 파티클 dict 리스트 (E2)
        self.popups = []           # 수치 팝업 dict 리스트 (E3)
        self.press_timers = {}     # {이름: 눌린 채 남은 시간(초)} (E1). 방침 버튼은 고를 때 눌린다
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

    def start_gauge_effects(self, before, for_event=False):
        """게이지가 before에서 지금 값으로 바뀐 만큼 수치 팝업(E3)과 게이지 애니메이션(E4)을 시작한다.

        행동과 이벤트(자동형 효과, 선택지 결과)가 함께 쓴다. 변화가 0인 게이지는 팝업을 띄우지 않는다.
        for_event가 True(이벤트)면 팝업을 머리 위가 아니라 무대 왼쪽 위 칸에 쌓는다
        (spawn_event_popups). 그래서 4학년(얼굴이 큼)에 행동 팝업 3줄과 이벤트 팝업이
        함께 떠도 무대 밖으로 잘리거나 서로 겹치지 않는다.
        """
        after = self.get_gauge_values()
        # 체력·멘탈이 소수(건강 관리 업그레이드)일 수 있으므로 변화량은 반올림한 정수로 보인다
        changes = [(label, round(after[key] - before[key])) for key, label in config.POPUP_GAUGES
                   if round(after[key] - before[key]) != config.NO_CHANGE]
        if for_event:
            self.spawn_event_popups(changes)
        else:
            self.spawn_popups(changes)
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
            self.add_popup(label, amount, config.STUDENT_CENTER_X,
                           lowest_y - (rows_below + skip_rows) * config.POPUP_LINE_HEIGHT)

    def spawn_event_popups(self, changes):
        """이벤트 결과 (라벨, 변화량) 목록으로 수치 팝업을 무대 왼쪽 위 칸에 위에서 아래로 쌓는다.

        머리 위 가운데는 행동 팝업 자리, 얼굴 양옆은 파티클 자리라서 비어 있는 왼쪽 위를 쓴다.
        자동형 알림이 떠 있으면 알림 상자 바로 아래부터, 없으면 무대 위쪽부터 쌓는다.
        목록 순서(체력, 멘탈, 지식)대로 위에서 아래로 놓인다.
        """
        top = config.PANEL_Y
        if self.notice is not None:
            top = config.EVENT_NOTICE_Y + config.EVENT_NOTICE_HEIGHT
        first_y = top + config.EVENT_POPUP_TOP_MARGIN
        for row, (label, amount) in enumerate(changes):
            self.add_popup(label, amount, config.EVENT_POPUP_X,
                           first_y + row * config.POPUP_LINE_HEIGHT)

    def add_popup(self, label, amount, x, y):
        """수치 팝업 하나("체력 +20")를 글자 가운데 (x, y)에 만든다. 늘면 초록, 줄면 빨강."""
        if amount > config.NO_CHANGE:
            color = config.COLOR_POPUP_UP
        else:
            color = config.COLOR_POPUP_DOWN
        self.popups.append({
            "text": config.POPUP_TEXT.format(label, amount),
            "color": color,
            "x": x,
            "y": y,
            "age": config.ZERO_TIME,
        })

    def update_effects(self, dt):
        """연출용 시계를 dt초만큼 진행한다.

        깜빡임 시계는 모든 화면에서 흐른다. 나머지(눌림·점프·숨쉬기·파티클·팝업·
        게이지 애니메이션·자동형 알림·진급 알림)는 게임 화면과 대화창 화면에서만 흐른다.
        (대화창 중에도 연출만 마저 흐르고, 게임 시간·게이지·자동 행동 시계는 update에서 멈춘다.)
        게임 결과 값은 건드리지 않는다.
        """
        self.blink_time += dt
        if self.state not in (config.STATE_PLAYING, config.STATE_EVENT):
            return
        if self.state == config.STATE_EVENT:
            self.dialog_time += dt   # 대화창 시계: 게임 시간은 멈춰도 이 시계는 흐른다
        if self.notice is not None:
            self.notice["timer"] -= dt
            if self.notice["timer"] <= config.TIME_EPSILON:
                self.notice = None
        if self.promotion_notice is not None:
            self.promotion_notice["timer"] -= dt
            if self.promotion_notice["timer"] <= config.TIME_EPSILON:
                self.promotion_notice = None
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
            if self.upgrade_panel_open:
                self.draw_upgrade_panel()
        elif self.state == config.STATE_EVENT:
            # 대화창이 떠 있는 동안에는 업그레이드 패널을 숨긴다(닫힌 것은 아니다)
            self.draw_playing()
            self.draw_pause_dots()
            self.draw_event_dialog()
        elif self.state == config.STATE_ENDING:
            self.draw_ending()
            self.draw_upgrade_button(self.ending_upgrade_button)
            if self.upgrade_panel_open:
                self.draw_upgrade_panel()
        pygame.display.flip()

    # ------------------------------------------------------------
    # 무대 배경 4겹 (기획서 10절 "배경", J단위)
    #   1) 장소(학년) 2) 하늘(계절·시간대) 3) 행동 소품 4) 시설
    #   계산 메서드(get_season 등)는 화면 없이도 부를 수 있다.
    # ------------------------------------------------------------
    def get_season_time(self):
        """(계절 번호 0~3, 그 계절 안에서 흐른 시간(초) 0~15)를 돌려준다.

        60초 주기 안 시간으로 정한다(기획서 11절): 0~15초 봄, 15~30초 여름,
        30~45초 가을, 45~60초 겨울(시험 기간). 학년·대학원 년차와는 상관없다.
        """
        time_in_term = self.student.get_cycle_time()
        index = int((time_in_term + config.TIME_EPSILON) // config.SEASON_SECONDS)
        index = min(index, len(config.SEASONS) - config.INDEX_STEP)
        time_in_season = time_in_term - index * config.SEASON_SECONDS
        return index, min(max(config.ZERO_TIME, time_in_season), config.SEASON_SECONDS)

    def get_season(self):
        """지금 계절 이름("spring"/"summer"/"autumn"/"winter")을 돌려준다."""
        index, _ = self.get_season_time()
        return config.SEASONS[index]

    def get_time_of_day(self):
        """지금 시간대("day"/"evening"/"night")를 돌려준다.

        계절 15초 안에서 0~9초 낮, 9~12초 저녁, 12~15초 밤이다.
        """
        _, time_in_season = self.get_season_time()
        if time_in_season + config.TIME_EPSILON < config.DAY_END:
            return config.TIME_DAY
        if time_in_season + config.TIME_EPSILON < config.EVENING_END:
            return config.TIME_EVENING
        return config.TIME_NIGHT

    def get_sky_color(self):
        """지금 하늘색 (R, G, B) 정수 튜플을 돌려준다.

        config.SKY_KEYFRAMES의 기준점 두 개 사이에서 시간 비율만큼 두 색을 섞는다(선형 보간).
        마지막 기준점(15초)은 다음 계절의 낮색이라 밤에서 다음 날 아침으로 자연스럽게 넘어간다.
        """
        index, time_in_season = self.get_season_time()
        frames = config.SKY_KEYFRAMES
        for start, end in zip(frames, frames[config.INDEX_STEP:]):
            start_time, start_name, start_skip = start
            end_time, end_name, end_skip = end
            if time_in_season <= end_time:
                ratio = (time_in_season - start_time) / (end_time - start_time)
                first = self.get_keyframe_color(index + start_skip, start_name)
                second = self.get_keyframe_color(index + end_skip, end_name)
                return tuple(round(a + (b - a) * ratio) for a, b in zip(first, second))
        _, last_name, last_skip = frames[-config.INDEX_STEP]
        return tuple(self.get_keyframe_color(index + last_skip, last_name))

    def get_keyframe_color(self, season_index, time_name):
        """계절 번호 season_index(4 이상이면 다음 해 봄부터 다시)의 시간대 time_name 하늘색."""
        season = config.SEASONS[season_index % len(config.SEASONS)]
        return config.SKY_COLORS[season][time_name]

    def get_place(self):
        """지금 장소 id를 돌려준다: 1학년 "lawn", 2학년 "lecture", 3학년 "library",
        4학년 "ceremony", 대학원 "lab"."""
        if self.grad_year > config.GRAD_YEAR_UNDERGRAD:
            return config.PLACE_LAB
        return config.PLACE_BY_GRADE[self.student.get_grade()]

    def get_owned_facilities(self):
        """산 시설(도서관·카페·헬스장) 업그레이드 id를 튜플로 돌려준다(배경 4겹째)."""
        return tuple(upgrade_id for upgrade_id in config.FACILITY_IDS
                     if self.upgrades[upgrade_id] >= config.FACILITY_OWNED_LEVEL)

    def make_sprite_surface(self, grid, colors, cell=config.SCENE_CELL):
        """스프라이트 grid를 한 번만 찍어 둔 Surface를 만들어 돌려준다.

        빈 칸은 COLOR_KEY(자홍색)로 칠하고 set_colorkey로 그 색을 빼고 붙인다(반투명 아님).
        매 프레임 칸을 하나씩 찍지 않고 이 Surface를 통째로 붙이면 빠르다.
        """
        surface = pygame.Surface(sprite_size(grid, cell))
        surface.fill(config.COLOR_KEY)
        surface.set_colorkey(config.COLOR_KEY)
        draw_sprite(surface, grid, config.NO_OFFSET, config.NO_OFFSET, cell, colors)
        return surface

    def get_scene_color(self, name, season, shade=config.SCENE_SHADE_NONE):
        """배경 색 이름 name의 색을 돌려준다. 계절 색(땅·잎·눈)이 먼저, 없으면 고정 색.

        겨울이 아닐 때의 "snow"처럼 그 계절에 없는 것은 None(그리지 않음)이다.
        shade(그늘 단계, 0이면 없음)가 있으면 밤 남색을 그 단계 비율만큼 섞은 색을 돌려준다.
        하늘 자리 색(COLOR_KEY)은 섞지 않는다(colorkey로 빠져야 하므로).
        """
        season_colors = config.SEASON_COLORS[season]
        if name in season_colors:
            color = season_colors[name]
        else:
            color = config.SCENE_COLORS[name]
        if color is None or shade == config.SCENE_SHADE_NONE or color == config.COLOR_KEY:
            return color
        ratio = config.SCENE_SHADE_RATIOS[shade]
        return tuple(round(a + (b - a) * ratio) for a, b in zip(color, config.SCENE_SHADE_COLOR))

    def get_scene_shade(self):
        """지금 배경 그늘 단계(0 = 낮, 클수록 어둡다)를 돌려준다.

        계절 안 시각으로 SCENE_SHADE_STEPS 표에서 찾는다(낮 0 -> 저녁 1 -> 밤 2 -> 새벽 1).
        실내(연구실)는 언제나 0이다. 단계가 몇 개뿐이라 배경을 다시 그리는 일이 적다.
        """
        if self.get_place() not in config.SCENE_SHADE_PLACES:
            return config.SCENE_SHADE_NONE
        _, time_in_season = self.get_season_time()
        shade = config.SCENE_SHADE_NONE
        for start_time, level in config.SCENE_SHADE_STEPS:
            if time_in_season + config.TIME_EPSILON >= start_time:
                shade = level
        return shade

    def draw_scene_sprite(self, surface, sprite_name, x, y, cell, season,
                          shade=config.SCENE_SHADE_NONE):
        """배경 스프라이트 sprite_name을 (x, y) 픽셀에 칸 크기 cell로 찍는다(계절 색·그늘 반영)."""
        grid, names = config.SCENE_SPRITES[sprite_name]
        colors = {}
        for char, name in names.items():
            color = self.get_scene_color(name, season, shade)
            if color is not None:
                colors[char] = color
        draw_sprite(surface, grid, x, y, cell, colors)

    def draw_scene_part(self, surface, part, season, shade=config.SCENE_SHADE_NONE):
        """배경 조각 하나(사각형 / 같은 사각형 여러 개 / 스프라이트)를 칸 단위 위치에 그린다."""
        cell = config.SCENE_CELL
        kind = part[config.FIRST_ROW]
        if kind == config.PART_SPRITE:
            _, sprite_name, col, row = part
            self.draw_scene_sprite(surface, sprite_name, col * cell, row * cell, cell, season,
                                   shade)
            return
        if kind == config.PART_RECT:
            _, name, col, row, width, height = part
            count_x, count_y, step_x, step_y = (config.SINGLE_COUNT, config.SINGLE_COUNT,
                                                config.NO_OFFSET, config.NO_OFFSET)
        else:
            _, name, col, row, count_x, count_y, width, height, step_x, step_y = part
        color = self.get_scene_color(name, season, shade)
        if color is None:
            return
        for i in range(count_x):
            for j in range(count_y):
                pygame.draw.rect(surface, color, ((col + i * step_x) * cell,
                                                  (row + j * step_y) * cell,
                                                  width * cell, height * cell))

    def make_scenery(self, place, season, facilities, shade=config.SCENE_SHADE_NONE):
        """장소·계절·시설·그늘 단계로 배경 그림(무대 안쪽 크기 Surface)을 새로 그려 돌려준다.

        순서: 장소 뒤쪽(땅·건물·나무) -> 산 시설 건물 -> 장소 앞쪽(벤치·꽃·의자 등).
        하늘 자리는 COLOR_KEY로 비워 두어(set_colorkey) 매 프레임 그린 하늘이 비쳐 보인다.
        연구실은 창유리만 비어 있어서 창밖으로 하늘(계절·시간대)이 보인다.
        shade가 0보다 크면(저녁·밤) 모든 색을 밤 남색 쪽으로 조금 섞어 어둡게 그린다.
        """
        inner = self.get_stage_inner()
        surface = pygame.Surface(inner.size)
        surface.fill(config.COLOR_KEY)
        surface.set_colorkey(config.COLOR_KEY)
        for part in config.PLACE_BACK[place]:
            self.draw_scene_part(surface, part, season, shade)
        for upgrade_id in facilities:
            x, bottom, cell = config.FACILITY_SLOTS[place][upgrade_id]
            sprite_name = config.FACILITY_SPRITES[upgrade_id]
            _, height = sprite_size(config.SCENE_SPRITES[sprite_name][config.FIRST_ROW], cell)
            self.draw_scene_sprite(surface, sprite_name, x, bottom - height, cell, season, shade)
        for part in config.PLACE_FRONT[place]:
            self.draw_scene_part(surface, part, season, shade)
        return surface

    def get_scenery(self):
        """지금 장소·계절·시설·그늘 단계에 맞는 배경 그림을 돌려준다.

        넷 중 하나라도 바뀌었을 때만 새로 그리고(make_scenery), 아니면 그려 둔 것을 다시 쓴다.
        그늘 단계는 계절마다 몇 번만 바뀌므로(낮 -> 저녁 -> 밤 -> 새벽) 다시 그리는 일이 적다.
        그래서 매 프레임에는 하늘색 채우기와 그림 붙이기만 한다(60 FPS 유지).
        """
        key = (self.get_place(), self.get_season(), self.get_owned_facilities(),
               self.get_scene_shade())
        if key != self.scenery_key:
            self.scenery = self.make_scenery(*key)
            self.scenery_key = key
        return self.scenery

    def draw_background(self):
        """제자 무대 안쪽에 배경 4겹을 그린다(제자·파티클·팝업·알림보다 먼저).

        하늘색 채우기 -> 해(낮)·노을 해(저녁)·달과 별(밤) -> 장소·시설 그림 -> 행동 소품.
        """
        inner = self.get_stage_inner()
        self.screen.fill(self.get_sky_color(), inner)
        self.screen.set_clip(inner)
        time_name = self.get_time_of_day()
        if time_name == config.TIME_NIGHT:
            for x, y in config.STAR_POSITIONS:
                pygame.draw.rect(self.screen, config.COLOR_STAR_NIGHT,
                                 (inner.left + x, inner.top + y,
                                  config.PIXEL_SIZE, config.PIXEL_SIZE))
        x, y = config.SKY_OBJECT_POS[self.get_place()][time_name]
        self.screen.blit(self.sky_objects[time_name], (inner.left + x, inner.top + y))
        self.screen.blit(self.get_scenery(), inner.topleft)
        self.draw_action_prop(inner)
        self.screen.set_clip(None)

    def draw_action_prop(self, inner):
        """마지막 자동 행동의 소품(공부: 책상과 책, 휴식: 이불, 학식: 식판)을 제자 오른쪽에 그린다.

        아직 행동이 없으면(last_action이 None) 아무것도 그리지 않는다.
        """
        prop = self.prop_surfaces.get(self.last_action)
        if prop is None:
            return
        self.screen.blit(prop, (inner.left + config.PROP_X,
                                inner.top + config.PROP_BOTTOM - prop.get_height()))

    # ------------------------------------------------------------
    # 업그레이드 화면 (H단위): [업그레이드 U] 버튼과 패널
    # ------------------------------------------------------------
    def draw_upgrade_button(self, button):
        """[업그레이드 U] 버튼을 그린다. 패널이 열려 있으면 노랑으로 강조, 마우스를 올리면 밝게."""
        hovered = self.mouse_pos is not None and button.is_clicked(self.mouse_pos)
        button.draw(self.screen, self.font, False, hovered,
                    selected=self.upgrade_panel_open)

    def draw_upgrade_panel(self):
        """업그레이드 패널을 왼쪽 상태 패널 자리에 그린다(반투명 없이 도트 상자).

        오른쪽 제자 무대는 가리지 않으므로 패널을 열어도 제자와 배경이 보인다.
        머리 줄: 왼쪽 "업그레이드", 오른쪽 "연구비 N".
        그 아래 미니 게이지 줄: 패널이 가린 체력·멘탈 막대를 작게 보여 준다(draw_panel_gauges).
        아래로 항목 10줄: 이름, "Lv 지금/최대", 가격(최고 레벨이면 "MAX").
        살 수 있는 항목은 민트, 연구비가 모자라거나 최고 레벨이면 회색이다.
        고른 줄(↑↓)에는 왼쪽에 화살표를 붙이고, 마우스를 올린 줄(살 수 있을 때)은 밝게 칠한다.
        바닥 줄에는 고른 줄 항목의 효과 설명("효과: 학식 체력 +4")을 쓴다.
        """
        panel = pygame.Rect(config.UPGRADE_PANEL_RECT)
        draw_pixel_box(self.screen, panel, config.COLOR_BG, config.COLOR_PANEL_LIGHT,
                       config.COLOR_PANEL_SHADOW, drop=config.COLOR_DROP)
        title = render_text(self.event_font, config.UPGRADE_PANEL_TITLE)
        title_rect = title.get_rect()
        title_rect.midleft = (config.UPGRADE_HEADER_LEFT, config.UPGRADE_HEADER_Y)
        self.screen.blit(title, title_rect)
        money = render_text(self.small_font,
                            config.MONEY_TEXT.format(config.MONEY_LABEL, self.money))
        money_rect = money.get_rect()
        money_rect.midright = (config.UPGRADE_HEADER_RIGHT, config.UPGRADE_HEADER_Y)
        self.screen.blit(money, money_rect)
        self.draw_panel_gauges()
        for index, upgrade_id in enumerate(config.UPGRADE_IDS):
            self.draw_upgrade_row(index, upgrade_id)
        chosen = config.UPGRADES_BY_ID[config.UPGRADE_IDS[self.upgrade_cursor]]
        footer = render_text(self.small_font,
                             config.UPGRADE_FOOTER_TEXT.format(chosen[config.UPGRADE_EFFECT_TEXT]),
                             config.COLOR_TEXT_SOFT)
        footer_rect = footer.get_rect()
        footer_rect.midleft = (config.UPGRADE_FOOTER_X, config.UPGRADE_FOOTER_Y)
        self.screen.blit(footer, footer_rect)

    def draw_panel_gauges(self):
        """업그레이드 패널 머리 줄 아래에 체력·멘탈 미니 게이지 2개를 한 줄에 나란히 그린다.

        패널이 열려 있어도 게임은 흐르므로(방치형) 가려진 게이지를 여기서 볼 수 있게 한다.
        각 칸: 작은 라벨 글자 + 남색 도트 테두리 막대. 막대 길이는 표시값(E4 부드러운 변화),
        채움 색은 실제 값이 30 미만이면 빨강, 아니면 초록(기능 6과 같은 규칙).
        """
        for name, label, label_x in config.UPGRADE_GAUGES:
            text = render_text(self.small_font, label)
            text_rect = text.get_rect()
            text_rect.midleft = (label_x, config.UPGRADE_GAUGE_Y)
            self.screen.blit(text, text_rect)
            bar = pygame.Rect(config.ORIGIN, (config.UPGRADE_GAUGE_BAR_WIDTH,
                                              config.UPGRADE_GAUGE_BAR_HEIGHT))
            bar.midleft = (text_rect.right + config.UPGRADE_GAUGE_BAR_GAP + config.PIXEL_SIZE,
                           config.UPGRADE_GAUGE_Y)
            draw_pixel_box(self.screen, bar.inflate(config.BOX_INSET, config.BOX_INSET),
                           config.COLOR_BAR_BG)
            if getattr(self.student, name) < config.LOW_GAUGE_LIMIT:
                main, light = config.COLOR_RED, config.COLOR_RED_LIGHT
            else:
                main, light = config.COLOR_GREEN, config.COLOR_GREEN_LIGHT
            shown = min(max(self.get_shown_gauge(name), config.GAUGE_MIN), config.GAUGE_MAX)
            fill = pygame.Rect(bar.left, bar.top, int(bar.width * shown / config.GAUGE_MAX),
                               bar.height)
            pygame.draw.rect(self.screen, main, fill)
            pygame.draw.rect(self.screen, light, (fill.left, fill.top, fill.width,
                                                  config.PIXEL_SIZE))

    def draw_upgrade_row(self, index, upgrade_id):
        """업그레이드 패널의 index번째 항목 줄 하나를 그린다(draw_upgrade_panel이 부른다).

        줄 안에는 이름, "Lv 지금/최대", 가격 세 가지만 작은 글자로 쓴다(효과는 바닥 줄).
        """
        upgrade = config.UPGRADES_BY_ID[upgrade_id]
        row = self.get_upgrade_row_rect(index)
        buyable = self.can_buy_upgrade(upgrade_id)
        hovered = self.mouse_pos is not None and row.collidepoint(self.mouse_pos)
        if buyable:
            fill, light, text_color = (config.COLOR_UPGRADE_ROW, config.COLOR_UPGRADE_ROW_LIGHT,
                                       config.COLOR_TEXT)
            if hovered:
                fill = config.COLOR_UPGRADE_ROW_HOVER
        else:
            fill, light, text_color = (config.COLOR_UPGRADE_ROW_OFF,
                                       config.COLOR_UPGRADE_ROW_OFF_LIGHT,
                                       config.COLOR_UPGRADE_TEXT_OFF)
        inner = draw_pixel_box(self.screen, row, fill, light)
        if index == self.upgrade_cursor:
            _, arrow_height = sprite_size(config.ARROW_SPRITE, config.PIXEL_SIZE)
            draw_sprite(self.screen, config.ARROW_SPRITE, config.UPGRADE_CURSOR_X,
                        inner.centery - arrow_height // config.HALF, config.PIXEL_SIZE,
                        {config.SPRITE_INK: config.COLOR_UPGRADE_CURSOR})
        level = self.upgrades[upgrade_id]
        max_level = upgrade[config.UPGRADE_MAX_LEVEL]
        if self.is_upgrade_maxed(upgrade_id):
            cost_text = config.UPGRADE_MAX_TEXT
        else:
            cost_text = config.UPGRADE_COST_TEXT.format(self.get_upgrade_cost(upgrade_id))
        columns = [
            (upgrade[config.UPGRADE_NAME], config.UPGRADE_NAME_X),
            (config.UPGRADE_LEVEL_TEXT.format(level, max_level), config.UPGRADE_LEVEL_X),
        ]
        for text, x in columns:
            surface = render_text(self.small_font, text, text_color)
            rect = surface.get_rect()
            rect.midleft = (x, inner.centery)
            self.screen.blit(surface, rect)
        cost = render_text(self.small_font, cost_text, text_color)
        cost_rect = cost.get_rect()
        cost_rect.midright = (config.UPGRADE_COST_RIGHT, inner.centery)
        self.screen.blit(cost, cost_rect)

    # ------------------------------------------------------------
    # 랜덤 이벤트 화면 (D단위): 자동형 알림, 대화창, 멈춤 점무늬
    # ------------------------------------------------------------
    def get_slide_offset(self, age, duration, distance):
        """등장 연출로 원래 자리보다 위에 있을 거리(픽셀)를 돌려준다.

        age(나타난 뒤 흐른 시간)가 0이면 distance만큼 위, duration이 지나면 0(제자리)이다.
        PIXEL_SIZE 단위로 끊어서 한 칸씩 계단처럼 내려온다.
        """
        if age >= duration:
            return config.NO_OFFSET
        return self.snap_to_pixel(distance * (config.FULL_RATIO - age / duration))

    def draw_event_notice(self):
        """자동형 이벤트 알림(도트 상자: 아이콘 + 제목)을 무대 왼쪽 위 구석에 그린다.

        좋은 일(효과 합 0 이상)은 민트 바탕 + 하트, 나쁜 일은 연분홍 바탕 + 느낌표.
        나타날 때 EVENT_NOTICE_SLIDE_TIME 동안 위에서 한 칸씩 내려온다(무대 안쪽으로 잘라 그림).
        가운데 머리 위(행동 팝업 자리)와 겹치지 않도록 왼쪽 구석에 두고, 제목이 길면
        EVENT_NOTICE_TEXT_MAX_WIDTH에서 2줄로 나눠 상자가 오른쪽으로 너무 길어지지 않게 한다.
        상자 높이는 2줄 자리로 늘 같고, 글자 줄들은 상자 세로 가운데에 놓는다.
        """
        self.draw_notice(self.notice)

    def draw_promotion_notice(self):
        """진급 알림("2학년 진급!", "대학원 2년차!")을 무대 오른쪽 위 구석에 그린다.

        자동형 알림과 같은 모양(민트 도트 상자 + 하트, 위에서 내려오는 등장)이고,
        자동형 알림(왼쪽 위)과 같은 때 떠도 겹치지 않도록 오른쪽 끝을 PROMOTION_NOTICE_RIGHT에 맞춘다.
        """
        self.draw_notice(self.promotion_notice, right=config.PROMOTION_NOTICE_RIGHT)

    def draw_notice(self, notice, right=None):
        """알림 notice({"text", "timer", "good"})를 도트 상자로 그린다(자동형 알림·진급 알림 공통).

        right가 None이면 상자 왼쪽 끝을 EVENT_NOTICE_X(무대 왼쪽 위)에 맞추고,
        숫자면 상자 오른쪽 끝을 그 x에 맞춘다(무대 오른쪽 위).
        """
        if notice["good"]:
            icon, icon_colors = config.NOTICE_GOOD_ICON, config.NOTICE_GOOD_COLORS
            fill, light, shadow = config.NOTICE_GOOD_BOX
        else:
            icon, icon_colors = config.NOTICE_BAD_ICON, config.NOTICE_BAD_COLORS
            fill, light, shadow = config.NOTICE_BAD_BOX
        age = config.EVENT_NOTICE_TIME - notice["timer"]
        slide = self.get_slide_offset(age, config.EVENT_NOTICE_SLIDE_TIME,
                                      config.EVENT_NOTICE_SLIDE_DISTANCE)
        lines = self.wrap_text(self.notice_font, notice["text"],
                               config.EVENT_NOTICE_TEXT_MAX_WIDTH)
        surfaces = [render_text(self.notice_font, line) for line in lines]
        text_width = max(surface.get_width() for surface in surfaces)
        icon_width, icon_height = sprite_size(icon, config.PIXEL_SIZE)
        width = (config.BOX_INSET + config.EVENT_NOTICE_PAD + icon_width
                 + config.EVENT_NOTICE_ICON_GAP + text_width + config.EVENT_NOTICE_PAD_RIGHT)
        left = config.EVENT_NOTICE_X
        if right is not None:
            left = right - width
        box = pygame.Rect(left, config.EVENT_NOTICE_Y - slide,
                          width, config.EVENT_NOTICE_HEIGHT)
        self.screen.set_clip(self.get_stage_inner())
        inner = draw_pixel_box(self.screen, box, fill, light, shadow, drop=config.COLOR_DROP)
        icon_x = inner.left + config.EVENT_NOTICE_PAD
        draw_sprite(self.screen, icon, icon_x, inner.centery - icon_height // config.HALF,
                    config.PIXEL_SIZE, icon_colors)
        text_x = icon_x + icon_width + config.EVENT_NOTICE_ICON_GAP
        # 첫 줄 가운데 y: 줄들 전체가 상자 세로 가운데에 오도록
        first_y = (inner.centery
                   - (len(surfaces) - config.FULL_LINE) * config.EVENT_NOTICE_LINE_HEIGHT
                   // config.HALF)
        for index, surface in enumerate(surfaces):
            text_rect = surface.get_rect()
            text_rect.midleft = (text_x, first_y + index * config.EVENT_NOTICE_LINE_HEIGHT)
            self.screen.blit(surface, text_rect)
        self.screen.set_clip(None)

    def draw_pause_dots(self):
        """대화창 뒤 화면 전체에 3칸(PAUSE_DOT_STEP) 간격 남색 점무늬를 덮어 "게임이 멈췄다"는 느낌을 준다.

        Surface 알파(반투명)로 어둡게 하지 않고 도트를 찍는다. 점을 듬성듬성 찍어
        뒤 화면 글자가 읽히도록 한다. 대화창은 이 위에 그려지므로 점이 덮이지 않는다.
        """
        rows = range(config.FIRST_ROW, config.SCREEN_HEIGHT, config.PAUSE_DOT_STEP)
        for row, y in enumerate(rows):
            shift = (row % config.HALF) * config.PAUSE_DOT_SHIFT
            for x in range(shift, config.SCREEN_WIDTH, config.PAUSE_DOT_STEP):
                pygame.draw.rect(self.screen, config.COLOR_PAUSE_DOT,
                                 (x, y, config.PIXEL_SIZE, config.PIXEL_SIZE))

    def wrap_text(self, font, text, max_width):
        """글자 text를 띄어쓰기 자리에서 끊어 한 줄이 max_width를 넘지 않는 줄 목록으로 돌려준다.

        EVENT_TEXT_MAX_LINES(2)줄을 넘으면 마지막 줄 끝에 줄임표를 붙여 자른다.
        """
        lines = []
        current = ""
        for word in text.split(config.TEXT_SEPARATOR):
            candidate = word if not current else current + config.TEXT_SEPARATOR + word
            width, _ = font.size(candidate)
            if current and width > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
        if len(lines) > config.EVENT_TEXT_MAX_LINES:
            lines = lines[:config.EVENT_TEXT_MAX_LINES]
            lines.append(lines.pop() + config.TEXT_ELLIPSIS)
        return lines

    def draw_event_dialog(self):
        """선택지형 이벤트 대화창을 무대 위 가운데에 그린다.

        도트 상자 -> 제목 띠(연분홍, 양끝 별) -> 상황 글자(2줄까지) -> 선택 버튼 2개와
        각 버튼 아래 효과 미리보기 한 줄. 뜬 직후 EVENT_DIALOG_SLIDE_TIME 동안 위에서
        한 칸씩 내려온다. 입력 대기(0.3초) 동안은 선택 버튼이 회색이고 진행 막대가 차오르며(E1 진행 막대),
        그 뒤에는 마우스를 올린 버튼이 밝아진다(E1 호버).
        """
        if self.current_event is None:
            return
        slide = self.get_slide_offset(self.dialog_time, config.EVENT_DIALOG_SLIDE_TIME,
                                      config.EVENT_DIALOG_SLIDE_DISTANCE)
        box = pygame.Rect(config.EVENT_DIALOG_RECT).move(config.NO_OFFSET, -slide)
        draw_pixel_box(self.screen, box, config.COLOR_BG, config.COLOR_PANEL_LIGHT,
                       config.COLOR_PANEL_SHADOW, drop=config.COLOR_DROP)
        self.draw_dialog_title(slide)

        lines = self.wrap_text(self.event_font, self.current_event[config.EVENT_TEXT],
                               config.EVENT_TEXT_MAX_WIDTH)
        area_height = config.EVENT_TEXT_MAX_LINES * config.EVENT_TEXT_LINE_HEIGHT
        first_y = (config.EVENT_TEXT_TOP - slide
                   + (area_height - len(lines) * config.EVENT_TEXT_LINE_HEIGHT) // config.HALF
                   + config.EVENT_TEXT_LINE_HEIGHT // config.HALF)
        for index, line in enumerate(lines):
            surface = render_text(self.event_font, line)
            rect = surface.get_rect()
            rect.center = (config.EVENT_DIALOG_CENTER_X,
                           first_y + index * config.EVENT_TEXT_LINE_HEIGHT)
            self.screen.blit(surface, rect)

        waiting = not self.is_dialog_ready()
        progress = None
        if waiting:
            progress = self.dialog_time / config.EVENT_INPUT_DELAY
        options = self.current_event[config.EVENT_OPTIONS]
        for button, option in zip(self.choice_buttons, options):
            hovered = self.mouse_pos is not None and button.is_clicked(self.mouse_pos)
            shown = button
            if slide != config.NO_OFFSET:
                # 등장 중에는 내려오는 자리에 그린다(클릭 판정 자리는 그대로, 이때는 입력 대기 중)
                shown = Button(button.rect.x, button.rect.y - slide, button.rect.width,
                               button.rect.height, button.text)
            shown.draw(self.screen, self.event_font, waiting, hovered,
                       config.NO_OFFSET, progress)
            self.draw_choice_preview(option, shown.rect.centerx,
                                     shown.rect.bottom + config.CHOICE_PREVIEW_GAP)

    def draw_dialog_title(self, slide):
        """대화창 맨 위 제목 띠(연분홍 도트 상자 + 양끝 별 + 이벤트 이름)를 그린다."""
        band = pygame.Rect(config.EVENT_TITLE_BAND_RECT).move(config.NO_OFFSET, -slide)
        inner = draw_pixel_box(self.screen, band, config.COLOR_PINK_LIGHT, config.COLOR_WHITE,
                               config.COLOR_PINK)
        title = render_text(self.font, self.current_event[config.EVENT_TITLE])
        rect = title.get_rect()
        rect.center = inner.center
        self.screen.blit(title, rect)
        star_width, star_height = sprite_size(config.STAR_SPRITE, config.PIXEL_SIZE)
        star_y = inner.centery - star_height // config.HALF
        ink = {config.SPRITE_INK: config.COLOR_PINK_DARK}
        draw_sprite(self.screen, config.STAR_SPRITE, band.left + config.EVENT_TITLE_ICON_MARGIN,
                    star_y, config.PIXEL_SIZE, ink)
        draw_sprite(self.screen, config.STAR_SPRITE,
                    band.right - config.EVENT_TITLE_ICON_MARGIN - star_width,
                    star_y, config.PIXEL_SIZE, ink)

    def get_option_preview(self, option):
        """선택지 option의 효과 미리보기 항목 [(글자, 색), ...]을 돌려준다.

        게이지 효과는 "멘탈 +15"(늘면 초록, 줄면 빨강), 특성·외형은 "특성: 음악 힐링",
        "외형: 기타"(옅은 남색). 연계 플래그는 숨긴다(나중에 생기는 이벤트의 깜짝 요소).
        보일 것이 하나도 없으면 "변화 없음".
        """
        labels = dict(config.POPUP_GAUGES)
        parts = []
        for key, amount in option[config.OPTION_EFFECTS].items():
            color = config.COLOR_PREVIEW_UP
            if amount < config.NO_CHANGE:
                color = config.COLOR_PREVIEW_DOWN
            parts.append((config.POPUP_TEXT.format(labels[key], amount), color))
        if option[config.OPTION_TRAIT] is not None:
            parts.append((config.PREVIEW_TRAIT_TEXT.format(option[config.OPTION_TRAIT]),
                          config.COLOR_PREVIEW_OTHER))
        if option[config.OPTION_LOOK] is not None:
            parts.append((config.PREVIEW_LOOK_TEXT.format(
                config.LOOK_NAMES[option[config.OPTION_LOOK]]), config.COLOR_PREVIEW_OTHER))
        if not parts:
            parts.append((config.PREVIEW_NONE_TEXT, config.COLOR_PREVIEW_OTHER))
        return parts

    def draw_choice_preview(self, option, center_x, center_y):
        """선택 버튼 아래에 효과 미리보기 한 줄을 (center_x, center_y) 가운데에 작은 글씨로 그린다.

        항목마다 색이 달라서 글자를 따로 그린 뒤 " · "로 이어 붙여 가운데 정렬한다.
        """
        surfaces = []
        for text, color in self.get_option_preview(option):
            if surfaces:   # 두 번째 항목부터 앞에 구분 글자를 붙인다
                surfaces.append(render_text(self.small_font, config.PREVIEW_SEPARATOR,
                                            config.COLOR_PREVIEW_OTHER))
            surfaces.append(render_text(self.small_font, text, color))
        total = sum(surface.get_width() for surface in surfaces)
        x = center_x - total // config.HALF
        for surface in surfaces:
            rect = surface.get_rect()
            rect.midleft = (x, center_y)
            self.screen.blit(surface, rect)
            x += surface.get_width()

    def get_stage_inner(self):
        """제자 무대 패널의 안쪽 사각형(외곽선 1칸 안)을 돌려준다. 무대 연출을 잘라 그릴 때 쓴다."""
        stage = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH,
                            config.PANEL_HEIGHT)
        return stage.inflate(-config.BOX_INSET, -config.BOX_INSET)

    def draw_panel(self, rect):
        """크림색 도트 패널(계단 모서리, 남색 외곽선, 아래 그림자)을 그리고 안쪽 사각형을 돌려준다."""
        return draw_pixel_box(self.screen, rect, config.COLOR_BG,
                              config.COLOR_PANEL_LIGHT, config.COLOR_PANEL_SHADOW,
                              drop=config.COLOR_DROP)

    def draw_text_center(self, font, text, center_y, color=config.COLOR_TEXT,
                         center_x=config.SCREEN_CENTER_X):
        """글자 text를 가운데 x가 center_x(기본: 화면 가운데), 세로 가운데가 center_y가 되게
        그리고 사각형을 돌려준다."""
        surface = render_text(font, text, color)
        rect = surface.get_rect()
        rect.center = (center_x, center_y)
        self.screen.blit(surface, rect)
        return rect

    def draw_big_text(self, text, center_y, center_x=config.SCREEN_CENTER_X,
                      max_width=config.ENDING_NAME_MAX_WIDTH):
        """큰 제목 글자를 살구색 그림자 글자와 겹쳐 가운데 x = center_x 에 그린다(레트로 느낌).

        글자가 길어 큰 글씨로 max_width를 넘으면(예: "대학원 12년차 수료")
        조금 작은 글씨(ending_font)로 그려서 가운데 패널 밖으로 나가지 않게 한다.
        """
        font = self.title_font
        shadow = render_text(font, text, config.COLOR_TITLE_SHADOW)
        if shadow.get_width() > max_width:
            font = self.ending_font
            shadow = render_text(font, text, config.COLOR_TITLE_SHADOW)
        rect = shadow.get_rect()
        rect.center = (center_x + config.TITLE_SHADOW_OFFSET,
                       center_y + config.TITLE_SHADOW_OFFSET)
        self.screen.blit(shadow, rect)
        self.draw_text_center(font, text, center_y, center_x=center_x)

    def draw_badge(self, text, center_y, fill, light, center_x=config.SCREEN_CENTER_X):
        """글자 하나를 감싸는 작은 도트 배지(상자)를 가운데 x = center_x 에 그린다."""
        surface = render_text(self.font, text)
        rect = surface.get_rect()
        box = pygame.Rect(config.ORIGIN, (rect.width + config.BADGE_PADDING_X * config.HALF,
                                          config.BADGE_HEIGHT))
        box.center = (center_x, center_y)
        inner = draw_pixel_box(self.screen, box, fill, light, drop=config.COLOR_DROP)
        rect.center = inner.center
        self.screen.blit(surface, rect)

    def draw_key_hint(self, text, center_y, center_x=config.SCREEN_CENTER_X):
        """키 안내 문구(예: "Enter를 눌러 시작") 앞에 작은 도트 화살표를 붙여 그린다.

        글자 가운데 x는 center_x(기본: 화면 가운데)다.
        E6 깜빡임: 0.5초마다 화살표가 보였다 숨었다 하고, 숨은 차례에는 글자 색이
        살짝 옅어진다. 글자 자체는 늘 보여서 읽기 불편하지 않다.
        """
        if not self.is_blink_on():
            self.draw_text_center(self.font, text, center_y, config.COLOR_HINT_DIM, center_x)
            return
        rect = self.draw_text_center(self.font, text, center_y, center_x=center_x)
        arrow_width, arrow_height = sprite_size(config.ARROW_SPRITE, config.PIXEL_SIZE)
        draw_sprite(self.screen, config.ARROW_SPRITE,
                    rect.left - config.HINT_ARROW_GAP - arrow_width,
                    center_y - arrow_height // config.HALF,
                    config.PIXEL_SIZE, {config.SPRITE_INK: config.COLOR_PINK_DARK})

    def draw_stars(self, stars, shift_x=config.NO_OFFSET):
        """장식용 반짝이 별들을 (x, y, 색) 목록대로 찍는다. shift_x만큼 오른쪽으로 옮겨 찍을 수 있다."""
        for x, y, color in stars:
            draw_sprite(self.screen, config.STAR_SPRITE, x + shift_x, y, config.PIXEL_SIZE,
                        {config.SPRITE_INK: color})

    def draw_title(self):
        """타이틀 화면: 패널, 큰 제목, 도트 장식 줄·별, 최고 기록 배지, "Enter를 눌러 시작"."""
        self.draw_panel(config.MENU_PANEL_RECT)
        self.draw_stars(config.TITLE_STARS)
        self.draw_big_text(config.TITLE_TEXT, config.TITLE_TEXT_Y)
        self.draw_dot_line(config.TITLE_LINE_Y)
        self.draw_badge(config.BEST_RECORD_TEXT.format(self.best_record),
                        config.BEST_RECORD_Y, config.COLOR_PINK_LIGHT, config.COLOR_WHITE)
        self.draw_text_center(self.font, config.TITLE_WALLET_TEXT.format(self.fame, self.money),
                              config.TITLE_WALLET_Y, config.COLOR_TEXT_SOFT)
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
        """게임 화면: 상단 정보바, 목표 진행 막대, (시험 기간이면) 노란 배너, 상태 패널(게이지),
        제자 무대(배경 4겹 -> 제자 -> 파티클·팝업 -> 알림·진급 알림),
        방침 버튼과 자동 행동 진행 막대, 경과 시간."""
        self.draw_info_bar()
        self.draw_goal_bar()
        if self.student.is_exam_period():
            self.draw_exam_banner()
        self.draw_panel((config.STATUS_PANEL_X, config.PANEL_Y,
                         config.STATUS_PANEL_WIDTH, config.PANEL_HEIGHT))
        self.draw_panel((config.STAGE_X, config.PANEL_Y,
                         config.STAGE_WIDTH, config.PANEL_HEIGHT))
        self.draw_background()
        self.student.draw_gauges(self.screen, self.font,
                                 self.get_shown_gauge(config.GAUGE_HEALTH),
                                 self.get_shown_gauge(config.GAUGE_MENTAL))
        self.student.draw_traits(self.screen, self.small_font)
        self.student.draw(self.screen, self.get_student_lift())
        self.draw_stage_effects()
        if self.notice is not None:
            self.draw_event_notice()
        if self.promotion_notice is not None:
            self.draw_promotion_notice()
        self.draw_buttons()
        self.draw_elapsed_time()

    def draw_stage_effects(self):
        """제자 무대 안에 파티클(E2)과 수치 팝업(E3)을 그린다.

        무대 패널 안쪽으로 그리기 영역을 잘라(set_clip) 두어서 파티클·팝업이
        패널 밖(버튼·상태 패널 쪽)으로 넘쳐 보이지 않게 한다.
        """
        self.screen.set_clip(self.get_stage_inner())
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
        """수치 팝업 하나("체력 +20")를 떠오른 높이에 굵은 글씨로 그린다.

        순서: 남색 그림자(오른쪽 아래 2px) -> 크림색 테두리(사방 1px) -> 색 글자.
        크림 테두리 덕분에 남색 밤하늘에서도, 남색 그림자 덕분에 밝은 낮 하늘에서도 읽힌다
        (반투명 없이 글자를 여러 번 찍는다).
        POPUP_BLINK_START가 지나면 POPUP_BLINK_STEP마다 보였다 숨었다 하며 사라진다.
        글자 가운데 x는 popup["x"](행동 팝업 = 무대 가운데, 이벤트 팝업 = 왼쪽 위 칸)이고,
        x가 없는 팝업은 무대 가운데에 그린다.
        """
        age = popup["age"]
        if age >= config.POPUP_BLINK_START:
            step = int((age - config.POPUP_BLINK_START) / config.POPUP_BLINK_STEP)
            if step % config.HALF == config.BLINK_HIDE:
                return
        center = (popup.get("x", config.STUDENT_CENTER_X),
                  round(popup["y"] - config.POPUP_RISE_SPEED * age))
        outline = render_text(self.popup_font, popup["text"], config.COLOR_OUTLINE)
        rect = outline.get_rect()
        rect.center = center
        for dx, dy in config.POPUP_OUTLINE_OFFSETS:
            self.screen.blit(outline, rect.move(dx, dy))
        rim = render_text(self.popup_font, popup["text"], config.COLOR_POPUP_RIM)
        for dx, dy in config.POPUP_RIM_OFFSETS:
            self.screen.blit(rim, rect.move(dx, dy))
        self.screen.blit(render_text(self.popup_font, popup["text"], popup["color"]), rect)

    def draw_ending(self):
        """엔딩 화면: 패널, 엔딩 이름, (졸업·수료) 학사모와 별 / (휴학) 비구름, 누적 지식 배지, 키 안내.

        - 학부 졸업: 등급(수석/무사/아슬아슬 졸업), 걸린 시간("졸업까지 3분 52초"), 졸업 보너스,
          "R: 환생 (명성 +1)" / "C: 대학원 진학"
        - 대학원 수료: "대학원 n년차 수료", "R: 환생 (명성 +1)" (졸업 보너스 없음)
        - 휴학: "R을 눌러 다시 하기"
        업그레이드 패널(왼쪽)이 열려 있으면 가운데 패널과 글자·그림을 오른쪽으로 옮겨
        그려서 패널이 엔딩 이름·안내를 가리지 않게 한다(get_ending_layout).
        """
        panel_rect, center_x, name_max_width = self.get_ending_layout()
        self.draw_panel(panel_rect)
        self.draw_big_text(self.ending, config.ENDING_NAME_Y, center_x, name_max_width)
        if self.ending == config.ENDING_LEAVE:
            self.draw_center_sprite(config.CLOUD_SPRITE, config.CLOUD_TOP_Y,
                                    config.CLOUD_PIXEL, config.CLOUD_COLORS, center_x)
        else:
            self.draw_stars(config.ENDING_STARS, center_x - config.SCREEN_CENTER_X)
            self.draw_graduation_cap(center_x)
        if self.is_graduation_ending() and self.student.has_graduated():
            # 졸업까지 걸린 시간: "졸업까지 3분 52초" (기획서 11절)
            self.draw_text_center(
                self.event_font,
                config.ENDING_TIME_TEXT.format(format_time(self.student.graduation_time)),
                config.ENDING_TIME_Y, config.COLOR_TEXT, center_x)
        self.draw_badge(config.ENDING_KNOWLEDGE_TEXT.format(self.student.knowledge),
                        config.ENDING_KNOWLEDGE_Y, config.COLOR_MINT_LIGHT, config.COLOR_WHITE,
                        center_x)
        if self.graduation_bonus > config.MONEY_START:
            self.draw_text_center(self.event_font,
                                  config.GRADUATION_BONUS_TEXT.format(self.graduation_bonus),
                                  config.GRADUATION_BONUS_Y, config.COLOR_TEXT_SOFT, center_x)
        if self.can_reincarnate():
            self.draw_key_hint(config.REINCARNATE_HINT_TEXT, config.RESTART_HINT_Y, center_x)
            if self.is_graduation_ending():
                self.draw_key_hint(config.GRAD_SCHOOL_HINT_TEXT, config.GRAD_SCHOOL_HINT_Y,
                                   center_x)
        else:
            self.draw_key_hint(config.RESTART_HINT_TEXT, config.RESTART_HINT_Y, center_x)

    def get_ending_layout(self):
        """엔딩 화면 배치 (가운데 패널 사각형, 글자 가운데 x, 엔딩 이름 최대 가로 길이)를 돌려준다.

        업그레이드 패널이 닫혀 있으면 화면 가운데 패널(MENU_PANEL_RECT, 가운데 400),
        열려 있으면 패널과 겹치지 않는 오른쪽 자리(ENDING_PANEL_OPEN_RECT, 가운데 536)다.
        """
        if self.upgrade_panel_open:
            return (config.ENDING_PANEL_OPEN_RECT, config.ENDING_OPEN_CENTER_X,
                    config.ENDING_NAME_MAX_WIDTH_OPEN)
        return config.MENU_PANEL_RECT, config.SCREEN_CENTER_X, config.ENDING_NAME_MAX_WIDTH

    def draw_center_sprite(self, grid, top, cell, colors, center_x=config.SCREEN_CENTER_X):
        """스프라이트 grid를 가운데 x가 center_x(기본: 화면 가운데), 위쪽 y가 top이 되게
        칸 크기 cell로 찍는다."""
        width, _ = sprite_size(grid, cell)
        draw_sprite(self.screen, grid, center_x - width // config.HALF, top, cell, colors)

    def draw_graduation_cap(self, center_x=config.SCREEN_CENTER_X):
        """도트 학사모(납작한 마름모 윗판 + 띠 + 금색 술)를 가운데 x = center_x 위쪽에 찍는다."""
        self.draw_center_sprite(config.CAP_SPRITE, config.CAP_TOP_Y,
                                config.CAP_PIXEL, config.CAP_COLORS, center_x)

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

    def get_goal_text(self):
        """정보바의 목표 글자를 돌려준다(기획서 11절).

        1~3학년 "다음 학년까지 지식 n", 4학년 "졸업까지 지식 n", 대학원 "다음 년차까지 지식 n".
        n은 다음 목표까지 더 모아야 하는 지식이다(0 아래로 내려가지 않음).
        """
        left = self.student.get_knowledge_to_goal()
        if self.student.is_in_grad_school():
            return config.NEXT_GRAD_YEAR_TEXT.format(left)
        if self.student.get_grade() >= config.MAX_GRADE:
            return config.GRADUATION_GOAL_TEXT.format(left)
        return config.NEXT_GRADE_TEXT.format(left)

    def draw_goal_bar(self):
        """정보바 바로 아래 왼쪽(상태 패널 위)에 목표 진행 막대를 도트 상자로 그린다.

        상자 안 왼쪽에 "목표" 글자, 그 오른쪽에 막대. 막대는 지금 목표 구간
        (앞 목표 -> 다음 목표)에서 지식이 얼마나 찼는지(Student.get_goal_progress)를
        PIXEL_SIZE 단위로 끊어 채운다(도트 방식, 반투명 없음).
        시험 기간 배너는 오른쪽(무대 위)에 뜨므로 서로 겹치지 않는다.
        """
        box = pygame.Rect(config.GOAL_BOX_X, config.GOAL_BOX_Y,
                          config.GOAL_BOX_WIDTH, config.GOAL_BOX_HEIGHT)
        inner = draw_pixel_box(self.screen, box, config.COLOR_INFO_BAR,
                               config.COLOR_MINT_LIGHT, config.COLOR_MINT_DARK,
                               drop=config.COLOR_DROP)
        label = render_text(self.event_font, config.GOAL_LABEL_TEXT)
        label_rect = label.get_rect()
        label_rect.midleft = (inner.left + config.GOAL_BAR_PAD, inner.centery)
        self.screen.blit(label, label_rect)

        bar_left = label_rect.right + config.GOAL_LABEL_GAP
        bar = pygame.Rect(bar_left, inner.centery - config.GOAL_BAR_HEIGHT // config.HALF,
                          inner.right - config.GOAL_BAR_PAD - bar_left, config.GOAL_BAR_HEIGHT)
        # 막대 테두리(남색 1칸)와 빈 부분(연한 색)은 상태 패널 게이지와 같은 모양이다
        draw_pixel_box(self.screen, bar.inflate(config.BOX_INSET, config.BOX_INSET),
                       config.COLOR_BAR_BG, light=config.COLOR_BAR_BG_SHADE)
        cells = int(bar.width * self.student.get_goal_progress()) // config.PIXEL_SIZE
        fill = pygame.Rect(bar.left, bar.top, cells * config.PIXEL_SIZE, bar.height)
        pygame.draw.rect(self.screen, config.COLOR_YELLOW, fill)
        pygame.draw.rect(self.screen, config.COLOR_YELLOW_LIGHT,
                         (fill.left, fill.top, fill.width, config.PIXEL_SIZE))
        pygame.draw.rect(self.screen, config.COLOR_YELLOW_DARK,
                         (fill.left, fill.bottom - config.PIXEL_SIZE, fill.width,
                          config.PIXEL_SIZE))

    def draw_elapsed_time(self):
        """오른쪽 아래([업그레이드 U] 버튼 밑)에 판 시작부터 흐른 게임 시간("경과 3분 12초")을 쓴다."""
        text = render_text(self.font,
                           config.ELAPSED_TEXT.format(format_time(self.student.elapsed)),
                           config.COLOR_TEXT_SOFT)
        rect = text.get_rect()
        rect.center = (config.ELAPSED_CENTER_X, config.ELAPSED_CENTER_Y)
        self.screen.blit(text, rect)

    def draw_info_bar(self):
        """상단 정보바를 그린다.

        민트색 도트 상자 위에 왼쪽 "N학년"(대학원이면 "대학원 n년차"),
        그 오른쪽(INFO_GOAL_X부터) 목표 글자("다음 학년까지 지식 n" 등, get_goal_text),
        오른쪽 "연구비 N  지식 N"을 쓴다. 목표 진행 막대는 정보바 바로 아래(draw_goal_bar)다.
        """
        box = pygame.Rect(config.INFO_BOX_X, config.INFO_BOX_Y,
                          config.INFO_BOX_WIDTH, config.INFO_BOX_HEIGHT)
        draw_pixel_box(self.screen, box, config.COLOR_INFO_BAR,
                       config.COLOR_MINT_LIGHT, config.COLOR_MINT_DARK,
                       drop=config.COLOR_DROP)

        if self.grad_year > config.GRAD_YEAR_UNDERGRAD:
            grade_text = config.GRAD_YEAR_TEXT.format(self.grad_year)
        else:
            grade_text = config.GRADE_TEXT.format(self.student.get_grade())
        grade = render_text(self.font, grade_text)
        grade_rect = grade.get_rect()
        grade_rect.midleft = (config.INFO_BAR_MARGIN, config.INFO_TEXT_CENTER_Y)
        self.screen.blit(grade, grade_rect)

        goal = render_text(self.font, self.get_goal_text())
        goal_rect = goal.get_rect()
        goal_rect.midleft = (config.INFO_GOAL_X, config.INFO_TEXT_CENTER_Y)
        self.screen.blit(goal, goal_rect)

        knowledge = render_text(
            self.font,
            config.KNOWLEDGE_TEXT.format(config.KNOWLEDGE_LABEL, self.student.knowledge))
        knowledge_rect = knowledge.get_rect()
        knowledge_rect.midright = (config.SCREEN_WIDTH - config.INFO_BAR_MARGIN,
                                   config.INFO_TEXT_CENTER_Y)
        self.screen.blit(knowledge, knowledge_rect)

        # 연구비: 지식 글자 왼쪽에 INFO_ITEM_GAP 띄워서
        money = render_text(self.font, config.MONEY_TEXT.format(config.MONEY_LABEL, self.money))
        money_rect = money.get_rect()
        money_rect.midright = (knowledge_rect.left - config.INFO_ITEM_GAP,
                               config.INFO_TEXT_CENTER_Y)
        self.screen.blit(money, money_rect)

    def get_auto_progress(self):
        """다음 자동 행동까지의 진행률(0~1)을 돌려준다. 방금 행동했으면 0, 곧 행동하면 1에 가깝다.

        자동 행동 간격은 시간 관리 업그레이드에 따라 2.0초보다 짧을 수 있다.
        """
        return config.FULL_RATIO - self.auto_timer / self.get_auto_interval()

    def draw_buttons(self):
        """방침 버튼 3개, 그 아래 자동 행동 진행 막대와 "다음 자동 행동까지" 안내 문구를 그린다.

        지금 고른 방침 버튼은 노랑 계열로 밝게 강조하고(반투명 없음),
        마우스가 올라간 버튼은 밝은 하늘색, 방금 고른 버튼은 잠깐 눌린 자리(4px 아래)에 그린다.
        진행 막대는 방침 버튼 3개 너비의 도트 상자 안에 2초에 걸쳐 차오른다(draw_progress_bar).
        """
        for name, button in self.buttons.items():
            hovered = self.mouse_pos is not None and button.is_clicked(self.mouse_pos)
            offset = config.NO_OFFSET
            if self.press_timers.get(name, config.ZERO_TIME) > config.TIME_EPSILON:
                offset = config.BUTTON_PRESS_OFFSET
            button.draw(self.screen, self.font, False, hovered, offset,
                        selected=(name == self.policy))

        bar = pygame.Rect(config.BUTTON_START_X, config.AUTO_BAR_Y,
                          config.POLICY_AREA_WIDTH, config.AUTO_BAR_HEIGHT)
        inner = draw_pixel_box(self.screen, bar, config.COLOR_COOLDOWN_TRACK)
        draw_progress_bar(self.screen, inner, self.get_auto_progress())

        hint = render_text(self.small_font, config.AUTO_HINT_TEXT, config.COLOR_TEXT_SOFT)
        hint_rect = hint.get_rect()
        hint_rect.midtop = (bar.centerx, config.AUTO_HINT_Y)
        self.screen.blit(hint, hint_rect)

        self.draw_upgrade_button(self.upgrade_button)   # 오른쪽 [업그레이드 U] 버튼

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
