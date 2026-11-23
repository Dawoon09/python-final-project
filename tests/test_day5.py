"""5일차 검수: 타이틀/엔딩 화면(기능 10), 휴학 엔딩(기능 9), 시험 기간(기능 11), 졸업 엔딩(기능 12).

완료 기준: 처음부터 끝까지 한 판을 플레이할 수 있음.

(L단위, 기획서 11절) 판에 시간 제한이 없다. 졸업은 4학년에서 누적 지식 1100 이상이 되는 순간이고,
등급은 졸업까지 걸린 시간(200초 이하 수석 / 360초 이하 무사 / 초과 아슬아슬, 11절 A안)으로 정한다.
시험 기간은 60초 주기의 마지막 15초다. 240초 제한을 전제로 한 테스트는 새 규칙으로 바꿨다.
"""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import random  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
import student as student_module  # noqa: E402
from conftest import press, reach_grade  # noqa: E402
from game import Game  # noqa: E402
from student import Student, judge_ending  # noqa: E402
from button import sprite_size  # noqa: E402

FRAME = 1 / 60
# (L단위) 60초 주기의 시작 시각. 240초 이후에도 주기가 계속 이어진다
CYCLE_STARTS = [0, 60, 120, 180, 240, 300]
GRADUATIONS = (config.ENDING_TOP, config.ENDING_NORMAL, config.ENDING_BARELY)


@pytest.fixture
def title_game():
    """막 켠(타이틀 화면) Game."""
    g = Game()
    yield g
    pygame.quit()


class RecordingFont:
    """render에 넘긴 글자를 기록하는 폰트 래퍼."""

    def __init__(self, font):
        self.font = font
        self.texts = []

    def render(self, text, *args, **kwargs):
        self.texts.append(text)
        return self.font.render(text, *args, **kwargs)


def color(surf, x, y):
    return tuple(surf.get_at((x, y)))[:3]


def snapshot(g):
    s = g.student
    # (G단위) 쿨타임 대신 자동 행동 시계·방침·마지막 행동을 본다
    return (s.health, s.mental, s.knowledge, s.elapsed, s.decay_timer, g.auto_timer,
            g.policy, g.last_action, g.state, g.ending)


def click(g, pos):
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def button_center(g, name):
    return g.buttons[name].rect.center


def force_ending_by_study(g):
    """게임 중 Game을 공부 행동으로 휴학 엔딩에 보낸다(체력 5 -> 0)."""
    g.student.health = 5
    assert g.do_action(config.ACTION_STUDY)
    assert g.state == config.STATE_ENDING


def count_color(surf, rgb, rect):
    n = 0
    for x in range(rect.left, rect.right):
        for y in range(rect.top, rect.bottom):
            if color(surf, x, y) == rgb:
                n += 1
    return n


# ======================= config 값 =======================

def test_config_values():
    assert config.START_STATE == config.STATE_TITLE
    assert config.CYCLE_SECONDS == 60   # (L단위) TOTAL_SECONDS·SECONDS_PER_GRADE 삭제
    assert config.EXAM_SECONDS == 15
    assert config.MENTAL_DECAY_PER_SEC_EXAM == 2 and config.MENTAL_DECAY_PER_SEC == 1
    assert config.STUDY_KNOWLEDGE_EXAM == 20 and config.STUDY_KNOWLEDGE == 10
    # (L단위) 졸업 기준: 지식 1000/750 -> 걸린 시간 200/360초(11절 A안, 수석 240 -> 200), 졸업 지식 1100
    assert config.TOP_GRADUATE_SECONDS == 200 and config.NORMAL_GRADUATE_SECONDS == 360
    assert config.GRADUATION_KNOWLEDGE == 1100
    assert (config.ENDING_LEAVE, config.ENDING_TOP, config.ENDING_NORMAL,
            config.ENDING_BARELY) == ("휴학", "수석 졸업", "무사 졸업", "아슬아슬 졸업")
    assert config.EXAM_BANNER_TEXT == "시험 기간! 공부 효과 2배, 멘탈 감소 2배"
    assert config.START_HINT_TEXT == "Enter를 눌러 시작"
    assert config.RESTART_HINT_TEXT == "R을 눌러 다시 하기"


# ======================= 기능 10: 화면 전환 =======================

def test_starts_on_title(title_game):
    assert title_game.state == config.STATE_TITLE
    assert title_game.ending is None


def test_enter_starts_new_game(title_game):
    g = title_game
    press(g, pygame.K_RETURN)
    s = g.student
    assert g.state == config.STATE_PLAYING
    assert (s.health, s.mental, s.knowledge) == (80, 80, 0)
    assert s.get_grade() == 1 and s.elapsed == 0 and s.decay_timer == 0
    assert g.ending is None
    # (G단위) 쿨타임 0 대신: 방침은 균형, 자동 행동 시계는 꽉 참, 아직 행동 없음
    assert g.policy == config.POLICY_START
    assert g.auto_timer == config.AUTO_ACTION_INTERVAL
    assert g.last_action is None


def test_numpad_enter_ignored_on_title(title_game):
    before = snapshot(title_game)
    press(title_game, pygame.K_KP_ENTER)
    assert snapshot(title_game) == before


@pytest.mark.parametrize("key", [pygame.K_r, pygame.K_1, pygame.K_2, pygame.K_3,
                                 pygame.K_SPACE, pygame.K_KP_ENTER, pygame.K_a])
def test_title_ignores_other_keys(title_game, key):
    before = snapshot(title_game)
    press(title_game, key)
    assert snapshot(title_game) == before


def test_title_ignores_button_clicks(title_game):
    g = title_game
    before = snapshot(g)
    # (G단위) 버튼은 방침 버튼이다
    for policy, name in zip(config.POLICY_ORDER,
                            (config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY)):
        click(g, button_center(g, policy))
        assert g.do_action(name) is False
    assert snapshot(g) == before


def test_title_time_does_not_flow(title_game):
    g = title_game
    before = snapshot(g)
    for _ in range(600):
        g.update(FRAME)
    g.update(1000.0)
    assert snapshot(g) == before


@pytest.mark.parametrize("key", [pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r])
def test_playing_ignores_enter_and_r(playing_game, key):
    g = playing_game
    g.update(10.5)
    g.do_action(config.ACTION_STUDY)
    before = snapshot(g)
    press(g, key)
    assert snapshot(g) == before


def test_ending_r_fully_resets(playing_game):
    g = playing_game
    g.update(30.4)  # elapsed 30.4, decay_timer 0.4
    g.student.knowledge = 200
    g.set_policy(config.POLICY_STUDY_FOCUS)   # 공부 체력 -8: 5 -> 0
    force_ending_by_study(g)
    assert g.ending == config.ENDING_LEAVE
    press(g, pygame.K_r)
    s = g.student
    assert g.state == config.STATE_PLAYING
    assert (s.health, s.mental, s.knowledge) == (80, 80, 0)
    assert s.elapsed == 0 and s.decay_timer == 0 and s.get_grade() == 1
    assert g.ending is None
    # (G단위) 쿨타임 대신: 방침은 균형으로, 자동 행동 시계는 처음(2초)으로, last_action 없음
    assert g.policy == config.POLICY_START
    assert g.auto_timer == config.AUTO_ACTION_INTERVAL
    assert g.last_action is None
    assert g.do_action(config.ACTION_FEED) is True


def test_ending_r_after_graduation_resets(playing_game):
    g = playing_game
    s = g.student
    # (L단위) 4학년에서 지식이 졸업 목표 이상이면 다음 판정(update)에서 졸업, 200초 -> 수석(11절 A안)
    s.elapsed, s.health, s.mental, s.knowledge = 199.5, 100, 100, config.GRADUATION_KNOWLEDGE + 100
    g.update(0.5)
    assert g.ending == config.ENDING_TOP
    assert s.graduation_time == 200
    press(g, pygame.K_r)
    s = g.student
    assert g.state == config.STATE_PLAYING
    assert (s.health, s.mental, s.knowledge, s.elapsed) == (80, 80, 0, 0)
    assert not s.is_exam_period() and g.ending is None


@pytest.mark.parametrize("key", [pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_1,
                                 pygame.K_2, pygame.K_3, pygame.K_SPACE])
def test_ending_ignores_other_keys(playing_game, key):
    g = playing_game
    force_ending_by_study(g)
    before = snapshot(g)
    press(g, key)
    assert snapshot(g) == before


def test_ending_ignores_clicks_and_actions(playing_game):
    g = playing_game
    force_ending_by_study(g)
    before = snapshot(g)
    for policy, name in zip(config.POLICY_ORDER,
                            (config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY)):
        click(g, button_center(g, policy))
        assert g.do_action(name) is False
    assert snapshot(g) == before


def test_ending_time_does_not_flow(playing_game):
    g = playing_game
    g.update(3.3)
    force_ending_by_study(g)
    before = snapshot(g)
    for _ in range(600):
        g.update(FRAME)
    g.update(1000.0)
    assert snapshot(g) == before


def _go_to(state):
    g = Game()
    if state != config.STATE_TITLE:
        press(g, pygame.K_RETURN)
    if state == config.STATE_ENDING:
        force_ending_by_study(g)
    assert g.state == state
    return g


@pytest.mark.parametrize("state", [config.STATE_TITLE, config.STATE_PLAYING,
                                   config.STATE_ENDING])
def test_esc_quits_every_screen(state):
    g = _go_to(state)
    try:
        press(g, pygame.K_ESCAPE)
        assert g.running is False
    finally:
        pygame.quit()


@pytest.mark.parametrize("state", [config.STATE_TITLE, config.STATE_PLAYING,
                                   config.STATE_ENDING])
def test_quit_event_every_screen(state):
    g = _go_to(state)
    try:
        g.handle_event(pygame.event.Event(pygame.QUIT))
        assert g.running is False
    finally:
        pygame.quit()


def test_title_to_ending_to_playing_cycle_many_times(title_game):
    g = title_game
    press(g, pygame.K_RETURN)
    for _ in range(5):
        force_ending_by_study(g)
        press(g, pygame.K_r)
        assert g.state == config.STATE_PLAYING
        assert (g.student.health, g.student.mental, g.student.knowledge) == (80, 80, 0)


# ======================= 기능 9: 휴학 엔딩 =======================

def test_natural_decay_mental_zero_ends_immediately(playing_game):
    """멘탈은 시험 기간 2배로 65초에 0이 된다 -> 그 프레임에 바로 휴학."""
    g = playing_game
    g.update(64.0)
    assert g.state == config.STATE_PLAYING
    assert (g.student.health, g.student.mental) == (16, 1)
    for frame in range(1, 61):
        g.update(FRAME)
        if frame < 60:
            assert g.state == config.STATE_PLAYING, frame
    assert g.state == config.STATE_ENDING
    assert g.ending == config.ENDING_LEAVE
    assert (g.student.health, g.student.mental) == (15, 0)


def test_natural_decay_health_zero_ends_immediately(playing_game):
    g = playing_game
    g.student.health = 3
    g.student.mental = 100
    g.update(2.0)
    assert g.state == config.STATE_PLAYING
    g.update(1.0)
    assert g.state == config.STATE_ENDING
    assert g.ending == config.ENDING_LEAVE
    assert g.student.health == 0


def test_study_health_to_zero_ends_immediately(playing_game):
    g = playing_game
    g.student.health = 5
    g.do_action(config.ACTION_STUDY)
    assert g.student.health == 0
    assert g.state == config.STATE_ENDING and g.ending == config.ENDING_LEAVE


def test_study_mental_to_zero_ends_immediately(playing_game):
    g = playing_game
    g.student.mental = 8
    g.do_action(config.ACTION_STUDY)   # (G단위) 키 3은 방침 선택이므로 do_action
    assert g.student.mental == 0
    assert g.state == config.STATE_ENDING and g.ending == config.ENDING_LEAVE


def test_study_below_zero_ends(playing_game):
    """(G단위: 예전 '클릭 공부') 멘탈 3에서 공부(-8)하면 0에서 멈추고 바로 휴학."""
    g = playing_game
    g.student.mental = 3
    g.do_action(config.ACTION_STUDY)
    assert g.student.mental == 0
    assert g.state == config.STATE_ENDING and g.ending == config.ENDING_LEAVE
    assert g.state == config.STATE_ENDING and g.ending == config.ENDING_LEAVE


def test_study_to_one_keeps_playing(playing_game):
    g = playing_game
    g.student.health, g.student.mental = 6, 9
    g.do_action(config.ACTION_STUDY)
    assert (g.student.health, g.student.mental) == (1, 1)
    assert g.state == config.STATE_PLAYING and g.ending is None


def test_after_leave_ending_update_changes_nothing(playing_game):
    g = playing_game
    g.update(64.0)
    g.update(1.0)
    assert g.state == config.STATE_ENDING
    before = snapshot(g)
    g.update(5.0)
    g.update(FRAME)
    assert snapshot(g) == before


def test_student_get_ending():
    s = Student()
    assert s.get_ending() is None
    s.health = 0
    assert s.get_ending() == config.ENDING_LEAVE
    s = Student()
    s.mental = 0
    assert s.get_ending() == config.ENDING_LEAVE
    # (L단위) 시간이 아무리 흘러도 졸업하지 않는다. 4학년에서 지식 1100 이상 + 진급 판정이면 졸업
    s = Student()
    s.elapsed = 240.0
    assert s.get_ending() is None
    s.elapsed = 10000.0
    assert s.get_ending() is None
    s.elapsed = 200.0   # 11절 A안: 수석은 200초 이하
    s.knowledge = config.GRADUATION_KNOWLEDGE
    s.promote()
    assert s.get_ending() == config.ENDING_TOP
    s.health = 0
    assert s.get_ending() == config.ENDING_LEAVE


# ======================= 기능 12: 졸업 엔딩 =======================

@pytest.mark.parametrize("seconds, ending", [
    # (L단위) 졸업 등급은 걸린 시간으로: 200 이하 수석, 360 이하 무사, 초과 아슬아슬 (11절 A안)
    (0, config.ENDING_TOP), (100.0, config.ENDING_TOP), (199.999, config.ENDING_TOP),
    (200, config.ENDING_TOP), (200.0001, config.ENDING_NORMAL), (239.999, config.ENDING_NORMAL),
    (240, config.ENDING_NORMAL), (300, config.ENDING_NORMAL),
    (360, config.ENDING_NORMAL), (360.0001, config.ENDING_BARELY), (361, config.ENDING_BARELY),
    (100000, config.ENDING_BARELY),
])
def test_judge_ending_boundaries(seconds, ending):
    assert judge_ending(seconds) == ending
    s = Student()
    s.elapsed = seconds
    s.knowledge = config.GRADUATION_KNOWLEDGE
    s.promote()
    assert s.graduation_time == seconds
    assert s.get_graduation_ending() == ending


@pytest.mark.parametrize("elapsed, ending", [
    (150.0, config.ENDING_TOP), (199.0, config.ENDING_TOP), (201.0, config.ENDING_NORMAL),
    (241.0, config.ENDING_NORMAL),
    (359.0, config.ENDING_NORMAL), (361.0, config.ENDING_BARELY),
])
def test_graduation_in_game_flow(playing_game, elapsed, ending):
    """(L단위) 4학년 1090에서 공부(+10, 시험 기간이면 +20)로 1100에 닿는 순간 졸업, 등급은 그 시각."""
    g = playing_game
    s = g.student
    s.elapsed, s.health, s.mental = elapsed, 100, 100
    reach_grade(s, 4)
    s.knowledge = config.GRADUATION_KNOWLEDGE - 10
    g.do_action(config.ACTION_STUDY)
    assert s.knowledge >= config.GRADUATION_KNOWLEDGE
    assert g.state == config.STATE_ENDING
    assert g.ending == ending
    assert s.graduation_time == elapsed


def test_graduation_after_exam_study_crosses_goal(playing_game):
    """(L단위) 시험 기간 공부(+20)로 졸업 목표를 넘기면 그 순간 졸업(1090 -> 1110).

    (11절 A안) 수석이 200초 이하가 되어 시각을 주기 4의 225초 -> 주기 3의 시험 기간 165초로 옮겼다.
    """
    g = playing_game
    s = g.student
    s.elapsed, s.health, s.mental = 165.0, 100, 100
    reach_grade(s, 4)
    s.knowledge = config.GRADUATION_KNOWLEDGE - 10
    assert s.is_exam_period()
    g.do_action(config.ACTION_STUDY)
    assert s.knowledge == config.GRADUATION_KNOWLEDGE + 10
    assert g.ending == config.ENDING_TOP and s.graduation_time == 165.0



def test_no_graduation_by_time_alone(playing_game):
    """(L단위, 예전 '14400프레임에 졸업') 240초(14400프레임)가 지나도 지식이 모자라면 계속 논다."""
    g = playing_game
    for _ in range(14400 + 600):
        g.student.health = g.student.mental = 100  # 휴학하지 않게 유지
        g.update(FRAME)
    assert g.state == config.STATE_PLAYING
    assert g.ending is None
    assert abs(g.student.elapsed - 250) < 1e-6


@pytest.mark.parametrize("start, dt", [(230.0, 50.0), (0.0, 1000.0), (239.9, 0.2),
                                       (239.999, 5.0)])
def test_big_dt_time_keeps_flowing(start, dt):
    """(L단위, 예전 '240초에서 멈춤') 시간 제한이 없으므로 경과 시간은 240초를 넘어 계속 흐른다."""
    s = Student()
    s.elapsed = start
    s.update(dt)
    assert s.elapsed == pytest.approx(start + dt)
    s.update(dt)
    assert s.elapsed == pytest.approx(start + 2 * dt)


def test_big_dt_decays_every_second_past_240():
    """230초에서 dt=50: 감소는 231~280초 50번. 시험 기간(주기 4의 225~240)인 231~239초만 멘탈 -2."""
    s = Student()
    s.elapsed, s.health, s.mental = 230.0, 100, 100
    s.update(50.0)
    assert (s.health, s.mental) == (50, 100 - 9 * 2 - 41)


def test_big_dt_in_game_does_not_graduate_without_knowledge(playing_game):
    g = playing_game
    s = g.student
    s.elapsed, s.health, s.mental = 230.0, 100, 100
    reach_grade(s, 4)
    s.knowledge = config.GRADUATION_KNOWLEDGE - 1
    g.update(50.0)
    assert g.state == config.STATE_PLAYING and g.ending is None
    assert s.elapsed == pytest.approx(280.0)


@pytest.mark.parametrize("health, mental", [(5, 100), (100, 8), (5, 8)])
def test_zero_and_graduation_same_moment_leave_wins(playing_game, health, mental):
    """(L단위) 공부로 졸업 목표를 넘는 순간 체력·멘탈도 0이 되면 휴학이 먼저다."""
    g = playing_game
    s = g.student
    reach_grade(s, 4)
    s.health, s.mental, s.knowledge = health, mental, config.GRADUATION_KNOWLEDGE - 10
    g.do_action(config.ACTION_STUDY)
    assert s.knowledge >= config.GRADUATION_KNOWLEDGE
    assert g.state == config.STATE_ENDING
    assert g.ending == config.ENDING_LEAVE
    assert s.graduation_time is None


def test_zero_by_decay_with_goal_reached_leave_wins(playing_game):
    """자연 감소로 0이 된 같은 판정에서 지식이 졸업 목표 이상이어도 휴학이 먼저다."""
    g = playing_game
    s = g.student
    reach_grade(s, 4)
    s.health, s.mental, s.knowledge = 1, 100, config.GRADUATION_KNOWLEDGE
    g.update(1.0)
    assert g.ending == config.ENDING_LEAVE


def _ending_screen(g, ending, knowledge):
    g.student.knowledge = knowledge
    g.end_game(ending)
    g.draw()


# (도트 재디자인) 학사모는 CAP_SPRITE를 칸 크기 CAP_PIXEL로 화면 가운데, 위쪽 y = CAP_TOP_Y에 찍는다.
_CAP_W, _CAP_H = sprite_size(config.CAP_SPRITE, config.CAP_PIXEL)
CAP_REGION = pygame.Rect(config.SCREEN_CENTER_X - _CAP_W // 2, config.CAP_TOP_Y, _CAP_W, _CAP_H)
# 학사모 몸통(띠 위, 가운데 열의 14번째 행) 점
CAP_BODY_POINT = (config.SCREEN_CENTER_X, config.CAP_TOP_Y + 14 * config.CAP_PIXEL + 2)


@pytest.mark.parametrize("ending", GRADUATIONS)
def test_graduation_cap_pixels(playing_game, ending):
    g = playing_game
    _ending_screen(g, ending, 321)
    assert color(g.screen, *CAP_BODY_POINT) == config.COLOR_CAP
    assert count_color(g.screen, config.COLOR_CAP, CAP_REGION) > 1000
    assert count_color(g.screen, config.COLOR_TASSEL, g.screen.get_rect()) > 0


def test_leave_ending_has_no_cap(playing_game):
    g = playing_game
    _ending_screen(g, config.ENDING_LEAVE, 321)
    assert count_color(g.screen, config.COLOR_CAP, g.screen.get_rect()) == 0
    assert count_color(g.screen, config.COLOR_TASSEL, g.screen.get_rect()) == 0


def test_cap_does_not_overlap_texts():
    """학사모 영역이 엔딩 이름·누적 지식·다시 하기 글자 줄과 겹치지 않는다.

    (도트 재디자인) 학사모 스프라이트 영역(술 포함)이 엔딩 이름 아래, 누적 지식 배지 상자 위에 있고
    가운데 패널 안쪽에 들어간다.
    """
    assert CAP_REGION.top > config.ENDING_NAME_Y + config.TITLE_FONT_SIZE // 2
    assert CAP_REGION.bottom < config.ENDING_KNOWLEDGE_Y - config.BADGE_HEIGHT // 2
    panel = pygame.Rect(config.MENU_PANEL_RECT)
    assert panel.inflate(-2 * config.PIXEL_SIZE, -2 * config.PIXEL_SIZE).contains(CAP_REGION)


@pytest.mark.parametrize("ending", [config.ENDING_LEAVE, *GRADUATIONS])
def test_ending_texts(playing_game, ending):
    g = playing_game
    rec_small = RecordingFont(g.font)
    rec_big = RecordingFont(g.title_font)
    g.font, g.title_font = rec_small, rec_big
    _ending_screen(g, ending, 456)
    all_texts = rec_small.texts + rec_big.texts
    assert ending in all_texts
    assert "누적 지식 456" in all_texts
    if ending == config.ENDING_LEAVE:
        assert "R을 눌러 다시 하기" in all_texts
    else:
        # (I단위, 기획서 10절) 졸업 엔딩의 R은 환생, C는 대학원 진학 안내로 바뀌었다
        assert config.REINCARNATE_HINT_TEXT in all_texts
        assert config.GRAD_SCHOOL_HINT_TEXT in all_texts
        assert "R을 눌러 다시 하기" not in all_texts
    # 게임 화면 요소(버튼·배너)는 엔딩 화면에 없다
    for policy in config.POLICY_ORDER:   # (G단위) 방침 버튼 글자
        assert config.POLICIES[policy][config.POLICY_TEXT] not in all_texts
    assert config.EXAM_BANNER_TEXT not in all_texts


def test_title_texts(title_game):
    g = title_game
    rec_small = RecordingFont(g.font)
    rec_big = RecordingFont(g.title_font)
    g.font, g.title_font = rec_small, rec_big
    g.draw()
    all_texts = rec_small.texts + rec_big.texts
    assert "제자 키우기" in all_texts
    assert "최고 기록: 지식 0" in all_texts
    assert "Enter를 눌러 시작" in all_texts
    for policy in config.POLICY_ORDER:   # (G단위) 방침 버튼 글자
        assert config.POLICIES[policy][config.POLICY_TEXT] not in all_texts


def test_title_screen_has_no_game_elements(title_game):
    g = title_game
    g.draw()
    full = g.screen.get_rect()
    for rgb in (config.COLOR_BUTTON, config.COLOR_YELLOW, config.COLOR_SKIN,
                config.COLOR_GREEN, config.COLOR_CAP):
        assert count_color(g.screen, rgb, full) == 0, rgb


# ======================= 기능 11: 시험 기간 =======================

@pytest.mark.parametrize("base", CYCLE_STARTS)
@pytest.mark.parametrize("offset, exam", [
    (0.0, False), (30.0, False), (44.9, False), (44.999, False), (45.0, True),
    (50.0, True), (59.9, True), (59.999, True),
])
def test_exam_period_boundaries(base, offset, exam):
    s = Student()
    s.elapsed = base + offset
    assert s.is_exam_period() is exam


@pytest.mark.parametrize("elapsed", [60.0, 120.0, 180.0, 240.0, 300.0, 360.0])
def test_exam_period_ends_at_cycle_boundary(elapsed):
    s = Student()
    s.elapsed = elapsed
    assert s.is_exam_period() is False


@pytest.mark.parametrize("frames, exam", [(2699, False), (2700, True), (3599, True),
                                          (3600, False), (6299, False), (6300, True),
                                          (17099, False), (17100, True), (18000, False)])
def test_exam_period_by_frames(frames, exam):
    s = Student()
    for _ in range(frames):
        s.update(FRAME)
    assert s.is_exam_period() is exam


@pytest.mark.parametrize("base", CYCLE_STARTS)
@pytest.mark.parametrize("offset, gain", [(44.9, 10), (45.0, 20), (59.9, 20), (60.0, 10)])
def test_study_knowledge_in_exam(base, offset, gain):
    s = Student()
    s.elapsed = base + offset
    s.knowledge = 100
    s.study()
    assert s.knowledge == 100 + gain
    assert (s.health, s.mental) == (75, 72)  # 체력 -5, 멘탈 -8 은 시험 기간에도 그대로


def test_study_in_exam_via_game(playing_game):
    g = playing_game
    g.update(45.0)
    assert g.student.is_exam_period()
    k, h, m = g.student.knowledge, g.student.health, g.student.mental
    g.do_action(config.ACTION_STUDY)   # (G단위) 균형 방침: 배수 1.0
    assert (g.student.knowledge, g.student.health, g.student.mental) == (k + 20, h - 5, m - 8)


def test_rest_and_feed_unchanged_in_exam():
    s = Student()
    s.elapsed = 50.0
    s.health, s.mental, s.knowledge = 50, 50, 10
    s.feed()
    s.rest()
    assert (s.health, s.mental, s.knowledge) == (70, 70, 8)


@pytest.mark.parametrize("start, mental_drop", [(43.0, 1), (44.0, 2), (58.0, 2), (59.0, 1),
                                                (103.0, 1), (104.0, 2), (119.0, 1),
                                                (224.0, 2), (238.0, 2), (239.0, 1),
                                                (283.0, 1), (284.0, 2), (299.0, 1)])
def test_decay_amount_at_boundaries(start, mental_drop):
    """start초에서 1초 흘림 -> start+1초 시점의 감소가 시험 기간이면 멘탈 -2. 체력은 항상 -1."""
    s = Student()
    s.elapsed, s.health, s.mental = start, 50, 50
    s.update(1.0)
    assert s.health == 49
    assert s.mental == 50 - mental_drop


def _drops_per_second(step):
    """0~240초를 step 단위로 흘리며 초마다의 멘탈 감소량 목록을 만든다(게이지는 매번 100으로 채움).

    (L단위) is_time_over가 없어져 240초(주기 4개)까지만 직접 센다.
    """
    s = Student()
    drops = []
    while s.elapsed < 240 - 1e-6:
        s.health = s.mental = 100
        s.update(step)
        if s.mental != 100:
            drops.append((round(s.elapsed), 100 - s.mental))
    return drops


@pytest.mark.parametrize("step", [1.0, FRAME, 0.1])
def test_double_decay_15_times_per_cycle(step):
    drops = _drops_per_second(step)
    assert len(drops) == 240
    for base in CYCLE_STARTS[:4]:
        doubled = [t for t, d in drops if d == 2 and base < t <= base + 60]
        assert doubled == list(range(base + 45, base + 60)), base
    assert sum(1 for _, d in drops if d == 2) == 60
    assert all(d in (1, 2) for _, d in drops)


def test_health_decay_never_doubled():
    s = Student()
    s.elapsed, s.health, s.mental = 45.0, 100, 100
    s.update(14.0)
    assert s.health == 86


def test_full_240_seconds_total_decay():
    """240초 동안 체력은 240, 멘탈은 240 + 60(시험 기간 추가분) 만큼 줄어야 한다."""
    s = Student()
    total_h = total_m = 0
    for _ in range(240 * 60):
        s.health = s.mental = 100
        s.update(FRAME)
        total_h += 100 - s.health
        total_m += 100 - s.mental
    assert (total_h, total_m) == (240, 300)


def _banner_pixel(g):
    """(도트 재디자인) 배너 몸통 점: 왼쪽 외곽선 1칸 안쪽, 세로 가운데."""
    return color(g.screen, config.EXAM_BANNER_X + 2 * config.PIXEL_SIZE,
                 config.EXAM_BANNER_Y + config.EXAM_BANNER_HEIGHT // 2)


@pytest.mark.parametrize("elapsed, shown", [
    (0.0, False), (44.9, False), (45.0, True), (59.9, True), (60.0, False),
    (105.0, True), (165.0, True), (225.0, True), (239.9, True),
    (240.0, False), (285.0, True), (300.0, False), (645.0, True),
])
def test_banner_only_in_exam(playing_game, elapsed, shown):
    g = playing_game
    g.student.elapsed = elapsed
    rec = RecordingFont(g.font)
    g.font = rec
    g.draw()
    assert (_banner_pixel(g) == config.COLOR_YELLOW) is shown
    assert (config.EXAM_BANNER_TEXT in rec.texts) is shown


def test_banner_not_on_title_or_ending(title_game):
    g = title_game
    g.student.elapsed = 50.0
    g.draw()
    assert count_color(g.screen, config.COLOR_YELLOW, g.screen.get_rect()) == 0
    press(g, pygame.K_RETURN)
    g.update(50.0)
    g.end_game(config.ENDING_LEAVE)
    g.draw()
    assert count_color(g.screen, config.COLOR_YELLOW, g.screen.get_rect()) == 0


def test_banner_does_not_overlap_gauges_or_info_bar():
    banner = pygame.Rect(config.EXAM_BANNER_X, config.EXAM_BANNER_Y,
                         config.EXAM_BANNER_WIDTH, config.EXAM_BANNER_HEIGHT)
    info = pygame.Rect(0, 0, config.SCREEN_WIDTH, config.INFO_BAR_HEIGHT)
    health_area = pygame.Rect(config.GAUGE_X - config.PIXEL_SIZE, config.HEALTH_LABEL_Y,
                              config.BAR_WIDTH + 2 * config.PIXEL_SIZE,
                              config.MENTAL_BAR_Y + config.BAR_HEIGHT + config.PIXEL_SIZE
                              - config.HEALTH_LABEL_Y)
    # (도트 재디자인) 배너 아래 그림자 1칸까지 포함해 정보바(그림자 포함)·게이지·두 패널과 겹치지 않는다
    banner_with_drop = pygame.Rect(banner.left, banner.top, banner.width,
                                   banner.height + config.PIXEL_SIZE)
    assert not banner_with_drop.colliderect(info)
    assert not banner_with_drop.colliderect(health_area)
    for panel in ((config.STATUS_PANEL_X, config.PANEL_Y, config.STATUS_PANEL_WIDTH,
                   config.PANEL_HEIGHT),
                  (config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH, config.PANEL_HEIGHT)):
        assert not banner_with_drop.colliderect(pygame.Rect(panel))
    assert banner.right <= config.SCREEN_WIDTH
    # 4학년(반지름 70) 얼굴과도 겹치지 않음
    face_top = config.STUDENT_CENTER_Y - (config.BASE_RADIUS + 3 * config.RADIUS_PER_GRADE)
    assert banner.bottom < face_top


def test_banner_pixels_do_not_cover_gauges(playing_game):
    """시험 기간 화면에서도 게이지 막대 색이 그대로 보인다."""
    g = playing_game
    g.student.elapsed = 50.0
    g.student.health, g.student.mental = 80, 20
    g.draw()
    y_h = config.HEALTH_BAR_Y + config.BAR_HEIGHT // 2
    y_m = config.MENTAL_BAR_Y + config.BAR_HEIGHT // 2
    assert color(g.screen, config.GAUGE_X + 5, y_h) == config.COLOR_GREEN
    assert color(g.screen, config.GAUGE_X + 5, y_m) == config.COLOR_RED
    # 정보바 몸통도 남아 있다 (도트 재디자인: 외곽선 1칸 안쪽, 글자 세로 가운데)
    assert color(g.screen, config.INFO_BOX_X + 2 * config.PIXEL_SIZE,
                 config.INFO_TEXT_CENTER_Y) == config.COLOR_INFO_BAR


# ======================= 회귀: (G단위) 쿨타임 없음, 게이지 범위 =======================

def test_no_cooldown_between_actions(playing_game):
    """(예전: 쿨타임 공유) 기획서 10절로 쿨타임이 없어져 이어서 한 행동이 모두 실행된다."""
    g = playing_game
    assert g.do_action(config.ACTION_FEED) is True
    assert g.do_action(config.ACTION_REST) is True
    assert g.do_action(config.ACTION_STUDY) is True
    g.update(0.01)
    assert g.do_action(config.ACTION_STUDY) is True


@pytest.mark.parametrize("seed", range(5))
def test_random_full_play_gauges_in_range(seed):
    """무작위 행동으로 끝까지 플레이: 게이지 0~100, 지식 0 이상, 반드시 엔딩에 도달."""
    rng = random.Random(seed)
    g = Game()
    try:
        press(g, pygame.K_RETURN)
        # (G단위) 키 1/2/3은 방침이므로 행동은 do_action으로 무작위로 시킨다
        actions = [config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY]
        frames = 0
        # (L단위) 시간 제한이 없으므로 240초 상한 대신 넉넉한 상한(20분) 안에 엔딩에 닿는지 본다
        while g.state == config.STATE_PLAYING and frames < 20 * 60 * 60:
            if rng.random() < 0.05:
                g.do_action(rng.choice(actions))
            g.update(FRAME)
            frames += 1
            s = g.student
            assert 0 <= s.health <= 100 and 0 <= s.mental <= 100
            assert s.knowledge >= 0
        assert g.ending in (config.ENDING_LEAVE, *GRADUATIONS)
        g.draw()
    finally:
        pygame.quit()


# ======================= 완료 기준: 처음부터 끝까지 한 판 =======================

LEGACY_ACTION_GAP = 1.0   # (G단위) 예전 쿨타임(1초). 사람 흉내 봇의 행동 간격으로만 쓴다


def _smart_bot_action(s):
    if s.health <= 40:
        return config.ACTION_FEED
    if s.mental <= 40:
        return config.ACTION_REST
    return config.ACTION_STUDY


def test_full_play_title_to_graduation_and_restart(title_game):
    """타이틀 -> Enter -> 60fps로 1초마다 행동 -> 지식 1100에 졸업 엔딩 -> R -> 새 판.

    (L단위) 예전에는 240초(14400프레임)에 졸업했지만, 이제는 졸업 목표에 닿는 순간 졸업하고
    등급은 걸린 시간(graduation_time)으로 정한다.

    (G단위) 키 1/2/3이 방침 선택이 되어 행동은 do_action으로 시킨다(자동 행동은 conftest가 끔).
    """
    g = title_game
    g.draw()
    press(g, pygame.K_RETURN)
    frames = 0
    banner_frames = 0
    wait = 0.0
    while g.state == config.STATE_PLAYING:
        if wait <= 1e-9:
            g.do_action(_smart_bot_action(g.student))
            wait = LEGACY_ACTION_GAP
        g.update(FRAME)
        wait -= FRAME
        frames += 1
        if g.state == config.STATE_PLAYING and frames % 30 == 0:
            g.draw()
            if _banner_pixel(g) == config.COLOR_YELLOW:
                banner_frames += 1
    assert g.ending in GRADUATIONS
    assert g.student.knowledge >= config.GRADUATION_KNOWLEDGE
    # 졸업은 그 프레임의 update 전(do_action) 또는 update 안에서 일어난다
    assert (frames - 1) * FRAME - 1e-6 <= g.student.graduation_time <= frames * FRAME + 1e-6
    assert g.ending == judge_ending(g.student.graduation_time)
    assert banner_frames > 0
    g.draw()
    assert count_color(g.screen, config.COLOR_CAP, CAP_REGION) > 0
    press(g, pygame.K_r)
    assert g.state == config.STATE_PLAYING
    assert (g.student.health, g.student.mental, g.student.knowledge) == (80, 80, 0)


def test_full_play_idle_leads_to_leave(title_game):
    """타이틀 -> Enter -> 아무것도 안 하면 휴학(65초) -> R -> 새 판."""
    g = title_game
    press(g, pygame.K_RETURN)
    frames = 0
    while g.state == config.STATE_PLAYING:
        g.update(FRAME)
        frames += 1
        g.draw() if frames % 600 == 0 else None
    assert frames == 65 * 60
    assert g.ending == config.ENDING_LEAVE
    g.draw()
    press(g, pygame.K_r)
    assert g.state == config.STATE_PLAYING


def test_real_run_loop_enter_then_esc():
    """실제 run() 루프: 이벤트 큐에 Enter, ESC를 넣으면 게임 화면으로 갔다가 종료(SystemExit)."""
    g = Game()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    with pytest.raises(SystemExit):
        g.run()
    assert g.state == config.STATE_PLAYING
    assert g.running is False


# ======================= 정적 검사 =======================

def test_judge_ending_takes_only_seconds():
    """(L단위) judge_ending은 졸업까지 걸린 시간(초) 하나만 받는다(예전: 지식)."""
    import inspect
    assert list(inspect.signature(judge_ending).parameters) == ["seconds"]
    assert callable(getattr(student_module, "judge_ending"))


def test_record_file_io_only_in_game():
    """(6일차 기준으로 변경) 기록 파일 입출력은 Game(game.py)만 맡는다.

    5일차에는 game.py에 open(이 없어야 했지만, 6일차부터는 game.py에 있는 것이 정상이다.
    Student·Button·main은 파일을 열지 않는다.
    """
    from pathlib import Path
    root = Path(config.__file__).parent
    assert "open(" in (root / "game.py").read_text(encoding="utf-8")
    for name in ("student.py", "button.py", "main.py"):
        assert "open(" not in (root / name).read_text(encoding="utf-8"), name
