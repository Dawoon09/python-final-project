"""(명성 칭호) 명성에 따라 칭호가 오르고 타이틀에 보이며, 환생으로 오르면 알림. 게임 수치에는 영향 없음."""

import pygame
import pytest

import config
from conftest import press
from game import Game


@pytest.fixture
def g():
    """타이틀 Game."""
    game = Game(seed=2)
    yield game
    pygame.quit()


@pytest.mark.parametrize("fame, title", [
    (0, "시간강사"), (1, "시간강사"), (2, "조교수"), (4, "조교수"), (5, "부교수"), (9, "부교수"),
    (10, "정교수"), (19, "정교수"), (20, "명예교수"), (99, "명예교수"),
])
def test_title_by_fame(g, fame, title):
    assert g.get_fame_title(fame) == title
    g.fame = fame
    assert g.get_fame_title() == title


def test_titles_ascending():
    needs = [n for n, _ in config.FAME_TITLES]
    assert needs[0] == 0 and needs == sorted(needs) and len(set(needs)) == len(needs)


def test_title_screen_shows_title(g):
    g.fame, g.money = 5, 300
    texts = []
    real = g.font

    class Spy:
        """render 호출을 기록하는 래퍼."""

        def render(self, text, *a, **k):
            texts.append(text)
            return real.render(text, *a, **k)

        def __getattr__(self, attr):
            return getattr(real, attr)

    g.font = Spy()
    g.draw()
    assert "부교수 · 명성 5 · 연구비 300" in texts


def test_longest_wallet_fits_panel(g):
    panel = pygame.Rect(config.MENU_PANEL_RECT).inflate(-2 * config.PIXEL_SIZE, 0)
    w, _ = g.font.size(config.TITLE_WALLET_TEXT.format("명예교수", 999, 9999999))
    assert w <= panel.width


def graduate_and_reincarnate(g):
    """졸업시키고 R로 환생한다."""
    press(g, pygame.K_RETURN)
    g.student.knowledge = config.GRADUATION_KNOWLEDGE
    g.check_promotion()
    g.check_ending()
    assert g.can_reincarnate()
    press(g, pygame.K_r)


def test_reincarnate_promotion_notice(g):
    g.fame = 1
    graduate_and_reincarnate(g)
    assert g.fame == 2
    assert g.promotion_notice is not None
    assert g.promotion_notice["text"] == "조교수 승진!"


def test_no_notice_without_title_change(g):
    g.fame = 2
    graduate_and_reincarnate(g)
    assert g.fame == 3
    assert g.promotion_notice is None


def test_title_does_not_change_money_ratio(g):
    g.fame = 4
    before = g.get_fame_multiplier()
    g.fame = 5   # 칭호가 오른다
    assert g.get_fame_multiplier() == pytest.approx(before + config.FAME_MONEY_BONUS)


def test_new_game_resets_title(g):
    g.fame = 12
    g.money = 10
    press(g, pygame.K_n)
    press(g, pygame.K_y)
    assert g.get_fame_title() == "시간강사"
