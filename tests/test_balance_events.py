"""검수 단위 E: 밸런스·가독성 조정 + 엔딩 기준 변경 (기획서 2절·9절, jeja-spec 5절·14절).

이 파일에는 conftest 의 no_events 가 적용되지 않는다(이벤트가 켜진 상태). 모든 Game 은 seed 고정.

- (a) 확률 이벤트 최소 간격 EVENT_MIN_GAP(8초): 경계 7.99/8.0, 보장 예외, 학년 넘어 이어 셈,
      대화 정지 시간 미포함, 새 판 초기화, 간격 미충족 시 rng 를 뽑지 않음(결정성)
- 최소 4·최대 5 보장 유지(시드 여러 개 x 간격 1~3초 완주) + 완주 중 간격 규칙 위반 0
- (b) 엔딩 기준 1000/750(K단위 승인, 처음 E단위는 700/450): judge_ending 경계 749/750/999/1000, 실제 게임 흐름(이벤트로 경계를 넘는 경우 포함)
- 이벤트 켠 밸런스(시드 20개, 자동 행동 끈 수동 행동): 1.5초 수석, 2.0초 무사, 2.5~4.0초 아슬아슬(+휴학)이 과반
- (c) 가독성: 알림 2줄 나눔·상자 안, 알림·이벤트 팝업·행동 팝업·파티클 비겹침(4학년 포함),
      점무늬(대화 상태에서만, 대화창 안 미덮음, 밀도 무관), 하트 핀 위치, 미리보기 글자 대비
- 문서 일치: 기획서 2절 표·jeja-spec 5절·README·config 가 1000/750

(L단위, 기획서 11절) 졸업 등급은 걸린 시간(200/360초, 11절 A안 밸런스로 수석 240 -> 200), 졸업은 4학년에서 지식 1100,
이벤트 최소 4·최대 5회는 60초 주기마다 센다(event_counts 키 = 주기 번호). 위 (b)·밸런스 항목은 새 규칙으로 바꿨다.
"""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pathlib  # noqa: E402
import re  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
import game as game_module  # noqa: E402
from conftest import (JEJA_SPEC_PATH, doc_section, press, reach_grade, read_doc,  # noqa: E402
                      spec_appendix, spec_rule_text)
from game import Game, sprite_size  # noqa: E402
from student import Student, judge_ending  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = config.PIXEL_SIZE
FEED, REST, STUDY = config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY
H, M, K = config.GAUGE_HEALTH, config.GAUGE_MENTAL, config.GAUGE_KNOWLEDGE
GAP = config.EVENT_MIN_GAP
GRADE_STARTS = [0.0, 60.0, 120.0, 180.0]   # (L단위) 이제는 1~4번 60초 주기의 시작 시각
SIM_CAP_SECONDS = 1800                       # (L단위) 시간 제한이 없으므로 완주 시뮬레이션 상한(30분)
STAGE_INNER = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH,
                          config.PANEL_HEIGHT).inflate(-2 * P, -2 * P)
DIALOG = pygame.Rect(config.EVENT_DIALOG_RECT)
DIALOG_WITH_DROP = DIALOG.union(DIALOG.move(0, P))
DT = 0.05


# ======================= 도우미 =======================

@pytest.fixture
def make_game():
    """seed 고정 Game 을 타이틀에서 Enter 눌러 게임 진행 중으로 만든다."""
    def factory(seed=0):
        g = Game(seed=seed)
        press(g, pygame.K_RETURN)
        assert g.state == config.STATE_PLAYING
        return g

    yield factory
    pygame.quit()


@pytest.fixture
def quiet_game(make_game, monkeypatch):
    """자동 이벤트 판정을 끈 Game(화면 검사용: start_event 로 직접 띄운다)."""
    monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 0)
    return make_game


def event_by_id(event_id):
    for event in config.ALL_EVENTS:
        if event[config.EVENT_ID] == event_id:
            return event
    raise KeyError(event_id)


def color(surf, x, y):
    return tuple(surf.get_at((x, y)))[:3]


def set_time(g, elapsed, count=None, last=None):
    """제자의 게임 시각·그 주기 이벤트 수·직전 이벤트 시각을 맞춘다.

    (L단위) 이벤트 수는 학년이 아니라 60초 주기 번호로 센다.
    """
    s = g.student
    s.elapsed = elapsed
    if count is not None:
        s.event_counts[s.get_cycle_index()] = count
    s.last_event_time = last
    s.health = s.mental = 80
    # (G단위) 쿨타임이 없어져 g.cooldown = 0 으로 풀어 줄 필요가 없다


def count(g, cycle=1):
    """(L단위) cycle번 주기의 이벤트 수(없는 주기는 0)."""
    return g.student.event_counts.get(cycle, 0)


def rng_draws(monkeypatch, g, value=0.0):
    """g.rng.random 을 value 를 돌려주는 가짜로 바꾸고, 호출 횟수 목록을 돌려준다."""
    calls = []

    def fake():
        calls.append(1)
        return value
    monkeypatch.setattr(g.rng, "random", fake)
    return calls


# ======================= 0. 상수 =======================

def test_e_constants():
    assert config.EVENT_MIN_GAP == 8.0
    # (L단위) 지식 1000/750 -> 걸린 시간 200/360초 (11절 A안: 수석 240 -> 200)
    assert (config.TOP_GRADUATE_SECONDS, config.NORMAL_GRADUATE_SECONDS) == (200, 360)
    assert config.PAUSE_DOT_STEP == 12 == P * 3
    assert config.EVENT_NOTICE_FONT_SIZE == 16
    assert config.EVENT_NOTICE_TEXT_MAX_WIDTH == 160
    assert config.EVENT_NOTICE_HEIGHT == 56
    assert config.LOOK_SPRITES[config.LOOK_HEART_PIN][0] == (-3, 2)
    # 알림이 있을 때 이벤트 팝업 첫 줄 가운데 y = 212
    assert config.EVENT_NOTICE_Y + config.EVENT_NOTICE_HEIGHT + config.EVENT_POPUP_TOP_MARGIN == 212
    # 기존 이벤트 규칙은 그대로
    assert (config.EVENT_CHANCE, config.EVENT_MIN_PER_GRADE, config.EVENT_MAX_PER_GRADE) == (0.25, 4, 5)


# ======================= 1. 최소 간격 =======================

def test_new_student_and_new_game_have_no_last_event():
    assert Student().last_event_time is None
    assert Student().is_event_gap_passed()


@pytest.mark.parametrize("gap, passed", [(0.0, False), (1.0, False), (7.99, False),
                                         (8.0, True), (8.01, True), (30.0, True)])
def test_gap_boundary_student(gap, passed):
    s = Student()
    s.last_event_time = 12.0
    s.elapsed = 12.0 + gap
    assert s.is_event_gap_passed() is passed


@pytest.mark.parametrize("gap, fires", [(7.99, False), (8.0, True)])
def test_gap_boundary_chance_path(make_game, monkeypatch, gap, fires):
    """확률 경로(보장 아님, 확률 1): 직전 이벤트 후 7.99초면 안 뜨고 8.0초면 뜬다."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g = make_game(1)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    last = 20.0
    set_time(g, last + gap, count=4, last=last)    # 이벤트 수 4 -> 보장 없음, 최대 5 미만
    assert not g.student.needs_guaranteed_event()
    assert g.do_action(FEED)
    assert count(g) == (5 if fires else 4)
    if fires:
        assert g.student.last_event_time == pytest.approx(last + gap)
    else:
        assert g.student.last_event_time == last


def test_gap_passes_exactly_after_480_frames(make_game, monkeypatch):
    """1/60초 프레임 480번(부동소수 누적) 뒤 정확히 8초로 통과한다(TIME_EPSILON 처리)."""
    g = make_game(2)
    g.student.last_event_time = g.student.elapsed
    for frame in range(480):
        g.student.health = g.student.mental = 80
        if frame == 479:
            assert not g.student.is_event_gap_passed()
        g.update(1 / 60)
    assert g.student.is_event_gap_passed()


@pytest.mark.parametrize("cycle", [1, 2, 3, 4, 7])
@pytest.mark.parametrize("k", [1, 4])
def test_guarantee_ignores_gap(make_game, monkeypatch, cycle, k):
    """보장 경로는 직전 이벤트가 0.25초 전이어도(확률 0) 뜬다. (L단위) 주기 기준."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 0.0)
    g = make_game(3)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    t = (cycle - 1) * config.CYCLE_SECONDS + config.EVENT_GUARANTEE_INTERVAL * k
    set_time(g, t, count=k - 1, last=t - 0.25)
    assert g.student.needs_guaranteed_event()
    assert not g.student.is_event_gap_passed()
    assert g.do_action(FEED)
    assert count(g, cycle) == k
    assert g.student.last_event_time == t


def test_guaranteed_event_also_restarts_gap(make_game, monkeypatch):
    """보장으로 뜬 이벤트도 직전 이벤트 시각으로 기록되어, 그 뒤 확률 경로는 8초를 기다린다."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g = make_game(4)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    set_time(g, config.EVENT_GUARANTEE_INTERVAL, count=0, last=None)
    g.student.last_event_time = config.EVENT_GUARANTEE_INTERVAL - 1.0
    assert g.do_action(FEED)                         # 보장
    assert count(g) == 1
    g.update(GAP - 0.5)
    g.student.health = g.student.mental = 80
    assert g.do_action(FEED)                         # 7.5초 뒤: 확률 1 이어도 없음
    assert count(g) == 1
    g.update(0.5)
    g.student.health = g.student.mental = 80
    # (G단위) 쿨타임이 없어져 g.cooldown = 0 으로 풀어 줄 필요가 없다
    assert g.do_action(FEED)                         # 8.0초 뒤: 뜸
    assert count(g) == 2


@pytest.mark.parametrize("gap, fires", [(5.99, False), (7.99, False), (8.0, True)])
def test_gap_continues_across_cycles(make_game, monkeypatch, gap, fires):
    """1번 주기 58초에 이벤트 -> 2번 주기(주기 안 경과 < 11.25, 보장 없음)에서도 이어서 센다.

    (L단위) 예전 "학년이 바뀌어도"는 이제 "60초 주기가 바뀌어도"다(학년은 1학년 그대로).
    """
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g = make_game(5)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    set_time(g, 58.0, count=4, last=None)
    assert g.do_action(FEED)
    assert count(g) == 5 and g.student.last_event_time == 58.0
    set_time(g, 58.0 + gap, last=58.0)
    assert g.student.get_cycle_index() == 2 and count(g, 2) == 0
    assert g.student.get_grade() == 1
    assert not g.student.needs_guaranteed_event()
    assert g.do_action(FEED)
    assert count(g, 2) == (1 if fires else 0)


def test_dialog_pause_not_counted_in_gap(make_game, monkeypatch):
    """선택지형 대화창이 20초 떠 있어도 게임 시간은 멈춰 있으므로 간격에 들어가지 않는다."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g = make_game(6)
    mt = event_by_id("mt_invite")
    monkeypatch.setattr(g, "pick_event", lambda: mt)
    set_time(g, 1.0, count=0, last=None)
    assert g.do_action(FEED)
    assert g.state == config.STATE_EVENT
    t_event = g.student.last_event_time
    assert t_event == 1.0
    for _ in range(400):                       # 실제 시간 20초
        g.update(DT)
    assert g.student.elapsed == t_event
    assert not g.student.is_event_gap_passed()
    assert g.choose_option(config.CHOICE_FIRST)
    assert g.state == config.STATE_PLAYING
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    for _ in range(int(round((GAP - 0.5) / 0.5))):   # 게임 시간 7.5초
        g.student.health = g.student.mental = 80
        g.update(0.5)
    assert g.student.elapsed == pytest.approx(t_event + GAP - 0.5)
    assert not g.student.is_event_gap_passed()
    assert g.do_action(FEED)
    assert count(g) == 1                 # 간격 미충족 -> 없음
    g.update(0.5)
    g.student.health = g.student.mental = 80
    # (G단위) 쿨타임이 없어져 g.cooldown = 0 으로 풀어 줄 필요가 없다
    assert g.student.is_event_gap_passed()
    assert g.do_action(FEED)
    assert count(g) == 2


def test_new_game_resets_last_event_time(make_game, monkeypatch):
    """R 로 새 판을 시작하면 직전 이벤트 시각이 None 으로 초기화된다."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g = make_game(7)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    set_time(g, 5.0, count=0, last=None)
    assert g.do_action(FEED)
    assert g.student.last_event_time == 5.0
    g.end_game(config.ENDING_LEAVE)
    press(g, pygame.K_r)
    assert g.state == config.STATE_PLAYING
    assert g.student.last_event_time is None
    assert g.student.event_counts == {}
    # 새 판 첫 행동은 간격 제한이 없다(확률 1 -> 뜸)
    assert g.do_action(FEED)
    assert count(g) == 1


def test_gap_not_met_draws_no_random(make_game, monkeypatch):
    """간격 미충족이면 rng.random 을 한 번도 부르지 않는다. 간격 충족이면 1번 부른다."""
    g = make_game(8)
    calls = rng_draws(monkeypatch, g, value=0.99)   # 0.99 >= 0.25 -> 확률 실패
    set_time(g, 20.0, count=2, last=15.0)
    assert not g.student.needs_guaranteed_event()
    assert g.roll_event() is None
    assert calls == []
    set_time(g, 23.0, count=2, last=15.0)
    assert g.roll_event() is None
    assert calls == [1]


def test_guarantee_and_max_draw_no_random_for_decision(make_game, monkeypatch):
    """최대 도달이면 rng 를 안 부르고, 보장이면 발생 판정용 rng 를 안 부른다(종류 고르기만)."""
    g = make_game(9)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    calls = rng_draws(monkeypatch, g, value=0.99)
    set_time(g, 20.0, count=config.EVENT_MAX_PER_GRADE, last=None)
    assert g.roll_event() is None and calls == []
    set_time(g, config.EVENT_GUARANTEE_INTERVAL, count=0, last=None)
    assert g.roll_event() is not None and calls == []


def test_gap_skip_keeps_rng_sequence_deterministic(make_game, monkeypatch):
    """간격 안에서 행동을 몇 번 하든 rng 상태가 그대로라서, 그 뒤 결과가 같다."""
    g1, g2 = make_game(11), make_game(11)
    for g, n in ((g1, 0), (g2, 6)):
        set_time(g, 2.0, count=0, last=None)
        g.student.last_event_time = 1.0
        state = g.rng.getstate()
        for _ in range(n):                    # 간격 안(2~7.9초) 행동 n 번
            assert g.do_action(FEED)
            g.student.elapsed += 0.9
        assert g.rng.getstate() == state
        assert sum(g.student.event_counts.values()) == 0
    assert [g1.rng.random() for _ in range(5)] == [g2.rng.random() for _ in range(5)]


# ======================= 2. 완주 시뮬레이션: 4~5 보장 + 간격 규칙 =======================

def greedy(s, low=30):
    if s.health <= low:
        return FEED
    if s.mental <= low:
        return REST
    return STUDY


def choose_knowledge(event):
    opts = event[config.EVENT_OPTIONS]
    k = [o[config.OPTION_EFFECTS].get(K, 0) for o in opts]
    return config.CHOICE_SECOND if k[1] > k[0] else config.CHOICE_FIRST


def choose_safe(event):
    opts = event[config.EVENT_OPTIONS]
    v = [o[config.OPTION_EFFECTS].get(H, 0) + o[config.OPTION_EFFECTS].get(M, 0) for o in opts]
    return config.CHOICE_SECOND if v[1] > v[0] else config.CHOICE_FIRST


def choose_first(event):
    return config.CHOICE_FIRST


CHOOSERS = (choose_knowledge, choose_safe, choose_first)


def run(seed, interval, policy=greedy, chooser=None, think=0.3):
    """한 판 완주: interval 초마다(쿨타임 풀리면) policy, 대화창은 think 초 뒤 chooser.

    이벤트가 뜰 때마다 (게임 시각, 보장 여부, 직전 이벤트 시각) 을 기록한다.
    """
    if chooser is None:
        chooser = CHOOSERS[seed % len(CHOOSERS)]
    g = Game(seed=seed)
    press(g, pygame.K_RETURN)
    log = []
    real_start = g.start_event

    def logged(event):
        s = g.student
        log.append((s.elapsed, s.needs_guaranteed_event(), s.last_event_time, s.get_grade()))
        real_start(event)
    g.start_event = logged
    wait = 0.0
    dialog_wait = None
    steps = 0
    while g.state in (config.STATE_PLAYING, config.STATE_EVENT) and \
            steps < SIM_CAP_SECONDS / DT:
        if g.state == config.STATE_EVENT:
            if dialog_wait is None:
                dialog_wait = think
            if dialog_wait <= 1e-9:
                g.choose_option(chooser(g.current_event))
                dialog_wait = None
            else:
                g.update(DT)
                dialog_wait -= DT
            continue
        if wait <= 1e-9:   # (G단위) 쿨타임 없음: interval(>=1초)마다 행동
            action = policy(g.student)
            if action is not None:
                assert g.do_action(action)
            wait = interval
        if g.state != config.STATE_PLAYING:
            continue
        g.update(DT)
        wait -= DT
        steps += 1
    return g, log


@pytest.mark.parametrize("interval", [1.0, 1.5, 2.0, 2.5, 3.0])
def test_full_runs_keep_4_to_5_per_cycle_and_gap_rule(interval):
    """시드 8개 x 간격: 완주한 60초 주기마다 이벤트 4~5회, 확률 이벤트는 모두 직전 이벤트 후 8초 이상."""
    for seed in range(8):
        g, log = run(seed, interval)
        s = g.student
        completed = int(s.elapsed // config.CYCLE_SECONDS)
        assert completed >= 1, (seed, interval)
        assert all(c <= config.EVENT_MAX_PER_GRADE for c in s.event_counts.values())
        for cycle in range(config.CYCLE_INDEX_START, completed + config.CYCLE_INDEX_START):
            assert config.EVENT_MIN_PER_GRADE <= s.event_counts.get(cycle, 0), \
                (seed, interval, s.event_counts)
        for elapsed, guaranteed, last, _ in log:
            if not guaranteed and last is not None:
                assert elapsed - last >= GAP - 1e-6, (seed, interval, elapsed, last)
        times = [e[0] for e in log]
        assert times == sorted(times)
    pygame.quit()


def test_gap_reduces_chance_events():
    """간격 규칙 때문에 확률 이벤트끼리 8초 안에 붙어 나오는 경우가 없고,
    한 판 총수가 (완주한 주기 수 x 4) ~ (지나간 주기 수 x 5). (L단위: 학년 4개 -> 주기 수)"""
    for seed in range(6):
        g, log = run(seed, 1.0)
        chance = [e for e in log if not e[1]]
        for a, b in zip(log, log[1:]):
            if not b[1]:
                assert b[0] - a[0] >= GAP - 1e-6
        assert len(chance) <= len(log)
        completed = int(g.student.elapsed // config.CYCLE_SECONDS)
        started = g.student.get_cycle_index()
        assert 4 * completed <= len(log) <= 5 * started, (seed, completed, len(log))
    pygame.quit()


# ======================= 3. 엔딩 기준 (L단위: 걸린 시간 200/360초) =======================

@pytest.mark.parametrize("seconds, ending", [
    (0, config.ENDING_TOP), (200, config.ENDING_TOP), (200.0001, config.ENDING_NORMAL),
    (240, config.ENDING_NORMAL),
    (360, config.ENDING_NORMAL), (360.0001, config.ENDING_BARELY), (5000, config.ENDING_BARELY),
])
def test_judge_ending_200_360(seconds, ending):
    """(L단위, 예전 1000/750 지식 경계) 졸업 등급은 걸린 시간으로 정한다."""
    assert judge_ending(seconds) == ending
    s = Student()
    s.elapsed = seconds
    s.knowledge = config.GRADUATION_KNOWLEDGE
    s.promote()
    assert s.get_graduation_ending() == ending


@pytest.mark.parametrize("start, ending", [
    (200.0 - DT, config.ENDING_TOP), (200.0, config.ENDING_NORMAL),
    (360.0 - DT, config.ENDING_NORMAL), (360.0, config.ENDING_BARELY),
])
def test_graduation_flow_boundaries_events_on(make_game, start, ending):
    """이벤트 켠 실제 흐름: 4학년 지식 1100에서 update 한 번(DT) -> 그 시각으로 등급, 기록 저장."""
    g = make_game(12)
    s = g.student
    s.elapsed, s.health, s.mental = start, 100, 100
    s.knowledge = config.GRADUATION_KNOWLEDGE + 5
    g.update(DT)
    assert g.state == config.STATE_ENDING
    assert g.ending == ending
    assert s.graduation_time == pytest.approx(start + DT)
    assert g.best_record == config.GRADUATION_KNOWLEDGE + 5


@pytest.mark.parametrize("start, elapsed, ending", [
    (1084, 198.5, None), (1085, 198.5, config.ENDING_TOP),
    (1085, 300.0, config.ENDING_NORMAL), (1085, 400.0, config.ENDING_BARELY),
])
def test_event_knowledge_crosses_graduation_goal(make_game, monkeypatch, start, elapsed, ending):
    """(L단위) 4학년에서 학식 + 자동형 '교수님께 칭찬'(지식 +15)으로 졸업 목표 1100을 넘으면 그 순간 졸업.

    1084 + 15 = 1099 는 못 넘어 계속 논다. 등급은 그 시각(198.5 수석 / 300 무사 / 400 아슬아슬).
    """
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g = make_game(13)
    monkeypatch.setattr(g, "pick_event", lambda: event_by_id("professor_praise"))
    reach_grade(g.student, 4)
    set_time(g, elapsed, count=0, last=None)
    g.student.event_counts[g.student.get_cycle_index()] = 4
    g.student.knowledge = start
    assert g.do_action(FEED)
    assert g.student.knowledge == start + 15
    if ending is None:
        assert g.state == config.STATE_PLAYING and g.ending is None
    else:
        assert g.state == config.STATE_ENDING and g.ending == ending
        assert g.student.graduation_time == elapsed


# ======================= 4. 이벤트 켠 밸런스 (시드 20개) =======================

BALANCE_SEEDS = range(20)


@pytest.mark.parametrize("interval, expected", [
    (1.0, config.ENDING_TOP),
    (1.5, config.ENDING_NORMAL),
    (2.0, config.ENDING_NORMAL),
    (2.5, config.ENDING_BARELY),
    (3.0, config.ENDING_BARELY),
    (4.0, config.ENDING_BARELY),
])
def test_balance_with_events(interval, expected):
    """사람처럼 interval 초마다 탐욕 행동(선택은 시드별 3전략 순환): 기대 엔딩이 과반.

    이 파일은 자동 행동을 끈(no_auto) 방치형 이전 수동 플레이 모형이다. K단위에서 기준이 1000/750으로
    오르며(방치형은 자동 행동 + 업그레이드로 지식을 더 버는 것을 전제) 같은 수동 모형의 기대 엔딩도 한 칸씩
    내려갔다(검수팀 실측 시드 20개: 1.5초 20 수석, 2.0초 17 무사, 2.5·3.0초 20 아슬아슬, 4.0초 17 아슬아슬 + 3 휴학).
    방치형 분포(기획서 2절 변경 메모)는 test_idle_final.py 에서 본다.
    (L단위) 등급이 졸업까지 걸린 시간으로 바뀐 뒤 검수팀 실측(시드 20개, 졸업 시각): 1.0초 20 수석(143~166초),
    1.5초 19 수석 + 1 무사(218~245초), 2.0초 20 무사(292~354초), 2.5초 19 아슬아슬 + 1 휴학,
    3.0초 17 아슬아슬 + 3 휴학, 4.0초 14 아슬아슬 + 6 휴학. 기대 엔딩은 K단위와 같다.
    (11절 A안, 수석 240 -> 200초) 1.5초 간격 졸업 시각 218~245초는 이제 무사라서, 수석 사례는
    1.0초 간격(143~166초)으로 옮기고 1.5초는 무사를 기대한다.
    """
    counts = {}
    for seed in BALANCE_SEEDS:
        g, _ = run(seed, interval)
        counts[g.ending] = counts.get(g.ending, 0) + 1
    assert counts.get(expected, 0) > len(BALANCE_SEEDS) // 2, (interval, counts)
    if interval == 4.0:
        # 4초 간격은 수석·무사가 거의 없고 아슬아슬 또는 휴학
        slow = counts.get(config.ENDING_BARELY, 0) + counts.get(config.ENDING_LEAVE, 0)
        assert slow >= len(BALANCE_SEEDS) - 2, counts
    assert None not in counts, counts   # (L단위) 상한(30분) 안에 모두 엔딩에 닿는다
    if interval <= 2.0:
        assert counts.get(config.ENDING_LEAVE, 0) == 0, counts
    if interval >= 2.5:
        # 수동 2.5초 이상은 수석에 못 미친다(기준이 오른 효과)
        assert counts.get(config.ENDING_TOP, 0) == 0, counts
    pygame.quit()


# ======================= 5. 가독성: 알림 2줄 =======================

def wrap(font, text, max_width):
    """검수팀 계산: 띄어쓰기 자리에서 max_width 이하 줄로 나눈다(줄 수 제한 없음)."""
    lines, cur = [], ""
    for word in text.split(" "):
        cand = word if not cur else cur + " " + word
        if cur and font.size(cand)[0] > max_width:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    lines.append(cur)
    return lines


def notice_box(g):
    """알림 상자(그림자 1칸 포함, 슬라이드 끝난 자리) 사각형."""
    icon = config.NOTICE_GOOD_ICON if g.notice["good"] else config.NOTICE_BAD_ICON
    icon_w, _ = sprite_size(icon, P)
    lines = wrap(g.notice_font, g.notice["text"], config.EVENT_NOTICE_TEXT_MAX_WIDTH)
    text_w = max(g.notice_font.size(line)[0] for line in lines)
    width = (config.BOX_INSET + config.EVENT_NOTICE_PAD + icon_w + config.EVENT_NOTICE_ICON_GAP
             + text_w + config.EVENT_NOTICE_PAD_RIGHT)
    box = pygame.Rect(config.EVENT_NOTICE_X, config.EVENT_NOTICE_Y, width,
                      config.EVENT_NOTICE_HEIGHT)
    return box.union(box.move(0, P))


@pytest.mark.parametrize("event", config.AUTO_EVENTS, ids=lambda e: e[config.EVENT_ID])
def test_notice_title_fits_two_lines(quiet_game, event):
    """자동형 제목 5종: 16px 로 최대 2줄, 각 줄 폭 <= 160, 상자 오른쪽 끝 <= 496."""
    g = quiet_game()
    assert g.notice_font.get_height() >= config.SMALL_FONT_SIZE
    lines = wrap(g.notice_font, event[config.EVENT_TITLE], config.EVENT_NOTICE_TEXT_MAX_WIDTH)
    assert 1 <= len(lines) <= 2, lines
    for line in lines:
        assert g.notice_font.size(line)[0] <= config.EVENT_NOTICE_TEXT_MAX_WIDTH, line
    assert g.wrap_text(g.notice_font, event[config.EVENT_TITLE],
                       config.EVENT_NOTICE_TEXT_MAX_WIDTH) == lines
    g.start_event(event)
    box = notice_box(g)
    assert box.right <= 496
    assert STAGE_INNER.contains(box)
    # 두 줄 높이(줄 간격 20 x 2)가 상자 안쪽 높이 안에 들어간다
    assert len(lines) * config.EVENT_NOTICE_LINE_HEIGHT <= config.EVENT_NOTICE_HEIGHT - 2 * P


@pytest.mark.parametrize("event", config.AUTO_EVENTS, ids=lambda e: e[config.EVENT_ID])
def test_notice_pixels_inside_box(quiet_game, event):
    """알림을 그렸을 때 바뀐 픽셀(아이콘·글자·상자)은 모두 계산한 상자 안이다."""
    g = quiet_game()
    g.student.elapsed = 5.0
    g.start_event(event)
    g.update(config.EVENT_NOTICE_SLIDE_TIME + 0.01)
    g.popups = []
    g.draw()
    with_notice = g.screen.copy()
    note = g.notice
    g.notice = None
    g.draw()
    without = g.screen.copy()
    g.notice = note
    box = notice_box(g)
    changed = []
    for y in range(STAGE_INNER.top, STAGE_INNER.bottom):
        for x in range(STAGE_INNER.left, STAGE_INNER.right):
            if with_notice.get_at((x, y)) != without.get_at((x, y)):
                changed.append((x, y))
    assert changed
    xs = [p[0] for p in changed]
    ys = [p[1] for p in changed]
    assert box.left <= min(xs) and max(xs) < box.right, (min(xs), max(xs), box)
    assert box.top <= min(ys) and max(ys) < box.bottom, (min(ys), max(ys), box)


# ======================= 6. 가독성: 알림·팝업·파티클 비겹침 =======================

def popup_rect(g, popup):
    surf = g.popup_font.render(popup["text"], False, (0, 0, 0))
    rect = surf.get_rect()
    rect.center = (popup["x"], round(popup["y"] - config.POPUP_RISE_SPEED * popup["age"]))
    glyph = surf.get_bounding_rect().move(rect.topleft)
    return glyph.unionall([glyph.move(dx, dy) for dx, dy in config.POPUP_OUTLINE_OFFSETS])


def particle_rect(g, p):
    age = p["age"]
    cell = P if age < p["life"] * config.PARTICLE_SHRINK_RATIO else P // 2
    w, h = sprite_size(p["sprite"], cell)
    left = g.snap_to_pixel(p["x"] + p["vx"] * age - w / 2)
    top = g.snap_to_pixel(p["y"] + p["vy"] * age - h / 2)
    return pygame.Rect(left, top, w, h)


def assert_no_overlap_frames(g, seconds, tag):
    t = 0.0
    while t < seconds:
        note = notice_box(g) if g.notice is not None else None
        pops = [(p, popup_rect(g, p)) for p in g.popups]
        parts = [particle_rect(g, p) for p in g.particles]
        for i, (p, r) in enumerate(pops):
            assert STAGE_INNER.contains(r), (tag, p["text"], r)
            if note is not None:
                assert not r.colliderect(note), (tag, p["text"], r, note)
            for pr in parts:
                assert not r.colliderect(pr), (tag, p["text"], r, pr)
            for q, r2 in pops[i + 1:]:
                assert not r.colliderect(r2), (tag, p["text"], q["text"])
        if note is not None:
            for pr in parts:
                assert not note.colliderect(pr), (tag, note, pr)
        g.update(1 / 60)
        t += 1 / 60


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
@pytest.mark.parametrize("event", config.AUTO_EVENTS, ids=lambda e: e[config.EVENT_ID])
def test_study_then_auto_event_no_overlap(quiet_game, grade, event):
    """공부(행동 팝업 3줄 + 파티클) 직후 자동형 알림 + 이벤트 팝업: 2초 동안 매 프레임 비겹침."""
    g = quiet_game()
    g.student.elapsed = GRADE_STARTS[grade - 1] + 5.0
    reach_grade(g.student, grade)   # (L단위) 학년은 지식으로 (아래에서 지식을 10으로 줄여도 학년은 그대로)
    g.student.health, g.student.mental, g.student.knowledge = 60, 60, 10
    assert g.do_action(STUDY)
    g.start_event(event)
    ev_pops = [p for p in g.popups if p["x"] == config.EVENT_POPUP_X]
    assert ev_pops
    assert min(p["y"] for p in ev_pops) == 212
    assert_no_overlap_frames(g, config.EVENT_NOTICE_TIME, (grade, event[config.EVENT_ID]))


@pytest.mark.parametrize("grade", [1, 4])
def test_choice_result_under_notice_no_overlap(quiet_game, grade):
    """알림이 떠 있을 때 선택 결과(3줄: 교환학생 첫 선택지 등) 팝업도 212부터 쌓이고 비겹침·무대 안."""
    g = quiet_game()
    g.student.elapsed = GRADE_STARTS[grade - 1] + 5.0
    reach_grade(g.student, grade)   # (L단위) 학년은 지식으로 (아래에서 지식을 10으로 줄여도 학년은 그대로)
    g.student.health, g.student.mental, g.student.knowledge = 60, 60, 10
    assert g.do_action(STUDY)
    g.start_event(event_by_id("professor_praise"))
    g.update(0.5)
    # (G단위) 쿨타임이 없어져 g.cooldown = 0 으로 풀어 줄 필요가 없다
    assert g.do_action(STUDY)
    event = max(config.CHOICE_EVENTS,
                key=lambda e: len(e[config.EVENT_OPTIONS][0][config.OPTION_EFFECTS]))
    g.start_event(event)
    g.update(config.EVENT_INPUT_DELAY)
    n = len(g.popups)
    assert g.choose_option(config.CHOICE_FIRST)
    new = g.popups[n:]
    assert new and all(p["x"] == config.EVENT_POPUP_X for p in new)
    assert min(p["y"] for p in new) == 212
    assert_no_overlap_frames(g, 1.0, grade)


# ======================= 7. 가독성: 멈춤 점무늬 =======================

def dotted_and_plain(g, monkeypatch):
    g.draw()
    dotted = g.screen.copy()
    real = g.draw_pause_dots
    monkeypatch.setattr(g, "draw_pause_dots", lambda: None)
    g.draw()
    plain = g.screen.copy()
    monkeypatch.setattr(g, "draw_pause_dots", real)
    return dotted, plain


@pytest.mark.parametrize("step", [P * 2, P * 3, P * 4])
def test_pause_dots_never_cover_dialog_any_density(quiet_game, monkeypatch, step):
    """점 간격(밀도)이 바뀌어도 대화창(그림자 포함) 안은 점무늬가 없고, 바깥은 점 색으로만 바뀐다."""
    monkeypatch.setattr(config, "PAUSE_DOT_STEP", step)
    g = quiet_game()
    g.student.elapsed = 5.0
    g.start_event(event_by_id("mt_invite"))
    g.update(config.EVENT_INPUT_DELAY)
    dotted, plain = dotted_and_plain(g, monkeypatch)
    a = pygame.image.tobytes(dotted.subsurface(DIALOG_WITH_DROP).copy(), "RGB")
    b = pygame.image.tobytes(plain.subsurface(DIALOG_WITH_DROP).copy(), "RGB")
    assert a == b
    diff = 0
    for y in range(config.SCREEN_HEIGHT):
        for x in range(0, config.SCREEN_WIDTH):
            if dotted.get_at((x, y)) != plain.get_at((x, y)):
                assert color(dotted, x, y) == tuple(config.COLOR_PAUSE_DOT)
                diff += 1
    assert diff > 0


def test_pause_dots_lighter_at_step_12(quiet_game, monkeypatch):
    """점 1칸 + 빈칸 2칸: 화면에서 점이 차지하는 비율이 1/9 정도(예전 2칸 간격 1/4 보다 옅다)."""
    g = quiet_game()
    g.student.elapsed = 5.0
    g.start_event(event_by_id("mt_invite"))
    g.update(config.EVENT_INPUT_DELAY)
    surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    surf.fill((1, 2, 3))
    g.screen = surf
    g.draw_pause_dots()
    dots = sum(1 for y in range(config.SCREEN_HEIGHT) for x in range(config.SCREEN_WIDTH)
               if color(surf, x, y) == tuple(config.COLOR_PAUSE_DOT))
    ratio = dots / (config.SCREEN_WIDTH * config.SCREEN_HEIGHT)
    assert 0.09 < ratio < 0.13, ratio


def test_pause_dots_only_in_dialog_state(quiet_game, monkeypatch):
    g = quiet_game()
    g.student.elapsed = 5.0
    calls = []
    real = g.draw_pause_dots
    monkeypatch.setattr(g, "draw_pause_dots", lambda: (calls.append(g.state), real()))
    g.draw()
    g.start_event(event_by_id("professor_praise"))     # 자동형: 정지 아님
    g.draw()
    assert calls == []
    g.start_event(event_by_id("mt_invite"))
    g.draw()
    assert calls == [config.STATE_EVENT]
    g.update(config.EVENT_INPUT_DELAY)
    g.choose_option(config.CHOICE_FIRST)
    g.draw()
    g.end_game(config.ENDING_LEAVE)
    g.draw()
    g.state = config.STATE_TITLE
    g.draw()
    assert calls == [config.STATE_EVENT]


# ======================= 8. 가독성: 하트 핀·미리보기 색 =======================

def look_cells(look):
    (col, row), grid = config.LOOK_SPRITES[look]
    return {(col + c, row + r) for r, line in enumerate(grid) for c, ch in enumerate(line)
            if ch != "."}


def test_heart_pin_position_and_spacing():
    """하트 핀은 (-3, 2) 시작 5x5, 다른 외형 칸과 겹치지 않고 선글라스와 1칸 이상 띄어져 있다."""
    (col, row), grid = config.LOOK_SPRITES[config.LOOK_HEART_PIN]
    assert (col, row) == (-3, 2)
    assert len(grid) == 5 and all(len(line) == 5 for line in grid)
    pin = look_cells(config.LOOK_HEART_PIN)
    for look in config.LOOK_IDS:
        if look == config.LOOK_HEART_PIN:
            continue
        assert not (pin & look_cells(look)), look
    sun = look_cells(config.LOOK_SUNGLASSES)
    gap = min(max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a in pin for b in sun)
    assert gap >= 2, gap   # 사이에 빈 칸이 최소 1칸


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
def test_heart_pin_visible_with_all_looks(grade):
    """외형 5종을 모두 가져도 하트 핀 색 픽셀이 보이고 무대 안이다(1학년 포함)."""
    pygame.init()
    s = Student()
    s.elapsed = GRADE_STARTS[grade - 1] + 1.0
    reach_grade(s, grade)   # (L단위) 학년은 지식으로
    base = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    base.fill(config.COLOR_BG)
    others = [lk for lk in config.LOOK_IDS if lk != config.LOOK_HEART_PIN]
    s.looks = list(others)
    s.draw(base)
    full = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    full.fill(config.COLOR_BG)
    s.looks = list(config.LOOK_IDS)
    s.draw(full)
    diff = [(x, y) for y in range(config.SCREEN_HEIGHT) for x in range(config.SCREEN_WIDTH)
            if base.get_at((x, y)) != full.get_at((x, y))]
    assert diff
    assert all(STAGE_INNER.collidepoint(p) for p in diff)
    pygame.quit()


def contrast(a, b):
    def lum(c):
        def ch(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, g, b_ = (ch(v) for v in c[:3])
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_preview_other_color_darker_than_soft_text():
    """미리보기 특성·외형 글자색이 예전(COLOR_TEXT_SOFT)보다 크림 바탕 대비가 크다(4.5:1 이상)."""
    new = contrast(config.COLOR_PREVIEW_OTHER, config.COLOR_BG)
    old = contrast(config.COLOR_TEXT_SOFT, config.COLOR_BG)
    assert new > old
    assert new >= 4.5, new


# ======================= 9. 문서 일치 =======================

def test_spec_section2_table_1000_750():
    """(문서 정리) 기획서 2절 졸업 등급 표는 최종 규칙(걸린 시간 200/360초)만 적는다.

    예전 기준(지식 500/300 -> 700/450 -> 1000/750)은 본문 규칙 절에 남지 않고
    부록 변경 이력에만 기록으로 남는다. 이벤트 최소 간격 8초는 4절 발생 규칙에 있다.
    (이름은 E단위·K단위 때 그대로 둔다)
    """
    text = read_doc()
    grades = doc_section(doc_section(text, "게임 규칙"), "졸업 등급과 졸업 보너스")
    assert "| 수석 졸업 | 200초 이하 | +200 |" in grades
    assert "| 무사 졸업 | 200초 초과 360초 이하 | +100 |" in grades
    assert "| 아슬아슬 졸업 | 360초 초과 | +50 |" in grades
    rules = spec_rule_text(text)
    assert not re.search(r"\|\s*(500 이상|300~499|300 미만|700 이상|450~699|450 미만|"
                         r"1000 이상|750~999|750 미만)\s*\|", rules)
    assert "1000/750" not in rules and "700/450" not in rules
    history = spec_appendix(text)
    assert "수석 500 / 무사 300" in history          # 원본 PDF
    assert "졸업 기준 700 / 450" in history          # 이벤트 도입(E단위)
    assert "졸업 기준 1000 / 750" in history         # 방치형 밸런스(K단위)
    assert "최소 간격 8초" in history
    occur = doc_section(text, "발생 규칙")
    assert "**8초 이상**" in occur and "최소 간격" in occur
    assert config.EVENT_MIN_GAP == 8.0


def test_jeja_spec_section5_1000_750():
    """(문서 정리) jeja-spec 졸업 등급은 걸린 시간 기준과 경계값만 적고, 예전 지식 기준은 없다.

    (이름은 K단위 때 그대로 둔다) 이벤트 최소 간격 EVENT_MIN_GAP 8.0초는 4절 표에 있다.
    """
    text = read_doc(JEJA_SPEC_PATH)
    grades = doc_section(doc_section(text, "게임 규칙"), "졸업 등급")
    assert "≤ 200초 (`TOP_GRADUATE_SECONDS`)" in grades
    assert "200초 초과 ≤ 360초 (`NORMAL_GRADUATE_SECONDS`)" in grades
    assert "360초 초과" in grades
    for boundary in ("200 → 수석", "200.0001 → 무사", "360 → 무사", "360.0001 → 아슬아슬"):
        assert boundary in grades, boundary
    for old in ("누적 지식 ≥ 1000", "750 ≤ 지식 ≤ 999", "지식 < 750", "1000 → 수석",
                "500 이상", "700 이상"):
        assert old not in text, old
    events = doc_section(text, "랜덤 이벤트와 성장 요소")
    assert "`EVENT_MIN_GAP`" in events and "8.0초" in events


def test_readme_has_no_older_ending_criteria():
    """README 에 E단위 이전 기준(500/300, 700/450)이 남아 있지 않다.

    (L단위) README 가 1000/750 을 말해야 한다는 검사는 기획서 11절로 그 규칙이 없어져 뺐다.
    새 규칙 문구는 test_final.py::test_readme_describes_no_time_limit 에서 본다.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "500 이상" not in text and "300~499" not in text
    assert "700 이상" not in text and "450~699" not in text and "449/450/699/700" not in text


def test_config_and_game_code_use_constants():
    """엔딩 판정 코드(docstring 제외)에 500/300/700/450/1000/750 숫자를 직접 쓰지 않는다(config 상수만)."""
    import ast
    for name in ("student.py", "game.py"):
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        nums = {n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
                and not isinstance(n.value, bool)}
        # (L단위) 진급 목표·졸업 지식·졸업 시간 숫자도 config 상수로만 쓴다
        old_and_new = {500, 300, 700, 450, 1000, 750, 200, 1100, 240, 360, 400, 1500, 2000}
        assert not nums & old_and_new, (name, nums & old_and_new)
    assert game_module.config.TOP_GRADUATE_SECONDS == 200



def test_code_docstrings_mention_new_ending_criteria():
    """student.py·game.py 의 설명(docstring·주석)에 옛 엔딩 기준 500/300 이 남아 있지 않다."""
    for name in ("student.py", "game.py"):
        src = (ROOT / name).read_text(encoding="utf-8")
        assert "500 이상" not in src and "300~499" not in src and "300 미만" not in src, name
