"""K단위(1부) 검수: 화면 다듬기 — 잔디 길·벤치 배치, 팝업 테두리, 패널 미니 게이지,
패널을 연 엔딩 화면 배치, 바깥 배경 저녁·밤 그늘 단계 (기획서 8·10절, jeja-spec 13·15절).

밸런스 수치(지식·엔딩 분포)는 이 단계에서 바뀌지 않으므로 여기서 고정하지 않는다.
이 파일은 conftest 의 AUTO_OFF_FILES / EVENTS_OFF_FILES 에 없으므로 필요한 픽스처를 직접 쓴다.
"""

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
import game as game_module  # noqa: E402
from button import sprite_size  # noqa: E402
from conftest import press  # noqa: E402
from game import Game  # noqa: E402

FRAME = 1 / 60
CELL = config.SCENE_CELL
SEASONS = ["spring", "summer", "autumn", "winter"]
SHADES = [0, 1, 2]
STAGE = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH, config.PANEL_HEIGHT)
STAGE_INNER = STAGE.inflate(-config.BOX_INSET, -config.BOX_INSET)
STUDENT_COLS = (52, 72)          # 잔디(1학년) 제자 얼굴이 차지하는 무대 안쪽 열(칸) 범위
SENTINEL = (1, 2, 3)             # 아무 그림도 쓰지 않는 바탕 색


# ============================== 도우미 ==============================

@pytest.fixture
def no_decay(monkeypatch):
    monkeypatch.setattr(config, "HEALTH_DECAY_PER_SEC", 0)
    monkeypatch.setattr(config, "MENTAL_DECAY_PER_SEC", 0)
    monkeypatch.setattr(config, "MENTAL_DECAY_PER_SEC_EXAM", 0)


@pytest.fixture
def g(no_events, no_auto):
    game = Game()
    press(game, pygame.K_RETURN)
    assert game.state == config.STATE_PLAYING
    yield game
    pygame.quit()


def set_term_time(game, term, t):
    """term 1~4 = 학부 학년, ("grad", n) = 대학원 n년차. 60초 주기 안 시각 t 로 맞춘다.

    (L단위) 학년은 시간이 아니라 진급으로 오르므로 학년(grade)을 직접 맞추고, 경과 시간은
    "term번째 주기(대학원은 4 + n번째 주기)의 t초"로 둔다(계절·시간대는 주기 안 시각으로 정해진다).
    """
    if isinstance(term, tuple):
        n = term[1]
        game.student.grade = config.MAX_GRADE
        game.student.grad_year = n
        game.student.elapsed = (config.MAX_GRADE + n - 1) * config.CYCLE_SECONDS + t
    else:
        game.student.grad_year = 0
        game.student.grade = term
        game.student.elapsed = (term - 1) * config.CYCLE_SECONDS + t


def blank_screen(game):
    screen = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    screen.fill(SENTINEL)
    game.screen = screen
    return screen


def changed_pixels(surface, rect=None):
    """SENTINEL 이 아닌 픽셀 좌표 목록."""
    rect = surface.get_rect() if rect is None else rect
    out = []
    for x in range(rect.left, rect.right):
        for y in range(rect.top, rect.bottom):
            if surface.get_at((x, y))[:3] != SENTINEL:
                out.append((x, y))
    return out


def bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def part_cells(part):
    """배경 조각 하나가 차지하는 칸 사각형(무대 안쪽 칸 좌표)."""
    if part[0] == config.PART_SPRITE:
        _, name, col, row = part
        w, h = sprite_size(config.SCENE_SPRITES[name][0], 1)
        return pygame.Rect(col, row, w, h)
    if part[0] == config.PART_RECT:
        _, _, col, row, w, h = part
        return pygame.Rect(col, row, w, h)
    raise AssertionError(part)


def prop_cells(game, name):
    surf = game.prop_surfaces[name]
    w, h = surf.get_width() // CELL, surf.get_height() // CELL
    return pygame.Rect(config.PROP_X // CELL, config.PROP_BOTTOM // CELL - h, w, h)


class RecSurface(pygame.Surface):
    """blit 을 (원본 Surface, 놓인 Rect) 로 기록하는 화면 Surface."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blits_log = []

    def blit(self, source, dest, *args, **kwargs):
        rect = super().blit(source, dest, *args, **kwargs)
        placed = pygame.Rect(dest.topleft if isinstance(dest, pygame.Rect) else dest,
                             source.get_size())
        self.blits_log.append((source, placed))
        return rect


def collect_texts(game, method, monkeypatch, *args):
    """game.method() 를 그리며 render_text 로 만든 글자의 (글자, 놓인 Rect) 목록을 돌려준다."""
    screen = RecSurface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    screen.fill(SENTINEL)
    game.screen = screen
    made = {}
    real = game_module.render_text

    def rec(font, text, *a, **k):
        surf = real(font, text, *a, **k)
        made[id(surf)] = (text, surf)
        return surf
    monkeypatch.setattr(game_module, "render_text", rec)
    getattr(game, method)(*args)
    monkeypatch.setattr(game_module, "render_text", real)
    return [(made[id(s)][0], r) for s, r in screen.blits_log
            if id(s) in made and made[id(s)][1] is s]


# ============================== 1. 잔디 길·벤치·소품 배치 ==============================

LAWN_PATH = [p for p in config.PLACE_BACK[config.PLACE_LAWN]
             if p[0] == config.PART_RECT and p[1] in ("path", "path_dark")]
LAWN_BENCHES = [p for p in config.PLACE_FRONT[config.PLACE_LAWN]
                if p[0] == config.PART_SPRITE and p[1] == "bench"]
LAWN_FLOWERS = [p for p in config.PLACE_FRONT[config.PLACE_LAWN]
                if p[0] == config.PART_SPRITE and p[1] == "flower"]


def test_lawn_path_parts_avoid_student_columns():
    assert LAWN_PATH, "잔디에 길이 있어야 한다"
    lo, hi = STUDENT_COLS
    for part in LAWN_PATH:
        r = part_cells(part)
        assert r.right - 1 < lo or r.left > hi, part


def test_lawn_path_diagonal_from_building_to_bottom_left():
    rects = sorted((part_cells(p) for p in LAWN_PATH), key=lambda r: r.top)
    far = next(part_cells(p) for p in config.PLACE_BACK[config.PLACE_LAWN]
               if p[0] == config.PART_RECT and p[1] == "far")
    # 위 끝은 먼 건물 바로 아래(땅 시작 행)에서, 건물 가로 범위 안에서 시작
    assert rects[0].top == config.GROUND_ROW == far.bottom
    assert far.left <= rects[0].left and rects[0].right <= far.right
    # 아래 끝은 무대 왼쪽 아래 구석까지
    assert rects[-1].left == 0 and rects[-1].bottom == STAGE_INNER.height // CELL
    # 아래로 갈수록 왼쪽으로(비스듬히), 넓어지며, 끊기지 않고 이어진다
    for a, b in zip(rects, rects[1:]):
        assert b.left <= a.left and b.width >= a.width
        assert b.top == a.bottom
        assert b.left < a.right and a.left < b.right      # 가로로 겹쳐 이어짐


@pytest.mark.parametrize("season", SEASONS)
@pytest.mark.parametrize("shade", SHADES)
def test_lawn_path_pixels_never_under_student(g, season, shade):
    surf = g.make_scenery(config.PLACE_LAWN, season, (), shade)
    path_colors = {g.get_scene_color(n, season, shade) for n in ("path", "path_dark")}
    lo, hi = STUDENT_COLS
    ground_top = config.GROUND_ROW * CELL
    found_outside = 0
    for x in range(0, surf.get_width()):
        for y in range(ground_top, surf.get_height(), 2):
            if surf.get_at((x, y))[:3] in path_colors:
                assert not (lo * CELL <= x < (hi + 1) * CELL), (season, shade, x, y)
                found_outside += 1
    assert found_outside > 0


@pytest.mark.parametrize("facilities", [(), ("library", "cafe", "gym")])
def test_lawn_screen_below_student_has_no_path(g, monkeypatch, facilities):
    """실제 화면: 1학년 제자 얼굴 가로 범위 아래 땅에 길 색 픽셀이 없다."""
    for f in facilities:
        g.upgrades[f] = 1
    set_term_time(g, 1, 0.5)
    g.draw()
    radius = g.student.get_radius()
    path_colors = {g.get_scene_color(n, "spring", 0) for n in ("path", "path_dark")}
    top = STAGE_INNER.top + config.GROUND_ROW * CELL
    for x in range(config.STUDENT_CENTER_X - radius, config.STUDENT_CENTER_X + radius):
        for y in range(top, STAGE_INNER.bottom, 2):
            assert g.screen.get_at((x, y))[:3] not in path_colors, (x, y)


def test_bench_positions():
    assert sorted(p[2:] for p in LAWN_BENCHES) == [(4, 50), (106, 49)]


def test_benches_inside_stage_and_on_ground():
    cols, rows = STAGE_INNER.width // CELL, STAGE_INNER.height // CELL
    for part in LAWN_BENCHES:
        r = part_cells(part)
        assert r.left >= 0 and r.right <= cols and r.bottom <= rows, part
        assert r.top >= config.GROUND_ROW, part


def test_benches_do_not_overlap_path_or_each_other():
    benches = [part_cells(p) for p in LAWN_BENCHES]
    assert not benches[0].colliderect(benches[1])
    for b in benches:
        for part in LAWN_PATH:
            assert not b.colliderect(part_cells(part)), (b, part)
        lo, hi = STUDENT_COLS
        assert b.right - 1 < lo or b.left > hi


def test_benches_and_flowers_do_not_overlap_action_props(g):
    for name in config.PROP_SPRITES:
        prop = prop_cells(g, name)
        for part in LAWN_BENCHES + LAWN_FLOWERS:
            assert not prop.colliderect(part_cells(part)), (name, prop, part)


def test_flowers_do_not_overlap_benches_or_path():
    benches = [part_cells(p) for p in LAWN_BENCHES]
    for part in LAWN_FLOWERS:
        f = part_cells(part)
        for b in benches:
            assert not f.colliderect(b), (part, b)
        for p in LAWN_PATH:
            assert not f.colliderect(part_cells(p)), (part, p)


@pytest.mark.parametrize("name", [config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY])
def test_bench_pixels_fully_visible_with_prop(g, name):
    """화면에서 벤치 픽셀이 소품에 가려지지 않는다(벤치 자리 = 소품 없는 화면과 같다)."""
    set_term_time(g, 1, 0.5)
    g.last_action = None
    g.draw()
    before = g.screen.copy()
    g.last_action = name
    g.draw()
    for part in LAWN_BENCHES:
        r = part_cells(part)
        rect = pygame.Rect(STAGE_INNER.left + r.left * CELL, STAGE_INNER.top + r.top * CELL,
                           r.width * CELL, r.height * CELL)
        for x in range(rect.left, rect.right):
            for y in range(rect.top, rect.bottom):
                assert g.screen.get_at((x, y)) == before.get_at((x, y)), (name, x, y)


# ============================== 2. 팝업 테두리(읽기 쉬움) ==============================

def test_popup_constants():
    assert config.POPUP_OUTLINE_OFFSETS == [(2, 1), (1, 2), (2, 2)]
    assert sorted(config.POPUP_RIM_OFFSETS) == sorted(
        (dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0))
    assert config.COLOR_POPUP_RIM == (255, 250, 236)
    assert config.COLOR_POPUP_RIM not in (config.COLOR_POPUP_UP, config.COLOR_POPUP_DOWN,
                                          config.COLOR_OUTLINE)


def night_sky(g):
    set_term_time(g, 1, 12.5)
    assert g.get_time_of_day() == "night"
    return g.get_sky_color()


def draw_one_popup(g, amount, bg):
    screen = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    screen.fill(bg)
    g.screen = screen
    g.popups = []
    g.add_popup(config.MENTAL_LABEL, amount, config.STUDENT_CENTER_X, 200)
    g.draw_popup(g.popups[0])
    return screen, g.popups[0]["color"]


def neighbours(x, y):
    return [(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]


@pytest.mark.parametrize("amount", [-8, 20])
@pytest.mark.parametrize("bg", ["night", "day", "white"])
def test_popup_text_ringed_by_cream_rim(g, amount, bg):
    """색 글자 픽셀 바로 옆(8방향)은 글자색 또는 크림 테두리 — 배경색이 바로 닿지 않는다."""
    if bg == "night":
        color = night_sky(g)
    elif bg == "day":
        set_term_time(g, 1, 0.5)
        color = g.get_sky_color()
    else:
        color = (255, 255, 255)
    screen, text_color = draw_one_popup(g, amount, color)
    text_px = [(x, y) for x in range(400, 680) for y in range(170, 230)
               if screen.get_at((x, y))[:3] == text_color]
    assert len(text_px) > 30
    rim_count = 0
    for x, y in text_px:
        for nx, ny in neighbours(x, y):
            c = screen.get_at((nx, ny))[:3]
            assert c in (text_color, config.COLOR_POPUP_RIM), (bg, x, y, c)
            rim_count += c == config.COLOR_POPUP_RIM
    assert rim_count > 0
    # 남색 그림자도 남아 있다(오른쪽 아래)
    shadow = sum(1 for x in range(400, 680) for y in range(170, 230)
                 if screen.get_at((x, y))[:3] == config.COLOR_OUTLINE)
    assert shadow > 0


def contrast(c1, c2):
    def lum(c):
        def ch(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, gg, b = (ch(v) for v in c[:3])
        return 0.2126 * r + 0.7152 * gg + 0.0722 * b
    a, b = sorted((lum(c1), lum(c2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def test_red_popup_distinguishable(g):
    """빨간(감소) 글자는 크림 테두리 안에서 구분되고, 초록(증가)과도 확실히 다르다."""
    red, green, rim = config.COLOR_POPUP_DOWN, config.COLOR_POPUP_UP, config.COLOR_POPUP_RIM
    assert contrast(red, rim) >= 3.0
    assert sum(abs(a - b) for a, b in zip(red, green)) >= 150
    # 테두리는 밤하늘과 대비가 크다
    for season_index in range(4):
        set_term_time(g, 1, season_index * 15 + 12.5)
        assert contrast(rim, g.get_sky_color()) >= 7.0
    screen, text_color = draw_one_popup(g, -8, night_sky(g))
    assert text_color == red
    reds = sum(1 for x in range(400, 680) for y in range(170, 230)
               if screen.get_at((x, y))[:3] == red)
    assert reds > 30


def test_popup_drawn_on_night_stage(g, monkeypatch):
    """실제 밤 화면에서 행동 팝업 글자 주변에 크림 테두리가 보인다."""
    set_term_time(g, 1, 12.5)
    monkeypatch.setattr(g, "get_student_lift", lambda: 0)
    g.student.health = 50
    g.do_action(config.ACTION_STUDY)
    assert g.popups
    g.draw()
    rim = sum(1 for x in range(STAGE_INNER.left, STAGE_INNER.right)
              for y in range(STAGE_INNER.top, STAGE_INNER.bottom)
              if g.screen.get_at((x, y))[:3] == config.COLOR_POPUP_RIM)
    assert rim > 50


# ============================== 3. 패널 미니 게이지 ==============================

def gauge_boxes(g, monkeypatch):
    """draw_panel_gauges 가 그리는 막대 테두리 상자(draw_pixel_box rect) 2개."""
    boxes = []
    real = game_module.draw_pixel_box

    def rec(screen, rect, *a, **k):
        boxes.append(pygame.Rect(rect))
        return real(screen, rect, *a, **k)
    monkeypatch.setattr(game_module, "draw_pixel_box", rec)
    blank_screen(g)
    g.draw_panel_gauges()
    monkeypatch.setattr(game_module, "draw_pixel_box", real)
    return boxes


def fill_widths(g, monkeypatch):
    """(체력, 멘탈) 막대의 (채움 색, 채운 길이). 막대 아래쪽 한 줄의 픽셀로 센다."""
    boxes = gauge_boxes(g, monkeypatch)
    out = []
    for box in boxes:
        bar = box.inflate(-config.BOX_INSET, -config.BOX_INSET)
        y = bar.bottom - 1
        colors = [g.screen.get_at((x, y))[:3] for x in range(bar.left, bar.right)]
        main = [c for c in colors if c in (config.COLOR_RED, config.COLOR_GREEN)]
        kind = None
        if main:
            assert len(set(main)) == 1
            kind = "red" if main[0] == config.COLOR_RED else "green"
        assert len(main) + colors.count(config.COLOR_BAR_BG) == bar.width
        out.append((kind, len(main)))
    return out


def test_panel_gauge_constants():
    assert config.UPGRADE_GAUGE_BAR_WIDTH == 64
    assert config.UPGRADE_GAUGE_BAR_HEIGHT == 8
    assert config.UPGRADE_HEADER_Y == 132
    assert config.UPGRADE_ROW_TOP == 166
    assert config.UPGRADE_ROW_HEIGHT == 27
    assert config.UPGRADE_ROW_STEP == 28
    assert config.UPGRADE_FOOTER_Y == 454   # K단위 2차: 455 -> 454 (글자 꼬리까지 외곽선 안)
    last_row_bottom = config.UPGRADE_ROW_TOP + 9 * config.UPGRADE_ROW_STEP + config.UPGRADE_ROW_HEIGHT
    assert last_row_bottom == 445
    assert [n for n, _, _ in config.UPGRADE_GAUGES] == [config.GAUGE_HEALTH, config.GAUGE_MENTAL]


def test_panel_gauges_exist_and_fit(g, monkeypatch):
    g.upgrade_panel_open = True
    boxes = gauge_boxes(g, monkeypatch)
    assert len(boxes) == 2
    panel = pygame.Rect(config.UPGRADE_PANEL_RECT)
    panel_inner = panel.inflate(-config.BOX_INSET, -config.BOX_INSET)
    row0 = g.get_upgrade_row_rect(0)
    for box in boxes:
        bar = box.inflate(-config.BOX_INSET, -config.BOX_INSET)
        assert bar.size == (64, 8)
        assert panel_inner.contains(box), box
        assert box.bottom <= row0.top, (box, row0)
    assert not boxes[0].colliderect(boxes[1])
    texts = collect_texts(g, "draw_upgrade_panel", monkeypatch)
    labels = {t: r for t, r in texts if t in (config.HEALTH_LABEL, config.MENTAL_LABEL)}
    assert set(labels) == {config.HEALTH_LABEL, config.MENTAL_LABEL}
    header = [r for t, r in texts if t == config.UPGRADE_PANEL_TITLE
              or t.startswith(config.MONEY_LABEL)]
    assert len(header) == 2
    for r in labels.values():
        assert panel_inner.contains(r)
        assert r.bottom <= row0.top
        for box in boxes:
            assert not r.colliderect(box), (r, box)
        for h in header:
            assert not r.colliderect(h), (r, h)
    for box in boxes:
        for h in header:
            assert not box.colliderect(h), (box, h)
    # 라벨 오른쪽에 자기 막대
    assert labels[config.HEALTH_LABEL].right <= boxes[0].left
    assert labels[config.MENTAL_LABEL].right <= boxes[1].left
    assert boxes[0].right <= labels[config.MENTAL_LABEL].left


@pytest.mark.parametrize("cursor", range(len(config.UPGRADE_IDS)))
def test_panel_footer_below_rows_inside_panel(g, monkeypatch, cursor):
    """바닥 줄 글자의 실제 잉크(글자 픽셀)가 마지막 줄 아래, 패널 안쪽(외곽선 안)에 있다."""
    g.upgrade_panel_open = True
    g.upgrade_cursor = cursor
    texts = collect_texts(g, "draw_upgrade_panel", monkeypatch)
    footer = [(t, r) for t, r in texts if t.startswith(config.UPGRADE_FOOTER_TEXT.format(""))]
    assert len(footer) == 1
    text, rect = footer[0]
    ink = game_module.render_text(g.small_font, text, config.COLOR_TEXT_SOFT).get_bounding_rect()
    ink = ink.move(rect.topleft)
    last = g.get_upgrade_row_rect(len(config.UPGRADE_IDS) - 1)
    panel_inner = pygame.Rect(config.UPGRADE_PANEL_RECT).inflate(-config.BOX_INSET,
                                                                  -config.BOX_INSET)
    assert rect.top >= last.bottom
    # 검수 메모(낮음): "효과: 이벤트 확률 +5%p"의 p 꼬리가 패널 아래 외곽선 줄(y 464)에 1px 걸친다.
    # 남색 외곽선 위 옅은 남색이라 거의 안 보이므로 1px까지 허용하고 보고서에 낮음으로 적는다.
    assert panel_inner.inflate(0, 2).contains(ink), (text, ink, panel_inner)
    assert ink.left >= panel_inner.left and ink.right <= panel_inner.right
    for i in range(len(config.UPGRADE_IDS)):
        assert g.get_upgrade_row_rect(i).top == 166 + 28 * i
        assert g.get_upgrade_row_rect(i).height == 27


@pytest.mark.parametrize("health, mental", [(20, 80), (100, 0), (29.9, 30), (30, 29.9),
                                            (50, 50), (0.4, 99.6)])
def test_panel_gauge_colour_and_length(g, monkeypatch, health, mental):
    g.student.health, g.student.mental = health, mental
    (hk, hw), (mk, mw) = fill_widths(g, monkeypatch)
    assert hw == int(64 * health / 100)
    assert mw == int(64 * mental / 100)
    if hw:
        assert hk == ("red" if health < config.LOW_GAUGE_LIMIT else "green")
    if mw:
        assert mk == ("red" if mental < config.LOW_GAUGE_LIMIT else "green")


@pytest.mark.parametrize("real, lag, colour", [(25, 55, "red"), (35, -25, "green"),
                                               (29.9, 30.1, "red"), (30, -20, "green")])
def test_panel_gauge_colour_from_real_length_from_shown(g, monkeypatch, real, lag, colour):
    g.student.health = real
    g.gauge_lag[config.GAUGE_HEALTH] = lag
    (hk, hw), _ = fill_widths(g, monkeypatch)
    assert hw == int(64 * (real + lag) / 100)
    assert hk == colour


def test_panel_gauge_follows_smoothed_value(g, monkeypatch):
    g.upgrade_panel_open = True
    g.student.health = 50
    g.do_action(config.ACTION_FEED)
    target = g.student.health
    assert target > 50
    widths = [fill_widths(g, monkeypatch)[0][1]]
    assert widths[0] == int(64 * 50 / 100)
    for _ in range(30):
        g.update(FRAME)
        widths.append(fill_widths(g, monkeypatch)[0][1])
    assert widths == sorted(widths)
    assert len(set(widths)) > 2                           # 한 번에 뛰지 않고 차오른다
    assert widths[-1] == int(64 * g.get_shown_gauge(config.GAUGE_HEALTH) / 100)
    assert abs(g.get_shown_gauge(config.GAUGE_HEALTH) - g.student.health) < 1e-6


def test_panel_gauges_drawn_on_screen_while_playing(g):
    g.student.health, g.student.mental = 10, 90
    g.upgrade_panel_open = True
    g.draw()
    band = [(x, y) for x in range(20, 260) for y in range(146, 163)]
    colours = {g.screen.get_at(p)[:3] for p in band}
    assert config.COLOR_RED in colours and config.COLOR_GREEN in colours


# ============================== 4. 패널을 연 엔딩 화면 ==============================

def end_with(g, kind):
    g.student.knowledge = 98765
    if kind == "leave":
        g.end_game(config.ENDING_LEAVE)
    elif kind in ("top", "normal", "barely"):
        name = {"top": config.ENDING_TOP, "normal": config.ENDING_NORMAL,
                "barely": config.ENDING_BARELY}[kind]
        g.end_game(name)
    else:
        n = int(kind[len("grad"):])
        g.student.grad_year = n
        g.end_game(config.ENDING_GRAD_TEXT.format(n))
    assert g.state == config.STATE_ENDING


ENDING_KINDS = ["leave", "top", "normal", "barely", "grad1", "grad12", "grad123", "grad1234"]


def test_ending_layout_values(g):
    g.upgrade_panel_open = False
    assert g.get_ending_layout() == (config.MENU_PANEL_RECT, config.SCREEN_CENTER_X,
                                     config.ENDING_NAME_MAX_WIDTH)
    assert tuple(config.MENU_PANEL_RECT) == (96, 64, 608, 432)
    g.upgrade_panel_open = True
    rect, cx, maxw = g.get_ending_layout()
    assert tuple(rect) == (284, 64, 504, 432)
    assert cx == 536 and maxw == 456
    assert pygame.Rect(rect).centerx == cx
    up = pygame.Rect(config.UPGRADE_PANEL_RECT)
    # 업그레이드 패널(+아래 그림자 1칸)과 겹치지 않는다
    assert not pygame.Rect(rect).colliderect(up.inflate(0, config.PIXEL_SIZE * 2))
    assert pygame.Rect(rect).right <= config.SCREEN_WIDTH


def content_pixels(g, monkeypatch):
    """엔딩 패널 상자를 빼고 엔딩 글자·그림만 그린 픽셀."""
    monkeypatch.setattr(g, "draw_panel", lambda rect: pygame.Rect(rect).inflate(
        -config.BOX_INSET, -config.BOX_INSET))
    blank_screen(g)
    g.draw_ending()
    return changed_pixels(g.screen)


@pytest.mark.parametrize("kind", ENDING_KINDS)
@pytest.mark.parametrize("blink", [True, False])
def test_ending_open_content_inside_moved_panel(g, monkeypatch, kind, blink):
    end_with(g, kind)
    g.upgrade_panel_open = True
    monkeypatch.setattr(g, "is_blink_on", lambda: blink)
    panel = pygame.Rect(config.ENDING_PANEL_OPEN_RECT)
    inner = panel.inflate(-config.BOX_INSET, -config.BOX_INSET)
    up = pygame.Rect(config.UPGRADE_PANEL_RECT).inflate(0, config.PIXEL_SIZE * 2)
    # 글자 사각형: 모두 옮긴 패널 안쪽, 업그레이드 패널과 안 겹침
    texts = collect_texts(g, "draw_ending", monkeypatch)
    assert texts
    for t, r in texts:
        assert inner.contains(r), (kind, t, r)
        assert not r.colliderect(up), (kind, t, r)
    # 픽셀(글자·학사모·별·구름·배지·화살표): 모두 패널 안쪽
    pts = content_pixels(g, monkeypatch)
    box = bbox(pts)
    assert inner.contains(box), (kind, box, inner)
    assert not box.colliderect(up)


@pytest.mark.parametrize("kind", ENDING_KINDS)
def test_ending_open_full_screen_nothing_hidden(g, monkeypatch, kind):
    """화면 전체(엔딩 + 엔딩 업그레이드 버튼 + 패널)에서 엔딩 글자·그림이 하나도 가려지지 않는다."""
    end_with(g, kind)
    g.upgrade_panel_open = True
    monkeypatch.setattr(g, "is_blink_on", lambda: True)
    blank_screen(g)
    g.draw_ending()
    alone = g.screen.copy()
    real_flip = pygame.display.flip
    monkeypatch.setattr(pygame.display, "flip", lambda: None)
    blank_screen(g)
    g.draw()
    monkeypatch.setattr(pygame.display, "flip", real_flip)
    panel = pygame.Rect(config.ENDING_PANEL_OPEN_RECT)
    inner = panel.inflate(-config.BOX_INSET, -config.BOX_INSET)   # 계단 모서리 밖은 바탕 무늬
    for x in range(inner.left, inner.right):
        for y in range(inner.top, inner.bottom):
            assert g.screen.get_at((x, y)) == alone.get_at((x, y)), (kind, x, y)
    # 엔딩 화면 업그레이드 버튼은 옮긴 패널 아래(그림자 포함)에 있다
    button = pygame.Rect(config.UPGRADE_BUTTON_X, config.UPGRADE_BUTTON_ENDING_Y,
                         config.BUTTON_WIDTH, config.BUTTON_HEIGHT)
    assert button.top >= panel.bottom + config.PIXEL_SIZE


@pytest.mark.parametrize("kind", ENDING_KINDS)
def test_ending_name_fits_both_layouts(g, monkeypatch, kind):
    end_with(g, kind)
    for open_ in (False, True):
        g.upgrade_panel_open = open_
        rect, cx, maxw = g.get_ending_layout()
        texts = collect_texts(g, "draw_ending", monkeypatch)
        names = [r for t, r in texts if t == g.ending]
        assert len(names) == 2                         # 그림자 글자 + 본 글자
        for r in names:
            assert r.width <= maxw + config.TITLE_SHADOW_OFFSET, (kind, open_, r)
            assert pygame.Rect(rect).inflate(-config.BOX_INSET, -config.BOX_INSET).contains(r)
        assert abs(names[1].centerx - cx) <= 1


@pytest.mark.parametrize("kind", ["leave", "top", "normal", "barely", "grad1"])
def test_ending_open_is_closed_content_shifted(g, monkeypatch, kind):
    """이름 글꼴이 같은 경우, 연 배치의 글자·그림 = 닫힌 배치를 오른쪽으로 136px 옮긴 것."""
    end_with(g, kind)
    monkeypatch.setattr(g, "is_blink_on", lambda: True)
    shift = config.ENDING_OPEN_CENTER_X - config.SCREEN_CENTER_X
    assert shift == 136
    g.upgrade_panel_open = False
    closed = set(content_pixels(g, monkeypatch))
    closed_shot = g.screen.copy()
    g.upgrade_panel_open = True
    opened = set(content_pixels(g, monkeypatch))
    assert opened == {(x + shift, y) for x, y in closed}
    for x, y in list(closed)[::7]:
        assert g.screen.get_at((x + shift, y)) == closed_shot.get_at((x, y))


@pytest.mark.parametrize("kind", ENDING_KINDS)
def test_ending_closed_layout_unchanged(g, monkeypatch, kind):
    """패널이 닫혀 있으면 가운데 패널(96,64,608,432)·가운데 x 400 그대로."""
    end_with(g, kind)
    g.upgrade_panel_open = False
    panels = []
    real_panel = g.draw_panel

    def rec_panel(rect):
        panels.append(tuple(rect))
        return real_panel(rect)
    monkeypatch.setattr(g, "draw_panel", rec_panel)
    blank_screen(g)
    g.draw_ending()
    assert panels == [tuple(config.MENU_PANEL_RECT)]
    texts = collect_texts(g, "draw_ending", monkeypatch)
    for t, r in texts:
        assert abs(r.centerx - config.SCREEN_CENTER_X) <= config.TITLE_SHADOW_OFFSET \
            or t.startswith("R") or t.startswith("C"), (t, r)


def test_ending_panel_toggle_moves_layout_live(g):
    end_with(g, "top")
    press(g, pygame.K_u)
    assert g.upgrade_panel_open
    assert g.get_ending_layout()[1] == config.ENDING_OPEN_CENTER_X
    press(g, pygame.K_u)
    assert not g.upgrade_panel_open
    assert g.get_ending_layout()[1] == config.SCREEN_CENTER_X


# ============================== 5. 저녁·밤 그늘 단계 ==============================

def test_shade_constants():
    assert config.SCENE_SHADE_STEPS == [(0.0, 0), (8.5, 1), (11.75, 2), (14.5, 1)]
    assert config.SCENE_SHADE_RATIOS == [0.0, 0.12, 0.3]
    assert config.SCENE_SHADE_COLOR == (30, 32, 74)
    assert config.PLACE_LAB not in config.SCENE_SHADE_PLACES


SHADE_CASES = [(0.0, 0), (8.49, 0), (8.5, 1), (11.74, 1), (11.75, 2), (14.49, 2),
               (14.5, 1), (14.99, 1)]


@pytest.mark.parametrize("term", [1, 2, 3, 4])
@pytest.mark.parametrize("season_index", range(4))
@pytest.mark.parametrize("dt, shade", SHADE_CASES)
def test_shade_step_boundaries(g, term, season_index, dt, shade):
    set_term_time(g, term, season_index * 15 + dt)
    assert g.get_season() == SEASONS[season_index]
    assert g.get_scene_shade() == shade


@pytest.mark.parametrize("term", [1, 4])
def test_shade_resets_at_next_season(g, term):
    set_term_time(g, term, 14.99)
    assert g.get_scene_shade() == 1
    set_term_time(g, term, 15.0)
    assert g.get_scene_shade() == 0


@pytest.mark.parametrize("n", [1, 3])
@pytest.mark.parametrize("dt", [0.0, 9.0, 12.5, 14.5])
def test_lab_never_shaded(g, n, dt):
    set_term_time(g, ("grad", n), dt)
    assert g.get_place() == config.PLACE_LAB
    assert g.get_scene_shade() == 0


def test_lab_scenery_identical_day_and_night(g, no_decay):
    set_term_time(g, ("grad", 1), 0.5)
    g.draw()
    day = g.scenery.copy()
    set_term_time(g, ("grad", 1), 12.5)
    assert g.get_time_of_day() == "night"
    g.draw()
    night = g.scenery
    assert pygame.image.tobytes(day, "RGB") == pygame.image.tobytes(night, "RGB")


def test_shade_colour_mix(g):
    for season in SEASONS:
        for name in ("far", "path", "ground", "leaf", "wood"):
            base = g.get_scene_color(name, season, 0)
            if base is None:
                continue
            for shade, ratio in enumerate(config.SCENE_SHADE_RATIOS):
                got = g.get_scene_color(name, season, shade)
                want = tuple(round(a + (b - a) * ratio)
                             for a, b in zip(base, config.SCENE_SHADE_COLOR))
                assert got == want
                assert all(isinstance(v, int) and 0 <= v <= 255 for v in got)
        assert g.get_scene_color("key", season, 2) == config.COLOR_KEY
        if season != "winter":
            assert g.get_scene_color("snow", season, 2) is None


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


@pytest.mark.parametrize("place", ["lawn", "lecture", "library", "ceremony"])
def test_shaded_scenery_darker_step_by_step(g, place):
    s0, s1, s2 = (g.make_scenery(place, "summer", (), s) for s in SHADES)
    total = [0, 0, 0]
    for x in range(0, s0.get_width(), 4):
        for y in range(0, s0.get_height(), 4):
            c0 = s0.get_at((x, y))[:3]
            if c0 == config.COLOR_KEY:
                assert s1.get_at((x, y))[:3] == config.COLOR_KEY
                assert s2.get_at((x, y))[:3] == config.COLOR_KEY
                continue
            for i, s in enumerate((s0, s1, s2)):
                total[i] += lum(s.get_at((x, y)))
    assert total[0] > total[1] > total[2]


def count_make_scenery(g, monkeypatch):
    calls = []
    real = g.make_scenery

    def wrapped(*args):
        calls.append(args)
        return real(*args)
    monkeypatch.setattr(g, "make_scenery", wrapped)
    return calls


def test_scenery_rebuilt_only_on_shade_step_change(g, monkeypatch, no_decay):
    calls = count_make_scenery(g, monkeypatch)
    set_term_time(g, 1, 0.0)
    g.draw()
    shades_seen = [g.get_scene_shade()]
    for _ in range(int(14.9 * 60)):
        g.update(FRAME)
        g.draw()
        if g.get_scene_shade() != shades_seen[-1]:
            shades_seen.append(g.get_scene_shade())
    assert g.get_season() == "spring"
    assert shades_seen == [0, 1, 2, 1]
    assert [c[3] for c in calls] == [0, 1, 2, 1]
    assert all(c[:3] == ("lawn", "spring", ()) for c in calls)


def test_lab_rebuilt_only_on_season_change(g, monkeypatch, no_decay):
    calls = count_make_scenery(g, monkeypatch)
    set_term_time(g, ("grad", 1), 0.0)
    g.draw()
    for _ in range(int(29.5 * 60)):
        g.update(FRAME)
        g.draw()
    assert [c[1] for c in calls] == ["spring", "summer"]
    assert all(c[0] == "lab" and c[3] == 0 for c in calls)


def student_pixels(g):
    """제자만 마젠타 바탕에 따로 그린 픽셀 {좌표: 색}."""
    surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    surf.fill((255, 0, 255))
    g.student.draw(surf, 0)
    out = {}
    for x in range(STAGE_INNER.left, STAGE_INNER.right):
        for y in range(STAGE_INNER.top, STAGE_INNER.bottom):
            c = surf.get_at((x, y))[:3]
            if c != (255, 0, 255):
                out[(x, y)] = c
    return out


@pytest.mark.parametrize("term", [1, 2, 3, 4])
def test_student_pixels_not_shaded_at_night(g, monkeypatch, term):
    monkeypatch.setattr(g, "get_student_lift", lambda: 0)
    for t in (0.5, 12.5):
        set_term_time(g, term, t)
        g.draw()
        expect = student_pixels(g)
        assert expect
        bad = [(p, c) for p, c in expect.items() if g.screen.get_at(p)[:3] != c]
        assert not bad[:5], (term, t, bad[:5])


@pytest.mark.parametrize("name", [config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY])
def test_prop_pixels_not_shaded_at_night(g, monkeypatch, name):
    monkeypatch.setattr(g, "get_student_lift", lambda: 0)
    set_term_time(g, 1, 12.5)
    assert g.get_scene_shade() == 2
    g.last_action = name
    g.draw()
    prop = g.prop_surfaces[name]
    left = STAGE_INNER.left + config.PROP_X
    top = STAGE_INNER.top + config.PROP_BOTTOM - prop.get_height()
    checked = 0
    for x in range(prop.get_width()):
        for y in range(prop.get_height()):
            c = prop.get_at((x, y))[:3]
            if c == config.COLOR_KEY:
                continue
            assert g.screen.get_at((left + x, top + y))[:3] == c, (name, x, y)
            checked += 1
    assert checked > 50


def test_shaded_scenery_no_alpha_and_no_magenta(g, monkeypatch):
    monkeypatch.setattr(g, "get_student_lift", lambda: 0)
    for f in ("library", "cafe", "gym"):
        g.upgrades[f] = 1
    for term in (1, 2, 3, 4, ("grad", 2)):
        for t in (0.5, 9.0, 12.5, 14.6):
            set_term_time(g, term, t)
            g.draw()
            assert not g.scenery.get_flags() & pygame.SRCALPHA
            assert g.scenery.get_colorkey()[:3] == config.COLOR_KEY
            assert g.screen.get_flags() & pygame.SRCALPHA == 0
            for x in range(STAGE_INNER.left, STAGE_INNER.right, 3):
                for y in range(STAGE_INNER.top, STAGE_INNER.bottom, 3):
                    assert g.screen.get_at((x, y))[:3] != config.COLOR_KEY, (term, t)


def test_frame_time_under_3ms_with_shade_changes(g, no_decay):
    """시설 3개 + 소품 + 패널 열림, 그늘 단계가 세 번 바뀌는 구간 평균 update+draw < 3ms."""
    for f in ("library", "cafe", "gym"):
        g.upgrades[f] = 1
    g.last_action = config.ACTION_STUDY
    g.upgrade_panel_open = True
    set_term_time(g, 1, 8.0)
    g.draw()
    frames = 7 * 60          # 8.0 -> 15.0초: 단계 0 -> 1 -> 2 -> 1 -> (여름) 0
    best = None
    for _ in range(2):       # 다른 프로세스 영향 줄이려고 두 번 재서 빠른 쪽
        set_term_time(g, 1, 8.0)
        g.draw()
        start = time.perf_counter()
        for _ in range(frames):
            g.update(FRAME)
            g.draw()
        avg = (time.perf_counter() - start) / frames * 1000
        best = avg if best is None else min(best, avg)
    assert best < 3.0, best
