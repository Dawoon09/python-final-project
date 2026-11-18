"""3일차 검수: 세 가지 행동(기능 1~3), 쿨타임(기능 4), 버튼 클릭과 키보드 단축키."""

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
    assert config.ACTION_COOLDOWN == 1.0


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

def test_do_action_each(game):
    assert game.do_action(config.ACTION_FEED) is True
    assert gauges(game) == (100, 80, 0)
    game.cooldown = 0.0
    assert game.do_action(config.ACTION_STUDY) is True
    assert gauges(game) == (95, 72, 10)
    game.cooldown = 0.0
    assert game.do_action(config.ACTION_REST) is True
    assert gauges(game) == (95, 92, 8)


def test_do_action_unknown_name_ignored(game):
    assert game.do_action("dance") is False
    assert gauges(game) == (80, 80, 0)
    assert game.is_cooling_down() is False


# ======================= 기능 4: 쿨타임 =======================

def test_action_starts_cooldown(game):
    assert game.is_cooling_down() is False
    game.do_action(config.ACTION_FEED)
    assert game.cooldown == pytest.approx(1.0)
    assert game.is_cooling_down() is True


@pytest.mark.parametrize("second", [config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY])
def test_cooldown_shared_between_actions(game, second):
    game.do_action(config.ACTION_STUDY)
    before = gauges(game)
    assert game.do_action(second) is False
    assert gauges(game) == before


def test_0_999_ignored_1_0_allowed(game):
    game.do_action(config.ACTION_STUDY)          # 지식 10
    game.update(0.999)
    assert game.do_action(config.ACTION_STUDY) is False
    assert game.student.knowledge == 10
    game.update(0.001)
    assert game.is_cooling_down() is False
    assert game.do_action(config.ACTION_STUDY) is True
    assert game.student.knowledge == 20


def test_cooldown_60fps_frames(game):
    game.do_action(config.ACTION_STUDY)
    for _ in range(59):
        game.update(1 / 60)
    assert game.is_cooling_down() is True
    assert game.do_action(config.ACTION_STUDY) is False
    game.update(1 / 60)
    assert game.is_cooling_down() is False
    assert game.do_action(config.ACTION_STUDY) is True
    assert game.student.knowledge == 20


def test_cooldown_tenths_float_error(game):
    """0.1을 10번 흘려도(0.9999999...) 1초로 보고 쿨타임이 끝난다."""
    game.do_action(config.ACTION_STUDY)
    for _ in range(10):
        game.update(0.1)
    assert game.do_action(config.ACTION_STUDY) is True


def test_attempt_during_cooldown_does_not_extend(game):
    game.do_action(config.ACTION_FEED)
    game.update(0.5)
    game.do_action(config.ACTION_FEED)
    game.handle_event(key(pygame.K_2))
    game.handle_event(click(center(game, config.ACTION_STUDY)))
    assert game.cooldown == pytest.approx(0.5)
    game.update(0.5)
    assert game.is_cooling_down() is False
    assert game.do_action(config.ACTION_STUDY) is True


def test_cooldown_never_negative(game):
    game.do_action(config.ACTION_FEED)
    game.update(5.0)
    assert game.cooldown == 0.0


def test_cooldown_ignores_key_and_click(game):
    game.handle_event(key(pygame.K_3))
    before = gauges(game)
    game.handle_event(key(pygame.K_1))
    game.handle_event(key(pygame.K_2))
    game.handle_event(key(pygame.K_3))
    for name in game.buttons:
        game.handle_event(click(center(game, name)))
    assert gauges(game) == before


def test_cooldown_not_counting_outside_playing(game):
    """게임 화면이 아니면 update가 시간을 흘리지 않는다(쿨타임도 그대로)."""
    game.do_action(config.ACTION_FEED)
    game.state = config.STATE_TITLE
    game.update(5.0)
    assert game.cooldown == pytest.approx(1.0)


# ======================= 키보드 단축키 =======================

@pytest.mark.parametrize("k, expected", [
    (pygame.K_1, (100, 80, 0)),
    (pygame.K_2, (80, 100, 0)),
    (pygame.K_3, (75, 72, 10)),
])
def test_keys(game, k, expected):
    game.handle_event(key(k))
    assert gauges(game) == expected
    assert game.is_cooling_down() is True


@pytest.mark.parametrize("k", [pygame.K_KP1, pygame.K_KP2, pygame.K_KP3])
def test_numpad_keys_no_action(game, k):
    """(4일차 리드 결정) 숫자패드는 기획서에 없으므로 행동을 일으키지 않는다."""
    game.handle_event(key(k))
    assert gauges(game) == (80, 80, 0)
    assert game.is_cooling_down() is False


@pytest.mark.parametrize("k", [pygame.K_0, pygame.K_4, pygame.K_a, pygame.K_RETURN, pygame.K_r,
                               pygame.K_SPACE])
def test_other_keys_no_action(game, k):
    game.handle_event(key(k))
    assert gauges(game) == (80, 80, 0)
    assert game.is_cooling_down() is False


def test_keyup_no_action(game):
    game.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_1, mod=0))
    assert gauges(game) == (80, 80, 0)


def test_escape_still_quits(game):
    game.handle_event(key(pygame.K_ESCAPE))
    assert game.running is False


# ======================= 버튼 클릭 =======================

@pytest.mark.parametrize("name, expected", [
    (config.ACTION_FEED, (100, 80, 0)),
    (config.ACTION_REST, (80, 100, 0)),
    (config.ACTION_STUDY, (75, 72, 10)),
])
def test_click_each_button(game, name, expected):
    game.handle_event(click(center(game, name)))
    assert gauges(game) == expected
    assert game.is_cooling_down() is True


@pytest.mark.parametrize("btn", [pygame.BUTTON_RIGHT, pygame.BUTTON_MIDDLE,
                                 pygame.BUTTON_WHEELUP, pygame.BUTTON_WHEELDOWN])
def test_non_left_click_ignored(game, btn):
    game.handle_event(click(center(game, config.ACTION_FEED), button=btn))
    game.handle_event(click(center(game, config.ACTION_STUDY), button=btn))
    assert gauges(game) == (80, 80, 0)
    assert game.is_cooling_down() is False


def test_mouse_up_ignored(game):
    game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=center(game, config.ACTION_FEED),
                                         button=pygame.BUTTON_LEFT))
    assert gauges(game) == (80, 80, 0)


def test_click_outside_buttons(game):
    feed = game.buttons[config.ACTION_FEED].rect
    rest = game.buttons[config.ACTION_REST].rect
    for pos in [(0, 0), (400, 300), (feed.left - 1, feed.centery),
                (feed.right, feed.centery),           # 버튼 사이 간격
                (rest.left - 1, rest.centery),
                (feed.centerx, feed.top - 1), (feed.centerx, feed.bottom)]:
        game.handle_event(click(pos))
    assert gauges(game) == (80, 80, 0)
    assert game.is_cooling_down() is False


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
    rects = [game.buttons[n].rect for n in (config.ACTION_FEED, config.ACTION_REST,
                                            config.ACTION_STUDY)]
    for r in rects:
        assert r.size == (config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
        assert r.top == config.BUTTON_Y
        assert 0 <= r.left and r.right <= config.SCREEN_WIDTH
        assert r.bottom <= config.SCREEN_HEIGHT
    assert rects[0].right <= rects[1].left and rects[1].right <= rects[2].left
    # 가운데 정렬
    assert rects[0].left == config.SCREEN_WIDTH - rects[2].right


def test_button_texts(game):
    assert game.buttons[config.ACTION_FEED].text == "학식 먹이기 [1]"
    assert game.buttons[config.ACTION_REST].text == "쉬게 하기 [2]"
    assert game.buttons[config.ACTION_STUDY].text == "공부시키기 [3]"
    assert len(game.buttons) == 3


def test_draw_renders_button_texts_and_hint(game):
    rec = RecordingFont(game.font)
    game.font = rec
    game.draw()
    for t in ("학식 먹이기 [1]", "쉬게 하기 [2]", "공부시키기 [3]"):
        assert t in rec.texts
    assert any("누른 뒤 1초 동안 회색" in t for t in rec.texts)


# ======================= 쿨타임 회색 (픽셀) =======================

def test_buttons_normal_color(game):
    game.draw()
    for name in game.buttons:
        assert color_at(game.screen, button_body_point(game, name)) == config.COLOR_BUTTON


def test_buttons_gray_during_cooldown_then_back(game):
    game.handle_event(key(pygame.K_1))
    game.draw()
    for name in game.buttons:
        assert color_at(game.screen, button_body_point(game, name)) == config.COLOR_GRAY
    game.update(0.999)
    game.draw()
    for name in game.buttons:
        assert color_at(game.screen, button_body_point(game, name)) == config.COLOR_GRAY
    game.update(0.001)
    game.draw()
    for name in game.buttons:
        assert color_at(game.screen, button_body_point(game, name)) == config.COLOR_BUTTON


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
    game.state = state
    for k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_KP1, pygame.K_KP2, pygame.K_KP3):
        game.handle_event(key(k))
    for name in list(game.buttons):
        game.handle_event(click(center(game, name)))
    assert gauges(game) == (80, 80, 0)
    assert game.is_cooling_down() is False


@pytest.mark.parametrize("state", [config.STATE_TITLE, config.STATE_ENDING])
def test_escape_quits_in_any_state(game, state):
    game.state = state
    game.handle_event(key(pygame.K_ESCAPE))
    assert game.running is False


# ======================= 완료 기준: 클릭과 1~3키로 게이지가 변함 =======================

def test_done_criteria_play_sequence(game):
    """키 1 -> 1초 -> 클릭 공부 -> 1초 -> 키 2 를 실제 이벤트로 진행."""
    game.handle_event(key(pygame.K_1))
    assert gauges(game) == (100, 80, 0)
    for _ in range(60):
        game.update(1 / 60)                       # 자연 감소 1회: 99, 79
    game.handle_event(click(center(game, config.ACTION_STUDY)))
    assert gauges(game) == (94, 71, 10)
    for _ in range(60):
        game.update(1 / 60)                       # 93, 70
    game.handle_event(key(pygame.K_2))
    assert gauges(game) == (93, 90, 8)
    game.draw()


def test_done_criteria_bar_redrawn_after_action(game):
    """행동 후 다시 그리면 체력 막대 채움 폭이 바뀐다."""
    game.student.health = 50
    game.draw()
    y = config.HEALTH_BAR_Y + config.BAR_HEIGHT // 2
    x_after_50 = config.GAUGE_X + config.BAR_WIDTH * 60 // config.GAUGE_MAX
    assert color_at(game.screen, (x_after_50, y)) == config.COLOR_BAR_BG
    game.handle_event(key(pygame.K_1))
    game.draw()
    assert game.student.health == 70
    assert color_at(game.screen, (x_after_50, y)) == config.COLOR_GREEN
