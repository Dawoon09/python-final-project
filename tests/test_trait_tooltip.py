"""(특성 배지 툴팁) 특성 배지에 마우스를 올리면 효과 한 줄이 뜬다: 글자, 조건, 위치, 알파 없음."""

import pygame
import pytest

import config
from game import Game

P = config.PIXEL_SIZE
TRAITS = [config.TRAIT_FITNESS, config.TRAIT_MUSIC, config.TRAIT_CAFFEINE, config.TRAIT_LOVE]
EXPECTED = {
    config.TRAIT_FITNESS: "체력 단련: 학식 든든함 +10초 (이번 판 끝까지)",
    config.TRAIT_MUSIC: "음악 힐링: 휴식 멘탈 +5 (이번 판 끝까지)",
    config.TRAIT_CAFFEINE: "카페인: 공부 체력 소모 -2 (이번 판 끝까지)",
    config.TRAIT_LOVE: "연애 중: 휴식 체력 +5 (이번 판 끝까지)",
}


@pytest.fixture
def g():
    """특성 4종을 모두 가진 게임 화면 Game."""
    game = Game(seed=1)
    game.start_new_game()
    for trait in TRAITS:
        game.student.add_trait(trait)
    yield game
    pygame.quit()


def badge(g, index):
    """index번째 특성 배지 사각형."""
    return g.student.get_badge_rect(index, config.TRAIT_BADGE_Y)


@pytest.mark.parametrize("trait", TRAITS)
def test_tip_text(g, trait):
    assert g.get_trait_tip_text(trait) == EXPECTED[trait]


def test_tip_text_follows_config(g, monkeypatch):
    monkeypatch.setitem(config.TRAIT_BONUSES, config.TRAIT_MUSIC, {config.BONUS_REST_MENTAL: 7})
    assert g.get_trait_tip_text(config.TRAIT_MUSIC) == "음악 힐링: 휴식 멘탈 +7 (이번 판 끝까지)"


def test_every_trait_bonus_has_tip_effect():
    for bonuses in config.TRAIT_BONUSES.values():
        for bonus_name in bonuses:
            assert bonus_name in config.TRAIT_TIP_EFFECTS


@pytest.mark.parametrize("index", range(len(TRAITS)))
def test_hover_each_badge(g, index):
    g.mouse_pos = badge(g, index).center
    assert g.get_hovered_trait() == (index, TRAITS[index])
    g.draw()
    rect = g.draw_trait_tooltip()
    assert rect is not None


def test_badge_edges(g):
    r = badge(g, 0)
    g.mouse_pos = (r.right - 1, r.bottom - 1)
    assert g.get_hovered_trait() == (0, TRAITS[0])
    g.mouse_pos = (r.right, r.bottom)  # 배지 바로 바깥(사이 간격)
    assert g.get_hovered_trait() is None


@pytest.mark.parametrize("case", ["no_mouse", "away", "panel_open", "title", "ending", "event"])
def test_no_tooltip_when_not_allowed(g, case):
    g.mouse_pos = badge(g, 0).center
    if case == "no_mouse":
        g.mouse_pos = None
    elif case == "away":
        g.mouse_pos = (config.SCREEN_WIDTH - 1, config.SCREEN_HEIGHT - 1)
    elif case == "panel_open":
        g.upgrade_panel_open = True
    elif case == "title":
        g.state = config.STATE_TITLE
    elif case == "ending":
        g.state = config.STATE_ENDING
    elif case == "event":
        g.state = config.STATE_EVENT
    assert g.get_hovered_trait() is None
    assert g.draw_trait_tooltip() is None


def test_no_traits_no_tooltip():
    game = Game(seed=1)
    game.start_new_game()
    game.mouse_pos = badge(game, 0).center
    assert game.get_hovered_trait() is None
    pygame.quit()


@pytest.mark.parametrize("index", range(len(TRAITS)))
def test_tooltip_position(g, index):
    g.mouse_pos = badge(g, index).center
    rect = g.get_tooltip_rect([(g.get_trait_tip_text(TRAITS[index]), config.COLOR_TOOLTIP_TITLE)],
                              badge(g, index).top)
    panel = pygame.Rect(config.STATUS_PANEL_X, config.PANEL_Y, config.STATUS_PANEL_WIDTH,
                        config.PANEL_HEIGHT)
    assert rect.left == config.TOOLTIP_X and rect.left > panel.right
    assert rect.top >= config.TOOLTIP_TOP_MIN
    assert rect.bottom + P <= config.TOOLTIP_BOTTOM_MAX  # 아래 그림자 포함
    assert rect.right <= config.TOOLTIP_RIGHT_MAX
    # 글자가 상자 안에 들어간다
    text_w, _ = g.small_font.size(g.get_trait_tip_text(TRAITS[index]))
    assert text_w + 2 * config.TOOLTIP_PAD_X <= rect.width


def test_drawn_on_screen_without_alpha(g, monkeypatch):
    g.mouse_pos = badge(g, 1).center
    created = []
    real_surface = pygame.Surface

    def spy(*args, **kwargs):
        surf = real_surface(*args, **kwargs)
        created.append(surf)
        return surf

    monkeypatch.setattr(pygame, "Surface", spy)
    g.draw()
    for surf in created:
        assert not (surf.get_flags() & pygame.SRCALPHA)
        assert surf.get_alpha() is None
    rect = g.get_tooltip_rect([(EXPECTED[TRAITS[1]], config.COLOR_TOOLTIP_TITLE)], badge(g, 1).top)
    inner = (rect.left + 2 * P, rect.bottom - 3 * P)
    assert tuple(g.screen.get_at(inner))[:3] == tuple(config.COLOR_TOOLTIP)[:3]


def test_draw_calls_trait_tooltip_text(g):
    g.mouse_pos = badge(g, 2).center
    calls = []
    real = g.small_font

    class Spy:
        """render 호출을 기록하는 래퍼."""

        def render(self, text, antialias, *args, **kwargs):
            calls.append((text, antialias))
            return real.render(text, antialias, *args, **kwargs)

        def __getattr__(self, attr):
            return getattr(real, attr)

    g.small_font = Spy()
    g.draw()
    assert (EXPECTED[TRAITS[2]], False) in calls


def test_status_and_trait_tooltips_do_not_both_show(g):
    """상태 배지(위)와 특성 배지(아래)는 자리가 달라 마우스 하나로 둘 다 뜨지 않는다."""
    g.student.health = 10  # 피곤 배지가 생김
    g.mouse_pos = badge(g, 0).center
    assert g.get_hovered_status() is None and g.get_hovered_trait() is not None
    g.mouse_pos = g.student.get_badge_rect(0, config.STATUS_BADGE_Y).center
    assert g.get_hovered_status() is not None and g.get_hovered_trait() is None
