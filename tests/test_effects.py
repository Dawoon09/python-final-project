"""검수 단위 B: 상호작용 효과 E1~E6 (기획서 8절, jeja-spec 13절 효과 표와 규칙).

- E1 버튼 호버·눌림(4px, 0.12초)·쿨타임 회색 + 진행 막대
- E2 행동별 파티클(8~12개, 종류·색, 수명 0.6~0.8, 결정성, random 금지)
- E3 수치 팝업(clamp 반영 실제 변화, 0이면 생략, 0.8초, 무대 패널 밖으로 안 그림)
- E4 게이지 부드러운 변화(표시값, 0.25초, 색은 실제 값, 새 판 초기화)
- E5 제자 점프(0.3초, 최대 8px)·숨쉬기(4px 이내, 1.5초 주기), 반지름 불변
- E6 안내 깜빡임(0.5초), 타이틀·엔딩에서는 게임 시간이 흐르지 않음
- 규칙: 무시된 입력엔 연출 없음, 엔딩·새 판에서 연출 초기화, 연출이 결과에 영향 없음
"""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import ast  # noqa: E402
import pathlib  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402

from conftest import reach_grade  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAME_FILES = ["main.py", "game.py", "student.py", "button.py", "config.py"]
P = config.PIXEL_SIZE
CX, CY = config.STUDENT_CENTER_X, config.STUDENT_CENTER_Y
FRAME = 1 / 60
# (L단위) 시간 제한이 없어져 대본 시나리오를 넉넉한 시간(15분) 안에서 엔딩까지 돌린다
SCRIPT_FRAMES = 15 * 60 * 60


def old_grade_at(student, elapsed):
    """(L단위) 예전 테스트의 "elapsed초 = (elapsed // 60 + 1)학년"을 재현한다.

    경과 시간(주기·시험 기간)은 elapsed로 두고, 학년은 지식으로 올린다(reach_grade).
    """
    student.elapsed = elapsed
    grade = min(config.MAX_GRADE, int(elapsed // config.CYCLE_SECONDS) + config.FIRST_GRADE)
    reach_grade(student, grade)


# ======================= 공통 도우미 =======================

def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=pygame.BUTTON_LEFT)


def motion(pos):
    return pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0))


def color(surf, x, y):
    return tuple(surf.get_at((x, y)))[:3]


def body_point(g, name):
    """버튼 몸통 점(외곽선·하이라이트 줄·글자를 피한 왼쪽 안쪽 열의 세로 가운데)."""
    r = g.buttons[name].rect
    return r.left + 2 * P, r.centery


# (G단위) 키 1/2/3은 이제 방침 선택이다. 예전 "키로 행동" 자리는 이 표로 do_action을 부른다.
LEGACY_KEY_ACTIONS = {pygame.K_1: config.ACTION_FEED, pygame.K_2: config.ACTION_REST,
                      pygame.K_3: config.ACTION_STUDY}
# (G단위) 호버 검사에 쓰는, 시작 방침(균형)이 아닌 방침 버튼 두 개
HOVER_A = config.POLICY_STUDY_FOCUS
HOVER_B = config.POLICY_REST_FOCUS


def normal_color(g, name):
    """(G단위) 호버가 없을 때 방침 버튼 몸통 색: 고른 방침은 노랑, 나머지는 하늘색."""
    if name == g.policy:
        return config.COLOR_POLICY_SELECTED
    return config.COLOR_BUTTON


def popup_texts(g):
    """팝업 글자를 위에서 아래(y 오름차순) 순서로 돌려준다."""
    return [p["text"] for p in sorted(g.popups, key=lambda p: p["y"])]


def effects_snapshot(g):
    return (
        [dict(p) for p in g.particles], [dict(p) for p in g.popups], dict(g.press_timers),
        g.jump_timer, dict(g.gauge_lag), dict(g.gauge_lag_speed),
    )


def assert_effects_cleared(g):
    assert g.particles == []
    assert g.popups == []
    assert all(t == 0 for t in g.press_timers.values())
    assert g.jump_timer == 0
    assert all(v == 0 for v in g.gauge_lag.values())
    for name in config.GAUGE_NAMES:
        assert g.get_shown_gauge(name) == getattr(g.student, name)


@pytest.fixture
def game(playing_game):
    """타이틀에서 Enter를 눌러 게임 진행 중인 Game (conftest.playing_game)."""
    return playing_game


@pytest.fixture
def title_game():
    g = Game()
    yield g
    pygame.quit()


# ======================= 설정값 (jeja-spec 13절 효과 표) =======================

def test_effect_constants_match_spec():
    assert config.BUTTON_PRESS_OFFSET == 4
    assert config.BUTTON_PRESS_TIME == 0.12
    assert 8 <= config.PARTICLE_COUNT <= 12
    assert all(0.6 <= life <= 0.8 for life in config.PARTICLE_LIFETIMES)
    assert config.POPUP_TIME == 0.8
    assert config.GAUGE_ANIM_TIME == 0.25
    assert config.JUMP_TIME == 0.3 and config.JUMP_HEIGHT == 8
    assert config.BREATH_PERIOD == 1.5 and config.BREATH_HEIGHT <= 4
    assert config.BLINK_INTERVAL == 0.5
    assert config.POPUP_TEXT.format("체력", 20) == "체력 +20"
    assert config.POPUP_TEXT.format("멘탈", -8) == "멘탈 -8"


def test_apricot_light_removed_and_cool_text_darker():
    """A단위 낮음 정리: 안 쓰는 COLOR_APRICOT_LIGHT 삭제, 쿨타임 글자색이 회색 몸통보다 충분히 진함."""
    assert not hasattr(config, "COLOR_APRICOT_LIGHT")
    for name in GAME_FILES:
        assert "COLOR_APRICOT_LIGHT" not in (ROOT / name).read_text(encoding="utf-8")

    def lum(rgb):
        return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    assert lum(config.COLOR_GRAY) - lum(config.COLOR_BUTTON_TEXT_COOL) >= 80


def test_gauge_rows_moved():
    assert (config.HEALTH_LABEL_Y, config.HEALTH_BAR_Y,
            config.MENTAL_LABEL_Y, config.MENTAL_BAR_Y) == (200, 232, 320, 352)


# ======================= E1 버튼 호버·눌림·쿨타임 =======================

def test_hover_brightens_only_hovered_button(game):
    game.draw()
    assert all(color(game.screen, *body_point(game, n)) == normal_color(game, n)
               for n in game.buttons)
    game.handle_event(motion(game.buttons[HOVER_B].rect.center))
    game.draw()
    assert color(game.screen, *body_point(game, HOVER_B)) == config.COLOR_BUTTON_BRIGHT
    for n in (HOVER_A, config.POLICY_BALANCED):
        assert color(game.screen, *body_point(game, n)) == normal_color(game, n)
    # 버튼 밖(버튼 사이 틈)으로 나가면 원래 색
    gap_x = game.buttons[HOVER_A].rect.right + config.BUTTON_GAP // 2
    game.handle_event(motion((gap_x, config.BUTTON_Y + 10)))
    game.draw()
    assert all(color(game.screen, *body_point(game, n)) == normal_color(game, n)
               for n in game.buttons)


def test_hover_does_not_override_selected(game):
    """(G단위) 고른 방침 버튼은 호버해도 노랑 강조가 그대로다(호버보다 선택 강조가 우선)."""
    game.handle_event(motion(game.buttons[config.POLICY_BALANCED].rect.center))
    game.draw()
    assert color(game.screen, *body_point(game, config.POLICY_BALANCED)) == \
        config.COLOR_POLICY_SELECTED


@pytest.mark.parametrize("edge", ["left", "right"])
def test_hover_edges(game, edge):
    r = game.buttons[HOVER_A].rect
    inside = (r.left, r.centery) if edge == "left" else (r.right - 1, r.centery)
    outside = (r.left - 1, r.centery) if edge == "left" else (r.right, r.centery)
    game.handle_event(motion(inside))
    game.draw()
    assert color(game.screen, *body_point(game, HOVER_A)) == config.COLOR_BUTTON_BRIGHT
    game.handle_event(motion(outside))
    game.draw()
    assert color(game.screen, *body_point(game, HOVER_A)) == config.COLOR_BUTTON


def test_mouse_pos_starts_unknown_and_only_motion_updates(game):
    assert game.mouse_pos is None
    game.draw()      # mouse_pos 가 None 이어도 그리기 오류 없음
    game.handle_event(click(game.buttons[HOVER_A].rect.center))
    assert game.mouse_pos is None
    game.handle_event(motion((5, 6)))
    assert game.mouse_pos == (5, 6)


def test_hover_after_action_still_bright_no_gray(game):
    """(예전: 쿨타임 중 호버해도 회색) G단위: 쿨타임이 없어 행동 직후에도 호버가 밝게 보인다."""
    game.handle_event(motion(game.buttons[HOVER_B].rect.center))
    game.do_action(config.ACTION_STUDY)
    game.update(0.5)
    game.draw()
    assert color(game.screen, *body_point(game, HOVER_B)) == config.COLOR_BUTTON_BRIGHT
    assert all(color(game.screen, *body_point(game, n)) != config.COLOR_GRAY for n in game.buttons)


def _is_pressed_on_screen(g, name):
    """버튼 외곽선 맨 윗줄 자리(rect.top + 2)가 남색이 아니면 몸통이 4px 내려간 것."""
    r = g.buttons[name].rect
    return color(g.screen, r.left + 2 * P, r.top + 2) != config.COLOR_OUTLINE


@pytest.mark.parametrize("trigger, name", [
    ("key", config.POLICY_STUDY_FOCUS), ("key", config.POLICY_BALANCED),
    ("key", config.POLICY_REST_FOCUS),
    ("click", config.POLICY_STUDY_FOCUS), ("click", config.POLICY_BALANCED),
    ("click", config.POLICY_REST_FOCUS),
])
def test_only_executed_button_is_pressed(game, trigger, name):
    """(G단위) 고른 방침 버튼만 눌린다(키 1/2/3 또는 클릭)."""
    keys = {config.POLICY_STUDY_FOCUS: pygame.K_1, config.POLICY_BALANCED: pygame.K_2,
            config.POLICY_REST_FOCUS: pygame.K_3}
    game.draw()
    assert not any(_is_pressed_on_screen(game, n) for n in game.buttons)
    if trigger == "key":
        game.handle_event(key(keys[name]))
    else:
        game.handle_event(click(game.buttons[name].rect.center))
    assert game.press_timers == {name: config.BUTTON_PRESS_TIME}
    game.draw()
    for n in game.buttons:
        assert _is_pressed_on_screen(game, n) is (n == name), n
    # 눌린 버튼: 몸통 외곽선이 정확히 4px 아래(받침 줄 위)
    r = game.buttons[name].rect
    assert color(game.screen, r.left + 2 * P, r.top + config.BUTTON_PRESS_OFFSET) == config.COLOR_OUTLINE


def test_press_returns_after_012s_boundary(game):
    game.handle_event(key(pygame.K_1))    # (G단위) 공부 위주 방침 버튼
    game.update(0.11)
    game.draw()
    assert _is_pressed_on_screen(game, config.POLICY_STUDY_FOCUS)
    game.update(0.02)
    game.draw()
    assert not _is_pressed_on_screen(game, config.POLICY_STUDY_FOCUS)


def test_press_returns_after_012s_frames(game):
    """60fps 프레임: 7프레임(0.117초) 뒤 눌림, 8프레임(0.133초) 뒤 복귀."""
    game.handle_event(key(pygame.K_3))    # (G단위) 휴식 위주 방침 버튼
    for _ in range(7):
        game.update(FRAME)
    game.draw()
    assert _is_pressed_on_screen(game, config.POLICY_REST_FOCUS)
    game.update(FRAME)
    game.draw()
    assert not _is_pressed_on_screen(game, config.POLICY_REST_FOCUS)


# (G단위) 예전 "버튼 안 쿨타임 진행 막대(1초, 비례·단조·1초 뒤 사라짐)" 테스트 2개는 쿨타임 삭제로
# 규칙이 없어져 지웠다. 대신 방침 버튼 아래 자동 행동 진행 막대(2초)는 test_idle_g.py에서 픽셀로 본다.


# ======================= E2 행동별 파티클 =======================

@pytest.mark.parametrize("k, name", [(pygame.K_1, config.ACTION_FEED),
                                     (pygame.K_2, config.ACTION_REST),
                                     (pygame.K_3, config.ACTION_STUDY)])
def test_particle_count_and_lifetime(game, k, name):
    game.do_action(LEGACY_KEY_ACTIONS[k])
    assert 8 <= len(game.particles) <= 12
    assert all(0.6 <= p["life"] <= 0.8 for p in game.particles)
    kinds = config.PARTICLE_KINDS[name]
    assert {id(p["sprite"]) for p in game.particles} == {id(s) for s, _ in kinds}


def test_particle_kinds_and_colors_per_action():
    feed = config.PARTICLE_KINDS[config.ACTION_FEED]
    rest = config.PARTICLE_KINDS[config.ACTION_REST]
    study = config.PARTICLE_KINDS[config.ACTION_STUDY]
    assert [s for s, _ in feed] == [config.PARTICLE_HEART, config.PARTICLE_RICE]
    assert [s for s, _ in rest] == [config.PARTICLE_ZZZ, config.PARTICLE_CLOUD]
    assert [s for s, _ in study] == [config.PARTICLE_STAR, config.PARTICLE_PENCIL]
    # 학식 = 분홍·흰, 휴식 = 하늘, 공부 = 노랑
    feed_colors = {c for _, cs in feed for c in cs.values()}
    assert {config.COLOR_PINK_DARK, config.COLOR_WHITE} <= feed_colors
    rest_colors = {c for _, cs in rest for c in cs.values()}
    assert rest_colors <= {config.COLOR_SKY, config.COLOR_SKY_LIGHT, config.COLOR_SKY_DARK}
    for rgb in rest_colors:
        assert rgb[2] > rgb[0] and rgb[2] > rgb[1]          # 파란 기운
    study_colors = {c for _, cs in study for c in cs.values()}
    assert config.COLOR_YELLOW in study_colors and config.COLOR_YELLOW_DARK in study_colors
    # 모든 스프라이트 글자는 색 사전에 있거나 투명
    for kinds in (feed, rest, study):
        for grid, colors in kinds:
            assert len({len(row) for row in grid}) == 1
            assert all(ch == "." or ch in colors for row in grid for ch in row)


def test_particles_spawn_near_student_edge(game):
    for elapsed in (0.0, 60.0, 120.0, 180.0):
        game.start_new_game()
        old_grade_at(game.student, elapsed)
        game.do_action(config.ACTION_FEED)
        r = game.student.get_radius()
        for p in game.particles:
            dist = ((p["x"] - CX) ** 2 + (p["y"] - CY) ** 2) ** 0.5
            assert r <= dist <= r * 1.3, (elapsed, dist)


def test_particles_removed_when_life_ends(game):
    game.do_action(config.ACTION_FEED)
    lives = sorted(p["life"] for p in game.particles)
    game.update(0.59)
    assert len(game.particles) == len(lives)
    game.update(0.06)      # 0.65
    assert len(game.particles) == sum(1 for life in lives if life > 0.65)
    game.update(0.1)       # 0.75
    assert len(game.particles) == sum(1 for life in lives if life > 0.75)
    game.update(0.06)      # 0.81
    assert game.particles == []


def test_particles_removed_frames(game):
    game.do_action(config.ACTION_STUDY)
    for _ in range(int(0.8 * 60) + 1):
        game.update(FRAME)
    assert game.particles == []


def _particle_layout(g):
    return [(p["x"], p["y"], p["vx"], p["vy"], p["life"], id(p["sprite"])) for p in g.particles]


def test_particles_deterministic_between_games(tmp_path):
    a = Game(record_path=str(tmp_path / "a.json"))
    b = Game(record_path=str(tmp_path / "b.json"))
    for g in (a, b):
        g.start_new_game()
        g.do_action(config.ACTION_REST)
        g.update(0.3)
    assert _particle_layout(a) == _particle_layout(b)
    a.draw()
    img_a = pygame.image.tobytes(a.screen, "RGB")
    b.draw()
    assert img_a == pygame.image.tobytes(b.screen, "RGB")
    pygame.quit()


def test_particles_same_every_time_in_same_grade(game):
    game.do_action(config.ACTION_FEED)
    first = _particle_layout(game)
    game.update(1.0)
    game.do_action(config.ACTION_FEED)
    assert _particle_layout(game) == first     # 첫 번째 것은 이미 사라졌고 같은 자리에 다시 나옴


RANDOM_METHODS = ("random", "randint", "uniform", "choice", "choices", "shuffle",
                  "sample", "randrange", "gauss")


def _is_self_rng(node):
    """node가 self.rng 이면 True."""
    return (isinstance(node, ast.Attribute) and node.attr == "rng"
            and isinstance(node.value, ast.Name) and node.value.id == "self")


def test_no_random_module_anywhere():
    """(C단위 갱신) random은 랜덤 이벤트 전용: game.py만 import random 하고,
    random 모듈은 random.Random( 한 곳에서만 쓰며 난수 호출은 모두 self.rng.~ 이다.
    다른 파일은 random·secrets·math·time을 import하지 않는다(파티클 결정성 유지)."""
    banned = ("random", "secrets", "math", "time")
    for name in GAME_FILES:
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        random_uses = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    mod = a.name.split(".")[0]
                    if name == "game.py" and mod == "random":
                        assert a.name == "random" and a.asname is None, name
                        continue
                    assert mod not in banned, (name, mod)
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in banned, name
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.value.id == "random":
                    random_uses.append(node.attr)
                elif node.attr in RANDOM_METHODS:
                    assert name == "game.py" and _is_self_rng(node.value), (
                        f"{name}: {node.attr}는 self.rng에서만 호출해야 함")
            elif isinstance(node, ast.Name) and node.id == "rng":
                raise AssertionError(f"{name}: 지역 rng 변수 금지(self.rng만)")
        if name == "game.py":
            assert random_uses == ["Random"], random_uses
        else:
            assert random_uses == [], (name, random_uses)
            assert "rng" not in (ROOT / name).read_text(encoding="utf-8"), name


# ======================= E3 수치 팝업 =======================

@pytest.mark.parametrize("setup, k, expected", [
    ({"health": 80}, pygame.K_1, ["체력 +20"]),
    ({"health": 95}, pygame.K_1, ["체력 +5"]),
    ({"health": 100}, pygame.K_1, []),
    ({"mental": 80, "knowledge": 10}, pygame.K_2, ["멘탈 +20", "지식 -2"]),
    ({"mental": 80, "knowledge": 0}, pygame.K_2, ["멘탈 +20"]),
    ({"mental": 90, "knowledge": 1}, pygame.K_2, ["멘탈 +10", "지식 -1"]),
    ({"mental": 100, "knowledge": 0}, pygame.K_2, []),
    ({}, pygame.K_3, ["체력 -5", "멘탈 -8", "지식 +10"]),
    ({"elapsed": 45.0}, pygame.K_3, ["체력 -5", "멘탈 -8", "지식 +20"]),
    ({"elapsed": 44.9}, pygame.K_3, ["체력 -5", "멘탈 -8", "지식 +10"]),
    ({"elapsed": 225.0}, pygame.K_3, ["체력 -5", "멘탈 -8", "지식 +20"]),
])
def test_popup_texts_use_clamped_real_change(game, setup, k, expected):
    for attr, value in setup.items():
        setattr(game.student, attr, value)
    game.do_action(LEGACY_KEY_ACTIONS[k])   # (G단위) 균형 방침: 배수 1.0
    assert game.state == config.STATE_PLAYING
    assert popup_texts(game) == expected


def test_popup_colors_by_sign(game):
    game.do_action(config.ACTION_STUDY)
    colors = {p["text"]: p["color"] for p in game.popups}
    assert colors["체력 -5"] == config.COLOR_POPUP_DOWN == config.COLOR_RED
    assert colors["멘탈 -8"] == config.COLOR_POPUP_DOWN
    assert colors["지식 +10"] == config.COLOR_POPUP_UP == config.COLOR_GREEN


def test_no_popup_when_no_change_but_other_effects_still_run(game):
    """체력 100에서 학식: 실제로 행동은 실행됐으므로 last_action·눌림·파티클·점프는 있고 팝업만 없다.

    (G단위) 쿨타임 대신 last_action 으로 "실행됨"을 본다.
    """
    game.student.health = 100
    assert game.do_action(config.ACTION_FEED) is True
    assert game.popups == []
    assert game.last_action == config.ACTION_FEED
    assert game.press_timers == {config.ACTION_FEED: config.BUTTON_PRESS_TIME}
    assert len(game.particles) == config.PARTICLE_COUNT
    assert game.jump_timer == config.JUMP_TIME
    assert game.gauge_lag == {n: 0 for n in config.GAUGE_NAMES}


def test_popups_stacked_without_glyph_overlap(game):
    game.do_action(config.ACTION_STUDY)
    ys = sorted(p["y"] for p in game.popups)
    assert [b - a for a, b in zip(ys, ys[1:])] == [config.POPUP_LINE_HEIGHT] * 2
    glyph_h = max(game.popup_font.render(p["text"], False, (0, 0, 0)).get_bounding_rect().height
                  for p in game.popups)
    assert glyph_h < config.POPUP_LINE_HEIGHT


def test_popup_removed_after_08s(game):
    game.do_action(config.ACTION_FEED)
    game.update(0.79)
    assert len(game.popups) == 1
    game.update(0.02)
    assert game.popups == []


def test_popup_removed_after_08s_frames(game):
    game.do_action(config.ACTION_STUDY)
    for _ in range(47):
        game.update(FRAME)
    assert len(game.popups) == 3
    for _ in range(2):
        game.update(FRAME)
    assert game.popups == []


def _diff_pixels(a, b):
    """두 화면에서 색이 다른 픽셀 좌표 목록."""
    w, h = a.get_size()
    ba, bb = pygame.image.tobytes(a, "RGB"), pygame.image.tobytes(b, "RGB")
    out = []
    for i in range(0, len(ba), 3):
        if ba[i:i + 3] != bb[i:i + 3]:
            n = i // 3
            out.append((n % w, n // w))
    return out


def test_popups_and_particles_never_drawn_outside_stage(game):
    """팝업·파티클을 무대 바깥쪽에 억지로 놓아도 무대 패널 안쪽 밖 픽셀은 바뀌지 않는다(set_clip)."""
    game.draw()
    base = game.screen.copy()
    game.popups = [
        {"text": "체력 +20", "color": config.COLOR_POPUP_UP, "y": config.PANEL_Y, "age": 0.0},
        {"text": "멘탈 -8", "color": config.COLOR_POPUP_DOWN, "y": config.PANEL_Y + 340, "age": 0.0},
    ]
    sprite, colors = config.PARTICLE_KINDS[config.ACTION_FEED][0]
    game.particles = [
        {"x": x, "y": y, "vx": 0, "vy": 0, "age": 0.0, "life": 0.8, "sprite": sprite,
         "colors": colors}
        for x, y in ((config.STAGE_X, 300), (config.STAGE_X + config.STAGE_WIDTH, 300),
                     (CX, config.PANEL_Y), (CX, config.PANEL_Y + config.PANEL_HEIGHT))
    ]
    game.draw()
    diff = _diff_pixels(base, game.screen)
    assert diff, "그려진 것이 없음"
    inner = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH,
                        config.PANEL_HEIGHT).inflate(-2 * P, -2 * P)
    assert all(inner.collidepoint(pt) for pt in diff), [pt for pt in diff
                                                        if not inner.collidepoint(pt)][:5]


@pytest.mark.parametrize("elapsed", [0.0, 60.0, 120.0, 180.0, 230.0])
def test_real_popups_fit_inside_stage_and_above_head(game, elapsed):
    """실제 공부(팝업 3개)를 4학년(반지름 70)까지 해 봐도 글자가 무대 안에서 잘리지 않고, 머리와 겹치지 않는다."""
    old_grade_at(game.student, elapsed)
    game.do_action(config.ACTION_STUDY)
    inner = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH,
                        config.PANEL_HEIGHT).inflate(-2 * P, -2 * P)
    head_top = CY - game.student.get_radius() - config.JUMP_HEIGHT - config.BREATH_HEIGHT
    for p in game.popups:
        surf = game.popup_font.render(p["text"], False, (0, 0, 0))
        glyph = surf.get_bounding_rect()
        rect = surf.get_rect()
        for age in (0.0, config.POPUP_TIME):
            rect.center = (CX, round(p["y"] - config.POPUP_RISE_SPEED * age))
            g = glyph.move(rect.topleft)
            assert inner.contains(g), (elapsed, p["text"], g)
        rect.center = (CX, round(p["y"]))
        assert glyph.move(rect.topleft).bottom <= head_top


def test_popup_rises_12px_and_blinks_from_05s(game):
    game.do_action(config.ACTION_FEED)
    p = game.popups[0]
    assert config.POPUP_RISE_SPEED * config.POPUP_TIME == pytest.approx(12)
    # 0.5초 전에는 항상 보이고, 0.5초부터 보임/숨김이 섞인다
    seen = []
    t = 0.0
    while game.popups:
        game.draw()
        seen.append((round(t, 4), _popup_visible(game, p)))
        game.update(FRAME)
        t += FRAME
    assert all(v for tt, v in seen if tt < config.POPUP_BLINK_START)
    after = [v for tt, v in seen if tt >= config.POPUP_BLINK_START]
    assert True in after and False in after


def _popup_visible(g, p):
    inner = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH, 120)
    return any(color(g.screen, x, y) == p["color"]
               for x in range(CX - 50, CX + 50) for y in range(inner.top + 8, CY - 40))


# ======================= E4 게이지 부드러운 변화 =======================

def _fill_width(g, bar_y):
    y = bar_y + config.BAR_HEIGHT // 2
    return sum(1 for x in range(config.GAUGE_X, config.GAUGE_X + config.BAR_WIDTH)
               if color(g.screen, x, y) in (config.COLOR_GREEN, config.COLOR_RED))


def _fill_color(g, bar_y):
    return color(g.screen, config.GAUGE_X + 1, bar_y + config.BAR_HEIGHT // 2)


def test_shown_value_animates_25_to_45_color_by_real(game):
    game.student.health = 25
    game.do_action(config.ACTION_FEED)
    assert game.student.health == 45
    assert game.get_shown_gauge(config.GAUGE_HEALTH) == 25
    game.draw()
    assert _fill_width(game, config.HEALTH_BAR_Y) == 50            # 길이는 이전 값
    assert _fill_color(game, config.HEALTH_BAR_Y) == config.COLOR_GREEN   # 색은 실제 값 45
    game.update(config.GAUGE_ANIM_TIME / 2)
    mid = game.get_shown_gauge(config.GAUGE_HEALTH)
    assert 25 < mid < 45 and mid == pytest.approx(35)
    game.draw()
    assert 50 < _fill_width(game, config.HEALTH_BAR_Y) < 90
    game.update(config.GAUGE_ANIM_TIME / 2)
    assert game.get_shown_gauge(config.GAUGE_HEALTH) == 45
    game.draw()
    assert _fill_width(game, config.HEALTH_BAR_Y) == 90


def test_shown_value_animates_down_red_by_real(game):
    """체력 32에서 공부 -> 27: 막대는 32 길이에서 시작하지만 색은 처음부터 빨강."""
    game.student.health = 32
    game.do_action(config.ACTION_STUDY)
    assert game.student.health == 27
    game.draw()
    assert _fill_width(game, config.HEALTH_BAR_Y) == 64
    assert _fill_color(game, config.HEALTH_BAR_Y) == config.COLOR_RED
    assert game.get_shown_gauge(config.GAUGE_MENTAL) == 80
    game.update(config.GAUGE_ANIM_TIME)
    game.draw()
    assert _fill_width(game, config.HEALTH_BAR_Y) == 54
    assert game.get_shown_gauge(config.GAUGE_MENTAL) == 72


def test_shown_value_frames_monotonic_and_bounded(game):
    game.student.mental = 50
    game.do_action(config.ACTION_REST)      # 50 -> 70
    values = [game.get_shown_gauge(config.GAUGE_MENTAL)]
    for _ in range(20):
        game.update(FRAME)
        values.append(game.get_shown_gauge(config.GAUGE_MENTAL))
    assert values == sorted(values)
    assert all(50 <= v <= 70 for v in values)
    assert values[-1] == 70          # 20프레임(0.33초) 뒤에는 실제 값
    # 0.25초(15프레임)가 지나면 실제 값이다 (16프레임째 확인)
    assert values[16] == 70


def test_natural_decay_not_animated(game):
    for _ in range(60):
        game.update(FRAME)
    assert game.student.health == 79
    assert game.get_shown_gauge(config.GAUGE_HEALTH) == 79
    assert game.gauge_lag == {n: 0 for n in config.GAUGE_NAMES}


def test_new_game_shown_equals_real(game):
    game.student.health = 30
    game.do_action(config.ACTION_FEED)
    assert game.get_shown_gauge(config.GAUGE_HEALTH) != game.student.health
    game.end_game(config.ENDING_LEAVE)
    game.handle_event(key(pygame.K_r))
    assert game.state == config.STATE_PLAYING
    for name in config.GAUGE_NAMES:
        assert game.get_shown_gauge(name) == getattr(game.student, name) == 80
    game.draw()
    assert _fill_width(game, config.HEALTH_BAR_Y) == 160


# ======================= E5 제자 반응 =======================

def test_jump_curve_max_8_snapped(game):
    lifts = []
    steps = 120
    for i in range(steps + 1):
        game.breath_time = 0.0                           # 숨쉬기 높이 0
        game.jump_timer = config.JUMP_TIME * (1 - i / steps)
        lifts.append(game.get_student_lift())
    assert max(lifts) == 8
    assert set(lifts) <= {0, 4, 8}
    assert lifts[0] == 0 and lifts[-1] == 0
    # 올라갔다 내려온다
    peak = lifts.index(8)
    assert lifts[:peak + 1] == sorted(lifts[:peak + 1])


def test_jump_starts_on_action_and_ends_after_03s(game):
    game.do_action(config.ACTION_FEED)
    assert game.jump_timer == config.JUMP_TIME
    game.update(0.29)
    assert game.jump_timer > 0
    game.update(0.02)
    assert game.jump_timer == 0


def test_breath_within_4px_period_15s(game):
    values = []
    t = 0.0
    for _ in range(int(3.0 * 120)):
        game.breath_time = t
        values.append(game.get_student_lift())
        t += 1 / 120
    assert set(values) <= {0, 4}
    assert 0 in values and 4 in values
    for i in range(0, 180, 7):
        game.breath_time = i / 120
        a = game.get_student_lift()
        game.breath_time = i / 120 + config.BREATH_PERIOD
        assert game.get_student_lift() == a


def test_breath_runs_in_play_only(title_game):
    title_game.update(0.75)
    assert title_game.breath_time == 0


def _face_bbox(surf):
    xs, ys = [], []
    for x in range(config.STAGE_X, config.STAGE_X + config.STAGE_WIDTH):
        for y in range(config.PANEL_Y, config.PANEL_Y + config.PANEL_HEIGHT):
            c = color(surf, x, y)
            if c not in (config.COLOR_BG, config.COLOR_STAGE_SHADOW):
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


@pytest.mark.parametrize("elapsed", [0.0, 60.0, 120.0, 180.0])
@pytest.mark.parametrize("lift", [0, 4, 8, 12])
def test_lift_moves_face_without_resizing(elapsed, lift):
    pygame.init()
    surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    surf.fill(config.COLOR_BG)
    s = Student()
    old_grade_at(s, elapsed)
    r = s.get_radius()
    s.draw(surf, lift)
    left, top, right, bottom = _face_bbox(surf)
    assert right - left == 2 * r and bottom - top == 2 * r
    assert top == CY - r - lift
    assert s.get_radius() == r
    # 발밑 그림자는 제자리, 가로가 lift 만큼 줄어든다
    shadow_y = CY + r + config.SHADOW_GAP + 1
    shadow_xs = [x for x in range(config.STAGE_X, config.STAGE_X + config.STAGE_WIDTH)
                 if color(surf, x, shadow_y) == config.COLOR_STAGE_SHADOW]
    assert len(shadow_xs) == int(r * config.SHADOW_WIDTH_RATIO) - lift - 2 * P
    pygame.quit()


def test_effects_never_change_radius(game):
    for k in (pygame.K_1, pygame.K_2, pygame.K_3):
        game.do_action(LEGACY_KEY_ACTIONS[k])
        for _ in range(60):
            game.update(FRAME)
            assert game.student.get_radius() == config.BASE_RADIUS


# ======================= E6 안내 깜빡임 =======================

def test_blink_toggles_every_05s(title_game):
    seq = []
    for t in (0.0, 0.25, 0.49, 0.5, 0.75, 0.99, 1.0, 1.49, 1.5):
        title_game.blink_time = t
        seq.append(title_game.is_blink_on())
    assert seq == [True, True, True, False, False, False, True, True, False]


def test_blink_frames(title_game):
    states = []
    for _ in range(120):
        states.append(title_game.is_blink_on())
        title_game.update(FRAME)
    changes = [i for i in range(1, len(states)) if states[i] != states[i - 1]]
    assert len(changes) == 3     # 2초 동안 0.5초마다 바뀜 (소수 오차로 ±1프레임 허용)
    assert all(abs(c - want) <= 1 for c, want in zip(changes, (30, 60, 90)))


def _hint_render(g, center_y):
    """안내 줄(화살표 포함 영역)의 화살표색 픽셀 수, 진한 글자색 수, 옅은 글자색 수."""
    pts = [(x, y) for x in range(150, 650) for y in range(center_y - 16, center_y + 16)]
    cols = [color(g.screen, *pt) for pt in pts]
    return (cols.count(config.COLOR_PINK_DARK), cols.count(config.COLOR_TEXT),
            cols.count(config.COLOR_HINT_DIM))


@pytest.mark.parametrize("ending", [None, config.ENDING_LEAVE, config.ENDING_TOP])
def test_hint_arrow_blinks_text_always_visible(title_game, ending):
    g = title_game
    y = config.START_HINT_Y
    if ending is not None:
        g.start_new_game()
        g.end_game(ending)
        y = config.RESTART_HINT_Y
    g.blink_time = 0.0
    g.draw()
    arrow_on, text_on, dim_on = _hint_render(g, y)
    g.blink_time = 0.5
    g.draw()
    arrow_off, text_off, dim_off = _hint_render(g, y)
    assert arrow_on > 0 and arrow_off == 0
    assert text_on > 0 and dim_off > 0          # 글자는 두 차례 모두 보인다
    assert text_off == 0


def test_title_time_does_not_flow_but_blink_does(title_game):
    g = title_game
    before = (g.student.elapsed, g.student.health, g.student.mental, g.auto_timer)
    for _ in range(90):
        g.update(FRAME)
    assert g.blink_time == pytest.approx(1.5)
    assert (g.student.elapsed, g.student.health, g.student.mental, g.auto_timer) == before


def test_ending_time_does_not_flow_but_blink_does(game):
    game.do_action(config.ACTION_STUDY)     # (G단위) 쿨타임 대신 자동 행동 시계를 본다
    game.update(0.2)
    game.end_game(config.ENDING_NORMAL)
    snap = (game.student.elapsed, game.student.health, game.student.mental,
            game.student.knowledge, game.auto_timer, game.ending, game.best_record)
    blink = game.blink_time
    for _ in range(120):
        game.update(FRAME)
    assert game.blink_time == pytest.approx(blink + 2.0)
    assert (game.student.elapsed, game.student.health, game.student.mental,
            game.student.knowledge, game.auto_timer, game.ending, game.best_record) == snap
    assert_effects_cleared(game)            # 엔딩 화면에서 연출이 다시 생기지 않음


# ======================= 규칙: 무시된 입력·초기화 =======================

@pytest.mark.parametrize("trigger", ["key", "click"])
def test_policy_input_makes_no_action_effects(game, trigger):
    """(G단위, 예전: 쿨타임 중 무시된 입력은 연출 없음) 키 1/2/3·방침 버튼은 방침만 바꾸므로
    파티클·팝업·점프·게이지 애니메이션이 생기지 않고 게이지도 그대로다. 눌림은 그 방침 버튼만."""
    game.do_action(config.ACTION_FEED)
    game.update(0.5)
    particles, popups = list(game.particles), list(game.popups)
    jump, lag = game.jump_timer, dict(game.gauge_lag)
    gauges = (game.student.health, game.student.mental, game.student.knowledge)
    for name, k in ((config.POLICY_STUDY_FOCUS, pygame.K_1), (config.POLICY_BALANCED, pygame.K_2),
                    (config.POLICY_REST_FOCUS, pygame.K_3)):
        if trigger == "key":
            game.handle_event(key(k))
        else:
            game.handle_event(click(game.buttons[name].rect.center))
        assert game.policy == name
        assert game.press_timers[name] == config.BUTTON_PRESS_TIME
    assert (game.particles, game.popups, game.jump_timer, game.gauge_lag) == \
        (particles, popups, jump, lag)
    assert (game.student.health, game.student.mental, game.student.knowledge) == gauges
    assert game.last_action == config.ACTION_FEED


def test_second_action_right_after_first_has_effects(game):
    """(G단위, 예전: 쿨타임 끝나기 직전 입력 무시) 쿨타임이 없어 바로 이은 행동도 연출이 생긴다."""
    game.do_action(config.ACTION_FEED)
    game.update(FRAME)
    game.do_action(config.ACTION_REST)
    assert config.ACTION_REST in game.press_timers
    assert len(game.particles) == 2 * config.PARTICLE_COUNT


def test_input_outside_buttons_and_other_states_no_effects(game, title_game):
    game.handle_event(click((5, 5)))
    game.handle_event(key(pygame.K_4))
    assert game.particles == [] and game.popups == [] and game.press_timers == {}
    for k in (pygame.K_1, pygame.K_2, pygame.K_3):
        title_game.handle_event(key(k))
    assert title_game.particles == [] and title_game.popups == []


def test_leave_by_natural_decay_clears_effects(game):
    game.update(0.9)
    game.do_action(config.ACTION_REST)
    game.student.health = 1
    game.update(0.05)
    assert game.state == config.STATE_PLAYING and game.particles and game.popups
    assert game.gauge_lag[config.GAUGE_MENTAL] != 0
    game.update(0.05)
    assert game.state == config.STATE_ENDING and game.ending == config.ENDING_LEAVE
    assert_effects_cleared(game)


@pytest.mark.parametrize("attr, value", [("health", 5), ("mental", 8), ("health", 3)])
def test_leave_by_study_action_clears_effects(game, attr, value):
    setattr(game.student, attr, value)
    game.student.knowledge = 40
    assert game.do_action(config.ACTION_STUDY) is True
    assert game.state == config.STATE_ENDING and game.ending == config.ENDING_LEAVE
    assert game.student.knowledge == 50
    assert game.best_record == 50
    assert_effects_cleared(game)
    game.draw()                       # 엔딩 화면 그리기 오류 없음


def test_graduation_clears_effects(game):
    """(L단위) 4학년에서 졸업 목표에 닿으면 졸업하고 연출이 비워진다(240초 -> 수석)."""
    reach_grade(game.student, 4)
    game.student.elapsed = 239.5
    game.do_action(config.ACTION_FEED)
    assert game.particles
    game.student.knowledge = config.GRADUATION_KNOWLEDGE
    game.update(0.5)
    assert game.state == config.STATE_ENDING and game.ending == config.ENDING_TOP
    assert_effects_cleared(game)


def test_restart_clears_everything_mid_effects(game):
    game.do_action(config.ACTION_STUDY)
    game.update(0.05)
    game.state = config.STATE_ENDING      # 연출이 남은 채 엔딩 화면이라고 가정해도
    game.handle_event(key(pygame.K_r))
    assert game.state == config.STATE_PLAYING
    assert_effects_cleared(game)
    assert game.press_timers == {}
    assert game.breath_time == 0


# ======================= 규칙: 연출은 결과에 영향 없음 =======================

def _script(kind):
    """프레임 번호 -> 이벤트 목록. kind 별로 다른 엔딩이 나오게 행동 순서를 정한다."""
    events = {}
    if kind == "leave":
        for f in range(10, SCRIPT_FRAMES, 62):
            events[f] = [("key", pygame.K_3)]
    elif kind == "balanced":
        order = [pygame.K_3, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_1, pygame.K_2]
        for i, f in enumerate(range(5, SCRIPT_FRAMES, 61)):
            events[f] = [("key", order[i % len(order)])]
    elif kind == "clicks":
        # (G단위) 방침 버튼을 호버·클릭한 뒤 행동한다(방침 배수가 공부 결과를 바꾼다)
        names = [config.POLICY_STUDY_FOCUS, config.POLICY_BALANCED, config.POLICY_REST_FOCUS,
                 config.POLICY_BALANCED]
        actions = [config.ACTION_STUDY, config.ACTION_FEED, config.ACTION_STUDY, config.ACTION_REST]
        for i, f in enumerate(range(3, SCRIPT_FRAMES, 45)):
            events[f] = [("move", names[i % 4]), ("click", names[i % 4]),
                         ("act", actions[i % 4])]
    return events


def _run(g, kind, with_draw):
    g.handle_event(key(pygame.K_RETURN))
    script = _script(kind)
    log = []
    for f in range(SCRIPT_FRAMES + 30):
        for what, arg in script.get(f, []):
            if what == "key":
                g.do_action(LEGACY_KEY_ACTIONS[arg])   # (G단위) 예전 행동 키 -> do_action
            elif what == "act":
                g.do_action(arg)
            elif what == "move":
                g.handle_event(motion(g.buttons[arg].rect.center))
            else:
                g.handle_event(click(g.buttons[arg].rect.center))
        g.update(FRAME)
        if with_draw and f % 20 == 0:
            g.draw()
        s = g.student
        log.append((s.health, s.mental, s.knowledge, round(s.elapsed, 9), round(g.auto_timer, 9),
                    g.state, g.ending, s.get_grade(), g.best_record, g.policy))
        if g.state == config.STATE_ENDING:
            break
    return log


@pytest.mark.parametrize("kind", ["leave", "balanced", "clicks"])
def test_effects_do_not_change_results(tmp_path, monkeypatch, kind):
    with_fx = Game(record_path=str(tmp_path / "fx.json"))
    log_fx = _run(with_fx, kind, with_draw=True)
    pygame.quit()

    monkeypatch.setattr(Game, "start_action_effects", lambda self, name, before: None)
    monkeypatch.setattr(Game, "update_effects", lambda self, dt: None)
    no_fx = Game(record_path=str(tmp_path / "nofx.json"))
    log_no = _run(no_fx, kind, with_draw=False)
    pygame.quit()

    assert log_fx == log_no
    assert log_fx[-1][5] == config.STATE_ENDING
    assert (tmp_path / "fx.json").read_text() == (tmp_path / "nofx.json").read_text()


def test_script_endings_cover_leave_and_graduation(tmp_path):
    endings = set()
    for kind in ("leave", "balanced"):
        g = Game(record_path=str(tmp_path / f"{kind}.json"))
        endings.add(_run(g, kind, with_draw=False)[-1][6])
        pygame.quit()
    assert config.ENDING_LEAVE in endings
    assert endings & {config.ENDING_TOP, config.ENDING_NORMAL, config.ENDING_BARELY}


def test_update_effects_and_draw_touch_no_game_state(game):
    game.do_action(config.ACTION_STUDY)
    s = game.student
    snap = (s.health, s.mental, s.knowledge, s.elapsed, s.decay_timer, game.auto_timer,
            game.policy, game.state, game.ending, game.best_record)
    game.update_effects(5.0)
    game.draw()
    game.start_action_effects(config.ACTION_FEED, game.get_gauge_values())
    game.spawn_particles(config.ACTION_REST)
    game.spawn_popups([("체력", 3)])
    game.clear_effects()
    assert (s.health, s.mental, s.knowledge, s.elapsed, s.decay_timer, game.auto_timer,
            game.policy, game.state, game.ending, game.best_record) == snap


# ======================= 연출 다듬기 (B단위 낮음 3건 수정) =======================
# 1) 파티클이 위쪽으로 가지 않아 수치 팝업 글자와 겹치지 않는다
# 2) 호버 밝은 색(COLOR_BUTTON_BRIGHT)이 평소 색과 한눈에 구분되고 글자도 잘 읽힌다
# 3) 마우스가 창 밖으로 나가면(WINDOWLEAVE) 호버 표시가 꺼진다

from button import sprite_size  # noqa: E402


def window_leave():
    return pygame.event.Event(pygame.WINDOWLEAVE, window=None)


def _popup_rect(g, popup):
    """draw_popup 과 같은 계산으로, 팝업 글자(그림자 포함)의 실제 글자 픽셀 사각형."""
    surf = g.popup_font.render(popup["text"], False, (0, 0, 0))
    glyph = surf.get_bounding_rect()
    rect = surf.get_rect()
    rect.center = (CX, round(popup["y"] - config.POPUP_RISE_SPEED * popup["age"]))
    g_rect = glyph.move(rect.topleft)
    return g_rect.unionall([g_rect.move(dx, dy) for dx, dy in config.POPUP_OUTLINE_OFFSETS])


def _particle_rect(g, p):
    """draw_particle 과 같은 계산으로, 파티클 스프라이트 전체 사각형(투명 칸 포함, 보수적)."""
    age = p["age"]
    cell = P
    if age >= p["life"] * config.PARTICLE_SHRINK_RATIO:
        cell = P // 2
    w, h = sprite_size(p["sprite"], cell)
    left = g.snap_to_pixel(p["x"] + p["vx"] * age - w / 2)
    top = g.snap_to_pixel(p["y"] + p["vy"] * age - h / 2)
    return pygame.Rect(left, top, w, h)


@pytest.mark.parametrize("k", [pygame.K_1, pygame.K_2, pygame.K_3])
@pytest.mark.parametrize("elapsed", [0.0, 45.0, 59.0, 60.0, 105.0, 120.0, 165.0, 180.0, 225.0,
                                     238.0])
def test_particles_never_overlap_popups_every_frame(game, k, elapsed):
    """1~4학년(시험 기간 포함) x 세 행동: 1/60초 프레임마다 팝업 글자(그림자 포함)와
    파티클 사각형이 겹치지 않는다. 깜빡여 숨은 프레임도 자리로는 검사(더 엄격)."""
    game.student.health, game.student.mental, game.student.knowledge = 60, 60, 10
    old_grade_at(game.student, elapsed)
    game.do_action(LEGACY_KEY_ACTIONS[k])
    assert game.popups and len(game.particles) == config.PARTICLE_COUNT
    frames = 0
    while game.popups and game.particles:
        prects = [_popup_rect(game, p) for p in game.popups]
        for part in game.particles:
            r = _particle_rect(game, part)
            for pop, pr in zip(game.popups, prects):
                assert not r.colliderect(pr), (elapsed, k, frames, pop["text"], r, pr)
        game.update(FRAME)
        frames += 1
        assert game.state == config.STATE_PLAYING
    assert frames >= 30          # 최소 0.5초 이상 함께 살아 있는 구간을 검사함


@pytest.mark.parametrize("k", [pygame.K_1, pygame.K_2, pygame.K_3])
@pytest.mark.parametrize("elapsed", [0.0, 60.0, 120.0, 180.0, 225.0])
def test_particles_and_popups_pixels_never_overlap(game, k, elapsed):
    """화면 픽셀로도 확인: 파티클만 그린 화면과 팝업만 그린 화면에서 바뀐 픽셀이 겹치지 않는다."""
    game.student.health, game.student.mental, game.student.knowledge = 60, 60, 10
    old_grade_at(game.student, elapsed)
    game.do_action(LEGACY_KEY_ACTIONS[k])
    for step in range(12):
        parts, pops = game.particles, game.popups
        game.particles, game.popups = [], []
        game.draw()
        base = game.screen.copy()
        game.particles = parts
        game.draw()
        only_p = set(_diff_pixels(base, game.screen))
        game.particles, game.popups = [], pops
        game.draw()
        only_q = set(_diff_pixels(base, game.screen))
        game.particles, game.popups = parts, pops
        assert only_p and only_q or step > 0
        assert not (only_p & only_q), (elapsed, k, step, sorted(only_p & only_q)[:5])
        for _ in range(4):
            game.update(FRAME)
        if not (game.particles and game.popups):
            break


def test_particle_directions_never_go_upward():
    """머리 위(팝업 자리)로 가는 방향 없음: 위로 가더라도 옆으로 두 배 넘게 가는 방향만.
    길이 대략 1, 왼쪽·오른쪽 같은 수."""
    dirs = config.PARTICLE_DIRECTIONS
    assert len(dirs) >= config.PARTICLE_COUNT
    for dx, dy in dirs:
        assert dy >= 0 or abs(dy) < abs(dx) * 0.5, (dx, dy)
        assert 0.9 <= (dx * dx + dy * dy) ** 0.5 <= 1.1, (dx, dy)
    used = dirs[:config.PARTICLE_COUNT]
    assert sum(1 for dx, _ in used if dx < 0) == sum(1 for dx, _ in used if dx > 0)


def _rgb_distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _contrast(a, b):
    """WCAG 명도 대비 비율."""
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    def lum(rgb):
        r, g, b = (lin(v) for v in rgb)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_hover_color_clearly_different_and_readable():
    """기준: 평소 색과 RGB 거리 >= 60 (이전 값은 약 43), 밝기(Y) 차 >= 30.
    호버 몸통 위 버튼 글자 대비 >= 7 (WCAG AAA), 호버가 쿨타임 회색과도 구분(거리 >= 40)."""
    normal, bright = config.COLOR_BUTTON, config.COLOR_BUTTON_BRIGHT
    assert bright == (200, 234, 255)
    assert _rgb_distance(normal, bright) >= 60

    def y(rgb):
        return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    assert y(bright) - y(normal) >= 30
    assert _contrast(config.COLOR_BUTTON_TEXT, bright) >= 7
    assert _contrast(config.COLOR_BUTTON_TEXT, bright) >= _contrast(config.COLOR_BUTTON_TEXT, normal)
    assert _rgb_distance(bright, config.COLOR_GRAY) >= 40
    assert all(0 <= v <= 255 for v in bright)


def test_hovered_button_text_drawn_on_bright_body(game):
    """실제 화면: 호버 버튼 안에 글자색 픽셀과 밝은 몸통 픽셀이 함께 있고 평소 몸통색은 없다."""
    name = HOVER_B
    game.handle_event(motion(game.buttons[name].rect.center))
    game.draw()
    r = game.buttons[name].rect
    cols = [color(game.screen, x, y) for x in range(r.left, r.right) for y in range(r.top, r.bottom)]
    assert cols.count(config.COLOR_BUTTON_BRIGHT) > cols.count(config.COLOR_BUTTON_TEXT) > 20
    assert config.COLOR_BUTTON not in cols


def test_window_leave_turns_hover_off_then_motion_turns_it_on(game):
    name = HOVER_A
    game.handle_event(motion(game.buttons[name].rect.center))
    game.draw()
    assert color(game.screen, *body_point(game, name)) == config.COLOR_BUTTON_BRIGHT
    game.handle_event(window_leave())
    assert game.mouse_pos is None
    game.draw()
    assert all(color(game.screen, *body_point(game, n)) == normal_color(game, n)
               for n in game.buttons)
    # 다시 들어와 다른 버튼 위로 움직이면 그 버튼만 호버
    game.handle_event(motion(game.buttons[HOVER_B].rect.center))
    assert game.mouse_pos == game.buttons[HOVER_B].rect.center
    game.draw()
    for n in game.buttons:
        want = config.COLOR_BUTTON_BRIGHT if n == HOVER_B else normal_color(game, n)
        assert color(game.screen, *body_point(game, n)) == want


def test_window_leave_has_no_other_effect(game, title_game):
    """WINDOWLEAVE 는 게이지·자동 행동 시계·방침·상태·연출을 바꾸지 않고, 타이틀·엔딩에서도 오류 없음."""
    game.do_action(config.ACTION_STUDY)
    snap = (effects_snapshot(game), game.auto_timer, game.policy, game.state, game.student.health,
            game.student.mental, game.student.knowledge)
    game.handle_event(window_leave())
    assert (effects_snapshot(game), game.auto_timer, game.policy, game.state, game.student.health,
            game.student.mental, game.student.knowledge) == snap
    title_game.handle_event(window_leave())
    assert title_game.state == config.STATE_TITLE and title_game.mouse_pos is None
    title_game.draw()
    game.end_game(config.ENDING_NORMAL)
    game.handle_event(window_leave())
    assert game.state == config.STATE_ENDING
    game.draw()


def test_window_leave_after_action_then_back(game):
    """(G단위, 예전: 쿨타임 중 창 밖) 행동 뒤 창 밖으로 나가면 호버가 꺼지고(회색 없음), 돌아오면 다시 켜진다."""
    game.handle_event(motion(game.buttons[HOVER_B].rect.center))
    game.do_action(config.ACTION_STUDY)
    game.handle_event(window_leave())
    game.update(0.5)
    game.draw()
    assert all(color(game.screen, *body_point(game, n)) == normal_color(game, n)
               for n in game.buttons)
    game.handle_event(motion(game.buttons[HOVER_B].rect.center))
    game.draw()
    assert color(game.screen, *body_point(game, HOVER_B)) == config.COLOR_BUTTON_BRIGHT
