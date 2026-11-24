"""I단위 검수: 졸업 후 환생(R, 명성+1)·대학원(C, 끝없이, 년차 배수)·엔딩 화면 분기
(기획서 10절 "졸업 후: 환생과 대학원", jeja-spec 15절).

(L단위, 기획서 11절) 졸업은 4학년에서 누적 지식 1100, 등급은 걸린 시간, 대학원 년차는 지식 목표
(1500 / 2000 / 2600 …)로 오른다. 60초 주기 시계는 대학원에서도 이어진다. 시간으로 년차가 오르던
테스트는 지식 목표로 바꿨다.

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
from conftest import graduate, press, reach_grade  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402

ROOT = Path(config.__file__).parent
FRAME = 1 / 60
FEED, REST, STUDY = config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY
CARE, MENU, SCHOL = config.UPGRADE_HEALTH_CARE, config.UPGRADE_MENU, config.UPGRADE_SCHOLARSHIP
GRADUATIONS = (config.ENDING_TOP, config.ENDING_NORMAL, config.ENDING_BARELY)


# ============================== 도우미 ==============================

def read_record(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


@pytest.fixture
def g(no_events, no_auto):
    """이벤트·자동 행동을 끈 채 타이틀에서 Enter 를 눌러 게임 중인 Game."""
    game = Game()
    press(game, pygame.K_RETURN)
    assert game.state == config.STATE_PLAYING
    yield game
    pygame.quit()


@pytest.fixture
def no_decay(monkeypatch):
    """체력·멘탈 자연 감소를 0으로 만든다(년차 진행만 보는 테스트용)."""
    monkeypatch.setattr(config, "HEALTH_DECAY_PER_SEC", 0)
    monkeypatch.setattr(config, "MENTAL_DECAY_PER_SEC", 0)
    monkeypatch.setattr(config, "MENTAL_DECAY_PER_SEC_EXAM", 0)


# (L단위) 예전 지식 기준(1000/750)과 같은 등급이 나오는 졸업 시각: 수석 200초, 무사 300초, 아슬아슬 400초
# (M단위) 시간 기준을 config 상수로 잡으므로 config 상수로: 수석 = 기준 초, 무사 = 두 기준 가운데, 아슬아슬 = 무사 기준 + 40
OLD_TOP_KNOWLEDGE, OLD_NORMAL_KNOWLEDGE = 1000, 750


def graduation_seconds_for(old_knowledge):
    """예전 테스트의 "지식 old_knowledge로 졸업"과 같은 등급이 나오는 졸업 시각(초)."""
    if old_knowledge >= OLD_TOP_KNOWLEDGE:
        return float(config.TOP_GRADUATE_SECONDS)
    if old_knowledge >= OLD_NORMAL_KNOWLEDGE:
        return (config.TOP_GRADUATE_SECONDS + config.NORMAL_GRADUATE_SECONDS) / 2
    return config.NORMAL_GRADUATE_SECONDS + 40.0


def graduate_with(game, knowledge, seconds=None):
    """게임 중 game 을 졸업시킨다(update 경로의 진급 판정).

    (L단위) 지식은 졸업 지식 1100 그대로(대학원 1년차 목표 1500 아래), 등급은 예전 지식 knowledge 와
    같은 등급이 나오는 졸업 시각으로 정한다. seconds 를 주면 그 시각에 졸업한다.
    """
    if seconds is None:
        seconds = graduation_seconds_for(knowledge)
    game.student.knowledge = config.GRADUATION_KNOWLEDGE
    game.student.elapsed = seconds - FRAME
    game.update(FRAME)
    assert game.state == config.STATE_ENDING
    assert game.ending in GRADUATIONS


def leave_with(game, knowledge=0):
    """게임 중 game 을 지식 knowledge 로 휴학시킨다(자연 감소로 체력 0)."""
    game.student.knowledge = knowledge
    game.student.health = 1
    game.update(1.0)
    assert game.ending == config.ENDING_LEAVE


def to_grad(game, knowledge=500):
    """졸업 엔딩에서 C 를 눌러 대학원 1년차 게임 화면으로 만든다."""
    graduate_with(game, knowledge)
    press(game, pygame.K_c)
    assert game.state == config.STATE_PLAYING
    assert game.grad_year == 1


def grad_student(year=1, cycles=None):
    """졸업한 Student 를 대학원 year 년차로 만든다(감소 없이 값만 맞춤).

    (L단위) 240초에 지식 1100으로 졸업 -> 대학원 진학 -> 년차 목표(1500, 2000 …)까지 지식을 넣어
    진급 판정으로 년차를 올린다. 경과 시간은 (4 + year - 1)번째 60초 주기의 시작으로 둔다.
    (11절 A안) 대학원 진입 시각(grad_entry_time)은 240초다. cycles 를 주면 경과 시간을
    240 + 60 x cycles 로 둬서 대학원 주기 수 c = cycles 가 된다(기본은 예전처럼 year - 1).
    년차 배수만 보는 테스트는 cycles=0 으로 c 항을 뺀다.
    """
    if cycles is None:
        cycles = year - 1
    s = Student()
    graduate(s, 240.0)
    assert s.enter_grad_school()
    assert s.grad_entry_time == 240.0
    s.elapsed = 240.0 + cycles * config.CYCLE_SECONDS
    if year > config.GRAD_FIRST_YEAR:
        s.knowledge = s.get_grad_goal(year - 1)
        s.promote()
    assert s.grad_year == year
    return s


def drop_in_grad(game):
    """대학원 게임 중 game 을 자연 감소로 체력 0이 되게 해 수료 엔딩을 낸다."""
    game.student.health = 0.5
    game.update(1.0)
    assert game.state == config.STATE_ENDING


def record_texts(game, monkeypatch):
    """game.draw() 를 한 번 하며 render_text 로 만든 (글자, 글꼴, Surface) 목록을 돌려준다."""
    made = []
    real = game_module.render_text

    def rec(font, text, *a, **k):
        surf = real(font, text, *a, **k)
        made.append((text, font, surf))
        return surf
    monkeypatch.setattr(game_module, "render_text", rec)
    game.draw()
    return made


def texts_of(made):
    return [text for text, _, _ in made]


def spec_money(gain, fame, year):
    """기획서: 내림(오른 양 x (1 + 0.1 x 명성) x (1 + 1.0 x 년차)) 를 정수 산술로 정확히.

    (11절 A안) 대학원 연구비 배수 0.25 -> 1.0. 예전 식은 gain * (10 + fame) * (4 + year) // 40.
    """
    return gain * (10 + fame) * (1 + year) // 10


# ======================= config 수치 =======================

def test_constants():
    assert config.GRAD_YEAR_UNDERGRAD == 0
    assert config.GRAD_FIRST_YEAR == 1
    assert config.GRAD_DECAY_BONUS == 1.0    # B안 승인(K단위 0.5, 그 전 0.25)
    assert config.GRAD_CYCLE_DECAY_BONUS == 2.5   # 개운함 조정: 대학원 주기 하나마다 +2.5 (B안 1.5, A안 1.0)
    assert config.GRAD_CYCLES_NONE == 0
    assert config.GRAD_MONEY_BONUS == 1.0    # 11절 A안 승인(K단위 0.25 -> 1.0)
    assert config.FAME_STEP == 1
    assert config.GRAD_YEAR_TEXT.format(3) == "대학원 3년차"
    assert config.ENDING_GRAD_TEXT.format(2) == "대학원 2년차 수료"
    assert "R" in config.REINCARNATE_HINT_TEXT and "환생" in config.REINCARNATE_HINT_TEXT
    assert "C" in config.GRAD_SCHOOL_HINT_TEXT and "대학원" in config.GRAD_SCHOOL_HINT_TEXT
    assert config.ENDING_LONG_FONT_SIZE == 44
    assert config.ENDING_NAME_MAX_WIDTH == 520
    panel = pygame.Rect(config.MENU_PANEL_RECT)
    assert config.ENDING_NAME_MAX_WIDTH <= panel.width
    assert panel.top < config.GRAD_SCHOOL_HINT_Y < panel.bottom
    assert config.GRAD_SCHOOL_HINT_Y > config.RESTART_HINT_Y


# ======================= 엔딩 화면 키 규칙 =======================

@pytest.mark.parametrize("knowledge", [100, 750, 1000])   # 아슬아슬 / 무사 / 수석
def test_r_on_graduation_reincarnates(g, knowledge):
    g.fame = 2
    graduate_with(g, knowledge)
    press(g, pygame.K_r)
    assert g.fame == 3
    assert g.state == config.STATE_PLAYING and g.ending is None
    assert g.grad_year == 0 and g.student.elapsed == 0 and g.student.knowledge == 0


@pytest.mark.parametrize("knowledge", [100, 750, 1000])   # 아슬아슬 / 무사 / 수석
def test_c_on_graduation_enters_grad_school(g, knowledge):
    g.fame = 2
    graduate_with(g, knowledge)
    press(g, pygame.K_c)
    assert g.state == config.STATE_PLAYING and g.ending is None
    assert g.grad_year == 1
    assert g.fame == 2                      # 대학원 진학은 명성을 올리지 않는다
    assert g.student.knowledge == config.GRADUATION_KNOWLEDGE   # (L단위) 졸업한 지식 그대로


def test_r_on_grad_ending_reincarnates(g):
    to_grad(g)
    drop_in_grad(g)
    assert g.is_grad_school_ending() and g.can_reincarnate()
    assert not g.is_graduation_ending()
    press(g, pygame.K_r)
    assert g.fame == 1
    assert g.state == config.STATE_PLAYING and g.grad_year == 0


def test_c_on_grad_ending_is_ignored(g):
    to_grad(g)
    drop_in_grad(g)
    ending = g.ending
    press(g, pygame.K_c)
    assert g.state == config.STATE_ENDING and g.ending == ending
    assert g.enter_grad_school() is False
    assert g.state == config.STATE_ENDING


def test_r_on_leave_restarts_without_fame(g):
    g.fame = 3
    leave_with(g, 50)
    assert not g.can_reincarnate() and not g.is_graduation_ending()
    assert not g.is_grad_school_ending()
    press(g, pygame.K_r)
    assert g.fame == 3
    assert g.state == config.STATE_PLAYING and g.ending is None
    assert g.student.knowledge == 0
    assert read_record(g.record_path)["fame"] == 3


def test_c_on_leave_is_ignored(g):
    leave_with(g)
    press(g, pygame.K_c)
    assert g.state == config.STATE_ENDING and g.ending == config.ENDING_LEAVE
    assert g.enter_grad_school() is False
    assert g.grad_year == 0


def test_c_and_r_ignored_on_title_and_playing(no_events, no_auto):
    game = Game()
    press(game, pygame.K_c)
    press(game, pygame.K_r)
    assert game.state == config.STATE_TITLE and game.fame == 0
    press(game, pygame.K_RETURN)
    game.update(1.0)
    press(game, pygame.K_c)
    press(game, pygame.K_r)
    assert game.state == config.STATE_PLAYING
    assert game.grad_year == 0 and game.fame == 0
    assert game.student.elapsed == pytest.approx(1.0)
    assert game.enter_grad_school() is False
    pygame.quit()


def test_c_r_ignored_in_grad_playing(g):
    to_grad(g)
    g.update(1.0)
    press(g, pygame.K_c)
    press(g, pygame.K_r)
    assert g.state == config.STATE_PLAYING and g.grad_year == 1 and g.fame == 0
    assert g.enter_grad_school() is False


def test_keys_work_with_upgrade_panel_open(g):
    graduate_with(g, 500)
    press(g, pygame.K_u)
    press(g, pygame.K_c)
    assert g.state == config.STATE_PLAYING and g.grad_year == 1
    assert g.upgrade_panel_open           # 패널 상태는 그대로
    drop_in_grad(g)
    press(g, pygame.K_r)
    assert g.fame == 1 and g.grad_year == 0


def test_u_toggles_panel_on_grad_ending(g):
    to_grad(g)
    drop_in_grad(g)
    press(g, pygame.K_u)
    assert g.upgrade_panel_open
    press(g, pygame.K_u)
    assert not g.upgrade_panel_open


# ======================= 대학원 진학: 그대로 이어지는 것 =======================

def test_enter_grad_school_keeps_everything(g):
    s = g.student
    g.upgrades[MENU] = 2
    s.health, s.mental = 63, 41
    s.add_trait("체력 단련")
    s.add_look(config.LOOK_HEADBAND)
    s.add_look(config.LOOK_GUITAR)
    s.add_flag("MT 참석")
    s.seen_events.add("mt_invite")
    s.event_counts[2] = 3
    g.money = 77
    graduate_with(g, 810)                 # (L단위) 무사 졸업 시각(예전 지식 810)
    before = dict(health=s.health, mental=s.mental, knowledge=s.knowledge,
                  traits=list(s.traits), looks=list(s.looks), flags=set(s.flags),
                  seen=set(s.seen_events), counts=dict(s.event_counts),
                  last=s.last_event_time)
    money = g.money
    assert money == 77 + 100              # 무사 졸업 보너스
    upgrades = g.upgrades
    press(g, pygame.K_c)
    assert g.student is s                 # 같은 제자
    assert s.health == before["health"] and s.mental == before["mental"]
    assert s.knowledge == config.GRADUATION_KNOWLEDGE
    assert s.traits == before["traits"] and s.looks == before["looks"]
    assert s.flags == before["flags"] and s.seen_events == before["seen"]
    assert s.event_counts == before["counts"]
    assert s.last_event_time == before["last"]
    assert g.money == money               # 진학으로 연구비가 바뀌지 않는다
    assert g.upgrades is upgrades and g.upgrades[MENU] == 2
    assert s.upgrades is g.upgrades
    # (L단위) 주기 시계는 이어서 흐른다
    assert s.elapsed == pytest.approx(graduation_seconds_for(810)) == s.graduation_time
    assert g.graduation_bonus == 0
    assert g.auto_timer == pytest.approx(g.get_auto_interval())
    assert g.notice is None and g.current_event is None


def test_enter_grad_school_student_rules():
    """(L단위) 졸업(지식 1100으로 graduation_time 기록)한 제자만 대학원에 간다. 시간은 상관없다."""
    s = Student()
    assert s.enter_grad_school() is False          # 졸업 전
    s.elapsed = 240.0
    assert s.enter_grad_school() is False          # 240초가 지나도 졸업 전이면 못 간다
    graduate(s, 240.0)
    s.health = 0
    assert s.enter_grad_school() is False          # 휴학 상태
    s.health = 50
    assert s.enter_grad_school() is True
    assert s.grad_year == 1 and s.is_in_grad_school()
    assert s.enter_grad_school() is False          # 이미 대학원
    assert s.grad_year == 1


# ======================= 년차 진행 경계 =======================

@pytest.mark.parametrize("year, goal", [(1, 3000), (2, 4000), (3, 5200), (4, 6600)])
def test_year_boundaries_by_knowledge(no_decay, year, goal):
    """(L단위, 예전 '60초마다 년차') n년차 -> n+1년차 목표 누적 지식.

    (M단위) 2배: 1500 / 2000 / 2600 / 3300 -> 3000 / 4000 / 5200 / 6600.
    """
    s = grad_student(year)
    assert s.get_next_goal() == goal
    s.knowledge = goal - 1
    assert s.promote() == 0 and s.grad_year == year
    s.knowledge = goal
    assert s.promote() == 1 and s.grad_year == year + 1


def test_time_alone_never_advances_year(no_decay):
    """(L단위, 예전 '3600프레임에 2년차') 시간만 흘러서는 년차가 오르지 않는다(주기 번호만 바뀐다)."""
    s = grad_student()
    for _ in range(3600):
        s.update(FRAME)
    s.promote()
    assert s.grad_year == 1
    assert s.get_cycle_index() == 6


@pytest.mark.parametrize("dt", [60, 119.9, 120, 150, 180, 600])
def test_large_dt_keeps_year_and_flows(no_decay, dt):
    """(L단위) 큰 dt 도 경과 시간만 늘리고 년차는 그대로다."""
    s = grad_student()
    s.update(dt)
    s.promote()
    assert s.grad_year == 1
    assert s.elapsed == pytest.approx(240.0 + dt)


# (M단위) 년차 목표 2배: 3000, 4000, 5200, 6600, 8200, … 10년차 -> 11년차 19200
@pytest.mark.parametrize("knowledge, year", [(2999, 1), (3000, 2), (4000, 3), (5199, 3),
                                             (5200, 4), (6600, 5), (19199, 10), (19200, 11),
                                             (20000, 11)])
def test_many_years_at_once(no_decay, knowledge, year):
    """(L단위) 지식이 한 번에 여러 년차 목표를 넘으면 그만큼 오른다(끝없이)."""
    s = grad_student()
    s.knowledge = knowledge
    s.promote()
    assert s.grad_year == year


def test_grad_grade_size_and_glasses_stay(no_decay):
    s = grad_student()
    for _ in range(5):
        s.update(60)
        s.knowledge = s.get_next_goal()      # (L단위) 년차는 지식으로 오른다
        s.promote()
        assert s.get_grade() == 4
        assert s.get_radius() == 60
        assert s.has_glasses()
    assert s.grad_year == 6


def test_grad_knowledge_to_goal(no_decay):
    """(L단위, 예전 '년차 남은 시간') 대학원 목표까지 남은 지식.

    (M단위) 1년차 2200 -> 3000 이라 800, 2년차 3000 -> 4000 이라 1000.
    """
    s = grad_student()
    assert s.get_knowledge_to_goal() == 800
    s.knowledge = 2999
    assert s.get_knowledge_to_goal() == 1
    s.knowledge = 3000
    s.promote()
    assert s.get_knowledge_to_goal() == 1000
    assert s.get_goal_start() == 3000


def test_game_update_continues_past_240(g, no_decay):
    to_grad(g)
    t0 = g.student.elapsed
    g.update(150)
    assert g.state == config.STATE_PLAYING
    assert g.student.elapsed == pytest.approx(t0 + 150)
    assert g.grad_year == 1               # (L단위) 시간만으로는 년차가 오르지 않는다


# ======================= 시험 기간 (년차마다 마지막 15초) =======================

@pytest.mark.parametrize("year", [1, 2, 3])
def test_exam_period_each_cycle_in_grad(no_decay, year):
    """(L단위) 대학원에서도 시험 기간은 60초 주기의 마지막 15초이고, 주기가 끝나도 년차는 그대로다."""
    s = grad_student(year)
    s.update(44.99)
    assert not s.is_exam_period()
    s.update(0.01)
    assert s.is_exam_period()
    s.update(14.99)
    assert s.is_exam_period() and s.grad_year == year
    s.update(0.01)
    assert not s.is_exam_period() and s.grad_year == year


def test_exam_study_bonus_in_grad(no_decay):
    s = grad_student()
    s.update(50)
    k = s.knowledge
    s.study()
    assert s.knowledge == k + 20


# ======================= 자연 감소 배수 =======================

# K단위: n년차 자연 감소 배수 = 1 + 0.5 x n (예전 0.25)
# (B안) 배수 = 1 + 1.0n + 1.5c. 년차 항만 보려고 c = 0(cycles=0)으로 둔다. c 항은 test_idle_grad_cycle.py
@pytest.mark.parametrize("year, ratio", [(1, 2.0), (2, 3.0), (3, 4.0), (4, 5.0)])
def test_grad_decay_ratio(year, ratio):
    s = grad_student(year, cycles=0)
    assert s.get_grad_decay_ratio() == pytest.approx(ratio)
    assert ratio == pytest.approx(1 + config.GRAD_DECAY_BONUS * year)
    assert s.get_health_decay() == pytest.approx(ratio)
    assert s.get_mental_decay() == pytest.approx(ratio)


def test_undergrad_decay_ratio_is_one():
    s = Student()
    assert s.get_grad_decay_ratio() == 1
    assert s.get_health_decay() == 1 and s.get_mental_decay() == 1


# (1 - 0.1 x 건강 관리) x (1 + 1.0 x 년차)  (B안)
@pytest.mark.parametrize("year, care, ratio", [(1, 2, 1.6), (2, 2, 2.4), (3, 5, 2.0),
                                               (1, 5, 1.0), (2, 1, 2.7)])
def test_grad_decay_with_health_care(year, care, ratio):
    s = grad_student(year, cycles=0)        # (11절 A안) c = 0: 주기 안 50초로 옮겨도 c 는 0
    s.upgrades[CARE] = care
    assert s.get_health_decay() == pytest.approx(ratio)
    assert s.get_mental_decay() == pytest.approx(ratio)
    s.elapsed = (s.get_cycle_index() - 1) * config.CYCLE_SECONDS + 50      # 시험 기간(주기 안 50초)
    assert s.get_mental_decay() == pytest.approx(2 * ratio)


def test_grad_actual_decay_one_second():
    s = grad_student(1)
    s.health = s.mental = 80
    s.update(1.0)
    assert s.health == pytest.approx(78.0)    # 80 - 1 x 2.0 (B안 1년차 배수)
    assert s.mental == pytest.approx(78.0)


def test_grad_decay_in_year2_exam():
    s = grad_student(2, cycles=0)           # (11절 A안) c = 0: 46초 동안 대학원 주기를 다 채우지 않는다
    s.health = s.mental = 100
    # (B안) 2년차 배수 3.0 이라 46초를 다 흘리면 0이 되므로 주기 안 30초에서 시작해 16초만 흘린다
    s.elapsed = 240.0 + 30.0
    s.update(16.0)
    # 주기 안 31~44초 시각의 감소(14번): 평소, 45·46초 시각의 감소: 시험 기간(멘탈 x2)
    # (학부와 같은 규칙: 감소가 일어난 시각으로 판정)
    assert s.get_grad_cycles() == 0
    assert s.health == pytest.approx(100 - 16 * 3.0)
    assert s.mental == pytest.approx(100 - 14 * 3.0 - 2 * 6.0)


def test_decay_after_year_promotion_uses_new_year():
    """(L단위) 지식으로 2년차가 되면 다음 감소부터 2년차 배수(B안 3.0)를 쓴다.

    (11절 A안) 예전 299.5 -> 300초는 진입(240초) 뒤 주기 하나를 채워 c = 1 이 되므로,
    c = 0 인 279.5 -> 280초로 옮겨 년차 항만 본다.
    """
    s = grad_student(1)
    s.elapsed = 279.5
    s.decay_timer = 0.5
    s.health = s.mental = 80
    s.knowledge = 3000                # (M단위) 2년차 목표 3000
    s.promote()
    s.update(0.5)                     # 280초 시각의 감소 -> 2년차, 시험 기간 아님, c = 0
    assert s.grad_year == 2
    assert s.health == pytest.approx(77.0)   # 2년차 배수 3.0 (1년차였다면 2.0)
    assert s.mental == pytest.approx(77.0)


# ======================= 연구비 배수 =======================

@pytest.mark.parametrize("fame", [0, 1, 3])
@pytest.mark.parametrize("year", [0, 1, 2, 3])
@pytest.mark.parametrize("gain", [1, 7, 10, 14, 20])
def test_money_multiplier_floor(g, fame, year, gain):
    g.fame = fame
    g.grad_year = year
    assert g.get_grad_money_multiplier() == pytest.approx(1 + 1.0 * year)   # 11절 A안
    before = g.student.knowledge
    g.student.knowledge = before + gain
    money = g.money
    earned = g.earn_knowledge_money(before)
    assert earned == spec_money(gain, fame, year)
    assert g.money == money + earned


def test_grad_study_earns_with_multiplier(g):
    g.fame = 2
    to_grad(g, 500)
    money = g.money
    g.do_action(STUDY)                       # 1년차 0초: 평소 공부 +10
    assert g.money == money + spec_money(10, 2, 1)   # 10 x 1.2 x 2.0 = 24 (11절 A안)
    assert spec_money(10, 2, 1) == 24


def test_grad_ending_no_bonus(g):
    to_grad(g, 700)
    money = g.money
    drop_in_grad(g)
    assert g.ending == config.ENDING_GRAD_TEXT.format(1)
    assert g.graduation_bonus == 0
    assert g.money == money


def test_scholarship_in_grad_is_30x4(no_auto, monkeypatch):
    game = Game(seed=1)
    press(game, pygame.K_RETURN)
    game.upgrades[SCHOL] = 1
    graduate_with(game, 500)
    press(game, pygame.K_c)
    game.fame = 5
    money = game.money
    game.start_event(config.SCHOLARSHIP_EVENT)
    assert game.money == money + 30 * 4      # 리드 승인: 학년 4 고정, 명성·대학원 배수 없음
    pygame.quit()


# ======================= 대학원 이벤트 =======================

def test_no_choice_candidates_in_grad():
    s = grad_student()
    s.flags.update({config.FLAG_MT, config.FLAG_BAND, config.FLAG_LOVE})
    choices = [e for e in config.CHOICE_EVENTS if s.can_see_event(e)]
    autos = [e for e in config.AUTO_EVENTS if s.can_see_event(e)]
    assert choices == []
    assert len(autos) == len(config.AUTO_EVENTS)
    # 같은 상태라도 학부 4학년이면 선택지형이 후보에 있다
    u = Student()
    u.elapsed = 200
    reach_grade(u, 4)   # (L단위) 4학년은 지식으로
    assert any(u.can_see_event(e) for e in config.CHOICE_EVENTS)


@pytest.mark.parametrize("seed", range(12))
def test_grad_auto_events_min4_max5_per_year(seed, monkeypatch):
    game = Game(seed=seed)
    press(game, pygame.K_RETURN)
    monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 0)   # 학부는 이벤트 없이 바로 졸업
    graduate_with(game, 500, seconds=240.0)    # (L단위) 240초 졸업 -> 대학원은 5번 주기부터
    monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 5)
    press(game, pygame.K_c)
    seen_state_event = False
    step = 0.1
    for _ in range(int(180 / step) + 1):
        game.student.health = game.student.mental = 100
        game.update(step)
        if game.state == config.STATE_EVENT:
            seen_state_event = True
            game.dialog_time = 1.0
            game.choose_option(0)
        assert game.state == config.STATE_PLAYING
    assert not seen_state_event
    assert game.grad_year >= 1   # (L단위) 년차는 자동 공부로 번 지식에 따라 오른다
    counts = game.student.event_counts
    for key in (5, 6, 7):
        assert config.EVENT_MIN_PER_GRADE <= counts.get(key, 0) <= config.EVENT_MAX_PER_GRADE, \
            (seed, key, counts)
    for key in (1, 2, 3, 4):
        assert counts.get(key, 0) == 0           # 학부 칸은 건드리지 않는다
    pygame.quit()


def test_grad_event_gap_and_counter_uses_cycle_key(no_decay):
    """(L단위) 대학원 이벤트 수도 60초 주기 번호로 센다: 2년차를 300초(6번 주기)에 시작."""
    s = grad_student(2)
    s.update(1.0)
    s.count_event()
    assert s.event_counts[6] == 1
    assert s.last_event_time == pytest.approx(301)
    s.update(7.0)
    assert not s.is_event_gap_passed()
    s.update(1.0)
    assert s.is_event_gap_passed()
    s.event_counts[6] = 5
    assert not s.can_have_event()
    s.update(60)
    assert s.get_cycle_index() == 7 and s.can_have_event()
    assert s.grad_year == 2


# ======================= 대학원 수료 엔딩 =======================

def test_grad_ending_text_by_year(g):
    to_grad(g)
    g.student.knowledge = 3000             # (L단위) 2년차는 지식 1500 -> M단위 3000
    g.update(1.0)
    assert g.grad_year == 2
    drop_in_grad(g)
    assert g.ending == "대학원 2년차 수료"
    assert g.is_grad_school_ending()


def test_grad_ending_by_mental(g):
    to_grad(g)
    g.student.mental = 0.5
    g.update(1.0)
    assert g.ending == config.ENDING_GRAD_TEXT.format(1)


def test_grad_ending_by_study_action(g):
    to_grad(g)
    g.student.mental = 5
    g.do_action(STUDY)
    assert g.state == config.STATE_ENDING
    assert g.ending == config.ENDING_GRAD_TEXT.format(1)


def test_grad_ending_saves_record_and_best(g):
    g.fame = 1
    g.best_record = 100
    to_grad(g, 500)
    g.student.knowledge = 2800             # (M단위) 졸업 2200 보다 크고 2년차 3000 보다 작게
    drop_in_grad(g)
    assert g.best_record == 2800
    data = read_record(g.record_path)
    assert data["best_knowledge"] == 2800
    assert data["money"] == g.money
    assert data["fame"] == 1


def test_grad_ending_does_not_lower_best(g):
    g.best_record = 5000
    to_grad(g, 500)
    drop_in_grad(g)
    assert g.best_record == 5000
    assert read_record(g.record_path)["best_knowledge"] == 5000


# ======================= 환생 =======================

def test_reincarnate_persists_and_resets_round(g):
    g.upgrades[MENU] = 3
    g.money = 40
    g.set_policy(config.POLICY_STUDY_FOCUS)
    g.student.add_trait("체력 단련")
    graduate_with(g, 1000)                    # 수석 졸업 보너스 200
    old_student = g.student
    money = g.money
    assert money == 240
    press(g, pygame.K_r)
    assert g.fame == 1
    data = read_record(g.record_path)
    assert data["fame"] == 1 and data["money"] == money
    assert data["upgrades"][MENU] == 3
    assert g.money == money and g.upgrades[MENU] == 3
    s = g.student
    assert s is not old_student
    assert s.upgrades is g.upgrades
    assert (s.health, s.mental, s.knowledge) == (config.HEALTH_START, config.MENTAL_START,
                                                 config.KNOWLEDGE_START)
    assert s.traits == [] and s.looks == [] and s.flags == set()
    assert s.grad_year == 0 and s.elapsed == 0
    assert g.policy == config.POLICY_START
    assert g.graduation_bonus == 0
    # 새 Game 이 파일에서 명성을 읽는다
    other = Game()
    assert other.fame == 1 and other.money == money


def test_reincarnate_twice_and_fame_multiplier(g):
    graduate_with(g, 100)
    press(g, pygame.K_r)
    graduate_with(g, 100)
    press(g, pygame.K_r)
    assert g.fame == 2
    assert read_record(g.record_path)["fame"] == 2
    assert g.get_money_multiplier() == pytest.approx(1.2)


def test_reincarnate_from_grad(g):
    to_grad(g)
    g.update(121.0)
    drop_in_grad(g)
    press(g, pygame.K_r)
    assert g.fame == 1 and g.grad_year == 0
    assert g.get_money_multiplier() == pytest.approx(1.1)
    assert g.student.get_grade() == 1


# ======================= 학부 240초 규칙은 그대로 =======================

def test_undergrad_time_no_longer_stops_at_240(no_decay):
    """(L단위, 예전 '학부는 240초에서 멈춤') 학부도 시간이 계속 흐르고, 지식이 없으면 1학년 그대로다."""
    s = Student()
    s.update(300)
    assert s.elapsed == pytest.approx(300)
    assert s.get_grade() == 1 and not s.has_graduated()
    assert s.get_ending() is None
    s.update(10)
    assert s.elapsed == pytest.approx(310)
    assert s.grad_year == 0


def test_undergrad_frames_reach_240():
    """(L단위) 1/60초 x 14400프레임 = 240초가 흘러도 졸업이 아니다(4번째 주기가 끝나고 5번째 시작)."""
    s = Student()
    s.health = s.mental = 10 ** 6   # 감소에 상관없이 시간만 본다
    for _ in range(240 * 60):
        s.update(FRAME)
    assert s.elapsed == pytest.approx(240.0)
    assert not s.has_graduated() and s.get_cycle_index() == 5


def test_undergrad_cycle_index_and_time():
    """(L단위, 예전 학년 키) 주기 번호 = 경과 // 60 + 1, 주기 안 시간 = 경과 % 60. 학년과 무관."""
    s = Student()
    for t, cycle in [(0, 1), (59.9, 1), (60, 2), (120, 3), (180, 4), (239.9, 4), (240, 5),
                     (659.5, 11)]:
        s.elapsed = t
        assert s.get_cycle_index() == cycle
        assert s.get_cycle_time() == pytest.approx(t - (cycle - 1) * 60)
        assert s.get_grade() == 1


def test_undergrad_graduation_still_works(g, no_decay):
    """(L단위) 4학년에서 지식이 1100에 닿는 순간 졸업. 시간이 흐르는 것만으로는 졸업하지 않는다."""
    g.student.knowledge = config.GRADUATION_KNOWLEDGE - 1
    g.update(199.99)                          # (11절 A안) 수석 200초 이하에 맞춰 240 -> 200초
    assert g.state == config.STATE_PLAYING and g.student.get_grade() == 4
    g.student.knowledge = config.GRADUATION_KNOWLEDGE
    g.update(0.01)
    assert g.ending == config.ENDING_TOP and g.grad_year == 0
    assert g.student.graduation_time == pytest.approx(200.0)



# ======================= 화면: 정보바·엔딩 안내·긴 이름 =======================

def test_info_bar_shows_grad_year(g, monkeypatch, no_decay):
    texts = texts_of(record_texts(g, monkeypatch))
    assert "1학년" in texts
    to_grad(g)
    texts = texts_of(record_texts(g, monkeypatch))
    assert "대학원 1년차" in texts
    # (L단위) "남은 시간" -> "다음 년차까지 지식 n" (M단위: 2200 -> 3000)
    assert config.NEXT_GRAD_YEAR_TEXT.format(800) in texts
    assert "4학년" not in texts
    g.student.knowledge = 3100             # (M단위) 2년차(3000 이상), 3년차 목표 4000
    g.update(1.0)
    texts = texts_of(record_texts(g, monkeypatch))
    assert "대학원 2년차" in texts
    assert config.NEXT_GRAD_YEAR_TEXT.format(900) in texts


@pytest.mark.parametrize("knowledge", [100, 750, 1000])   # 아슬아슬 / 무사 / 수석
def test_graduation_ending_hints(g, monkeypatch, knowledge):
    graduate_with(g, knowledge)
    texts = texts_of(record_texts(g, monkeypatch))
    assert g.ending in texts
    assert config.REINCARNATE_HINT_TEXT in texts
    assert config.GRAD_SCHOOL_HINT_TEXT in texts
    assert config.RESTART_HINT_TEXT not in texts
    assert config.GRADUATION_BONUS_TEXT.format(g.graduation_bonus) in texts


def test_grad_ending_hints(g, monkeypatch):
    to_grad(g)
    drop_in_grad(g)
    texts = texts_of(record_texts(g, monkeypatch))
    assert config.ENDING_GRAD_TEXT.format(1) in texts
    assert config.REINCARNATE_HINT_TEXT in texts
    assert config.GRAD_SCHOOL_HINT_TEXT not in texts
    assert config.RESTART_HINT_TEXT not in texts
    assert not any(t.startswith("졸업 보너스") for t in texts)


def test_leave_ending_hints(g, monkeypatch):
    leave_with(g)
    texts = texts_of(record_texts(g, monkeypatch))
    assert config.RESTART_HINT_TEXT in texts
    assert config.REINCARNATE_HINT_TEXT not in texts
    assert config.GRAD_SCHOOL_HINT_TEXT not in texts
    assert not any(t.startswith("졸업 보너스") for t in texts)


@pytest.mark.parametrize("year", [1, 9, 12, 99, 999])
def test_long_ending_name_fits(g, monkeypatch, year):
    to_grad(g)
    g.grad_year = year
    drop_in_grad(g)
    name = config.ENDING_GRAD_TEXT.format(g.grad_year)
    assert g.ending == name
    made = [m for m in record_texts(g, monkeypatch) if m[0] == name]
    assert len(made) >= 2, "엔딩 이름(그림자+글자)이 그려지지 않음"
    panel = pygame.Rect(config.MENU_PANEL_RECT)
    # 마지막 두 개 = 화면에 실제로 찍히는 그림자 글자와 본 글자(앞의 것은 폭을 재 본 큰 글씨일 수 있다)
    for _, font, surf in made[-2:]:
        assert surf.get_width() <= config.ENDING_NAME_MAX_WIDTH
        assert surf.get_width() <= panel.width
        if g.title_font.size(name)[0] > config.ENDING_NAME_MAX_WIDTH:
            assert font is g.ending_font
        else:
            assert font is g.title_font


@pytest.mark.parametrize("ending", GRADUATIONS + (config.ENDING_LEAVE,))
def test_short_ending_names_keep_big_font(g, monkeypatch, ending):
    g.end_game(ending)
    made = [m for m in record_texts(g, monkeypatch) if m[0] == ending]
    assert made and all(font is g.title_font for _, font, _ in made)


def test_draw_grad_playing_smoke(g):
    to_grad(g)
    # K단위: 1년차 감소 배수 1.5 라 80 으로는 60초를 못 버틴다. 건강 관리 5레벨(x0.5) + 가득 찬 게이지로
    # 2년차까지 살아남게 한다(1년차 60초 체력 45 소모, 2년차 15초 15 소모)
    g.upgrades[CARE] = 5
    g.student.health = g.student.mental = 100
    g.student.knowledge = 3000            # (L단위) 2년차 목표 (M단위 3000)
    for _ in range(3):
        g.update(25)
        g.draw()
    assert g.grad_year == 2


# ======================= 코드 규칙 =======================

I_FUNCTIONS = {
    # (L단위) get_grad_year_end·advance_grad_year·get_term_start·get_term_key 삭제 ->
    # 년차 목표(get_grad_goal)·진급 판정(promote)·60초 주기(get_cycle_index·get_cycle_time)
    "student.py": ["is_in_grad_school", "enter_grad_school", "get_grad_goal", "promote",
                   "get_cycle_index", "get_cycle_time", "get_grad_decay_ratio"],
    "game.py": ["grad_year", "is_graduation_ending", "is_grad_school_ending", "can_reincarnate",
                "reincarnate", "enter_grad_school", "get_grad_money_multiplier", "check_promotion",
                "draw_big_text", "draw_ending", "draw_info_bar"],
}


def _defs(name):
    tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]


@pytest.mark.parametrize("name", list(I_FUNCTIONS))
def test_i_functions_have_docstrings(name):
    defs = _defs(name)
    for fname in I_FUNCTIONS[name]:
        found = [d for d in defs if d.name == fname]
        assert found, fname
        for d in found:
            assert ast.get_docstring(d), fname


@pytest.mark.parametrize("name", list(I_FUNCTIONS))
def test_i_functions_no_alpha(name):
    for d in _defs(name):
        if d.name in I_FUNCTIONS[name]:
            src = ast.unparse(d)
            for bad in ("alpha", "SRCALPHA", "BLEND"):
                assert bad not in src, (d.name, bad)


def test_no_magic_grad_numbers():
    """대학원 관련 함수에 0.25·240·300 같은 숫자를 직접 쓰지 않는다(config 상수 사용)."""
    for name, funcs in I_FUNCTIONS.items():
        for d in _defs(name):
            if d.name not in funcs:
                continue
            for node in ast.walk(d):
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                        and not isinstance(node.value, bool):
                    assert node.value in (0, 1), (name, d.name, node.value)
