"""11절 A안 밸런스 검수: 대학원 주기 감소 항(c)과 대학원 연구비 배수 1.0.

기획서 11절 "대학원", jeja-spec 16절:
- 대학원 자연 감소 배수 = 1 + 0.5n + 1.0c. n = 대학원 년차,
  c = 대학원 진입 뒤 다 채운 60초 주기 수 = floor((elapsed - grad_entry_time) / 60). 학부는 1.
  건강 관리 배수 (1 - 0.1 x 레벨)와 곱한다.
- Student.grad_entry_time: 대학원에 들어간 순간의 elapsed(학부면 None). Student.get_grad_cycles().
- 대학원 연구비 배수 = 1 + 1.0n, 연구비 획득 배수 = (1 + 0.1 x 명성) x (1 + 1.0n).
- 밸런스 메모: 대학원 수료까지 업그레이드 없음 약 5분, 중간 약 8분, 최고 약 24분(끝이 있다).

이 파일은 conftest 의 AUTO_OFF_FILES / EVENTS_OFF_FILES 에 없다. 단위 테스트는 no_auto·no_events 를 직접 쓰고,
시뮬레이션은 자동 행동·이벤트를 켠 실제 흐름(시드 고정)으로 돈다.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
from conftest import graduate, press, reach_grade  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402

CARE = config.UPGRADE_HEALTH_CARE
STUDY = config.ACTION_STUDY
GRADUATIONS = (config.ENDING_TOP, config.ENDING_NORMAL, config.ENDING_BARELY)
ENTRY = 213.7          # 주기 경계가 아닌 진입 시각(주기 수가 진입 시각부터 세는지 본다)
SIM_DT = 0.1           # 시뮬레이션 한 걸음(초)
FIFTEEN_MINUTES = 15 * 60


@pytest.fixture
def quiet(no_auto, no_events):
    """자동 행동·이벤트를 끈다(값만 보는 단위 테스트용)."""
    yield
    pygame.quit()


def grad_student(entry=ENTRY, year=1):
    """entry 초에 졸업해 대학원에 들어간 Student. year 가 1보다 크면 지식 목표로 년차를 올린다(시간은 그대로)."""
    s = Student()
    graduate(s, entry)
    assert s.enter_grad_school()
    if year > config.GRAD_FIRST_YEAR:
        s.knowledge = s.get_grad_goal(year - 1)
        s.promote()
    assert s.grad_year == year
    assert s.elapsed == entry
    return s


# ======================= config =======================

def test_grad_cycle_constants():
    assert config.GRAD_DECAY_BONUS == 0.5
    assert config.GRAD_CYCLE_DECAY_BONUS == 1.0
    assert config.GRAD_CYCLES_NONE == 0
    assert config.GRAD_MONEY_BONUS == 1.0
    assert config.CYCLE_SECONDS == 60


# ======================= grad_entry_time =======================

def test_grad_entry_time_none_in_undergrad():
    s = Student()
    assert s.grad_entry_time is None
    s.elapsed = 500.0
    reach_grade(s, 4)
    assert s.grad_entry_time is None


@pytest.mark.parametrize("entry", [0.0, 60.0, ENTRY, 359.95, 1234.5])
def test_grad_entry_time_recorded_on_entry(entry):
    s = Student()
    graduate(s, entry)
    assert s.grad_entry_time is None            # 졸업만 해서는 기록하지 않는다
    assert s.enter_grad_school()
    assert s.grad_entry_time == entry
    s.update(100.0)                             # 시간이 흘러도 진입 시각은 그대로
    assert s.grad_entry_time == entry


def test_grad_entry_time_not_changed_by_failed_second_entry():
    s = grad_student()
    s.update(30.0)
    assert not s.enter_grad_school()            # 이미 대학원이면 다시 들어가지 않는다
    assert s.grad_entry_time == ENTRY


def test_enter_grad_school_refused_before_graduation():
    s = Student()
    s.elapsed = 100.0
    assert not s.enter_grad_school()
    assert s.grad_entry_time is None and s.get_grad_cycles() == 0


def test_game_c_key_records_entry_and_reincarnate_resets(quiet):
    """실제 흐름: 4학년 1090에서 공부로 졸업(ENTRY초) -> C -> 진입 시각 = 졸업 시각. R 환생이면 새 제자는 None."""
    g = Game()
    press(g, pygame.K_RETURN)
    s = g.student
    reach_grade(s, 4)
    s.elapsed, s.health, s.mental = ENTRY, 100, 100
    s.knowledge = config.GRADUATION_KNOWLEDGE - 10
    g.do_action(STUDY)
    assert g.state == config.STATE_ENDING and g.ending in GRADUATIONS
    g.update(5.0)                               # 엔딩 화면에 머문 시간은 흐르지 않는다
    press(g, pygame.K_c)
    assert g.state == config.STATE_PLAYING and g.grad_year == 1
    assert g.student.grad_entry_time == pytest.approx(ENTRY)
    g.update(60.0)
    assert g.student.get_grad_cycles() == 1
    g.student.health = 0.5
    g.update(1.0)
    assert g.state == config.STATE_ENDING
    press(g, pygame.K_r)                        # 환생 -> 새 신입생
    assert g.grad_year == 0
    assert g.student.grad_entry_time is None and g.student.get_grad_cycles() == 0


# ======================= get_grad_cycles =======================

@pytest.mark.parametrize("after, cycles", [
    (0.0, 0), (0.5, 0), (59.99, 0), (60.0, 1), (60.01, 1), (119.99, 1), (120.0, 2),
    (179.99, 2), (180.0, 3), (600.0, 10),
])
@pytest.mark.parametrize("entry", [240.0, ENTRY])
def test_grad_cycles_boundaries(entry, after, cycles):
    s = grad_student(entry)
    s.elapsed = entry + after
    assert s.get_grad_cycles() == cycles


def test_grad_cycles_after_60fps_frames():
    """1/60초 프레임 3600개(60초)를 쌓은 소수 오차에서도 진입 60초 뒤 c = 1."""
    s = grad_student(240.0)
    s.health = s.mental = 100
    for _ in range(60 * 60 - 1):
        s.update(1 / 60)
        s.health = s.mental = 100
    assert s.get_grad_cycles() == 0
    s.update(1 / 60)
    assert s.get_grad_cycles() == 1


def test_grad_cycles_counted_from_entry_not_cycle_clock():
    """c 는 60초 주기 시계(주기 번호)가 아니라 진입 시각부터 센다: 213.7초 진입 -> 240초 주기 경계에서도 0."""
    s = grad_student(ENTRY)
    s.elapsed = 240.0                           # 주기 번호는 4 -> 5 로 바뀌었지만
    assert s.get_cycle_index() == 5
    assert s.get_grad_cycles() == 0             # 대학원에서 60초를 다 채우지 않았다
    s.elapsed = ENTRY + 60.0
    assert s.get_grad_cycles() == 1


@pytest.mark.parametrize("elapsed", [0.0, 59.99, 60.0, 240.0, 1000.0, 99999.0])
def test_undergrad_grad_cycles_zero(elapsed):
    s = Student()
    s.elapsed = elapsed
    assert s.get_grad_cycles() == config.GRAD_CYCLES_NONE == 0
    assert s.get_grad_decay_ratio() == 1


def test_graduated_but_not_entered_cycles_zero():
    s = Student()
    graduate(s, 150.0)
    s.elapsed = 1000.0
    assert s.get_grad_cycles() == 0 and s.get_grad_decay_ratio() == 1


def test_grad_cycles_zero_when_entry_time_missing():
    """대학원 년차인데 진입 시각이 없으면(예전 방식으로 년차만 넣은 경우) c = 0."""
    s = Student()
    s.grad_year = 2
    s.elapsed = 600.0
    assert s.grad_entry_time is None
    assert s.get_grad_cycles() == 0
    assert s.get_grad_decay_ratio() == pytest.approx(2.0)


# ======================= 자연 감소 배수 1 + 0.5n + 1.0c =======================

@pytest.mark.parametrize("year, cycles, ratio", [
    (1, 0, 1.5), (1, 1, 2.5), (1, 2, 3.5), (2, 0, 2.0), (2, 1, 3.0), (2, 3, 5.0),
    (3, 1, 3.5), (4, 5, 8.0), (15, 24, 32.5),
])
def test_grad_decay_ratio_n_and_c(year, cycles, ratio):
    s = grad_student(240.0, year)
    s.elapsed = 240.0 + cycles * config.CYCLE_SECONDS + 1.0    # 주기 안 1초(시험 기간 아님)
    assert s.get_grad_cycles() == cycles
    assert s.get_grad_decay_ratio() == pytest.approx(ratio)
    assert s.get_health_decay() == pytest.approx(ratio)
    assert s.get_mental_decay() == pytest.approx(ratio)
    s.elapsed = 240.0 + cycles * config.CYCLE_SECONDS + 50.0   # 주기 안 50초: 시험 기간
    assert s.is_exam_period() and s.get_grad_cycles() == cycles
    assert s.get_mental_decay() == pytest.approx(2 * ratio)
    assert s.get_health_decay() == pytest.approx(ratio)


@pytest.mark.parametrize("year, cycles, care, ratio", [
    (1, 0, 1, 1.35), (1, 1, 5, 1.25), (2, 2, 2, 3.2), (3, 0, 5, 1.25), (1, 3, 1, 4.05),
    (4, 4, 3, 4.9),
])
def test_grad_decay_ratio_times_health_care(year, cycles, care, ratio):
    """(1 - 0.1 x 건강 관리) x (1 + 0.5n + 1.0c)."""
    s = grad_student(240.0, year)
    s.upgrades[CARE] = care
    s.elapsed = 240.0 + cycles * config.CYCLE_SECONDS + 1.0
    assert s.get_health_decay() == pytest.approx(ratio)
    assert s.get_mental_decay() == pytest.approx(ratio)
    assert s.get_health_decay() == pytest.approx(
        (1 - 0.1 * care) * (1 + 0.5 * year + 1.0 * cycles))


def test_actual_decay_switches_at_cycle_boundary():
    """240초 진입, 1년차: 241~299초 감소는 x1.5, 300·301초 감소는 c = 1 이라 x2.5."""
    s = grad_student(240.0)
    s.health = 100
    s.mental = 100
    s.update(61.0)
    assert s.elapsed == pytest.approx(301.0)
    assert s.health == pytest.approx(100 - 59 * 1.5 - 2 * 2.5)


def test_decay_ratio_uses_promoted_year_and_cycles_together():
    """1년차 진입 뒤 c = 2 일 때 지식으로 2년차가 되면 배수는 1 + 1.0 + 2.0 = 4.0."""
    s = grad_student(240.0)
    s.elapsed = 240.0 + 2 * config.CYCLE_SECONDS + 1.0
    assert s.get_grad_decay_ratio() == pytest.approx(3.5)
    s.knowledge = s.get_grad_goal(1)
    s.promote()
    assert s.grad_year == 2
    assert s.get_grad_decay_ratio() == pytest.approx(4.0)


def test_undergrad_decay_unaffected_by_long_time():
    """학부에는 시간 압박이 없다: 1000초가 지나도 감소는 1(건강 관리 2레벨이면 0.8)."""
    s = Student()
    s.elapsed = 1000.0 + 1.0
    assert s.get_health_decay() == 1
    s.upgrades[CARE] = 2
    assert s.get_health_decay() == pytest.approx(0.8)


# ======================= 연구비 배수 (1 + 0.1 x 명성) x (1 + 1.0n) =======================

@pytest.mark.parametrize("fame", [0, 1, 3, 10])
@pytest.mark.parametrize("year", [0, 1, 2, 5])
def test_money_multiplier_fame_times_grad(quiet, fame, year):
    g = Game()
    press(g, pygame.K_RETURN)
    g.fame = fame
    g.grad_year = year
    assert g.get_grad_money_multiplier() == pytest.approx(1 + 1.0 * year)
    assert g.get_money_multiplier() == pytest.approx((1 + 0.1 * fame) * (1 + 1.0 * year))


@pytest.mark.parametrize("fame, year, gain, earned", [
    (0, 1, 10, 20), (0, 2, 10, 30), (2, 1, 10, 24), (3, 2, 7, 27), (1, 4, 20, 110), (0, 0, 10, 10),
])
def test_grad_money_earned_floor(quiet, fame, year, gain, earned):
    """내림(오른 양 x (1 + 0.1 x 명성) x (1 + 1.0n)). 예: 3명성 2년차 지식 +7 -> 7 x 1.3 x 3 = 27.3 -> 27."""
    g = Game()
    press(g, pygame.K_RETURN)
    g.fame = fame
    g.grad_year = year
    before = g.student.knowledge
    g.student.knowledge = before + gain
    money = g.money
    assert g.earn_knowledge_money(before) == earned
    assert g.money == money + earned


def test_grad_cycles_do_not_change_money_multiplier(quiet):
    """주기 수 c 는 자연 감소에만 쓴다. 연구비 배수는 년차로만 정한다."""
    g = Game()
    press(g, pygame.K_RETURN)
    s = g.student
    reach_grade(s, 4)
    s.elapsed, s.health, s.mental = 240.0, 100, 100
    s.knowledge = config.GRADUATION_KNOWLEDGE
    g.update(0.0)
    assert g.state == config.STATE_ENDING
    press(g, pygame.K_c)
    m0 = g.get_money_multiplier()
    s = g.student
    s.elapsed = 240.0 + 3 * config.CYCLE_SECONDS + 1.0
    assert s.get_grad_cycles() == 3
    assert g.get_money_multiplier() == pytest.approx(m0) == pytest.approx(2.0)


# ======================= 대학원은 끝이 있다 (시드 고정 시뮬레이션) =======================

MID_LEVELS = {config.UPGRADE_MENU: 2, config.UPGRADE_BED: 2, config.UPGRADE_BOOK: 2,
              config.UPGRADE_TIME: 2, config.UPGRADE_HEALTH_CARE: 2, config.UPGRADE_LIBRARY: 1}
MAX_LEVELS = {u[config.UPGRADE_ID]: u[config.UPGRADE_MAX_LEVEL] for u in config.UPGRADES}


def run_until_not_playing(g, max_seconds):
    """균형 방침 방치: 선택지는 첫 번째. 게임 시간 max_seconds 안에 PLAYING/EVENT 를 벗어나면 멈춘다."""
    start = g.student.elapsed
    while g.student.elapsed - start < max_seconds:
        if g.state == config.STATE_EVENT:
            if not g.choose_option(config.CHOICE_FIRST):
                g.update(SIM_DT)
        elif g.state == config.STATE_PLAYING:
            g.update(SIM_DT)
        else:
            return


def grad_run(seed, levels, grad_limit):
    """levels 업그레이드로 졸업 -> C 대학원 -> 수료(또는 grad_limit 초)까지. (엔딩, 대학원에서 버틴 초, 년차)."""
    g = Game(seed=seed)
    g.upgrades.update(levels)
    press(g, pygame.K_RETURN)
    assert g.policy == config.POLICY_BALANCED
    run_until_not_playing(g, 3600)
    assert g.ending in GRADUATIONS, g.ending
    press(g, pygame.K_c)
    assert g.state == config.STATE_PLAYING and g.grad_year == 1
    entry = g.student.grad_entry_time
    assert entry == pytest.approx(g.student.graduation_time)
    run_until_not_playing(g, grad_limit)
    survived = g.student.elapsed - entry
    year = g.grad_year
    ending = g.ending
    pygame.quit()
    return ending, survived, year


@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("name, levels", [("none", {}), ("mid", MID_LEVELS)])
def test_grad_school_ends_within_15_minutes(seed, name, levels):
    """업그레이드 없음·중간이면 대학원 수료까지 15분 안(밸런스 메모: 약 5분·약 8분)."""
    ending, survived, year = grad_run(seed, levels, FIFTEEN_MINUTES)
    assert ending == config.ENDING_GRAD_TEXT.format(year), (name, seed, survived)
    assert survived < FIFTEEN_MINUTES, (name, seed, survived)
    if name == "mid":
        assert year >= 3, (seed, year)          # 중간 업그레이드는 3년차 이상(실측 4년차)


@pytest.mark.parametrize("seed", [0])
def test_grad_school_ends_with_max_upgrades(seed):
    """전부 최고 레벨이어도 끝이 있다(밸런스 메모: 약 24분, 14~16년차). 상한 40분."""
    ending, survived, year = grad_run(seed, MAX_LEVELS, 40 * 60)
    assert ending == config.ENDING_GRAD_TEXT.format(year), (seed, survived)
    assert 15 * 60 < survived < 40 * 60, (seed, survived)
    assert 10 <= year <= 20, (seed, year)


def test_without_cycle_term_grad_school_lasts_beyond_15_minutes(monkeypatch):
    """대조 실험: c 항을 0으로 끄면 업그레이드가 없어도 15분을 넘게 버틴다 -> 끝이 나는 것은 c 항 덕분이다."""
    monkeypatch.setattr(config, "GRAD_CYCLE_DECAY_BONUS", 0)
    ending, survived, _ = grad_run(0, {}, FIFTEEN_MINUTES)
    assert ending is None and survived >= FIFTEEN_MINUTES - SIM_DT
