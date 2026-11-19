"""H단위 검수: 연구비·명성·업그레이드 10종·U 패널·record.json 확장 (기획서 10절, jeja-spec 15절).

이 파일은 conftest 의 AUTO_OFF_FILES / EVENTS_OFF_FILES 에 없으므로 자동 행동·이벤트가 켜진 채로 돈다.
자동 행동이 끼어들면 안 되는 테스트는 no_auto, 이벤트가 끼어들면 안 되는 테스트는 no_events 를 직접 쓴다.
"""

import ast
import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
import game as game_module  # noqa: E402
from conftest import press  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402

ROOT = Path(config.__file__).parent
FRAME = 1 / 60
FEED, REST, STUDY = config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY
SF, BAL, RF = config.POLICY_STUDY_FOCUS, config.POLICY_BALANCED, config.POLICY_REST_FOCUS
MENU, BED, BOOK = config.UPGRADE_MENU, config.UPGRADE_BED, config.UPGRADE_BOOK
TIME, CARE, LIB = config.UPGRADE_TIME, config.UPGRADE_HEALTH_CARE, config.UPGRADE_LIBRARY
CAFE, GYM, CHARM, SCHOL = (config.UPGRADE_CAFE, config.UPGRADE_GYM, config.UPGRADE_CHARM,
                           config.UPGRADE_SCHOLARSHIP)
RECORD_KEYS = {"best_knowledge", "money", "fame", "upgrades"}

# 기획서 10절 업그레이드 표: id -> (최대 레벨, 기본 가격)
SPEC_TABLE = {
    "menu": (5, 80), "bed": (5, 80), "reference_book": (5, 120),
    "time_management": (5, 150), "health_care": (5, 150),
    "library": (1, 300), "cafe": (1, 300), "gym": (1, 300),
    "lucky_charm": (3, 200), "scholarship": (1, 250),
}


def spec_cost(base, level):
    """기획서 가격 = 내림(기본 가격 x 1.6^레벨). 정수 산술로 정확히 계산한다(16^L / 10^L)."""
    return base * 16 ** level // 10 ** level


def levels(**kw):
    """모든 업그레이드 0레벨 사전에 kw 레벨을 덮어쓴 사전."""
    d = {uid: 0 for uid in config.UPGRADE_IDS}
    for key, value in kw.items():
        d[{"menu": MENU, "bed": BED, "book": BOOK, "time": TIME, "care": CARE, "lib": LIB,
           "cafe": CAFE, "gym": GYM, "charm": CHARM, "schol": SCHOL}[key]] = value
    return d


def read_record(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_raw(path, text):
    Path(path).write_text(text, encoding="utf-8")


@pytest.fixture
def g(no_events, no_auto):
    """이벤트·자동 행동을 끈 채 타이틀에서 Enter 를 눌러 게임 중인 Game(행동은 테스트가 직접)."""
    game = Game()
    press(game, pygame.K_RETURN)
    assert game.state == config.STATE_PLAYING
    yield game
    pygame.quit()


def graduate_with(game, knowledge):
    """게임 중 game 을 지식 knowledge 로 240초 졸업시킨다(update 경로)."""
    game.student.knowledge = knowledge
    game.student.elapsed = config.TOTAL_SECONDS - FRAME / 2
    game.update(FRAME)
    assert game.state == config.STATE_ENDING
    assert game.ending != config.ENDING_LEAVE


def leave_with(game, knowledge):
    """게임 중 game 을 지식 knowledge 로 휴학시킨다(자연 감소로 체력 0)."""
    game.student.knowledge = knowledge
    game.student.health = 1
    game.update(1.0)
    assert game.ending == config.ENDING_LEAVE


def click(game, pos):
    game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


# ======================= config 수치 (기획서 10절 표) =======================

def test_upgrade_table_matches_spec():
    assert config.UPGRADE_IDS == list(SPEC_TABLE)
    for uid, (max_level, base) in SPEC_TABLE.items():
        u = config.UPGRADES_BY_ID[uid]
        assert u[config.UPGRADE_MAX_LEVEL] == max_level, uid
        assert u[config.UPGRADE_BASE_COST] == base, uid
    per = {uid: config.UPGRADES_BY_ID[uid][config.UPGRADE_PER_LEVEL] for uid in SPEC_TABLE}
    assert per == {"menu": 4, "bed": 4, "reference_book": 2, "time_management": 0.2,
                   "health_care": 0.1, "library": 3, "cafe": 5, "gym": 2,
                   "lucky_charm": 0.05, "scholarship": 30}


def test_money_constants():
    assert config.UPGRADE_COST_GROWTH == 1.6
    assert config.FAME_MONEY_BONUS == 0.1
    assert config.GRADUATION_BONUS == {config.ENDING_TOP: 200, config.ENDING_NORMAL: 100,
                                       config.ENDING_BARELY: 50}
    assert config.ENDING_LEAVE not in config.GRADUATION_BONUS
    assert (config.RECORD_KEY, config.RECORD_MONEY_KEY, config.RECORD_FAME_KEY,
            config.RECORD_UPGRADES_KEY) == ("best_knowledge", "money", "fame", "upgrades")
    assert config.SCHOLARSHIP_EVENT[config.EVENT_KIND] == config.EVENT_KIND_AUTO
    assert config.SCHOLARSHIP_EVENT[config.EVENT_TITLE] == "장학금을 받았다"
    assert config.SCHOLARSHIP_EVENT[config.EVENT_EFFECTS] == {}
    assert config.SCHOLARSHIP_EVENT not in config.AUTO_EVENTS   # 사야만 후보가 된다


# ======================= 업그레이드 효과 (Student) =======================

@pytest.mark.parametrize("lv", range(6))
def test_menu_feed_health(lv):
    s = Student(levels(menu=lv))
    s.health = 10
    s.feed()
    assert s.health == 10 + 20 + 4 * lv


@pytest.mark.parametrize("lv", [0, 3, 5])
def test_menu_stacks_with_fitness_trait_and_caps(lv):
    s = Student(levels(menu=lv))
    s.add_trait(config.TRAIT_FITNESS)
    s.health = 10
    s.feed()
    assert s.health == 10 + 25 + 4 * lv
    s.health = 90
    s.feed()
    assert s.health == 100


@pytest.mark.parametrize("lv", range(6))
def test_bed_rest_mental(lv):
    s = Student(levels(bed=lv))
    s.mental, s.health, s.knowledge = 10, 50, 30
    s.rest()
    assert (s.mental, s.health, s.knowledge) == (10 + 20 + 4 * lv, 50, 28)


def test_bed_stacks_with_music_trait():
    s = Student(levels(bed=5))
    s.add_trait(config.TRAIT_MUSIC)
    s.mental = 10
    s.rest()
    assert s.mental == 10 + 25 + 20


@pytest.mark.parametrize("traits, expected", [([], 5), ([config.TRAIT_LOVE], 10)])
def test_cafe_rest_health_and_love_trait(traits, expected):
    s = Student(levels(cafe=1))
    for t in traits:
        s.add_trait(t)
    s.health = 40
    s.rest()
    assert s.health == 40 + expected
    s0 = Student()   # 카페가 없으면 휴식 체력 변화 없음
    s0.health = 40
    s0.rest()
    assert s0.health == 40


# 공부: (기본 10/시험 20 + 참고서 2/Lv + 도서관 3) x 지식배수 -> round
@pytest.mark.parametrize("book, lib, policy, exam, expected", [
    (0, 0, BAL, False, 10), (1, 0, BAL, False, 12), (5, 0, BAL, False, 20),
    (0, 1, BAL, False, 13), (5, 1, BAL, False, 23),
    (5, 1, SF, False, round(23 * 1.4)),   # 32.2 -> 32
    (5, 1, RF, False, round(23 * 0.8)),   # 18.4 -> 18
    (2, 1, SF, False, round(17 * 1.4)),   # 23.8 -> 24
    (5, 1, BAL, True, 33), (5, 1, SF, True, round(33 * 1.4)),   # 46.2 -> 46
    (1, 0, RF, True, round(22 * 0.8)),    # 17.6 -> 18
    (0, 1, SF, True, round(23 * 1.4)),    # 시험 20+3=23 -> 32
])
def test_study_knowledge_book_library_policy_exam(book, lib, policy, exam, expected):
    s = Student(levels(book=book, lib=lib))
    if exam:
        s.elapsed = 50.0
        assert s.is_exam_period()
    p = config.POLICIES[policy]
    s.study(p[config.POLICY_KNOWLEDGE_RATIO], p[config.POLICY_COST_RATIO])
    assert s.knowledge == expected


# 공부 체력: (-5 + 카페인 2 + 헬스장 2) x 소모배수 -> round. 멘탈은 헬스장과 무관
@pytest.mark.parametrize("gym, caffeine, policy, d_health, d_mental", [
    (0, False, BAL, -5, -8), (1, False, BAL, -3, -8), (1, True, BAL, -1, -8),
    (1, False, SF, round(-3 * 1.6), round(-8 * 1.6)),   # -4.8 -> -5, -12.8 -> -13
    (1, True, SF, round(-1 * 1.6), -13),                # -1.6 -> -2
    (1, False, RF, round(-3 * 0.7), round(-8 * 0.7)),   # -2.1 -> -2, -5.6 -> -6
    (1, True, RF, round(-1 * 0.7), -6),                 # -0.7 -> -1
])
def test_gym_study_health_cost(gym, caffeine, policy, d_health, d_mental):
    s = Student(levels(gym=gym))
    if caffeine:
        s.add_trait(config.TRAIT_CAFFEINE)
    s.health = s.mental = 50
    p = config.POLICIES[policy]
    s.study(p[config.POLICY_KNOWLEDGE_RATIO], p[config.POLICY_COST_RATIO])
    assert (s.health - 50, s.mental - 50) == (d_health, d_mental)


@pytest.mark.parametrize("lv", range(6))
def test_health_care_decay_amounts(lv):
    s = Student(levels(care=lv))
    ratio = 1 - 0.1 * lv
    assert s.get_health_decay() == pytest.approx(1 * ratio)
    assert s.get_mental_decay() == pytest.approx(1 * ratio)
    s.elapsed = 50.0
    assert s.get_mental_decay() == pytest.approx(2 * ratio)


def test_health_care_zero_level_keeps_integers():
    s = Student()
    s.update(5.0)
    assert s.health == 75 and type(s.health) is int and type(s.mental) is int


@pytest.mark.parametrize("lv, seconds", [(1, 10), (3, 7), (5, 13)])
def test_health_care_fractional_decay_accumulates(lv, seconds):
    s = Student(levels(care=lv))
    for _ in range(seconds * 60):
        s.update(FRAME)
    expected = 80 - seconds * (1 - 0.1 * lv)
    assert s.health == pytest.approx(expected, abs=1e-6)
    assert s.mental == pytest.approx(expected, abs=1e-6)
    # 6자리 반올림이라 오차가 쌓이지 않는다
    assert s.health == round(s.health, config.GAUGE_DECIMALS)


def test_health_care_exam_mental_fractional():
    s = Student(levels(care=1))
    s.elapsed = 45.0
    s.decay_timer = 0.0
    s.update(1.0)
    assert s.mental == pytest.approx(80 - 1.8)
    assert s.health == pytest.approx(80 - 0.9)


@pytest.mark.parametrize("start, lv, dropped", [
    (0.9, 1, True),    # 0.9 - 0.9 = 0 -> 0 이하 휴학
    (0.5, 5, True),
    (1.0, 1, False),   # 0.1 남음 -> 아직 휴학 아님
    (0.4, 5, True),    # 음수는 0으로
])
def test_fractional_dropout_at_zero_or_below(start, lv, dropped):
    s = Student(levels(care=lv))
    s.health = start
    s.update(1.0)
    assert s.is_dropped_out() is dropped
    assert s.health >= 0
    assert (s.get_ending() == config.ENDING_LEAVE) is dropped


def test_fractional_leave_through_game(g):
    g.upgrades[CARE] = 1
    g.student.health = 1.8
    g.update(1.0)
    assert g.state == config.STATE_PLAYING and g.student.health == pytest.approx(0.9)
    g.update(1.0)
    assert g.ending == config.ENDING_LEAVE


def test_fractional_popups_show_integers(g):
    g.upgrades[CARE] = 1
    g.update(1.0)          # 체력 79.1
    g.student.health = 90.6
    g.do_action(FEED)      # 100 까지 -> 실제 변화 9.4 -> 표시 +9
    texts = [p["text"] for p in g.popups]
    assert any(t.startswith(config.HEALTH_LABEL) for t in texts)
    assert all("." not in t for t in texts), texts


# ======================= 자동 행동 간격 (시간 관리) / 이벤트 확률 (행운 부적) =======================

@pytest.mark.parametrize("lv, interval", [(0, 2.0), (1, 1.8), (2, 1.6), (3, 1.4), (4, 1.2),
                                          (5, 1.0)])
def test_time_management_interval(no_events, lv, interval):
    game = Game()
    game.upgrades[TIME] = lv
    assert game.get_auto_interval() == pytest.approx(interval)
    game.start_new_game()
    assert game.auto_timer == pytest.approx(interval)   # 새 판 첫 행동도 새 간격
    log = []
    real = game.do_action
    game.do_action = lambda name: (log.append(round(game.student.elapsed, 4)), real(name))[1]
    for _ in range(int(round(6.0 * 60))):
        game.update(FRAME)
    expected = [pytest.approx(interval * (i + 1), abs=1e-3)
                for i in range(int(6.0 / interval + 1e-9))]
    assert log == expected
    pygame.quit()


@pytest.mark.parametrize("timer_before, timer_after", [(1.95, 1.8), (0.5, 0.5), (1.8, 1.8)])
def test_time_management_purchase_clamps_timer(no_events, timer_before, timer_after):
    game = Game()          # 자동 행동을 켠 상태(간격 2.0)여야 한다
    game.start_new_game()
    game.money = 10_000
    game.auto_timer = timer_before
    assert game.buy_upgrade(TIME)
    assert game.auto_timer == pytest.approx(timer_after)
    assert 0 <= game.get_auto_progress() <= 1
    pygame.quit()


def test_other_purchase_does_not_change_timer(g):
    g.money = 10_000
    g.auto_timer = 1.5
    g.buy_upgrade(MENU)
    assert g.auto_timer == 1.5


@pytest.mark.parametrize("lv, chance", [(0, 0.25), (1, 0.30), (2, 0.35), (3, 0.40)])
def test_lucky_charm_chance(lv, chance):
    game = Game()
    game.upgrades[CHARM] = lv
    assert game.get_event_chance() == pytest.approx(chance)
    pygame.quit()


class FixedRng:
    """random() 은 항상 value, choice 는 첫 항목."""

    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value

    def choice(self, seq):
        return seq[0]


@pytest.mark.parametrize("lv, roll, fires", [
    (0, 0.27, False), (1, 0.27, True), (1, 0.31, False), (3, 0.39, True), (3, 0.41, False),
    (0, 0.24, True),
])
def test_lucky_charm_changes_roll(no_auto, lv, roll, fires):
    game = Game()
    game.start_new_game()
    game.upgrades[CHARM] = lv
    game.student.elapsed = 2.0      # 보장 구간 전, 직전 이벤트 없음
    assert not game.student.needs_guaranteed_event()
    game.rng = FixedRng(roll)
    assert (game.roll_event() is not None) is fires
    pygame.quit()


# ======================= 장학금 제도 =======================

def test_scholarship_candidate_only_when_owned(g):
    g.student.elapsed = 70.0
    _, autos = g.get_event_candidates()
    assert config.SCHOLARSHIP_EVENT not in autos
    g.upgrades[SCHOL] = 1
    _, autos = g.get_event_candidates()
    assert config.SCHOLARSHIP_EVENT in autos


@pytest.mark.parametrize("elapsed, grade", [(1.0, 1), (70.0, 2), (130.0, 3), (190.0, 4)])
@pytest.mark.parametrize("fame", [0, 3])
def test_scholarship_money_per_grade(g, elapsed, grade, fame):
    g.upgrades[SCHOL] = 1
    g.fame = fame
    g.student.elapsed = elapsed
    g.money = 7
    before = (g.student.health, g.student.mental, g.student.knowledge)
    g.start_event(config.SCHOLARSHIP_EVENT)
    assert g.money == 7 + 30 * grade      # 명성 배수 없음(팀장 승인)
    assert (g.student.health, g.student.mental, g.student.knowledge) == before
    assert g.notice is not None and "장학금을 받았다" in g.notice["text"]
    assert g.student.get_grade_event_count() == 1


def test_scholarship_can_actually_appear(no_auto):
    """장학금을 사면 실제 roll 에서 장학금이 뽑힐 수 있다(자동형 후보 맨 끝)."""
    game = Game()
    game.start_new_game()
    game.upgrades[SCHOL] = 1

    class LastRng(FixedRng):
        def choice(self, seq):
            return seq[-1]
    game.rng = LastRng(0.9)        # 선택지형 대신 자동형, 자동형 중 마지막
    game.student.elapsed = 12.0    # 보장 이벤트
    event = game.roll_event()
    assert event is config.SCHOLARSHIP_EVENT
    assert game.money == 30
    pygame.quit()


# ======================= 업그레이드 가격·구매 =======================

@pytest.mark.parametrize("uid", list(SPEC_TABLE))
def test_cost_every_level_and_max(g, uid):
    max_level, base = SPEC_TABLE[uid]
    g.money = 1_000_000
    for level in range(max_level):
        assert g.upgrades[uid] == level
        cost = spec_cost(base, level)
        assert g.get_upgrade_cost(uid) == cost, (uid, level)
        assert g.can_buy_upgrade(uid)
        money = g.money
        assert g.buy_upgrade(uid) is True
        assert g.money == money - cost
    assert g.upgrades[uid] == max_level
    assert g.is_upgrade_maxed(uid)
    assert not g.can_buy_upgrade(uid)
    money = g.money
    assert g.buy_upgrade(uid) is False
    assert (g.money, g.upgrades[uid]) == (money, max_level)


def test_known_cost_values(g):
    expect = {MENU: [80, 128, 204, 327, 524], BOOK: [120, 192, 307, 491, 786],
              TIME: [150, 240, 384, 614, 983], CHARM: [200, 320, 512]}
    for uid, costs in expect.items():
        for level, cost in enumerate(costs):
            g.upgrades[uid] = level
            assert g.get_upgrade_cost(uid) == cost, (uid, level)


@pytest.mark.parametrize("uid", list(SPEC_TABLE))
def test_cannot_buy_when_short(g, uid):
    cost = spec_cost(SPEC_TABLE[uid][1], 0)
    g.money = cost - 1
    assert not g.can_buy_upgrade(uid)
    assert g.buy_upgrade(uid) is False
    assert g.money == cost - 1 and g.upgrades[uid] == 0
    g.money = cost
    assert g.buy_upgrade(uid) is True
    assert g.money == 0 and g.upgrades[uid] == 1


def test_unknown_upgrade_cannot_be_bought(g):
    g.money = 10_000
    assert g.can_buy_upgrade("rocket") is False
    assert g.buy_upgrade("rocket") is False
    assert g.money == 10_000


def test_purchase_applies_immediately_to_current_student(g):
    assert g.student.upgrades is g.upgrades
    g.money = 10_000
    g.buy_upgrade(MENU)
    g.student.health = 10
    g.do_action(FEED)
    assert g.student.health == 34


def test_purchase_saves_immediately(g, isolated_record_path):
    g.money = 500
    assert g.buy_upgrade(BED)
    data = read_record(isolated_record_path)
    assert set(data) == RECORD_KEYS
    assert data["money"] == 420
    assert data["upgrades"][BED] == 1
    assert data["upgrades"] == g.upgrades


def test_failed_purchase_does_not_write(g, isolated_record_path):
    g.money = 0
    assert not g.buy_upgrade(BED)
    assert not os.path.exists(isolated_record_path)


# ======================= 연구비 =======================

@pytest.mark.parametrize("fame, policy, exam, expected", [
    (0, BAL, False, 10), (1, BAL, False, 11), (3, BAL, False, 13),
    (0, SF, False, 14), (1, SF, False, 15),   # 14 x 1.1 = 15.4 -> 15
    (3, SF, False, 18),                       # 14 x 1.3 = 18.2 -> 18
    (1, BAL, True, 22), (3, SF, True, 36),    # 28 x 1.3 = 36.4 -> 36
    (3, RF, False, 10),                       # 8 x 1.3 = 10.4 -> 10
])
def test_money_from_study(g, fame, policy, exam, expected):
    g.fame = fame
    g.set_policy(policy)
    if exam:
        g.student.elapsed = 50.0
    g.do_action(STUDY)
    assert g.money == expected


@pytest.mark.parametrize("fame, expected", [(0, 1.0), (1, 1.1), (3, 1.3), (10, 2.0)])
def test_money_multiplier(g, fame, expected):
    g.fame = fame
    assert g.get_money_multiplier() == pytest.approx(expected)


def test_money_not_reduced_by_rest_or_feed(g):
    g.student.knowledge = 30
    g.money = 50
    g.do_action(REST)          # 지식 -2
    assert g.student.knowledge == 28 and g.money == 50
    g.do_action(FEED)
    assert g.money == 50
    g.student.knowledge = 0
    g.do_action(REST)          # 0 아래로 안 내려감
    assert g.money == 50


def test_money_from_auto_event_with_fame(g):
    knowledge_event = next(e for e in config.AUTO_EVENTS
                           if e[config.EVENT_EFFECTS].get(config.GAUGE_KNOWLEDGE, 0) > 0)
    gain = knowledge_event[config.EVENT_EFFECTS][config.GAUGE_KNOWLEDGE]
    g.fame = 3
    g.start_event(knowledge_event)
    assert g.money == int(gain * 1.3 + 1e-9)


def test_money_not_from_negative_auto_event(g):
    bad = next(e for e in config.AUTO_EVENTS
               if sum(e[config.EVENT_EFFECTS].values()) < 0)
    g.money = 5
    g.start_event(bad)
    assert g.money == 5


def test_money_from_choice_option(g):
    mt = next(e for e in config.CHOICE_EVENTS if e[config.EVENT_ID] == "mt_invite")
    g.fame = 3
    g.start_event(mt)
    assert g.state == config.STATE_EVENT
    g.dialog_time = 1.0
    assert g.choose_option(1)                   # 지식 +10
    assert g.money == 13
    g.start_event(mt)
    g.dialog_time = 1.0
    g.choose_option(0)                          # 지식 변화 없음
    assert g.money == 13


def test_money_through_auto_loop_equals_knowledge_gains(no_events):
    """자동 행동만으로 30초: 연구비 = 지식이 오른 양의 합(명성 0)."""
    game = Game()
    game.start_new_game()
    gains = []
    real = game.do_action

    def spy(name):
        before = game.student.knowledge
        result = real(name)
        gains.append(max(0, game.student.knowledge - before))
        return result
    game.do_action = spy
    for _ in range(30 * 60):
        game.update(FRAME)
    assert sum(gains) > 0
    assert game.money == sum(gains)
    assert game.money >= game.student.knowledge
    pygame.quit()


def test_money_not_lost_on_leave(g):
    g.do_action(STUDY)
    g.do_action(STUDY)
    assert g.money == 20
    leave_with(g, g.student.knowledge)
    assert g.money == 20 and g.graduation_bonus == 0


# ======================= 졸업 보너스 =======================

@pytest.mark.parametrize("knowledge, ending, bonus", [
    (0, config.ENDING_BARELY, 50), (449, config.ENDING_BARELY, 50),
    (450, config.ENDING_NORMAL, 100), (699, config.ENDING_NORMAL, 100),
    (700, config.ENDING_TOP, 200), (1500, config.ENDING_TOP, 200),
])
@pytest.mark.parametrize("fame", [0, 1, 3])
def test_graduation_bonus(g, knowledge, ending, bonus, fame):
    g.fame = fame
    g.money = 10
    graduate_with(g, knowledge)
    assert g.ending == ending
    expected = int(bonus * (1 + 0.1 * fame) + 1e-9)
    assert g.graduation_bonus == expected
    assert g.money == 10 + expected


def test_graduation_bonus_shown_on_ending(g):
    graduate_with(g, 450)
    texts = []
    real = game_module.render_text

    def rec(font, text, *a, **k):
        texts.append(text)
        return real(font, text, *a, **k)
    game_module.render_text = rec
    try:
        g.draw()
    finally:
        game_module.render_text = real
    assert config.GRADUATION_BONUS_TEXT.format(100) in texts


def test_new_round_resets_graduation_bonus(g):
    graduate_with(g, 700)
    assert g.graduation_bonus == 200
    press(g, pygame.K_r)
    assert g.state == config.STATE_PLAYING
    assert g.graduation_bonus == 0
    assert g.money == 200     # 연구비는 유지


# ======================= record.json 저장·불러오기 =======================

@pytest.mark.parametrize("finish", ["leave", "graduate"])
def test_round_end_saves_four_keys(g, isolated_record_path, finish):
    g.money = 33
    g.fame = 2
    g.upgrades[BED] = 3
    if finish == "leave":
        leave_with(g, 40)
        money = 33
    else:
        graduate_with(g, 40)
        money = 33 + 60
    data = read_record(isolated_record_path)
    assert data == {"best_knowledge": 40, "money": money, "fame": 2,
                    "upgrades": {**levels(), BED: 3}}
    assert all(type(v) is int for v in (data["best_knowledge"], data["money"], data["fame"]))


def test_round_end_with_zero_knowledge_still_saves(g, isolated_record_path):
    leave_with(g, 0)
    assert read_record(isolated_record_path)["best_knowledge"] == 0


def test_best_knowledge_only_increases(g, isolated_record_path):
    for k, best in [(300, 300), (100, 300), (300, 300), (301, 301), (0, 301)]:
        graduate_with(g, k)
        data = read_record(isolated_record_path)
        assert data["best_knowledge"] == best == g.best_record
        assert data["money"] == g.money
        press(g, pygame.K_r)


def test_persistence_across_game_instances(g, isolated_record_path):
    g.money = 1000
    g.buy_upgrade(MENU)
    g.buy_upgrade(LIB)
    g.fame = 2   # (I단위에서 환생으로 오른다) 판 끝에 함께 저장
    graduate_with(g, 450)
    money = g.money
    pygame.quit()
    g2 = Game()
    assert (g2.best_record, g2.money, g2.fame) == (450, money, 2)
    assert g2.upgrades == {**levels(), MENU: 1, LIB: 1}
    g2.start_new_game()
    assert g2.student.upgrades is g2.upgrades
    g2.student.health = 10
    g2.do_action(FEED)
    assert g2.student.health == 34
    pygame.quit()


def test_persistence_across_rounds_in_same_game(g):
    g.money = 1000
    g.buy_upgrade(BOOK)
    leave_with(g, 10)
    press(g, pygame.K_r)
    assert g.upgrades[BOOK] == 1 and g.student.upgrades is g.upgrades
    g.do_action(STUDY)
    assert g.student.knowledge == 12
    assert g.money == 1000 - 120 + 12


def test_title_shows_fame_and_money(isolated_record_path):
    write_raw(isolated_record_path, json.dumps(
        {"best_knowledge": 5, "money": 340, "fame": 2, "upgrades": {}}))
    game = Game()
    texts = []
    real = game_module.render_text

    def rec(font, text, *a, **k):
        texts.append(text)
        return real(font, text, *a, **k)
    game_module.render_text = rec
    try:
        game.draw()
    finally:
        game_module.render_text = real
    assert config.TITLE_WALLET_TEXT.format(2, 340) in texts
    assert "최고 기록: 지식 5" in texts
    pygame.quit()


def test_old_format_file(isolated_record_path):
    write_raw(isolated_record_path, '{"best_knowledge": 300}')
    game = Game()
    assert (game.best_record, game.money, game.fame) == (300, 0, 0)
    assert game.upgrades == levels()
    game.start_new_game()
    graduate_with(game, 100)
    data = read_record(isolated_record_path)
    assert set(data) == RECORD_KEYS and data["best_knowledge"] == 300
    pygame.quit()


@pytest.mark.parametrize("content", ["", "{", "[1]", "null", "500", '"x"', "{}",
                                     '{"money": 5, "fame": 1'])
def test_broken_or_missing_file_is_zeros(isolated_record_path, content):
    write_raw(isolated_record_path, content)
    game = Game()
    assert (game.best_record, game.money, game.fame) == (0, 0, 0)
    assert game.upgrades == levels()
    pygame.quit()


def test_missing_file_is_zeros_and_not_created(isolated_record_path):
    game = Game()
    assert (game.best_record, game.money, game.fame, game.upgrades) == (0, 0, 0, levels())
    assert not os.path.exists(isolated_record_path)
    pygame.quit()


def test_invalid_fields_become_zero(isolated_record_path):
    write_raw(isolated_record_path, json.dumps({
        "best_knowledge": 10, "money": "100", "fame": -1,
        "upgrades": {"menu": 9, "bed": 2, "cafe": True, "gym": 1.0, "library": -1,
                     "lucky_charm": 3, "scholarship": 2, "rocket": 3, "time_management": None},
    }))
    game = Game()
    assert (game.best_record, game.money, game.fame) == (10, 0, 0)
    assert game.upgrades == {**levels(), BED: 2, CHARM: 3}
    assert "rocket" not in game.upgrades
    pygame.quit()


@pytest.mark.parametrize("value", [1.5, True, None, [3], {"a": 1}, -3])
def test_invalid_money_and_fame_values(isolated_record_path, value):
    write_raw(isolated_record_path, json.dumps({"best_knowledge": 1, "money": value,
                                                "fame": value, "upgrades": []}))
    game = Game()
    assert (game.best_record, game.money, game.fame) == (1, 0, 0)
    assert game.upgrades == levels()
    pygame.quit()


def test_load_save_best_record_wrappers(g, isolated_record_path):
    g.best_record = 9
    g.money = 4
    assert g.save_best_record() is True
    assert read_record(isolated_record_path)["money"] == 4
    assert g.load_best_record() == 9


def test_save_failure_returns_false(tmp_path, no_events, no_auto):
    game = Game(record_path=str(tmp_path))      # 폴더 -> 쓰기 실패
    game.start_new_game()
    game.money = 1000
    assert game.buy_upgrade(MENU) is True       # 저장 실패해도 산 것은 적용
    assert game.upgrades[MENU] == 1
    assert game.save_record() is False
    graduate_with(game, 10)
    pygame.quit()


# ======================= 업그레이드 패널 입력 =======================

def test_panel_not_on_title(isolated_record_path):
    game = Game()
    press(game, pygame.K_u)
    assert not game.upgrade_panel_open
    click(game, game.upgrade_button.rect.center)
    assert not game.upgrade_panel_open and game.state == config.STATE_TITLE
    pygame.quit()


def test_panel_toggle_key_and_button_in_playing(g):
    press(g, pygame.K_u)
    assert g.upgrade_panel_open
    press(g, pygame.K_u)
    assert not g.upgrade_panel_open
    click(g, g.upgrade_button.rect.center)
    assert g.upgrade_panel_open
    click(g, g.upgrade_button.rect.center)
    assert not g.upgrade_panel_open


def test_panel_toggle_on_ending_with_button(g):
    graduate_with(g, 100)
    press(g, pygame.K_u)
    assert g.upgrade_panel_open
    click(g, g.ending_upgrade_button.rect.center)
    assert not g.upgrade_panel_open
    click(g, g.ending_upgrade_button.rect.center)
    assert g.upgrade_panel_open


def test_panel_not_toggled_during_event_dialog_and_hidden(g, monkeypatch):
    press(g, pygame.K_u)
    assert g.upgrade_panel_open
    mt = next(e for e in config.CHOICE_EVENTS if e[config.EVENT_ID] == "mt_invite")
    g.start_event(mt)
    assert g.state == config.STATE_EVENT
    press(g, pygame.K_u)
    assert g.upgrade_panel_open      # 대화창 중 U 무시(상태 그대로)
    g.money = 10_000
    press(g, pygame.K_RETURN)        # 대화창 중 Enter 로 사지 않는다
    assert g.upgrades == levels()
    calls = []
    monkeypatch.setattr(g, "draw_upgrade_panel", lambda: calls.append(1))
    g.draw()
    assert calls == []               # 대화창이 떠 있으면 패널을 그리지 않는다
    g.dialog_time = 1.0
    press(g, pygame.K_1)             # 1 = 선택지 1 (방침 아님)
    assert g.state == config.STATE_PLAYING and g.policy == BAL
    g.draw()
    assert calls == [1]              # 대화창이 닫히면 다시 보인다


def test_panel_closed_during_dialog_cannot_open(g):
    mt = next(e for e in config.CHOICE_EVENTS if e[config.EVENT_ID] == "mt_invite")
    g.start_event(mt)
    press(g, pygame.K_u)
    click(g, g.upgrade_button.rect.center)
    assert not g.upgrade_panel_open


def test_game_keeps_running_with_panel_open(no_events):
    game = Game()
    press(game, pygame.K_RETURN)
    press(game, pygame.K_u)
    assert game.upgrade_panel_open
    for _ in range(5 * 60):
        game.update(FRAME)
    assert game.student.elapsed == pytest.approx(5.0)
    assert game.last_action is not None        # 자동 행동도 계속
    assert game.student.health < 80 or game.student.knowledge > 0
    pygame.quit()


def test_policy_keys_and_buttons_work_with_panel_open(g):
    press(g, pygame.K_u)
    press(g, pygame.K_1)
    assert g.policy == SF
    press(g, pygame.K_3)
    assert g.policy == RF
    click(g, g.buttons[BAL].rect.center)
    assert g.policy == BAL
    assert g.upgrade_panel_open


def test_cursor_wraps(g):
    press(g, pygame.K_u)
    assert g.upgrade_cursor == 0
    press(g, pygame.K_UP)
    assert g.upgrade_cursor == len(config.UPGRADE_IDS) - 1
    press(g, pygame.K_DOWN)
    assert g.upgrade_cursor == 0
    for i in range(1, 12):
        press(g, pygame.K_DOWN)
        assert g.upgrade_cursor == i % 10


def test_arrows_ignored_when_panel_closed(g):
    press(g, pygame.K_DOWN)
    assert g.upgrade_cursor == 0


@pytest.mark.parametrize("key", [pygame.K_RETURN, pygame.K_KP_ENTER])
def test_enter_buys_cursor_item(g, key):
    g.money = 1000
    press(g, pygame.K_u)
    press(g, pygame.K_DOWN)
    press(g, pygame.K_DOWN)                     # reference_book
    press(g, key)
    assert g.upgrades[BOOK] == 1 and g.money == 880
    g.money = 10
    press(g, key)                               # 모자라면 그대로
    assert g.upgrades[BOOK] == 1 and g.money == 10


def test_enter_does_nothing_when_panel_closed(g):
    g.money = 1000
    press(g, pygame.K_RETURN)
    assert g.upgrades == levels() and g.money == 1000


@pytest.mark.parametrize("index", range(10))
def test_click_row_buys_that_item(g, index):
    g.money = 10_000
    press(g, pygame.K_u)
    uid = config.UPGRADE_IDS[index]
    click(g, g.get_upgrade_row_rect(index).center)
    assert g.upgrade_cursor == index
    assert g.upgrades[uid] == 1
    assert g.money == 10_000 - SPEC_TABLE[uid][1]


def test_click_row_when_closed_does_nothing(g):
    g.money = 10_000
    click(g, g.get_upgrade_row_rect(0).center)
    assert g.upgrades == levels()


def test_buy_on_ending_screen(g):
    graduate_with(g, 700)                       # 보너스 200
    press(g, pygame.K_u)
    press(g, pygame.K_RETURN)                   # menu 80
    assert g.upgrades[MENU] == 1 and g.money == 120


def test_r_restarts_with_panel_open_on_ending(g):
    graduate_with(g, 100)
    press(g, pygame.K_u)
    press(g, pygame.K_r)
    assert g.state == config.STATE_PLAYING and g.ending is None


def test_esc_quits_with_panel_open(g):
    press(g, pygame.K_u)
    press(g, pygame.K_ESCAPE)
    assert g.running is False


def test_esc_quits_with_panel_open_on_ending(g):
    graduate_with(g, 100)
    press(g, pygame.K_u)
    press(g, pygame.K_ESCAPE)
    assert g.running is False


# ======================= 패널 그리기 =======================

class RecSurface(pygame.Surface):
    """blit 을 (원본 Surface, 놓인 Rect) 로 기록하는 화면 Surface."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blits_log = []

    def blit(self, source, dest, *args, **kwargs):
        rect = super().blit(source, dest, *args, **kwargs)
        if isinstance(dest, pygame.Rect):
            placed = pygame.Rect(dest.topleft, source.get_size())
        else:
            placed = pygame.Rect(dest, source.get_size())
        self.blits_log.append((source, placed))
        return rect


def draw_and_collect(game, method, monkeypatch):
    """game.method() 를 그리며 render_text 로 만든 글자의 (글자, 놓인 Rect) 목록을 돌려준다."""
    screen = RecSurface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    game.screen = screen
    made = {}
    real = game_module.render_text

    def rec(font, text, *a, **k):
        surf = real(font, text, *a, **k)
        made[id(surf)] = (text, surf)
        return surf
    monkeypatch.setattr(game_module, "render_text", rec)
    getattr(game, method)()
    out = []
    for surf, rect in screen.blits_log:
        if id(surf) in made and made[id(surf)][1] is surf:
            out.append((made[id(surf)][0], rect))
    return out


@pytest.mark.parametrize("setup", ["zero", "mid", "max", "rich"])
def test_panel_texts_fit_inside_rows(g, monkeypatch, setup):
    if setup == "mid":
        for uid in config.UPGRADE_IDS:
            g.upgrades[uid] = SPEC_TABLE[uid][0] - 1
        g.money = 300
    elif setup == "max":
        for uid in config.UPGRADE_IDS:
            g.upgrades[uid] = SPEC_TABLE[uid][0]
    elif setup == "rich":
        g.money = 9_999_999
    g.upgrade_panel_open = True
    texts = draw_and_collect(g, "draw_upgrade_panel", monkeypatch)
    panel = pygame.Rect(config.UPGRADE_PANEL_RECT)
    for text, rect in texts:
        assert panel.contains(rect), (text, rect)
    for index, uid in enumerate(config.UPGRADE_IDS):
        row = g.get_upgrade_row_rect(index)
        inner = row.inflate(-config.BOX_INSET, -config.BOX_INSET)
        name = config.UPGRADES_BY_ID[uid][config.UPGRADE_NAME]
        in_row = [(t, r) for t, r in texts if inner.colliderect(r)]
        assert any(t == name for t, _ in in_row)
        for t, r in in_row:
            assert inner.contains(r), (uid, t, r, inner)
        # 같은 줄 글자끼리 겹치지 않는다(이름 / 레벨 / 가격)
        # (J단위 재배치) 효과 설명은 줄 안에서 빠지고 패널 바닥 줄("효과: …")로 옮겨졌다
        rects = sorted((r for _, r in in_row), key=lambda r: r.left)
        assert len(rects) == 3
        for a, b in zip(rects, rects[1:]):
            assert a.right <= b.left, (uid, a, b)
    # 머리 줄 글자(제목·연구비)도 서로 겹치지 않는다 (J단위: 안내 문구는 빠짐)
    header = sorted((r for t, r in texts if r.bottom <= config.UPGRADE_ROW_TOP), key=lambda r: r.left)
    assert len(header) == 2
    for a, b in zip(header, header[1:]):
        assert a.right <= b.left
    # (J단위) 바닥 줄: 고른 줄 항목의 효과 설명 하나가 마지막 줄 아래, 패널 안에 있다
    last_row = g.get_upgrade_row_rect(len(config.UPGRADE_IDS) - 1)
    footer = [(t, r) for t, r in texts if r.top >= last_row.bottom]
    chosen = config.UPGRADES_BY_ID[config.UPGRADE_IDS[g.upgrade_cursor]]
    assert [t for t, _ in footer] == [
        config.UPGRADE_FOOTER_TEXT.format(chosen[config.UPGRADE_EFFECT_TEXT])]
    assert panel.contains(footer[0][1])


def test_panel_row_texts_show_level_cost_and_max(g, monkeypatch):
    g.upgrades[MENU] = 2
    g.upgrades[LIB] = 1
    g.upgrade_panel_open = True
    texts = [t for t, _ in draw_and_collect(g, "draw_upgrade_panel", monkeypatch)]
    # (J단위 재배치) 좁은 왼쪽 패널이라 가격은 숫자만("204") 쓴다. 단위는 머리 줄 "연구비 N"
    assert "Lv 2/5" in texts and "204" in texts
    assert "Lv 1/1" in texts and "MAX" in texts
    assert config.MONEY_TEXT.format("연구비", 0) in texts


def test_panel_rows_inside_panel_and_not_over_buttons(g):
    panel = pygame.Rect(config.UPGRADE_PANEL_RECT)
    for i in range(10):
        assert panel.contains(g.get_upgrade_row_rect(i))
    for i in range(9):
        assert g.get_upgrade_row_rect(i).bottom <= g.get_upgrade_row_rect(i + 1).top
    assert panel.top >= config.INFO_BAR_HEIGHT
    for b in list(g.buttons.values()) + [g.upgrade_button, g.ending_upgrade_button]:
        assert not panel.colliderect(b.rect), b.text
    assert not g.upgrade_button.rect.colliderect(list(g.buttons.values())[-1].rect)
    assert pygame.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT).contains(
        g.ending_upgrade_button.rect)


@pytest.mark.parametrize("state", [config.STATE_PLAYING, config.STATE_ENDING])
def test_panel_is_opaque(g, state):
    """배경을 두 색으로 바꿔 그려도 패널 안쪽 픽셀이 똑같다 = 반투명 없음."""
    if state == config.STATE_ENDING:
        graduate_with(g, 100)
    g.upgrade_panel_open = True
    inner = pygame.Rect(config.UPGRADE_PANEL_RECT).inflate(-16, -16)
    shots = []
    for fill in ((255, 0, 255), (0, 255, 0)):
        g.screen.fill(fill)
        g.draw_upgrade_panel()
        shots.append(pygame.image.tobytes(g.screen.subsurface(inner), "RGB"))
    assert shots[0] == shots[1]


def test_panel_code_uses_no_alpha():
    tree = ast.parse((ROOT / "game.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and "upgrade" in node.name:
            src = ast.unparse(node)
            for bad in ("alpha", "SRCALPHA", "BLEND"):
                assert bad not in src, (node.name, bad)


def test_full_draw_with_panel_in_each_state(g):
    g.upgrade_panel_open = True
    g.draw()
    graduate_with(g, 500)
    g.draw()
    leave_g = g
    press(leave_g, pygame.K_r)
    leave_with(leave_g, 0)
    leave_g.draw()


def test_info_bar_money_text_fits(g, monkeypatch):
    g.money = 9_999_999
    g.student.knowledge = 9999
    texts = draw_and_collect(g, "draw_info_bar", monkeypatch)
    by_text = {t: r for t, r in texts}
    money_rect = by_text[config.MONEY_TEXT.format("연구비", 9_999_999)]
    time_rect = next(r for t, r in texts if t.startswith("남은 시간"))
    knowledge_rect = by_text["지식 9999"]
    box = pygame.Rect(config.INFO_BOX_X, config.INFO_BOX_Y, config.INFO_BOX_WIDTH,
                      config.INFO_BOX_HEIGHT)
    assert box.contains(money_rect)
    assert time_rect.right <= money_rect.left
    assert money_rect.right <= knowledge_rect.left


def test_upgrade_button_selected_when_open(g, monkeypatch):
    seen = []
    real = g.upgrade_button.draw

    def spy(*a, **k):
        seen.append(k.get("selected"))
        return real(*a, **k)
    monkeypatch.setattr(g.upgrade_button, "draw", spy)
    g.draw()
    press(g, pygame.K_u)
    g.draw()
    assert seen == [False, True]


# ======================= 정적 검사 =======================

def test_student_shares_game_upgrades_dict(g):
    assert g.student.upgrades is g.upgrades
    press(g, pygame.K_ESCAPE)


def test_new_names_have_docstrings():
    for name in ("game.py", "student.py"):
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                assert ast.get_docstring(node), (name, node.name)


def test_random_only_via_game_rng():
    src = (ROOT / "game.py").read_text(encoding="utf-8")
    assert src.count("random.Random(") == 1
    assert "random.random(" not in src and "random.choice(" not in src
