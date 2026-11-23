"""4일차 검수: 캐릭터 그리기, 표정 변화(기능 7), 학년과 성장(기능 8), 상단 정보바.

(L단위, 기획서 11절) 학년은 60초 타이머가 아니라 누적 지식으로 오른다. 학년별 크기·안경 검사는
지식으로 학년을 올려서 확인하고, 정보바 "남은 시간"은 "다음 학년까지 지식 n"으로 바뀌었다.
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


def student_at(knowledge, health=None, mental=None):
    """(L단위) 누적 지식 knowledge까지 공부한 제자: 지식을 넣고 진급 판정으로 학년을 맞춘다."""
    s = Student()
    s.knowledge = knowledge
    s.promote()
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
    # (L단위) SECONDS_PER_GRADE·TOTAL_SECONDS 삭제 -> 진급 목표(지식) 200/450/750, 졸업 1100
    assert config.GRADE_GOALS == [200, 450, 750]
    assert config.GRADUATION_KNOWLEDGE == 1100
    assert config.MAX_GRADE == 4
    assert config.CYCLE_SECONDS == 60
    assert (config.BASE_RADIUS, config.RADIUS_PER_GRADE) == (40, 10)
    assert config.GLASSES_GRADE == 3
    assert (config.MENTAL_SMILE_MIN, config.MENTAL_FLAT_MIN, config.LOW_GAUGE_LIMIT) == (60, 30, 30)
    assert config.ZERO_TIME == 0.0


@pytest.mark.parametrize("knowledge, grade, radius", [
    (0, 1, 40), (199, 1, 40),
    (200, 2, 50), (449, 2, 50),
    (450, 3, 60), (749, 3, 60),
    (750, 4, 70), (1099, 4, 70), (1100, 4, 70), (5000, 4, 70),
])
def test_grade_and_radius(knowledge, grade, radius):
    s = student_at(knowledge)
    assert s.get_grade() == grade
    assert s.get_radius() == radius


def test_new_student_is_grade_1():
    s = Student()
    assert (s.elapsed, s.get_grade(), s.get_radius(), s.has_glasses()) == (0.0, 1, 40, False)


@pytest.mark.parametrize("frames", [3599, 3600, 7200, 10800, 18000])
def test_time_alone_never_promotes(frames):
    """(L단위) 60fps로 오래 흘러도 지식이 그대로면 학년은 1학년 그대로다(예전: 60초마다 진급)."""
    s = Student()
    for _ in range(frames):
        s.health = s.mental = 100
        s.update(1 / 60)
    s.promote()
    assert s.get_grade() == 1


def test_grade_by_study_actions():
    """(L단위) 공부를 반복해 지식이 200에 닿는 순간 2학년이 된다(시험 기간 아닌 0초: +10씩)."""
    s = Student()
    for _ in range(19):
        s.study()
        s.health = s.mental = 100
        s.promote()
    assert (s.knowledge, s.get_grade()) == (190, 1)
    s.study()
    s.promote()
    assert (s.knowledge, s.get_grade()) == (200, 2)


def test_game_update_advances_grade(game):
    """Game.update 안의 진급 판정: 지식이 목표 이상이면 다음 update에서 학년이 오른다."""
    game.student.knowledge = 200
    game.update(1 / 60)
    assert game.student.get_grade() == 2
    assert game.student.get_radius() == 50


def test_grade_does_not_advance_outside_playing(game):
    game.state = config.STATE_TITLE
    game.student.knowledge = 800
    game.update(100.0)
    assert game.student.get_grade() == 1


@pytest.mark.parametrize("knowledge, glasses", [
    (0, False), (199, False), (200, False), (449, False),
    (450, True), (749, True), (750, True), (1100, True),
])
def test_glasses(knowledge, glasses):
    assert student_at(knowledge).has_glasses() is glasses


def test_glasses_stay_after_knowledge_drops():
    """(L단위) 학년은 내려가지 않으므로 지식이 줄어도 안경·크기는 그대로다."""
    s = student_at(450)
    s.rest()
    s.promote()
    assert s.knowledge == 448
    assert (s.get_grade(), s.has_glasses(), s.get_radius()) == (3, True, 60)


# (L단위) "남은 시간" 테스트(test_grade_time_left, test_time_left_60fps_frames,
# test_time_left_always_in_range)는 학년 시간 제한이 없어져 삭제했다(기획서 11절).
# 대신 다음 목표까지 남은 지식을 확인한다.
@pytest.mark.parametrize("knowledge, left", [
    (0, 200), (120, 80), (199, 1), (200, 250), (449, 1), (450, 300), (749, 1),
    (750, 350), (1099, 1),
])
def test_knowledge_to_goal(knowledge, left):
    assert student_at(knowledge).get_knowledge_to_goal() == left


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


@pytest.mark.parametrize("knowledge, radius", [(0, 40), (200, 50), (450, 60), (750, 70)])
def test_face_drawn_with_grade_size(surface, knowledge, radius):
    s = student_at(knowledge)
    draw_on(surface, s)
    assert abs(face_extent(surface) - radius) <= 1
    assert abs(face_height(surface) - radius) <= 1
    # 얼굴 안쪽(눈·안경·입을 피한 곳: 중심에서 3칸 아래)은 살구색 피부
    # (도트 재디자인: 3학년부터 CX + r/2 자리는 안경알이라 피부 점을 옮겼다)
    cell = radius // 10
    assert color(surface, CX, CY + 3 * cell + 1) == config.COLOR_SKIN
    # 얼굴 밖은 배경
    assert color(surface, CX + radius + 2, CY) == config.COLOR_BG


def test_face_grows_each_grade_pixels(surface):
    extents = []
    for knowledge in (0, 200, 450, 750, 1100, 3000):
        draw_on(surface, student_at(knowledge))
        extents.append(face_extent(surface))
    assert extents[0] < extents[1] < extents[2] < extents[3]
    assert extents[3] == extents[4] == extents[5]


def test_done_criteria_game_face_grows_every_grade(game):
    """완료 기준: 학년이 오를 때마다 크기가 바뀜 (Game.update + Game.draw, 1/60초 프레임).

    (L단위) 학년은 지식으로 오르므로, 매 구간마다 지식을 다음 목표까지 채운 뒤 1초를 흘린다.

    (J단위) 무대에 배경(하늘·잔디 등)이 깔려 게임 화면에서는 COLOR_BG로 얼굴 끝을 찾을 수
    없으므로, Game.draw()가 문제없이 도는 것을 확인한 뒤 그 순간의 game.student를
    크림색 빈 Surface에 그려 얼굴 폭을 잰다(의도: Game 시간 진행으로 60초마다 커짐).
    """
    sizes = []
    grades = []
    plain = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    for _ in range(4):
        game.draw()
        draw_on(plain, game.student)
        sizes.append(face_extent(plain))
        grades.append(game.student.get_grade())
        # 체력·멘탈이 0이 되지 않게 유지(휴학은 5일차)
        game.student.health = game.student.mental = 100
        if game.student.get_grade() < config.MAX_GRADE:
            game.student.knowledge = game.student.get_next_goal()
        for _ in range(60):
            game.update(1 / 60)
    assert grades == [1, 2, 3, 4]
    assert sizes[0] < sizes[1] < sizes[2] < sizes[3]
    for size, radius in zip(sizes, (40, 50, 60, 70)):
        assert abs(size - radius) <= 1


def eye_y(radius):
    """(도트 재디자인) 눈 높이: 얼굴 격자 20칸 중 9번째 행(0부터)의 세로 가운데. 칸 = 반지름 // 10."""
    cell = radius // 10
    return CY - radius + 9 * cell + cell // 2


@pytest.mark.parametrize("knowledge, glasses", [(0, False), (200, False), (450, True), (750, True)])
def test_glasses_pixels(surface, knowledge, glasses):
    """안경 가운데 다리(두 눈 사이, 눈 높이)는 안경이 있을 때만 남색(얼굴 선 색), 없으면 피부."""
    s = student_at(knowledge)
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


@pytest.mark.parametrize("knowledge", [0, 200, 450, 750])
@pytest.mark.parametrize("health, dark", [(29, True), (30, False), (1, True), (100, False)])
def test_dark_circle_pixels(surface, knowledge, health, dark):
    s = student_at(knowledge, health=health)
    draw_on(surface, s)
    n = count_color(surface, config.COLOR_DARK_CIRCLE, s.get_radius())
    assert (n > 0) is dark


def mouth_line_rows(surf, radius, col):
    """(도트 재디자인) 얼굴 격자 열 col(0~19)의 세로 가운데 x에서, 입이 있는 아래쪽
    (12행 ~ 18행: 안경·눈 아래, 턱 외곽선 위) 남색(얼굴 선) 픽셀의 y 목록."""
    cell = radius // 10
    x = CX - radius + col * cell + cell // 2
    rows = []
    for y in range(CY + 2 * cell, CY + radius - cell):
        if color(surf, x, y) == config.COLOR_FACE_LINE:
            rows.append(y)
    return rows


# 얼굴 격자의 입 열: 입꼬리(왼 7, 오른 12)와 가운데(10)
MOUTH_LEFT_COL, MOUTH_CENTER_COL, MOUTH_RIGHT_COL = 7, 10, 12


@pytest.mark.parametrize("knowledge", [0, 200, 450, 750])
@pytest.mark.parametrize("mental, mouth", [(60, "smile"), (59, "flat"), (30, "flat"), (29, "cry")])
def test_mouth_pixels(surface, knowledge, mental, mouth):
    """입 모양을 픽셀로 구분한다(도트 재디자인).

    웃는 입: 양 입꼬리가 가운데보다 위(입꼬리 행 < 가운데 행).
    우는 입: 양 입꼬리가 가운데보다 아래(입꼬리 행 > 가운데 행).
    일자 입: 8~11열이 같은 한 행이고 입꼬리 열(7·12)에는 선이 없다.
    """
    s = student_at(knowledge, mental=mental)
    radius = s.get_radius()
    draw_on(surface, s)
    center = mouth_line_rows(surface, radius, MOUTH_CENTER_COL)
    left = mouth_line_rows(surface, radius, MOUTH_LEFT_COL)
    right = mouth_line_rows(surface, radius, MOUTH_RIGHT_COL)
    assert center, "입이 그려지지 않음"
    if mouth == "smile":
        assert left and right
        assert max(left) < min(center) and max(right) < min(center)
    elif mouth == "cry":
        assert left and right
        assert min(left) > max(center) and min(right) > max(center)
    else:
        assert left == [] and right == []
        rows = [mouth_line_rows(surface, radius, col) for col in (8, 9, 10, 11)]
        assert all(r == rows[0] for r in rows)
        cell = radius // 10
        assert len(rows[0]) == cell   # 도트 1칸 두께의 한 행


def test_mouth_pixels_differ_between_three(surface):
    images = []
    for mental in (80, 45, 10):
        draw_on(surface, student_at(0, mental=mental))
        images.append(pygame.image.tobytes(surface, "RGB"))
    assert len(set(images)) == 3


def test_draw_all_combinations_no_crash(surface):
    for knowledge in (0, 199, 200, 450, 750, 1100, 3000):
        for health in (0, 1, 29, 30, 100):
            for mental in (0, 29, 30, 59, 60, 100):
                draw_on(surface, student_at(knowledge, health=health, mental=mental))


def test_face_inside_student_area(game):
    """4학년(최대) 얼굴이 정보바·게이지·버튼 영역과 겹치지 않고 창 안에 있다."""
    r = 70
    face = pygame.Rect(CX - r, CY - r, 2 * r, 2 * r)
    assert face.top > config.INFO_BAR_HEIGHT
    assert face.bottom < config.BUTTON_Y
    assert face.left > config.GAUGE_X + config.BAR_WIDTH + config.PIXEL_SIZE
    # (도트 재디자인) 제자 무대 패널 안쪽(외곽선 1칸 안)에 들어간다
    stage = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH, config.PANEL_HEIGHT)
    assert stage.inflate(-2 * config.PIXEL_SIZE, -2 * config.PIXEL_SIZE).contains(face)
    assert face.right < config.SCREEN_WIDTH


# ======================= 상단 정보바 =======================

@pytest.mark.parametrize("knowledge, texts", [
    # (L단위) "남은 시간 n초" -> "다음 학년까지 지식 n" / 4학년 "졸업까지 지식 n" (기획서 11절)
    (0, ["1학년", "다음 학년까지 지식 200"]),
    (120, ["1학년", "다음 학년까지 지식 80"]),
    (199, ["1학년", "다음 학년까지 지식 1"]),
    (200, ["2학년", "다음 학년까지 지식 250"]),
    (500, ["3학년", "다음 학년까지 지식 250"]),
    (750, ["4학년", "졸업까지 지식 350"]),
    (1099, ["4학년", "졸업까지 지식 1"]),
])
def test_info_bar_texts(game, knowledge, texts):
    rec = RecordingFont(game.font)
    game.font = rec
    game.student.change_knowledge(knowledge)
    game.check_promotion()
    game.draw()
    for t in texts + [f"지식 {knowledge}"]:
        assert t in rec.texts


def test_info_bar_via_draw_info_bar(game):
    rec = RecordingFont(game.font)
    game.font = rec
    game.draw_info_bar()
    # (H단위) 연구비 추가, (L단위) 남은 시간 -> 다음 학년까지 지식 (기획서 11절 화면)
    assert rec.texts == ["1학년", "다음 학년까지 지식 200", "지식 0", "연구비 0"]


def test_info_bar_updates_with_frames(game):
    """(L단위) 시간이 흐르면 정보바 대신 경과 시간 글자가 바뀐다: 22초 -> "경과 0분 22초"."""
    rec = RecordingFont(game.font)
    game.font = rec
    for _ in range(60 * 22):
        game.student.health = game.student.mental = 100
        game.update(1 / 60)
    game.draw()
    assert "경과 0분 22초" in rec.texts and "1학년" in rec.texts


def test_info_bar_positions(game):
    """정보바 상자(민트)가 맨 위에 있고, 왼쪽·가운데·오른쪽 구역에 글자(남색)가 있다.

    (도트 재디자인) 정보바 외곽선도 남색이라, 외곽선·위아래 줄을 뺀 상자 안쪽에서만 글자색을 찾는다.
    """
    game.draw()
    p = config.PIXEL_SIZE
    assert color(game.screen, config.INFO_BOX_X + 2 * p, config.INFO_TEXT_CENTER_Y)         == config.COLOR_INFO_BAR
    assert config.INFO_BOX_Y + config.INFO_BOX_HEIGHT + p <= config.INFO_BAR_HEIGHT
    y0 = config.INFO_BOX_Y + 2 * p
    y1 = config.INFO_BOX_Y + config.INFO_BOX_HEIGHT - 2 * p
    x_min = config.INFO_BOX_X + 2 * p
    x_max = config.INFO_BOX_X + config.INFO_BOX_WIDTH - 2 * p

    def has_text(x0, x1):
        return any(color(game.screen, x, y) == config.COLOR_TEXT
                   for x in range(max(x0, x_min), min(x1, x_max)) for y in range(y0, y1))

    w = config.SCREEN_WIDTH
    assert has_text(0, w // 4)
    assert has_text(w // 2 - 40, w // 2 + 40)
    assert has_text(w * 3 // 4, w)


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
    assert game.last_action is None   # (G단위) 쿨타임 대신: 아무 행동도 실행되지 않음
    assert game.running is True


# ======================= 정적 검사: 도형·import·매직 넘버·docstring =======================

ALLOWED_DRAW = {"circle", "rect", "line", "arc"}
ALLOWED_IMPORTS = {"pygame", "json", "sys", "os", "random", "config", "button", "student", "game"}


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
    for m in ("get_grade", "get_next_goal", "get_radius", "get_mouth",
              "has_dark_circles", "has_glasses", "draw"):
        assert callable(getattr(Student, m))
