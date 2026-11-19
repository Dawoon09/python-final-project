"""검수 단위 E: 밸런스·가독성 조정 + 엔딩 기준 변경 (기획서 2절·9절, jeja-spec 5절·14절).

이 파일에는 conftest 의 no_events 가 적용되지 않는다(이벤트가 켜진 상태). 모든 Game 은 seed 고정.

- (a) 확률 이벤트 최소 간격 EVENT_MIN_GAP(8초): 경계 7.99/8.0, 보장 예외, 학년 넘어 이어 셈,
      대화 정지 시간 미포함, 새 판 초기화, 간격 미충족 시 rng 를 뽑지 않음(결정성)
- 최소 4·최대 5 보장 유지(시드 여러 개 x 간격 1~3초 완주) + 완주 중 간격 규칙 위반 0
- (b) 엔딩 기준 700/450: judge_ending 경계 449/450/699/700, 실제 게임 흐름(이벤트로 경계를 넘는 경우 포함)
- 이벤트 켠 밸런스(시드 20개): 1.5~2.0초 수석, 2.5~3.0초 무사, 4.0초 아슬아슬(+휴학)이 과반
- (c) 가독성: 알림 2줄 나눔·상자 안, 알림·이벤트 팝업·행동 팝업·파티클 비겹침(4학년 포함),
      점무늬(대화 상태에서만, 대화창 안 미덮음, 밀도 무관), 하트 핀 위치, 미리보기 글자 대비
- 문서 일치: 기획서 2절 표·jeja-spec 5절·README·config 가 700/450
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
from conftest import press  # noqa: E402
from game import Game, sprite_size  # noqa: E402
from student import Student, judge_ending  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = config.PIXEL_SIZE
FEED, REST, STUDY = config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY
H, M, K = config.GAUGE_HEALTH, config.GAUGE_MENTAL, config.GAUGE_KNOWLEDGE
GAP = config.EVENT_MIN_GAP
TOP, NORMAL = config.TOP_GRADUATE_KNOWLEDGE, config.NORMAL_GRADUATE_KNOWLEDGE
GRADE_STARTS = [0.0, 60.0, 120.0, 180.0]
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
    """제자의 게임 시각·그 학년 이벤트 수·직전 이벤트 시각을 맞춘다. 쿨타임은 푼다."""
    s = g.student
    s.elapsed = elapsed
    if count is not None:
        s.event_counts[s.get_grade()] = count
    s.last_event_time = last
    s.health = s.mental = 80
    g.cooldown = 0


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
    assert (config.TOP_GRADUATE_KNOWLEDGE, config.NORMAL_GRADUATE_KNOWLEDGE) == (700, 450)
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
    assert g.student.event_counts[1] == (5 if fires else 4)
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


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
@pytest.mark.parametrize("k", [1, 4])
def test_guarantee_ignores_gap(make_game, monkeypatch, grade, k):
    """보장 경로는 직전 이벤트가 0.25초 전이어도(확률 0) 뜬다."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 0.0)
    g = make_game(3)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    t = GRADE_STARTS[grade - 1] + config.EVENT_GUARANTEE_INTERVAL * k
    set_time(g, t, count=k - 1, last=t - 0.25)
    assert g.student.needs_guaranteed_event()
    assert not g.student.is_event_gap_passed()
    assert g.do_action(FEED)
    assert g.student.event_counts[grade] == k
    assert g.student.last_event_time == t


def test_guaranteed_event_also_restarts_gap(make_game, monkeypatch):
    """보장으로 뜬 이벤트도 직전 이벤트 시각으로 기록되어, 그 뒤 확률 경로는 8초를 기다린다."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g = make_game(4)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    set_time(g, config.EVENT_GUARANTEE_INTERVAL, count=0, last=None)
    g.student.last_event_time = config.EVENT_GUARANTEE_INTERVAL - 1.0
    assert g.do_action(FEED)                         # 보장
    assert g.student.event_counts[1] == 1
    g.update(GAP - 0.5)
    g.student.health = g.student.mental = 80
    assert g.do_action(FEED)                         # 7.5초 뒤: 확률 1 이어도 없음
    assert g.student.event_counts[1] == 1
    g.update(0.5)
    g.student.health = g.student.mental = 80
    g.cooldown = 0
    assert g.do_action(FEED)                         # 8.0초 뒤: 뜸
    assert g.student.event_counts[1] == 2


@pytest.mark.parametrize("gap, fires", [(5.99, False), (7.99, False), (8.0, True)])
def test_gap_continues_across_grades(make_game, monkeypatch, gap, fires):
    """1학년 58초에 이벤트 -> 2학년(학년 안 경과 < 11.25, 보장 없음)에서도 이어서 센다."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g = make_game(5)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    set_time(g, 58.0, count=4, last=None)
    assert g.do_action(FEED)
    assert g.student.event_counts[1] == 5 and g.student.last_event_time == 58.0
    set_time(g, 58.0 + gap, last=58.0)
    assert g.student.get_grade() == 2 and g.student.event_counts[2] == 0
    assert not g.student.needs_guaranteed_event()
    assert g.do_action(FEED)
    assert g.student.event_counts[2] == (1 if fires else 0)


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
    assert g.student.event_counts[1] == 1                 # 간격 미충족 -> 없음
    g.update(0.5)
    g.student.health = g.student.mental = 80
    g.cooldown = 0
    assert g.student.is_event_gap_passed()
    assert g.do_action(FEED)
    assert g.student.event_counts[1] == 2


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
    assert g.student.event_counts == {1: 0, 2: 0, 3: 0, 4: 0}
    # 새 판 첫 행동은 간격 제한이 없다(확률 1 -> 뜸)
    assert g.do_action(FEED)
    assert g.student.event_counts[1] == 1


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
            g.cooldown = 0
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
    while g.state in (config.STATE_PLAYING, config.STATE_EVENT):
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
        if wait <= 1e-9 and not g.is_cooling_down():
            action = policy(g.student)
            if action is not None:
                assert g.do_action(action)
            wait = interval
        if g.state != config.STATE_PLAYING:
            continue
        g.update(DT)
        wait -= DT
        steps += 1
        assert steps <= config.TOTAL_SECONDS / DT + 10
    return g, log


@pytest.mark.parametrize("interval", [1.0, 1.5, 2.0, 2.5, 3.0])
def test_full_runs_keep_4_to_5_per_grade_and_gap_rule(interval):
    """시드 8개 x 간격: 완주한 학년마다 이벤트 4~5회, 확률 이벤트는 모두 직전 이벤트 후 8초 이상."""
    for seed in range(8):
        g, log = run(seed, interval)
        s = g.student
        completed = int(s.elapsed // config.SECONDS_PER_GRADE)
        for grade in config.ALL_GRADES:
            assert s.event_counts[grade] <= config.EVENT_MAX_PER_GRADE
            if grade <= completed:
                assert config.EVENT_MIN_PER_GRADE <= s.event_counts[grade], \
                    (seed, interval, s.event_counts)
        for elapsed, guaranteed, last, _ in log:
            if not guaranteed and last is not None:
                assert elapsed - last >= GAP - 1e-6, (seed, interval, elapsed, last)
        times = [e[0] for e in log]
        assert times == sorted(times)
    pygame.quit()


def test_gap_reduces_chance_events():
    """간격 규칙 때문에 확률 이벤트끼리 8초 안에 붙어 나오는 경우가 없고, 한 판 총수가 4x4~4x5."""
    totals = []
    for seed in range(6):
        g, log = run(seed, 1.0)
        chance = [e for e in log if not e[1]]
        for a, b in zip(log, log[1:]):
            if not b[1]:
                assert b[0] - a[0] >= GAP - 1e-6
        totals.append(len(log))
        assert len(chance) <= len(log)
    assert all(16 <= t <= 20 for t in totals), totals
    pygame.quit()


# ======================= 3. 엔딩 기준 700/450 =======================

@pytest.mark.parametrize("knowledge, ending", [
    (0, config.ENDING_BARELY), (449, config.ENDING_BARELY), (450, config.ENDING_NORMAL),
    (699, config.ENDING_NORMAL), (700, config.ENDING_TOP), (5000, config.ENDING_TOP),
])
def test_judge_ending_700_450(knowledge, ending):
    assert judge_ending(knowledge) == ending
    s = Student()
    s.knowledge = knowledge
    assert s.get_graduation_ending() == ending


@pytest.mark.parametrize("knowledge, ending", [
    (449, config.ENDING_BARELY), (450, config.ENDING_NORMAL),
    (699, config.ENDING_NORMAL), (700, config.ENDING_TOP),
])
def test_graduation_flow_boundaries_events_on(make_game, knowledge, ending):
    """이벤트 켠 실제 흐름: 행동 없이 240초까지 update -> 경계값대로 엔딩, 기록 저장."""
    g = make_game(12)
    s = g.student
    s.elapsed, s.health, s.mental, s.knowledge = 238.0, 100, 100, knowledge
    for _ in range(int(2.0 / DT) + 1):
        g.update(DT)
    assert g.state == config.STATE_ENDING
    assert g.ending == ending
    assert g.best_record == knowledge


@pytest.mark.parametrize("start, ending", [(434, config.ENDING_BARELY), (435, config.ENDING_NORMAL),
                                           (684, config.ENDING_NORMAL), (685, config.ENDING_TOP)])
def test_event_knowledge_crosses_boundary_before_graduation(make_game, monkeypatch, start, ending):
    """마지막 몇 초에 학식 + 자동형 '교수님께 칭찬'(지식 +15)으로 경계를 넘거나 못 넘는다."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g = make_game(13)
    monkeypatch.setattr(g, "pick_event", lambda: event_by_id("professor_praise"))
    set_time(g, 238.5, count=4, last=None)
    g.student.knowledge = start
    assert g.do_action(FEED)
    assert g.student.knowledge == start + 15
    while g.state == config.STATE_PLAYING:
        g.update(DT)
    assert g.ending == ending


# ======================= 4. 이벤트 켠 밸런스 (시드 20개) =======================

BALANCE_SEEDS = range(20)


@pytest.mark.parametrize("interval, expected", [
    (1.5, config.ENDING_TOP),
    (2.0, config.ENDING_TOP),
    (2.5, config.ENDING_NORMAL),
    (3.0, config.ENDING_NORMAL),
    (4.0, config.ENDING_BARELY),
])
def test_balance_with_events(interval, expected):
    """사람처럼 interval 초마다 탐욕 행동(선택은 시드별 3전략 순환): 기대 엔딩이 과반.

    개발팀 표(2.0초 99% 수석, 2.5초 90% 무사, 3.0초 94% 무사, 4.0초 88% 아슬아슬)와 대략 일치하는지 본다.
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
    if interval <= 2.0:
        assert counts.get(config.ENDING_LEAVE, 0) == 0, counts
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
    g.student.health, g.student.mental, g.student.knowledge = 60, 60, 10
    assert g.do_action(STUDY)
    g.start_event(event_by_id("professor_praise"))
    g.update(0.5)
    g.cooldown = 0
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

def test_spec_section2_table_700_450():
    text = (ROOT / "docs" / "기획서.md").read_text(encoding="utf-8")
    sec2 = text.split("## 2.")[1].split("## 3.")[0]
    assert "| 수석 졸업 | 700 이상 |" in sec2
    assert "| 무사 졸업 | 450~699 |" in sec2
    assert "| 아슬아슬 졸업 | 450 미만 |" in sec2
    assert not re.search(r"\|\s*(500 이상|300~499|300 미만)\s*\|", sec2)
    sec9 = text.split("## 9.")[1]
    assert "700/450" in sec9
    assert "8초" in sec9 and "최소 간격" in sec9


def test_jeja_spec_section5_700_450():
    text = (ROOT / ".claude" / "skills" / "jeja-spec" / "SKILL.md").read_text(encoding="utf-8")
    sec5 = text.split("## 5.")[1].split("## 6.")[0]
    assert "누적 지식 ≥ 700" in sec5
    assert "450 ≤ 지식 ≤ 699" in sec5
    assert "지식 < 450" in sec5
    assert "449 → 아슬아슬, 450 → 무사, 699 → 무사, 700 → 수석" in sec5
    assert "500" not in sec5.split("(2026")[0].replace("≥ 700", "")
    sec14 = text.split("## 14.")[1]
    assert "EVENT_MIN_GAP" in sec14 and "8.0초" in sec14


def test_readme_700_450():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "수석 졸업(700 이상) / 무사 졸업(450~699) / 아슬아슬 졸업(450 미만)" in text
    assert "449/450/699/700" in text
    assert "500 이상" not in text and "300~499" not in text


def test_config_and_game_code_use_constants():
    """엔딩 판정 코드(docstring 제외)에 500/300/700/450 숫자를 직접 쓰지 않는다(config 상수만)."""
    import ast
    for name in ("student.py", "game.py"):
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        nums = {n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
                and not isinstance(n.value, bool)}
        assert not nums & {500, 300, 700, 450}, (name, nums & {500, 300, 700, 450})
    assert game_module.config.TOP_GRADUATE_KNOWLEDGE == 700


def test_code_docstrings_mention_new_ending_criteria():
    """student.py·game.py 의 설명(docstring·주석)에 옛 엔딩 기준 500/300 이 남아 있지 않다."""
    for name in ("student.py", "game.py"):
        src = (ROOT / name).read_text(encoding="utf-8")
        assert "500 이상" not in src and "300~499" not in src and "300 미만" not in src, name
