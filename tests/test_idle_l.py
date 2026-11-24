"""L단위 검수: 시간 제한 없애기 (기획서 11절, jeja-spec 16절).

- 진급: 누적 지식 200/450/750 이상이면 2/3/4학년, 4학년에서 1100 이상이면 졸업. 여러 목표를 한 번에
  넘으면 그만큼 오르고, 학년은 내려가지 않는다. 체력·멘탈 0이면 휴학이 졸업보다 먼저다.
- 졸업 등급: 걸린 게임 시간(대화창 정지 제외) 200초 이하 수석 / 360초 이하 무사 / 초과 아슬아슬.
  (11절 A안 밸런스로 수석 240 -> 200초. 수석 경계 테스트는 200/200.0001초로 옮겼다.)
- 60초 주기: 계절·낮밤·시험 기간·이벤트 최소 4·최대 5회는 주기 기준(주기 번호 = 경과 // 60 + 1).
- 대학원: 년차 목표 누적 1500 / 2000 / 2600 / 3300 …, 진학해도 시계는 이어진다. 이미 넘었으면 바로 오른다.
- 화면: 정보바 "다음 학년까지 지식 n" / "졸업까지 지식 n", 목표 진행 막대, 경과 시간, 진급 알림(무대 오른쪽 위),
  엔딩의 "졸업까지 m분 s초".

이 파일은 conftest 의 AUTO_OFF_FILES / EVENTS_OFF_FILES 에 없다. 필요한 테스트만 no_auto / no_events 를 쓴다.
"""

import ast
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
import game as game_module  # noqa: E402
from button import sprite_size  # noqa: E402
from conftest import graduate, press, reach_grade  # noqa: E402
from game import Game, format_time  # noqa: E402
from student import Student, judge_ending  # noqa: E402

ROOT = Path(config.__file__).parent
FRAME = 1 / 60
P = config.PIXEL_SIZE
FEED, REST, STUDY = config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY
TOP, NORMAL, BARELY = config.ENDING_TOP, config.ENDING_NORMAL, config.ENDING_BARELY
# (M단위) 졸업 등급 시간 기준은 config 상수라 경계 테스트는 config 상수로 쓴다
TOP_S, NORMAL_S = config.TOP_GRADUATE_SECONDS, config.NORMAL_GRADUATE_SECONDS
GOAL = config.GRADUATION_KNOWLEDGE   # (M단위) 졸업 지식 2200
STAGE_INNER = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH,
                          config.PANEL_HEIGHT).inflate(-2 * P, -2 * P)
GOAL_BOX = pygame.Rect(config.GOAL_BOX_X, config.GOAL_BOX_Y, config.GOAL_BOX_WIDTH,
                       config.GOAL_BOX_HEIGHT)


# ============================== 도우미 ==============================

@pytest.fixture
def g(no_events, no_auto):
    """이벤트·자동 행동을 끈 채 게임 중인 Game."""
    game = Game()
    press(game, pygame.K_RETURN)
    assert game.state == config.STATE_PLAYING
    yield game
    pygame.quit()


@pytest.fixture
def seeded():
    """이벤트·자동 행동이 켜진 seed 고정 Game 을 게임 중으로 만든다."""
    def factory(seed):
        game = Game(seed=seed)
        press(game, pygame.K_RETURN)
        return game
    yield factory
    pygame.quit()


def event_by_id(event_id):
    for event in config.ALL_EVENTS:
        if event[config.EVENT_ID] == event_id:
            return event
    raise KeyError(event_id)


def record_texts(game, monkeypatch, method="draw"):
    """game.<method>() 를 하며 render_text 로 만든 (글자, 글꼴) 목록을 돌려준다."""
    made = []
    real = game_module.render_text

    def rec(font, text, *a, **k):
        made.append((text, font))
        return real(font, text, *a, **k)
    monkeypatch.setattr(game_module, "render_text", rec)
    getattr(game, method)()
    monkeypatch.setattr(game_module, "render_text", real)
    return made


def texts_of(game, monkeypatch, method="draw"):
    return [t for t, _ in record_texts(game, monkeypatch, method)]


def changed_pixels(a, b):
    """두 Surface 에서 색이 다른 픽셀 좌표 집합."""
    w, h = a.get_size()
    ba = pygame.image.tobytes(a, "RGB")
    bb = pygame.image.tobytes(b, "RGB")
    out = set()
    for i in range(0, len(ba), 3):
        if ba[i:i + 3] != bb[i:i + 3]:
            n = i // 3
            out.add((n % w, n // w))
    return out


def screen_without(game, monkeypatch, method_name):
    """game.draw() 화면과, method_name 을 빈 함수로 바꾼 game.draw() 화면을 돌려준다."""
    game.draw()
    with_it = game.screen.copy()
    setattr(game, method_name, lambda *a, **k: None)
    game.draw()
    without = game.screen.copy()
    delattr(game, method_name)          # 인스턴스 속성을 지워 원래 메서드로 되돌린다
    return with_it, without


def bbox(points):
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


# ======================= 1. config 수치 (기획서 11절 표) =======================

def test_l_constants_match_spec():
    # (M단위) 진급 기준 2배: 200/450/750/1100 -> 400/900/1500/2200, 시간 기준은 config 상수라 순서만
    assert config.GRADE_GOALS == [400, 900, 1500]
    assert config.GRADUATION_KNOWLEDGE == 2200
    assert 0 < config.TOP_GRADUATE_SECONDS < config.NORMAL_GRADUATE_SECONDS
    assert config.CYCLE_SECONDS == 60 and config.EXAM_SECONDS == 15
    assert config.CYCLE_INDEX_START == 1
    assert (config.GRAD_GOAL_FIRST_STEP, config.GRAD_GOAL_STEP_GROWTH) == (800, 200)   # M단위 2배
    assert config.GRADUATION_BONUS == {TOP: 200, NORMAL: 100, BARELY: 50}
    # 이벤트 보장 구간 4 x 11.25 = 주기 안 시험 기간 시작(45초), 최소 간격 8초 그대로
    assert config.EVENT_GUARANTEE_INTERVAL * config.EVENT_MIN_PER_GRADE == \
        config.CYCLE_SECONDS - config.EXAM_SECONDS
    assert (config.EVENT_MIN_PER_GRADE, config.EVENT_MAX_PER_GRADE, config.EVENT_MIN_GAP) == \
        (4, 5, 8.0)
    assert config.NEXT_GRADE_TEXT.format(80) == "다음 학년까지 지식 80"
    assert config.GRADUATION_GOAL_TEXT.format(5) == "졸업까지 지식 5"
    assert config.ELAPSED_TEXT.format(format_time(192)) == "경과 3분 12초"
    assert config.ENDING_TIME_TEXT.format(format_time(232)) == "졸업까지 3분 52초"
    assert config.PROMOTION_TEXT.format(3) == "3학년 진급!"


@pytest.mark.parametrize("name", ["SECONDS_PER_GRADE", "TOTAL_SECONDS", "TOP_GRADUATE_KNOWLEDGE",
                                  "NORMAL_GRADUATE_KNOWLEDGE", "TIME_LEFT_TEXT", "INFO_TIME_X"])
def test_removed_config_names(name):
    assert not hasattr(config, name)


@pytest.mark.parametrize("name", ["is_time_over", "get_time_in_grade", "get_term_start",
                                  "get_term_key", "get_grad_year_end", "advance_grad_year",
                                  "get_grade_time_left", "get_grade_event_count"])
def test_removed_student_methods(name):
    assert not hasattr(Student, name)


def test_rules_read_from_config_at_runtime(monkeypatch):
    """진급 목표·졸업 지식·등급 시간·주기 길이를 config 에서 그때그때 읽는다(숫자를 박아 두지 않음)."""
    monkeypatch.setattr(config, "GRADE_GOALS", [10, 20, 30])
    monkeypatch.setattr(config, "GRADUATION_KNOWLEDGE", 40)
    s = Student()
    s.knowledge = 25
    assert s.promote() == 2 and s.get_grade() == 3
    s.knowledge = 40
    s.elapsed = 100.0
    s.promote()
    assert s.graduation_time == 100.0
    monkeypatch.setattr(config, "TOP_GRADUATE_SECONDS", 50)
    monkeypatch.setattr(config, "NORMAL_GRADUATE_SECONDS", 99)
    assert judge_ending(50) == TOP and judge_ending(99) == NORMAL and judge_ending(100) == BARELY
    monkeypatch.setattr(config, "CYCLE_SECONDS", 40)
    s.elapsed = 85.0
    assert s.get_cycle_index() == 3 and s.get_cycle_time() == pytest.approx(5.0)
    monkeypatch.setattr(config, "GRAD_GOAL_FIRST_STEP", 10)
    monkeypatch.setattr(config, "GRAD_GOAL_STEP_GROWTH", 1)
    assert s.get_grad_goal(3) == 40 + 10 + 11 + 12


L_FUNCTIONS = {
    "student.py": ["judge_ending", "get_grade", "get_grad_goal", "get_next_goal", "get_goal_start",
                   "get_goal_progress", "get_knowledge_to_goal", "has_graduated", "promote",
                   "get_cycle_index", "get_cycle_time", "get_cycle_event_count",
                   "is_exam_period", "needs_guaranteed_event", "get_graduation_ending"],
    "game.py": ["format_time", "check_promotion", "draw_promotion_notice", "draw_notice",
                "get_goal_text", "draw_goal_bar", "draw_elapsed_time", "draw_info_bar",
                "draw_ending", "enter_grad_school", "get_season_time"],
}


def _defs(name):
    tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
    return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


@pytest.mark.parametrize("name", list(L_FUNCTIONS))
def test_l_functions_docstring_no_numbers_no_alpha(name):
    """L단위 함수: 한국어 docstring, 숫자 리터럴 없음(config 상수만), 반투명 없음."""
    defs = _defs(name)
    for fname in L_FUNCTIONS[name]:
        assert fname in defs, fname
        node = defs[fname]
        assert ast.get_docstring(node), fname
        body = ast.Module(body=node.body[1:], type_ignores=[])
        nums = [n.value for n in ast.walk(body) if isinstance(n, ast.Constant)
                and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)]
        assert nums == [], (fname, nums)
        src = ast.unparse(node)
        for bad in ("alpha", "SRCALPHA", "BLEND", "set_alpha"):
            assert bad not in src, (fname, bad)


def test_screen_surface_has_no_alpha(g):
    g.draw()
    assert not g.screen.get_flags() & pygame.SRCALPHA


# ======================= 2. 진급 경계와 여러 번 진급 =======================

@pytest.mark.parametrize("knowledge, grade, goal", [
    # (M단위) 진급 기준 2배
    (0, 1, 400), (399, 1, 400), (400, 2, 900), (899, 2, 900), (900, 3, 1500), (1499, 3, 1500),
    (1500, 4, 2200), (2199, 4, 2200),
])
def test_milestone_boundaries(knowledge, grade, goal):
    s = Student()
    s.knowledge = knowledge
    s.promote()
    assert s.get_grade() == grade
    assert s.get_next_goal() == goal
    assert not s.has_graduated() and s.get_ending() is None


@pytest.mark.parametrize("knowledge", [2200, 2201, 10000])   # (M단위) 졸업 지식 2200
def test_graduation_boundary_1100(knowledge):
    s = Student()
    s.elapsed = 123.0
    s.knowledge = knowledge
    assert s.promote() == 3            # 1 -> 4학년 3번. 졸업은 진급 수에 넣지 않는다
    assert s.has_graduated() and s.graduation_time == 123.0
    assert s.get_ending() == TOP


def test_1099_does_not_graduate_even_after_long_time(monkeypatch):
    for name in ("HEALTH_DECAY_PER_SEC", "MENTAL_DECAY_PER_SEC", "MENTAL_DECAY_PER_SEC_EXAM"):
        monkeypatch.setattr(config, name, 0)
    s = Student()
    s.knowledge = GOAL - 1               # (M단위) 2199
    s.promote()
    s.update(10000.0)
    s.promote()
    assert s.get_grade() == 4 and not s.has_graduated() and s.get_ending() is None


@pytest.mark.parametrize("start, end, count, grade", [
    # (M단위) 진급 기준 2배
    (0, 399, 0, 1), (0, 400, 1, 2), (0, 900, 2, 3), (0, 1600, 3, 4), (399, 1501, 3, 4),
    (400, 899, 0, 2), (899, 900, 1, 3), (899, 2199, 2, 4),
])
def test_multiple_promotions_at_once(start, end, count, grade):
    s = Student()
    s.knowledge = start
    s.promote()
    s.knowledge = end
    assert s.promote() == count
    assert s.get_grade() == grade
    assert s.promote() == 0            # 다시 불러도 더 오르지 않는다


def test_game_check_promotion_returns_count_and_notice(g):
    g.student.knowledge = 1600
    assert g.check_promotion() == 3
    assert g.student.get_grade() == 4
    assert g.promotion_notice == {"text": "4학년 진급!", "timer": config.EVENT_NOTICE_TIME,
                                  "good": True}
    assert g.check_promotion() == 0


def test_check_promotion_graduation_not_counted(g):
    reach_grade(g.student, 4)
    g.promotion_notice = None
    g.student.knowledge = GOAL
    assert g.check_promotion() == 0
    assert g.student.has_graduated()
    assert g.promotion_notice is None      # 졸업은 진급 알림이 아니다(엔딩 화면으로 간다)


def test_promotion_by_study_action(g):
    g.student.knowledge = 390               # (M단위) 2학년 목표 400
    assert g.do_action(STUDY)              # 0초: 평소 +10
    assert g.student.knowledge == 400 and g.student.get_grade() == 2
    assert g.promotion_notice["text"] == "2학년 진급!"


def test_promotion_by_auto_event(g, monkeypatch):
    """자동형 '교수님께 칭찬받았다'(지식 +15)로 목표를 넘으면 바로 진급."""
    g.student.knowledge = 390
    g.start_event(event_by_id("professor_praise"))
    assert g.student.knowledge == 405 and g.student.get_grade() == 2
    assert g.promotion_notice["text"] == "2학년 진급!"


def test_promotion_by_choice_option(g):
    """선택지 '공부한다'(지식 +10) 결과로 목표를 넘으면 진급."""
    g.student.knowledge = 395
    g.start_event(event_by_id("mt_invite"))
    g.update(config.EVENT_INPUT_DELAY)
    assert g.student.get_grade() == 1
    assert g.choose_option(config.CHOICE_SECOND)
    assert g.student.knowledge == 405 and g.student.get_grade() == 2
    assert g.promotion_notice["text"] == "2학년 진급!"


def test_promotion_by_auto_action_in_update(no_events):
    """자동 행동(2초마다)으로 지식이 목표에 닿으면 그 update 안에서 진급한다."""
    game = Game()
    press(game, pygame.K_RETURN)
    game.student.knowledge = 395
    game.student.feed()                      # (M단위) 든든함이 있어야 자동 행동이 공부를 고른다
    game.update(2.0)                         # 2초 자동 행동: 균형, 체력·멘탈 78 -> 공부 +10
    assert game.last_action == STUDY
    assert game.student.get_grade() == 2
    pygame.quit()


def test_no_demotion_after_rest(g):
    reach_grade(g.student, 2)
    assert g.student.knowledge == 400        # (M단위) 2학년 목표 400, 3학년 900
    g.do_action(REST)                        # 지식 -2
    assert g.student.knowledge == 398
    assert g.student.get_grade() == 2 and g.check_promotion() == 0
    assert g.student.get_goal_progress() == 0.0          # 구간 시작 아래 -> 0으로 자름
    assert g.student.get_knowledge_to_goal() == 502
    assert g.get_goal_text() == "다음 학년까지 지식 502"
    for _ in range(30):
        g.do_action(REST)
    assert g.student.knowledge == 338 and g.student.get_grade() == 2
    assert g.student.get_radius() == 60


def test_no_demotion_glasses_and_place_stay(g):
    reach_grade(g.student, 3)
    g.student.knowledge = 0
    g.check_promotion()
    assert g.student.has_glasses() and g.get_place() == config.PLACE_BY_GRADE[3]


def test_promote_noop_when_gauge_zero():
    for attr in ("health", "mental"):
        s = Student()
        s.knowledge = 2400
        setattr(s, attr, 0)
        assert s.promote() == 0
        assert s.get_grade() == 1 and not s.has_graduated()


# ======================= 3. 휴학이 졸업보다 먼저 =======================

@pytest.mark.parametrize("health, mental", [(5, 100), (100, 8), (5, 8)])
def test_dropout_beats_graduation_on_study(g, health, mental):
    reach_grade(g.student, 4)
    g.student.knowledge = GOAL - 5
    g.student.health, g.student.mental = health, mental
    g.do_action(STUDY)
    # (M단위) 체력 5는 피곤(30 미만): 공부 지식 x0.7 = +7, 아니면 +10. 어느 쪽이든 졸업 목표를 넘는다
    gain = 7 if health < config.LOW_GAUGE_LIMIT else 10
    assert g.student.knowledge == GOAL - 5 + gain
    assert g.ending == config.ENDING_LEAVE
    assert g.student.graduation_time is None
    assert g.graduation_bonus == 0


def test_dropout_beats_graduation_on_auto_event(g):
    """자동형 '감기 기운'(체력 -10)으로 0이 되는 판정에서 지식이 졸업 지식 이상이어도 휴학."""
    reach_grade(g.student, 4)
    g.student.knowledge = GOAL
    g.student.health = 10
    g.start_event(event_by_id("cold"))
    assert g.ending == config.ENDING_LEAVE


def test_dropout_beats_graduation_on_choice(g):
    """선택 '대기업 지원'(지식 +20, 멘탈 -15)으로 1100을 넘으면서 멘탈 0 -> 휴학."""
    reach_grade(g.student, 4)
    g.student.knowledge = GOAL - 10
    g.student.mental = 15
    g.start_event(event_by_id("job_fair"))
    g.update(config.EVENT_INPUT_DELAY)
    assert g.choose_option(config.CHOICE_FIRST)
    assert g.student.knowledge == GOAL + 10
    assert g.ending == config.ENDING_LEAVE


# ======================= 4. 졸업 시각과 등급 =======================

@pytest.mark.parametrize("seconds, ending", [
    # (M단위) 경계는 config 상수 기준(지금 290/720초)
    (0.0, TOP), (TOP_S, TOP), (TOP_S + 0.0000000001, TOP), (TOP_S + 0.0001, NORMAL),
    (TOP_S + 40, NORMAL), ((TOP_S + NORMAL_S) / 2, NORMAL),
    (NORMAL_S, NORMAL), (NORMAL_S + 0.0001, BARELY), (NORMAL_S * 10, BARELY),
])
def test_judge_ending_time_boundaries(seconds, ending):
    assert judge_ending(seconds) == ending


@pytest.mark.parametrize("frames, ending", [(TOP_S * 60, TOP), (TOP_S * 60 + 1, NORMAL),
                                            (NORMAL_S * 60, NORMAL), (NORMAL_S * 60 + 1, BARELY)])
def test_graduation_time_after_60fps_frames(g, frames, ending):
    """1/60초 프레임을 쌓은 소수 오차(399.9999…)에서도 경계(config 수석·무사 기준 초)가 맞게 판정된다."""
    for _ in range(frames - 1):
        g.student.health = g.student.mental = 100
        g.update(FRAME)
    reach_grade(g.student, 4)
    g.student.knowledge = config.GRADUATION_KNOWLEDGE
    g.update(FRAME)
    assert g.state == config.STATE_ENDING
    assert g.student.graduation_time == pytest.approx(frames / 60)
    assert g.ending == ending


@pytest.mark.parametrize("seconds, ending", [(float(TOP_S), TOP), (TOP_S + 40.0, NORMAL),
                                             ((TOP_S + NORMAL_S) / 2, NORMAL),
                                             (NORMAL_S + 40.0, BARELY)])
@pytest.mark.parametrize("fame", [0, 2])
def test_bonus_by_time_grade(g, seconds, ending, fame):
    g.fame = fame
    g.money = 5
    reach_grade(g.student, 4)
    g.student.elapsed = seconds
    g.student.knowledge = GOAL - 5
    g.do_action(STUDY)
    assert g.ending == ending
    assert g.student.graduation_time == seconds
    bonus = config.GRADUATION_BONUS[ending] * (10 + fame) // 10
    assert g.graduation_bonus == bonus
    assert g.money >= 5 + bonus


def test_graduation_time_excludes_dialog_pause(g):
    """대화창이 30초 떠 있어도 게임 시간은 멈추므로 졸업 시각에 들어가지 않는다.

    (11절 A안) 수석 200초에 맞춰 199초에서 시작(30초를 셌다면 229초로 무사가 된다).
    (M단위) 수석 기준 1초 전(TOP_S - 1)에서 시작한다.
    """
    reach_grade(g.student, 4)
    g.student.knowledge = GOAL - 10
    g.student.elapsed = TOP_S - 1.0
    g.student.health = g.student.mental = 100
    g.start_event(event_by_id("job_fair"))
    for _ in range(30 * 60):
        g.update(FRAME)
    assert g.student.elapsed == TOP_S - 1.0
    assert g.choose_option(config.CHOICE_SECOND)          # 대학원 상담: 지식 +10 -> 졸업 지식
    assert g.ending == TOP and g.student.graduation_time == TOP_S - 1.0



def test_best_record_is_cumulative_knowledge(g):
    g.best_record = 0
    reach_grade(g.student, 4)
    g.student.knowledge = GOAL + 134
    g.update(FRAME)
    assert g.state == config.STATE_ENDING
    assert g.best_record == GOAL + 134


# ======================= 5. 60초 주기 =======================

CYCLE_STARTS = [0, 60, 240, 300, 600, 2220]


@pytest.mark.parametrize("start", CYCLE_STARTS)
@pytest.mark.parametrize("t, season, tod, exam", [
    (0.0, "spring", "day", False), (8.99, "spring", "day", False),
    (9.0, "spring", "evening", False), (12.0, "spring", "night", False),
    (14.99, "spring", "night", False), (15.0, "summer", "day", False),
    (30.0, "autumn", "day", False), (44.99, "autumn", "night", False),
    (45.0, "winter", "day", True), (54.0, "winter", "evening", True),
    (57.0, "winter", "night", True), (59.99, "winter", "night", True),
])
def test_cycle_clock_over_many_cycles(g, start, t, season, tod, exam):
    """계절·시간대·시험 기간은 학년과 상관없이 60초 주기 안 시간으로 정한다(여러 주기 반복)."""
    g.student.elapsed = start + t
    assert g.student.get_cycle_index() == start // 60 + 1
    assert g.student.get_cycle_time() == pytest.approx(t)
    assert g.get_season() == season
    assert g.get_time_of_day() == tod
    assert g.student.is_exam_period() is exam
    assert g.student.get_grade() == 1


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
def test_cycle_clock_independent_of_grade(g, grade):
    reach_grade(g.student, grade)
    g.student.elapsed = 50.0
    assert g.get_season() == "winter" and g.student.is_exam_period()
    g.student.elapsed = 65.0
    assert g.get_season() == "spring" and not g.student.is_exam_period()


def test_cycle_index_by_frames():
    s = Student()
    s.health = s.mental = 10 ** 6
    for _ in range(3600):
        s.update(FRAME)
    assert s.get_cycle_index() == 2 and s.get_cycle_time() < 1e-6
    for _ in range(3600 * 3):
        s.update(FRAME)
    assert s.get_cycle_index() == 5


def test_exam_decay_and_study_in_later_cycles():
    s = Student()
    s.elapsed, s.health, s.mental = 584.0, 50, 50     # 10번 주기 44초
    s.update(1.0)                                     # 585초(주기 안 45초) 감소: 시험 기간
    assert (s.health, s.mental) == (49, 48)
    s.knowledge = 0
    s.study()
    assert s.knowledge == 20
    s.elapsed = 600.0                                 # 11번 주기 시작
    s.study()
    assert s.knowledge == 30


def test_exam_banner_by_cycle_after_240(g, monkeypatch):
    for elapsed, shown in ((285.0, True), (300.0, False), (705.0, True), (719.9, True),
                           (720.0, False)):
        g.student.elapsed = elapsed
        assert (config.EXAM_BANNER_TEXT in texts_of(g, monkeypatch)) is shown, elapsed


def test_exam_banner_spans_stage_and_not_goal_bar():
    banner = pygame.Rect(config.EXAM_BANNER_X, config.EXAM_BANNER_Y, config.EXAM_BANNER_WIDTH,
                         config.EXAM_BANNER_HEIGHT)
    assert (banner.left, banner.right) == (284, 788)
    assert (banner.left, banner.right) == (config.STAGE_X, config.STAGE_X + config.STAGE_WIDTH)
    goal_with_drop = GOAL_BOX.union(GOAL_BOX.move(0, P))
    banner_with_drop = banner.union(banner.move(0, P))
    assert not goal_with_drop.colliderect(banner_with_drop)
    assert goal_with_drop.bottom < config.PANEL_Y and banner_with_drop.bottom < config.PANEL_Y
    assert goal_with_drop.top >= config.INFO_BAR_HEIGHT


# ======================= 6. 이벤트: 주기마다 4~5회, 8초 간격 =======================

def _auto_play_log(game, until):
    """방치 플레이를 until 초까지(졸업하면 C 로 대학원) 돌리며 이벤트 기록을 모은다.

    게이지는 매 프레임 가득 채워 휴학하지 않게 한다(이벤트 규칙만 본다).
    기록: (게임 시각, 보장 여부, 직전 이벤트 시각, 주기 번호, 종류, 학년)
    """
    log = []
    real = game.start_event

    def logged(event):
        s = game.student
        log.append((s.elapsed, s.needs_guaranteed_event(), s.last_event_time,
                    s.get_cycle_index(), event[config.EVENT_KIND], s.get_grade(),
                    s.is_in_grad_school()))
        real(event)
    game.start_event = logged
    frames = 0
    while game.student.elapsed < until:
        frames += 1
        assert frames < until * 60 * 3
        if game.state == config.STATE_EVENT:
            if game.is_dialog_ready():
                game.choose_option(config.CHOICE_FIRST)
        elif game.state == config.STATE_ENDING:
            assert game.is_graduation_ending(), game.ending
            press(game, pygame.K_c)
        game.student.health = game.student.mental = 100
        game.update(FRAME)
    return log


@pytest.mark.parametrize("seed", range(5))
def test_events_min4_max5_per_cycle_and_gap_over_many_cycles(seeded, seed):
    """seed 5개 x 8주기(480초, 졸업 뒤 대학원 포함): 끝난 주기마다 4~5회, 확률 이벤트는 8초 간격."""
    game = seeded(seed)
    log = _auto_play_log(game, 480.0)
    counts = game.student.event_counts
    for cycle in range(1, 9):
        assert 4 <= counts.get(cycle, 0) <= 5, (seed, counts)
    assert sum(counts.values()) == len(log)
    for elapsed, guaranteed, last, cycle, _, _, _ in log:
        if not guaranteed and last is not None:
            assert elapsed - last >= config.EVENT_MIN_GAP - 1e-6, (seed, elapsed, last)
    times = [e[0] for e in log]
    assert times == sorted(times)
    # 대학원에서는 선택지형이 나오지 않는다
    assert all(kind == config.EVENT_KIND_AUTO for *_, kind, _, grad in log if grad)


def test_max5_in_late_cycle_then_resets(g, monkeypatch):
    monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 5)
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    g.student.elapsed = 482.0                         # 9번 주기
    for _ in range(8):
        g.student.last_event_time = None
        g.do_action(FEED)
    assert g.student.event_counts == {9: 5}
    g.student.elapsed = 540.0                         # 10번 주기
    g.do_action(FEED)
    assert g.student.event_counts == {9: 5, 10: 1}


def test_guarantee_by_cycle_time_in_late_cycle(g, monkeypatch):
    monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 5)
    monkeypatch.setattr(config, "EVENT_CHANCE", 0.0)
    g.student.elapsed = 600.0 + 11.24                 # 11번 주기, 구간 1 끝나기 직전
    assert not g.student.needs_guaranteed_event()
    g.student.elapsed = 600.0 + 11.25
    assert g.student.needs_guaranteed_event()
    g.student.event_counts[11] = 1
    assert not g.student.needs_guaranteed_event()
    g.student.elapsed = 600.0 + 59.0                  # 시험 기간: 끝난 구간 최대 4
    g.student.event_counts[11] = 4
    assert not g.student.needs_guaranteed_event()


@pytest.mark.parametrize("gap, fires", [(7.99, False), (8.0, True)])
def test_gap_continues_across_late_cycle_boundary(g, monkeypatch, gap, fires):
    monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 5)
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    monkeypatch.setattr(g, "pick_event", lambda: config.AUTO_EVENTS[1])
    g.student.elapsed = 418.0                         # 7번 주기 58초
    g.student.event_counts[7] = 4
    assert g.do_action(FEED) and g.student.last_event_time == 418.0
    g.student.elapsed = 418.0 + gap                   # 8번 주기(주기 안 6초 근처, 보장 없음)
    assert g.student.get_cycle_index() == 8 and not g.student.needs_guaranteed_event()
    g.do_action(FEED)
    assert g.student.event_counts.get(8, 0) == (1 if fires else 0)


@pytest.mark.parametrize("grade, elapsed, expected", [
    (1, 200.0, {"mt_invite", "club_fair", "morning_class"}),   # 4번 주기지만 1학년
    (2, 5.0, {"free_rider", "all_nighter", "study_group"}),    # 1번 주기지만 2학년
    (3, 400.0, {"confession", "exchange_student", "living_alone"}),
    (4, 5.0, {"job_fair", "thesis_stress"}),
])
def test_choice_events_use_current_grade(g, grade, elapsed, expected):
    g.student.elapsed = elapsed
    reach_grade(g.student, grade)
    choices, autos = g.get_event_candidates()
    assert {e[config.EVENT_ID] for e in choices} == expected
    assert autos == config.AUTO_EVENTS


def test_choice_candidates_follow_promotion_mid_cycle(g):
    g.student.elapsed = 20.0
    assert {e[config.EVENT_ID] for e in g.get_event_candidates()[0]} == \
        {"mt_invite", "club_fair", "morning_class"}
    g.student.knowledge = 900                # (M단위) 3학년 목표 900
    g.check_promotion()
    assert {e[config.EVENT_ID] for e in g.get_event_candidates()[0]} == \
        {"confession", "exchange_student", "living_alone"}


def test_scholarship_uses_current_grade(g):
    g.upgrades[config.UPGRADE_SCHOLARSHIP] = 1
    g.student.elapsed = 5.0
    reach_grade(g.student, 3)
    money = g.money
    g.start_event(config.SCHOLARSHIP_EVENT)
    assert g.money == money + 30 * 3


# ======================= 7. 대학원 =======================

# (M단위) 2배: 2200 + Σ(800 + 200(k-1))
@pytest.mark.parametrize("year, goal", [(0, 2200), (1, 3000), (2, 4000), (3, 5200), (4, 6600),
                                        (5, 8200)])
def test_grad_goals(year, goal):
    assert Student().get_grad_goal(year) == goal


def _graduate_and_enter(game, knowledge, seconds=250.0):
    reach_grade(game.student, 4)
    game.student.elapsed = seconds
    game.student.knowledge = knowledge
    game.check_promotion()
    game.check_ending()
    assert game.is_graduation_ending()
    press(game, pygame.K_c)
    assert game.state == config.STATE_PLAYING


@pytest.mark.parametrize("knowledge, year, notice", [
    # (M단위) 년차 목표 2배
    (2200, 1, None), (2999, 1, None), (3000, 2, "대학원 2년차!"), (3999, 2, "대학원 2년차!"),
    (4000, 3, "대학원 3년차!"), (5200, 4, "대학원 4년차!"),
])
def test_grad_entry_immediate_promotion(g, knowledge, year, notice):
    _graduate_and_enter(g, knowledge)
    assert g.grad_year == year
    assert g.student.elapsed == 250.0                 # 진학해도 시계는 이어진다
    assert g.student.graduation_time == 250.0
    if notice is None:
        assert g.promotion_notice is None
    else:
        assert g.promotion_notice["text"] == notice


@pytest.mark.parametrize("start, end, count, year", [
    (2200, 2999, 0, 1), (2200, 3000, 1, 2), (2200, 4000, 2, 3), (3000, 5199, 1, 3),
    (4000, 6600, 2, 5),
])
def test_grad_year_promotions(g, start, end, count, year):
    _graduate_and_enter(g, start)
    g.student.knowledge = end
    assert g.check_promotion() == count
    assert g.grad_year == year
    if count:
        assert g.promotion_notice["text"] == config.GRAD_PROMOTION_TEXT.format(year)


def test_grad_goal_text_and_progress(g, monkeypatch):
    _graduate_and_enter(g, 2600)             # (M단위) 2200 ~ 3000 구간의 절반
    assert g.get_goal_text() == "다음 년차까지 지식 400"
    assert g.student.get_goal_start() == 2200
    assert g.student.get_goal_progress() == pytest.approx(0.5)
    texts = texts_of(g, monkeypatch, "draw_info_bar")
    assert texts[:2] == ["대학원 1년차", "다음 년차까지 지식 400"]


def test_grad_time_alone_never_advances_year(g, monkeypatch):
    monkeypatch.setattr(config, "HEALTH_DECAY_PER_SEC", 0)
    monkeypatch.setattr(config, "MENTAL_DECAY_PER_SEC", 0)
    monkeypatch.setattr(config, "MENTAL_DECAY_PER_SEC_EXAM", 0)
    _graduate_and_enter(g, GOAL)
    g.update(600.0)
    assert g.grad_year == 1 and g.state == config.STATE_PLAYING
    assert g.student.elapsed == pytest.approx(850.0)


def test_grad_events_counted_by_cycle_after_entry(g, monkeypatch):
    _graduate_and_enter(g, GOAL, seconds=250.0)       # 5번 주기 10초
    monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 5)
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    g.student.last_event_time = None
    g.do_action(FEED)
    assert g.student.event_counts.get(5) == 1


# ======================= 8. 화면: 정보바·목표 막대·경과 시간 =======================

@pytest.mark.parametrize("knowledge, grade_text, goal_text", [
    # (M단위) 진급 기준 2배
    (0, "1학년", "다음 학년까지 지식 400"), (399, "1학년", "다음 학년까지 지식 1"),
    (400, "2학년", "다음 학년까지 지식 500"), (1499, "3학년", "다음 학년까지 지식 1"),
    (1500, "4학년", "졸업까지 지식 700"), (2199, "4학년", "졸업까지 지식 1"),
])
def test_info_bar_texts(g, monkeypatch, knowledge, grade_text, goal_text):
    g.student.knowledge = knowledge
    g.check_promotion()
    g.money = 345
    assert texts_of(g, monkeypatch, "draw_info_bar") == [
        grade_text, goal_text, f"지식 {knowledge}", "연구비 345"]


def _info_rects(font, grade_text, goal_text, money, knowledge):
    cy = config.INFO_TEXT_CENTER_Y
    grade = font.render(grade_text, False, (0, 0, 0)).get_rect(midleft=(config.INFO_BAR_MARGIN, cy))
    goal = font.render(goal_text, False, (0, 0, 0)).get_rect(midleft=(config.INFO_GOAL_X, cy))
    know = font.render(config.KNOWLEDGE_TEXT.format(config.KNOWLEDGE_LABEL, knowledge), False,
                       (0, 0, 0)).get_rect(midright=(config.SCREEN_WIDTH - config.INFO_BAR_MARGIN, cy))
    mon = font.render(config.MONEY_TEXT.format(config.MONEY_LABEL, money), False, (0, 0, 0))
    mon = mon.get_rect(midright=(know.left - config.INFO_ITEM_GAP, cy))
    return grade, goal, mon, know


@pytest.mark.parametrize("grade_text, goal_text, money, knowledge", [
    # (M단위) 진급·년차 목표 2배, 업그레이드 합계 92,590
    ("4학년", "다음 학년까지 지식 400", 92590, 2199),
    ("4학년", "졸업까지 지식 2200", 99999, 2199),
    ("대학원 12년차", "다음 년차까지 지식 3000", 99999, 99999),
    ("대학원 99년차", "다음 년차까지 지식 20400", 99999, 99999),
])
def test_info_bar_texts_fit_and_do_not_overlap(g, grade_text, goal_text, money, knowledge):
    """정보바 4개 글자가 상자 안쪽에 들어가고 서로 겹치지 않는다(현실적인 큰 값: 연구비 5자리,
    지식 5자리, 대학원 두 자리 년차)."""
    inner = pygame.Rect(config.INFO_BOX_X, config.INFO_BOX_Y, config.INFO_BOX_WIDTH,
                        config.INFO_BOX_HEIGHT).inflate(-2 * P, -2 * P)
    rects = _info_rects(g.font, grade_text, goal_text, money, knowledge)
    for r in rects:
        assert inner.contains(r), (r, inner)
    grade, goal, mon, know = rects
    assert grade.right < goal.left, (grade, goal)
    assert goal.right < mon.left, (goal, mon)
    assert mon.right < know.left


def test_goal_bar_box_position_and_pixels(g, monkeypatch):
    """목표 막대 상자는 (12, 64, 256x40) 도트 상자이고, 그리는 픽셀은 상자(+그림자 1칸) 안뿐이다."""
    assert (GOAL_BOX.x, GOAL_BOX.y, GOAL_BOX.w, GOAL_BOX.h) == (12, 64, 256, 40)
    g.student.knowledge = 100
    with_it, without = screen_without(g, monkeypatch, "draw_goal_bar")
    diff = changed_pixels(with_it, without)
    area = GOAL_BOX.union(GOAL_BOX.move(0, P))
    assert diff and all(area.collidepoint(p) for p in diff)
    assert texts_of(g, monkeypatch, "draw_goal_bar") == [config.GOAL_LABEL_TEXT]


def _yellow_span(game):
    game.draw()
    y = GOAL_BOX.centery
    xs = [x for x in range(GOAL_BOX.left, GOAL_BOX.right)
          if tuple(game.screen.get_at((x, y)))[:3] == config.COLOR_YELLOW]
    return len(xs), (min(xs) if xs else None)


def test_goal_bar_fill_follows_progress(g):
    g.student.elapsed = 5.0                           # 시험 기간 아님
    g.student.knowledge = 0
    assert _yellow_span(g)[0] == 0
    g.student.knowledge = 200                         # (M단위) 0~400 구간의 절반
    half, left_half = _yellow_span(g)
    g.student.knowledge = 399
    almost, _ = _yellow_span(g)
    reach_grade(g.student, 2)                         # 400: 새 구간(400~900)의 0
    assert _yellow_span(g)[0] == 0
    g.student.knowledge = 899
    full_ish, left_full = _yellow_span(g)
    assert half > 0 and half % P == 0 and almost % P == 0
    assert abs(almost - 2 * half) <= 2 * P
    assert left_half == left_full                     # 왼쪽부터 찬다
    assert full_ish >= almost


def test_goal_bar_full_when_ratio_one(g):
    g.student.knowledge = 399
    almost, _ = _yellow_span(g)
    g.student.grade = 1
    g.student.knowledge = 400                         # 진급 판정 전: 진행률 1 (M단위 목표 400)
    assert g.student.get_goal_progress() == 1.0
    full, _ = _yellow_span(g)
    assert full >= almost and full % P == 0


@pytest.mark.parametrize("elapsed, text", [(0.0, "경과 0분 0초"), (59.99, "경과 0분 59초"),
                                           (60.0, "경과 1분 0초"), (192.4, "경과 3분 12초"),
                                           (3725.0, "경과 62분 5초")])
def test_elapsed_time_text(g, monkeypatch, elapsed, text):
    g.student.elapsed = elapsed
    assert texts_of(g, monkeypatch, "draw_elapsed_time") == [text]


def test_elapsed_time_by_frames(g, monkeypatch):
    for _ in range(192 * 60):
        g.student.health = g.student.mental = 100
        g.update(FRAME)
    assert texts_of(g, monkeypatch, "draw_elapsed_time") == ["경과 3분 12초"]


@pytest.mark.parametrize("elapsed", [0.0, 192.0, 5999.0])
def test_elapsed_time_position(g, monkeypatch, elapsed):
    """경과 시간은 [업그레이드 U] 버튼 밑, 화면 안이고 버튼·자동 행동 안내와 겹치지 않는다."""
    g.student.elapsed = elapsed
    with_it, without = screen_without(g, monkeypatch, "draw_elapsed_time")
    diff = changed_pixels(with_it, without)
    assert diff
    box = bbox(diff)
    button = pygame.Rect(config.UPGRADE_BUTTON_X, config.UPGRADE_BUTTON_Y, config.BUTTON_WIDTH,
                         config.BUTTON_HEIGHT + 2 * P)        # 받침·눌림 자리까지
    assert box.top >= button.bottom
    assert box.bottom <= config.SCREEN_HEIGHT and box.right <= config.SCREEN_WIDTH
    assert button.left <= box.left and box.right <= button.right
    hint = g.small_font.render(config.AUTO_HINT_TEXT, False, (0, 0, 0)).get_rect(
        midtop=(config.BUTTON_START_X + config.POLICY_AREA_WIDTH // 2, config.AUTO_HINT_Y))
    bar = pygame.Rect(config.BUTTON_START_X, config.AUTO_BAR_Y, config.POLICY_AREA_WIDTH,
                      config.AUTO_BAR_HEIGHT)
    assert not box.colliderect(hint) and not box.colliderect(bar)


def test_format_time_function():
    assert format_time(0) == "0분 0초"
    assert format_time(59.999) == "0분 59초"
    assert format_time(239.99999999999) == "4분 0초"     # 소수 오차는 봐준다
    assert format_time(232.9) == "3분 52초"
    assert format_time(360) == "6분 0초"


# ======================= 9. 진급 알림 =======================

def test_promotion_notice_text_timer_and_expiry(g):
    g.student.knowledge = 900                # (M단위) 3학년 목표 900
    g.check_promotion()
    assert g.promotion_notice["text"] == "3학년 진급!"
    g.update(config.EVENT_NOTICE_TIME - 0.1)
    assert g.promotion_notice is not None
    g.update(0.2)
    assert g.promotion_notice is None


def test_promotion_notice_position_top_right_of_stage(g, monkeypatch):
    g.student.knowledge = 400                # (M단위) 2학년 목표 400
    g.check_promotion()
    g.update(config.EVENT_NOTICE_SLIDE_TIME + 0.05)   # 내려오는 연출이 끝난 자리
    monkeypatch.setattr(g, "get_student_lift", lambda: 0)
    with_it, without = screen_without(g, monkeypatch, "draw_promotion_notice")
    diff = changed_pixels(with_it, without)
    assert diff
    box = bbox(diff)
    assert STAGE_INNER.contains(box), box
    assert box.right <= config.PROMOTION_NOTICE_RIGHT + P
    assert box.right >= config.PROMOTION_NOTICE_RIGHT - P
    assert box.left > config.STUDENT_CENTER_X               # 오른쪽 위 구석
    assert box.top <= config.EVENT_NOTICE_Y + P
    texts = [t for t, f in record_texts(g, monkeypatch, "draw_promotion_notice")]
    assert texts == ["2학년 진급!"]


@pytest.mark.parametrize("event_id", ["side_dish", "deadline_alarm", "professor_praise"])
def test_promotion_notice_does_not_overlap_event_notice(g, monkeypatch, event_id):
    """자동형 알림(왼쪽 위)과 진급 알림(오른쪽 위)이 같이 떠도 겹치지 않는다."""
    event = event_by_id(event_id)
    g.student.knowledge = 390
    g.start_event(event)
    g.student.knowledge = 1600
    g.check_promotion()
    g.update(config.EVENT_NOTICE_SLIDE_TIME + 0.05)
    monkeypatch.setattr(g, "get_student_lift", lambda: 0)
    full, no_promo = screen_without(g, monkeypatch, "draw_promotion_notice")
    _, no_event = screen_without(g, monkeypatch, "draw_event_notice")
    promo = bbox(changed_pixels(full, no_promo))
    note = bbox(changed_pixels(full, no_event))
    assert not promo.colliderect(note), (promo, note)


def test_promotion_notice_cleared_on_new_game_and_ending(g):
    g.student.knowledge = 400                # (M단위) 2학년 목표 400
    g.check_promotion()
    g.end_game(config.ENDING_LEAVE)
    assert g.promotion_notice is None
    g.start_new_game()
    assert g.promotion_notice is None


# ======================= 10. 엔딩 화면: 졸업까지 걸린 시간 =======================

def _graduate_at(game, seconds):
    reach_grade(game.student, 4)
    game.student.elapsed = seconds
    game.student.knowledge = config.GRADUATION_KNOWLEDGE
    game.check_promotion()
    assert game.check_ending()


@pytest.mark.parametrize("seconds, text", [(232.9, "졸업까지 3분 52초"), (240.0, "졸업까지 4분 0초"),
                                           (361.5, "졸업까지 6분 1초")])
def test_ending_time_line_on_graduation(g, monkeypatch, seconds, text):
    _graduate_at(g, seconds)
    texts = texts_of(g, monkeypatch)
    assert text in texts
    assert g.ending in texts


def test_ending_time_line_not_on_leave_or_grad_completion(g, monkeypatch):
    g.student.health = 1
    g.update(1.0)
    assert g.ending == config.ENDING_LEAVE
    assert not any(t.startswith("졸업까지") for t in texts_of(g, monkeypatch))
    g.start_new_game()
    _graduate_at(g, 250.0)
    press(g, pygame.K_c)
    g.student.health = 0.5
    g.update(1.0)
    assert g.is_grad_school_ending()
    assert not any(t.startswith("졸업까지") for t in texts_of(g, monkeypatch))


@pytest.mark.parametrize("panel_open", [False, True])
def test_ending_time_line_layout(g, monkeypatch, panel_open):
    """걸린 시간 줄은 패널 안, 학사모·별·누적 지식 배지·보너스 글자와 겹치지 않는다(패널을 열어도)."""
    _graduate_at(g, 232.9)
    g.upgrade_panel_open = panel_open
    g.draw()
    with_line = g.screen.copy()
    saved = g.student.graduation_time
    g.student.has_graduated = lambda: False
    g.draw()
    without = g.screen.copy()
    del g.student.has_graduated
    assert g.student.graduation_time == saved and g.student.has_graduated()
    diff = changed_pixels(with_line, without)
    assert diff
    line = bbox(diff)
    panel_rect, center_x, _ = g.get_ending_layout()
    assert pygame.Rect(panel_rect).inflate(-2 * P, -2 * P).contains(line)
    assert abs(line.centerx - center_x) <= 2 * P
    cap_w, cap_h = sprite_size(config.CAP_SPRITE, config.CAP_PIXEL)
    cap = pygame.Rect(center_x - cap_w // 2, config.CAP_TOP_Y, cap_w, cap_h)
    assert not line.colliderect(cap)
    kw = g.font.size(config.ENDING_KNOWLEDGE_TEXT.format(g.student.knowledge))[0]
    badge = pygame.Rect(0, 0, kw + 2 * config.BADGE_PADDING_X, config.BADGE_HEIGHT + P)
    badge.midtop = (center_x, config.ENDING_KNOWLEDGE_Y - config.BADGE_HEIGHT // 2)
    assert not line.colliderect(badge)
    sw, sh = sprite_size(config.STAR_SPRITE, P)
    shift = center_x - config.SCREEN_CENTER_X
    for x, y, _ in config.ENDING_STARS:
        assert not line.colliderect(pygame.Rect(x + shift, y, sw, sh))
    if panel_open:
        assert not line.colliderect(pygame.Rect(config.UPGRADE_PANEL_RECT))


# ======================= 11. 한 판 흐름 =======================

def test_full_idle_round_promotes_in_order_and_graduates_by_time(seeded):
    """방치 한 판: 학년이 1->2->3->4 순서로(지식 200/450/750에서) 오르고 1100에서 졸업,
    등급은 걸린 시간과 같다. 자동 행동·이벤트가 켜진 실제 update 흐름."""
    game = seeded(7)
    game.set_policy(config.POLICY_STUDY_FOCUS)
    grades = [game.student.get_grade()]
    knowledge_at = {}
    frames = 0
    while game.state in (config.STATE_PLAYING, config.STATE_EVENT):
        frames += 1
        assert frames < 60 * 60 * 20
        if game.state == config.STATE_EVENT and game.is_dialog_ready():
            game.choose_option(config.CHOICE_FIRST)
        game.update(FRAME)
        grade = game.student.get_grade()
        if grade != grades[-1]:
            grades.append(grade)
            knowledge_at[grade] = game.student.knowledge
        assert grade >= grades[-1]
    if game.ending == config.ENDING_LEAVE:
        pytest.skip("이 시드는 휴학으로 끝남(밸런스 문제는 여기서 보지 않음)")
    assert grades == [1, 2, 3, 4]
    for grade, goal in zip((2, 3, 4), config.GRADE_GOALS):
        assert knowledge_at[grade] >= goal
    assert game.student.knowledge >= config.GRADUATION_KNOWLEDGE
    assert game.ending == judge_ending(game.student.graduation_time)
    assert game.student.graduation_time <= game.student.elapsed + 1e-9
