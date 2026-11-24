"""(이벤트 로그) L키 패널: 기록 내용, 여닫기 규칙, 판마다 비우기, 배치·글자 맞춤, 알파 없음."""

import pygame
import pytest

import config
from conftest import press
from game import Game, format_time

P = config.PIXEL_SIZE


def event_by_id(event_id):
    """id로 이벤트 표의 항목을 찾는다."""
    return next(e for e in config.ALL_EVENTS if e[config.EVENT_ID] == event_id)


@pytest.fixture
def g():
    """게임 화면 Game (시드 고정)."""
    game = Game(seed=5)
    game.start_new_game()
    yield game
    pygame.quit()


def choose(g, event_id, index):
    """선택지형 이벤트를 띄우고 index번 선택지를 고른다."""
    g.start_event(event_by_id(event_id))
    g.dialog_time = config.EVENT_INPUT_DELAY
    assert g.choose_option(index)


# ----------------------------- 기록 -----------------------------

def test_starts_empty_and_closed(g):
    assert g.event_log == [] and g.event_log_open is False
    assert g.get_event_log_rows() == []


def test_auto_event_logged(g):
    g.student.elapsed = 12.4
    g.start_event(event_by_id("side_dish"))
    assert g.event_log == [{"time": 12.4, "title": "엄마가 반찬을 보내셨다", "result": "체력 +15"}]


def test_auto_event_with_two_effects(g):
    g.start_event(event_by_id("professor_praise"))
    assert g.event_log[-1]["result"] == "지식 +15 · 멘탈 +5"


def test_scholarship_logged_with_money(g):
    g.upgrades[config.UPGRADE_SCHOLARSHIP] = 1
    g.start_event(config.SCHOLARSHIP_EVENT)
    assert g.event_log[-1]["title"] == config.SCHOLARSHIP_EVENT[config.EVENT_TITLE]
    assert g.event_log[-1]["result"] == "연구비 +30"


def test_choice_logged_on_choose_not_on_start(g):
    g.start_event(event_by_id("free_rider"))
    assert g.event_log == []      # 고르기 전에는 기록 없음
    g.dialog_time = config.EVENT_INPUT_DELAY
    g.choose_option(config.CHOICE_FIRST)
    assert g.event_log[-1]["title"] == "조별과제 무임승차자"
    assert g.event_log[-1]["result"] == "혼자 다 한다 → 지식 +20 · 체력 -15 · 멘탈 -10"


def test_choice_with_trait_and_look(g):
    choose(g, "club_fair", config.CHOICE_FIRST)
    assert g.event_log[-1]["result"] == "밴드부 → 특성: 음악 힐링 · 외형: 기타"


def test_choice_with_trait_only(g):
    choose(g, "thesis_stress", config.CHOICE_FIRST)
    assert g.event_log[-1]["result"] == "명상을 배운다 → 멘탈 +10 · 특성: 명상"


def test_rows_newest_first_and_limited(g):
    for i in range(10):
        g.student.elapsed = float(i)
        g.start_event(event_by_id("group_chat_praise"))
    rows = g.get_event_log_rows()
    assert len(rows) == config.EVENT_LOG_ROWS == 7
    assert [r["time"] for r in rows] == [9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0]


def test_log_capped(g):
    for i in range(config.EVENT_LOG_MAX + 5):
        g.student.elapsed = float(i)
        g.start_event(event_by_id("cold"))
    assert len(g.event_log) == config.EVENT_LOG_MAX
    assert g.event_log[0]["time"] == 5.0


@pytest.mark.parametrize("how", ["start_new_game", "reincarnate", "restart_key"])
def test_cleared_on_new_round(g, how):
    g.start_event(event_by_id("cold"))
    assert g.event_log
    if how == "start_new_game":
        g.start_new_game()
    elif how == "reincarnate":
        g.student.knowledge = config.GRADUATION_KNOWLEDGE
        g.check_promotion()
        g.check_ending()
        assert g.can_reincarnate()
        g.reincarnate()
    else:
        g.student.health = 0
        g.check_ending()
        press(g, pygame.K_r)
    assert g.event_log == []


def test_kept_into_grad_school(g):
    g.start_event(event_by_id("cold"))
    g.student.knowledge = config.GRADUATION_KNOWLEDGE
    g.check_promotion()
    g.check_ending()
    g.enter_grad_school()
    assert g.student.is_in_grad_school()
    assert len(g.event_log) == 1


# ----------------------------- 여닫기 -----------------------------

def test_l_toggles_in_game(g):
    press(g, pygame.K_l)
    assert g.event_log_open
    press(g, pygame.K_l)
    assert not g.event_log_open


@pytest.mark.parametrize("state", [config.STATE_TITLE, config.STATE_ENDING, config.STATE_EVENT])
def test_l_ignored_elsewhere(g, state):
    g.state = state
    press(g, pygame.K_l)
    assert not g.event_log_open


def test_upgrade_and_log_exclusive(g):
    press(g, pygame.K_l)
    press(g, pygame.K_u)
    assert g.upgrade_panel_open and not g.event_log_open
    press(g, pygame.K_l)
    assert g.event_log_open and not g.upgrade_panel_open


def test_upgrade_button_click_closes_log(g):
    press(g, pygame.K_l)
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=pygame.BUTTON_LEFT,
                                      pos=g.upgrade_button.rect.center))
    assert g.upgrade_panel_open and not g.event_log_open


def test_policy_keys_work_while_log_open(g):
    press(g, pygame.K_l)
    press(g, pygame.K_1)
    assert g.policy == config.POLICY_STUDY_FOCUS
    assert g.event_log_open


def test_esc_quits_with_log_open(g):
    press(g, pygame.K_l)
    press(g, pygame.K_ESCAPE)
    assert g.running is False


def test_game_keeps_running_with_log_open(g):
    press(g, pygame.K_l)
    before = g.student.elapsed
    g.update(1.0)
    assert g.student.elapsed == pytest.approx(before + 1.0)


def test_tooltips_off_while_log_open(g):
    g.student.add_trait(config.TRAIT_MUSIC)
    g.student.health = 10
    press(g, pygame.K_l)
    g.mouse_pos = g.student.get_badge_rect(0, config.TRAIT_BADGE_Y).center
    assert g.get_hovered_trait() is None
    g.mouse_pos = g.student.get_badge_rect(0, config.STATUS_BADGE_Y).center
    assert g.get_hovered_status() is None


# ----------------------------- 화면 -----------------------------

def test_rows_inside_panel_without_overlap(g):
    panel = pygame.Rect(config.EVENT_LOG_PANEL_RECT).inflate(-2 * P, -2 * P)
    rects = [g.get_event_log_row_rect(i) for i in range(config.EVENT_LOG_ROWS)]
    for i, r in enumerate(rects):
        assert panel.contains(r), r
        assert r.top > config.UPGRADE_HEADER_Y + g.event_font.get_height() // 2
        for other in rects[i + 1:]:
            assert not r.colliderect(other)


def test_panel_above_policy_buttons():
    assert pygame.Rect(config.EVENT_LOG_PANEL_RECT).bottom + P <= config.BUTTON_Y


def test_fit_text(g):
    font = g.small_font
    assert g.fit_text(font, "짧음", 200) == "짧음"
    long = "혼자 다 한다 → 지식 +20 · 체력 -15 · 멘탈 -10 · 특성: 아침형 인간"
    cut = g.fit_text(font, long, 216)
    assert cut.endswith(config.EVENT_LOG_ELLIPSIS) and font.size(cut)[0] <= 216
    assert long.startswith(cut[:-1])


def test_drawn_texts_fit_rows(g, monkeypatch):
    choose(g, "free_rider", config.CHOICE_FIRST)
    choose(g, "club_fair", config.CHOICE_FIRST)
    g.start_event(event_by_id("side_dish"))
    press(g, pygame.K_l)
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
    width = config.EVENT_LOG_WIDTH - 2 * config.EVENT_LOG_PAD_X
    rows = g.get_event_log_rows()
    first = config.EVENT_LOG_LINE_TEXT.format(time=format_time(rows[0]["time"]),
                                              title=rows[0]["title"])
    drawn = [t for t, _ in calls]
    assert first in drawn
    assert all(aa is False for _, aa in calls)
    for t in drawn:
        if t in (config.EVENT_LOG_CLOSE_TEXT, config.EVENT_LOG_HINT_TEXT):
            continue
        assert real.size(t)[0] <= width, t


def test_empty_text_shown(g):
    press(g, pygame.K_l)
    calls = []
    real = g.small_font

    class Spy:
        """render 호출을 기록하는 래퍼."""

        def render(self, text, *args, **kwargs):
            calls.append(text)
            return real.render(text, *args, **kwargs)

        def __getattr__(self, attr):
            return getattr(real, attr)

    g.small_font = Spy()
    g.draw()
    assert config.EVENT_LOG_EMPTY_TEXT in calls


def test_panel_drawn_without_alpha(g, monkeypatch):
    g.start_event(event_by_id("cold"))
    press(g, pygame.K_l)
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
    # 패널 몸통 색이 그대로 찍혔다 (항목 상자 아래 빈 곳)
    panel = pygame.Rect(config.EVENT_LOG_PANEL_RECT)
    probe = (panel.centerx, panel.bottom - 4 * P)
    assert tuple(g.screen.get_at(probe))[:3] == tuple(config.COLOR_BG)[:3]


def test_hint_inside_screen_and_clear_of_others(g):
    hint = pygame.Rect(config.ORIGIN, g.small_font.size(config.EVENT_LOG_HINT_TEXT))
    hint.center = (config.ELAPSED_CENTER_X, config.EVENT_LOG_HINT_Y)
    assert pygame.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT).contains(hint)
    elapsed = pygame.Rect(config.ORIGIN, g.font.size(config.ELAPSED_TEXT.format("99분 59초")))
    elapsed.center = (config.ELAPSED_CENTER_X, config.ELAPSED_CENTER_Y)
    assert not hint.colliderect(elapsed)
    button = pygame.Rect(config.UPGRADE_BUTTON_X, config.UPGRADE_BUTTON_Y, config.BUTTON_WIDTH,
                         config.BUTTON_HEIGHT + P)
    assert not hint.colliderect(button)
