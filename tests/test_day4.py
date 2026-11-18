"""4일차 검수: 캐릭터 그리기, 표정 변화(기능 7), 학년 타이머와 성장(기능 8), 상단 정보바."""

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

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAME_FILES = ["main.py", "game.py", "student.py", "button.py", "config.py"]
CX, CY = config.STUDENT_CENTER_X, config.STUDENT_CENTER_Y


@pytest.fixture
def game():
    g = Game()
    g.state = config.STATE_PLAYING
    yield g
    pygame.quit()


@pytest.fixture
def surface():
    pygame.init()
    s = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    yield s
    pygame.quit()


class RecordingFont:
    """render에 넘긴 글자를 기록하는 폰트 래퍼."""

    def __init__(self, font):
        self.font = font
        self.texts = []

    def render(self, text, *args, **kwargs):
        self.texts.append(text)
        return self.font.render(text, *args, **kwargs)


def student_at(elapsed, health=None, mental=None):
    s = Student()
    s.elapsed = elapsed
    if health is not None:
        s.health = health
    if mental is not None:
        s.mental = mental
    return s


def color(surf, x, y):
    return tuple(surf.get_at((x, y)))[:3]


def draw_on(surf, s):
    surf.fill(config.COLOR_BG)
    s.draw(surf)


# ======================= 기능 8: 학년·반지름 =======================

def test_config_grade_values():
    assert config.SECONDS_PER_GRADE == 60
    assert config.MAX_GRADE == 4
    assert config.TOTAL_SECONDS == 240
    assert (config.BASE_RADIUS, config.RADIUS_PER_GRADE) == (40, 10)
    assert config.GLASSES_GRADE == 3
    assert (config.MENTAL_SMILE_MIN, config.MENTAL_FLAT_MIN, config.LOW_GAUGE_LIMIT) == (60, 30, 30)
    assert config.ZERO_TIME == 0.0


@pytest.mark.parametrize("elapsed, grade, radius", [
    (0, 1, 40), (0.0, 1, 40), (59.9, 1, 40), (59.999, 1, 40),
    (60, 2, 50), (119.9, 2, 50),
    (120, 3, 60), (179.9, 3, 60),
    (180, 4, 70), (239.9, 4, 70), (240, 4, 70), (300, 4, 70), (10000, 4, 70),
])
def test_grade_and_radius(elapsed, grade, radius):
    s = student_at(elapsed)
    assert s.get_grade() == grade
    assert s.get_radius() == radius


def test_new_student_is_grade_1():
    s = Student()
    assert (s.elapsed, s.get_grade(), s.get_radius(), s.has_glasses()) == (0.0, 1, 40, False)


@pytest.mark.parametrize("frames, grade", [(3599, 1), (3600, 2), (7199, 2), (7200, 3),
                                           (10799, 3), (10800, 4), (14400, 4), (18000, 4)])
def test_grade_by_60fps_frames(frames, grade):
    s = Student()
    for _ in range(frames):
        s.update(1 / 60)
    assert s.get_grade() == grade


def test_grade_by_tenths_float_error():
    s = Student()
    for _ in range(600):
        s.update(0.1)
    assert s.get_grade() == 2
    assert s.get_grade_time_left() == 60


def test_game_update_advances_grade(game):
    for _ in range(3600):
        game.update(1 / 60)
    assert game.student.get_grade() == 2
    assert game.student.get_radius() == 50


def test_grade_does_not_advance_outside_playing(game):
    game.state = config.STATE_TITLE
    game.update(100.0)
    assert game.student.get_grade() == 1


@pytest.mark.parametrize("elapsed, glasses", [
    (0, False), (59.9, False), (60, False), (119.9, False),
    (120, True), (179.9, True), (180, True), (240, True), (300, True),
])
def test_glasses(elapsed, glasses):
    assert student_at(elapsed).has_glasses() is glasses


# ======================= 남은 시간 =======================

@pytest.mark.parametrize("elapsed, left", [
    (0, 60), (0.5, 60), (0.999, 60), (1, 59), (30, 30), (45, 15), (58.5, 2), (59, 1),
    (59.9, 1), (60, 60), (60.5, 60), (61, 59), (119.9, 1), (120, 60), (179.9, 1),
    (180, 60), (238.2, 2), (239.9, 1), (240, 0), (300, 0), (10000, 0),
])
def test_grade_time_left(elapsed, left):
    assert student_at(elapsed).get_grade_time_left() == left


def test_time_left_60fps_frames():
    s = Student()
    for _ in range(60):
        s.update(1 / 60)
    assert s.get_grade_time_left() == 59
    for _ in range(3600 - 60 - 1):
        s.update(1 / 60)
    assert s.get_grade_time_left() == 1
    s.update(1 / 60)
    assert s.get_grade_time_left() == 60
    assert s.get_grade() == 2


def test_time_left_always_in_range():
    s = Student()
    for _ in range(int(250 / 0.1)):
        s.update(0.1)
        left = s.get_grade_time_left()
        assert 0 <= left <= 60
        assert isinstance(left, int)


# ======================= 기능 7: 표정·다크서클 =======================

@pytest.mark.parametrize("mental, mouth", [
    (0, "cry"), (1, "cry"), (29, "cry"), (30, "flat"), (45, "flat"), (59, "flat"),
    (60, "smile"), (80, "smile"), (100, "smile"),
])
def test_mouth(mental, mouth):
    assert student_at(0, mental=mental).get_mouth() == mouth


def test_mouth_constants():
    assert (config.MOUTH_SMILE, config.MOUTH_FLAT, config.MOUTH_CRY) == ("smile", "flat", "cry")


@pytest.mark.parametrize("health, dark", [(0, True), (1, True), (29, True), (30, False),
                                          (31, False), (80, False), (100, False)])
def test_dark_circles(health, dark):
    assert student_at(0, health=health).has_dark_circles() is dark


def test_mouth_follows_mental_changes_through_actions():
    s = Student()
    assert s.get_mouth() == "smile"          # 80
    s.study()                                 # 72
    s.study()                                 # 64
    assert s.get_mouth() == "smile"
    s.study()                                 # 56
    assert s.get_mouth() == "flat"
    s.mental = 30
    s.update(1.0)                             # 29
    assert s.get_mouth() == "cry"
    s.rest()                                  # 49
    assert s.get_mouth() == "flat"


# ======================= 그리기 (픽셀) =======================

def face_extent(surf):
    """얼굴 중심 가로줄에서 오른쪽으로 배경이 아닌 픽셀이 이어진 길이."""
    x = CX
    while x < config.SCREEN_WIDTH and color(surf, x, CY) != config.COLOR_BG:
        x += 1
    return x - CX


def face_height(surf):
    y = CY
    while y < config.SCREEN_HEIGHT and color(surf, CX, y) != config.COLOR_BG:
        y += 1
    return y - CY


@pytest.mark.parametrize("elapsed, radius", [(0, 40), (60, 50), (120, 60), (180, 70)])
def test_face_drawn_with_grade_size(surface, elapsed, radius):
    s = student_at(elapsed)
    draw_on(surface, s)
    assert abs(face_extent(surface) - radius) <= 1
    assert abs(face_height(surface) - radius) <= 1
    # 얼굴 안쪽(중심 근처, 눈·입을 피한 곳)은 살구색
    assert color(surface, CX + radius // 2, CY) == config.COLOR_SKIN
    # 얼굴 밖은 배경
    assert color(surface, CX + radius + 2, CY) == config.COLOR_BG


def test_face_grows_each_grade_pixels(surface):
    extents = []
    for elapsed in (0, 60, 120, 180, 240, 300):
        draw_on(surface, student_at(elapsed))
        extents.append(face_extent(surface))
    assert extents[0] < extents[1] < extents[2] < extents[3]
    assert extents[3] == extents[4] == extents[5]


def test_done_criteria_game_face_grows_every_60s(game):
    """완료 기준: 60초마다 학년과 크기가 바뀜 (Game.update + Game.draw, 1/60초 프레임)."""
    sizes = []
    grades = []
    for _ in range(4):
        game.draw()
        sizes.append(face_extent(game.screen))
        grades.append(game.student.get_grade())
        # 체력·멘탈이 0이 되지 않게 유지(휴학은 5일차)
        game.student.health = game.student.mental = 100
        for _ in range(3600):
            game.update(1 / 60)
    assert grades == [1, 2, 3, 4]
    assert sizes[0] < sizes[1] < sizes[2] < sizes[3]
    for size, radius in zip(sizes, (40, 50, 60, 70)):
        assert abs(size - radius) <= 1


def eye_y(radius):
    return CY - int(radius * config.EYE_OFFSET_Y_RATIO)


@pytest.mark.parametrize("elapsed, glasses", [(0, False), (60, False), (120, True), (180, True)])
def test_glasses_pixels(surface, elapsed, glasses):
    """안경 가운데 다리(두 눈 사이, 눈 높이)는 안경이 있을 때만 검은색."""
    s = student_at(elapsed)
    draw_on(surface, s)
    bridge = color(surface, CX, eye_y(s.get_radius()))
    if glasses:
        assert bridge == config.COLOR_FACE_LINE
    else:
        assert bridge == config.COLOR_SKIN


def count_color(surf, target, radius):
    n = 0
    for x in range(CX - radius, CX + radius + 1):
        for y in range(CY - radius, CY + radius + 1):
            if color(surf, x, y) == target:
                n += 1
    return n


@pytest.mark.parametrize("elapsed", [0, 60, 120, 180])
@pytest.mark.parametrize("health, dark", [(29, True), (30, False), (1, True), (100, False)])
def test_dark_circle_pixels(surface, elapsed, health, dark):
    s = student_at(elapsed, health=health)
    draw_on(surface, s)
    n = count_color(surface, config.COLOR_DARK_CIRCLE, s.get_radius())
    assert (n > 0) is dark


def mouth_black_rows(surf, radius):
    """얼굴 가운데 세로줄의 아래쪽 절반(테두리 제외)에서 검은 픽셀의 y 목록."""
    rows = []
    for y in range(CY + 1, CY + radius - 4):
        if color(surf, CX, y) == config.COLOR_FACE_LINE:
            rows.append(y)
    return rows


@pytest.mark.parametrize("elapsed", [0, 60, 120, 180])
@pytest.mark.parametrize("mental, mouth", [(60, "smile"), (59, "flat"), (30, "flat"), (29, "cry")])
def test_mouth_pixels(surface, elapsed, mental, mouth):
    """입 가운데 점의 높이: 웃는 입은 입꼬리 줄보다 아래, 우는 입은 위, 일자 입은 그 줄."""
    s = student_at(elapsed, mental=mental)
    radius = s.get_radius()
    draw_on(surface, s)
    rows = mouth_black_rows(surface, radius)
    assert rows, "입이 그려지지 않음"
    mouth_y = CY + int(radius * config.MOUTH_OFFSET_Y_RATIO)
    height = int(radius * config.MOUTH_HEIGHT_RATIO)
    mean = sum(rows) / len(rows)
    if mouth == "smile":
        assert mean > mouth_y + height / 4
    elif mouth == "cry":
        assert mean < mouth_y - height / 4
    else:
        assert abs(mean - mouth_y) <= max(2, height / 4)


def test_mouth_pixels_differ_between_three(surface):
    images = []
    for mental in (80, 45, 10):
        draw_on(surface, student_at(0, mental=mental))
        images.append(pygame.image.tobytes(surface, "RGB"))
    assert len(set(images)) == 3


def test_draw_all_combinations_no_crash(surface):
    for elapsed in (0, 59.9, 60, 120, 180, 240, 300):
        for health in (0, 1, 29, 30, 100):
            for mental in (0, 29, 30, 59, 60, 100):
                draw_on(surface, student_at(elapsed, health=health, mental=mental))


def test_face_inside_student_area(game):
    """4학년(최대) 얼굴이 정보바·게이지·버튼 영역과 겹치지 않고 창 안에 있다."""
    r = 70
    face = pygame.Rect(CX - r, CY - r, 2 * r, 2 * r)
    assert face.top > config.INFO_BAR_HEIGHT
    assert face.bottom < config.BUTTON_Y
    assert face.left > config.GAUGE_X + config.BAR_WIDTH + config.BAR_BORDER_WIDTH
    assert face.right < config.SCREEN_WIDTH


# ======================= 상단 정보바 =======================

@pytest.mark.parametrize("elapsed, texts", [
    (0, ["1학년", "남은 시간 60초"]),
    (22, ["1학년", "남은 시간 38초"]),
    (59.9, ["1학년", "남은 시간 1초"]),
    (60, ["2학년", "남은 시간 60초"]),
    (130, ["3학년", "남은 시간 50초"]),
    (239.9, ["4학년", "남은 시간 1초"]),
    (240, ["4학년", "남은 시간 0초"]),
])
def test_info_bar_texts(game, elapsed, texts):
    rec = RecordingFont(game.font)
    game.font = rec
    game.student.elapsed = elapsed
    game.student.change_knowledge(120)
    game.draw()
    for t in texts + ["지식 120"]:
        assert t in rec.texts


def test_info_bar_via_draw_info_bar(game):
    rec = RecordingFont(game.font)
    game.font = rec
    game.draw_info_bar()
    assert rec.texts == ["1학년", "남은 시간 60초", "지식 0"]


def test_info_bar_updates_with_frames(game):
    rec = RecordingFont(game.font)
    game.font = rec
    for _ in range(60 * 22):
        game.update(1 / 60)
    game.draw()
    assert "남은 시간 38초" in rec.texts and "1학년" in rec.texts


def test_info_bar_positions(game):
    """정보바 배경이 맨 위에 있고, 왼쪽·가운데·오른쪽 구역에 글자(검정)가 있다."""
    game.draw()
    assert color(game.screen, config.SCREEN_WIDTH // 2, 2) == config.COLOR_INFO_BAR

    def has_dark(x0, x1):
        return any(sum(color(game.screen, x, y)) < 200
                   for x in range(x0, x1) for y in range(0, config.INFO_BAR_HEIGHT))

    w = config.SCREEN_WIDTH
    assert has_dark(0, w // 4)
    assert has_dark(w // 2 - 40, w // 2 + 40)
    assert has_dark(w * 3 // 4, w)


def test_knowledge_not_drawn_by_gauges_anymore(surface):
    font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
    rec = RecordingFont(font)
    Student().draw_gauges(surface, rec)
    assert rec.texts == [config.HEALTH_LABEL, config.MENTAL_LABEL]


# ======================= 숫자패드 =======================

@pytest.mark.parametrize("k", [pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP0,
                               pygame.K_KP_ENTER])
def test_numpad_no_action(game, k):
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0))
    s = game.student
    assert (s.health, s.mental, s.knowledge) == (80, 80, 0)
    assert game.is_cooling_down() is False
    assert game.running is True


# ======================= 정적 검사: 도형·import·매직 넘버·docstring =======================

ALLOWED_DRAW = {"circle", "rect", "line", "arc"}
ALLOWED_IMPORTS = {"pygame", "json", "sys", "os", "config", "button", "student", "game"}


def parse(name):
    return ast.parse((ROOT / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", GAME_FILES)
def test_only_allowed_draw_functions(name):
    for node in ast.walk(parse(name)):
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute)
                and node.value.attr == "draw" and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "pygame"):
            assert node.attr in ALLOWED_DRAW, f"{name}: pygame.draw.{node.attr}"
    src = (ROOT / name).read_text(encoding="utf-8")
    for bad in ("pygame.image.load", "pygame.mixer", "gfxdraw", "polygon", "ellipse"):
        assert bad not in src.replace("# ", "#"), f"{name}: {bad}"


@pytest.mark.parametrize("name", GAME_FILES)
def test_only_allowed_imports(name):
    for node in ast.walk(parse(name)):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] in ALLOWED_IMPORTS, a.name
        elif isinstance(node, ast.ImportFrom):
            assert node.module.split(".")[0] in ALLOWED_IMPORTS, node.module


@pytest.mark.parametrize("name", ["main.py", "game.py", "student.py", "button.py"])
def test_no_magic_numbers(name):
    """config.py 밖의 코드(주석·docstring 제외)에 숫자 리터럴이 없다."""
    found = []
    for node in ast.walk(parse(name)):
        if (isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
                and not isinstance(node.value, bool)):
            found.append((node.lineno, node.value))
    assert found == []


@pytest.mark.parametrize("name", GAME_FILES)
def test_docstrings(name):
    tree = parse(name)
    assert ast.get_docstring(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            assert ast.get_docstring(node), f"{name}:{node.lineno} {node.name}"


def test_student_draw_methods_exist():
    for m in ("get_grade", "get_grade_time_left", "get_radius", "get_mouth",
              "has_dark_circles", "has_glasses", "draw"):
        assert callable(getattr(Student, m))
