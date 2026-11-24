"""제자(Student) 클래스가 들어 있는 파일."""

import pygame

import config
from button import draw_cut_rect, draw_pixel_box, draw_sprite, render_text, sprite_size


def clamp(value, low, high):
    """value를 low 이상 high 이하로 잘라서 돌려준다."""
    return max(low, min(value, high))


def judge_ending(seconds):
    """졸업까지 걸린 게임 시간 seconds(초)로 졸업 엔딩 이름을 돌려준다(기획서 2절)."""
    if seconds <= config.TOP_GRADUATE_SECONDS + config.TIME_EPSILON:
        return config.ENDING_TOP
    if seconds <= config.NORMAL_GRADUATE_SECONDS + config.TIME_EPSILON:
        return config.ENDING_NORMAL
    return config.ENDING_BARELY


class Student:
    """교수가 돌보는 제자 한 명."""

    def __init__(self, upgrades=None):
        """게이지를 시작값으로 정하고 경과 시간을 0으로 둔다."""
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
        self.event_counts = {}     # {60초 주기 번호: 그 주기에 나온 이벤트 수}. 없는 주기는 0번
        self.last_event_time = None  # 직전 이벤트가 뜬 게임 시각(초). 이번 판에 아직 없으면 None
        self.grad_year = config.GRAD_YEAR_UNDERGRAD  # 대학원 년차. 0이면 학부(1~4학년)
        self.grade = config.FIRST_GRADE  # 지금까지 오른 학년(1~4). 지식이 줄어도 내려가지 않는다
        self.graduation_time = None  # 졸업한 순간의 경과 시간(초). 아직 졸업 전이면 None
        self.grad_entry_time = None  # 대학원에 들어간 순간의 경과 시간(초). 학부면 None
        self.full_until = None     # 버프 '든든함'이 끝나는 경과 시간(초). 학식을 안 먹었으면 None

    # ------------------------------------------------------------
    # 최댓값 (기획서 3절: 체력 증진·멘탈 관리 업그레이드)
    # ------------------------------------------------------------
    @property
    def max_health(self):
        """체력 최댓값 = 100 + 10 x 체력 증진 레벨."""
        return config.GAUGE_MAX + self.get_upgrade_bonus(config.UPGRADE_HEALTH_MAX)

    @property
    def max_mental(self):
        """멘탈 최댓값 = 100 + 10 x 멘탈 관리 레벨."""
        return config.GAUGE_MAX + self.get_upgrade_bonus(config.UPGRADE_MENTAL_MAX)

    # ------------------------------------------------------------
    # 디버프와 버프 (기획서 2절 "디버프와 버프")
    # ------------------------------------------------------------
    def is_tired(self):
        """디버프 '피곤'이면 True: 체력이 30 미만(최댓값과 상관없이 30)."""
        return self.health < config.LOW_GAUGE_LIMIT

    def is_depressed(self):
        """디버프 '우울'이면 True: 멘탈이 30 미만."""
        return self.mental < config.LOW_GAUGE_LIMIT

    def has_debuff(self, name):
        """디버프 name("피곤" 또는 "우울")이 지금 붙어 있으면 True. 모르는 이름이면 False."""
        if name == config.DEBUFF_TIRED:
            return self.is_tired()
        if name == config.DEBUFF_DEPRESSED:
            return self.is_depressed()
        return False

    def get_full_duration(self):
        """학식 한 번으로 붙는 든든함 지속 시간(초) = 30 + 6 x 학식 메뉴 개선 Lv (+ 체력 단련 10)."""
        return (config.FULL_DURATION + self.get_upgrade_bonus(config.UPGRADE_MENU)
                + self.get_trait_bonus(config.BONUS_FULL_TIME))

    def get_full_time_left(self):
        """든든함이 끝날 때까지 남은 시간(초)을 돌려준다(없거나 끝났으면 0)."""
        if self.full_until is None:
            return config.ZERO_TIME
        return max(config.ZERO_TIME, self.full_until - self.elapsed)

    def is_full_buff_active(self):
        """버프 '든든함'이 붙어 있으면 True(남은 시간이 0보다 클 때)."""
        return self.get_full_time_left() > config.TIME_EPSILON

    def get_statuses(self):
        """지금 붙어 있는 디버프·버프 이름 목록을 돌려준다(상태 배지용): 피곤, 우울, 든든함 순서."""
        statuses = []
        if self.is_tired():
            statuses.append(config.DEBUFF_TIRED)
        if self.is_depressed():
            statuses.append(config.DEBUFF_DEPRESSED)
        if self.is_full_buff_active():
            statuses.append(config.BUFF_FULL)
        return statuses

    # ------------------------------------------------------------
    # 진급과 졸업 (기획서 2절): 학년은 누적 지식으로 오른다
    # ------------------------------------------------------------
    def get_grade(self):
        """지금 학년(1~4)을 돌려준다. 대학원에서는 4로 둔다."""
        if self.is_in_grad_school():
            return config.MAX_GRADE
        return self.grade

    def get_grad_goal(self, year):
        """대학원 year년차를 마치는(다음 년차로 오르는) 누적 지식 목표를 돌려준다."""
        goal = config.GRADUATION_KNOWLEDGE
        for k in range(config.GRAD_FIRST_YEAR, year + config.GRAD_YEAR_STEP):
            goal += (config.GRAD_GOAL_FIRST_STEP
                     + config.GRAD_GOAL_STEP_GROWTH * (k - config.GRAD_FIRST_YEAR))
        return goal

    def get_next_goal(self):
        """다음 목표(누적 지식)를 돌려준다."""
        if self.is_in_grad_school():
            return self.get_grad_goal(self.grad_year)
        if self.grade < config.MAX_GRADE:
            return config.GRADE_GOALS[self.grade - config.FIRST_GRADE]
        return config.GRADUATION_KNOWLEDGE

    def get_goal_start(self):
        """지금 목표 구간이 시작된 누적 지식(앞 목표)을 돌려준다(진행 막대의 왼쪽 끝)."""
        if self.is_in_grad_school():
            return self.get_grad_goal(self.grad_year - config.GRAD_YEAR_STEP)
        if self.grade == config.FIRST_GRADE:
            return config.KNOWLEDGE_START
        return config.GRADE_GOALS[self.grade - config.FIRST_GRADE - config.GRADE_STEP]

    def get_goal_progress(self):
        """다음 목표까지의 진행률(0~1)을 돌려준다(정보바 아래 목표 진행 막대용)."""
        start = self.get_goal_start()
        ratio = (self.knowledge - start) / (self.get_next_goal() - start)
        return clamp(ratio, config.GOAL_PROGRESS_MIN, config.GOAL_PROGRESS_MAX)

    def get_knowledge_to_goal(self):
        """다음 목표까지 더 모아야 하는 지식(0 이상)을 돌려준다: "다음 학년까지 지식 n"의 n."""
        return max(config.GAUGE_MIN, self.get_next_goal() - self.knowledge)

    def has_graduated(self):
        """학부를 졸업했으면 True(졸업 순간의 경과 시간이 기록되어 있다)."""
        return self.graduation_time is not None

    def promote(self):
        """지금 누적 지식으로 진급·졸업·대학원 년차 오름을 판정하고, 오른 횟수를 돌려준다."""
        count = config.PROMOTION_COUNT_START
        if self.is_dropped_out():
            return count
        if self.is_in_grad_school():
            while self.knowledge >= self.get_next_goal():
                self.grad_year += config.GRAD_YEAR_STEP
                count += config.GRAD_YEAR_STEP
            return count
        if self.has_graduated():
            return count
        while self.grade < config.MAX_GRADE and self.knowledge >= self.get_next_goal():
            self.grade += config.GRADE_STEP
            count += config.GRADE_STEP
        if self.grade == config.MAX_GRADE and self.knowledge >= config.GRADUATION_KNOWLEDGE:
            self.graduation_time = self.elapsed
        return count

    # ------------------------------------------------------------
    # 60초 주기 (기획서 2절): 계절·낮밤·시험 기간·이벤트 횟수용 시계
    # ------------------------------------------------------------
    def get_cycle_index(self):
        """지금 60초 주기 번호를 돌려준다: 경과 시간 // 60 + 1 (0~60초 1번, 60~120초 2번 …)."""
        passed = int((self.elapsed + config.TIME_EPSILON) // config.CYCLE_SECONDS)
        return passed + config.CYCLE_INDEX_START

    def get_cycle_time(self):
        """지금 주기 안에서 흐른 시간(0~60초 미만)을 돌려준다: 경과 시간 % 60."""
        cycle_start = (self.get_cycle_index() - config.CYCLE_INDEX_START) * config.CYCLE_SECONDS
        return max(config.ZERO_TIME, self.elapsed - cycle_start)

    # ------------------------------------------------------------
    # 대학원 (기획서 3절)
    # ------------------------------------------------------------
    def is_in_grad_school(self):
        """대학원에 다니는 중이면 True(대학원 년차가 1 이상)."""
        return self.grad_year > config.GRAD_YEAR_UNDERGRAD

    def enter_grad_school(self):
        """졸업한 제자가 대학원 1년차로 들어간다."""
        if self.is_in_grad_school() or self.is_dropped_out() or not self.has_graduated():
            return False
        self.grad_year = config.GRAD_FIRST_YEAR
        self.grad_entry_time = self.elapsed
        return True

    def get_grad_cycles(self):
        """대학원에 들어간 뒤 다 채운 60초 주기 수를 돌려준다(학부거나 들어간 시각이 없으면 0)."""
        if not self.is_in_grad_school() or self.grad_entry_time is None:
            return config.GRAD_CYCLES_NONE
        spent = self.elapsed - self.grad_entry_time + config.TIME_EPSILON
        return int(max(config.ZERO_TIME, spent) // config.CYCLE_SECONDS)

    def get_grad_decay_ratio(self):
        """대학원 자연 감소 배수 = 1 + 1.0 x n + 1.5 x c 를 돌려준다(학부는 1)."""
        return (config.NO_RATIO + config.GRAD_DECAY_BONUS * self.grad_year
                + config.GRAD_CYCLE_DECAY_BONUS * self.get_grad_cycles())

    # ------------------------------------------------------------
    # 게이지 값 바꾸기
    # ------------------------------------------------------------
    def change_health(self, amount):
        """체력을 amount만큼 바꾸고 0~체력 최댓값(max_health) 안으로 맞춘다."""
        value = round(self.health + amount, config.GAUGE_DECIMALS)
        self.health = clamp(value, config.GAUGE_MIN, self.max_health)

    def change_mental(self, amount):
        """멘탈을 amount만큼 바꾸고 0~멘탈 최댓값(max_mental) 안으로 맞춘다."""
        value = round(self.mental + amount, config.GAUGE_DECIMALS)
        self.mental = clamp(value, config.GAUGE_MIN, self.max_mental)

    def change_knowledge(self, amount):
        """지식을 amount만큼 바꾼다. 지식은 0 아래로 내려가지 않는다(상한 없음)."""
        self.knowledge = max(config.GAUGE_MIN, self.knowledge + amount)

    # ------------------------------------------------------------
    # 시간 흐름과 자연 감소
    # ------------------------------------------------------------
    def update(self, dt):
        """dt초만큼 시간을 흘려 게이지를 자연 감소시킨다."""
        end_time = self.elapsed + dt
        self.decay_timer += dt
        while self.decay_timer + config.TIME_EPSILON >= config.DECAY_INTERVAL:
            self.decay_timer -= config.DECAY_INTERVAL
            # 이번 1초 감소가 일어나는 시각 = 끝 시각 - 아직 남겨 둔 시간
            self.elapsed = end_time - self.decay_timer
            self.decay_once()
        self.elapsed = end_time

    def decay_once(self):
        """1초분 자연 감소를 한 번 적용한다."""
        regen = self.get_self_care_regen()
        self.change_health(round(regen - self.get_health_decay(), config.GAUGE_DECIMALS))
        self.change_mental(round(regen - self.get_mental_decay(), config.GAUGE_DECIMALS))

    def get_self_care_regen(self):
        """자기 관리 업그레이드로 1초마다 체력·멘탈에 더하는 양 = 0.2 x 레벨."""
        if self.get_upgrade_level(config.UPGRADE_SELF_CARE) == config.LEVEL_START:
            return config.NO_CHANGE
        return self.get_upgrade_bonus(config.UPGRADE_SELF_CARE)

    def get_health_decay(self):
        """1초마다 줄어드는 체력 양을 돌려준다: 1 x 건강 관리 배수 (든든함이면 x0.5)."""
        decay = self.apply_decay_ratio(config.HEALTH_DECAY_PER_SEC)
        if self.is_full_buff_active():
            decay = round(decay * config.FULL_HEALTH_DECAY_RATIO, config.GAUGE_DECIMALS)
        return decay

    def get_mental_decay(self):
        """1초마다 줄어드는 멘탈 양을 돌려준다: 평소 1, 시험 기간 2 (x 건강 관리 배수)."""
        if self.is_exam_period():
            return self.apply_decay_ratio(config.MENTAL_DECAY_PER_SEC_EXAM)
        return self.apply_decay_ratio(config.MENTAL_DECAY_PER_SEC)

    def apply_decay_ratio(self, amount):
        """자연 감소량 amount에 건강 관리 배수 (1 - 0.1 x 레벨)와
        대학원 배수 (1 + 0.5 x 년차 + 1.0 x 대학원 주기 수)를 곱해 돌려준다."""
        level = self.get_upgrade_level(config.UPGRADE_HEALTH_CARE)
        if level == config.LEVEL_START and not self.is_in_grad_school():
            return amount
        ratio = config.FULL_RATIO - self.get_upgrade_bonus(config.UPGRADE_HEALTH_CARE)
        return round(amount * ratio * self.get_grad_decay_ratio(), config.GAUGE_DECIMALS)

    # ------------------------------------------------------------
    # 업그레이드 (기획서 3절)
    # ------------------------------------------------------------
    def get_upgrade_level(self, upgrade_id):
        """업그레이드 upgrade_id의 지금 레벨을 돌려준다(사지 않았으면 0)."""
        return self.upgrades.get(upgrade_id, config.LEVEL_START)

    def get_upgrade_bonus(self, upgrade_id):
        """업그레이드 upgrade_id가 주는 효과 크기 = 레벨 x 레벨당 효과 를 돌려준다."""
        per_level = config.UPGRADES_BY_ID[upgrade_id][config.UPGRADE_PER_LEVEL]
        return self.get_upgrade_level(upgrade_id) * per_level

    def is_dropped_out(self):
        """체력이나 멘탈이 0이면 True(휴학 조건)를 돌려준다."""
        return self.health <= config.GAUGE_MIN or self.mental <= config.GAUGE_MIN

    # ------------------------------------------------------------
    # 시험 기간과 엔딩
    # ------------------------------------------------------------
    def is_exam_period(self):
        """지금이 시험 기간(60초 주기의 마지막 15초)이면 True를 돌려준다."""
        exam_start = config.CYCLE_SECONDS - config.EXAM_SECONDS
        return self.get_cycle_time() + config.TIME_EPSILON >= exam_start

    def get_graduation_ending(self):
        """졸업까지 걸린 시간으로 졸업 엔딩 이름을 돌려준다(judge_ending 사용)."""
        if not self.has_graduated():
            return None
        return judge_ending(self.graduation_time)

    def get_ending(self):
        """지금 엔딩이 났는지 보고 엔딩 이름을 돌려준다. 아직 아니면 None."""
        if self.is_dropped_out():
            if self.is_in_grad_school():
                return config.ENDING_GRAD_TEXT.format(self.grad_year)
            return config.ENDING_LEAVE
        if not self.is_in_grad_school():
            return self.get_graduation_ending()
        return None

    # ------------------------------------------------------------
    # 행동 (기획서 2절 "행동 효과"): 회복은 휴식에서만
    # ------------------------------------------------------------
    def feed(self):
        """학식 먹이기: 게이지는 바로 오르지 않고 버프 '든든함'이 붙는다."""
        self.full_until = self.elapsed + self.get_full_duration()

    def rest(self, recovery_ratio=config.NO_RATIO):
        """쉬게 하기: 체력 +15, 멘탈 +20, 지식 -2."""
        bed = self.get_upgrade_bonus(config.UPGRADE_BED)
        health = (config.REST_HEALTH + self.get_trait_bonus(config.BONUS_REST_HEALTH)
                  + self.get_upgrade_bonus(config.UPGRADE_CAFE) + bed)
        mental = config.REST_MENTAL + self.get_trait_bonus(config.BONUS_REST_MENTAL) + bed
        self.change_health(round(health * recovery_ratio))
        self.change_mental(round(mental * recovery_ratio))
        self.change_knowledge(config.REST_KNOWLEDGE)

    def study(self, knowledge_ratio=config.NO_RATIO, cost_ratio=config.NO_RATIO):
        """공부시키기: 지식 +(공부 지식량), 체력 -5, 멘탈 -8 (특성·업그레이드 보정 뒤 방침 배수)."""
        health = (config.STUDY_HEALTH + self.get_trait_bonus(config.BONUS_STUDY_HEALTH)
                  + self.get_upgrade_bonus(config.UPGRADE_GYM))
        knowledge = (self.get_study_knowledge() + self.get_upgrade_bonus(config.UPGRADE_BOOK)
                     + self.get_upgrade_bonus(config.UPGRADE_LIBRARY)
                     + self.get_trait_bonus(config.BONUS_STUDY_KNOWLEDGE)) * knowledge_ratio
        if self.is_tired():
            knowledge *= config.TIRED_KNOWLEDGE_RATIO
        self.change_knowledge(round(knowledge))
        self.change_health(round(health * cost_ratio))
        mental = config.STUDY_MENTAL + self.get_trait_bonus(config.BONUS_STUDY_MENTAL)
        self.change_mental(round(mental * cost_ratio))

    def get_study_knowledge(self):
        """공부시키기 한 번에 오르는 지식 양을 돌려준다: 평소 10, 시험 기간 20."""
        if self.is_exam_period():
            return config.STUDY_KNOWLEDGE_EXAM
        return config.STUDY_KNOWLEDGE

    # ------------------------------------------------------------
    # 성장: 학년(get_grade)에 따라 크기·안경이 바뀐다
    # ------------------------------------------------------------
    def get_radius(self):
        """캐릭터 반지름을 돌려준다: 40 + (학년-1) x 10 -> 40/50/60/70."""
        return (config.BASE_RADIUS
                + (self.get_grade() - config.FIRST_GRADE) * config.RADIUS_PER_GRADE)

    # ------------------------------------------------------------
    # 랜덤 이벤트와 성장 (기획서 4절)
    # ------------------------------------------------------------
    def get_trait_bonus(self, bonus_name):
        """가진 특성들이 행동 효과 bonus_name에 더해 주는 양의 합을 돌려준다(없으면 0)."""
        total = config.TRAIT_BONUS_START
        for trait in self.traits:
            total += config.TRAIT_BONUSES[trait].get(bonus_name, config.NO_CHANGE)
        return total

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
        """이벤트 효과 {게이지 속성 이름: 변화량}을 적용한다."""
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

    def get_cycle_event_count(self):
        """지금 60초 주기에 나온 이벤트 수를 돌려준다."""
        return self.event_counts.get(self.get_cycle_index(), config.EVENT_COUNT_START)

    def count_event(self):
        """지금 주기의 이벤트 수를 하나 늘리고, 지금 게임 시각을 직전 이벤트 시각으로 적어 둔다."""
        key = self.get_cycle_index()
        self.event_counts[key] = self.get_cycle_event_count() + config.EVENT_COUNT_STEP
        self.last_event_time = self.elapsed

    def is_event_gap_passed(self):
        """직전 이벤트 이후 게임 시간이 최소 간격(EVENT_MIN_GAP, 8초) 이상 지났으면 True."""
        if self.last_event_time is None:
            return True
        return self.elapsed - self.last_event_time + config.TIME_EPSILON >= config.EVENT_MIN_GAP

    def can_have_event(self):
        """지금 주기 이벤트 수가 최대(5) 미만이면 True(아직 이벤트가 나올 수 있음)."""
        return self.get_cycle_event_count() < config.EVENT_MAX_PER_GRADE

    def needs_guaranteed_event(self):
        """최소 보장 조건이면 True(다음 행동 때 확률과 상관없이 이벤트가 뜬다)."""
        passed = int((self.get_cycle_time() + config.TIME_EPSILON)
                     // config.EVENT_GUARANTEE_INTERVAL)
        finished_sections = min(config.EVENT_MIN_PER_GRADE, passed)
        return self.get_cycle_event_count() < finished_sections

    def can_see_event(self, event):
        """이벤트 event가 지금 후보가 될 수 있으면 True."""
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
    # 표정
    # ------------------------------------------------------------
    def get_mouth(self):
        """멘탈에 따른 입 모양 이름을 돌려준다."""
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
        """왼쪽 상태 패널에 체력·멘탈 게이지를 그린다."""
        if shown_health is None:
            shown_health = self.health
        if shown_mental is None:
            shown_mental = self.mental
        self.draw_bar(screen, font, config.HEALTH_LABEL, self.health, self.max_health,
                      config.HEALTH_LABEL_Y, config.HEALTH_BAR_Y,
                      config.HEART_SPRITE, config.HEART_COLORS, shown_health)
        self.draw_bar(screen, font, config.MENTAL_LABEL, self.mental, self.max_mental,
                      config.MENTAL_LABEL_Y, config.MENTAL_BAR_Y,
                      config.STAR_SPRITE, {config.SPRITE_INK: config.COLOR_SKY}, shown_mental)

    def draw_bar(self, screen, font, label, value, max_value, label_y, bar_y, icon,
                 icon_colors, shown_value):
        """아이콘·라벨과 도트 게이지 막대 하나를 그린다."""
        # 1) 아이콘 + 라벨 (아이콘 세로 가운데에 글자를 맞춘다)
        icon_width, icon_height = sprite_size(icon, config.PIXEL_SIZE)
        draw_sprite(screen, icon, config.GAUGE_X, label_y, config.PIXEL_SIZE, icon_colors)
        label_text = render_text(font, label)
        label_rect = label_text.get_rect()
        label_rect.midleft = (config.GAUGE_X + icon_width + config.GAUGE_LABEL_GAP,
                              label_y + icon_height // config.HALF)
        screen.blit(label_text, label_rect)
        value_text = render_text(font, config.GAUGE_VALUE_TEXT.format(round(value), max_value))
        value_rect = value_text.get_rect()
        value_rect.midright = (config.GAUGE_X + config.BAR_WIDTH, label_rect.centery)
        screen.blit(value_text, value_rect)

        # 2) 테두리 상자: 막대보다 사방으로 1칸 크다 -> 상자 안쪽 = 막대 자리
        bar_rect = pygame.Rect(config.GAUGE_X, bar_y, config.BAR_WIDTH, config.BAR_HEIGHT)
        draw_pixel_box(screen, bar_rect.inflate(config.BOX_INSET, config.BOX_INSET),
                       config.COLOR_BAR_BG, light=config.COLOR_BAR_BG_SHADE)

        # 3) 값 비율만큼 채우기 (색은 실제 값 기준)
        if value < config.LOW_GAUGE_LIMIT:
            colors = (config.COLOR_RED, config.COLOR_RED_LIGHT, config.COLOR_RED_DARK)
        else:
            colors = (config.COLOR_GREEN, config.COLOR_GREEN_LIGHT, config.COLOR_GREEN_DARK)
        shown_value = clamp(shown_value, config.GAUGE_MIN, max_value)
        fill_width = int(config.BAR_WIDTH * shown_value / max_value)
        self.draw_bar_fill(screen, bar_rect, fill_width, colors)

    def draw_bar_fill(self, screen, bar_rect, fill_width, colors):
        """막대 왼쪽부터 fill_width 픽셀만큼 채운다. colors = (몸통, 위 줄, 아래 줄)."""
        main, light, dark = colors
        fill = pygame.Rect(bar_rect.left, bar_rect.top, fill_width, bar_rect.height)
        pygame.draw.rect(screen, main, fill)
        pygame.draw.rect(screen, light, (fill.left, fill.top, fill.width, config.PIXEL_SIZE))
        pygame.draw.rect(screen, dark, (fill.left, fill.bottom - config.PIXEL_SIZE,
                                        fill.width, config.PIXEL_SIZE))

    def get_cell_size(self):
        """제자 스프라이트의 도트 1칸 크기를 돌려준다: 반지름 // 10 -> 4/5/6/7 픽셀."""
        return self.get_radius() // config.FACE_CELL_DIVISOR

    def draw(self, screen, lift=config.NO_OFFSET):
        """오른쪽 제자 무대에 제자를 도트 스프라이트로 그린다."""
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
        """얻은 외형 중 order 목록에 있는 것을 order 차례대로 얼굴 격자 위치에 찍는다."""
        for look in order:
            if look not in self.looks:
                continue
            (col, row), grid = config.LOOK_SPRITES[look]
            draw_sprite(screen, grid, left + col * cell, top + row * cell,
                        cell, config.LOOK_COLORS)

    def draw_traits(self, screen, font):
        """상태 패널 안 아래쪽(멘탈 막대 아래)에 얻은 특성을 작은 도트 배지로 그린다."""
        self.draw_badges(screen, font, self.traits, config.TRAIT_BADGE_Y, config.TRAIT_COLORS)

    def draw_status_badges(self, screen, font, statuses):
        """상태 패널 위쪽(체력 라벨 위)에 지금 붙은 디버프·버프를 아이콘 + 이름 배지로 그린다."""
        self.draw_badges(screen, font, statuses, config.STATUS_BADGE_Y, config.STATUS_COLORS,
                         config.STATUS_ICONS)

    def get_badge_rect(self, index, top):
        """top부터 2열로 놓는 배지 중 index번째 배지의 사각형을 돌려준다(특성·상태 배지 공통)."""
        row, col = divmod(index, config.TRAIT_BADGE_COLUMNS)
        return pygame.Rect(
            config.TRAIT_BADGE_X + col * (config.TRAIT_BADGE_WIDTH + config.TRAIT_BADGE_GAP),
            top + row * (config.TRAIT_BADGE_HEIGHT + config.TRAIT_BADGE_GAP),
            config.TRAIT_BADGE_WIDTH, config.TRAIT_BADGE_HEIGHT)

    def draw_badges(self, screen, font, names, top, colors, icons=None):
        """이름 목록 names를 top부터 2열 도트 배지로 그린다. icons가 있으면 이름 앞에 아이콘을 찍는다."""
        for index, name in enumerate(names):
            box = self.get_badge_rect(index, top)
            fill, light = colors[name]
            inner = draw_pixel_box(screen, box, fill, light, drop=config.COLOR_DROP)
            text = render_text(font, name)
            text_rect = text.get_rect()
            if icons is None:
                text_rect.center = inner.center
            else:
                icon = icons[name]
                icon_width, icon_height = sprite_size(icon, config.STATUS_ICON_CELL)
                icon_left = inner.left + config.STATUS_ICON_PAD
                draw_sprite(screen, icon, icon_left, inner.centery - icon_height // config.HALF,
                            config.STATUS_ICON_CELL, config.STATUS_ICON_COLORS)
                text_rect.midleft = (icon_left + icon_width + config.STATUS_ICON_GAP, inner.centery)
            screen.blit(text, text_rect)

    def draw_shadow(self, screen, radius, lift):
        """얼굴 아래에 납작한 도트 그림자(모서리 깎은 사각형)를 그린다."""
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
        """안경 부품들을 얼굴 위에 찍는다."""
        for (col, row), grid in config.GLASSES_PARTS:
            self.draw_parts(screen, left, top, cell, grid, [(col, row)])

    def draw_mouth(self, screen, left, top, cell):
        """멘탈에 따른 입(get_mouth)을 찍는다."""
        (col, row), grid = config.MOUTH_SPRITES[self.get_mouth()]
        self.draw_parts(screen, left, top, cell, grid, [(col, row)])
