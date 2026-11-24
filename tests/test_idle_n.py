"""N단위 검수: 업그레이드 툴팁, 상태 배지 아이콘·툴팁, 업그레이드 장식 13종 (화면만, 규칙 그대로).

기준: docs/기획서.md 6절(툴팁, 무대 배경 4겹, 업그레이드 장식), 7절 #18·#21·#23,
jeja-spec N단위 항목.
"""

import math
import os
import re
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
import game as game_module  # noqa: E402
from button import sprite_size  # noqa: E402
from conftest import PROJECT_ROOT, press, reach_grade  # noqa: E402
from game import Game  # noqa: E402

P = config.PIXEL_SIZE
CELL = config.SCENE_CELL
IDS = list(config.UPGRADE_IDS)
DECOR = list(config.DECOR_IDS)
FAC = list(config.FACILITY_IDS)
PLACES = [config.PLACE_LAWN, config.PLACE_LECTURE, config.PLACE_LIBRARY,
          config.PLACE_CEREMONY, config.PLACE_LAB]
OUTDOOR = PLACES[:4]
MAXLV = {uid: config.UPGRADES_BY_ID[uid][config.UPGRADE_MAX_LEVEL] for uid in IDS}
PANEL = pygame.Rect(config.UPGRADE_PANEL_RECT)
PANEL_WITH_SHADOW = PANEL.union(PANEL.move(0, P))
STAGE_INNER = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH,
                          config.PANEL_HEIGHT).inflate(-2 * P, -2 * P)
TIRED, DEPRESSED = config.DEBUFF_TIRED, config.DEBUFF_DEPRESSED
FULL, GOOD = config.BUFF_FULL, config.CONDITION_GOOD


# ============================== 도우미 ==============================

@pytest.fixture
def g(no_events, no_auto):
    """이벤트·자동 행동을 끈 채 게임 중인 Game."""
    game = Game()
    press(game, pygame.K_RETURN)
    assert game.state == config.STATE_PLAYING
    yield game
    pygame.quit()


def set_level(game, uid, level):
    game.upgrades[uid] = level


def zero_levels():
    return tuple(0 for _ in DECOR)


def levels_with(**kw):
    return tuple(kw.get(uid, 0) for uid in DECOR)


def max_levels():
    return tuple(MAXLV[uid] for uid in DECOR)


def fmt_effect(uid, level):
    """기대 효과 글자: config 틀에 round(레벨 x 레벨당 효과, 6)."""
    per = config.UPGRADES_BY_ID[uid][config.UPGRADE_PER_LEVEL]
    return config.UPGRADE_LEVEL_EFFECTS[uid].format(round(level * per, 6))


def diff_rect(a, b):
    """두 같은 크기 Surface 에서 색이 다른 픽셀을 감싼 Rect 와 개수 (없으면 None, 0)."""
    w, h = a.get_size()
    ba = pygame.image.tobytes(a, "RGB")
    bb = pygame.image.tobytes(b, "RGB")
    row = w * 3
    xs, ys, count = [], [], 0
    for y in range(h):
        ra, rb = ba[y * row:(y + 1) * row], bb[y * row:(y + 1) * row]
        if ra == rb:
            continue
        for x in range(w):
            if ra[x * 3:x * 3 + 3] != rb[x * 3:x * 3 + 3]:
                xs.append(x)
                ys.append(y)
                count += 1
    if not count:
        return None, 0
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1), count


def scenery(game, place, levels, season="spring", shade=0, facilities=()):
    return game.make_scenery(place, season, facilities, shade, levels)


def record_calls(monkeypatch, obj, name):
    calls = []
    real = getattr(obj, name)

    def wrapped(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)
    monkeypatch.setattr(obj, name, wrapped)
    return calls


def record_texts(monkeypatch, call):
    made = []
    real = game_module.render_text

    def rec(font, text, *a, **k):
        made.append(text)
        return real(font, text, *a, **k)
    monkeypatch.setattr(game_module, "render_text", rec)
    call()
    monkeypatch.setattr(game_module, "render_text", real)
    return made


def row_center(game, index):
    return game.get_upgrade_row_rect(index).center


def open_panel(game):
    press(game, pygame.K_u)
    assert game.upgrade_panel_open


# ============================== 1. 업그레이드 효과·툴팁 글자 ==============================

@pytest.mark.parametrize("uid", IDS)
def test_effect_text_every_level_from_config(g, uid):
    for level in range(1, MAXLV[uid] + 1):
        text = g.get_upgrade_effect_text(uid, level)
        assert text == fmt_effect(uid, level)
        # 부동소수 찌꺼기(0.6000000000000001 등)가 없다
        assert not re.search(r"\d\.\d{3,}", text), text
        assert "e-" not in text and "None" not in text


def test_effect_text_spec_examples(g):
    assert g.get_upgrade_effect_text("reference_book", 2) == "공부 지식 +4"
    assert g.get_upgrade_effect_text("reference_book", 3) == "공부 지식 +6"
    assert g.get_upgrade_effect_text("health_care", 3) == "자연 감소 -30%"
    assert g.get_upgrade_effect_text("lucky_charm", 1) == "이벤트 확률 +5%p"
    assert g.get_upgrade_effect_text("lucky_charm", 3) == "이벤트 확률 +15%p"
    assert g.get_upgrade_effect_text("time_management", 3) == "자동 행동 간격 -0.6초"
    assert g.get_upgrade_effect_text("self_care", 5) == "1초마다 체력·멘탈 +1"
    assert g.get_upgrade_effect_text("menu", 5) == "든든함 지속 +30초"


@pytest.mark.parametrize("uid", IDS)
def test_effect_amount_matches_real_student_bonus(g, uid):
    """툴팁 숫자 = 실제 규칙이 쓰는 효과 크기(Student.get_upgrade_bonus)."""
    for level in range(1, MAXLV[uid] + 1):
        set_level(g, uid, level)
        bonus = g.student.get_upgrade_bonus(uid)
        per = config.UPGRADES_BY_ID[uid][config.UPGRADE_PER_LEVEL]
        assert round(level * per, 6) == pytest.approx(bonus)


def tooltip_levels(uid):
    mx = MAXLV[uid]
    return sorted({0, mx // 2 if mx > 1 else 0, mx - 1, mx} | ({1} if mx > 1 else set()))


@pytest.mark.parametrize("uid", IDS)
def test_tooltip_rows_every_upgrade_levels(g, uid):
    name = config.UPGRADES_BY_ID[uid][config.UPGRADE_NAME]
    mx = MAXLV[uid]
    g.money = 10 ** 12
    for level in tooltip_levels(uid):
        set_level(g, uid, level)
        rows = g.get_upgrade_tooltip_rows(uid)
        texts = [t for t, _ in rows]
        assert texts[0] == f"{name}  Lv {level}/{mx}"
        assert rows[0][1] == config.COLOR_TOOLTIP_TITLE
        if level == 0:
            assert texts[1] == "지금: 아직 없음"
        else:
            assert texts[1] == "지금: " + fmt_effect(uid, level)
        if level >= mx:
            assert texts[2] == "다음: 최고 레벨"
            assert texts[4] == "가격: MAX"
        else:
            assert texts[2] == "다음: " + fmt_effect(uid, level + 1)
            cost = math.floor(config.UPGRADES_BY_ID[uid][config.UPGRADE_BASE_COST]
                              * 2.0 ** level)
            assert texts[4] == f"가격: 연구비 {cost}"
        assert texts[3].startswith("무대: ")
        assert texts[3] == config.UPGRADE_DECOR_TEXTS[uid]
        assert len(rows) == 5            # 돈이 넉넉하면 경고 줄 없음
        assert "연구비가 모자라요" not in texts


def test_tooltip_spec_example_reference_book_lv2(g):
    set_level(g, "reference_book", 2)
    g.money = 0
    texts = [t for t, _ in g.get_upgrade_tooltip_rows("reference_book")]
    assert texts[:4] == ["참고서  Lv 2/5", "지금: 공부 지식 +4", "다음: 공부 지식 +6",
                         "무대: 책장이 생겨요 (책 = Lv)"]
    assert texts[4] == "가격: 연구비 1440"
    assert texts[5] == "연구비가 모자라요"


@pytest.mark.parametrize("uid", IDS)
def test_affordability_line_boundary(g, uid):
    """연구비 < 가격 이면 빨간 줄, 연구비 == 가격 이면 없음, MAX 면 없음."""
    set_level(g, uid, 0)
    cost = g.get_upgrade_cost(uid)
    g.money = cost - 1
    rows = g.get_upgrade_tooltip_rows(uid)
    assert rows[-1] == ("연구비가 모자라요", config.COLOR_TOOLTIP_WARN)
    assert config.COLOR_TOOLTIP_WARN[0] > 150 and config.COLOR_TOOLTIP_WARN[1] < 120  # 빨강 계열
    g.money = cost
    assert "연구비가 모자라요" not in [t for t, _ in g.get_upgrade_tooltip_rows(uid)]
    set_level(g, uid, MAXLV[uid])
    g.money = 0
    texts = [t for t, _ in g.get_upgrade_tooltip_rows(uid)]
    assert "연구비가 모자라요" not in texts and texts[-1] == "가격: MAX"


def test_decor_texts_cover_all_13(g):
    assert set(config.UPGRADE_DECOR_TEXTS) == set(IDS)
    assert set(config.UPGRADE_LEVEL_EFFECTS) == set(IDS)
    assert "책 = Lv" in config.UPGRADE_DECOR_TEXTS["reference_book"]


def test_tooltip_rows_do_not_change_rules(g):
    """툴팁 글자를 만들어도 연구비·레벨이 바뀌지 않는다."""
    g.money = 5000
    before = (g.money, dict(g.upgrades))
    for uid in IDS:
        g.get_upgrade_tooltip_rows(uid)
    assert (g.money, dict(g.upgrades)) == before


# ============================== 2. 툴팁은 마우스 올렸을 때만 ==============================

def test_cursor_alone_shows_no_tooltip(g, monkeypatch):
    open_panel(g)
    g.mouse_pos = None
    for _ in range(len(IDS) + 2):
        press(g, pygame.K_DOWN)
        assert g.get_hovered_upgrade_index() is None
        assert g.draw_upgrade_tooltip() is None
    calls = record_calls(monkeypatch, g, "draw_tooltip")
    g.draw()
    assert calls == []


def test_footer_effect_line_still_drawn(g, monkeypatch):
    open_panel(g)
    for index in (0, 5, 12):
        g.upgrade_cursor = index
        uid = IDS[index]
        effect = config.UPGRADES_BY_ID[uid][config.UPGRADE_EFFECT_TEXT]
        texts = record_texts(monkeypatch, g.draw_upgrade_panel)
        assert config.UPGRADE_FOOTER_TEXT.format(effect) in texts
        assert config.UPGRADE_FOOTER_TEXT.format(effect).startswith("효과: ")


@pytest.mark.parametrize("index", range(len(IDS)))
def test_hover_row_gives_index_and_tooltip(g, index):
    open_panel(g)
    g.mouse_pos = row_center(g, index)
    assert g.get_hovered_upgrade_index() == index
    rect = g.draw_upgrade_tooltip()
    assert rect is not None


def test_mouse_off_rows_no_tooltip(g):
    open_panel(g)
    first = g.get_upgrade_row_rect(0)
    gap_y = first.bottom          # 줄 사이 1픽셀 틈
    for pos in [(first.centerx, gap_y), (first.centerx, first.top - 1),
                (first.right, first.centery), (first.left - 1, first.centery),
                STAGE_INNER.center, (700, 500), (20, 130)]:
        g.mouse_pos = pos
        assert g.get_hovered_upgrade_index() is None, pos
        assert g.draw_upgrade_tooltip() is None, pos


def test_tooltip_follows_mouse_not_cursor(g):
    open_panel(g)
    g.upgrade_cursor = 0
    g.mouse_pos = row_center(g, 7)
    assert g.get_hovered_upgrade_index() == 7
    expect = g.get_tooltip_rect(g.get_upgrade_tooltip_rows(IDS[7]),
                                g.get_upgrade_row_rect(7).top)
    assert g.draw_upgrade_tooltip() == expect


def test_no_upgrade_tooltip_when_panel_closed(g):
    g.mouse_pos = row_center(g, 3)
    assert not g.upgrade_panel_open
    assert g.draw_upgrade_tooltip() is None


def test_mousemotion_event_sets_hover(g):
    open_panel(g)
    g.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=row_center(g, 2),
                                      rel=(0, 0), buttons=(0, 0, 0)))
    assert g.get_hovered_upgrade_index() == 2
    g.handle_event(pygame.event.Event(pygame.WINDOWLEAVE))
    assert g.get_hovered_upgrade_index() is None


def test_ending_screen_hover_tooltip(g, monkeypatch):
    g.end_game(config.ENDING_LEAVE)
    assert g.state == config.STATE_ENDING
    open_panel(g)
    g.mouse_pos = None
    calls = record_calls(monkeypatch, g, "draw_tooltip")
    g.draw()
    assert calls == []
    g.mouse_pos = row_center(g, 4)
    g.draw()
    assert len(calls) == 1
    rect = g.draw_upgrade_tooltip()
    assert rect.left >= 276


def test_event_dialog_hides_tooltip(g, monkeypatch):
    open_panel(g)
    g.mouse_pos = row_center(g, 1)
    g.start_event(config.CHOICE_EVENTS[0])
    assert g.state == config.STATE_EVENT
    calls = record_calls(monkeypatch, g, "draw_tooltip")
    g.draw()
    assert calls == []


def test_draw_order_tooltip_after_panel(g, monkeypatch):
    order = []
    for name in ("draw_playing", "draw_upgrade_panel", "draw_upgrade_tooltip"):
        real = getattr(g, name)

        def wrapped(*a, _n=name, _r=real, **k):
            order.append(_n)
            return _r(*a, **k)
        monkeypatch.setattr(g, name, wrapped)
    open_panel(g)
    g.mouse_pos = row_center(g, 0)
    g.draw()
    assert order == ["draw_playing", "draw_upgrade_panel", "draw_upgrade_tooltip"]


def test_hover_and_tooltip_do_not_buy(g):
    open_panel(g)
    g.money = 10 ** 6
    before = (g.money, dict(g.upgrades))
    for index in range(len(IDS)):
        g.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=row_center(g, index),
                                          rel=(0, 0), buttons=(0, 0, 0)))
        g.draw()
    assert (g.money, dict(g.upgrades)) == before


# ============================== 3. 툴팁 위치 ==============================

def check_box(rect):
    assert rect.left >= 276, rect
    assert rect.top >= 116, rect
    assert rect.bottom + P <= 460, rect          # 아래 그림자 1칸 포함
    assert rect.right <= 792, rect
    assert pygame.Rect(0, 0, 800, 600).contains(rect.union(rect.move(0, P)))
    assert not rect.union(rect.move(0, P)).colliderect(PANEL_WITH_SHADOW), rect


MONEYS = [0, 10 ** 12]


@pytest.mark.parametrize("money", MONEYS)
@pytest.mark.parametrize("level_kind", ["zero", "mid", "max"])
@pytest.mark.parametrize("index", range(len(IDS)))
def test_tooltip_placement_all_rows(g, index, money, level_kind):
    uid = IDS[index]
    level = {"zero": 0, "mid": MAXLV[uid] // 2, "max": MAXLV[uid]}[level_kind]
    set_level(g, uid, level)
    g.money = money
    open_panel(g)
    g.mouse_pos = row_center(g, index)
    rect = g.draw_upgrade_tooltip()
    check_box(rect)
    rows = g.get_upgrade_tooltip_rows(uid)
    # 모든 줄 글자가 상자 안(좌우 여백 포함)에 들어간다
    for text, _ in rows:
        assert g.small_font.size(text)[0] + 2 * config.TOOLTIP_PAD_X <= rect.width, text
    assert len(rows) * config.TOOLTIP_LINE_HEIGHT + 2 * config.TOOLTIP_PAD_Y <= rect.height
    # 그 줄 높이에 맞춘다(아래로 넘칠 때만 위로 밀어 올림)
    row_top = g.get_upgrade_row_rect(index).top
    if row_top + rect.height + P <= 460:
        assert rect.top == row_top
    else:
        assert rect.bottom + P == 460 or rect.top == 116


def test_tooltip_pixels_stay_in_box(g):
    """툴팁을 그려서 바뀐 픽셀은 상자(+그림자) 안에만 있다."""
    open_panel(g)
    g.money = 0
    for index in (0, 6, 12):
        g.mouse_pos = row_center(g, index)
        monkey_rect = None
        g.draw_playing()
        g.draw_upgrade_panel()
        before = g.screen.copy()
        monkey_rect = g.draw_upgrade_tooltip()
        after = g.screen.copy()
        box, count = diff_rect(before, after)
        assert count > 0
        assert monkey_rect.union(monkey_rect.move(0, P)).contains(box), (index, box)


def test_tooltip_rect_extreme_long_lines_stay_right_of_panel(g):
    """긴 줄이 와도 상자가 왼쪽 패널 쪽으로 밀려 들어가지 않는다(오른쪽 끝 792 고정 시)."""
    rows = [("가" * 30, config.COLOR_TOOLTIP_TEXT)]
    rect = g.get_tooltip_rect(rows, 200)
    if g.small_font.size(rows[0][0])[0] + 2 * config.TOOLTIP_PAD_X <= 792 - 276:
        check_box(rect)


@pytest.mark.parametrize("anchor", [0, 50, 116, 300, 440, 460, 600])
def test_tooltip_rect_clamped_vertically(g, anchor):
    rows = g.get_upgrade_tooltip_rows("menu")
    check_box(g.get_tooltip_rect(rows, anchor))


def test_tooltip_box_is_opaque_cream(g):
    open_panel(g)
    g.mouse_pos = row_center(g, 3)
    g.draw_playing()
    g.draw_upgrade_panel()
    rect = g.draw_upgrade_tooltip()
    # 외곽선 안쪽 오른쪽 아래 여백 부분은 크림색 그대로(아래 무대가 비치지 않음)
    x, y = rect.right - 2 * P - 1, rect.bottom - 2 * P - 1
    assert g.screen.get_at((x, y))[:3] == config.COLOR_TOOLTIP
    assert g.screen.get_alpha() is None


# ============================== 4. 상태 배지 툴팁 ==============================

def test_status_tip_texts_exact(g):
    assert g.get_status_tip_text(TIRED) == "피곤: 체력 30 미만 — 공부 지식 ×0.7"
    assert g.get_status_tip_text(DEPRESSED) == "우울: 멘탈 30 미만 — 버는 연구비 ×0.7"
    assert (g.get_status_tip_text(GOOD)
            == "컨디션 좋음: 휴식 위주, 체력·멘탈 70 이상 — 버는 연구비 ×1.5")   # B안
    g.student.elapsed = 100.0
    g.student.full_until = 112.0
    assert g.get_status_tip_text(FULL) == "든든함: 남은 시간 12초 — 체력 감소 ×0.5"


def test_status_tip_values_from_config(g):
    assert str(config.LOW_GAUGE_LIMIT) in g.get_status_tip_text(TIRED)
    assert f"×{config.TIRED_KNOWLEDGE_RATIO:g}" in g.get_status_tip_text(TIRED)
    assert f"×{config.DEPRESSED_MONEY_RATIO:g}" in g.get_status_tip_text(DEPRESSED)
    assert f"×{config.FULL_HEALTH_DECAY_RATIO:g}" in g.get_status_tip_text(FULL)
    bonus = config.POLICIES[config.POLICY_REST_FOCUS][config.POLICY_CONDITION_BONUS]
    assert f"×{round(1 + bonus, 6):g}" in g.get_status_tip_text(GOOD)
    assert str(config.CONDITION_GOOD_MIN) in g.get_status_tip_text(GOOD)


@pytest.mark.parametrize("left, shown", [(12.0, 12), (11.2, 12), (11.0001, 12), (11.0, 11),
                                         (0.4, 1), (0.0001, 1), (29.5, 30), (30.0, 30)])
def test_full_countdown_is_ceiling(g, left, shown):
    g.student.elapsed = 50.0
    g.student.full_until = 50.0 + left
    assert g.get_status_tip_text(FULL) == f"든든함: 남은 시간 {shown}초 — 체력 감소 ×0.5"


def test_full_countdown_after_real_feed(g):
    g.student.feed()
    dur = g.student.get_full_duration()
    assert g.get_status_tip_text(FULL).startswith(f"든든함: 남은 시간 {math.ceil(dur)}초")
    g.student.elapsed += 0.5
    assert f"남은 시간 {math.ceil(dur - 0.5)}초" in g.get_status_tip_text(FULL)


def set_all_debuffs(game):
    game.student.health = 20
    game.student.mental = 20
    game.student.full_until = game.student.elapsed + 12.0


def test_hovered_status_each_badge(g):
    set_all_debuffs(g)
    names = g.get_status_names()
    assert names == [TIRED, DEPRESSED, FULL]
    for index, name in enumerate(names):
        badge = g.student.get_badge_rect(index, config.STATUS_BADGE_Y)
        g.mouse_pos = badge.center
        assert g.get_hovered_status() == (index, name)
        rect = g.draw_status_tooltip()
        check_box(rect)
        assert rect.top == badge.top
        line = g.get_status_tip_text(name)
        assert g.small_font.size(line)[0] + 2 * config.TOOLTIP_PAD_X <= rect.width


def test_condition_good_badge_hover(g):
    g.set_policy(config.POLICY_REST_FOCUS)
    g.student.health = g.student.mental = 80
    names = g.get_status_names()
    assert names == [GOOD]
    g.mouse_pos = g.student.get_badge_rect(0, config.STATUS_BADGE_Y).center
    assert g.get_hovered_status() == (0, GOOD)
    check_box(g.draw_status_tooltip())


def test_status_tooltip_text_drawn(g, monkeypatch):
    set_all_debuffs(g)
    g.mouse_pos = g.student.get_badge_rect(2, config.STATUS_BADGE_Y).center
    texts = record_texts(monkeypatch, g.draw)
    assert "든든함: 남은 시간 12초 — 체력 감소 ×0.5" in texts


def test_status_tooltip_none_cases(g, monkeypatch):
    set_all_debuffs(g)
    badge = g.student.get_badge_rect(0, config.STATUS_BADGE_Y)
    # 배지 밖
    g.mouse_pos = (badge.right + 2, badge.centery)
    assert g.get_hovered_status() is None
    # 없는 배지 자리(4번째 칸)
    g.mouse_pos = g.student.get_badge_rect(3, config.STATUS_BADGE_Y).center
    assert g.get_hovered_status() is None
    # 패널 열림
    g.mouse_pos = badge.center
    open_panel(g)
    assert g.get_hovered_status() is None
    assert g.draw_status_tooltip() is None
    press(g, pygame.K_u)
    assert g.get_hovered_status() == (0, TIRED)
    # 마우스 없음
    g.mouse_pos = None
    assert g.get_hovered_status() is None
    # 엔딩 화면
    g.mouse_pos = badge.center
    g.end_game(config.ENDING_LEAVE)
    assert g.get_hovered_status() is None


def test_status_tooltip_drawn_only_when_hovered(g, monkeypatch):
    set_all_debuffs(g)
    calls = record_calls(monkeypatch, g, "draw_tooltip")
    g.mouse_pos = None
    g.draw()
    assert calls == []
    g.mouse_pos = g.student.get_badge_rect(1, config.STATUS_BADGE_Y).center
    g.draw()
    assert len(calls) == 1


def test_no_statuses_no_tooltip(g):
    g.student.health = g.student.mental = 60
    assert g.get_status_names() == []
    g.mouse_pos = g.student.get_badge_rect(0, config.STATUS_BADGE_Y).center
    assert g.get_hovered_status() is None


# ============================== 5. 상태 아이콘 ==============================

@pytest.mark.parametrize("name", [TIRED, DEPRESSED, FULL, GOOD])
def test_status_icon_size_16x12(name):
    assert sprite_size(config.STATUS_ICONS[name], config.STATUS_ICON_CELL) == (16, 12)
    for row in config.STATUS_ICONS[name]:
        for ch in row:
            assert ch == "." or ch in config.STATUS_ICON_COLORS


def test_status_icons_distinct():
    grids = [tuple(config.STATUS_ICONS[n]) for n in (TIRED, DEPRESSED, FULL, GOOD)]
    assert len(set(grids)) == 4


@pytest.mark.parametrize("name", [TIRED, DEPRESSED, FULL, GOOD])
def test_status_badge_icon_pixels_and_name_fit(g, name):
    surf = pygame.Surface((300, 200))
    surf.fill((1, 2, 3))
    g.student.draw_status_badges(surf, g.small_font, [name])
    box = g.student.get_badge_rect(0, config.STATUS_BADGE_Y)
    inner = box.inflate(-2 * P, -2 * P)
    icon = config.STATUS_ICONS[name]
    cell = config.STATUS_ICON_CELL
    left = inner.left + config.STATUS_ICON_PAD
    top = inner.centery - 12 // 2
    for r, row in enumerate(icon):
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            assert surf.get_at((left + c * cell, top + r * cell))[:3] == \
                config.STATUS_ICON_COLORS[ch], (name, r, c)
    # 아이콘이 배지 안쪽에 들어가고, 이름이 아이콘 오른쪽에서 배지 안에 다 들어간다
    assert inner.contains(pygame.Rect(left, top, 16, 12))
    text_left = left + 16 + config.STATUS_ICON_GAP
    assert text_left + g.small_font.size(name)[0] <= inner.right, name


def test_badge_layout_unchanged(g):
    """배지 크기는 예전과 같은 2열, 사이 간격은 (특성 8종) 8 -> 4."""
    r0 = g.student.get_badge_rect(0, 128)
    r1 = g.student.get_badge_rect(1, 128)
    r2 = g.student.get_badge_rect(2, 128)
    assert tuple(r0) == (24, 128, 112, 24)
    assert tuple(r1) == (140, 128, 112, 24)
    assert tuple(r2) == (24, 156, 112, 24)


# ============================== 6. 장식 조각·레벨 ==============================

def test_decor_ids_are_ten_non_facilities():
    assert len(DECOR) == 10
    assert set(DECOR) | set(FAC) == set(IDS)
    assert not set(DECOR) & set(FAC)


def test_decor_levels_tuple(g):
    assert g.get_decor_levels() == zero_levels()
    set_level(g, "reference_book", 3)
    set_level(g, "self_care", 5)
    assert g.get_decor_levels() == levels_with(reference_book=3, self_care=5)


@pytest.mark.parametrize("uid", DECOR)
def test_no_pieces_at_level_zero(g, uid):
    assert g.get_decor_pieces(uid, 0) == []


def piece_counts(g, uid):
    return [len(g.get_decor_pieces(uid, lv)) for lv in range(0, MAXLV[uid] + 1)]


def test_bookshelf_books_equal_level(g):
    for lv in range(1, 6):
        pieces = g.get_decor_pieces("reference_book", lv)
        books = [p for p in pieces if p[0].startswith("decor_book")]
        assert len(books) == lv
        assert any(p[0] == "decor_shelf" for p in pieces)


def test_charm_rack_charms_equal_level(g):
    for lv in range(1, MAXLV["lucky_charm"] + 1):
        pieces = g.get_decor_pieces("lucky_charm", lv)
        charms = [p for p in pieces if p[0].startswith("decor_charm_") and p[0] != "decor_charm_rack"]
        assert len(charms) == lv
        assert any(p[0] == "decor_charm_rack" for p in pieces)


@pytest.mark.parametrize("uid", [u for u in DECOR if MAXLV[u] == 5
                                 and u != "reference_book"])
def test_more_pieces_at_lv3_and_lv5(g, uid):
    c = piece_counts(g, uid)
    assert c[1] >= 1
    assert c[1] == c[2] < c[3] == c[4] < c[5], (uid, c)


def test_scholarship_trophy_lv1(g):
    assert piece_counts(g, "scholarship") == [0, 1]


def test_specific_level_pieces(g):
    """기획서 표: Lv5 주먹밥·쿠션 3개·종·비타민 3병·케틀벨·꽃·물병, Lv3 2단·추·잎·말아 둔 매트."""
    names = lambda uid, lv: [p[0] for p in g.get_decor_pieces(uid, lv)]  # noqa: E731
    assert "decor_riceball" in names("menu", 5) and "decor_riceball" not in names("menu", 4)
    assert len([n for n in names("bed", 5) if n.startswith("decor_cushion")]) == 3
    assert "decor_pendulum" in names("time_management", 3)
    assert "decor_clock_bells" in names("time_management", 5)
    assert len([n for n in names("health_care", 5) if n.startswith("decor_vitamin")]) == 3
    assert names("health_max", 3).count("decor_dumbbell") == 2
    assert "decor_kettlebell" in names("health_max", 5)
    assert "decor_leaves" in names("mental_max", 3) and "decor_bloom" in names("mental_max", 5)
    assert "decor_sprout" in names("mental_max", 1) and "decor_pot" in names("mental_max", 1)
    assert "decor_mat_roll" in names("self_care", 3) and "decor_water" in names("self_care", 5)


# ============================== 7. 장식은 가졌을 때만 보인다 (픽셀) ==============================

@pytest.mark.parametrize("place", PLACES)
@pytest.mark.parametrize("uid", DECOR)
def test_decor_pixels_only_when_owned(g, place, uid):
    base = scenery(g, place, zero_levels())
    rects = g.get_decor_rects(place, levels_with(**{uid: 1}))
    assert set(rects) == {uid}
    prev = base
    for lv in range(1, MAXLV[uid] + 1):
        shot = scenery(g, place, levels_with(**{uid: lv}))
        box, count = diff_rect(base, shot)
        assert count > 0, (place, uid, lv)
        rect = g.get_decor_rects(place, levels_with(**{uid: lv}))[uid]
        assert rect.contains(box), (place, uid, lv, box, rect)
        # 조각이 늘어나는 레벨이면 앞 레벨 그림과 달라진다(책·부적·추 등)
        changed = diff_rect(prev, shot)[1]
        if len(g.get_decor_pieces(uid, lv)) > len(g.get_decor_pieces(uid, lv - 1)):
            assert changed > 0, (place, uid, lv)
        else:
            assert changed == 0, (place, uid, lv)
        prev = shot


@pytest.mark.parametrize("place", PLACES)
def test_zero_levels_same_as_no_decor(g, place):
    a = scenery(g, place, zero_levels())
    b = g.make_scenery(place, "spring", (), 0)
    assert diff_rect(a, b)[1] == 0


@pytest.mark.parametrize("uid", IDS)
def test_full_frame_shows_each_upgrade_only_when_owned(g, monkeypatch, uid):
    """화면 전체: 0레벨 vs 1레벨 차이가 무대 안쪽에 있다(13종 모두 보임).

    체력 증진·멘탈 관리는 최댓값이 바뀌어 상태 패널 글자("80/110")도 달라지므로(규칙 효과),
    무대 밖 차이는 상태 패널 안에서만 허용한다.
    """
    monkeypatch.setattr(g, "get_student_lift", lambda: 0)
    g.student.elapsed = 1.0
    g.draw()
    a = g.screen.copy()
    set_level(g, uid, 1)
    g.draw()
    b = g.screen.copy()
    stage_diff = diff_rect(a.subsurface(STAGE_INNER).copy(), b.subsurface(STAGE_INNER).copy())[1]
    assert stage_diff > 0, uid
    status_panel = pygame.Rect(config.STATUS_PANEL_X, config.PANEL_Y,
                               config.STATUS_PANEL_WIDTH, config.PANEL_HEIGHT + P)
    for clip in (STAGE_INNER, status_panel):
        a.fill((0, 0, 0), clip)
        b.fill((0, 0, 0), clip)
    assert diff_rect(a, b)[1] == 0, uid


@pytest.mark.parametrize("place", OUTDOOR)
def test_decor_receives_evening_shade(g, place):
    lv = max_levels()
    day = scenery(g, place, lv, shade=0)
    night = scenery(g, place, lv, shade=2)
    day0 = scenery(g, place, zero_levels(), shade=0)
    for uid, rect in g.get_decor_rects(place, lv).items():
        box, _ = diff_rect(day0, day)
        # 장식 자리 안 픽셀이 그늘에서 달라진다
        sub_day = day.subsurface(rect).copy()
        sub_night = night.subsurface(rect).copy()
        assert diff_rect(sub_day, sub_night)[1] > 0, uid


# ============================== 8. 장식 자리: 겹침 없음 ==============================

def sprite_rect(name, col, row, cell=CELL):
    w, h = sprite_size(config.SCENE_SPRITES[name][0], cell)
    return pygame.Rect(col * cell, row * cell, w, h)


def student_box(g):
    """4학년 + 외형 5종 + 최고 점프·숨쉬기 높이에서 제자가 칠하는 픽셀 상자(무대 안쪽 좌표)."""
    s = g.student
    reach_grade(s, 4)
    s.looks = list(config.LOOK_IDS)
    s.health = 10            # 다크서클
    box = None
    max_lift = config.JUMP_HEIGHT + config.BREATH_HEIGHT
    for lift in range(0, max_lift + 1, P):
        surf = pygame.Surface((800, 600))
        surf.fill((255, 0, 255))
        surf.set_colorkey((255, 0, 255))
        s.draw(surf, lift)
        r = surf.get_bounding_rect()
        box = r if box is None else box.union(r)
    return box.move(-STAGE_INNER.left, -STAGE_INNER.top)


def prop_boxes(g):
    out = []
    for name, surf in g.prop_surfaces.items():
        r = surf.get_bounding_rect()
        out.append((name, r.move(config.PROP_X, config.PROP_BOTTOM - surf.get_height())))
    return out


def obstacle_parts(place):
    """벤치·졸업식 의자(바깥), 연구실은 책장·화이트보드·화분 같은 가구."""
    out = []
    for part in config.PLACE_FRONT[place] + config.PLACE_BACK[place]:
        if part[0] == config.PART_SPRITE and part[1] in ("bench", "chair", "plant", "lamp"):
            out.append((part[1], sprite_rect(part[1], part[2], part[3])))
    if place == config.PLACE_LAB:
        out.append(("lab_shelf", pygame.Rect(4 * CELL, 12 * CELL, 24 * CELL, 50 * CELL)))
        out.append(("lab_board", pygame.Rect(32 * CELL, 10 * CELL, 32 * CELL, 21 * CELL)))
        out.append(("lab_window", pygame.Rect(66 * CELL, 6 * CELL, 48 * CELL, 34 * CELL)))
    return out


def facility_boxes(place):
    out = []
    for uid in FAC:
        x, bottom, cell = config.FACILITY_SLOTS[place][uid]
        w, h = sprite_size(config.SCENE_SPRITES[config.FACILITY_SPRITES[uid]][0], cell)
        out.append((uid, pygame.Rect(x, bottom - h, w, h)))
    return out


def notice_zones():
    """알림·팝업이 뜨는 무대 위쪽 자리(화면 좌표 -> 무대 안쪽 좌표)."""
    icon_w = sprite_size(config.NOTICE_GOOD_ICON, P)[0]
    notice_w = 2 * P + config.EVENT_NOTICE_PAD + icon_w + config.EVENT_NOTICE_ICON_GAP \
        + config.EVENT_NOTICE_TEXT_MAX_WIDTH + config.EVENT_NOTICE_PAD_RIGHT
    zones = [
        ("event_notice", pygame.Rect(config.EVENT_NOTICE_X, config.PANEL_Y, notice_w,
                                     config.EVENT_NOTICE_Y + config.EVENT_NOTICE_HEIGHT + P
                                     - config.PANEL_Y)),
        ("event_popups", pygame.Rect(STAGE_INNER.left, STAGE_INNER.top, 130, 160)),
        ("promotion", pygame.Rect(config.PROMOTION_NOTICE_RIGHT - 200, config.PANEL_Y, 200,
                                  config.EVENT_NOTICE_Y + config.EVENT_NOTICE_HEIGHT + P
                                  - config.PANEL_Y)),
    ]
    return [(n, r.move(-STAGE_INNER.left, -STAGE_INNER.top)) for n, r in zones]


@pytest.mark.parametrize("place", PLACES)
def test_decor_rects_inside_stage_and_disjoint(g, place):
    rects = g.get_decor_rects(place, max_levels())
    assert set(rects) == set(DECOR)
    stage = pygame.Rect(0, 0, STAGE_INNER.width, STAGE_INNER.height)
    items = list(rects.items())
    for uid, r in items:
        assert stage.contains(r), (place, uid, r)
    for i, (a, ra) in enumerate(items):
        for b, rb in items[i + 1:]:
            assert not ra.colliderect(rb), (place, a, b)


@pytest.mark.parametrize("place", PLACES)
def test_decor_not_on_student(g, place):
    box = student_box(g)
    for uid, r in g.get_decor_rects(place, max_levels()).items():
        assert not r.colliderect(box), (place, uid, r, box)


@pytest.mark.parametrize("place", PLACES)
def test_decor_not_on_action_props(g, place):
    for uid, r in g.get_decor_rects(place, max_levels()).items():
        for name, pr in prop_boxes(g):
            assert not r.colliderect(pr), (place, uid, name)


@pytest.mark.parametrize("place", PLACES)
def test_decor_not_on_benches_chairs_furniture(g, place):
    for uid, r in g.get_decor_rects(place, max_levels()).items():
        for name, orc in obstacle_parts(place):
            assert not r.colliderect(orc), (place, uid, name, r, orc)


@pytest.mark.parametrize("place", PLACES)
def test_decor_not_on_facilities(g, place):
    for uid, r in g.get_decor_rects(place, max_levels()).items():
        for fid, fr in facility_boxes(place):
            assert not r.colliderect(fr), (place, uid, fid)


@pytest.mark.parametrize("place", PLACES)
def test_decor_not_in_notice_popup_area(g, place):
    for uid, r in g.get_decor_rects(place, max_levels()).items():
        for name, zr in notice_zones():
            assert not r.colliderect(zr), (place, uid, name)
        if place in OUTDOOR:
            assert r.top >= config.GROUND_ROW * CELL, (place, uid)


@pytest.mark.parametrize("place", PLACES)
@pytest.mark.parametrize("lv_kind", ["one", "three", "max"])
def test_decor_rects_every_level_subset_of_max(g, place, lv_kind):
    """레벨이 낮을 때의 상자는 최고 레벨 상자 안(그래서 최고 레벨 검사로 모든 레벨이 안전)."""
    lv = {"one": levels_with(**{u: 1 for u in DECOR}),
          "three": tuple(min(3, MAXLV[u]) for u in DECOR), "max": max_levels()}[lv_kind]
    full = g.get_decor_rects(place, max_levels())
    for uid, r in g.get_decor_rects(place, lv).items():
        assert full[uid].contains(r)


def test_lab_has_its_own_layout():
    out = config.DECOR_SLOTS[config.PLACE_LAWN]
    lab = config.DECOR_SLOTS[config.PLACE_LAB]
    assert out != lab
    for p in OUTDOOR:
        assert config.DECOR_SLOTS[p] == out
    assert set(lab) == set(DECOR) and set(out) == set(DECOR)


def test_lab_wall_items_below_window_and_floor_items_on_floor(g):
    rects = g.get_decor_rects(config.PLACE_LAB, max_levels())
    window_bottom = 40 * CELL      # 창턱 아래 끝
    floor_top = 62 * CELL
    for uid, r in rects.items():
        assert r.top >= window_bottom, uid
        if uid not in ("time_management", "scholarship"):
            assert r.bottom > floor_top, uid


@pytest.mark.parametrize("place", PLACES)
def test_drawn_decor_pixels_not_under_student_on_screen(g, monkeypatch, place):
    """실제 그린 화면에서도: 장식을 모두 최고로 산 뒤 바뀐 픽셀이 제자 상자와 겹치지 않는다."""
    lv = max_levels()
    box = student_box(g)
    a = scenery(g, place, zero_levels(), facilities=tuple(FAC))
    b = scenery(g, place, lv, facilities=tuple(FAC))
    for uid, r in g.get_decor_rects(place, lv).items():
        sub_a, sub_b = a.subsurface(r).copy(), b.subsurface(r).copy()
        assert diff_rect(sub_a, sub_b)[1] > 0, (place, uid)   # 시설 앞에서도 보임
    whole, _ = diff_rect(a, b)
    assert whole is not None
    # 바뀐 픽셀 상자들은 모두 장식 상자 안
    union = None
    for r in g.get_decor_rects(place, lv).values():
        union = r if union is None else union.union(r)
    assert union.contains(whole)


# ============================== 9. 캐시 ==============================

def test_scenery_key_has_decor_levels(g):
    set_level(g, "bed", 2)
    g.draw()
    assert len(g.scenery_key) == 5
    assert g.scenery_key[4] == g.get_decor_levels()


def test_cache_rebuild_only_on_purchase(g, monkeypatch):
    calls = record_calls(monkeypatch, g, "make_scenery")
    g.student.elapsed = 1.0
    g.draw()
    assert len(calls) == 1
    for _ in range(20):
        g.draw()
    assert len(calls) == 1
    # 패널 열기·마우스 올리기·↑↓ 는 다시 그리지 않는다
    open_panel(g)
    for index in range(len(IDS)):
        g.mouse_pos = row_center(g, index)
        press(g, pygame.K_DOWN)
        g.draw()
    assert len(calls) == 1
    # 13종 각각 살 때마다 딱 한 번
    g.money = 10 ** 9
    for index, uid in enumerate(IDS):
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                          pos=row_center(g, index)))
        assert g.upgrades[uid] == 1
        n = len(calls)
        g.draw()
        g.draw()
        assert len(calls) == n + 1, uid
        assert calls[-1][4] == g.get_decor_levels()
    # 살 수 없는 클릭(돈 없음)은 다시 그리지 않는다
    g.money = 0
    n = len(calls)
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                      pos=row_center(g, 0)))
    g.draw()
    assert len(calls) == n


def test_status_hover_does_not_rebuild(g, monkeypatch):
    set_all_debuffs(g)
    g.draw()
    calls = record_calls(monkeypatch, g, "make_scenery")
    for index in range(3):
        g.mouse_pos = g.student.get_badge_rect(index, config.STATUS_BADGE_Y).center
        g.draw()
    assert calls == []


def test_decor_not_drawn_per_frame(g, monkeypatch):
    for uid in DECOR:
        set_level(g, uid, MAXLV[uid])
    g.draw()
    calls = record_calls(monkeypatch, g, "draw_decorations")
    for _ in range(10):
        g.draw()
    assert calls == []


# ============================== 10. 반투명 없음 ==============================

def test_no_alpha_in_code():
    for fname in ("game.py", "student.py", "button.py"):
        with open(os.path.join(PROJECT_ROOT, fname), encoding="utf-8") as f:
            code = f.read()
        for word in ("set_alpha", "SRCALPHA", "BLEND_", "convert_alpha"):
            assert word not in code, (fname, word)


def test_scenery_with_decor_uses_colorkey_not_alpha(g):
    s = scenery(g, config.PLACE_LAWN, max_levels())
    assert s.get_alpha() is None
    assert not (s.get_flags() & pygame.SRCALPHA)
    assert s.get_colorkey() is not None


# ============================== 11. 속도 ==============================

def best_avg_ms(g, frames=120, runs=3):
    """update+draw 평균(ms)의 best-of-runs."""
    best = None
    for _ in range(runs):
        start = time.perf_counter()
        for _ in range(frames):
            g.update(1 / 60)
            g.draw()
        avg = (time.perf_counter() - start) / frames * 1000
        best = avg if best is None else min(best, avg)
    return best


@pytest.fixture
def maxed(g, monkeypatch):
    monkeypatch.setattr(config, "HEALTH_DECAY_PER_SEC", 0)
    monkeypatch.setattr(config, "MENTAL_DECAY_PER_SEC", 0)
    monkeypatch.setattr(config, "MENTAL_DECAY_PER_SEC_EXAM", 0)
    for uid in IDS:
        set_level(g, uid, MAXLV[uid])
    reach_grade(g.student, 4)
    g.student.looks = list(config.LOOK_IDS)
    g.last_action = config.ACTION_STUDY
    g.money = 0
    return g


def test_perf_panel_open_with_tooltip(maxed):
    g = maxed
    open_panel(g)
    g.mouse_pos = row_center(g, 6)
    g.draw()
    ms = best_avg_ms(g)
    assert ms < 6.0, ms   # 계약은 3ms, 측정 ~1.8ms. 전체 실행 부하를 감안한 넉넉한 기준


def test_perf_status_tooltip(maxed):
    g = maxed
    set_all_debuffs(g)
    g.mouse_pos = g.student.get_badge_rect(0, config.STATUS_BADGE_Y).center
    g.draw()
    ms = best_avg_ms(g)
    assert ms < 6.0, ms   # 계약은 3ms, 측정 ~1.8ms. 전체 실행 부하를 감안한 넉넉한 기준


def test_perf_ending_with_tooltip(maxed):
    g = maxed
    g.end_game(config.ENDING_LEAVE)
    open_panel(g)
    g.mouse_pos = row_center(g, 12)
    g.draw()
    ms = best_avg_ms(g)
    assert ms < 6.0, ms   # 계약은 3ms, 측정 ~1.8ms. 전체 실행 부하를 감안한 넉넉한 기준
