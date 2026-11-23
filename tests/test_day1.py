"""1일차 검수: 창과 메인 루프, 클래스 뼈대, config 상수."""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import ast  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_FILES = ["main.py", "config.py", "student.py", "button.py", "game.py"]
ALLOWED_IMPORTS = {"pygame", "json", "sys", "os", "random", "config", "student", "button", "game"}


@pytest.fixture
def game():
    """dummy 드라이버로 Game을 만들고 끝나면 pygame을 정리한다."""
    g = Game()
    yield g
    pygame.quit()


def _parse(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return ast.parse(f.read())


# ---------------- 창과 종료 ----------------

def test_window_size_800x600(game):
    assert game.screen.get_size() == (800, 600)
    assert pygame.display.get_surface().get_size() == (800, 600)


def test_running_true_at_start(game):
    assert game.running is True


def test_esc_stops_running(game):
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert game.running is False


def test_quit_event_stops_running(game):
    game.handle_event(pygame.event.Event(pygame.QUIT))
    assert game.running is False


@pytest.mark.parametrize(
    "key",
    [pygame.K_a, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_r,
     pygame.K_RETURN, pygame.K_SPACE, pygame.K_q],
)
def test_other_keys_do_not_quit(game, key):
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
    assert game.running is True


def test_other_events_do_not_quit(game):
    game.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_ESCAPE))
    game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(10, 10), button=1))
    assert game.running is True


def test_run_exits_on_esc_event():
    """실제 run() 루프에 ESC 이벤트를 넣으면 SystemExit으로 끝난다."""
    g = Game()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    with pytest.raises(SystemExit):
        g.run()
    assert g.running is False


def test_run_exits_on_quit_event():
    g = Game()
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    with pytest.raises(SystemExit):
        g.run()
    assert g.running is False


def test_draw_does_not_crash(game):
    game.update(1 / 60)
    game.draw()


# ---------------- Student 시작값 ----------------

def test_student_start_values():
    s = Student()
    assert (s.health, s.mental, s.knowledge) == (80, 80, 0)


# ---------------- config 상수 (jeja-spec 표) ----------------

@pytest.mark.parametrize(
    "name, expected",
    [
        ("SCREEN_WIDTH", 800), ("SCREEN_HEIGHT", 600),
        # L단위(기획서 11절): 학년 60초·판 240초 제한 삭제 -> 60초 주기(CYCLE_SECONDS)
        ("CYCLE_SECONDS", 60), ("EXAM_SECONDS", 15),
        ("FONT_NAME", "malgungothic"),
        ("GAUGE_MIN", 0), ("GAUGE_MAX", 100),
        ("HEALTH_START", 80), ("MENTAL_START", 80), ("KNOWLEDGE_START", 0),
        ("HEALTH_DECAY_PER_SEC", 1), ("MENTAL_DECAY_PER_SEC", 1),
        ("MENTAL_DECAY_PER_SEC_EXAM", 2), ("LOW_GAUGE_LIMIT", 30),
        ("FEED_HEALTH", 20), ("REST_MENTAL", 20), ("REST_KNOWLEDGE", -2),
        ("STUDY_HEALTH", -5), ("STUDY_MENTAL", -8),
        ("STUDY_KNOWLEDGE", 10), ("STUDY_KNOWLEDGE_EXAM", 20),
        # G단위: ACTION_COOLDOWN(1초)은 기획서 10절로 삭제. AUTO_ACTION_INTERVAL 2.0은 test_idle_g.py에서 확인
        ("MENTAL_SMILE_MIN", 60), ("MENTAL_FLAT_MIN", 30),
        ("BASE_RADIUS", 40), ("RADIUS_PER_GRADE", 10), ("GLASSES_GRADE", 3),
        ("MAX_GRADE", 4),
        # 졸업 기준: E단위 500/300 -> 700/450 -> K단위 1000/750 -> L단위(기획서 11절) 걸린 시간 240/360초
        # -> 11절 A안 밸런스(2026-11-23) 200/360초
        ("TOP_GRADUATE_SECONDS", 200), ("NORMAL_GRADUATE_SECONDS", 360),

        ("GRADUATION_KNOWLEDGE", 1100), ("GRADE_GOALS", [200, 450, 750]),
        ("RECORD_FILENAME", "record.json"),
    ],
)
def test_config_constant(name, expected):
    assert getattr(config, name) == expected


def test_radius_per_grade_formula():
    radii = [config.BASE_RADIUS + (g - 1) * config.RADIUS_PER_GRADE for g in range(1, 5)]
    assert radii == [40, 50, 60, 70]


def test_ending_names():
    assert config.ENDING_LEAVE == "휴학"
    assert config.ENDING_TOP == "수석 졸업"
    assert config.ENDING_NORMAL == "무사 졸업"
    assert config.ENDING_BARELY == "아슬아슬 졸업"


# ---------------- 구조와 규칙 ----------------

def test_game_files_exist():
    for name in GAME_FILES:
        assert os.path.isfile(os.path.join(ROOT, name)), name


def test_only_three_classes_in_expected_files():
    found = {}
    for name in os.listdir(ROOT):
        if name.endswith(".py"):
            for node in ast.walk(_parse(name)):
                if isinstance(node, ast.ClassDef):
                    found[node.name] = name
    assert found == {"Student": "student.py", "Button": "button.py", "Game": "game.py"}


@pytest.mark.parametrize("name", GAME_FILES)
def test_korean_docstrings(name):
    tree = _parse(name)
    targets = [tree] + [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for node in targets:
        doc = ast.get_docstring(node)
        label = getattr(node, "name", name)
        assert doc, f"{name}:{label} docstring 없음"
        assert any("가" <= ch <= "힣" for ch in doc), f"{name}:{label} 한국어 아님"


@pytest.mark.parametrize("name", GAME_FILES)
def test_only_allowed_imports(name):
    for node in ast.walk(_parse(name)):
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods = [(node.module or "").split(".")[0]]
        else:
            continue
        for m in mods:
            assert m in ALLOWED_IMPORTS, f"{name}: 금지 import {m}"


@pytest.mark.parametrize("name", GAME_FILES)
def test_no_images_sounds_or_default_font(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        src = f.read()
    for banned in ["pygame.image", "pygame.mixer", "Font(None", ".png", ".jpg", ".wav", ".mp3", ".ogg"]:
        assert banned not in src, f"{name}: {banned} 사용"


@pytest.mark.parametrize("name", ["main.py", "student.py", "button.py", "game.py"])
def test_no_magic_numbers_outside_config(name):
    """config.py 밖에서는 0, 1을 제외한 숫자 리터럴을 쓰지 않는다."""
    bad = []
    for node in ast.walk(_parse(name)):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if node.value not in (0, 1):
                bad.append((node.lineno, node.value))
    assert not bad, f"{name}: 매직 넘버 {bad}"
