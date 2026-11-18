"""2일차 검수: Student 게이지, 자연 감소(기능 5), 게이지 막대(기능 6)."""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402


@pytest.fixture
def screen_font():
    """dummy 드라이버로 그릴 Surface와 한글 폰트를 준비한다."""
    pygame.init()
    surface = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    surface.fill(config.COLOR_BG)
    font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
    yield surface, font
    pygame.quit()


class RecordingFont:
    """render에 넘긴 글자를 기록하는 폰트 래퍼."""

    def __init__(self, font):
        self.font = font
        self.texts = []

    def render(self, text, *args, **kwargs):
        self.texts.append(text)
        return self.font.render(text, *args, **kwargs)


# ======================= 기능 5: 자연 감소 =======================

def test_one_second_decreases_by_one():
    s = Student()
    s.update(1.0)
    assert (s.health, s.mental, s.knowledge) == (79, 79, 0)


def test_0_999_seconds_no_change():
    s = Student()
    s.update(0.999)
    assert (s.health, s.mental) == (80, 80)


def test_0_999_then_small_step_triggers():
    s = Student()
    s.update(0.999)
    s.update(0.001)
    assert (s.health, s.mental) == (79, 79)


def test_frames_60fps_one_second_exact():
    s = Student()
    for _ in range(60):
        s.update(1 / 60)
    assert (s.health, s.mental) == (79, 79)


def test_frames_59_of_60_no_change():
    s = Student()
    for _ in range(59):
        s.update(1 / 60)
    assert (s.health, s.mental) == (80, 80)


def test_tenths_ten_times_exact():
    """0.1을 10번 더해도(0.9999999...) 정확히 1번 감소."""
    s = Student()
    for _ in range(10):
        s.update(0.1)
    assert (s.health, s.mental) == (79, 79)


def test_frames_60fps_ten_seconds_exact():
    s = Student()
    for _ in range(600):
        s.update(1 / 60)
    assert (s.health, s.mental) == (70, 70)


def test_frames_60fps_long_run_no_drift():
    """60초 분량 프레임을 누적해도 정확히 60 감소(오차 누적 없음)."""
    s = Student()
    s.health = s.mental = 100
    for _ in range(60 * 60):
        s.update(1 / 60)
    assert (s.health, s.mental) == (40, 40)


def test_irregular_frames():
    s = Student()
    for dt in [0.016, 0.017, 0.033, 0.5, 0.2, 0.234]:  # 합계 1.0
        s.update(dt)
    assert (s.health, s.mental) == (79, 79)


def test_large_dt_multiple_decays():
    s = Student()
    s.update(3.0)
    assert (s.health, s.mental) == (77, 77)


def test_large_dt_with_remainder_kept():
    s = Student()
    s.update(2.5)
    assert (s.health, s.mental) == (78, 78)
    s.update(0.5)
    assert (s.health, s.mental) == (77, 77)


def test_decay_never_below_zero():
    s = Student()
    s.update(500.0)
    assert (s.health, s.mental) == (0, 0)
    for _ in range(100):
        s.update(1.0)
    assert (s.health, s.mental) == (0, 0)


def test_knowledge_no_natural_decay():
    s = Student()
    s.change_knowledge(50)
    s.update(30.0)
    assert s.knowledge == 50


def test_elapsed_accumulates():
    s = Student()
    for _ in range(120):
        s.update(1 / 60)
    assert s.elapsed == pytest.approx(2.0)


def test_mental_decay_normal_is_one():
    assert Student().get_mental_decay() == 1


def test_decay_once():
    s = Student()
    s.decay_once()
    assert (s.health, s.mental) == (79, 79)


def test_update_zero_dt_no_change():
    s = Student()
    s.update(0)
    assert (s.health, s.mental) == (80, 80)


# ======================= 게이지 범위 =======================

@pytest.mark.parametrize("amount, expected", [
    (1000, 100), (20, 100), (19, 99), (-79, 1), (-80, 0), (-1000, 0), (0, 80),
])
def test_change_health_clamp(amount, expected):
    s = Student()
    s.change_health(amount)
    assert s.health == expected


@pytest.mark.parametrize("amount, expected", [
    (1000, 100), (20, 100), (19, 99), (-79, 1), (-80, 0), (-1000, 0), (0, 80),
])
def test_change_mental_clamp(amount, expected):
    s = Student()
    s.change_mental(amount)
    assert s.mental == expected


def test_repeated_increase_stays_100():
    s = Student()
    for _ in range(50):
        s.change_health(20)
        s.change_mental(20)
    assert (s.health, s.mental) == (100, 100)


def test_knowledge_not_negative_and_no_upper_limit():
    s = Student()
    s.change_knowledge(-2)
    assert s.knowledge == 0
    s.change_knowledge(1)
    s.change_knowledge(-2)
    assert s.knowledge == 0
    s.change_knowledge(100000)
    assert s.knowledge == 100000


def test_is_dropped_out():
    s = Student()
    assert s.is_dropped_out() is False
    s.change_health(-80)
    assert s.is_dropped_out() is True
    s = Student()
    s.change_mental(-80)
    assert s.is_dropped_out() is True
    s = Student()
    s.change_health(-79)
    s.change_mental(-79)
    assert s.is_dropped_out() is False


def test_dropped_out_by_natural_decay_after_80s():
    s = Student()
    s.update(79.0)
    assert s.is_dropped_out() is False
    s.update(1.0)
    assert s.is_dropped_out() is True


# ======================= 기능 6: 게이지 막대 =======================

def _mid_y(bar_y):
    return bar_y + config.BAR_HEIGHT // 2


def _inner_x():
    """테두리 바로 안쪽 x."""
    return config.GAUGE_X + config.BAR_BORDER_WIDTH + 1


def _color(surface, x, y):
    return tuple(surface.get_at((x, y)))[:3]


@pytest.mark.parametrize("value, expected", [
    # 값 1은 채움 폭 2px가 테두리 2px에 완전히 가려져 보이지 않는다(낮음 등급으로 보고).
    (2, config.COLOR_RED), (10, config.COLOR_RED), (29, config.COLOR_RED),
    (30, config.COLOR_GREEN), (31, config.COLOR_GREEN), (80, config.COLOR_GREEN),
    (100, config.COLOR_GREEN),
])
def test_bar_color_threshold_health(screen_font, value, expected):
    surface, font = screen_font
    s = Student()
    s.health = value
    s.draw_gauges(surface, font)
    assert _color(surface, _inner_x(), _mid_y(config.HEALTH_BAR_Y)) == expected


@pytest.mark.parametrize("value, expected", [
    (29, config.COLOR_RED), (30, config.COLOR_GREEN),
])
def test_bar_color_threshold_mental(screen_font, value, expected):
    surface, font = screen_font
    s = Student()
    s.mental = value
    s.draw_gauges(surface, font)
    assert _color(surface, _inner_x(), _mid_y(config.MENTAL_BAR_Y)) == expected


def test_red_health_green_mental_independent(screen_font):
    surface, font = screen_font
    s = Student()
    s.health, s.mental = 29, 30
    s.draw_gauges(surface, font)
    assert _color(surface, _inner_x(), _mid_y(config.HEALTH_BAR_Y)) == config.COLOR_RED
    assert _color(surface, _inner_x(), _mid_y(config.MENTAL_BAR_Y)) == config.COLOR_GREEN


def _fill_count(surface, bar_y):
    """막대 가운데 줄에서 채움 색(빨강/초록) 픽셀 수."""
    y = _mid_y(bar_y)
    count = 0
    for x in range(config.GAUGE_X, config.GAUGE_X + config.BAR_WIDTH):
        if _color(surface, x, y) in (config.COLOR_RED, config.COLOR_GREEN):
            count += 1
    return count


@pytest.mark.parametrize("value", [10, 25, 29, 30, 50, 79, 80, 90])
def test_bar_fill_proportional(screen_font, value):
    surface, font = screen_font
    s = Student()
    s.health = value
    s.mental = value
    s.draw_gauges(surface, font)
    fill_width = config.BAR_WIDTH * value // config.GAUGE_MAX
    # 왼쪽 테두리(BAR_BORDER_WIDTH)가 채움 앞부분을 덮는다
    expected = fill_width - config.BAR_BORDER_WIDTH
    assert _fill_count(surface, config.HEALTH_BAR_Y) == expected
    assert _fill_count(surface, config.MENTAL_BAR_Y) == expected
    # 채움 끝 바로 다음 칸은 빈 배경
    y = _mid_y(config.HEALTH_BAR_Y)
    assert _color(surface, config.GAUGE_X + fill_width, y) == config.COLOR_BAR_BG
    assert _color(surface, config.GAUGE_X + fill_width - 1, y) != config.COLOR_BAR_BG


def test_bar_full_and_empty(screen_font):
    surface, font = screen_font
    s = Student()
    s.health, s.mental = 100, 0
    s.draw_gauges(surface, font)
    y_h = _mid_y(config.HEALTH_BAR_Y)
    y_m = _mid_y(config.MENTAL_BAR_Y)
    right_inner = config.GAUGE_X + config.BAR_WIDTH - config.BAR_BORDER_WIDTH - 1
    assert _color(surface, right_inner, y_h) == config.COLOR_GREEN
    assert _fill_count(surface, config.MENTAL_BAR_Y) == 0
    assert _color(surface, _inner_x(), y_m) == config.COLOR_BAR_BG


def test_bar_has_border(screen_font):
    surface, font = screen_font
    Student().draw_gauges(surface, font)
    assert _color(surface, config.GAUGE_X, _mid_y(config.HEALTH_BAR_Y)) == config.COLOR_BLACK
    assert _color(surface, config.GAUGE_X + config.BAR_WIDTH - 1,
                  _mid_y(config.HEALTH_BAR_Y)) == config.COLOR_BLACK


def test_knowledge_drawn_as_number(screen_font):
    surface, font = screen_font
    rec = RecordingFont(font)
    s = Student()
    s.change_knowledge(123)
    s.draw_gauges(surface, rec)
    assert "지식 123" in rec.texts
    assert config.HEALTH_LABEL in rec.texts
    assert config.MENTAL_LABEL in rec.texts


def test_knowledge_text_in_top_right(screen_font):
    """지식 숫자가 정보바 오른쪽(상단)에 그려진다: 그 구역 픽셀이 배경색이 아님."""
    surface, font = screen_font
    Student().draw_gauges(surface, font)
    region = pygame.Rect(config.SCREEN_WIDTH // 2, 0,
                         config.SCREEN_WIDTH // 2, config.HEALTH_LABEL_Y)
    changed = any(
        _color(surface, x, y) != config.COLOR_BG
        for x in range(region.left, region.right)
        for y in range(region.top, region.bottom)
    )
    assert changed


# ======================= 완료 기준: 시간이 지나면 막대가 줄어듦 =======================

def test_game_bar_shrinks_over_time():
    g = Game()
    try:
        g.draw()
        before = _fill_count(g.screen, config.HEALTH_BAR_Y)
        for _ in range(60 * 5):
            g.update(1 / 60)
        g.draw()
        after = _fill_count(g.screen, config.HEALTH_BAR_Y)
        assert g.student.health == 75 and g.student.mental == 75
        assert before - after == config.BAR_WIDTH * 5 // config.GAUGE_MAX
        assert _fill_count(g.screen, config.MENTAL_BAR_Y) == after
    finally:
        pygame.quit()


def test_game_bar_turns_red_when_below_30():
    g = Game()
    try:
        g.update(51.0)  # 80 -> 29
        g.draw()
        x, y = _inner_x(), _mid_y(config.HEALTH_BAR_Y)
        assert g.student.health == 29
        assert _color(g.screen, x, y) == config.COLOR_RED
    finally:
        pygame.quit()


def test_game_update_only_in_playing_state():
    g = Game()
    try:
        g.state = config.STATE_TITLE
        g.update(5.0)
        assert g.student.health == 80
        g.state = config.STATE_ENDING
        g.update(5.0)
        assert g.student.health == 80
        g.state = config.STATE_PLAYING
        g.update(5.0)
        assert g.student.health == 75
    finally:
        pygame.quit()


def test_game_draw_after_long_time_no_crash():
    g = Game()
    try:
        g.update(1000.0)
        g.draw()
        assert (g.student.health, g.student.mental) == (0, 0)
    finally:
        pygame.quit()
