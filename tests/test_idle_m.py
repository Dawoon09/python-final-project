"""M단위 검수: 회복은 휴식에서만·든든함·새 자동 행동 규칙·최댓값·디버프·방침 수치·업그레이드 13종·진급 기준 2배.

기준: docs/기획서.md 2·3·6절, jeja-spec 2·3·6절 (M단위 반영).
- 졸업 등급 시간 기준은 B안(2026-11-24)으로 330/720초로 확정했다. 경계는 config 상수로 잡는다.
- 밸런스 분포는 고정하지 않는다(불변식만).

이 파일은 conftest 의 AUTO_OFF_FILES / EVENTS_OFF_FILES 에 없다. 필요한 테스트만 no_auto / no_events 를 쓴다.
"""

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
import game as game_module  # noqa: E402
import student as student_module  # noqa: E402
from conftest import press, reach_grade  # noqa: E402
from game import Game  # noqa: E402
from student import Student, judge_ending  # noqa: E402

FEED, REST, STUDY = config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY
SF, BAL, RF = config.POLICY_STUDY_FOCUS, config.POLICY_BALANCED, config.POLICY_REST_FOCUS
HMAX, MMAX, SELF = config.UPGRADE_HEALTH_MAX, config.UPGRADE_MENTAL_MAX, config.UPGRADE_SELF_CARE
NEW_IDS = (HMAX, MMAX, SELF)
OLD_IDS = ["menu", "bed", "reference_book", "time_management", "health_care", "library", "cafe",
           "gym", "lucky_charm", "scholarship"]
GOAL = config.GRADUATION_KNOWLEDGE
P = config.PIXEL_SIZE


def levels(**kw):
    """모든 업그레이드 0레벨 사전에 kw(id=레벨)를 덮어쓴 사전."""
    d = {uid: 0 for uid in config.UPGRADE_IDS}
    d.update(kw)
    return d


def student(health=80, mental=80, knowledge=0, elapsed=0.0, **upgrade_levels):
    s = Student(levels(**upgrade_levels))
    s.health, s.mental, s.knowledge, s.elapsed = health, mental, knowledge, elapsed
    return s


@pytest.fixture
def g(no_events, no_auto):
    """이벤트·자동 행동을 끈 채 게임 중인 Game(행동은 테스트가 직접)."""
    game = Game()
    press(game, pygame.K_RETURN)
    assert game.state == config.STATE_PLAYING
    yield game
    pygame.quit()


@pytest.fixture
def auto_g(no_events):
    """이벤트만 끄고 자동 행동은 켠 Game."""
    game = Game()
    press(game, pygame.K_RETURN)
    yield game
    pygame.quit()


def record_texts(monkeypatch, module, call):
    """module.render_text 로 만든 글자 목록을 모으며 call() 을 부른다."""
    made = []
    real = module.render_text

    def rec(font, text, *a, **k):
        made.append(text)
        return real(font, text, *a, **k)
    monkeypatch.setattr(module, "render_text", rec)
    call()
    monkeypatch.setattr(module, "render_text", real)
    return made


# ======================= 0. config 수치 =======================

def test_m_constants():
    assert not hasattr(config, "FEED_HEALTH")
    assert (config.REST_HEALTH, config.REST_MENTAL, config.REST_KNOWLEDGE) == (15, 20, -2)
    assert config.FULL_DURATION == 30 and config.FULL_HEALTH_DECAY_RATIO == 0.5
    assert config.BONUS_FULL_TIME == "full_time"
    assert config.TRAIT_BONUSES[config.TRAIT_FITNESS] == {config.BONUS_FULL_TIME: 10}
    assert config.TRAIT_BONUSES[config.TRAIT_LOVE] == {config.BONUS_REST_HEALTH: 5}
    assert config.TRAIT_BONUSES[config.TRAIT_MUSIC] == {config.BONUS_REST_MENTAL: 5}
    assert config.LOW_GAUGE_LIMIT == 30 and config.CONDITION_GOOD_MIN == 70
    assert config.TIRED_KNOWLEDGE_RATIO == 0.7 and config.DEPRESSED_MONEY_RATIO == 0.7
    assert (config.DEBUFF_TIRED, config.DEBUFF_DEPRESSED, config.BUFF_FULL, config.CONDITION_GOOD) \
        == ("피곤", "우울", "든든함", "컨디션 좋음")
    assert config.GAUGE_MAX == 100
    assert config.GRADE_GOALS == [400, 900, 1500] and config.GRADUATION_KNOWLEDGE == 2200
    assert (config.GRAD_GOAL_FIRST_STEP, config.GRAD_GOAL_STEP_GROWTH) == (800, 200)
    # 시간 기준은 B안으로 확정(예전 임시 400/720)
    assert (config.TOP_GRADUATE_SECONDS, config.NORMAL_GRADUATE_SECONDS) == (330, 720)
    assert 0 < config.TOP_GRADUATE_SECONDS < config.NORMAL_GRADUATE_SECONDS
    assert config.STATUS_BADGE_Y == 128 and config.GAUGE_VALUE_TEXT.format(80, 100) == "80/100"
    assert (config.UPGRADE_ROW_TOP, config.UPGRADE_ROW_HEIGHT, config.UPGRADE_ROW_STEP) == \
        (165, 19, 20)   # (연구비) 14줄 (M단위 166/20/21)


@pytest.mark.parametrize("policy, threshold, k_ratio, c_ratio, rest_ratio, bonus", [
    (SF, 25, 1.8, 1.8, 1.0, 0.0),     # B안 (M단위 20/1.6)
    (BAL, 50, 1.0, 1.0, 1.0, 0.0),
    (RF, 70, 0.7, 0.7, 1.5, 0.5),     # B안 (M단위 0.2)
])
def test_policy_table_m(policy, threshold, k_ratio, c_ratio, rest_ratio, bonus):
    p = config.POLICIES[policy]
    assert p[config.POLICY_THRESHOLD] == threshold
    assert p[config.POLICY_KNOWLEDGE_RATIO] == k_ratio
    assert p[config.POLICY_COST_RATIO] == c_ratio
    assert p[config.POLICY_REST_RATIO] == rest_ratio
    assert p[config.POLICY_CONDITION_BONUS] == bonus


def test_upgrade_table_13_kinds():
    assert config.UPGRADE_IDS == OLD_IDS + list(NEW_IDS) + [config.UPGRADE_RESEARCH]   # (연구비) 14번째
    table = {uid: (u[config.UPGRADE_MAX_LEVEL], u[config.UPGRADE_BASE_COST],
                   u[config.UPGRADE_PER_LEVEL], u[config.UPGRADE_CATEGORY])
             for uid, u in config.UPGRADES_BY_ID.items() if uid in NEW_IDS}
    assert table == {HMAX: (5, 300, 10, "컨디션"), MMAX: (5, 300, 10, "컨디션"),
                     SELF: (5, 400, 0.2, "컨디션")}
    assert config.UPGRADES_BY_ID["menu"][config.UPGRADE_PER_LEVEL] == 6
    assert config.UPGRADES_BY_ID["bed"][config.UPGRADE_PER_LEVEL] == 4


def test_upgrade_prices_and_total(g):
    costs = {}
    for uid in config.UPGRADE_IDS:
        out = []
        for level in range(config.UPGRADES_BY_ID[uid][config.UPGRADE_MAX_LEVEL]):
            g.upgrades[uid] = level
            out.append(g.get_upgrade_cost(uid))
        g.upgrades[uid] = 0
        costs[uid] = out
    assert costs[HMAX] == costs[MMAX] == [300, 600, 1200, 2400, 4800]
    assert costs[SELF] == [400, 800, 1600, 3200, 6400]
    assert sum(sum(costs[u]) for u in NEW_IDS) == 31000
    assert costs[config.UPGRADE_RESEARCH] == [500, 1000, 2000, 4000, 8000]
    assert sum(sum(c) for c in costs.values()) == 108090   # (연구비) 92,590 + 15,500


# ======================= 1. 회복은 휴식에서만 =======================

def test_feed_changes_no_gauge():
    s = student(health=50, mental=40, knowledge=30)
    s.feed()
    assert (s.health, s.mental, s.knowledge) == (50, 40, 30)
    assert s.is_full_buff_active()


@pytest.mark.parametrize("kw, traits, health, mental", [
    ({}, (), 15, 20),
    ({"bed": 1}, (), 19, 24),
    ({"bed": 5}, (), 35, 40),
    ({"cafe": 1}, (), 20, 20),
    ({}, (config.TRAIT_LOVE,), 20, 20),
    ({}, (config.TRAIT_MUSIC,), 15, 25),
    ({"bed": 2, "cafe": 1}, (config.TRAIT_LOVE, config.TRAIT_MUSIC), 33, 33),
])
def test_rest_amounts_with_bonuses(kw, traits, health, mental):
    """휴식: 체력 +15(+연애 중 5, +카페 5, +침대 4/Lv), 멘탈 +20(+음악 힐링 5, +침대 4/Lv), 지식 -2."""
    s = student(health=10, mental=10, knowledge=50, **kw)
    for t in traits:
        s.add_trait(t)
    s.rest()
    assert (s.health, s.mental, s.knowledge) == (10 + health, 10 + mental, 48)


@pytest.mark.parametrize("kw, traits, health, mental", [
    ({}, (), 22, 30),                                      # 22.5 -> 22 (round), 30
    ({"bed": 1, "cafe": 1}, (), 36, 36),                    # 24 x 1.5, 24 x 1.5
    ({}, (config.TRAIT_LOVE,), 30, 30),                     # 20 x 1.5
    ({}, (config.TRAIT_MUSIC,), 22, 38),                    # 25 x 1.5 = 37.5 -> 38 (round)
    ({"bed": 1}, (), 28, 36),                               # 19 x 1.5 = 28.5 -> 28 (round)
])
def test_rest_focus_ratio_uses_python_round(kw, traits, health, mental):
    """휴식 위주 회복 x1.5: round((기본 + 보너스) x 1.5). 지식 -2 는 배수 없음."""
    s = student(health=10, mental=10, knowledge=50, **kw)
    for t in traits:
        s.add_trait(t)
    s.rest(config.POLICIES[RF][config.POLICY_REST_RATIO])
    assert (s.health, s.mental, s.knowledge) == (10 + health, 10 + mental, 48)
    assert round(15 * 1.5) == 22 and round(37.5) == 38   # Python round 확인


@pytest.mark.parametrize("policy, health, mental", [(SF, 65, 70), (BAL, 65, 70), (RF, 72, 80)])
def test_rest_ratio_through_game(g, policy, health, mental):
    g.set_policy(policy)
    g.student.health, g.student.mental, g.student.knowledge = 50, 50, 10
    assert g.do_action(REST)
    assert (g.student.health, g.student.mental, g.student.knowledge) == (health, mental, 8)


def test_rest_knowledge_never_negative():
    s = student(knowledge=1)
    s.rest(1.5)
    assert s.knowledge == 0


def test_events_still_change_gauges_directly(g):
    """랜덤 이벤트는 예외: 게이지를 바로 바꾼다(반찬 체력 +15)."""
    g.student.health = 50
    side = next(e for e in config.AUTO_EVENTS if e[config.EVENT_ID] == "side_dish")
    g.start_event(side)
    assert g.student.health == 65


# ======================= 2. 버프 든든함 =======================

@pytest.mark.parametrize("menu, fitness, duration", [(0, False, 30), (1, False, 36), (5, False, 60),
                                                     (0, True, 40), (5, True, 70)])
def test_full_duration(menu, fitness, duration):
    s = student(menu=menu)
    if fitness:
        s.add_trait(config.TRAIT_FITNESS)
    assert s.get_full_duration() == duration
    s.elapsed = 12.5
    s.feed()
    assert s.full_until == 12.5 + duration
    assert s.get_full_time_left() == duration


def test_full_none_before_feed():
    s = Student()
    assert s.full_until is None
    assert s.get_full_time_left() == 0 and not s.is_full_buff_active()
    assert config.BUFF_FULL not in s.get_statuses()


def test_full_expiry_exact_time():
    s = Student()
    s.feed()
    s.elapsed = 29.99
    assert s.is_full_buff_active() and s.get_full_time_left() == pytest.approx(0.01)
    s.elapsed = 30.0
    assert not s.is_full_buff_active() and s.get_full_time_left() == 0
    s.elapsed = 31.0
    assert s.get_full_time_left() == 0          # 음수가 되지 않는다


def test_full_halves_health_decay_until_expiry():
    """t=0 학식 -> 1~29초 감소는 체력 0.5, 30초 감소(버프 끝난 시각)는 1. 멘탈은 그대로 1."""
    s = Student()
    s.feed()
    for _ in range(29):
        s.update(1.0)
    assert s.health == pytest.approx(80 - 29 * 0.5) and s.mental == 80 - 29
    s.update(1.0)
    assert s.health == pytest.approx(80 - 29 * 0.5 - 1)
    assert s.mental == 50


@pytest.mark.parametrize("care, grad, expected", [(0, False, 0.5), (2, False, 0.4),
                                                  (5, False, 0.25), (0, True, 1.0)])
def test_full_decay_combines_with_care_and_grad(care, grad, expected):
    s = student(health_care=care)
    if grad:
        s.knowledge = GOAL
        s.promote()
        assert s.enter_grad_school()            # 1년차 c = 0: 배수 2.0 (B안)
    s.feed()
    assert s.get_health_decay() == pytest.approx(expected)
    assert s.get_mental_decay() == pytest.approx(expected * 2)   # 멘탈은 버프와 상관없음


def test_full_refresh_not_stack():
    s = Student()
    s.feed()
    s.elapsed = 10.0
    s.feed()
    assert s.full_until == 40.0 and s.get_full_time_left() == 30.0


def test_full_pauses_during_dialog(g):
    g.do_action(FEED)
    g.update(5.0)
    assert g.student.get_full_time_left() == pytest.approx(25.0)
    mt = next(e for e in config.CHOICE_EVENTS if e[config.EVENT_ID] == "mt_invite")
    g.start_event(mt)
    assert g.state == config.STATE_EVENT
    g.update(100.0)
    assert g.student.get_full_time_left() == pytest.approx(25.0)
    g.update(config.EVENT_INPUT_DELAY)
    assert g.choose_option(config.CHOICE_SECOND)
    g.update(24.9)
    assert g.student.is_full_buff_active()
    g.update(0.1)
    assert not g.student.is_full_buff_active()


def test_full_survives_grad_entry(g):
    s = g.student
    reach_grade(s, 4)
    s.elapsed = 100.0
    s.feed()
    s.knowledge = GOAL
    g.check_promotion()
    assert g.check_ending() and g.is_graduation_ending()
    press(g, pygame.K_c)
    assert g.grad_year == 1 and g.student is s
    assert s.full_until == 130.0 and s.is_full_buff_active()


@pytest.mark.parametrize("how", ["start_new_game", "reincarnate", "restart_key"])
def test_full_cleared_on_new_round(g, how):
    g.do_action(FEED)
    assert g.student.full_until is not None
    if how == "start_new_game":
        g.start_new_game()
    elif how == "reincarnate":
        g.end_game(config.ENDING_TOP)
        g.reincarnate()
    else:
        g.end_game(config.ENDING_LEAVE)
        press(g, pygame.K_r)
    assert g.state == config.STATE_PLAYING
    assert g.student.full_until is None and not g.student.is_full_buff_active()


# ======================= 3. 자동 행동 고르기 =======================

@pytest.mark.parametrize("policy", [SF, BAL, RF])
@pytest.mark.parametrize("which", ["health", "mental"])
def test_choose_rest_boundary(g, policy, which):
    t = config.POLICIES[policy][config.POLICY_THRESHOLD]
    g.set_policy(policy)
    g.student.health = g.student.mental = 100
    g.student.feed()
    setattr(g.student, which, t - 0.01)
    assert g.choose_auto_action() == REST
    setattr(g.student, which, t)
    assert g.choose_auto_action() == STUDY
    g.student.full_until = None
    assert g.choose_auto_action() == FEED


def test_choose_feed_when_buff_expires_exactly(g):
    g.student.feed()                       # full_until 30
    g.student.elapsed = 29.99
    assert g.choose_auto_action() == STUDY
    g.student.elapsed = 30.0
    assert g.choose_auto_action() == FEED


def test_choose_threshold_independent_of_max(g):
    g.upgrades[HMAX] = 5
    g.upgrades[MMAX] = 5
    g.student.feed()
    g.student.health, g.student.mental = 49.99, 150
    assert g.choose_auto_action() == REST
    g.student.health = 50
    assert g.choose_auto_action() == STUDY


def test_auto_cycle_feed_then_study_then_rest(auto_g):
    """자동 행동: 2초 학식 -> 4초 공부 ... 체력·멘탈이 기준 아래면 휴식."""
    names = []
    real = auto_g.do_action

    def spy(name):
        names.append(name)
        return real(name)
    auto_g.do_action = spy
    auto_g.update(2.0)
    auto_g.update(2.0)
    assert names == [FEED, STUDY]
    auto_g.student.mental = 40
    auto_g.update(2.0)
    assert names[-1] == REST


def test_auto_rest_focus_rest_uses_ratio(auto_g):
    auto_g.set_policy(RF)
    auto_g.student.health = 60
    auto_g.update(2.0)                     # 감소 2 -> 58 / 78, 휴식 x1.5 -> 58 + 22, 78 + 30 -> 100
    assert auto_g.last_action == REST
    assert (auto_g.student.health, auto_g.student.mental) == (80, 100)


# ======================= 4. 최댓값 (체력 증진·멘탈 관리) =======================

@pytest.mark.parametrize("lv", range(6))
def test_max_values(lv):
    s = student(health_max=lv, mental_max=5 - lv)
    assert s.max_health == 100 + 10 * lv
    assert s.max_mental == 100 + 10 * (5 - lv)


@pytest.mark.parametrize("lv, start, expected", [(0, 90, 100), (0, 100, 100), (1, 100, 110),
                                                 (1, 96, 110), (1, 94, 109), (5, 140, 150),
                                                 (5, 150, 150)])
def test_rest_clamps_to_max_health(lv, start, expected):
    s = student(health=start, health_max=lv)
    s.rest()
    assert s.health == expected


@pytest.mark.parametrize("lv", [0, 2, 5])
def test_change_clamps_both_sides(lv):
    s = student(health_max=lv, mental_max=lv)
    s.change_health(1000)
    s.change_mental(1000)
    assert (s.health, s.mental) == (100 + 10 * lv, 100 + 10 * lv)
    s.change_health(-1000)
    s.change_mental(-1000)
    assert (s.health, s.mental) == (0, 0)


def test_event_effect_clamps_to_raised_max(g):
    g.upgrades[HMAX] = 2
    g.student.health = 115
    side = next(e for e in config.AUTO_EVENTS if e[config.EVENT_ID] == "side_dish")
    g.start_event(side)
    assert g.student.health == 120


def test_buying_raises_cap_only(g):
    g.money = 100_000
    assert g.student.max_health == 100
    assert g.buy_upgrade(HMAX)
    assert g.student.max_health == 110 and g.student.health == 80
    assert g.buy_upgrade(MMAX)
    assert g.student.max_mental == 110 and g.student.mental == 80
    for _ in range(4):
        assert g.buy_upgrade(HMAX)
    assert g.student.max_health == 150 and g.is_upgrade_maxed(HMAX)
    assert not g.buy_upgrade(HMAX)
    assert g.student.health == 80


def test_new_round_starts_at_80_with_raised_max(g):
    g.upgrades[HMAX] = 3
    g.start_new_game()
    assert g.student.health == config.HEALTH_START == 80
    assert g.student.max_health == 130


def test_low_limit_independent_of_max():
    s = student(health=29, mental=29, health_max=5, mental_max=5)
    assert s.is_tired() and s.is_depressed() and s.has_dark_circles()


# ======================= 5. 자기 관리 =======================

def test_self_care_zero_level_is_int_zero():
    s = Student()
    assert s.get_self_care_regen() == 0 and type(s.get_self_care_regen()) is int
    s.update(3.0)
    assert type(s.health) is int and s.health == 77


@pytest.mark.parametrize("lv", range(1, 6))
def test_self_care_regen_amount(lv):
    assert student(self_care=lv).get_self_care_regen() == pytest.approx(0.2 * lv)


@pytest.mark.parametrize("lv, full, exam, health, mental", [
    (1, False, False, 79.2, 79.2),
    (1, True, False, 79.7, 79.2),
    (1, False, True, 79.2, 78.2),
    (3, True, True, 80.1, 78.6),
    (5, False, False, 80, 80),
])
def test_self_care_with_decay_one_second(lv, full, exam, health, mental):
    s = student(self_care=lv, elapsed=45.0 if exam else 0.0)
    if full:
        s.feed()
    s.update(1.0)
    assert s.health == pytest.approx(health) and s.mental == pytest.approx(mental)
    assert s.health == round(s.health, config.GAUGE_DECIMALS)


def test_self_care_fractional_accumulates_without_drift():
    s = student(self_care=3)                   # 매초 -1 + 0.6 = -0.4
    for _ in range(10 * 60):
        s.update(1 / 60)
    assert s.health == pytest.approx(76.0, abs=1e-9)
    assert s.mental == pytest.approx(76.0, abs=1e-9)


def test_self_care_clamped_at_max_and_applies_while_resting():
    s = student(health=119.9, mental=119.9, self_care=5, health_max=2, mental_max=2)
    s.feed()                                   # 체력 +1 - 0.5 = +0.5 -> 120 에서 멈춤
    s.update(1.0)
    assert s.health == 120
    assert s.mental == pytest.approx(119.9)    # 멘탈 +1 - 1 = 0
    s.rest()
    s.update(1.0)
    assert s.health == 120 and s.mental == 120


# ======================= 6. 디버프·버프 =======================

@pytest.mark.parametrize("health, tired, gain", [(29.99, True, 7), (30, False, 10), (0.5, True, 7)])
def test_tired_boundary_and_study(health, tired, gain):
    s = student(health=health)
    assert s.is_tired() is tired and s.has_debuff(config.DEBUFF_TIRED) is tired
    s.study()
    assert s.knowledge == gain


def test_tired_judged_before_study():
    """공부 직전 체력 32(피곤 아님) -> 공부로 27이 되어도 이번 공부는 10 그대로, 다음 공부부터 7."""
    s = student(health=32)
    s.study()
    assert s.knowledge == 10 and s.health == 27 and s.is_tired()
    s.study()
    assert s.knowledge == 17


@pytest.mark.parametrize("policy, book, lib, exam, expected", [
    (SF, 5, 1, False, round((10 + 10 + 3) * 1.8 * 0.7)),   # 28.98 -> 29 (B안)
    (RF, 0, 0, True, round(20 * 0.7 * 0.7)),               # 9.8 -> 10
    (BAL, 1, 0, False, round(12 * 0.7)),                   # 8.4 -> 8
])
def test_tired_multiplies_after_bonus_and_policy(policy, book, lib, exam, expected):
    s = student(health=20, elapsed=45.0 if exam else 0.0, reference_book=book, library=lib)
    p = config.POLICIES[policy]
    s.study(p[config.POLICY_KNOWLEDGE_RATIO], p[config.POLICY_COST_RATIO])
    assert s.knowledge == expected


@pytest.mark.parametrize("mental, depressed", [(29.99, True), (30, False), (0.1, True)])
def test_depressed_boundary(g, mental, depressed):
    g.student.mental = mental
    assert g.student.is_depressed() is depressed
    assert g.student.has_debuff(config.DEBUFF_DEPRESSED) is depressed
    assert g.get_condition_money_ratio() == (0.7 if depressed else 1.0)


def test_has_debuff_unknown_name():
    s = student(health=0.5, mental=0.5)
    assert s.has_debuff("배고픔") is False
    assert s.has_debuff(config.BUFF_FULL) is False


@pytest.mark.parametrize("mental_before, money", [(37.99, 7), (38, 10), (50, 10), (20, 7)])
def test_depressed_money_judged_after_effects(g, mental_before, money):
    """공부(멘탈 -8) 뒤 멘탈이 30 미만이면 이번 지식 연구비 x0.7 (연구비를 쌓는 순간 판정)."""
    g.student.mental = mental_before
    g.do_action(STUDY)
    assert g.student.knowledge == 10
    assert g.money == money


def test_depressed_money_on_knowledge_event(g):
    g.student.mental = 20                    # 칭찬 +5 -> 25 여전히 우울
    praise = next(e for e in config.AUTO_EVENTS if e[config.EVENT_ID] == "professor_praise")
    g.start_event(praise)
    assert g.money == int(15 * 0.7)


@pytest.mark.parametrize("policy, health, mental, good", [
    (RF, 70, 70, True), (RF, 69.99, 100, False), (RF, 100, 69.99, False), (RF, 150, 150, True),
    (BAL, 100, 100, False), (SF, 100, 100, False),
])
def test_condition_good_boundary(g, policy, health, mental, good):
    g.upgrades[HMAX] = g.upgrades[MMAX] = 5
    g.set_policy(policy)
    g.student.health, g.student.mental = health, mental
    assert g.is_good_condition() is good
    assert g.get_condition_money_ratio() == pytest.approx(1.5 if good else 1.0)   # B안 (M단위 1.2)
    assert (config.CONDITION_GOOD in g.get_status_names()) is good


@pytest.mark.parametrize("start, money", [(90, 10), (75, 7)])
def test_condition_money_judged_after_study(g, start, money):
    """휴식 위주 공부(지식 7): 공부 뒤 체력·멘탈 둘 다 70 이상이면 x1.5 -> 10.5 -> 10, 아니면 7."""
    g.set_policy(RF)
    g.student.health = g.student.mental = start
    g.do_action(STUDY)
    assert g.student.knowledge == 7
    assert g.money == money


@pytest.mark.parametrize("fame", [0, 2])
def test_money_multiplier_combines(g, fame):
    g.fame = fame
    g.set_policy(RF)
    g.student.health = g.student.mental = 90
    assert g.get_money_multiplier() == pytest.approx((1 + 0.1 * fame) * 1.5)
    g.student.mental = 20
    assert g.get_money_multiplier() == pytest.approx((1 + 0.1 * fame) * 0.7)


@pytest.mark.parametrize("setup", ["good", "depressed"])
def test_graduation_bonus_not_affected_by_condition(g, setup):
    s = g.student
    reach_grade(s, 4)
    s.elapsed = 10.0
    if setup == "good":
        g.set_policy(RF)
        s.health = s.mental = 100
        gain = 7
    else:
        s.health, s.mental = 100, 20
        gain = 10
    s.knowledge = GOAL - 5
    g.money = 0
    g.do_action(STUDY)
    assert g.state == config.STATE_ENDING and g.ending == judge_ending(10.0)
    bonus = config.GRADUATION_BONUS[g.ending]
    assert g.graduation_bonus == bonus
    ratio = 1.5 if setup == "good" else 0.7
    assert g.money == int(gain * ratio + 1e-9) + bonus


@pytest.mark.parametrize("setup", ["good", "depressed"])
def test_scholarship_not_affected_by_condition(g, setup):
    g.upgrades[config.UPGRADE_SCHOLARSHIP] = 1
    reach_grade(g.student, 3)
    if setup == "good":
        g.set_policy(RF)
        g.student.health = g.student.mental = 100
    else:
        g.student.mental = 10
    g.money = 0
    g.start_event(config.SCHOLARSHIP_EVENT)
    assert g.money == 30 * 3


def test_statuses_order():
    s = student(health=20, mental=20)
    assert s.get_statuses() == [config.DEBUFF_TIRED, config.DEBUFF_DEPRESSED]
    s.feed()
    assert s.get_statuses() == [config.DEBUFF_TIRED, config.DEBUFF_DEPRESSED, config.BUFF_FULL]
    s.health = 30
    assert s.get_statuses() == [config.DEBUFF_DEPRESSED, config.BUFF_FULL]
    s.health = s.mental = 80
    assert s.get_statuses() == [config.BUFF_FULL]
    s.full_until = None
    assert s.get_statuses() == []


def test_status_names_append_condition_last(g):
    g.set_policy(RF)
    g.student.feed()
    assert g.get_status_names() == [config.BUFF_FULL, config.CONDITION_GOOD]
    g.set_policy(BAL)
    assert g.get_status_names() == [config.BUFF_FULL]


# ======================= 7. 진급 기준 2배 =======================

@pytest.mark.parametrize("knowledge, grade", [(399, 1), (400, 2), (899, 2), (900, 3), (1499, 3),
                                              (1500, 4), (2199, 4)])
def test_grade_goals_doubled(knowledge, grade):
    s = student(knowledge=knowledge)
    s.promote()
    assert s.get_grade() == grade and not s.has_graduated()


def test_graduation_at_2200():
    s = student(knowledge=GOAL - 1, elapsed=123.0)
    s.promote()
    assert not s.has_graduated()
    s.knowledge = GOAL
    s.promote()
    assert s.has_graduated() and s.get_ending() == judge_ending(123.0)


@pytest.mark.parametrize("year, goal", [(1, 3000), (2, 4000), (3, 5200), (4, 6600)])
def test_grad_goals_doubled(year, goal):
    assert Student().get_grad_goal(year) == goal


@pytest.mark.parametrize("offset, ending", [
    (0.0, config.ENDING_TOP), (0.0001, config.ENDING_NORMAL),
])
def test_time_threshold_boundaries_from_config(offset, ending):
    assert judge_ending(config.TOP_GRADUATE_SECONDS + offset) == ending
    assert judge_ending(config.NORMAL_GRADUATE_SECONDS + offset) == \
        (config.ENDING_NORMAL if offset == 0.0 else config.ENDING_BARELY)


# ======================= 8. 화면: 패널 13줄, 상태 배지, 막대 지금/최대 =======================

def test_panel_13_rows_geometry(g):
    panel = pygame.Rect(config.UPGRADE_PANEL_RECT)
    inner = panel.inflate(-2 * P, -2 * P)
    rows = [g.get_upgrade_row_rect(i) for i in range(len(config.UPGRADE_IDS))]
    assert len(rows) == 14   # (연구비) 13 -> 14
    for i, row in enumerate(rows):
        assert (row.top, row.height) == (165 + 20 * i, 19)
        assert inner.contains(row)
        assert row.right <= config.STATUS_PANEL_X + config.STATUS_PANEL_WIDTH   # 왼쪽 열
    for a, b in zip(rows, rows[1:]):
        assert a.bottom < b.top
    assert rows[-1].bottom == 444


@pytest.mark.parametrize("index", range(14))
def test_panel_every_row_clickable_buys(g, index):
    g.money = 100_000
    g.upgrade_panel_open = True
    uid = config.UPGRADE_IDS[index]
    cost = g.get_upgrade_cost(uid)
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                      pos=g.get_upgrade_row_rect(index).center))
    assert g.upgrade_cursor == index
    assert g.upgrades[uid] == 1 and g.money == 100_000 - cost


def test_panel_keys_wrap_and_enter_buys(g):
    g.money = 100_000
    press(g, pygame.K_u)
    assert g.upgrade_panel_open and g.upgrade_cursor == 0
    press(g, pygame.K_UP)
    assert g.upgrade_cursor == 13 and config.UPGRADE_IDS[13] == config.UPGRADE_RESEARCH
    press(g, pygame.K_RETURN)
    assert g.upgrades[config.UPGRADE_RESEARCH] == 1
    press(g, pygame.K_DOWN)
    assert g.upgrade_cursor == 0
    for _ in range(11):
        press(g, pygame.K_DOWN)
    assert g.upgrade_cursor == 11 and config.UPGRADE_IDS[11] == MMAX
    press(g, pygame.K_RETURN)
    assert g.upgrades[MMAX] == 1


def test_panel_draws_13_names(g, monkeypatch):
    g.upgrade_panel_open = True
    texts = record_texts(monkeypatch, game_module, g.draw)
    for uid in config.UPGRADE_IDS:
        assert config.UPGRADES_BY_ID[uid][config.UPGRADE_NAME] in texts, uid


def test_status_badges_drawn_in_status_panel(g, monkeypatch):
    g.student.health, g.student.mental = 20, 20
    g.student.feed()
    texts = record_texts(monkeypatch, student_module, g.draw)
    assert [t for t in texts if t in config.STATUS_COLORS] == \
        [config.DEBUFF_TIRED, config.DEBUFF_DEPRESSED, config.BUFF_FULL]
    # 배지 자리: 상태 패널 안, 체력 라벨 위. 2열로 1·2번째는 첫 줄, 3번째는 둘째 줄
    w, h, gap = config.TRAIT_BADGE_WIDTH, config.TRAIT_BADGE_HEIGHT, config.TRAIT_BADGE_GAP
    boxes = [pygame.Rect(config.TRAIT_BADGE_X, config.STATUS_BADGE_Y, w, h),
             pygame.Rect(config.TRAIT_BADGE_X + w + gap, config.STATUS_BADGE_Y, w, h),
             pygame.Rect(config.TRAIT_BADGE_X, config.STATUS_BADGE_Y + h + gap, w, h)]
    panel = pygame.Rect(config.STATUS_PANEL_X, config.PANEL_Y, config.STATUS_PANEL_WIDTH,
                        config.PANEL_HEIGHT)
    for box, name in zip(boxes, [config.DEBUFF_TIRED, config.DEBUFF_DEPRESSED, config.BUFF_FULL]):
        assert panel.contains(box)
        assert box.bottom + P <= config.HEALTH_LABEL_Y
        fill = config.STATUS_COLORS[name][0]
        assert any(tuple(g.screen.get_at((x, y)))[:3] == fill
                   for x in range(box.left, box.right) for y in range(box.top, box.bottom)), name


def test_condition_badge_drawn(g, monkeypatch):
    g.set_policy(RF)
    texts = record_texts(monkeypatch, student_module, g.draw)
    assert config.CONDITION_GOOD in texts


@pytest.mark.parametrize("hlv, mlv, health, mental, texts", [
    (0, 0, 80, 80, ["80/100", "80/100"]),
    (2, 1, 80, 80, ["80/120", "80/110"]),
    (0, 0, 79.6, 29.4, ["80/100", "29/100"]),
    (5, 5, 150, 0, ["150/150", "0/150"]),
])
def test_bars_show_now_over_max(monkeypatch, hlv, mlv, health, mental, texts):
    pygame.init()
    surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
    s = student(health=health, mental=mental, health_max=hlv, mental_max=mlv)
    made = record_texts(monkeypatch, student_module, lambda: s.draw_gauges(surface, font))
    assert made == [config.HEALTH_LABEL, texts[0], config.MENTAL_LABEL, texts[1]]


@pytest.mark.parametrize("hlv, health, width", [(0, 50, 100), (5, 75, 100), (5, 150, 200),
                                                (2, 30, 50)])
def test_bar_fill_relative_to_max(hlv, health, width):
    pygame.init()
    surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    surface.fill(config.COLOR_BG)
    font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
    s = student(health=health, health_max=hlv)
    s.draw_gauges(surface, font)
    y = config.HEALTH_BAR_Y + config.BAR_HEIGHT // 2
    filled = sum(1 for x in range(config.GAUGE_X, config.GAUGE_X + config.BAR_WIDTH)
                 if tuple(surface.get_at((x, y)))[:3] in (config.COLOR_GREEN, config.COLOR_RED))
    assert filled == width


def test_bar_colour_by_real_value_not_ratio():
    """최댓값이 150이어도 빨강은 실제 값 30 미만일 때만."""
    pygame.init()
    surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
    y = config.HEALTH_BAR_Y + config.BAR_HEIGHT // 2
    for health, colour in ((40, config.COLOR_GREEN), (29, config.COLOR_RED)):
        surface.fill(config.COLOR_BG)
        student(health=health, health_max=5).draw_gauges(surface, font)
        assert tuple(surface.get_at((config.GAUGE_X + 1, y)))[:3] == colour


def test_game_draw_bar_uses_max(g):
    g.upgrades[HMAX] = 5
    g.student.health = 75
    g.draw()
    y = config.HEALTH_BAR_Y + config.BAR_HEIGHT // 2
    filled = sum(1 for x in range(config.GAUGE_X, config.GAUGE_X + config.BAR_WIDTH)
                 if tuple(g.screen.get_at((x, y)))[:3] == config.COLOR_GREEN)
    assert filled == 100


# ======================= 9. record.json: 새 3종 저장·불러오기 =======================

def read_record(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_new_upgrades_saved_and_loaded(g, isolated_record_path):
    g.money = 100_000
    assert g.buy_upgrade(HMAX) and g.buy_upgrade(HMAX)
    assert g.buy_upgrade(MMAX) and g.buy_upgrade(SELF)
    data = read_record(isolated_record_path)
    assert set(data["upgrades"]) == set(config.UPGRADE_IDS)
    assert (data["upgrades"][HMAX], data["upgrades"][MMAX], data["upgrades"][SELF]) == (2, 1, 1)
    pygame.quit()
    g2 = Game()
    assert (g2.upgrades[HMAX], g2.upgrades[MMAX], g2.upgrades[SELF]) == (2, 1, 1)
    g2.start_new_game()
    assert g2.student.max_health == 120 and g2.student.max_mental == 110
    assert g2.student.get_self_care_regen() == pytest.approx(0.2)


def test_old_record_without_new_upgrades(isolated_record_path, no_events):
    old = {"best_knowledge": 1234, "money": 500, "fame": 2,
           "upgrades": {uid: 1 for uid in OLD_IDS}}
    Path(isolated_record_path).write_text(json.dumps(old), encoding="utf-8")
    g = Game()
    assert (g.best_record, g.money, g.fame) == (1234, 500, 2)
    for uid in OLD_IDS:
        assert g.upgrades[uid] == 1
    for uid in NEW_IDS:
        assert g.upgrades[uid] == 0
    g.start_new_game()
    assert g.student.max_health == 100 and g.student.get_self_care_regen() == 0
    assert g.save_record()
    assert set(read_record(isolated_record_path)["upgrades"]) == set(config.UPGRADE_IDS)
    pygame.quit()


@pytest.mark.parametrize("bad", [6, -1, 2.5, "3", None, True])
def test_invalid_new_upgrade_levels_are_zero(isolated_record_path, no_events, bad):
    data = {"best_knowledge": 0, "money": 0, "fame": 0,
            "upgrades": {HMAX: bad, MMAX: 5, SELF: bad}}
    Path(isolated_record_path).write_text(json.dumps(data), encoding="utf-8")
    g = Game()
    assert g.upgrades[HMAX] == 0 and g.upgrades[SELF] == 0
    assert g.upgrades[MMAX] == 5
    pygame.quit()


# ======================= 10. 밸런스 불변식 (분포는 고정하지 않음) =======================

def _idle_round(seed, policy_key, dt=0.25):
    g = Game(seed=seed)
    press(g, pygame.K_RETURN)
    press(g, policy_key)
    for _ in range(8000):
        if g.state == config.STATE_EVENT:
            if not g.choose_option(config.CHOICE_FIRST):
                g.update(dt)
        elif g.state == config.STATE_PLAYING:
            g.update(dt)
            s = g.student
            assert 0 <= s.health <= s.max_health and 0 <= s.mental <= s.max_mental
            assert s.knowledge >= 0
        else:
            break
    assert g.state == config.STATE_ENDING
    s = g.student
    return g.ending, s.graduation_time, s.knowledge, s.elapsed


def test_idle_balance_invariants():
    """시드 6개 x 방침 3개: 크래시 없이 엔딩, 등급 = judge_ending(걸린 시간),
    지식 버는 속도 공부 위주 > 균형 > 휴식 위주, 졸업 시각 평균도 같은 순서(졸업이 있는 방침끼리)."""
    rates, means = {}, {}
    for name, key in (("study", pygame.K_1), ("balanced", pygame.K_2), ("rest", pygame.K_3)):
        know, time, grads = 0, 0.0, []
        for seed in range(6):
            ending, grad_time, knowledge, elapsed = _idle_round(seed, key)
            if grad_time is None:
                assert ending == config.ENDING_LEAVE
            else:
                assert ending == judge_ending(grad_time)
                grads.append(grad_time)
            know += knowledge
            time += elapsed
        rates[name] = know / time
        if grads:
            means[name] = sum(grads) / len(grads)
    pygame.quit()
    assert rates["study"] > rates["balanced"] > rates["rest"], rates
    ordered = [means[n] for n in ("study", "balanced", "rest") if n in means]
    assert len(ordered) >= 2 and ordered == sorted(ordered), means
