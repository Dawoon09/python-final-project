"""3일차 검수: 세 가지 행동(기능 1~3), 버튼 클릭과 키보드 단축키.

(G단위) 쿨타임(기능 4)은 기획서 10절로 없어졌고, 키·버튼은 일과표 방침 선택으로 바뀌었다.
"""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
from button import Button  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402


@pytest.fixture
def game():
    """dummy 드라이버로 Game을 만든다(게임 화면 상태)."""
    g = Game()
    g.state = config.STATE_PLAYING
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


def gauges(g):
    s = g.student
    return (s.health, s.mental, s.knowledge)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def click(pos, button=pygame.BUTTON_LEFT):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button)


def center(g, name):
    return g.buttons[name].rect.center


def color_at(surface, pos):
    return tuple(surface.get_at(pos))[:3]


def button_body_point(g, name):
    """(도트 재디자인) 외곽선·위 하이라이트·아래 그림자 줄과 글자를 피한 버튼 몸통 점.

    외곽선 1칸 바로 안쪽(왼쪽 끝에서 2칸) 열의 세로 가운데. 글자는 가운데 정렬이라 닿지 않는다.
    """
    r = g.buttons[name].rect
    return (r.left + 2 * config.PIXEL_SIZE, r.centery)


# ======================= 기능 1~3: Student 행동 수치 =======================

def test_config_action_values_match_spec():
    assert config.FEED_HEALTH == 20
    assert (config.REST_MENTAL, config.REST_KNOWLEDGE) == (20, -2)
    assert (config.STUDY_HEALTH, config.STUDY_MENTAL, config.STUDY_KNOWLEDGE) == (-5, -8, 10)
    assert config.STUDY_KNOWLEDGE_EXAM == 20
    assert not hasattr(config, "ACTION_COOLDOWN")   # G단위: 쿨타임 삭제(기획서 10절)


def test_feed():
    s = Student()
    s.health = 50
    s.feed()
    assert (s.health, s.mental, s.knowledge) == (70, 80, 0)


def test_rest():
    s = Student()
    s.mental = 50
    s.knowledge = 10
    s.rest()
    assert (s.health, s.mental, s.knowledge) == (80, 70, 8)


def test_study():
    s = Student()
    s.study()
    assert (s.health, s.mental, s.knowledge) == (75, 72, 10)


def test_study_knowledge_is_10_now():
    assert Student().get_study_knowledge() == 10


@pytest.mark.parametrize("start, expected", [(90, 100), (81, 100), (80, 100), (79, 99), (100, 100)])
def test_feed_clamp(start, expected):
    s = Student()
    s.health = start
    s.feed()
    assert s.health == expected


@pytest.mark.parametrize("start, expected", [(90, 100), (80, 100), (79, 99)])
def test_rest_mental_clamp(start, expected):
    s = Student()
    s.mental = start
    s.rest()
    assert s.mental == expected


@pytest.mark.parametrize("start, expected", [(0, 0), (1, 0), (2, 0), (3, 1)])
def test_rest_knowledge_not_negative(start, expected):
    s = Student()
    s.knowledge = start
    s.rest()
    assert s.knowledge == expected


def test_study_health_3_to_zero_drops_out():
    s = Student()
    s.health = 3
    s.study()
    assert s.health == 0
    assert s.is_dropped_out() is True


def test_study_mental_5_to_zero_drops_out():
    s = Student()
    s.mental = 5
    s.study()
    assert s.mental == 0
    assert s.is_dropped_out() is True


def test_study_health_6_survives():
    s = Student()
    s.health = 6
    s.mental = 9
    s.study()
    assert (s.health, s.mental) == (1, 1)
    assert s.is_dropped_out() is False


def test_repeated_actions_stay_in_range():
    s = Student()
    for _ in range(30):
        s.feed()
        s.rest()
    assert (s.health, s.mental, s.knowledge) == (100, 100, 0)
    for _ in range(30):
        s.study()
    assert (s.health, s.mental, s.knowledge) == (0, 0, 300)


# ======================= Game.do_action =======================
# (G단위) 기획서 10절: 쿨타임이 없어지고 키 1/2/3·버튼은 일과표 방침 선택이 됐다.
# 행동은 제자가 2초마다 스스로 하므로(conftest no_auto로 끔) 여기서는 do_action으로 직접 시킨다.

def test_do_action_each(game):
    assert game.do_action(config.ACTION_FEED) is True
    assert gauges(game) == (100, 80, 0)
    assert game.do_action(config.ACTION_STUDY) is True
    assert gauges(game) == (95, 72, 10)
    assert game.do_action(config.ACTION_REST) is True
    assert gauges(game) == (95, 92, 8)
    assert game.last_action == config.ACTION_REST


def test_do_action_unknown_name_ignored(game):
    assert game.do_action("dance") is False
    assert gauges(game) == (80, 80, 0)
    assert game.last_action is None


# ======================= (G단위) 쿨타임 없음 =======================
# 예전 기능 4(쿨타임 1초: 0.999초 무시/1.0초 허용, 공유, 연장 안 됨, 음수 안 됨, 타이틀에서 안 셈)
# 테스트는 기획서 10절 "행동 쿨타임 1초 -> 없앤다"로 규칙이 사라져 삭제하고, 아래로 바꾼다.

def test_no_cooldown_attribute(game):
    assert not hasattr(game, "cooldown")
    assert not hasattr(game, "is_cooling_down")
    assert not hasattr(config, "ACTION_COOLDOWN")


@pytest.mark.parametrize("second, expected", [
    (config.ACTION_FEED, (95, 72, 10)),     # 체력 75 + 20 = 95
    (config.ACTION_REST, (75, 92, 8)),
    (config.ACTION_STUDY, (70, 64, 20)),
])
def test_consecutive_actions_all_run(game, second, expected):
    """(예전: 쿨타임 공유로 무시) 이제는 바로 이어서 한 두 번째 행동도 실행된다."""
    game.do_action(config.ACTION_STUDY)
    assert gauges(game) == (75, 72, 10)
    assert game.do_action(second) is True
    assert gauges(game) == expected


def test_actions_every_frame_60fps(game):
    """(예전: 59프레임 무시) 매 프레임 공부해도 매번 실행된다."""
    for i in range(1, 11):
        assert game.do_action(config.ACTION_STUDY) is True
        game.update(1 / 60)
        assert game.student.knowledge == 10 * i


@pytest.mark.parametrize("state", [config.STATE_TITLE, config.STATE_ENDING, config.STATE_EVENT])
def test_do_action_only_in_playing(game, state):
    """do_action은 게임 화면(STATE_PLAYING)에서만 실행된다."""
    game.state = state
    for name in (config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY):
        assert game.do_action(name) is False
    assert gauges(game) == (80, 80, 0)
    assert game.last_action is None


# ======================= 키보드 단축키 (G단위: 방침 선택) =======================

@pytest.mark.parametrize("k, policy", [
    (pygame.K_1, config.POLICY_STUDY_FOCUS),
    (pygame.K_2, config.POLICY_BALANCED),
    (pygame.K_3, config.POLICY_REST_FOCUS),
])
def test_keys(game, k, policy):
    """키 1/2/3은 방침을 바꾸고 행동은 하지 않는다."""
    if policy == config.POLICY_BALANCED:
        game.set_policy(config.POLICY_REST_FOCUS)   # 시작값과 구분되게
    game.handle_event(key(k))
    assert game.policy == policy
    assert gauges(game) == (80, 80, 0)
    assert game.last_action is None


@pytest.mark.parametrize("k", [pygame.K_KP1, pygame.K_KP2, pygame.K_KP3])
def test_numpad_keys_no_action(game, k):
    """(4일차 리드 결정) 숫자패드는 기획서에 없으므로 행동도 방침 변경도 일으키지 않는다."""
    game.handle_event(key(k))
    assert gauges(game) == (80, 80, 0)
    assert game.policy == config.POLICY_START
    assert game.last_action is None


@pytest.mark.parametrize("k", [pygame.K_0, pygame.K_4, pygame.K_a, pygame.K_RETURN, pygame.K_r,
                               pygame.K_SPACE])
def test_other_keys_no_action(game, k):
    game.handle_event(key(k))
    assert gauges(game) == (80, 80, 0)
    assert game.policy == config.POLICY_START
    assert game.last_action is None


def test_keyup_no_action(game):
    game.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_1, mod=0))
    assert gauges(game) == (80, 80, 0)
    assert game.policy == config.POLICY_START


def test_escape_still_quits(game):
    game.handle_event(key(pygame.K_ESCAPE))
    assert game.running is False


# ======================= 버튼 클릭 (G단위: 방침 버튼) =======================

@pytest.mark.parametrize("name", [config.POLICY_STUDY_FOCUS, config.POLICY_BALANCED,
                                  config.POLICY_REST_FOCUS])
def test_click_each_button(game, name):
    if name == config.POLICY_BALANCED:
        game.set_policy(config.POLICY_STUDY_FOCUS)
    game.handle_event(click(center(game, name)))
    assert game.policy == name
    assert gauges(game) == (80, 80, 0)
    assert game.last_action is None


@pytest.mark.parametrize("btn", [pygame.BUTTON_RIGHT, pygame.BUTTON_MIDDLE,
                                 pygame.BUTTON_WHEELUP, pygame.BUTTON_WHEELDOWN])
def test_non_left_click_ignored(game, btn):
    game.handle_event(click(center(game, config.POLICY_STUDY_FOCUS), button=btn))
    game.handle_event(click(center(game, config.POLICY_REST_FOCUS), button=btn))
    assert gauges(game) == (80, 80, 0)
    assert game.policy == config.POLICY_START


def test_mouse_up_ignored(game):
    game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP,
                                         pos=center(game, config.POLICY_STUDY_FOCUS),
                                         button=pygame.BUTTON_LEFT))
    assert game.policy == config.POLICY_START


def test_click_outside_buttons(game):
    first = game.buttons[config.POLICY_STUDY_FOCUS].rect
    second = game.buttons[config.POLICY_BALANCED].rect
    game.set_policy(config.POLICY_REST_FOCUS)
    for pos in [(0, 0), (400, 300), (first.left - 1, first.centery),
                (first.right, first.centery),           # 버튼 사이 간격
                (second.left - 1, second.centery),
                (first.centerx, first.top - 1), (first.centerx, first.bottom)]:
        game.handle_event(click(pos))
    assert gauges(game) == (80, 80, 0)
    assert game.policy == config.POLICY_REST_FOCUS


def test_button_is_clicked_boundaries():
    b = Button(40, 480, 220, 50, "x")
    assert b.is_clicked((40, 480)) is True        # 왼쪽 위 모서리
    assert b.is_clicked((259, 529)) is True       # 오른쪽 아래 마지막 픽셀
    assert b.is_clicked((150, 505)) is True
    assert b.is_clicked((39, 505)) is False
    assert b.is_clicked((260, 505)) is False
    assert b.is_clicked((150, 479)) is False
    assert b.is_clicked((150, 530)) is False


def test_buttons_layout(game):
    rects = [game.buttons[n].rect for n in config.POLICY_ORDER]
    for r in rects:
        assert r.size == (config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        assert r.top == config.BUTTON_Y
        assert 0 <= r.left and r.right <= config.SCREEN_WIDTH
        assert r.bottom <= config.SCREEN_HEIGHT
    assert rects[0].right <= rects[1].left and rects[1].right <= rects[2].left
    # (G단위) 가운데 정렬 검사는 삭제: 기획서 10절 화면에서 하단 오른편은 [업그레이드 U] 버튼 자리라
    # 방침 버튼 3개는 왼편에 놓인다. 대신 순서와 오른편 빈자리를 본다.
    assert list(game.buttons) == config.POLICY_ORDER
    assert rects[2].right < config.SCREEN_WIDTH - config.BUTTON_WIDTH // 2


def test_button_texts(game):
    assert game.buttons[config.POLICY_STUDY_FOCUS].text == "공부 위주 [1]"
    assert game.buttons[config.POLICY_BALANCED].text == "균형 [2]"
    assert game.buttons[config.POLICY_REST_FOCUS].text == "휴식 위주 [3]"
    assert len(game.buttons) == 3


def test_draw_renders_button_texts_and_hint(game):
    rec = RecordingFont(game.font)
    small = RecordingFont(game.small_font)
    game.font = rec
    game.small_font = small
    game.draw()
    for t in ("공부 위주 [1]", "균형 [2]", "휴식 위주 [3]"):
        assert t in rec.texts
    # G단위: 쿨타임 안내 대신 자동 행동 진행 막대 안내
    assert config.AUTO_HINT_TEXT in rec.texts + small.texts


# ======================= 쿨타임 회색 (픽셀) =======================

def expected_button_color(game, name):
    """(G단위) 고른 방침 버튼은 노랑, 나머지는 하늘색."""
    if name == game.policy:
        return config.COLOR_POLICY_SELECTED
    return config.COLOR_BUTTON


def test_buttons_normal_color(game):
    game.draw()
    for name in game.buttons:
        assert color_at(game.screen, button_body_point(game, name)) == \
            expected_button_color(game, name)


def test_buttons_never_gray_after_action(game):
    """(예전: 쿨타임 동안 회색) G단위: 쿨타임이 없으므로 행동 직후에도 회색이 되지 않는다."""
    game.do_action(config.ACTION_FEED)
    for dt in (0.0, 0.5, 0.5):
        game.update(dt)
        game.draw()
        for name in game.buttons:
            got = color_at(game.screen, button_body_point(game, name))
            assert got != config.COLOR_GRAY
            assert got == expected_button_color(game, name)


def test_button_draw_direct(game):
    surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    b = Button(10, 10, 100, 40, "x")
    body = (b.rect.left + 2 * config.PIXEL_SIZE, b.rect.centery)
    b.draw(surface, game.font, True)
    assert color_at(surface, body) == config.COLOR_GRAY
    assert color_at(surface, (10, 30)) == config.COLOR_OUTLINE   # 왼쪽 외곽선(도트 1칸)
    b.draw(surface, game.font, False)
    assert color_at(surface, body) == config.COLOR_BUTTON


def test_gray_differs_from_normal():
    assert config.COLOR_GRAY != config.COLOR_BUTTON


# ======================= 타이틀/엔딩 상태에서는 행동 없음 =======================

@pytest.mark.parametrize("state", [config.STATE_TITLE, config.STATE_ENDING])
def test_no_action_outside_playing(game, state):
    """타이틀·엔딩에서는 키 1/2/3·방침 버튼이 행동도 방침 변경도 하지 않는다."""
    game.state = state
    for k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_KP1, pygame.K_KP2, pygame.K_KP3):
        game.handle_event(key(k))
    for name in list(game.buttons):
        game.handle_event(click(center(game, name)))
    assert gauges(game) == (80, 80, 0)
    assert game.policy == config.POLICY_START
    assert game.last_action is None


@pytest.mark.parametrize("state", [config.STATE_TITLE, config.STATE_ENDING])
def test_escape_quits_in_any_state(game, state):
    game.state = state
    game.handle_event(key(pygame.K_ESCAPE))
    assert game.running is False


# ======================= 완료 기준: 클릭과 1~3키로 게이지가 변함 =======================

def test_done_criteria_play_sequence(game):
    """학식 -> 1초 -> 공부 -> 1초 -> 휴식 (G단위: 행동은 do_action, 균형 방침이라 배수 1.0)."""
    game.do_action(config.ACTION_FEED)
    assert gauges(game) == (100, 80, 0)
    for _ in range(60):
        game.update(1 / 60)                       # 자연 감소 1회: 99, 79
    game.do_action(config.ACTION_STUDY)
    assert gauges(game) == (94, 71, 10)
    for _ in range(60):
        game.update(1 / 60)                       # 93, 70
    game.do_action(config.ACTION_REST)
    assert gauges(game) == (93, 90, 8)
    game.draw()


def test_done_criteria_bar_redrawn_after_action(game):
    """행동 후 다시 그리면 체력 막대 채움 폭이 바뀐다.

    (화면 연출 E4 이후) 행동 직후 그림은 아직 이전 길이이고, GAUGE_ANIM_TIME 이 지나면
    새 길이가 된다. 막대 색은 처음부터 실제 값 기준(70 -> 초록).
    """
    game.student.health = 50
    game.draw()
    y = config.HEALTH_BAR_Y + config.BAR_HEIGHT // 2
    x_after_50 = config.GAUGE_X + config.BAR_WIDTH * 60 // config.GAUGE_MAX
    x_inside_50 = config.GAUGE_X + config.BAR_WIDTH * 40 // config.GAUGE_MAX
    assert color_at(game.screen, (x_after_50, y)) == config.COLOR_BAR_BG
    game.do_action(config.ACTION_FEED)
    assert game.student.health == 70
    assert game.get_shown_gauge(config.GAUGE_HEALTH) == 50
    game.draw()
    # 행동 직후: 길이는 이전(50), 색은 실제 값(70) 기준 초록
    assert color_at(game.screen, (x_after_50, y)) == config.COLOR_BAR_BG
    assert color_at(game.screen, (x_inside_50, y)) == config.COLOR_GREEN
    game.update(config.GAUGE_ANIM_TIME)
    assert game.get_shown_gauge(config.GAUGE_HEALTH) == 70
    game.draw()
    assert color_at(game.screen, (x_after_50, y)) == config.COLOR_GREEN
