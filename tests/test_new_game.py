"""(타이틀 새 게임) Enter 이어하기 / N 새 게임 확인 상자(Y 시작, N·Backspace 취소, ESC 종료) 검수."""

import json

import pygame
import pytest

import config
from button import sprite_size
from conftest import press
from game import Game

P = config.PIXEL_SIZE
BEST = 777  # 테스트용 최고 기록
SAVED = {"menu": 3, "bed": 1, "library": 1, "self_care": 2}  # 테스트용 업그레이드 레벨


def write_record(path, money=500, fame=2, upgrades=None, best=BEST):
    """테스트용 record.json을 쓴다."""
    data = {config.RECORD_KEY: best, config.RECORD_MONEY_KEY: money,
            config.RECORD_FAME_KEY: fame,
            config.RECORD_UPGRADES_KEY: dict(SAVED if upgrades is None else upgrades)}
    with open(path, "w", encoding=config.RECORD_ENCODING) as file:
        json.dump(data, file)


def read_record(path):
    """record.json을 읽어 사전으로 돌려준다."""
    with open(path, encoding=config.RECORD_ENCODING) as file:
        return json.load(file)


@pytest.fixture
def make(isolated_record_path):
    """진행이 있는(또는 없는) record.json으로 타이틀 Game을 만든다."""
    games = []

    def factory(**record):
        write_record(isolated_record_path, **record)
        g = Game(seed=1)
        games.append(g)
        return g

    yield factory
    pygame.quit()


def assert_reset(g):
    """진행이 모두 0이고 최고 기록은 남았는지 확인한다."""
    assert g.money == 0 and g.fame == 0
    assert set(g.upgrades) == set(config.UPGRADE_IDS)
    assert all(level == 0 for level in g.upgrades.values())
    assert g.best_record == BEST


# ----------------------------- 상수와 기본 상태 -----------------------------

def test_constants_and_initial_state(make):
    assert config.NEW_GAME_CONFIRM_TITLE == "새 게임을 시작할까요?"
    assert config.NEW_GAME_CONFIRM_WARNING == "업그레이드·연구비·명성이 모두 사라져요"
    assert config.FAME_START == 0
    g = make()
    assert g.state == config.STATE_TITLE and g.new_game_confirm is False
    assert g.has_progress()


@pytest.mark.parametrize("record, expected", [
    ({"money": 0, "fame": 0, "upgrades": {}}, False),
    ({"money": 1, "fame": 0, "upgrades": {}}, True),
    ({"money": 0, "fame": 1, "upgrades": {}}, True),
    ({"money": 0, "fame": 0, "upgrades": {"gym": 1}}, True),
])
def test_has_progress(make, record, expected):
    assert make(**record).has_progress() is expected


# ----------------------------- N → Y / N / Backspace -----------------------------

def test_n_opens_confirm_and_stays_on_title(make, isolated_record_path):
    g = make()
    press(g, pygame.K_n)
    assert g.new_game_confirm is True
    assert g.state == config.STATE_TITLE
    # 아직 아무것도 지우지 않았다(메모리·파일 모두)
    assert g.money == 500 and g.fame == 2 and g.upgrades["menu"] == 3
    assert read_record(isolated_record_path)[config.RECORD_MONEY_KEY] == 500


def test_y_confirms_new_game(make, isolated_record_path):
    g = make()
    press(g, pygame.K_n)
    press(g, pygame.K_y)
    assert g.new_game_confirm is False
    assert g.state == config.STATE_PLAYING
    assert_reset(g)
    s = g.student
    assert (s.health, s.mental, s.knowledge, s.elapsed) == (80, 80, 0, 0)
    assert g.policy == config.POLICY_START and g.last_action is None
    # 제자는 Game과 같은 업그레이드 사전을 쓴다
    assert s.upgrades is g.upgrades
    assert s.max_health == config.GAUGE_MAX


@pytest.mark.parametrize("cancel_key", [pygame.K_n, pygame.K_BACKSPACE])
def test_n_or_backspace_cancels(make, isolated_record_path, cancel_key):
    g = make()
    before = read_record(isolated_record_path)
    press(g, pygame.K_n)
    press(g, cancel_key)
    assert g.new_game_confirm is False
    assert g.state == config.STATE_TITLE
    assert g.money == 500 and g.fame == 2 and g.upgrades["menu"] == 3
    assert read_record(isolated_record_path) == before
    # 다시 N을 누르면 상자가 또 뜬다
    press(g, pygame.K_n)
    assert g.new_game_confirm is True


@pytest.mark.parametrize("key", [pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r, pygame.K_c,
                                 pygame.K_1, pygame.K_u, pygame.K_SPACE, pygame.K_a])
def test_other_keys_ignored_while_confirming(make, key):
    g = make()
    press(g, pygame.K_n)
    press(g, key)
    assert g.new_game_confirm is True
    assert g.state == config.STATE_TITLE
    assert g.money == 500 and g.fame == 2


def test_y_without_confirm_does_nothing(make):
    g = make()
    press(g, pygame.K_y)
    assert g.state == config.STATE_TITLE and g.new_game_confirm is False
    assert g.money == 500


def test_n_without_progress_starts_at_once(make, isolated_record_path):
    g = make(money=0, fame=0, upgrades={})
    press(g, pygame.K_n)
    assert g.state == config.STATE_PLAYING and g.new_game_confirm is False
    assert_reset(g)
    assert read_record(isolated_record_path)[config.RECORD_KEY] == BEST


# ----------------------------- 저장 -----------------------------

def test_reset_progress_persists_and_keeps_best(make, isolated_record_path):
    g = make()
    same_dict = g.upgrades
    assert g.reset_progress() is True
    assert g.upgrades is same_dict  # 같은 사전을 고친다
    assert_reset(g)
    data = read_record(isolated_record_path)
    assert data[config.RECORD_KEY] == BEST
    assert data[config.RECORD_MONEY_KEY] == 0
    assert data[config.RECORD_FAME_KEY] == 0
    assert data[config.RECORD_UPGRADES_KEY] == {uid: 0 for uid in config.UPGRADE_IDS}
    # 다시 켜도 0 그대로, 최고 기록은 유지
    g2 = Game()
    assert_reset(g2)


def test_confirmed_new_game_saved_to_file(make, isolated_record_path):
    g = make()
    press(g, pygame.K_n)
    press(g, pygame.K_y)
    data = read_record(isolated_record_path)
    assert data[config.RECORD_KEY] == BEST
    assert (data[config.RECORD_MONEY_KEY], data[config.RECORD_FAME_KEY]) == (0, 0)
    assert all(v == 0 for v in data[config.RECORD_UPGRADES_KEY].values())


# ----------------------------- Enter 이어하기, ESC 종료 -----------------------------

def test_enter_continues_with_progress(make, isolated_record_path):
    g = make()
    before = read_record(isolated_record_path)
    press(g, pygame.K_RETURN)
    assert g.state == config.STATE_PLAYING and g.new_game_confirm is False
    assert g.money == 500 and g.fame == 2
    assert g.upgrades["menu"] == 3 and g.upgrades["library"] == 1
    assert g.student.upgrades is g.upgrades
    assert g.student.max_health == config.GAUGE_MAX  # health_max 0레벨
    assert g.best_record == BEST
    assert read_record(isolated_record_path) == before


@pytest.mark.parametrize("confirming", [False, True])
def test_esc_still_quits(make, isolated_record_path, confirming):
    g = make()
    before = read_record(isolated_record_path)
    if confirming:
        press(g, pygame.K_n)
    press(g, pygame.K_ESCAPE)
    assert g.running is False
    assert g.money == 500 and g.fame == 2
    assert read_record(isolated_record_path) == before


def test_n_ignored_outside_title(make):
    g = make()
    press(g, pygame.K_RETURN)
    press(g, pygame.K_n)
    assert g.state == config.STATE_PLAYING and g.new_game_confirm is False
    assert g.money == 500


# ----------------------------- 화면 -----------------------------

def text_rect(font, text, center_y):
    """가운데 정렬 글자 사각형."""
    rect = pygame.Rect(config.ORIGIN, font.size(text))
    rect.center = (config.SCREEN_CENTER_X, center_y)
    return rect


def test_confirm_box_layout_texts_fit(make):
    g = make()
    panel_inner = pygame.Rect(config.MENU_PANEL_RECT).inflate(-2 * P, -2 * P)
    box = pygame.Rect(config.NEW_GAME_CONFIRM_RECT)
    inner = box.inflate(-2 * P, -2 * P)
    assert panel_inner.contains(box.move(0, P))  # 아래 그림자까지 패널 안
    rows = [text_rect(g.font, config.NEW_GAME_CONFIRM_TITLE, config.NEW_GAME_CONFIRM_TITLE_Y),
            text_rect(g.event_font, config.NEW_GAME_CONFIRM_WARNING,
                      config.NEW_GAME_CONFIRM_WARNING_Y),
            text_rect(g.event_font, config.NEW_GAME_CONFIRM_KEYS, config.NEW_GAME_CONFIRM_KEYS_Y)]
    for i, r in enumerate(rows):
        assert inner.contains(r), r
        for other in rows[i + 1:]:
            assert not r.colliderect(other), (r, other)
    # 위쪽 명성·연구비 글자와 겹치지 않는다
    wallet = text_rect(g.font, config.TITLE_WALLET_TEXT.format(99, 999999), config.TITLE_WALLET_Y)
    assert not wallet.colliderect(box)


def test_title_hints_fit(make):
    g = make()
    panel_inner = pygame.Rect(config.MENU_PANEL_RECT).inflate(-2 * P, -2 * P)
    start = text_rect(g.font, config.START_HINT_TEXT, config.START_HINT_Y)
    aw, ah = sprite_size(config.ARROW_SPRITE, P)
    arrow = pygame.Rect(start.left - config.HINT_ARROW_GAP - aw, config.START_HINT_Y - ah // 2, aw, ah)
    start = start.union(arrow)
    hint = text_rect(g.font, config.NEW_GAME_HINT_TEXT, config.NEW_GAME_HINT_Y)
    assert "Enter" in config.NEW_GAME_HINT_TEXT and "N" in config.NEW_GAME_HINT_TEXT
    sw, sh = sprite_size(config.STAR_SPRITE, P)
    stars = [pygame.Rect(x, y, sw, sh) for x, y, _ in config.TITLE_STARS]
    for r in (start, hint):
        assert panel_inner.contains(r), r
        for star in stars:
            assert not r.colliderect(star), (r, star)
    assert start.bottom <= hint.top


def test_title_stars_hidden_only_under_box(make):
    g = make()
    assert g.get_title_stars() == config.TITLE_STARS
    press(g, pygame.K_n)
    box = pygame.Rect(config.NEW_GAME_CONFIRM_RECT)
    sw, sh = sprite_size(config.STAR_SPRITE, P)
    shown = g.get_title_stars()
    for x, y, color in config.TITLE_STARS:
        hits = box.colliderect((x, y, sw, sh))
        assert ((x, y, color) in shown) is (not hits)


def test_confirm_box_drawn_without_alpha(make, monkeypatch):
    g = make()
    press(g, pygame.K_n)
    created = []
    real_surface = pygame.Surface

    def spy_surface(*args, **kwargs):
        surf = real_surface(*args, **kwargs)
        created.append(surf)
        return surf

    monkeypatch.setattr(pygame, "Surface", spy_surface)
    g.draw()
    for surf in created:
        assert not (surf.get_flags() & pygame.SRCALPHA)
        assert surf.get_alpha() is None
    # 상자 몸통 색이 화면에 그대로(섞이지 않고) 찍혔다
    fill = config.NEW_GAME_CONFIRM_BOX[0]
    box = pygame.Rect(config.NEW_GAME_CONFIRM_RECT)
    probe = (box.left + 3 * P, box.bottom - 3 * P)
    assert tuple(g.screen.get_at(probe))[:3] == tuple(fill)[:3]


def test_confirm_texts_not_antialiased(make):
    g = make()
    press(g, pygame.K_n)
    calls = []
    for name in ("font", "event_font"):
        real = getattr(g, name)

        class Spy:
            """render 호출을 기록하는 래퍼."""

            def __init__(self, font):
                self.font = font

            def render(self, text, antialias, *args, **kwargs):
                calls.append((text, antialias))
                return self.font.render(text, antialias, *args, **kwargs)

            def __getattr__(self, attr):
                return getattr(self.font, attr)

        setattr(g, name, Spy(real))
    g.draw()
    texts = {t: aa for t, aa in calls}
    for t in (config.NEW_GAME_CONFIRM_TITLE, config.NEW_GAME_CONFIRM_WARNING,
              config.NEW_GAME_CONFIRM_KEYS):
        assert t in texts and texts[t] is False
    assert config.START_HINT_TEXT not in texts and config.NEW_GAME_HINT_TEXT not in texts


def test_title_shows_hint_when_not_confirming(make):
    g = make()
    calls = []
    real = g.font

    class Spy:
        """render 호출을 기록하는 래퍼."""

        def render(self, text, *args, **kwargs):
            calls.append(text)
            return real.render(text, *args, **kwargs)

        def __getattr__(self, attr):
            return getattr(real, attr)

    g.font = Spy()
    g.draw()
    assert config.START_HINT_TEXT in calls and config.NEW_GAME_HINT_TEXT in calls
    assert config.NEW_GAME_CONFIRM_TITLE not in calls
