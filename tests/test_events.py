"""검수 단위 C: 랜덤 이벤트와 성장 (기획서 9절, jeja-spec 14절) — 로직.

이 파일에는 conftest 의 no_events 픽스처가 적용되지 않는다(이벤트가 켜진 상태).
모든 Game 은 seed 를 고정해서 만든다(결정적).

- 데이터: 9절 표 <-> config (자동형 5, 선택지형 10, 특성 보정 표)
- 발생 규칙: 쿨타임 무시·휴학엔 없음, 확률 경로, 최소 보장 경계, 최대 5, 한 판 1회, 학년·연계 조건
- 대화 상태: 정지, 입력 무시, 키/클릭 선택, 결과 적용, 휴학 판정, 재개, ESC
- 자동형: 즉시 효과, 알림 2초, 휴학
- 특성 보정, clamp, 시험 기간 지식 규칙
- 초기화, 결정성, 분포 시뮬레이션

(L단위, 기획서 11절) 이벤트 최소 보장·최대 5회는 학년이 아니라 60초 주기마다 센다
(event_counts 키 = 주기 번호, 처음엔 빈 사전). 선택지형의 학년 조건은 지식으로 오른 지금 학년이다.
"""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
from conftest import press, reach_grade  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402

H, M, K = config.GAUGE_HEALTH, config.GAUGE_MENTAL, config.GAUGE_KNOWLEDGE
FEED, REST, STUDY = config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY


# ======================= 공통 도우미 =======================

@pytest.fixture
def make_game():
    """seed 를 받아 타이틀에서 Enter 를 눌러 게임 진행 중인 Game 을 만든다."""
    games = []

    def factory(seed=0):
        g = Game(seed=seed)
        press(g, pygame.K_RETURN)
        assert g.state == config.STATE_PLAYING
        games.append(g)
        return g

    yield factory
    pygame.quit()


def event_by_id(event_id):
    for event in config.ALL_EVENTS:
        if event[config.EVENT_ID] == event_id:
            return event
    raise KeyError(event_id)


def event_by_title(title):
    for event in config.ALL_EVENTS:
        if event[config.EVENT_TITLE] == title:
            return event
    raise KeyError(title)


def click(g, pos):
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=pygame.BUTTON_LEFT, pos=pos))


def force_event(monkeypatch, g, event):
    """다음 do_action 에서 반드시 event 가 뜨게 한다(확률 1, pick_event 고정)."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    monkeypatch.setattr(g, "pick_event", lambda: event)


def pass_input_delay(g):
    """(D 단위) 대화창 입력 대기(EVENT_INPUT_DELAY, 0.3초)를 지나게 한다.

    대화 상태에서는 게임 시간·게이지·쿨타임이 멈춰 있으므로 대화창 시계만 흐른다.
    """
    g.update(config.EVENT_INPUT_DELAY)
    assert g.is_dialog_ready()


def gauges(g):
    s = g.student
    return (s.health, s.mental, s.knowledge)


def count(g, cycle=1):
    """(L단위) cycle번 60초 주기에 나온 이벤트 수(없는 주기는 0)."""
    return g.student.event_counts.get(cycle, 0)


def popup_texts(g):
    return [p["text"] for p in g.popups]


def texts_top_down(popups):
    """팝업 글자를 화면 위에서 아래 순서로(체력, 멘탈, 지식 순으로 쌓인다)."""
    return [p["text"] for p in sorted(popups, key=lambda p: p["y"])]


# ======================= 1. 데이터: 기획서 9절 표 <-> config =======================

def test_rule_constants():
    assert config.EVENT_CHANCE == 0.25
    assert config.EVENT_GUARANTEE_INTERVAL == 11.25
    assert config.EVENT_MIN_PER_GRADE == 4
    assert config.EVENT_MAX_PER_GRADE == 5
    assert config.EVENT_CHOICE_RATIO == 0.5
    assert config.EVENT_NOTICE_TIME == 2.0
    # 4구간 x 11.25 = 시험 기간 시작(45초)
    assert config.EVENT_GUARANTEE_INTERVAL * config.EVENT_MIN_PER_GRADE == \
        config.CYCLE_SECONDS - config.EXAM_SECONDS   # (L단위) 학년 60초 -> 60초 주기


SPEC_AUTO = {
    "엄마가 반찬을 보내셨다": {H: 15},
    "단톡방에서 칭찬받았다": {M: 10},
    "과제 마감 알림이 울렸다": {M: -10},
    "감기 기운이 돈다": {H: -10},
    "교수님께 칭찬받았다": {K: 15, M: 5},
}


def test_auto_events_match_spec():
    assert len(config.AUTO_EVENTS) == 5
    got = {e[config.EVENT_TITLE]: e[config.EVENT_EFFECTS] for e in config.AUTO_EVENTS}
    assert got == SPEC_AUTO
    for e in config.AUTO_EVENTS:
        assert e[config.EVENT_KIND] == config.EVENT_KIND_AUTO
        assert sorted(e[config.EVENT_GRADES]) == [1, 2, 3, 4]
        assert e[config.EVENT_REQUIRES] is None


# (학년, 필요 플래그, 제목, [(선택 글자, 효과, 특성, 외형, 플래그) x 2])
SPEC_CHOICE = [
    ([1], None, "MT 초대", [
        ("간다", {M: 15, H: -10}, None, None, "MT 참석"),
        ("공부한다", {K: 10, M: -5}, None, None, None)]),
    ([1], None, "동아리 박람회", [
        ("밴드부", {}, "음악 힐링", config.LOOK_GUITAR, "밴드부"),
        ("헬스부", {}, "체력 단련", config.LOOK_HEADBAND, None)]),
    ([2], None, "조별과제 무임승차자", [
        ("혼자 다 한다", {K: 20, H: -15, M: -10}, None, None, None),
        ("교수님께 말한다", {M: 5}, None, None, None)]),
    ([2], None, "밤샘의 유혹", [
        ("커피로 버틴다", {K: 10}, "카페인", config.LOOK_COFFEE, None),
        ("그냥 잔다", {H: 10}, None, None, None)]),
    ([3], None, "고백을 받았다", [
        ("사귄다", {M: 15}, "연애 중", config.LOOK_HEART_PIN, "연애 중"),
        ("공부에 집중", {K: 20, M: -10}, None, None, None)]),
    ([3], None, "교환학생 공고", [
        ("지원한다", {K: 25, H: -10}, None, None, None),
        ("다음에", {M: 5}, None, None, None)]),
    ([4], None, "취업 박람회", [
        ("대기업 지원", {K: 20, M: -15}, None, None, None),
        ("대학원 상담", {K: 10, M: 5}, None, None, None)]),
    ([2, 3, 4], "MT 참석", "선배가 족보를 준다", [
        ("받는다", {K: 15}, None, None, None),
        ("거절한다", {M: 5}, None, None, None)]),
    ([3, 4], "밴드부", "축제 무대 제안", [
        ("무대에 선다", {M: 25, H: -10}, None, config.LOOK_SUNGLASSES, None),
        ("연습만 한다", {M: 5}, None, None, None)]),
    ([4], "연애 중", "졸업 전 데이트", [
        ("데이트한다", {M: 20, H: -5}, None, None, None),
        ("도서관에 간다", {K: 15}, None, None, None)]),
]


@pytest.mark.parametrize("grades, requires, title, options", SPEC_CHOICE,
                         ids=[row[2] for row in SPEC_CHOICE])
def test_choice_event_matches_spec(grades, requires, title, options):
    e = event_by_title(title)
    assert e[config.EVENT_KIND] == config.EVENT_KIND_CHOICE
    assert sorted(e[config.EVENT_GRADES]) == grades
    assert e[config.EVENT_REQUIRES] == requires
    assert isinstance(e[config.EVENT_TEXT], str) and e[config.EVENT_TEXT].strip()
    assert len(e[config.EVENT_OPTIONS]) == 2
    for opt, (text, effects, trait, look, flag) in zip(e[config.EVENT_OPTIONS], options):
        assert opt[config.OPTION_TEXT] == text
        assert opt[config.OPTION_EFFECTS] == effects
        assert opt[config.OPTION_TRAIT] == trait
        assert opt[config.OPTION_LOOK] == look
        assert opt[config.OPTION_FLAG] == flag


def test_choice_event_list_complete_and_ids_unique():
    assert len(config.CHOICE_EVENTS) == 10
    assert sorted(e[config.EVENT_TITLE] for e in config.CHOICE_EVENTS) == \
        sorted(row[2] for row in SPEC_CHOICE)
    ids = [e[config.EVENT_ID] for e in config.ALL_EVENTS]
    assert len(ids) == len(set(ids)) == 15
    assert config.ALL_EVENTS == config.AUTO_EVENTS + config.CHOICE_EVENTS


def test_trait_and_look_and_flag_names():
    assert config.TRAIT_FITNESS == "체력 단련"
    assert config.TRAIT_MUSIC == "음악 힐링"
    assert config.TRAIT_CAFFEINE == "카페인"
    assert config.TRAIT_LOVE == "연애 중"
    assert len(config.LOOK_IDS) == len(set(config.LOOK_IDS)) == 5
    assert (config.FLAG_MT, config.FLAG_BAND, config.FLAG_LOVE) == ("MT 참석", "밴드부", "연애 중")
    # 표의 외형·특성은 모두 정의된 것만 쓴다
    for e in config.CHOICE_EVENTS:
        for opt in e[config.EVENT_OPTIONS]:
            assert opt[config.OPTION_LOOK] in config.LOOK_IDS + [None]
            assert opt[config.OPTION_TRAIT] in list(config.TRAIT_BONUSES) + [None]
            assert set(opt[config.OPTION_EFFECTS]) <= {H, M, K}


def test_trait_bonus_table():
    assert config.TRAIT_BONUSES == {
        "체력 단련": {config.BONUS_FEED_HEALTH: 5},
        "음악 힐링": {config.BONUS_REST_MENTAL: 5},
        "카페인": {config.BONUS_STUDY_HEALTH: 2},
        "연애 중": {config.BONUS_REST_HEALTH: 5},
    }
    assert config.REST_HEALTH == 0
    # 기본 행동 수치 불변
    assert (config.FEED_HEALTH, config.REST_MENTAL, config.REST_KNOWLEDGE) == (20, 20, -2)
    assert (config.STUDY_HEALTH, config.STUDY_MENTAL) == (-5, -8)
    assert (config.STUDY_KNOWLEDGE, config.STUDY_KNOWLEDGE_EXAM) == (10, 20)
    # 졸업 기준: E단위 700/450, K단위 1000/750 (지식) -> L단위 걸린 시간 240/360초, 졸업 지식 1100
    assert (config.TOP_GRADUATE_SECONDS, config.NORMAL_GRADUATE_SECONDS) == (240, 360)
    assert config.GRADUATION_KNOWLEDGE == 1100


# ======================= 2. 발생 규칙 =======================

def test_new_game_has_no_event_state(make_game):
    g = make_game(1)
    assert g.current_event is None and g.notice is None
    s = g.student
    assert s.traits == [] and s.looks == [] and s.flags == set() and s.seen_events == set()
    assert s.event_counts == {}   # (L단위) 주기 번호별로 센다. 처음엔 비어 있다


def test_policy_input_rolls_no_event(make_game, monkeypatch):
    """(G단위, 예전: 쿨타임 중 무시된 입력은 이벤트 판정 없음) 방침 키·방침 버튼은 행동이 아니므로
    이벤트를 판정하지 않는다. 행동(do_action)이 실행된 직후에만 판정한다."""
    g = make_game(2)
    monkeypatch.setattr(config, "EVENT_CHANCE", 0.0)
    assert g.do_action(FEED)
    calls = []
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    monkeypatch.setattr(g, "roll_event", lambda: calls.append(1))
    press(g, pygame.K_3)
    click(g, g.buttons[config.POLICY_STUDY_FOCUS].rect.center)
    assert g.policy == config.POLICY_STUDY_FOCUS
    assert calls == []
    assert sum(g.student.event_counts.values()) == 0
    assert g.do_action(STUDY) is True      # 쿨타임 없음: 바로 실행되고 판정 1번
    assert calls == [1]


def test_action_that_causes_leave_rolls_no_event(make_game, monkeypatch):
    g = make_game(3)
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g.student.health = 5
    g.student.elapsed = 50.0   # 보장 조건도 걸려 있는 시각
    assert g.student.needs_guaranteed_event()
    assert g.do_action(STUDY)
    assert g.state == config.STATE_ENDING and g.ending == config.ENDING_LEAVE
    assert sum(g.student.event_counts.values()) == 0
    assert g.current_event is None and g.notice is None


def test_chance_one_always_event_chance_zero_never(make_game, monkeypatch):
    g = make_game(4)
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    assert g.do_action(FEED)
    assert count(g) == 1
    g2 = make_game(4)
    monkeypatch.setattr(config, "EVENT_CHANCE", 0.0)
    for _ in range(10):   # 학년 안 0~10초: 보장 없음
        assert g2.do_action(FEED)
        g2.update(1.0)
    assert count(g2) == 0


def test_chance_is_about_25_percent(make_game):
    """보장이 없는 시각(학년 안 0초)에서 roll_event 를 많이 돌리면 약 25% 가 뜬다."""
    g = make_game(5)
    hits = 0
    n = 4000
    for _ in range(n):
        g.student.event_counts[1] = 0
        g.student.last_event_time = None   # (E단위) 최소 간격 영향 없이 확률만 본다
        g.state = config.STATE_PLAYING
        g.current_event = None
        g.student.seen_events.clear()
        g.student.health = g.student.mental = 80
        if g.roll_event() is not None:
            hits += 1
    assert 0.22 < hits / n < 0.28


@pytest.mark.parametrize("k", [1, 2, 3, 4])
@pytest.mark.parametrize("cycle", [1, 2, 3, 4, 6])
def test_guarantee_boundaries(make_game, monkeypatch, cycle, k):
    """(L단위) 주기 안 11.25*k 초 이후, 그 주기 이벤트 수 < k 면 확정. 직전 시각·이벤트 수 = k 면 확정 아님."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 0.0)
    start = (cycle - 1) * config.CYCLE_SECONDS
    boundary = start + config.EVENT_GUARANTEE_INTERVAL * k
    # 경계 직전, 이벤트 수 k-1: 아직 구간 k 가 안 끝남 -> 확정 아님 (k-1 구간은 끝났지만 수가 k-1)
    g = make_game(10 + k)
    g.student.elapsed = boundary - 0.01
    g.student.event_counts[cycle] = k - 1
    assert not g.student.needs_guaranteed_event()
    assert g.do_action(FEED)
    assert g.student.event_counts[cycle] == k - 1
    # 경계 정각, 이벤트 수 k-1 -> 확정
    g = make_game(20 + k)
    g.student.elapsed = boundary
    g.student.event_counts[cycle] = k - 1
    assert g.student.needs_guaranteed_event()
    assert g.do_action(FEED)
    assert g.student.event_counts[cycle] == k
    # 경계 뒤, 이벤트 수가 이미 k -> 확정 아님
    g = make_game(30 + k)
    g.student.elapsed = boundary + 0.5
    g.student.event_counts[cycle] = k
    assert not g.student.needs_guaranteed_event()
    assert g.do_action(FEED)
    assert g.student.event_counts[cycle] == k


def test_guarantee_after_45_capped_at_4(make_game, monkeypatch):
    """학년 안 45~60초(시험 기간)에도 끝난 구간은 최대 4: 이벤트 수 4 면 보장 없음."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 0.0)
    g = make_game(40)
    g.student.elapsed = 59.0
    g.student.event_counts[1] = 4
    assert not g.student.needs_guaranteed_event()
    g.student.event_counts[1] = 3
    assert g.student.needs_guaranteed_event()


def test_guarantee_resets_each_cycle(make_game, monkeypatch):
    """(L단위) 60초 주기가 바뀌면 그 주기 이벤트 수(0)와 주기 안 경과(0)로 다시 센다(학년과 무관)."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 0.0)
    g = make_game(41)
    g.student.event_counts[1] = 1
    g.student.elapsed = 60.0
    assert g.student.get_cycle_time() == 0 and g.student.get_cycle_index() == 2
    assert g.student.get_grade() == 1
    assert not g.student.needs_guaranteed_event()
    g.student.elapsed = 60.0 + 11.25
    assert g.student.needs_guaranteed_event()


def test_guarantee_fires_once_per_action(make_game, monkeypatch):
    """보장이 여러 개 밀려 있어도 행동 1번에 이벤트는 1개."""
    monkeypatch.setattr(config, "EVENT_CHANCE", 0.0)
    g = make_game(42)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    g.student.elapsed = 50.0
    assert g.do_action(FEED)
    assert count(g) == 1
    for expected in (2, 3, 4):
        g.update(1.0)
        assert g.do_action(FEED)
        assert count(g) == expected
    g.update(1.0)
    assert g.do_action(FEED)
    assert count(g) == 4


def test_max_five_per_cycle(make_game, monkeypatch):
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g = make_game(43)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    for _ in range(12):
        g.student.last_event_time = None   # (E단위) 최소 간격을 빼고 최대 5회 제한만 본다
        assert g.do_action(FEED)
        g.update(1.0)
    assert count(g) == 5
    assert not g.student.can_have_event()
    # (L단위) 다음 60초 주기는 다시 0부터 (학년은 1학년 그대로)
    g.student.elapsed = 60.0
    assert g.do_action(FEED)
    assert g.student.event_counts == {1: 5, 2: 1}
    assert g.student.get_grade() == 1


def test_choice_event_once_per_round(make_game, monkeypatch):
    g = make_game(44)
    mt = event_by_id("mt_invite")
    g.start_event(mt)
    g.choose_option(config.CHOICE_SECOND)
    choices, _ = g.get_event_candidates()
    assert mt not in choices
    assert [e[config.EVENT_ID] for e in choices] == ["club_fair"]
    g.start_event(event_by_id("club_fair"))
    g.choose_option(config.CHOICE_SECOND)
    choices, autos = g.get_event_candidates()
    assert choices == [] and autos == config.AUTO_EVENTS
    # 후보가 없으면 자동형만 나온다
    for _ in range(200):
        assert g.pick_event()[config.EVENT_KIND] == config.EVENT_KIND_AUTO


@pytest.mark.parametrize("grade, flags, expected", [
    (1, set(), {"mt_invite", "club_fair"}),
    (1, {"MT 참석", "밴드부", "연애 중"}, {"mt_invite", "club_fair"}),
    (2, set(), {"free_rider", "all_nighter"}),
    (2, {"MT 참석"}, {"free_rider", "all_nighter", "senior_notes"}),
    (2, {"밴드부", "연애 중"}, {"free_rider", "all_nighter"}),
    (3, set(), {"confession", "exchange_student"}),
    (3, {"MT 참석", "밴드부"}, {"confession", "exchange_student", "senior_notes",
                              "festival_stage"}),
    (3, {"연애 중"}, {"confession", "exchange_student"}),
    (4, set(), {"job_fair"}),
    (4, {"MT 참석", "밴드부", "연애 중"}, {"job_fair", "senior_notes", "festival_stage",
                                       "graduation_date"}),
])
def test_candidates_by_grade_and_flags(make_game, grade, flags, expected):
    """(L단위) 학년 조건은 지식으로 오른 지금 학년으로 본다(경과 시간은 1초 그대로)."""
    g = make_game(45)
    g.student.elapsed = 1.0
    reach_grade(g.student, grade)
    g.student.flags = set(flags)
    choices, autos = g.get_event_candidates()
    assert {e[config.EVENT_ID] for e in choices} == expected
    assert autos == config.AUTO_EVENTS


def test_pick_ratio_and_uniformity(make_game):
    """선택지형 후보가 있으면 약 50% 선택지형, 종류 안에서는 고르게."""
    g = make_game(46)
    counts = {}
    n = 6000
    for _ in range(n):
        e = g.pick_event()
        counts[e[config.EVENT_ID]] = counts.get(e[config.EVENT_ID], 0) + 1
    choice = counts.get("mt_invite", 0) + counts.get("club_fair", 0)
    assert 0.46 < choice / n < 0.54
    assert set(counts) == {"mt_invite", "club_fair"} | {e[config.EVENT_ID]
                                                        for e in config.AUTO_EVENTS}
    for e in config.AUTO_EVENTS:
        assert 0.07 < counts[e[config.EVENT_ID]] / n < 0.13
    assert 0.2 < counts["mt_invite"] / n < 0.3


def test_seen_choice_marked_and_counted_at_start(make_game):
    g = make_game(47)
    g.start_event(event_by_id("mt_invite"))
    assert "mt_invite" in g.student.seen_events
    assert count(g) == 1
    assert g.state == config.STATE_EVENT


# ======================= 3. 대화(선택지형) 상태 =======================

@pytest.fixture
def in_dialog(make_game, monkeypatch):
    """학식 행동 직후 MT 초대 대화창이 뜬 상태의 Game."""
    g = make_game(50)
    force_event(monkeypatch, g, event_by_id("mt_invite"))
    g.update(3.3)
    assert g.do_action(FEED)
    assert g.state == config.STATE_EVENT
    assert g.current_event is event_by_id("mt_invite")
    return g


def test_dialog_freezes_time_gauges_auto_timer(in_dialog):
    """(G단위) 쿨타임 대신 자동 행동 시계가 멈추는지 본다(2초 간격 실제 값 검사는 test_idle_g.py)."""
    g = in_dialog
    s = g.student
    before = (s.elapsed, s.decay_timer, s.health, s.mental, s.knowledge, g.auto_timer,
              g.last_action)
    for _ in range(300):
        g.update(0.05)   # 15초
    g.update(30.0)
    assert (s.elapsed, s.decay_timer, s.health, s.mental, s.knowledge, g.auto_timer,
            g.last_action) == before
    assert s.get_grade() == 1
    assert g.state == config.STATE_EVENT
    assert g.ending is None


def test_dialog_freeze_not_counted_in_graduation_time(make_game, monkeypatch):
    """(L단위) 대화창 동안 시간이 멈추고, 선택으로 졸업 목표에 닿으면 그 순간(멈춘 시각) 졸업한다.

    4학년 1090에서 취업 박람회 "대학원 상담"(지식 +10) -> 1100 졸업. 대화창 5초는 걸린 시간에 안 들어간다.
    """
    g = make_game(51)
    force_event(monkeypatch, g, event_by_id("job_fair"))
    reach_grade(g.student, 4)
    g.student.knowledge = config.GRADUATION_KNOWLEDGE - 10
    g.student.elapsed = 239.5
    assert g.do_action(FEED)
    assert g.state == config.STATE_EVENT
    g.update(5.0)
    assert g.state == config.STATE_EVENT and g.student.elapsed == 239.5
    assert g.choose_option(config.CHOICE_SECOND)
    assert g.state == config.STATE_ENDING
    assert g.student.graduation_time == 239.5
    assert g.ending == config.ENDING_TOP


def test_dialog_ignores_action_keys_and_buttons(in_dialog):
    g = in_dialog
    snap = gauges(g)
    press(g, pygame.K_3)
    for name, button in g.buttons.items():
        click(g, button.rect.center)
    assert g.do_action(STUDY) is False
    press(g, pygame.K_RETURN)
    press(g, pygame.K_r)
    assert gauges(g) == snap
    assert g.state == config.STATE_EVENT


def test_action_buttons_do_not_overlap_choice_buttons(in_dialog):
    g = in_dialog
    for cb in g.choice_buttons:
        for b in g.buttons.values():
            assert not cb.rect.colliderect(b.rect)


def test_dialog_click_outside_does_nothing(in_dialog):
    g = in_dialog
    pass_input_delay(g)
    click(g, (5, 5))
    assert g.state == config.STATE_EVENT


def test_choice_key_1_applies_option(in_dialog):
    g = in_dialog
    h, m, k = gauges(g)
    pass_input_delay(g)
    press(g, pygame.K_1)   # 간다: 멘탈 +15, 체력 -10, MT 참석
    assert g.state == config.STATE_PLAYING and g.current_event is None
    assert gauges(g) == (h - 10, min(100, m + 15), k)
    assert g.student.flags == {"MT 참석"}
    assert g.student.traits == [] and g.student.looks == []


def test_choice_key_2_applies_option(in_dialog):
    g = in_dialog
    h, m, k = gauges(g)
    pass_input_delay(g)
    press(g, pygame.K_2)   # 공부한다: 지식 +10, 멘탈 -5
    assert gauges(g) == (h, m - 5, k + 10)
    assert g.student.flags == set()


def test_choice_key_3_ignored(in_dialog):
    g = in_dialog
    snap = gauges(g)
    pass_input_delay(g)
    press(g, pygame.K_3)
    assert g.state == config.STATE_EVENT and gauges(g) == snap


@pytest.mark.parametrize("index", [0, 1])
def test_choice_click(make_game, monkeypatch, index):
    g = make_game(52)
    force_event(monkeypatch, g, event_by_id("club_fair"))
    assert g.do_action(FEED)
    assert g.choice_buttons[0].text == "[1] 밴드부"
    assert g.choice_buttons[1].text == "[2] 헬스부"
    pass_input_delay(g)
    click(g, g.choice_buttons[index].rect.center)
    assert g.state == config.STATE_PLAYING
    if index == 0:
        assert g.student.traits == ["음악 힐링"] and g.student.looks == [config.LOOK_GUITAR]
        assert g.student.flags == {"밴드부"}
    else:
        assert g.student.traits == ["체력 단련"] and g.student.looks == [config.LOOK_HEADBAND]
        assert g.student.flags == set()


def test_choice_shows_popups(make_game, monkeypatch):
    g = make_game(53)
    force_event(monkeypatch, g, event_by_id("free_rider"))
    g.student.elapsed = 61.0
    reach_grade(g.student, 2)   # (L단위) 2학년 이벤트: 학년은 지식으로
    assert g.do_action(FEED)   # 체력 80 -> 100
    n_action = len(g.popups)
    pass_input_delay(g)
    press(g, pygame.K_1)      # 지식 +20, 체력 -15, 멘탈 -10
    new = texts_top_down(g.popups[n_action:])
    assert new == ["체력 -15", "멘탈 -10", "지식 +20"]
    ys_old = [p["y"] for p in g.popups[:n_action]]
    ys_new = [p["y"] for p in g.popups[n_action:]]
    assert max(ys_new) < min(ys_old)   # 행동 팝업 위에 쌓인다


def test_choice_popup_uses_clamped_change(make_game, monkeypatch):
    g = make_game(54)
    force_event(monkeypatch, g, event_by_id("mt_invite"))
    g.student.mental = 95
    assert g.do_action(FEED)
    n = len(g.popups)
    pass_input_delay(g)
    press(g, pygame.K_1)
    assert g.student.mental == 100
    assert texts_top_down(g.popups[n:]) == ["체력 -10", "멘탈 +5"]


def test_choice_without_gauge_change_no_popup(make_game, monkeypatch):
    g = make_game(55)
    force_event(monkeypatch, g, event_by_id("club_fair"))
    assert g.do_action(FEED)
    n = len(g.popups)
    pass_input_delay(g)
    press(g, pygame.K_2)
    assert g.state == config.STATE_PLAYING   # (D 단위) 선택이 실제로 처리됐는지 확인
    assert len(g.popups) == n


def test_choice_result_zero_leaves(make_game, monkeypatch):
    g = make_game(56)
    force_event(monkeypatch, g, event_by_id("free_rider"))
    g.student.elapsed = 61.0
    reach_grade(g.student, 2)   # (L단위) 2학년 이벤트: 학년은 지식으로
    g.student.health = 10   # 학식 +20 -> 30, 혼자 다 한다 -15 -> 15
    g.student.mental = 10   # -10 -> 0
    assert g.do_action(FEED)
    pass_input_delay(g)
    press(g, pygame.K_1)
    assert g.state == config.STATE_ENDING and g.ending == config.ENDING_LEAVE
    assert g.student.mental == 0
    assert g.current_event is None


def test_dialog_resume_after_choice(in_dialog):
    g = in_dialog
    s = g.student
    t0 = s.elapsed
    cd = g.auto_timer
    pass_input_delay(g)
    assert (s.elapsed, g.auto_timer) == (t0, cd)   # 대기 동안에도 게임 시간·자동 행동 시계 정지
    press(g, pygame.K_2)
    assert g.state == config.STATE_PLAYING
    g.update(0.5)
    assert s.elapsed == pytest.approx(t0 + 0.5)
    assert g.auto_timer == pytest.approx(cd - 0.5)   # (G단위) 자동 행동 시계가 다시 흐른다
    assert g.do_action(FEED)


def test_choose_option_outside_dialog_does_nothing(make_game):
    g = make_game(57)
    snap = gauges(g)
    assert g.choose_option(0) is False
    assert gauges(g) == snap and g.state == config.STATE_PLAYING


def test_esc_and_quit_in_dialog(in_dialog):
    g = in_dialog
    press(g, pygame.K_ESCAPE)
    assert g.running is False


def test_quit_in_dialog(in_dialog):
    g = in_dialog
    g.handle_event(pygame.event.Event(pygame.QUIT))
    assert g.running is False


def test_draw_in_dialog_and_notice_no_crash(in_dialog, monkeypatch):
    g = in_dialog
    g.draw()
    pass_input_delay(g)
    press(g, pygame.K_1)
    assert g.state == config.STATE_PLAYING
    g.start_event(config.AUTO_EVENTS[0])
    assert g.notice is not None
    g.draw()


# ======================= 4. 자동형 =======================

@pytest.mark.parametrize("event", config.AUTO_EVENTS, ids=lambda e: e[config.EVENT_ID])
def test_auto_event_effect_and_notice(make_game, monkeypatch, event):
    g = make_game(60)
    g.student.health = g.student.mental = 50
    g.student.knowledge = 30
    force_event(monkeypatch, g, event)
    assert g.do_action(FEED)   # 체력 50 -> 70
    eff = event[config.EVENT_EFFECTS]
    assert gauges(g) == (70 + eff.get(H, 0), 50 + eff.get(M, 0), 30 + eff.get(K, 0))
    assert g.state == config.STATE_PLAYING and g.current_event is None
    assert g.notice is not None and event[config.EVENT_TITLE] in g.notice["text"]
    assert g.student.seen_events == set()   # 자동형은 반복 가능
    assert count(g) == 1


def test_auto_event_popups_shown(make_game, monkeypatch):
    g = make_game(61)
    force_event(monkeypatch, g, event_by_id("professor_praise"))
    g.student.mental = 50
    assert g.do_action(FEED)
    assert popup_texts(g)[:1] == ["체력 +20"]                 # 행동 팝업
    assert texts_top_down(g.popups[1:]) == ["멘탈 +5", "지식 +15"]   # 이벤트 팝업
    # (D/E단위) 이벤트 팝업은 머리 위가 아니라 EVENT_POPUP_X 열, 알림 상자 아래에 쌓인다
    action_pop, event_pops = g.popups[0], g.popups[1:]
    assert action_pop["x"] == config.STUDENT_CENTER_X
    assert all(p["x"] == config.EVENT_POPUP_X for p in event_pops)
    notice_bottom = config.EVENT_NOTICE_Y + config.EVENT_NOTICE_HEIGHT
    assert min(p["y"] for p in event_pops) == notice_bottom + config.EVENT_POPUP_TOP_MARGIN
    # 행동 팝업과 글자 사각형이 겹치지 않는다
    def rect(p):
        surf = g.popup_font.render(p["text"], False, (0, 0, 0))
        return surf.get_rect(center=(p["x"], p["y"]))
    for p in event_pops:
        assert not rect(p).colliderect(rect(action_pop)), (p["text"], action_pop["text"])


def test_auto_notice_lasts_two_seconds(make_game, monkeypatch):
    g = make_game(62)
    force_event(monkeypatch, g, config.AUTO_EVENTS[0])
    assert g.do_action(FEED)
    for _ in range(39):
        g.update(0.05)   # 1.95초
    assert g.notice is not None
    g.update(0.05)       # 2.0초
    assert g.notice is None


def test_auto_event_does_not_pause(make_game, monkeypatch):
    g = make_game(63)
    force_event(monkeypatch, g, config.AUTO_EVENTS[0])
    t0 = g.student.elapsed
    assert g.do_action(FEED)
    g.update(1.0)
    assert g.student.elapsed == pytest.approx(t0 + 1.0)
    assert g.do_action(FEED)


@pytest.mark.parametrize("event_id, attr", [("deadline_alarm", "mental"), ("cold", "health")])
def test_auto_event_to_zero_leaves(make_game, monkeypatch, event_id, attr):
    g = make_game(64)
    force_event(monkeypatch, g, event_by_id(event_id))
    setattr(g.student, attr, 10)
    action = REST if attr == "health" else FEED   # 그 게이지를 올리지 않는 행동
    if attr == "health":
        g.student.mental = 50
    assert g.do_action(action)
    assert getattr(g.student, attr) == 0
    assert g.state == config.STATE_ENDING and g.ending == config.ENDING_LEAVE
    assert g.notice is None


def test_auto_event_clamped(make_game, monkeypatch):
    g = make_game(65)
    force_event(monkeypatch, g, event_by_id("side_dish"))
    assert g.do_action(FEED)   # 80 -> 100, +15 -> 100
    assert g.student.health == 100
    assert "체력 +15" not in popup_texts(g)


def test_auto_event_repeats(make_game, monkeypatch):
    g = make_game(66)
    force_event(monkeypatch, g, event_by_id("group_chat_praise"))
    g.student.mental = 10
    for _ in range(3):
        g.student.last_event_time = None   # (E단위) 최소 간격을 빼고 자동형 반복 가능만 본다
        assert g.do_action(STUDY)
        g.update(1.0)
    assert count(g) == 3


# ======================= 5. 특성 보정 =======================

def student_with(*traits, health=50, mental=50, knowledge=50, elapsed=0.0):
    s = Student()
    for t in traits:
        s.add_trait(t)
    s.health, s.mental, s.knowledge, s.elapsed = health, mental, knowledge, elapsed
    return s


@pytest.mark.parametrize("traits, feed, rest, study", [
    ((), (70, 50, 50), (50, 70, 48), (45, 42, 60)),
    (("체력 단련",), (75, 50, 50), (50, 70, 48), (45, 42, 60)),
    (("음악 힐링",), (70, 50, 50), (50, 75, 48), (45, 42, 60)),
    (("연애 중",), (70, 50, 50), (55, 70, 48), (45, 42, 60)),
    (("카페인",), (70, 50, 50), (50, 70, 48), (47, 42, 60)),
    (("체력 단련", "음악 힐링", "연애 중", "카페인"), (75, 50, 50), (55, 75, 48), (47, 42, 60)),
    (("음악 힐링", "연애 중"), (70, 50, 50), (55, 75, 48), (45, 42, 60)),
])
def test_trait_bonuses(traits, feed, rest, study):
    for action, expected in ((Student.feed, feed), (Student.rest, rest), (Student.study, study)):
        s = student_with(*traits)
        action(s)
        assert (s.health, s.mental, s.knowledge) == expected, (traits, action.__name__)


def test_trait_bonus_clamped():
    s = student_with("체력 단련", health=90)
    s.feed()
    assert s.health == 100
    s = student_with("음악 힐링", "연애 중", health=98, mental=90, knowledge=1)
    s.rest()
    assert (s.health, s.mental, s.knowledge) == (100, 100, 0)
    s = student_with("카페인", health=2)
    s.study()
    assert s.health == 0 and s.is_dropped_out()


def test_trait_exam_knowledge_rule_kept():
    s = student_with("카페인", "체력 단련", "음악 힐링", "연애 중", elapsed=45.0)
    s.study()
    assert (s.health, s.mental, s.knowledge) == (47, 42, 70)
    s = student_with("카페인", elapsed=44.9)
    s.study()
    assert s.knowledge == 60


def test_traits_kept_in_order_without_duplicates():
    s = Student()
    for t in ("카페인", "체력 단련", "카페인"):
        s.add_trait(t)
    assert s.traits == ["카페인", "체력 단련"]
    assert s.get_trait_bonus(config.BONUS_FEED_HEALTH) == 5
    assert s.get_trait_bonus(config.BONUS_STUDY_HEALTH) == 2
    assert s.get_trait_bonus(config.BONUS_REST_HEALTH) == 0


def test_trait_works_through_game_action(make_game, monkeypatch):
    """선택지로 얻은 특성이 이후 행동에 반영된다(체력 단련: 학식 +25)."""
    g = make_game(70)
    force_event(monkeypatch, g, event_by_id("club_fair"))
    g.student.health = 50
    assert g.do_action(FEED)        # 70
    pass_input_delay(g)
    press(g, pygame.K_2)            # 헬스부
    monkeypatch.setattr(config, "EVENT_CHANCE", 0.0)
    g.update(1.0)
    assert g.do_action(FEED)
    assert g.student.health == 70 - 1 + 25
    assert "체력 +25" in popup_texts(g)


@pytest.mark.parametrize("event_id, index, attr, value", [
    ("mt_invite", 0, "health", 10), ("mt_invite", 1, "mental", 5),
    ("free_rider", 0, "health", 15), ("exchange_student", 0, "health", 10),
    ("job_fair", 0, "mental", 15), ("festival_stage", 0, "health", 10),
])
def test_every_negative_option_clamps_to_zero(make_game, event_id, index, attr, value):
    g = make_game(71)
    setattr(g.student, attr, value - 3)   # 효과보다 작게: 0에서 멈추고 휴학
    g.start_event(event_by_id(event_id))
    pass_input_delay(g)
    assert g.choose_option(index) is True
    assert getattr(g.student, attr) == 0
    assert g.ending == config.ENDING_LEAVE


def test_knowledge_never_negative_from_events():
    for e in config.ALL_EVENTS:
        effs = [e[config.EVENT_EFFECTS]] if e[config.EVENT_KIND] == config.EVENT_KIND_AUTO \
            else [o[config.OPTION_EFFECTS] for o in e[config.EVENT_OPTIONS]]
        for eff in effs:
            s = Student()
            s.knowledge = 0
            s.apply_effects(eff)
            assert s.knowledge >= 0
            assert 0 <= s.health <= 100 and 0 <= s.mental <= 100


# ======================= 6. 초기화 =======================

def _grow(g):
    s = g.student
    s.add_trait("카페인")
    s.add_look(config.LOOK_COFFEE)
    s.add_flag("MT 참석")
    s.seen_events.add("mt_invite")
    s.event_counts[1] = 3


def _assert_reset(g):
    s = g.student
    assert s.traits == [] and s.looks == [] and s.flags == set()
    assert s.seen_events == set() and s.event_counts == {}
    assert g.current_event is None and g.notice is None


def test_restart_with_r_resets_growth(make_game, monkeypatch):
    g = make_game(80)
    _grow(g)
    force_event(monkeypatch, g, config.AUTO_EVENTS[0])
    assert g.do_action(FEED)
    assert g.notice is not None
    g.student.health = 0
    g.update(0.01)
    assert g.state == config.STATE_ENDING
    assert g.notice is None and g.current_event is None
    press(g, pygame.K_r)
    assert g.state == config.STATE_PLAYING
    _assert_reset(g)


def test_ending_clears_dialog(make_game, monkeypatch):
    g = make_game(81)
    g.start_event(event_by_id("mt_invite"))
    g.end_game(config.ENDING_LEAVE)
    assert g.current_event is None and g.state == config.STATE_ENDING
    press(g, pygame.K_1)
    assert g.state == config.STATE_ENDING


def test_start_new_game_resets(make_game):
    g = make_game(82)
    _grow(g)
    g.start_event(event_by_id("club_fair"))
    g.start_new_game()
    _assert_reset(g)
    assert g.state == config.STATE_PLAYING


# ======================= 7. 결정성 =======================

def choose_knowledge(event):
    """지식이 더 많이 오르는 선택지(같으면 첫 번째)."""
    opts = event[config.EVENT_OPTIONS]
    k = [o[config.OPTION_EFFECTS].get(K, 0) for o in opts]
    return config.CHOICE_SECOND if k[1] > k[0] else config.CHOICE_FIRST


def choose_safe(event):
    """체력+멘탈 합이 더 좋은 선택지."""
    opts = event[config.EVENT_OPTIONS]
    v = [o[config.OPTION_EFFECTS].get(H, 0) + o[config.OPTION_EFFECTS].get(M, 0) for o in opts]
    return config.CHOICE_SECOND if v[1] > v[0] else config.CHOICE_FIRST


def choose_first(event):
    return config.CHOICE_FIRST


def greedy(s, low=30):
    if s.health <= low:
        return FEED
    if s.mental <= low:
        return REST
    return STUDY


def care_only(s):
    if s.health <= 50:
        return FEED
    if s.mental <= 50:
        return REST
    return None


def make_steady(stop_at):
    def policy(s):
        if s.knowledge < stop_at:
            return greedy(s)
        return care_only(s)
    return policy


def study_only(s):
    return STUDY


DT = 0.05
SIM_CAP_SECONDS = 900   # (L단위) 시간 제한이 없으므로 시뮬레이션 상한(15분)


def simulate(seed, policy, chooser, interval=1.0, think=0.3):
    """한 판을 끝까지 돈다. interval 초마다(쿨타임 풀리면) policy 행동, 대화창은 think 초 뒤 chooser.

    돌려주는 것: (Game, 기록 dict). 매 프레임 규칙 위반을 확인한다.
    """
    g = Game(seed=seed)
    press(g, pygame.K_RETURN)
    log = {"events": [], "violations": [], "cycle_counts": {}}
    real_start = g.start_event

    def logged_start(event):
        s = g.student
        log["events"].append((s.get_grade(), event[config.EVENT_ID],
                              round(s.get_cycle_time(), 2), event[config.EVENT_KIND]))
        if event[config.EVENT_KIND] == config.EVENT_KIND_CHOICE:
            if event[config.EVENT_ID] in s.seen_events:
                log["violations"].append(("choice repeated", event[config.EVENT_ID]))
        if s.get_grade() not in event[config.EVENT_GRADES]:
            log["violations"].append(("wrong grade", event[config.EVENT_ID]))
        req = event[config.EVENT_REQUIRES]
        if req is not None and req not in s.flags:
            log["violations"].append(("missing flag", event[config.EVENT_ID]))
        real_start(event)

    g.start_event = logged_start
    wait = 0.0
    dialog_wait = None
    frames = 0
    while g.state in (config.STATE_PLAYING, config.STATE_EVENT) and \
            frames < SIM_CAP_SECONDS / DT:
        s = g.student
        if g.state == config.STATE_EVENT:
            frozen = (s.elapsed, s.health, s.mental, s.knowledge, g.auto_timer)
            if dialog_wait is None:
                dialog_wait = think
            if dialog_wait <= 1e-9:
                g.choose_option(chooser(g.current_event))
                dialog_wait = None
            else:
                g.update(DT)
                dialog_wait -= DT
                if (s.elapsed, s.health, s.mental, s.knowledge, g.auto_timer) != frozen:
                    log["violations"].append(("not frozen", s.elapsed))
            continue
        if wait <= 1e-9:   # (G단위) 쿨타임 없음: interval(>=1초)마다 행동
            action = policy(s)
            if action is not None:
                assert g.do_action(action)
            wait = interval
        if g.state != config.STATE_PLAYING:
            continue
        g.update(DT)
        wait -= DT
        frames += 1
        if not (0 <= s.health <= 100 and 0 <= s.mental <= 100 and s.knowledge >= 0):
            log["violations"].append(("range", s.health, s.mental, s.knowledge))
        if any(c > config.EVENT_MAX_PER_GRADE for c in s.event_counts.values()):
            log["violations"].append(("max", dict(s.event_counts)))
    s = g.student
    # (L단위) 끝까지 지나간 60초 주기 번호들 (학년 대신 주기마다 4~5회)
    completed = int(s.elapsed // config.CYCLE_SECONDS)
    log["completed"] = list(range(config.CYCLE_INDEX_START, completed + config.CYCLE_INDEX_START))
    log["cycle_counts"] = dict(s.event_counts)
    return g, log


def test_same_seed_same_result():
    a, la = simulate(123, greedy, choose_knowledge)
    b, lb = simulate(123, greedy, choose_knowledge)
    assert la["events"] == lb["events"]
    assert (a.ending, gauges(a)) == (b.ending, gauges(b))
    pygame.quit()


def test_different_seeds_can_differ():
    results = set()
    for seed in range(6):
        g, log = simulate(seed, greedy, choose_knowledge)
        results.add(tuple(e[1] for e in log["events"]))
    assert len(results) > 1
    pygame.quit()


def test_rng_is_per_game_instance():
    """Game 마다 따로 rng 를 가진다(전역 random 상태와 무관)."""
    import random
    g1 = Game(seed=7)
    random.seed(999)
    random.random()
    g2 = Game(seed=7)
    assert [g1.rng.random() for _ in range(5)] == [g2.rng.random() for _ in range(5)]
    assert g1.rng is not g2.rng
    pygame.quit()


# ======================= 8. 분포 시뮬레이션 =======================

@pytest.mark.parametrize("interval", [1.0, 2.0, 3.0])
def test_distribution_events_per_completed_cycle(interval):
    """꾸준히 행동하면 완주한 60초 주기마다 이벤트 4~5회, 규칙 위반 0 (L단위: 학년 -> 주기)."""
    totals = []
    for seed in range(8):
        chooser = (choose_knowledge, choose_safe, choose_first)[seed % 3]
        g, log = simulate(seed, greedy, chooser, interval=interval)
        assert log["violations"] == [], (seed, log["violations"][:3])
        assert log["completed"], (seed, interval)
        for cycle in log["completed"]:
            assert 4 <= log["cycle_counts"].get(cycle, 0) <= 5, (seed, interval, log["cycle_counts"])
        totals.append(sum(log["cycle_counts"].values()))
    pygame.quit()


def test_distribution_care_only_also_gets_events():
    """행동이 드문 전략(체력·멘탈 50 이하일 때만)도 꾸준히 행동한다면 보장이 지켜진다."""
    for seed in range(4):
        g, log = simulate(seed, care_only, choose_safe, interval=1.0)
        assert log["violations"] == []
        # (L단위) 학식·휴식만으로는 지식이 거의 안 늘어 상한(15분)까지 졸업 못 하거나 휴학한다
        assert g.ending in (None, config.ENDING_LEAVE)
        assert all(c <= config.EVENT_MAX_PER_GRADE for c in log["cycle_counts"].values())


def test_all_three_graduation_endings_and_leave_reachable():
    endings = {}
    # (L단위) 등급은 걸린 시간이라 행동 간격으로 나눈다(1초 수석, 1.5초 무사, 2.5초 아슬아슬 쪽)
    scenarios = [
        ("top", greedy, choose_knowledge, 1.0),
        ("normal", greedy, choose_safe, 1.5),
        ("barely", greedy, choose_safe, 2.5),
        ("leave", study_only, choose_first, 1.0),
    ]
    for name, policy, chooser, interval in scenarios:
        for seed in range(5):
            g, log = simulate(seed, policy, chooser, interval=interval)
            assert log["violations"] == []
            endings.setdefault(name, set()).add(g.ending)
    assert config.ENDING_TOP in endings["top"]
    assert config.ENDING_NORMAL in endings["normal"]
    assert config.ENDING_BARELY in endings["barely"]
    assert endings["leave"] == {config.ENDING_LEAVE}
    pygame.quit()


def test_no_event_without_action():
    """행동을 전혀 안 하면 이벤트도 없다(행동 직후에만 판정)."""
    g = Game(seed=1)
    press(g, pygame.K_RETURN)
    while g.state == config.STATE_PLAYING:
        g.update(0.5)
    assert sum(g.student.event_counts.values()) == 0
    assert g.ending == config.ENDING_LEAVE
    pygame.quit()
