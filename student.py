"""제자(Student) 클래스가 들어 있는 파일."""

import pygame

import config
from button import draw_cut_rect, draw_pixel_box, draw_sprite, render_text, sprite_size


def clamp(value, low, high):
    """value를 low 이상 high 이하로 잘라서 돌려준다."""
    return max(low, min(value, high))


def judge_ending(knowledge):
    """240초를 버틴 제자의 누적 지식으로 졸업 엔딩 이름을 돌려준다.

    지식 700 이상 "수석 졸업", 450~699 "무사 졸업", 450 미만 "아슬아슬 졸업".
    (휴학은 체력·멘탈로 정하므로 여기서 다루지 않는다.)
    """
    if knowledge >= config.TOP_GRADUATE_KNOWLEDGE:
        return config.ENDING_TOP
    if knowledge >= config.NORMAL_GRADUATE_KNOWLEDGE:
        return config.ENDING_NORMAL
    return config.ENDING_BARELY


class Student:
    """교수가 돌보는 제자 한 명.

    체력·멘탈·지식 게이지와 지금까지 흐른 시간을 가지고 있다.
    로직은 화면 없이도 호출할 수 있도록 시간(dt)을 인자로 받는다.
    """

    def __init__(self, upgrades=None):
        """게이지를 시작값으로 정하고 경과 시간을 0으로 둔다.

        랜덤 이벤트로 생기는 성장 기록(특성·외형·연계 플래그·나온 선택지형 이벤트·
        학년별 이벤트 수)도 여기서 비운다. 새 판에서 Student를 새로 만들면 모두 초기화된다.
        upgrades는 업그레이드 레벨 사전 {업그레이드 id: 레벨}이다. Game이 가진 사전을
        그대로(같은 객체로) 넘기므로, 판 도중에 업그레이드를 사도 효과가 바로 적용된다.
        주지 않으면 모든 업그레이드가 0레벨이다(화면 없는 테스트용).
        """
        if upgrades is None:
            upgrades = {upgrade_id: config.LEVEL_START for upgrade_id in config.UPGRADE_IDS}
        self.upgrades = upgrades
        self.health = config.HEALTH_START
        self.mental = config.MENTAL_START
        self.knowledge = config.KNOWLEDGE_START
        self.elapsed = config.ZERO_TIME      # 게임 시작 후 흐른 시간(초)
        self.decay_timer = config.ZERO_TIME  # 다음 자연 감소까지 모아 둔 시간(초)
        self.traits = []           # 얻은 특성 이름 (얻은 순서대로, 화면 배지용)
        self.looks = []            # 얻은 외형 id (얻은 순서대로)
        self.flags = set()         # 연계 플래그 ("MT 참석" 등)
        self.seen_events = set()   # 이번 판에 이미 나온 선택지형 이벤트 id
        self.event_counts = {grade: config.EVENT_COUNT_START for grade in config.ALL_GRADES}  # 학년별 이벤트 수
        self.last_event_time = None  # 직전 이벤트가 뜬 게임 시각(초). 이번 판에 아직 없으면 None
        self.grad_year = config.GRAD_YEAR_UNDERGRAD  # 대학원 년차. 0이면 학부(1~4학년)

    # ------------------------------------------------------------
    # 대학원 (기획서 10절, I단위)
    # ------------------------------------------------------------
    def is_in_grad_school(self):
        """대학원에 다니는 중이면 True(대학원 년차가 1 이상)."""
        return self.grad_year > config.GRAD_YEAR_UNDERGRAD

    def enter_grad_school(self):
        """졸업한(240초를 버틴) 제자가 대학원 1년차로 들어간다.

        게이지·특성·외형·지식·연계 플래그·직전 이벤트 시각은 그대로 둔다.
        학부에서 아직 졸업하지 않았거나(240초 전), 휴학 상태이거나, 이미 대학원이면
        아무것도 하지 않고 False를 돌려준다. 들어갔으면 True.
        경과 시간은 240초에서 이어서 흐른다(대학원 1년차 = 240~300초, 2년차 = 300~360초 …).
        """
        if self.is_in_grad_school() or self.is_dropped_out() or not self.is_time_over():
            return False
        self.elapsed = config.TOTAL_SECONDS  # 소수 오차 없이 1년차 시작 시각에 맞춘다
        self.grad_year = config.GRAD_FIRST_YEAR
        return True

    def get_grad_year_end(self):
        """지금 대학원 년차가 끝나는 게임 시각(초) = 240 + 60 x 년차 를 돌려준다."""
        return config.TOTAL_SECONDS + self.grad_year * config.SECONDS_PER_GRADE

    def advance_grad_year(self):
        """대학원에서 지금 년차의 60초가 다 지났으면 다음 년차로 올린다(끝없이).

        dt가 커서 여러 해가 한꺼번에 지나가도 지난 해 수만큼 오른다. 학부에서는 아무것도 안 한다.
        학년과 같은 규칙으로, 년차가 끝나는 바로 그 시각부터 다음 년차로 본다.
        """
        if not self.is_in_grad_school():
            return
        while self.elapsed + config.TIME_EPSILON >= self.get_grad_year_end():
            self.grad_year += config.GRAD_YEAR_STEP

    def get_term_start(self):
        """지금 학년(대학원이면 지금 년차)이 시작된 게임 시각(초)을 돌려준다.

        학부: (학년-1) x 60 -> 0/60/120/180. 대학원 n년차: 240 + (n-1) x 60.
        """
        if self.is_in_grad_school():
            return (config.TOTAL_SECONDS
                    + (self.grad_year - config.GRAD_FIRST_YEAR) * config.SECONDS_PER_GRADE)
        return (self.get_grade() - config.FIRST_GRADE) * config.SECONDS_PER_GRADE

    def get_term_key(self):
        """이벤트 수를 셀 때 쓰는 "학년 칸" 번호를 돌려준다.

        학부는 학년(1~4) 그대로, 대학원 n년차는 4 + n(5, 6, 7 …)이다.
        그래서 대학원도 해마다 이벤트 수를 따로 센다(최소 4회 보장·최대 5회).
        """
        if self.is_in_grad_school():
            return config.MAX_GRADE + self.grad_year
        return self.get_grade()

    def get_grad_decay_ratio(self):
        """대학원 n년차의 자연 감소 배수 = 1 + 0.25 x n 을 돌려준다(학부는 1)."""
        return config.NO_RATIO + config.GRAD_DECAY_BONUS * self.grad_year

    # ------------------------------------------------------------
    # 게이지 값 바꾸기
    # ------------------------------------------------------------
    def change_health(self, amount):
        """체력을 amount만큼 바꾸고 0~100 안으로 맞춘다.

        건강 관리 업그레이드로 자연 감소가 소수(예: 0.9)가 되면 체력도 소수가 된다.
        소수 오차가 쌓이지 않도록 GAUGE_DECIMALS 자리에서 반올림한다(정수는 그대로 정수).
        """
        value = round(self.health + amount, config.GAUGE_DECIMALS)
        self.health = clamp(value, config.GAUGE_MIN, config.GAUGE_MAX)

    def change_mental(self, amount):
        """멘탈을 amount만큼 바꾸고 0~100 안으로 맞춘다(소수 처리는 change_health와 같다)."""
        value = round(self.mental + amount, config.GAUGE_DECIMALS)
        self.mental = clamp(value, config.GAUGE_MIN, config.GAUGE_MAX)

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
        경과 시간은 전체 시간(240초)에서 멈춘다. dt가 커서 240초를 넘겨도
        240초까지만 흐르고, 그 뒤로는 자연 감소도 일어나지 않는다.
        감소가 일어날 때마다 경과 시간을 "그 감소가 일어난 시각"으로 맞춰 두어서,
        dt가 커도 감소마다 시험 기간인지(멘탈 -2) 정확히 판단한다.
        대학원에서는 240초에서 멈추지 않고 끝없이 흐른다. 60초마다 년차가 오르며
        (advance_grad_year), 감소마다 그 시각의 년차 배수를 쓴다.
        """
        if not self.is_in_grad_school():
            time_left = max(config.ZERO_TIME, config.TOTAL_SECONDS - self.elapsed)
            dt = min(dt, time_left)
        end_time = self.elapsed + dt
        self.decay_timer += dt
        while self.decay_timer + config.TIME_EPSILON >= config.DECAY_INTERVAL:
            self.decay_timer -= config.DECAY_INTERVAL
            # 이번 1초 감소가 일어나는 시각 = 끝 시각 - 아직 남겨 둔 시간
            self.elapsed = end_time - self.decay_timer
            self.advance_grad_year()
            self.decay_once()
        self.elapsed = end_time
        self.advance_grad_year()
        if self.is_time_over():
            self.elapsed = config.TOTAL_SECONDS  # 소수 오차를 없애고 240에서 멈춘다

    def decay_once(self):
        """1초분 자연 감소를 한 번 적용한다: 체력 -(체력 감소량), 멘탈 -(멘탈 감소량)."""
        self.change_health(-self.get_health_decay())
        self.change_mental(-self.get_mental_decay())

    def get_health_decay(self):
        """1초마다 줄어드는 체력 양을 돌려준다: 1 x 건강 관리 배수."""
        return self.apply_decay_ratio(config.HEALTH_DECAY_PER_SEC)

    def get_mental_decay(self):
        """1초마다 줄어드는 멘탈 양을 돌려준다: 평소 1, 시험 기간 2 (x 건강 관리 배수)."""
        if self.is_exam_period():
            return self.apply_decay_ratio(config.MENTAL_DECAY_PER_SEC_EXAM)
        return self.apply_decay_ratio(config.MENTAL_DECAY_PER_SEC)

    def apply_decay_ratio(self, amount):
        """자연 감소량 amount에 건강 관리 배수 (1 - 0.1 x 레벨)와
        대학원 배수 (1 + 0.25 x 년차)를 곱해 돌려준다.

        건강 관리를 안 샀고(0레벨) 학부이면 amount를 그대로(정수로) 돌려준다.
        """
        level = self.get_upgrade_level(config.UPGRADE_HEALTH_CARE)
        if level == config.LEVEL_START and not self.is_in_grad_school():
            return amount
        ratio = config.FULL_RATIO - self.get_upgrade_bonus(config.UPGRADE_HEALTH_CARE)
        return round(amount * ratio * self.get_grad_decay_ratio(), config.GAUGE_DECIMALS)

    # ------------------------------------------------------------
    # 업그레이드 (기획서 10절, H단위)
    # ------------------------------------------------------------
    def get_upgrade_level(self, upgrade_id):
        """업그레이드 upgrade_id의 지금 레벨을 돌려준다(사지 않았으면 0)."""
        return self.upgrades.get(upgrade_id, config.LEVEL_START)

    def get_upgrade_bonus(self, upgrade_id):
        """업그레이드 upgrade_id가 주는 효과 크기 = 레벨 x 레벨당 효과 를 돌려준다.

        예: 학식 메뉴 개선 2레벨 -> 2 x 4 = 8 (학식 체력 +8).
        """
        per_level = config.UPGRADES_BY_ID[upgrade_id][config.UPGRADE_PER_LEVEL]
        return self.get_upgrade_level(upgrade_id) * per_level

    def is_dropped_out(self):
        """체력이나 멘탈이 0이면 True(휴학 조건)를 돌려준다."""
        return self.health <= config.GAUGE_MIN or self.mental <= config.GAUGE_MIN

    # ------------------------------------------------------------
    # 시험 기간과 엔딩 (5일차)
    # ------------------------------------------------------------
    def is_time_over(self):
        """경과 시간이 전체 시간(240초)에 도달했으면 True(졸업 시점)를 돌려준다.

        1/60초를 14400번 더하면 239.9999…가 될 수 있어서 TIME_EPSILON 만큼 봐준다.
        대학원은 끝없이 이어지므로 언제나 False다(대학원은 체력·멘탈 0으로만 끝난다).
        """
        if self.is_in_grad_school():
            return False
        return self.elapsed + config.TIME_EPSILON >= config.TOTAL_SECONDS

    def is_exam_period(self):
        """지금이 시험 기간(각 학년 마지막 15초)이면 True를 돌려준다.

        학년 안에서 흐른 시간이 45초 이상이면 시험 기간이다(45~60초, 105~120초 …).
        60초가 되면 다음 학년이 시작되므로 시험 기간이 아니다.
        240초(졸업 시점)부터는 시험 기간이 아니다.
        대학원도 해마다 마지막 15초가 시험 기간이다(1년차 285~300초 …).
        get_grade와 똑같이 TIME_EPSILON 만큼 봐준다.
        """
        if self.is_time_over():
            return False
        exam_start = config.SECONDS_PER_GRADE - config.EXAM_SECONDS
        return self.get_time_in_grade() + config.TIME_EPSILON >= exam_start

    def get_graduation_ending(self):
        """지금 지식으로 졸업 엔딩 이름을 돌려준다(judge_ending 사용)."""
        return judge_ending(self.knowledge)

    def get_ending(self):
        """지금 엔딩이 났는지 보고 엔딩 이름을 돌려준다. 아직 아니면 None.

        체력이나 멘탈이 0이면 휴학을 먼저 돌려준다(240초 시점과 겹쳐도 휴학 우선).
        그렇지 않고 240초가 되었으면 지식에 따른 졸업 엔딩을 돌려준다.
        대학원에서 체력이나 멘탈이 0이면 "대학원 n년차 수료"를 돌려준다(휴학이 아니다).
        """
        if self.is_dropped_out():
            if self.is_in_grad_school():
                return config.ENDING_GRAD_TEXT.format(self.grad_year)
            return config.ENDING_LEAVE
        if self.is_time_over():
            return self.get_graduation_ending()
        return None

    # ------------------------------------------------------------
    # 행동 (3일차)
    # ------------------------------------------------------------
    def feed(self):
        """학식 먹이기: 체력 +20 (체력 단련 특성 +5, 학식 메뉴 개선 +4/Lv). 100을 넘지 않음."""
        self.change_health(config.FEED_HEALTH + self.get_trait_bonus(config.BONUS_FEED_HEALTH)
                           + self.get_upgrade_bonus(config.UPGRADE_MENU))

    def rest(self):
        """쉬게 하기: 멘탈 +20 (음악 힐링 +5, 푹신한 침대 +4/Lv), 지식 -2,
        체력 +0 (연애 중 +5, 카페 +5).

        멘탈·체력은 0~100, 지식은 0 아래로 내려가지 않는다.
        """
        self.change_mental(config.REST_MENTAL + self.get_trait_bonus(config.BONUS_REST_MENTAL)
                           + self.get_upgrade_bonus(config.UPGRADE_BED))
        self.change_knowledge(config.REST_KNOWLEDGE)
        self.change_health(config.REST_HEALTH + self.get_trait_bonus(config.BONUS_REST_HEALTH)
                           + self.get_upgrade_bonus(config.UPGRADE_CAFE))

    def study(self, knowledge_ratio=config.NO_RATIO, cost_ratio=config.NO_RATIO):
        """공부시키기: 지식 +(공부 지식량), 체력 -5 (카페인 특성이면 -3), 멘탈 -8.

        0 아래로 내려가지 않는다. 시험 기간 지식 +20 규칙은 특성과 상관없이 그대로다.
        knowledge_ratio·cost_ratio는 일과표 방침(기획서 10절)의 배수다.
        특성·업그레이드 보너스를 먼저 더한 뒤 배수를 곱하고 round()로 정수로 만든다.
        - 지식: round((공부 지식량 + 참고서 2/Lv + 도서관 3) x knowledge_ratio)
        - 체력: round((-5 + 카페인 2 + 헬스장 2) x cost_ratio), 멘탈: round(-8 x cost_ratio)
        배수를 주지 않으면 1.0이라 예전과 같다.
        """
        health = (config.STUDY_HEALTH + self.get_trait_bonus(config.BONUS_STUDY_HEALTH)
                  + self.get_upgrade_bonus(config.UPGRADE_GYM))
        knowledge = (self.get_study_knowledge() + self.get_upgrade_bonus(config.UPGRADE_BOOK)
                     + self.get_upgrade_bonus(config.UPGRADE_LIBRARY))
        self.change_knowledge(round(knowledge * knowledge_ratio))
        self.change_health(round(health * cost_ratio))
        self.change_mental(round(config.STUDY_MENTAL * cost_ratio))

    def get_study_knowledge(self):
        """공부시키기 한 번에 오르는 지식 양을 돌려준다: 평소 10, 시험 기간 20."""
        if self.is_exam_period():
            return config.STUDY_KNOWLEDGE_EXAM
        return config.STUDY_KNOWLEDGE

    # ------------------------------------------------------------
    # 학년과 성장 (4일차)
    # ------------------------------------------------------------
    def get_grade(self):
        """경과 시간으로 지금 학년(1~4)을 계산해 돌려준다.

        0~60초 미만 1학년, 60~120초 미만 2학년, 120~180초 미만 3학년, 180초부터 4학년.
        240초(졸업 시점)에도 4학년으로 둔다. 대학원에서도 4로 둔다
        (그래서 캐릭터 크기는 4학년 반지름 70 그대로이고 안경을 쓴다).
        1/60초를 3600번 더하면 59.9999…가 될 수 있어서 TIME_EPSILON 만큼 봐준다.
        """
        passed_grades = int((self.elapsed + config.TIME_EPSILON)
                            // config.SECONDS_PER_GRADE)
        return min(config.FIRST_GRADE + passed_grades, config.MAX_GRADE)

    def get_grade_time_left(self):
        """현재 학년의 남은 시간(정수 초, 60 -> 1)을 돌려준다.

        학년 안에서 흐른 시간의 정수 부분을 60에서 뺀다(= 남은 시간을 올림).
        그래서 학년이 막 시작하면 60, 59초가 지나 1초 미만이 남으면 1이 된다.
        4학년에서 240초가 지나면 0으로 둔다(음수가 되지 않음).
        대학원에서는 지금 년차의 남은 시간(60 -> 1)이다.
        """
        passed_seconds = int(self.get_time_in_grade() + config.TIME_EPSILON)
        return max(config.GAUGE_MIN, config.SECONDS_PER_GRADE - passed_seconds)

    def get_radius(self):
        """캐릭터 반지름을 돌려준다: 40 + (학년-1) x 10 -> 40/50/60/70."""
        return (config.BASE_RADIUS
                + (self.get_grade() - config.FIRST_GRADE) * config.RADIUS_PER_GRADE)

    # ------------------------------------------------------------
    # 랜덤 이벤트와 성장 (기획서 9절)
    # ------------------------------------------------------------
    def get_trait_bonus(self, bonus_name):
        """가진 특성들이 행동 효과 bonus_name에 더해 주는 양의 합을 돌려준다(없으면 0)."""
        total = config.TRAIT_BONUS_START
        for trait in self.traits:
            total += config.TRAIT_BONUSES[trait].get(bonus_name, config.NO_CHANGE)
        return total

    def has_trait(self, trait):
        """특성 trait을 가지고 있으면 True."""
        return trait in self.traits

    def add_trait(self, trait):
        """특성 trait을 얻는다. 이미 있으면 다시 넣지 않는다(얻은 순서 유지)."""
        if trait not in self.traits:
            self.traits.append(trait)

    def add_look(self, look):
        """외형 look을 얻는다. 이미 있으면 다시 넣지 않는다(얻은 순서 유지)."""
        if look not in self.looks:
            self.looks.append(look)

    def add_flag(self, flag):
        """연계 플래그 flag를 켠다(연계 이벤트가 나올 수 있게 된다)."""
        self.flags.add(flag)

    def apply_effects(self, effects):
        """이벤트 효과 {게이지 속성 이름: 변화량}을 적용한다.

        체력·멘탈은 0~100, 지식은 0 이상으로 맞춘다(기존 change_ 메서드 사용).
        """
        for name, amount in effects.items():
            if name == config.GAUGE_HEALTH:
                self.change_health(amount)
            elif name == config.GAUGE_MENTAL:
                self.change_mental(amount)
            elif name == config.GAUGE_KNOWLEDGE:
                self.change_knowledge(amount)

    def apply_option(self, option):
        """선택지형 이벤트에서 고른 선택지 option의 효과·특성·외형·연계 플래그를 모두 적용한다."""
        self.apply_effects(option[config.OPTION_EFFECTS])
        if option[config.OPTION_TRAIT] is not None:
            self.add_trait(option[config.OPTION_TRAIT])
        if option[config.OPTION_LOOK] is not None:
            self.add_look(option[config.OPTION_LOOK])
        if option[config.OPTION_FLAG] is not None:
            self.add_flag(option[config.OPTION_FLAG])

    def get_time_in_grade(self):
        """지금 학년(대학원이면 지금 년차) 안에서 흐른 시간(초)을 돌려준다(시작 = 0)."""
        return self.elapsed - self.get_term_start()

    def get_grade_event_count(self):
        """지금 학년(대학원이면 지금 년차)에 나온 이벤트 수를 돌려준다."""
        return self.event_counts.get(self.get_term_key(), config.EVENT_COUNT_START)

    def count_event(self):
        """지금 학년(대학원이면 지금 년차)의 이벤트 수를 하나 늘리고,
        지금 게임 시각을 직전 이벤트 시각으로 적어 둔다."""
        key = self.get_term_key()
        self.event_counts[key] = self.get_grade_event_count() + config.EVENT_COUNT_STEP
        self.last_event_time = self.elapsed

    def is_event_gap_passed(self):
        """직전 이벤트 이후 게임 시간이 최소 간격(EVENT_MIN_GAP, 8초) 이상 지났으면 True.

        이번 판에 이벤트가 아직 없었으면 True. 학년이 바뀌어도 이어서 센다.
        대화창이 떠 있는 동안은 경과 시간(elapsed)이 멈추므로 간격에 들어가지 않는다.
        """
        if self.last_event_time is None:
            return True
        return self.elapsed - self.last_event_time + config.TIME_EPSILON >= config.EVENT_MIN_GAP

    def can_have_event(self):
        """지금 학년 이벤트 수가 최대(5) 미만이면 True(아직 이벤트가 나올 수 있음)."""
        return self.get_grade_event_count() < config.EVENT_MAX_PER_GRADE

    def needs_guaranteed_event(self):
        """최소 보장 조건이면 True(다음 행동 때 확률과 상관없이 이벤트가 뜬다).

        학년 안 0~45초를 11.25초씩 4구간으로 나눈다. 지금까지 끝난 구간 수
        k = min(4, 학년 안 경과 // 11.25) 보다 그 학년 이벤트 수가 적으면 보장한다.
        """
        passed = int((self.get_time_in_grade() + config.TIME_EPSILON)
                     // config.EVENT_GUARANTEE_INTERVAL)
        finished_sections = min(config.EVENT_MIN_PER_GRADE, passed)
        return self.get_grade_event_count() < finished_sections

    def can_see_event(self, event):
        """이벤트 event가 지금 후보가 될 수 있으면 True.

        학년 조건(표에 적힌 학년에서만), 연계 조건(필요한 플래그가 켜져 있음),
        선택지형은 이번 판에 아직 안 나왔어야 한다(자동형은 반복 가능).
        대학원에서는 선택지형이 나오지 않는다(자동형만, 학년 조건은 4학년으로 본다).
        """
        if self.get_grade() not in event[config.EVENT_GRADES]:
            return False
        required = event[config.EVENT_REQUIRES]
        if required is not None and required not in self.flags:
            return False
        if event[config.EVENT_KIND] == config.EVENT_KIND_CHOICE:
            if self.is_in_grad_school():
                return False
            return event[config.EVENT_ID] not in self.seen_events
        return True

    def mark_event_seen(self, event_id):
        """선택지형 이벤트 event_id가 나왔다고 기록한다(한 판에 한 번만 나오게)."""
        self.seen_events.add(event_id)

    # ------------------------------------------------------------
    # 표정 (4일차)
    # ------------------------------------------------------------
    def get_mouth(self):
        """멘탈에 따른 입 모양 이름을 돌려준다.

        멘탈 60 이상 "smile"(웃는 입), 30~59 "flat"(일자 입), 30 미만 "cry"(우는 입).
        """
        if self.mental >= config.MENTAL_SMILE_MIN:
            return config.MOUTH_SMILE
        if self.mental >= config.MENTAL_FLAT_MIN:
            return config.MOUTH_FLAT
        return config.MOUTH_CRY

    def has_dark_circles(self):
        """체력이 30 미만이면 True(다크서클을 그린다)."""
        return self.health < config.LOW_GAUGE_LIMIT

    def has_glasses(self):
        """3학년부터 True(안경을 그린다)."""
        return self.get_grade() >= config.GLASSES_GRADE

    # ------------------------------------------------------------
    # 그리기 (도트 스타일)
    # ------------------------------------------------------------
    def draw_gauges(self, screen, font, shown_health=None, shown_mental=None):
        """왼쪽 상태 패널에 체력·멘탈 게이지를 그린다.

        지식 숫자는 상단 정보바에서 Game이 학년·남은 시간과 함께 그린다.
        체력 줄에는 하트 아이콘, 멘탈 줄에는 별 아이콘을 라벨 앞에 붙인다.
        shown_health / shown_mental은 막대 길이에 쓸 "표시값"이다(E4 부드러운 변화).
        주지 않으면 실제 값을 그대로 쓴다. 막대 색(빨강/초록)은 언제나 실제 값으로 정한다.
        """
        if shown_health is None:
            shown_health = self.health
        if shown_mental is None:
            shown_mental = self.mental
        self.draw_bar(screen, font, config.HEALTH_LABEL, self.health,
                      config.HEALTH_LABEL_Y, config.HEALTH_BAR_Y,
                      config.HEART_SPRITE, config.HEART_COLORS, shown_health)
        self.draw_bar(screen, font, config.MENTAL_LABEL, self.mental,
                      config.MENTAL_LABEL_Y, config.MENTAL_BAR_Y,
                      config.STAR_SPRITE, {config.SPRITE_INK: config.COLOR_SKY}, shown_mental)

    def draw_bar(self, screen, font, label, value, label_y, bar_y, icon, icon_colors,
                 shown_value):
        """아이콘·라벨과 도트 게이지 막대 하나를 그린다.

        - 막대 바깥에 계단형 모서리 남색 테두리(도트 1칸)를 두르고, 안쪽 빈 부분은 연한 색.
        - 채움 폭 = 막대 폭 x 표시값 / 100 (픽셀 단위로 정확히 비례). 값이 1이어도 2픽셀이 보인다.
        - 채움 색은 실제 값(value)이 30 미만이면 빨강, 아니면 초록. 맨 위 줄은 밝게, 맨 아래 줄은 어둡게.
        테두리는 막대 바깥쪽에 있어서 채움을 가리지 않는다.
        """
        # 1) 아이콘 + 라벨 (아이콘 세로 가운데에 글자를 맞춘다)
        icon_width, icon_height = sprite_size(icon, config.PIXEL_SIZE)
        draw_sprite(screen, icon, config.GAUGE_X, label_y, config.PIXEL_SIZE, icon_colors)
        label_text = render_text(font, label)
        label_rect = label_text.get_rect()
        label_rect.midleft = (config.GAUGE_X + icon_width + config.GAUGE_LABEL_GAP,
                              label_y + icon_height // config.HALF)
        screen.blit(label_text, label_rect)

        # 2) 테두리 상자: 막대보다 사방으로 1칸 크다 -> 상자 안쪽 = 막대 자리
        bar_rect = pygame.Rect(config.GAUGE_X, bar_y, config.BAR_WIDTH, config.BAR_HEIGHT)
        draw_pixel_box(screen, bar_rect.inflate(config.BOX_INSET, config.BOX_INSET),
                       config.COLOR_BAR_BG, light=config.COLOR_BAR_BG_SHADE)

        # 3) 값 비율만큼 채우기 (색은 실제 값 기준)
        if value < config.LOW_GAUGE_LIMIT:
            colors = (config.COLOR_RED, config.COLOR_RED_LIGHT, config.COLOR_RED_DARK)
        else:
            colors = (config.COLOR_GREEN, config.COLOR_GREEN_LIGHT, config.COLOR_GREEN_DARK)
        fill_width = int(config.BAR_WIDTH * shown_value / config.GAUGE_MAX)
        self.draw_bar_fill(screen, bar_rect, fill_width, colors)

    def draw_bar_fill(self, screen, bar_rect, fill_width, colors):
        """막대 왼쪽부터 fill_width 픽셀만큼 채운다. colors = (몸통, 위 줄, 아래 줄).

        fill_width가 0이면 폭 0인 사각형이라 아무것도 그려지지 않는다.
        """
        main, light, dark = colors
        fill = pygame.Rect(bar_rect.left, bar_rect.top, fill_width, bar_rect.height)
        pygame.draw.rect(screen, main, fill)
        pygame.draw.rect(screen, light, (fill.left, fill.top, fill.width, config.PIXEL_SIZE))
        pygame.draw.rect(screen, dark, (fill.left, fill.bottom - config.PIXEL_SIZE,
                                        fill.width, config.PIXEL_SIZE))

    def get_cell_size(self):
        """제자 스프라이트의 도트 1칸 크기를 돌려준다: 반지름 // 10 -> 4/5/6/7 픽셀.

        얼굴 격자가 20칸이므로 얼굴 지름 = 20 x 칸 크기 = 2 x 반지름(80/100/120/140)이 된다.
        """
        return self.get_radius() // config.FACE_CELL_DIVISOR

    def draw(self, screen, lift=config.NO_OFFSET):
        """오른쪽 제자 무대에 제자를 도트 스프라이트로 그린다.

        발밑 그림자 -> (얼굴 뒤 외형: 기타) -> 얼굴(머리카락 포함) -> 볼 홍조 -> 눈
        -> (체력 30 미만) 다크서클 -> (3학년부터) 안경 -> 입
        -> (얼굴 앞 외형: 머리띠·하트 머리핀·선글라스·커피잔) 순서로 찍는다.
        모든 부품은 얼굴 격자 칸 단위로 놓이고, 칸 크기가 학년마다 커지므로
        얼굴과 부품(외형 포함)이 함께 커진다. 외형은 눈·안경·다크서클·입 칸과 겹치지 않는 자리에 있다.
        lift는 점프·숨쉬기로 제자가 위로 뜬 높이(픽셀)다. 얼굴과 외형이 그만큼 올라가고
        발밑 그림자는 제자리에서 조금 작아진다. 크기(반지름)는 바뀌지 않는다.
        """
        radius = self.get_radius()
        cell = self.get_cell_size()
        left = config.STUDENT_CENTER_X - radius
        top = config.STUDENT_CENTER_Y - radius - lift

        self.draw_shadow(screen, radius, lift)
        self.draw_looks(screen, left, top, cell, config.LOOKS_BEHIND)
        draw_sprite(screen, config.FACE_SPRITE, left, top, cell, config.FACE_COLORS)
        self.draw_parts(screen, left, top, cell, config.BLUSH_SPRITE, config.BLUSH_POSITIONS)
        self.draw_parts(screen, left, top, cell, config.EYE_SPRITE, config.EYE_POSITIONS)
        if self.has_dark_circles():
            self.draw_parts(screen, left, top, cell,
                            config.DARK_CIRCLE_SPRITE, config.DARK_CIRCLE_POSITIONS)
        if self.has_glasses():
            self.draw_glasses(screen, left, top, cell)
        self.draw_mouth(screen, left, top, cell)
        self.draw_looks(screen, left, top, cell, config.LOOKS_FRONT)

    def draw_looks(self, screen, left, top, cell, order):
        """얻은 외형 중 order 목록에 있는 것을 order 차례대로 얼굴 격자 위치에 찍는다.

        order는 config.LOOKS_BEHIND(얼굴보다 먼저) 또는 config.LOOKS_FRONT(입 다음)다.
        얻지 않은 외형은 건너뛴다. 위치는 얼굴 격자 (열, 행)이라 얼굴 밖(음수 칸)도 될 수 있다.
        """
        for look in order:
            if look not in self.looks:
                continue
            (col, row), grid = config.LOOK_SPRITES[look]
            draw_sprite(screen, grid, left + col * cell, top + row * cell,
                        cell, config.LOOK_COLORS)

    def draw_traits(self, screen, font):
        """상태 패널 안 아래쪽(멘탈 막대 아래)에 얻은 특성을 작은 도트 배지로 그린다.

        얻은 순서대로 왼쪽 위부터 한 줄에 TRAIT_BADGE_COLUMNS(2)개씩 채운다.
        특성 4개가 모두 있어도 2 x 2로 패널 안에 들어간다. 배지 색은 특성마다 다르다.
        """
        for index, trait in enumerate(self.traits):
            row, col = divmod(index, config.TRAIT_BADGE_COLUMNS)
            box = pygame.Rect(
                config.TRAIT_BADGE_X + col * (config.TRAIT_BADGE_WIDTH + config.TRAIT_BADGE_GAP),
                config.TRAIT_BADGE_Y + row * (config.TRAIT_BADGE_HEIGHT + config.TRAIT_BADGE_GAP),
                config.TRAIT_BADGE_WIDTH, config.TRAIT_BADGE_HEIGHT)
            fill, light = config.TRAIT_COLORS[trait]
            inner = draw_pixel_box(screen, box, fill, light, drop=config.COLOR_DROP)
            text = render_text(font, trait)
            text_rect = text.get_rect()
            text_rect.center = inner.center
            screen.blit(text, text_rect)

    def draw_shadow(self, screen, radius, lift):
        """얼굴 아래에 납작한 도트 그림자(모서리 깎은 사각형)를 그린다.

        제자가 lift 픽셀 떠 있으면 그림자 가로를 조금 줄여 공중에 뜬 느낌을 준다.
        """
        width = (int(radius * config.SHADOW_WIDTH_RATIO)
                 - lift * config.SHADOW_SHRINK_PER_LIFT)
        shadow = pygame.Rect(config.ORIGIN, (width, config.SHADOW_HEIGHT))
        shadow.midtop = (config.STUDENT_CENTER_X,
                         config.STUDENT_CENTER_Y + radius + config.SHADOW_GAP)
        draw_cut_rect(screen, config.COLOR_STAGE_SHADOW, shadow)

    def draw_parts(self, screen, left, top, cell, grid, positions):
        """같은 모양 부품 grid를 얼굴 격자의 여러 칸 위치(positions)에 찍는다."""
        for col, row in positions:
            draw_sprite(screen, grid, left + col * cell, top + row * cell,
                        cell, config.FACE_COLORS)

    def draw_glasses(self, screen, left, top, cell):
        """안경(둥근 안경알 2개 + 가운데 다리 + 양옆 다리)을 얼굴 위에 찍는다."""
        for (col, row), grid in config.GLASSES_PARTS:
            draw_sprite(screen, grid, left + col * cell, top + row * cell,
                        cell, config.FACE_COLORS)

    def draw_mouth(self, screen, left, top, cell):
        """멘탈에 따른 입(웃는 입 / 일자 입 / 우는 입)을 찍는다. 모양은 get_mouth가 정한다."""
        (col, row), grid = config.MOUTH_SPRITES[self.get_mouth()]
        draw_sprite(screen, grid, left + col * cell, top + row * cell,
                    cell, config.FACE_COLORS)
