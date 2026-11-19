"""J단위 검수: 무대 배경 4겹(장소·하늘/계절·행동 소품·시설) + 업그레이드 패널 왼쪽 재배치
(기획서 10절 "배경", jeja-spec 15절).

이 파일은 conftest 의 AUTO_OFF_FILES / EVENTS_OFF_FILES 에 없으므로 자동 행동·이벤트가 켜진 채로 돈다.
시간을 흘리는 테스트는 no_auto / no_events / no_decay 를 직접 쓴다.
"""

import ast
import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
from conftest import press  # noqa: E402
from game import Game  # noqa: E402

ROOT = Path(config.__file__).parent
FRAME = 1 / 60
FEED, REST, STUDY = config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY
SEASONS = ["spring", "summer", "autumn", "winter"]
FACILITIES = ["library", "cafe", "gym"]
# 개발 약속(J단위): 하늘색 기준점 (계절 안 시각, 시간대). 15초는 다음 계절의 낮
KEYFRAMES = [(0.0, "day"), (7.5, "day"), (9.5, "evening"), (11.0, "evening"),
             (12.5, "night"), (14.0, "night")]
STAGE = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH, config.PANEL_HEIGHT)
STAGE_INNER = STAGE.inflate(-config.BOX_INSET, -config.BOX_INSET)


# ============================== 도우미 ==============================

@pytest.fixture
def no_decay(monkeypatch):
    """체력·멘탈 자연 감소를 0으로(긴 시간 진행 테스트에서 휴학하지 않게)."""
    monkeypatch.setattr(config, "HEALTH_DECAY_PER_SEC", 0)
    monkeypatch.setattr(config, "MENTAL_DECAY_PER_SEC", 0)
    monkeypatch.setattr(config, "MENTAL_DECAY_PER_SEC_EXAM", 0)


@pytest.fixture
def g(no_events, no_auto):
    """이벤트·자동 행동을 끈 채 게임 중인 Game."""
    game = Game()
    press(game, pygame.K_RETURN)
    assert game.state == config.STATE_PLAYING
    yield game
    pygame.quit()


def set_term_time(game, term, t):
    """term 1~4 = 학부 학년, ("grad", n) = 대학원 n년차. 그 학년/년차 안 시각 t 로 맞춘다."""
    if isinstance(term, tuple):
        n = term[1]
        game.student.grad_year = n
        game.student.elapsed = config.TOTAL_SECONDS + (n - 1) * 60 + t
    else:
        game.student.grad_year = 0
        game.student.elapsed = (term - 1) * 60 + t


TERMS = [1, 2, 3, 4, ("grad", 1), ("grad", 3)]


def render(game):
    """game.draw() 한 뒤 화면 복사본을 돌려준다."""
    game.draw()
    return game.screen.copy()


def diff_pixels(a, b, rect=None):
    """두 Surface 에서 색이 다른 픽셀 좌표 목록(rect 안만, 기본 화면 전체)."""
    if rect is None:
        rect = a.get_rect()
    out = []
    for x in range(rect.left, rect.right):
        for y in range(rect.top, rect.bottom):
            if a.get_at((x, y)) != b.get_at((x, y)):
                out.append((x, y))
    return out


def count_diff(a, b, rect):
    """rect 안에서 색이 다른 픽셀 수 (RGB 바이트 비교로 빠르게)."""
    bytes_a = pygame.image.tobytes(a.subsurface(rect), "RGB")
    bytes_b = pygame.image.tobytes(b.subsurface(rect), "RGB")
    return sum(1 for i in range(0, len(bytes_a), 3) if bytes_a[i:i + 3] != bytes_b[i:i + 3])


def freeze_lift(game, monkeypatch):
    monkeypatch.setattr(game, "get_student_lift", lambda: 0)


# ============================== 1. 계절·시간대 경계 ==============================

SEASON_CASES = [(0.0, "spring"), (14.99, "spring"), (15.0, "summer"), (29.99, "summer"),
                (30.0, "autumn"), (44.99, "autumn"), (45.0, "winter"), (59.99, "winter")]


@pytest.mark.parametrize("term", TERMS)
@pytest.mark.parametrize("t, season", SEASON_CASES)
def test_season_boundaries(g, term, t, season):
    set_term_time(g, term, t)
    assert g.get_season() == season


@pytest.mark.parametrize("term", TERMS)
@pytest.mark.parametrize("season_index", range(4))
@pytest.mark.parametrize("dt, tod", [(0.0, "day"), (8.99, "day"), (9.0, "evening"),
                                     (11.99, "evening"), (12.0, "night"), (14.99, "night")])
def test_time_of_day_boundaries(g, term, season_index, dt, tod):
    set_term_time(g, term, season_index * 15 + dt)
    assert g.get_season() == SEASONS[season_index]
    assert g.get_time_of_day() == tod


def test_frame_accumulated_season_boundary(g):
    """1/60초를 900번 더해 15초가 될 때(14.9999…)도 여름으로 본다(소수 오차)."""
    g.student.elapsed = 0.0
    for _ in range(900):
        g.student.elapsed += FRAME
    assert g.get_season() == "summer"
    assert g.get_time_of_day() == "day"


def test_undergrad_240_is_winter_end(g):
    """졸업 순간(240초, 4학년 학년 안 60초)은 겨울 끝(밤)으로 본다."""
    g.student.elapsed = config.TOTAL_SECONDS
    assert g.student.get_grade() == 4
    assert g.get_season() == "winter"
    assert g.get_time_of_day() == "night"


def test_season_methods_need_no_screen():
    """화면 없이(pygame.display 없이) 계산 메서드를 부를 수 있다: 반환형 확인."""
    game = Game()
    set_term_time(game, 2, 20)
    assert game.get_season() in SEASONS
    assert game.get_time_of_day() in ("day", "evening", "night")
    pygame.quit()


# ============================== 2. 하늘색 ==============================

def sky_at(game, term, t):
    set_term_time(game, term, t)
    return game.get_sky_color()


@pytest.mark.parametrize("term", TERMS)
@pytest.mark.parametrize("season_index", range(4))
@pytest.mark.parametrize("dt, name", KEYFRAMES)
def test_sky_equals_keyframe_colors(g, term, season_index, dt, name):
    color = sky_at(g, term, season_index * 15 + dt)
    assert isinstance(color, tuple) and len(color) == 3
    assert all(type(c) is int and 0 <= c <= 255 for c in color)
    assert color == tuple(config.SKY_COLORS[SEASONS[season_index]][name])


def lerp(a, b, r):
    return tuple(round(x + (y - x) * r) for x, y in zip(a, b))


@pytest.mark.parametrize("season_index", range(4))
def test_sky_interpolates_between_keyframes(g, season_index):
    season = SEASONS[season_index]
    nxt = SEASONS[(season_index + 1) % 4]
    c = config.SKY_COLORS
    base = season_index * 15
    # 낮 7.5 -> 저녁 9.5 의 가운데
    assert sky_at(g, 1, base + 8.5) == lerp(c[season]["day"], c[season]["evening"], 0.5)
    # 저녁 11 -> 밤 12.5 의 가운데
    assert sky_at(g, 1, base + 11.75) == lerp(c[season]["evening"], c[season]["night"], 0.5)
    # 밤 14 -> 다음 계절 낮 15 의 가운데 (겨울이면 다음 학년 봄)
    assert sky_at(g, 1, base + 14.5) == lerp(c[season]["night"], c[nxt]["day"], 0.5)
    # 낮 구간(0~7.5)과 밤 구간(12.5~14)은 한 색
    assert sky_at(g, 1, base + 4.0) == tuple(c[season]["day"])
    assert sky_at(g, 1, base + 13.0) == tuple(c[season]["night"])


def channel_jump(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


@pytest.mark.parametrize("before, after", [
    ((1, 14.9999), (1, 15.0)),          # 봄 밤 -> 여름 낮
    ((1, 59.9999), (2, 0.0)),           # 1학년 겨울 밤 -> 2학년 봄 낮
    ((3, 59.9999), (4, 0.0)),
    ((("grad", 1), 59.9999), (("grad", 2), 0.0)),  # 대학원 년차 경계
])
def test_sky_continuous_across_boundaries(g, before, after):
    a = sky_at(g, *before)
    b = sky_at(g, *after)
    assert channel_jump(a, b) <= 1, (a, b)


def test_sky_continuous_undergrad_end_to_grad_school(g):
    """졸업 순간(240초, 겨울 끝) 하늘 = 대학원 1년차 시작(봄 낮) 하늘."""
    g.student.elapsed = config.TOTAL_SECONDS
    a = g.get_sky_color()
    set_term_time(g, ("grad", 1), 0.0)
    b = g.get_sky_color()
    assert a == b == tuple(config.SKY_COLORS["spring"]["day"])


def test_sky_smooth_over_full_run_into_grad_school(g, no_decay):
    """60fps 로 240초 + 대학원 70초(년차 경계 포함)를 흘리며 프레임마다 하늘색 변화가 작다."""
    colors = [g.get_sky_color()]
    for _ in range(240 * 60 + 5):
        g.update(FRAME)
        if g.state != config.STATE_PLAYING:
            break
        colors.append(g.get_sky_color())
    assert g.state == config.STATE_ENDING and g.ending != config.ENDING_LEAVE
    colors.append(g.get_sky_color())
    press(g, pygame.K_c)
    assert g.state == config.STATE_PLAYING and g.grad_year == 1
    colors.append(g.get_sky_color())
    for _ in range(70 * 60):
        g.update(FRAME)
        colors.append(g.get_sky_color())
    assert g.grad_year == 2
    jumps = [channel_jump(a, b) for a, b in zip(colors, colors[1:])]
    assert max(jumps) <= 6, max(jumps)
    # 실제로 여러 색을 지난다(멈춰 있지 않다)
    assert len(set(colors)) > 100


# ============================== 3. 장소 ==============================

@pytest.mark.parametrize("term, place", [(1, "lawn"), (2, "lecture"), (3, "library"),
                                         (4, "ceremony"), (("grad", 1), "lab"),
                                         (("grad", 5), "lab")])
@pytest.mark.parametrize("t", [0.0, 30.0, 59.99])
def test_place_by_grade(g, term, place, t):
    set_term_time(g, term, t)
    assert g.get_place() == place


def test_place_changes_by_update_at_60s(g, no_decay):
    places = []
    for _ in range(4):
        places.append(g.get_place())
        for _ in range(3600):
            g.update(FRAME)
    assert places == ["lawn", "lecture", "library", "ceremony"]


# ============================== 4. 행동 소품 ==============================

def test_last_action_none_at_start_and_after_new_game(g):
    assert g.last_action is None
    g.do_action(STUDY)
    assert g.last_action == STUDY
    g.start_new_game()
    assert g.last_action is None


@pytest.mark.parametrize("name", [FEED, REST, STUDY])
def test_last_action_follows_auto_action(no_events, name):
    game = Game()
    press(game, pygame.K_RETURN)
    game.choose_auto_action = lambda: name
    for _ in range(int(config.AUTO_ACTION_INTERVAL * 60) + 2):
        game.update(FRAME)
    assert game.last_action == name
    pygame.quit()


def test_prop_pixels_per_action(g, monkeypatch):
    """소품 없음 / 공부 / 휴식 / 학식 의 무대 그림이 모두 다르고, 다른 부분은 무대 안쪽뿐."""
    freeze_lift(g, monkeypatch)
    set_term_time(g, 1, 3.0)
    shots = {}
    for name in (None, FEED, REST, STUDY):
        g.last_action = name
        shots[name] = render(g)
    for name in (FEED, REST, STUDY):
        changed = diff_pixels(shots[None], shots[name])
        assert len(changed) > 100, name
        assert all(STAGE_INNER.collidepoint(p) for p in changed), name
    assert count_diff(shots[FEED], shots[REST], STAGE_INNER) > 100
    assert count_diff(shots[REST], shots[STUDY], STAGE_INNER) > 100
    assert count_diff(shots[FEED], shots[STUDY], STAGE_INNER) > 100


def test_prop_stays_until_next_action(g):
    """소품은 다음 행동 전까지 그대로(시간이 흘러도 last_action 유지)."""
    g.do_action(REST)
    for _ in range(120):
        g.update(FRAME)
    assert g.last_action == REST


# ============================== 5. 시설 ==============================

@pytest.mark.parametrize("term", TERMS)
@pytest.mark.parametrize("facility", FACILITIES)
def test_facility_pixels_only_when_owned(g, monkeypatch, term, facility):
    freeze_lift(g, monkeypatch)
    set_term_time(g, term, 3.0)
    base = render(g)
    again = render(g)
    assert count_diff(base, again, STAGE_INNER) == 0   # 같은 상태는 같은 그림
    g.upgrades[facility] = 1
    owned = render(g)
    changed = diff_pixels(base, owned)
    small = term[0] == "grad" if isinstance(term, tuple) else False
    assert len(changed) > (20 if small else 200), (term, facility, len(changed))
    assert all(STAGE_INNER.collidepoint(p) for p in changed)
    g.upgrades[facility] = 0
    assert count_diff(base, render(g), STAGE_INNER) == 0


def test_three_facilities_are_distinct(g, monkeypatch):
    freeze_lift(g, monkeypatch)
    set_term_time(g, 1, 3.0)
    base = render(g)
    regions = {}
    for facility in FACILITIES:
        for f in FACILITIES:
            g.upgrades[f] = 1 if f == facility else 0
        regions[facility] = set(diff_pixels(base, render(g), STAGE_INNER))
    # 시설마다 그려지는 자리가 대부분 다르다(같은 건물을 겹쳐 그리지 않음)
    for a in FACILITIES:
        for b in FACILITIES:
            if a < b:
                overlap = len(regions[a] & regions[b])
                assert overlap < 0.2 * min(len(regions[a]), len(regions[b])), (a, b)


def test_owned_facilities_tuple(g):
    assert g.get_owned_facilities() == ()
    g.upgrades["gym"] = 1
    g.upgrades["library"] = 1
    assert set(g.get_owned_facilities()) == {"gym", "library"}


# ============================== 6. 무대 안쪽에만 / 그리는 순서 ==============================

@pytest.mark.parametrize("term, t, action, owned", [
    (1, 3.0, None, False), (1, 13.0, STUDY, True), (2, 25.0, REST, True),
    (3, 43.0, FEED, False), (4, 58.0, STUDY, True), (("grad", 1), 57.0, REST, True),
])
def test_background_confined_to_stage(g, monkeypatch, term, t, action, owned):
    """배경을 빼고 그린 화면과 비교해 달라진 픽셀이 모두 무대 안쪽 사각형 안에 있다.

    정보바·시험 배너·상태 패널(게이지)·방침 버튼·[업그레이드] 버튼은 배경 영향이 없다.
    """
    freeze_lift(g, monkeypatch)
    set_term_time(g, term, t)
    g.last_action = action
    for f in FACILITIES:
        g.upgrades[f] = 1 if owned else 0
    with_bg = render(g)
    monkeypatch.setattr(g, "draw_background", lambda: None)
    without = render(g)
    changed = diff_pixels(with_bg, without)
    assert len(changed) > 1000
    assert all(STAGE_INNER.collidepoint(p) for p in changed)
    # 무대 테두리(외곽선) 위 줄은 그대로
    assert with_bg.get_at((STAGE.centerx, STAGE.top)) == without.get_at((STAGE.centerx, STAGE.top))


def test_background_not_on_title_or_ending(g, monkeypatch):
    """타이틀·엔딩 화면은 배경을 그리지 않는다(바뀌지 않음)."""
    def boom():
        raise AssertionError("draw_background called")
    monkeypatch.setattr(g, "draw_background", boom)
    g.state = config.STATE_TITLE
    g.draw()
    g.state = config.STATE_PLAYING
    g.student.knowledge = 500
    g.student.elapsed = config.TOTAL_SECONDS - FRAME / 2
    monkeypatch.setattr(config, "HEALTH_DECAY_PER_SEC", 0)
    g.update(FRAME)
    assert g.state == config.STATE_ENDING
    g.draw()
    g.upgrade_panel_open = True
    g.draw()


@pytest.mark.parametrize("term, t", [(1, 3.0), (1, 13.0), (3, 43.0), (4, 50.0),
                                     (("grad", 2), 10.0)])
def test_student_fully_drawn_over_background(g, monkeypatch, term, t):
    """제자를 빈 Surface에 따로 그린 픽셀이 게임 화면에서도 그대로 보인다(배경이 가리지 않음)."""
    freeze_lift(g, monkeypatch)
    set_term_time(g, term, t)
    g.last_action = STUDY
    for f in FACILITIES:
        g.upgrades[f] = 1
    screen = render(g)
    marker = (1, 2, 3)
    plain = pygame.Surface(screen.get_size())
    plain.fill(marker)
    g.student.draw(plain, 0)
    checked = 0
    for x in range(STAGE_INNER.left, STAGE_INNER.right, 2):
        for y in range(STAGE_INNER.top, STAGE_INNER.bottom, 2):
            c = plain.get_at((x, y))[:3]
            if c != marker:
                assert screen.get_at((x, y))[:3] == c, (x, y)
                checked += 1
    assert checked > 500
    # 얼굴 피부 픽셀이 있다
    r = g.student.get_radius()
    cell = r // 10
    assert screen.get_at((config.STUDENT_CENTER_X,
                          config.STUDENT_CENTER_Y + 3 * cell + 1))[:3] == config.COLOR_SKIN


def test_draw_order_in_playing(g, monkeypatch):
    """무대: 배경 -> 제자 -> 파티클·팝업 -> 알림 순서."""
    log = []
    for name in ("draw_background", "draw_stage_effects", "draw_event_notice"):
        real = getattr(g, name)
        monkeypatch.setattr(g, name, (lambda n, f: (lambda *a, **k: (log.append(n), f(*a, **k))))(name, real))
    real_draw = g.student.draw
    monkeypatch.setattr(g.student, "draw", lambda *a, **k: (log.append("student"), real_draw(*a, **k)))
    g.notice = {"good": True, "text": "테스트 알림", "timer": 1.0}
    g.draw()
    assert log == ["draw_background", "student", "draw_stage_effects", "draw_event_notice"]


def stage_shot_at(g, term, t, monkeypatch):
    freeze_lift(g, monkeypatch)
    set_term_time(g, term, t)
    return render(g)


def test_notice_opaque_over_day_and_night(g, monkeypatch):
    """자동형 알림 상자 안쪽은 낮·밤 하늘과 상관없이 같은 픽셀(불투명, 배경 위)."""
    g.notice = {"good": False, "text": "감기 기운이 돈다", "timer": 1.0}
    day = stage_shot_at(g, 1, 3.0, monkeypatch)
    night = stage_shot_at(g, 1, 13.0, monkeypatch)
    box = pygame.Rect(config.EVENT_NOTICE_X + 8, config.EVENT_NOTICE_Y + 8,
                      100, config.EVENT_NOTICE_HEIGHT - 16)
    assert count_diff(day, night, box) == 0
    # 알림 밖 하늘은 실제로 달라졌다(비교가 의미 있음)
    assert count_diff(day, night, STAGE_INNER) > 1000


def test_popups_drawn_over_background(g, monkeypatch):
    freeze_lift(g, monkeypatch)
    set_term_time(g, 1, 13.0)
    base = render(g)
    g.spawn_popups([("체력", 20)])
    with_popup = render(g)
    assert count_diff(base, with_popup, STAGE_INNER) > 30


def test_dialog_opaque_over_background(g, monkeypatch):
    """선택지형 대화창 안쪽은 낮·밤 배경과 상관없이 같다(배경 위에 그림)."""
    event = config.CHOICE_EVENTS[0]
    g.start_event(event)
    g.dialog_time = 5.0
    assert g.state == config.STATE_EVENT
    day = stage_shot_at(g, 1, 3.0, monkeypatch)
    night = stage_shot_at(g, 1, 13.0, monkeypatch)
    box = pygame.Rect(config.EVENT_DIALOG_RECT).inflate(-16, -16)
    assert count_diff(day, night, box) == 0


# ============================== 7. 캐시 ==============================

def count_make_scenery(g, monkeypatch):
    calls = []
    real = g.make_scenery

    def wrapped(*args):
        calls.append(args)
        return real(*args)
    monkeypatch.setattr(g, "make_scenery", wrapped)
    return calls


def test_scenery_cached_between_frames(g, monkeypatch, no_decay):
    calls = count_make_scenery(g, monkeypatch)
    set_term_time(g, 1, 0.5)
    g.draw()
    first = g.scenery
    assert len(calls) == 1
    # (K단위 갱신) 바깥 배경은 저녁·밤 그늘 단계(8.5 / 11.75 / 14.5초)가 바뀔 때만 다시 그린다.
    # 같은 그늘 단계 안(0.5 -> 8.4초, 낮 -> 저녁 시작 포함)에서는 다시 그리지 않는다
    while g.student.elapsed < 8.4:
        g.update(FRAME)
        g.draw()
    assert g.get_season() == "spring" and g.get_scene_shade() == 0
    assert len(calls) == 1
    assert g.scenery is first
    # 단계마다 딱 한 번씩만 다시 그리고, 단계 안 프레임에서는 같은 그림을 다시 쓴다
    for _ in range(int(4.6 * 60)):               # 13.0초까지: 저녁(1) -> 밤(2)
        before = g.scenery
        shade_before = g.get_scene_shade()
        g.update(FRAME)
        g.draw()
        if g.get_scene_shade() == shade_before:
            assert g.scenery is before
    assert g.get_season() == "spring" and g.get_time_of_day() == "night"
    assert [c[3] for c in calls] == [0, 1, 2]


def test_scenery_regenerated_on_season_place_facility(g, monkeypatch, no_decay):
    calls = count_make_scenery(g, monkeypatch)
    set_term_time(g, 1, 14.9)
    g.draw()
    g.draw()
    assert len(calls) == 1
    for _ in range(12):                      # 15초를 넘겨 여름
        g.update(FRAME)
        g.draw()
    assert g.get_season() == "summer"
    assert len(calls) == 2
    assert calls[-1][1] == "summer"
    g.upgrades["cafe"] = 1                   # 시설 추가
    g.draw()
    assert len(calls) == 3
    assert "cafe" in calls[-1][2]
    g.draw()
    assert len(calls) == 3
    set_term_time(g, 2, 15.5)                # 장소 바뀜(같은 여름)
    g.draw()
    assert len(calls) == 4
    assert calls[-1][0] == "lecture"


def test_scenery_regenerations_bounded_over_full_run(g, monkeypatch, no_decay):
    """240초 동안 다시 그리는 횟수 = 장소·계절 조합(16) x 그늘 단계 변화(계절당 0/1/2/1 = 4번)
    = 64 정도(K단위 갱신, 여유 두어 80 이하). 매 프레임 그리지 않는다."""
    calls = count_make_scenery(g, monkeypatch)
    for i in range(240 * 60):
        g.update(FRAME)
        if g.state != config.STATE_PLAYING:
            break
        if i % 10 == 0:
            g.draw()
    assert len(calls) <= 80
    # 연달은 두 번이 같은 열쇠로 다시 그려지는 일은 없다(바뀐 것이 있을 때만 다시 그림)
    for a, b in zip(calls, calls[1:]):
        assert a != b


# ============================== 8. 반투명 금지 / colorkey ==============================

def code_of(name):
    return (ROOT / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("fname", ["game.py", "student.py", "button.py", "config.py"])
def test_no_alpha_or_blend_in_code(fname):
    tree = ast.parse(code_of(fname))
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    for bad in ("SRCALPHA", "set_alpha", "convert_alpha"):
        assert bad not in names, (fname, bad)
    assert not any(n.startswith("BLEND_") for n in names), fname
    assert not any(isinstance(n, ast.keyword) and n.arg == "special_flags"
                   for n in ast.walk(tree)), fname


def test_scenery_and_sprites_use_colorkey_not_alpha(g):
    g.draw()
    surfaces = [g.scenery] + list(g.sky_objects.values()) + list(g.prop_surfaces.values())
    for surface in surfaces:
        assert not surface.get_flags() & pygame.SRCALPHA
        assert surface.get_colorkey()[:3] == (255, 0, 255)
    assert g.scenery.get_size() == STAGE_INNER.size


def test_magenta_never_visible_on_screen(g, monkeypatch):
    """colorkey 색(자홍)이 화면에 그대로 찍히지 않는다."""
    for term in TERMS:
        for t in (3.0, 10.0, 13.0, 50.0):
            set_term_time(g, term, t)
            for f in FACILITIES:
                g.upgrades[f] = 1
            g.last_action = STUDY
            screen = render(g)
            for x in range(STAGE_INNER.left, STAGE_INNER.right, 2):
                for y in range(STAGE_INNER.top, STAGE_INNER.bottom, 2):
                    assert screen.get_at((x, y))[:3] != (255, 0, 255), (term, t, x, y)


# ============================== 9. 속도 ==============================

def test_frame_draw_time_reasonable(g, no_decay):
    """300 프레임 update+draw 평균이 넉넉한 기준(12ms) 안. 60fps = 16.7ms."""
    for f in FACILITIES:
        g.upgrades[f] = 1
    g.last_action = STUDY
    set_term_time(g, 1, 13.0)
    g.draw()
    start = time.perf_counter()
    for _ in range(300):
        g.update(FRAME)
        g.draw()
    avg_ms = (time.perf_counter() - start) / 300 * 1000
    assert avg_ms < 12, avg_ms


# ============================== 10. 업그레이드 패널 재배치 ==============================

def test_panel_rect_in_left_column():
    panel = pygame.Rect(config.UPGRADE_PANEL_RECT)
    assert tuple(panel) == (12, 116, 256, 352)
    assert panel.right <= config.STAGE_X
    assert not panel.colliderect(STAGE)
    assert panel.top >= config.INFO_BAR_HEIGHT
    assert panel.bottom <= config.BUTTON_Y
    assert panel.left >= 0


def test_panel_rows_and_footer_inside(g):
    panel = pygame.Rect(config.UPGRADE_PANEL_RECT)
    for i in range(len(config.UPGRADE_IDS)):
        row = g.get_upgrade_row_rect(i)
        assert panel.contains(row)
        assert not row.colliderect(STAGE)
    assert config.UPGRADE_ROW_TOP > config.UPGRADE_HEADER_Y
    last = g.get_upgrade_row_rect(len(config.UPGRADE_IDS) - 1)
    assert last.bottom < config.UPGRADE_FOOTER_Y < panel.bottom


@pytest.mark.parametrize("term, t", [(1, 3.0), (2, 50.0), (("grad", 1), 13.0)])
def test_panel_does_not_cover_stage(g, monkeypatch, term, t):
    """패널을 열어도 무대(배경·제자)는 한 픽셀도 바뀌지 않는다."""
    freeze_lift(g, monkeypatch)
    set_term_time(g, term, t)
    closed = render(g)
    g.upgrade_panel_open = True
    opened = render(g)
    assert count_diff(closed, opened, STAGE) == 0
    changed = diff_pixels(closed, opened, pygame.Rect(0, 0, config.SCREEN_WIDTH, 470))
    assert changed
    panel = pygame.Rect(config.UPGRADE_PANEL_RECT)
    # 바뀐 곳은 패널(+그림자 1칸) 안
    shadow = panel.inflate(0, 0).union(panel.move(config.PIXEL_SIZE, config.PIXEL_SIZE))
    assert all(shadow.collidepoint(p) for p in changed)


def test_panel_row_click_buys_that_row(g):
    g.money = 10 ** 9
    g.upgrade_panel_open = True
    for index, uid in enumerate(config.UPGRADE_IDS):
        before = dict(g.upgrades)
        pos = g.get_upgrade_row_rect(index).center
        g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
        assert g.upgrade_cursor == index
        for other in config.UPGRADE_IDS:
            expect = before[other] + (1 if other == uid else 0)
            assert g.upgrades[other] == expect, (uid, other)


def test_panel_keys_buy_cursor_row(g):
    g.money = 10 ** 9
    press(g, pygame.K_u)
    assert g.upgrade_panel_open
    for _ in range(3):
        press(g, pygame.K_DOWN)
    press(g, pygame.K_RETURN)
    uid = config.UPGRADE_IDS[3]
    assert g.upgrades[uid] == 1
    assert sum(g.upgrades.values()) == 1
    press(g, pygame.K_UP)
    press(g, pygame.K_UP)
    press(g, pygame.K_UP)
    press(g, pygame.K_UP)
    assert g.upgrade_cursor == len(config.UPGRADE_IDS) - 1   # 위로 감싸 돈다
    press(g, pygame.K_u)
    assert not g.upgrade_panel_open


def test_stage_click_with_panel_open_buys_nothing(g):
    g.money = 10 ** 9
    g.upgrade_panel_open = True
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=STAGE.center))
    assert sum(g.upgrades.values()) == 0


def test_buying_facility_shows_it_immediately(g, monkeypatch):
    """패널에서 시설(도서관)을 사면 다음 그림에 바로 무대에 나타난다."""
    freeze_lift(g, monkeypatch)
    set_term_time(g, 1, 3.0)
    g.money = 10 ** 6
    base = render(g)
    g.upgrade_panel_open = True
    index = config.UPGRADE_IDS.index("library")
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                      pos=g.get_upgrade_row_rect(index).center))
    assert g.upgrades["library"] == 1
    after = render(g)
    assert count_diff(base, after, STAGE_INNER) > 200
