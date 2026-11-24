"""(개운함) 쉬게 하기 뒤 20초 동안 멘탈 자연 감소 x0.5: 지속·덮어쓰기·시험 기간·배지·툴팁·새 판."""

import pygame
import pytest

import config
from game import Game
from student import Student


def fresh(**up):
    """업그레이드만 정한 학생(시험 기간 아님, 경과 1초)."""
    upgrades = {u: 0 for u in config.UPGRADE_IDS}
    upgrades.update(up)
    s = Student(upgrades)
    s.elapsed = 1.0
    return s


@pytest.fixture
def g():
    """게임 화면 Game."""
    game = Game(seed=7)
    game.start_new_game()
    yield game
    pygame.quit()


def test_constants():
    assert config.BUFF_REFRESH == "개운함"
    assert config.REFRESH_DURATION == 20.0 and config.REFRESH_MENTAL_DECAY_RATIO == 0.5


def test_rest_gives_refresh():
    s = fresh()
    assert not s.is_refresh_buff_active() and s.refresh_until is None
    s.rest()
    assert s.is_refresh_buff_active()
    assert s.get_refresh_time_left() == pytest.approx(20.0)


def test_feed_and_study_do_not_give_refresh():
    s = fresh()
    s.feed()
    s.study()
    assert not s.is_refresh_buff_active()


def test_mental_decay_halved_only_while_active():
    s = fresh()
    assert s.get_mental_decay() == 1
    s.rest()
    assert s.get_mental_decay() == 0.5
    assert s.get_health_decay() == 1          # 체력은 그대로
    s.elapsed += 19.99
    assert s.get_mental_decay() == 0.5
    s.elapsed += 0.02
    assert s.get_mental_decay() == 1


def test_exam_mental_decay_halved():
    s = fresh()
    s.elapsed = 46.0
    s.rest()
    assert s.is_exam_period()
    assert s.get_mental_decay() == 1.0        # 2 x 0.5


def test_with_health_care_upgrade():
    s = fresh(**{config.UPGRADE_HEALTH_CARE: 5})
    s.rest()
    assert s.get_mental_decay() == pytest.approx(0.25)   # 1 x 0.5 x 0.5


def test_rest_again_resets_timer():
    s = fresh()
    s.rest()
    s.elapsed += 15
    s.rest()
    assert s.get_refresh_time_left() == pytest.approx(20.0)


def test_decay_once_uses_refresh():
    s = fresh()
    s.mental = 50
    s.rest()
    m = s.mental
    s.decay_once()
    assert s.mental == pytest.approx(m - 0.5)


def test_status_badge_order():
    s = fresh()
    s.health, s.mental = 20, 20
    s.feed()
    s.rest()
    s.health, s.mental = 20, 20
    assert s.get_statuses() == [config.DEBUFF_TIRED, config.DEBUFF_DEPRESSED, config.BUFF_FULL,
                                config.BUFF_REFRESH]


def test_tooltip_text(g):
    g.student.rest()
    g.student.elapsed += 7.2
    assert g.get_status_tip_text(config.BUFF_REFRESH) == "개운함: 남은 시간 13초 — 멘탈 감소 ×0.5"


def test_badge_drawn_with_icon_and_color(g):
    assert config.BUFF_REFRESH in config.STATUS_ICONS
    assert config.BUFF_REFRESH in config.STATUS_COLORS
    grid = config.STATUS_ICONS[config.BUFF_REFRESH]
    assert len(grid) == 6 and all(len(r) == 8 for r in grid)
    for row in grid:
        for ch in row:
            assert ch == "." or ch in config.STATUS_ICON_COLORS
    g.student.rest()
    g.draw()
    names = g.get_status_names()
    assert config.BUFF_REFRESH in names


def test_max_four_badges_fit_above_health():
    """동시에 붙을 수 있는 배지는 최대 4개(컨디션 좋음은 피곤·우울과 함께 안 붙음) -> 2줄."""
    s = fresh()
    rects = [s.get_badge_rect(i, config.STATUS_BADGE_Y) for i in range(4)]
    assert max(r.bottom for r in rects) + config.PIXEL_SIZE <= config.HEALTH_LABEL_Y


def test_auto_rest_in_game_gives_badge(g):
    g.student.health = 10
    g.do_action(g.choose_auto_action())
    assert g.last_action == config.ACTION_REST
    assert config.BUFF_REFRESH in g.get_status_names()


def test_new_round_clears_refresh(g):
    g.student.rest()
    g.start_new_game()
    assert g.student.refresh_until is None


def test_kept_into_grad_school(g):
    g.student.rest()
    g.student.knowledge = config.GRADUATION_KNOWLEDGE
    g.check_promotion()
    g.check_ending()
    left = g.student.get_refresh_time_left()
    g.enter_grad_school()
    assert g.student.get_refresh_time_left() == pytest.approx(left)
