"""검수 단위 A: 도트(픽셀) 그래픽 재디자인 (기획서 8절, jeja-spec 13절 도트 스타일 표).

- 게임 로직·수치 불변 (main 브랜치와 비교)
- config.py 한글 문자열 인코딩
- 도트 스타일 표 대조: PIXEL_SIZE 4, antialias=False, 30 미만 빨강/이상 초록, 쿨타임 회색,
  얼굴 지름 = 2 x 반지름(학년별 실측), 표정·다크서클·안경
- 도형 제한, 이미지·사운드 없음, 클래스 3개
- 화면 요소 겹침·글자 넘침
"""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import ast  # noqa: E402
import importlib.util  # noqa: E402
import pathlib  # noqa: E402
import subprocess  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
from button import Button, draw_cut_rect, draw_pixel_box, render_text, sprite_size  # noqa: E402
from conftest import press  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAME_FILES = ["main.py", "game.py", "student.py", "button.py", "config.py"]
CX, CY = config.STUDENT_CENTER_X, config.STUDENT_CENTER_Y
P = config.PIXEL_SIZE


# ======================= 공통 도우미 =======================

def color(surf, x, y):
    return tuple(surf.get_at((x, y)))[:3]


# 비교 기준: 화면 연출을 넣기 전의 main (PR #1 merge 커밋).
# "main" 이름으로 비교하면 연출이 main 에 합쳐진 뒤 기준 자체가 바뀌어 버린다.
BASELINE_REF = "9175b41"


def git_show(path):
    """연출 전 기준 커밋의 파일 내용을 돌려준다. git을 쓸 수 없으면 테스트를 건너뛴다."""
    try:
        out = subprocess.run(["git", "show", f"{BASELINE_REF}:{path}"], cwd=ROOT,
                             capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("기준 커밋을 읽을 수 없음")
    return out.stdout.decode("utf-8")


def load_main_config(tmp_path):
    src = git_show("config.py")
    path = tmp_path / "config_main.py"
    path.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("config_main", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecordingFont:
    """render 호출의 (글자, antialias) 를 기록하는 폰트 래퍼."""

    def __init__(self, font):
        self.font = font
        self.calls = []

    def render(self, text, antialias, *args, **kwargs):
        self.calls.append((text, antialias))
        return self.font.render(text, antialias, *args, **kwargs)

    def size(self, text):
        return self.font.size(text)


@pytest.fixture
def game():
    g = Game()
    yield g
    pygame.quit()


@pytest.fixture
def surface():
    pygame.init()
    s = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    yield s
    pygame.quit()


@pytest.fixture
def font():
    pygame.init()
    f = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
    yield f
    pygame.quit()


# ======================= 1. 게임 로직·수치 불변 =======================

# 기획서 1~9절(게임 규칙)에 해당하는 config 상수: main 과 같아야 한다
GAME_CONSTANTS = [
    "SCREEN_WIDTH", "SCREEN_HEIGHT", "FPS", "WINDOW_TITLE", "FONT_NAME", "MS_PER_SECOND",
    "STATE_TITLE", "STATE_PLAYING", "STATE_ENDING", "START_STATE",
    "SECONDS_PER_GRADE", "MAX_GRADE", "TOTAL_SECONDS", "EXAM_SECONDS", "FIRST_GRADE", "ZERO_TIME",
    "GAUGE_MIN", "GAUGE_MAX", "HEALTH_START", "MENTAL_START", "KNOWLEDGE_START",
    "HEALTH_DECAY_PER_SEC", "MENTAL_DECAY_PER_SEC", "MENTAL_DECAY_PER_SEC_EXAM",
    "DECAY_INTERVAL", "TIME_EPSILON", "LOW_GAUGE_LIMIT",
    "FEED_HEALTH", "REST_MENTAL", "REST_KNOWLEDGE", "STUDY_HEALTH", "STUDY_MENTAL",
    "STUDY_KNOWLEDGE", "STUDY_KNOWLEDGE_EXAM", "ACTION_COOLDOWN",
    "MENTAL_SMILE_MIN", "MENTAL_FLAT_MIN", "BASE_RADIUS", "RADIUS_PER_GRADE", "GLASSES_GRADE",
    "MOUTH_SMILE", "MOUTH_FLAT", "MOUTH_CRY",
    "TOP_GRADUATE_KNOWLEDGE", "NORMAL_GRADUATE_KNOWLEDGE",
    "ENDING_LEAVE", "ENDING_TOP", "ENDING_NORMAL", "ENDING_BARELY",
    "RECORD_FILENAME", "RECORD_KEY", "RECORD_ENCODING", "BEST_RECORD_START",
    "ACTION_FEED", "ACTION_REST", "ACTION_STUDY",
]

# 화면 글자 (기획서·jeja-spec 의 문구) : main 과도 같아야 한다
UI_TEXTS = [
    "HEALTH_LABEL", "MENTAL_LABEL", "KNOWLEDGE_LABEL", "GRADE_TEXT", "TIME_LEFT_TEXT",
    "KNOWLEDGE_TEXT", "FEED_BUTTON_TEXT", "REST_BUTTON_TEXT", "STUDY_BUTTON_TEXT",
    "COOLDOWN_HINT_TEXT", "EXAM_BANNER_TEXT", "TITLE_TEXT", "BEST_RECORD_TEXT",
    "START_HINT_TEXT", "ENDING_KNOWLEDGE_TEXT", "RESTART_HINT_TEXT",
]


def test_game_constants_same_as_main(tmp_path):
    main_cfg = load_main_config(tmp_path)
    diff = [(n, getattr(main_cfg, n), getattr(config, n)) for n in GAME_CONSTANTS + UI_TEXTS
            if getattr(main_cfg, n) != getattr(config, n)]
    assert diff == []
    # get_base_dir (record.json 위치) 도 그대로 (docstring 제외 코드 비교)
    old = _functions(git_show("config.py"))["get_base_dir"]
    new = _functions((ROOT / "config.py").read_text(encoding="utf-8"))["get_base_dir"]
    assert _strip_docstrings(old) == _strip_docstrings(new)


def _strip_docstrings(node):
    """함수 본문에서 docstring 을 빼고 ast.dump 를 돌려준다(설명 문구 수정은 로직 변경이 아님)."""
    node = ast.parse(ast.unparse(node)).body[0]
    for sub in ast.walk(node):
        if isinstance(sub, (ast.FunctionDef, ast.ClassDef)) and ast.get_docstring(sub):
            sub.body = sub.body[1:]
    return ast.dump(node)


def _functions(src):
    """모듈의 최상위 함수와 클래스 메서드를 {이름: ast 노드} 로 돌려준다."""
    tree = ast.parse(src)
    result = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            result[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    result[f"{node.name}.{item.name}"] = item
    return result


def _is_drawing(name):
    short = name.split(".")[-1]
    return short.startswith("draw") or short in ("make_backdrop", "get_cell_size",
                                                 "render_text")


# (화면 연출 B 단위) 로직 함수에 허용되는 "연출 연결" 문장. 이 문장만 빼면 main 과 같아야 한다.
EFFECT_HOOKS = {
    "Game.reset_round": ["self.clear_effects()"],
    "Game.end_game": ["self.clear_effects()"],
    "Game.do_action": ["before = self.get_gauge_values()",
                       "self.start_action_effects(name, before)"],
    "Game.update": ["self.update_effects(dt)"],
}
MOUSEMOTION_TEST = "event.type == pygame.MOUSEMOTION"
MOUSEMOTION_BODY = ["self.mouse_pos = event.pos"]
# (연출 다듬기) 창 밖으로 나가면 호버를 끄는 분기도 허용. 조건·본문이 정확히 이것이어야 한다.
WINDOWLEAVE_TEST = "event.type == pygame.WINDOWLEAVE"
WINDOWLEAVE_BODY = ["self.mouse_pos = None"]
# (C단위 랜덤 이벤트) 대화창 상태 분기도 허용. 조건·본문이 정확히 이것이어야 한다.
EVENT_STATE_TEST = "self.state == config.STATE_EVENT"
NL = chr(10)  # 줄바꿈 문자
EVENT_STATE_BODY = [ast.unparse(ast.parse(NL.join([
    "if event.type == pygame.KEYDOWN and event.key in CHOICE_KEYS:",
    "    self.choose_option(CHOICE_KEYS[event.key])",
    "elif event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_LEFT:",
    "    for index, button in enumerate(self.choice_buttons):",
    "        if button.is_clicked(event.pos):",
    "            self.choose_option(index)",
    "            break",
])))]
ROLL_AFTER_ENDING = NL.join(["if not self.check_ending():", "    self.roll_event()"])
ALLOWED_ELIF_BRANCHES = [(MOUSEMOTION_TEST, MOUSEMOTION_BODY),
                         (WINDOWLEAVE_TEST, WINDOWLEAVE_BODY),
                         (EVENT_STATE_TEST, EVENT_STATE_BODY)]

# (C단위 랜덤 이벤트) 로직 함수에 허용되는 이벤트 연결. 이것만 되돌리면 기준 커밋과 같아야 한다.
# - strip: 함수 소스에서 정확히 한 번씩 지울 글자(특성 보정 덧셈)
# - remove: 정확히 한 번씩 있는 문장을 지운다
# - replace: (새 문장, 기준 문장) — 새 문장이 정확히 한 번 있어야 하고 기준 문장으로 되돌린다
EVENT_HOOKS = {
    "Student.__init__": {"remove": [
        "self.traits = []", "self.looks = []", "self.flags = set()",
        "self.seen_events = set()",
        # (D 단위) 시작값 상수를 NO_CHANGE -> EVENT_COUNT_START 로 바꿈(값 0 동일)
        "self.event_counts = {grade: config.EVENT_COUNT_START for grade in config.ALL_GRADES}"]},
    "Student.feed": {"strip": [" + self.get_trait_bonus(config.BONUS_FEED_HEALTH)"]},
    "Student.rest": {"strip": [" + self.get_trait_bonus(config.BONUS_REST_MENTAL)",
                               " + self.get_trait_bonus(config.BONUS_REST_HEALTH)"],
                     "remove": ["self.change_health(config.REST_HEALTH)"]},
    "Student.study": {"strip": [" + self.get_trait_bonus(config.BONUS_STUDY_HEALTH)"]},
    "Game.reset_round": {"remove": ["self.current_event = None"]},
    "Game.end_game": {"remove": ["self.current_event = None"]},
    "Game.do_action": {"replace": [(ROLL_AFTER_ENDING, "self.check_ending()")]},
}


def _remove_event_hooks(fname, node):
    """node(함수)에서 허용된 이벤트 연결(EVENT_HOOKS)을 되돌린 사본을 돌려준다.

    되돌릴 것이 정확히 한 번 있지 않으면 AssertionError(빠뜨렸거나 다른 곳에 또 넣음).
    """
    spec = EVENT_HOOKS.get(fname)
    if spec is None:
        return node
    src = ast.unparse(node)
    for text in spec.get("strip", []):
        assert src.count(text) == 1, f"{fname}: '{text}' 가 정확히 한 번 있어야 함"
        src = src.replace(text, "")
    node = ast.parse(src).body[0]
    for stmt in spec.get("remove", []):
        lines = [ast.unparse(s) for s in node.body]
        assert lines.count(stmt) == 1, f"{fname}: '{stmt}' 가 정확히 한 번 있어야 함"
        node.body.pop(lines.index(stmt))
    for new_stmt, old_stmt in spec.get("replace", []):
        lines = [ast.unparse(s) for s in node.body]
        assert lines.count(new_stmt) == 1, f"{fname}: '{new_stmt}' 가 정확히 한 번 있어야 함"
        node.body[lines.index(new_stmt)] = ast.parse(old_stmt).body[0]
    return node


def _remove_effect_hooks(fname, node):
    """node(함수)에서 허용된 연출 연결 문장을 하나씩만 지운 사본을 돌려준다.

    지울 문장이 없으면(개발팀이 연결을 빠뜨림) AssertionError.
    handle_event 의 MOUSEMOTION elif 분기는 if-elif 사슬에서 그 분기만 걷어 낸다.
    """
    node = ast.parse(ast.unparse(node)).body[0]
    if fname == "Game.update":
        # update_effects 는 맨 끝(게임 진행 if 블록 뒤, if 밖)에 있어야 한다
        assert ast.unparse(node.body[-1]) == "self.update_effects(dt)"
    for stmt in EFFECT_HOOKS.get(fname, []):
        lines = [ast.unparse(s) for s in node.body]
        assert lines.count(stmt) == 1, f"{fname}: '{stmt}' 가 함수 본문에 정확히 한 번 있어야 함"
        node.body.pop(lines.index(stmt))
    if fname == "Game.handle_event":
        for test, body in ALLOWED_ELIF_BRANCHES:
            found = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.If) and len(sub.orelse) == 1 and isinstance(sub.orelse[0], ast.If):
                    branch = sub.orelse[0]
                    if ast.unparse(branch.test) == test:
                        found.append((sub, branch))
            assert len(found) == 1, f"handle_event: '{test}' elif 분기가 정확히 1개여야 함"
            sub, branch = found[0]
            assert [ast.unparse(s) for s in branch.body] == body, f"'{test}' 분기 본문이 다름"
            sub.orelse = branch.orelse
    return node


@pytest.mark.parametrize("name", ["student.py", "game.py", "button.py"])
def test_logic_functions_unchanged_from_main(name):
    """그리기 외 함수(게이지·쿨타임·학년·엔딩·기록·입력)는 main 과 docstring 빼고 똑같다.

    (B 단위) 단, reset_round/end_game 의 clear_effects, do_action 의 before 저장과
    start_action_effects, handle_event 의 MOUSEMOTION·WINDOWLEAVE 분기, update 끝 update_effects 는 허용.
    (C 단위) EVENT_HOOKS 의 이벤트 연결(특성 보정 덧셈, REST_HEALTH, Student 성장 속성,
    current_event=None, do_action 끝 roll_event)과 handle_event 의 STATE_EVENT 분기도 허용.
    """
    old =_functions(git_show(name))
    new = _functions((ROOT / name).read_text(encoding="utf-8"))
    changed = []
    for fname, node in old.items():
        if _is_drawing(fname) or fname == "Game.__init__":
            continue
        assert fname in new, f"{name}: {fname} 이 사라짐"
        new_node = _remove_event_hooks(fname, new[fname])
        if name == "game.py":
            new_node = _remove_effect_hooks(fname, new_node)
        if _strip_docstrings(node) != _strip_docstrings(new_node):
            changed.append(fname)
    assert changed == []


def test_do_action_effects_start_after_action_before_ending_check():
    """do_action: before 저장은 행동 전, start_action_effects 는 쿨타임 설정 뒤·check_ending 앞."""
    node = _functions((ROOT / "game.py").read_text(encoding="utf-8"))["Game.do_action"]
    lines = [ast.unparse(s) for s in node.body]
    i_before = lines.index("before = self.get_gauge_values()")
    i_if = next(i for i, s in enumerate(lines) if s.startswith("if name == config.ACTION_FEED"))
    i_cool = lines.index("self.cooldown = config.ACTION_COOLDOWN")
    i_fx = lines.index("self.start_action_effects(name, before)")
    # (C 단위) 휴학 판정 뒤, 휴학이 아닐 때만 이벤트 판정. 그다음 return True 로 끝난다
    i_end = lines.index(ROLL_AFTER_ENDING)
    assert i_before < i_if < i_cool < i_fx < i_end
    assert lines[i_end + 1:] == ["return True"]
    assert "self.check_ending()" not in lines


def test_game_init_only_adds_backdrop():
    """Game.__init__ 은 배경 Surface + (B 단위) 팝업 글꼴·마우스 위치·깜빡임 시계 줄만 늘었다."""
    old = _functions(git_show("game.py"))["Game.__init__"]
    new = _functions((ROOT / "game.py").read_text(encoding="utf-8"))["Game.__init__"]
    old_lines = [ast.unparse(s) for s in old.body[1:]]
    new_lines = [ast.unparse(s) for s in new.body[1:]]
    extra = [line for line in new_lines if line not in old_lines]
    assert [line for line in new_lines if line in old_lines] == old_lines
    assert extra == [
        "self.rng = random.Random(seed)",   # (C 단위) 이벤트 전용 난수 생성기
        "self.backdrop = self.make_backdrop()",
        "self.popup_font = pygame.font.SysFont(config.FONT_NAME, config.POPUP_FONT_SIZE, "
        "bold=config.POPUP_FONT_BOLD)",
        "self.event_font = pygame.font.SysFont(config.FONT_NAME, config.EVENT_FONT_SIZE)",
        # (D 단위) 미리보기·알림·특성 배지용 작은 글꼴
        "self.small_font = pygame.font.SysFont(config.FONT_NAME, config.SMALL_FONT_SIZE)",
        "self.mouse_pos = None",
        "self.blink_time = config.ZERO_TIME",
        "self.choice_buttons = self.make_choice_buttons()",
    ]
    # (C 단위) 인자는 record_path=None, seed=None 둘
    assert [a.arg for a in new.args.args] == ["self", "record_path", "seed"]
    assert [ast.unparse(d) for d in new.args.defaults] == ["None", "None"]


def test_action_keys_unchanged():
    import game as game_module
    assert game_module.ACTION_KEYS == {pygame.K_1: config.ACTION_FEED,
                                       pygame.K_2: config.ACTION_REST,
                                       pygame.K_3: config.ACTION_STUDY}


# ======================= 2. config.py 인코딩·한글 문자열 =======================

def test_config_is_valid_utf8_without_broken_chars():
    raw = (ROOT / "config.py").read_bytes()
    text = raw.decode("utf-8")          # 깨진 바이트가 있으면 여기서 실패
    assert "�" not in text          # 대체 문자(�) 없음
    # PowerShell 기본 인코딩(cp949/ANSI)으로 저장됐다가 다시 읽힌 흔적(모지바케) 없음
    for bad in ("ì", "ë", "ê", "Ã", "Â"):
        assert bad not in text, bad
    assert "제자 키우기" in text


@pytest.mark.parametrize("name, expected", [
    ("WINDOW_TITLE", "제자 키우기"),
    ("TITLE_TEXT", "제자 키우기"),
    ("HEALTH_LABEL", "체력"),
    ("MENTAL_LABEL", "멘탈"),
    ("KNOWLEDGE_LABEL", "지식"),
    ("ENDING_LEAVE", "휴학"),
    ("ENDING_TOP", "수석 졸업"),
    ("ENDING_NORMAL", "무사 졸업"),
    ("ENDING_BARELY", "아슬아슬 졸업"),
    ("FEED_BUTTON_TEXT", "학식 먹이기 [1]"),
    ("REST_BUTTON_TEXT", "쉬게 하기 [2]"),
    ("STUDY_BUTTON_TEXT", "공부시키기 [3]"),
    ("EXAM_BANNER_TEXT", "시험 기간! 공부 효과 2배, 멘탈 감소 2배"),
    ("START_HINT_TEXT", "Enter를 눌러 시작"),
    ("RESTART_HINT_TEXT", "R을 눌러 다시 하기"),
    ("COOLDOWN_HINT_TEXT", "누른 뒤 1초 동안 회색 (쿨타임)"),
    ("GRADE_TEXT", "{}학년"),
    ("TIME_LEFT_TEXT", "남은 시간 {}초"),
    ("BEST_RECORD_TEXT", "최고 기록: 지식 {}"),
    ("ENDING_KNOWLEDGE_TEXT", "누적 지식 {}"),
])
def test_korean_strings_match_spec(name, expected):
    assert getattr(config, name) == expected


def test_korean_strings_appear_in_spec_document():
    """엔딩 이름·배너·안내 문구가 기획서 본문에 그대로 있다(글자 하나 다르지 않음)."""
    spec = (ROOT / "docs" / "기획서.md").read_text(encoding="utf-8")
    for text in ("제자 키우기", "휴학", "수석 졸업", "무사 졸업", "아슬아슬 졸업",
                 "학식 먹이기 [1]", "쉬게 하기 [2]", "공부시키기 [3]",
                 "시험 기간! 공부 효과 2배, 멘탈 감소 2배", "누른 뒤 1초 동안 회색 (쿨타임)",
                 "Enter를 눌러 시작", "R을 눌러 다시 하기", "체력", "멘탈", "지식"):
        assert text in spec, text


@pytest.mark.parametrize("name", GAME_FILES)
def test_game_files_utf8(name):
    text = (ROOT / name).read_bytes().decode("utf-8")
    assert "�" not in text


# ======================= 3. 도트 스타일 표 대조 =======================

def test_pixel_size_is_4():
    assert config.PIXEL_SIZE == 4
    assert config.BOX_INSET == 2 * config.PIXEL_SIZE


def test_render_text_uses_no_antialias(font):
    rec = RecordingFont(font)
    render_text(rec, "가나다")
    assert rec.calls == [("가나다", False)]


def test_all_screens_render_text_without_antialias(game):
    """타이틀·게임(시험 기간)·휴학·졸업 엔딩 화면의 모든 글자가 antialias=False 로 그려진다."""
    small, big = RecordingFont(game.font), RecordingFont(game.title_font)
    game.font, game.title_font = small, big
    game.draw()                                       # 타이틀
    press(game, pygame.K_RETURN)
    game.student.elapsed = 50.0
    game.draw()                                       # 게임 + 시험 기간 배너
    game.end_game(config.ENDING_LEAVE)
    game.draw()                                       # 휴학
    game.ending = config.ENDING_TOP
    game.draw()                                       # 졸업
    calls = small.calls + big.calls
    assert len(calls) > 10
    assert all(aa is False for _, aa in calls), [c for c in calls if c[1] is not False]


@pytest.mark.parametrize("name", ["game.py", "student.py", "button.py"])
def test_font_render_only_inside_render_text(name):
    """글자는 모두 render_text 를 거친다: .render( 직접 호출은 render_text 안의 1곳뿐."""
    tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
    calls = []
    for func in ast.walk(tree):
        if isinstance(func, ast.FunctionDef):
            for node in ast.walk(func):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "render"):
                    calls.append(func.name)
    if name == "button.py":
        assert calls == ["render_text"]
    else:
        assert calls == []


def _is_reddish(rgb):
    r, g, b = rgb
    return r > g + 60 and r > b + 40


def _is_greenish(rgb):
    r, g, b = rgb
    return g > r + 40 and g > b + 20


def test_red_green_palette_clearly_different():
    for rgb in (config.COLOR_RED, config.COLOR_RED_LIGHT, config.COLOR_RED_DARK):
        assert _is_reddish(rgb), rgb
    for rgb in (config.COLOR_GREEN, config.COLOR_GREEN_LIGHT, config.COLOR_GREEN_DARK):
        assert _is_greenish(rgb), rgb
    dist = sum((a - b) ** 2 for a, b in zip(config.COLOR_RED, config.COLOR_GREEN)) ** 0.5
    assert dist > 150


@pytest.mark.parametrize("value, reddish", [(1, True), (29, True), (30, False), (100, False)])
def test_bar_whole_column_color_family(surface, font, value, reddish):
    """채움의 한 열 전체(밝은 위 줄·몸통·어두운 아래 줄)가 같은 색 계열이다. 판정은 실제 값."""
    surface.fill(config.COLOR_BG)
    s = Student()
    s.health = s.mental = value
    s.draw_gauges(surface, font)
    check = _is_reddish if reddish else _is_greenish
    for bar_y in (config.HEALTH_BAR_Y, config.MENTAL_BAR_Y):
        column = [color(surface, config.GAUGE_X, y) for y in range(bar_y, bar_y + config.BAR_HEIGHT)]
        assert all(check(c) for c in column), column
        assert column[0] != column[len(column) // 2] != column[-1]   # 위 줄 밝게 / 아래 줄 어둡게


@pytest.mark.parametrize("value", [0, 1, 13, 29, 30, 57, 99, 100])
def test_bar_fill_exact_width_all_rows(surface, font, value):
    """채움 폭 = int(BAR_WIDTH x 값 / 100) 이 위·가운데·아래 줄 모두 똑같다."""
    surface.fill(config.COLOR_BG)
    s = Student()
    s.health = value
    s.draw_gauges(surface, font)
    width = int(config.BAR_WIDTH * value / config.GAUGE_MAX)
    for y in (config.HEALTH_BAR_Y, config.HEALTH_BAR_Y + config.BAR_HEIGHT // 2,
              config.HEALTH_BAR_Y + config.BAR_HEIGHT - 1):
        n = sum(1 for x in range(config.GAUGE_X, config.GAUGE_X + config.BAR_WIDTH)
                if _is_reddish(color(surface, x, y)) or _is_greenish(color(surface, x, y)))
        assert n == width


def _is_grayish(rgb):
    return max(rgb) - min(rgb) <= 40


def test_cooldown_gray_palette():
    for rgb in (config.COLOR_GRAY, config.COLOR_GRAY_LIGHT, config.COLOR_GRAY_DARK):
        assert _is_grayish(rgb), rgb
    assert not _is_grayish(config.COLOR_BUTTON)


def test_cooldown_all_buttons_gray_then_back(game):
    press(game, pygame.K_RETURN)
    game.draw()
    points = {n: (b.rect.left + 2 * P, b.rect.centery) for n, b in game.buttons.items()}
    assert all(color(game.screen, *pt) == config.COLOR_BUTTON for pt in points.values())
    press(game, pygame.K_3)
    game.draw()
    assert all(color(game.screen, *pt) == config.COLOR_GRAY for pt in points.values())
    for _ in range(59):
        game.update(1 / 60)
    game.draw()
    assert all(color(game.screen, *pt) == config.COLOR_GRAY for pt in points.values())
    game.update(1 / 60)
    game.draw()
    assert all(color(game.screen, *pt) == config.COLOR_BUTTON for pt in points.values())


def _student(elapsed, health=80, mental=80):
    s = Student()
    s.elapsed = elapsed
    s.health, s.mental = health, mental
    return s


def _face_bbox(surf):
    """제자 무대 안에서 배경·발밑 그림자가 아닌 픽셀의 경계 상자."""
    xs, ys = [], []
    for x in range(config.STAGE_X, config.STAGE_X + config.STAGE_WIDTH):
        for y in range(config.PANEL_Y, config.PANEL_Y + config.PANEL_HEIGHT):
            c = color(surf, x, y)
            if c not in (config.COLOR_BG, config.COLOR_STAGE_SHADOW):
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


@pytest.mark.parametrize("elapsed, radius", [(0, 40), (60, 50), (120, 60), (180, 70), (240, 70)])
def test_face_diameter_is_twice_radius(surface, elapsed, radius):
    """실제로 그려진 얼굴(머리카락 포함)의 가로·세로 = 2 x 반지름, 중심 = 제자 무대 가운데."""
    s = _student(elapsed)
    assert s.get_radius() == radius
    surface.fill(config.COLOR_BG)
    s.draw(surface)
    left, top, right, bottom = _face_bbox(surface)
    assert right - left == 2 * radius
    assert bottom - top == 2 * radius
    assert (left + right) // 2 == CX and (top + bottom) // 2 == CY


@pytest.mark.parametrize("elapsed", [0, 60, 120, 180])
def test_dark_circles_fully_visible_under_glasses(surface, elapsed):
    """체력 30 미만 다크서클이 안경에 가리지 않고 양쪽 모두 온전히 보인다(2칸 x 2개)."""
    s = _student(elapsed, health=29)
    cell = s.get_radius() // config.FACE_CELL_DIVISOR
    surface.fill(config.COLOR_BG)
    s.draw(surface)
    n = sum(1 for x in range(CX - 70, CX + 70) for y in range(CY - 70, CY + 70)
            if color(surface, x, y) == config.COLOR_DARK_CIRCLE)
    assert n == 2 * 2 * cell * cell
    # 다크서클은 눈 아래(얼굴 가운데보다 아래)에 있다
    ys = [y for x in range(CX - 70, CX + 70) for y in range(CY - 70, CY + 70)
          if color(surface, x, y) == config.COLOR_DARK_CIRCLE]
    assert min(ys) > CY


@pytest.mark.parametrize("health", [30, 100])
def test_no_dark_circle_color_when_healthy(surface, health):
    for elapsed in (0, 120):
        surface.fill(config.COLOR_BG)
        _student(elapsed, health=health).draw(surface)
        assert not any(color(surface, x, y) == config.COLOR_DARK_CIRCLE
                       for x in range(CX - 70, CX + 70) for y in range(CY - 70, CY + 70))


@pytest.mark.parametrize("elapsed, glasses", [(0, False), (59.9, False), (60, False),
                                              (119.9, False), (120, True), (180, True)])
def test_glasses_lens_glass_color_only_with_glasses(surface, elapsed, glasses):
    surface.fill(config.COLOR_BG)
    _student(elapsed).draw(surface)
    found = any(color(surface, x, y) == config.COLOR_GLASS
                for x in range(CX - 70, CX + 70) for y in range(CY - 70, CY + 70))
    assert found is glasses


def test_three_mouths_produce_three_different_images(surface):
    for elapsed in (0, 120, 180):
        images = set()
        for mental in (60, 59, 29):
            surface.fill(config.COLOR_BG)
            _student(elapsed, mental=mental).draw(surface)
            images.add(pygame.image.tobytes(surface, "RGB"))
        assert len(images) == 3


def test_eyes_visible_with_glasses(surface):
    """안경을 써도 눈(남색 2x2칸, 흰 반짝임)이 보인다."""
    s = _student(180)
    surface.fill(config.COLOR_BG)
    s.draw(surface)
    n_white = sum(1 for x in range(CX - 70, CX + 70) for y in range(CY - 70, CY)
                  if color(surface, x, y) == config.COLOR_WHITE)
    cell = s.get_radius() // config.FACE_CELL_DIVISOR
    assert n_white == 2 * cell * cell


# ======================= 4. 도트 도우미 함수 =======================

def test_draw_cut_rect_corners_cut(surface):
    surface.fill(config.COLOR_BLACK)
    draw_cut_rect(surface, config.COLOR_WHITE, (40, 40, 80, 40))
    assert color(surface, 40, 40) == config.COLOR_BLACK              # 모서리 1칸 비움
    assert color(surface, 40 + P - 1, 40 + P - 1) == config.COLOR_BLACK
    assert color(surface, 40 + P, 40) == config.COLOR_WHITE
    assert color(surface, 40, 40 + P) == config.COLOR_WHITE
    assert color(surface, 119, 79) == config.COLOR_BLACK
    assert color(surface, 119 - P, 79) == config.COLOR_WHITE


def test_draw_pixel_box_layers(surface):
    surface.fill(config.COLOR_BLACK)
    inner = draw_pixel_box(surface, (40, 40, 80, 40), config.COLOR_YELLOW,
                           config.COLOR_WHITE, config.COLOR_RED, drop=config.COLOR_GRAY)
    assert inner == pygame.Rect(44, 44, 72, 32)
    assert color(surface, 60, 41) == config.COLOR_OUTLINE      # 외곽선 1칸
    assert color(surface, 60, 45) == config.COLOR_WHITE        # 위 하이라이트
    assert color(surface, 60, 60) == config.COLOR_YELLOW       # 몸통
    assert color(surface, 60, 74) == config.COLOR_RED          # 아래 그림자 줄
    assert color(surface, 60, 82) == config.COLOR_GRAY         # 상자 아래 그림자 1칸
    assert sprite_size(["abc", "abc"], 5) == (15, 10)


# ======================= 5. 도형 제한·리소스·클래스 =======================

def test_no_image_or_sound_files_in_project():
    bad_ext = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".wav", ".ogg", ".mp3", ".ttf", ".otf"}
    skip = {"build", "dist", ".git", ".pytest_cache", "__pycache__", ".claude", ".venv"}
    found = []
    for path in ROOT.rglob("*"):
        if any(part in skip for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix.lower() in bad_ext:
            found.append(str(path))
    assert found == []


def test_exactly_three_classes():
    names = []
    for name in GAME_FILES:
        for node in ast.walk(ast.parse((ROOT / name).read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef):
                names.append(node.name)
    assert sorted(names) == ["Button", "Game", "Student"]


@pytest.mark.parametrize("name", GAME_FILES)
def test_fonts_only_sysfont(name):
    src = (ROOT / name).read_text(encoding="utf-8")
    assert "Font(None" not in src
    assert "pygame.font.Font(" not in src


@pytest.mark.parametrize("name", GAME_FILES)
def test_no_draw_functions_beyond_rect_circle_line_arc(name):
    """pygame.draw.* 뿐 아니라 import 별칭으로 부르는 도형 함수도 없다."""
    src = (ROOT / name).read_text(encoding="utf-8")
    for bad in ("polygon", "ellipse", "aaline", "lines(", "gfxdraw", "image.load", "mixer",
                "from pygame.draw", "from pygame import draw"):
        assert bad not in src, bad


def test_sprites_use_only_known_characters():
    """스프라이트 격자의 모든 글자는 색 사전에 있거나 투명(".")이다. 각 격자는 직사각형."""
    pairs = [
        (config.FACE_SPRITE, config.FACE_COLORS), (config.EYE_SPRITE, config.FACE_COLORS),
        (config.BLUSH_SPRITE, config.FACE_COLORS), (config.DARK_CIRCLE_SPRITE, config.FACE_COLORS),
        (config.GLASSES_LENS_SPRITE, config.FACE_COLORS),
        (config.CAP_SPRITE, config.CAP_COLORS), (config.CLOUD_SPRITE, config.CLOUD_COLORS),
        (config.HEART_SPRITE, config.HEART_COLORS),
    ]
    pairs += [(grid, config.FACE_COLORS) for _, grid in config.MOUTH_SPRITES.values()]
    pairs += [(grid, config.FACE_COLORS) for _, grid in config.GLASSES_PARTS]
    for grid in (config.STAR_SPRITE, config.ARROW_SPRITE, config.EXCLAIM_SPRITE):
        pairs.append((grid, {config.SPRITE_INK: config.COLOR_BLACK}))
    for grid, colors in pairs:
        assert len({len(row) for row in grid}) == 1, grid
        for row in grid:
            for ch in row:
                assert ch == "." or ch in colors, (ch, grid)
    assert len(config.FACE_SPRITE) == len(config.FACE_SPRITE[0]) == 20


# ======================= 6. 겹침·글자 넘침 =======================

def _text_rect(font, text, **pos):
    rect = pygame.Rect(config.ORIGIN, font.size(text))
    for k, v in pos.items():
        setattr(rect, k, v)
    return rect


def _with_drop(rect):
    rect = pygame.Rect(rect)
    return pygame.Rect(rect.left, rect.top, rect.width, rect.height + P)


def test_game_screen_boxes_do_not_overlap():
    info = _with_drop((config.INFO_BOX_X, config.INFO_BOX_Y, config.INFO_BOX_WIDTH,
                       config.INFO_BOX_HEIGHT))
    banner = _with_drop((config.EXAM_BANNER_X, config.EXAM_BANNER_Y, config.EXAM_BANNER_WIDTH,
                         config.EXAM_BANNER_HEIGHT))
    status = _with_drop((config.STATUS_PANEL_X, config.PANEL_Y, config.STATUS_PANEL_WIDTH,
                         config.PANEL_HEIGHT))
    stage = _with_drop((config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH, config.PANEL_HEIGHT))
    buttons = [_with_drop(b.rect) for b in Game.make_buttons(None).values()]
    boxes = [info, banner, status, stage] + buttons
    screen = pygame.Rect(config.ORIGIN, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    for i, a in enumerate(boxes):
        assert screen.contains(a), a
        for b in boxes[i + 1:]:
            assert not a.colliderect(b), (a, b)


def test_gauges_inside_status_panel():
    inner = pygame.Rect(config.STATUS_PANEL_X, config.PANEL_Y, config.STATUS_PANEL_WIDTH,
                        config.PANEL_HEIGHT).inflate(-2 * P, -2 * P)
    for bar_y in (config.HEALTH_BAR_Y, config.MENTAL_BAR_Y):
        frame = pygame.Rect(config.GAUGE_X, bar_y, config.BAR_WIDTH,
                            config.BAR_HEIGHT).inflate(2 * P, 2 * P)
        assert inner.contains(frame)
    for label_y, icon in ((config.HEALTH_LABEL_Y, config.HEART_SPRITE),
                          (config.MENTAL_LABEL_Y, config.STAR_SPRITE)):
        w, h = sprite_size(icon, P)
        assert inner.contains(pygame.Rect(config.GAUGE_X, label_y, w, h))
    # 라벨 줄과 막대 테두리가 겹치지 않는다
    assert config.HEALTH_LABEL_Y + sprite_size(config.HEART_SPRITE, P)[1] <= config.HEALTH_BAR_Y - P
    assert config.MENTAL_LABEL_Y + sprite_size(config.STAR_SPRITE, P)[1] <= config.MENTAL_BAR_Y - P
    assert config.HEALTH_BAR_Y + config.BAR_HEIGHT + P < config.MENTAL_LABEL_Y


@pytest.mark.parametrize("elapsed", [0, 60, 120, 180])
def test_student_and_shadow_inside_stage(elapsed):
    r = _student(elapsed).get_radius()
    inner = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH,
                        config.PANEL_HEIGHT).inflate(-2 * P, -2 * P)
    assert inner.contains(pygame.Rect(CX - r, CY - r, 2 * r, 2 * r))
    shadow_bottom = CY + r + config.SHADOW_GAP + config.SHADOW_HEIGHT
    assert shadow_bottom <= inner.bottom


def test_texts_fit_in_boxes(font):
    # 버튼 글자는 버튼 안쪽(외곽선·위아래 줄 제외)에 들어간다
    for b in Game.make_buttons(None).values():
        inner = b.rect.inflate(-4 * P, -2 * P)
        assert inner.contains(_text_rect(font, b.text, center=b.rect.center)), b.text
    # 배너 글자는 배너 안쪽, 양옆 느낌표와 겹치지 않는다
    banner = pygame.Rect(config.EXAM_BANNER_X, config.EXAM_BANNER_Y, config.EXAM_BANNER_WIDTH,
                         config.EXAM_BANNER_HEIGHT)
    inner = banner.inflate(-2 * P, -2 * P)
    text = _text_rect(font, config.EXAM_BANNER_TEXT, center=inner.center)
    assert inner.contains(text)
    ew, _ = sprite_size(config.EXCLAIM_SPRITE, P)
    assert banner.left + config.EXAM_ICON_MARGIN + ew < text.left
    assert text.right < banner.right - config.EXAM_ICON_MARGIN - ew
    # 쿨타임 안내는 버튼 아래(받침 포함)이고 화면 안
    hint = _text_rect(font, config.COOLDOWN_HINT_TEXT,
                      midtop=(config.COOLDOWN_HINT_X, config.COOLDOWN_HINT_Y))
    assert hint.top >= config.BUTTON_Y + config.BUTTON_HEIGHT + P
    assert hint.bottom <= config.SCREEN_HEIGHT


def test_info_bar_texts_fit_and_do_not_overlap(font):
    inner = pygame.Rect(config.INFO_BOX_X, config.INFO_BOX_Y, config.INFO_BOX_WIDTH,
                        config.INFO_BOX_HEIGHT).inflate(-2 * P, -2 * P)
    grade = _text_rect(font, "4학년", midleft=(config.INFO_BAR_MARGIN, config.INFO_TEXT_CENTER_Y))
    time_left = _text_rect(font, "남은 시간 60초",
                           center=(config.INFO_TIME_X, config.INFO_TEXT_CENTER_Y))
    knowledge = _text_rect(font, "지식 99999",
                           midright=(config.SCREEN_WIDTH - config.INFO_BAR_MARGIN,
                                     config.INFO_TEXT_CENTER_Y))
    for r in (grade, time_left, knowledge):
        assert inner.contains(r), r
    assert grade.right < time_left.left and time_left.right < knowledge.left


def test_title_screen_layout_no_overlap(game):
    panel_inner = pygame.Rect(config.MENU_PANEL_RECT).inflate(-2 * P, -2 * P)
    title = _text_rect(game.title_font, config.TITLE_TEXT,
                       center=(config.SCREEN_CENTER_X, config.TITLE_TEXT_Y))
    title_shadow = title.move(config.TITLE_SHADOW_OFFSET, config.TITLE_SHADOW_OFFSET)
    record_text = game.font.size(config.BEST_RECORD_TEXT.format(99999))
    badge = pygame.Rect(config.ORIGIN, (record_text[0] + 2 * config.BADGE_PADDING_X,
                                        config.BADGE_HEIGHT + P))
    badge.midtop = (config.SCREEN_CENTER_X, config.BEST_RECORD_Y - config.BADGE_HEIGHT // 2)
    hint = _text_rect(game.font, config.START_HINT_TEXT,
                      center=(config.SCREEN_CENTER_X, config.START_HINT_Y))
    aw, ah = sprite_size(config.ARROW_SPRITE, P)
    arrow = pygame.Rect(hint.left - config.HINT_ARROW_GAP - aw, config.START_HINT_Y - ah // 2, aw, ah)
    line = pygame.Rect(config.SCREEN_CENTER_X - config.TITLE_LINE_DOTS * P, config.TITLE_LINE_Y,
                       config.TITLE_LINE_DOTS * 2 * P, P)
    sw, sh = sprite_size(config.STAR_SPRITE, P)
    stars = [pygame.Rect(x, y, sw, sh) for x, y, _ in config.TITLE_STARS]
    items = [title.union(title_shadow), badge, hint.union(arrow), line] + stars
    for i, a in enumerate(items):
        assert panel_inner.contains(a), a
        for b in items[i + 1:]:
            assert not a.colliderect(b), (a, b)


@pytest.mark.parametrize("ending", [config.ENDING_LEAVE, config.ENDING_TOP,
                                    config.ENDING_NORMAL, config.ENDING_BARELY])
def test_ending_screen_layout_no_overlap(game, ending):
    panel_inner = pygame.Rect(config.MENU_PANEL_RECT).inflate(-2 * P, -2 * P)
    name = _text_rect(game.title_font, ending, center=(config.SCREEN_CENTER_X, config.ENDING_NAME_Y))
    name = name.union(name.move(config.TITLE_SHADOW_OFFSET, config.TITLE_SHADOW_OFFSET))
    kw = game.font.size(config.ENDING_KNOWLEDGE_TEXT.format(99999))[0]
    badge = pygame.Rect(config.ORIGIN, (kw + 2 * config.BADGE_PADDING_X, config.BADGE_HEIGHT + P))
    badge.midtop = (config.SCREEN_CENTER_X, config.ENDING_KNOWLEDGE_Y - config.BADGE_HEIGHT // 2)
    hint = _text_rect(game.font, config.RESTART_HINT_TEXT,
                      center=(config.SCREEN_CENTER_X, config.RESTART_HINT_Y))
    aw, _ = sprite_size(config.ARROW_SPRITE, P)
    hint.union_ip(hint.move(-(config.HINT_ARROW_GAP + aw), 0))
    items = [name, badge, hint]
    if ending == config.ENDING_LEAVE:
        w, h = sprite_size(config.CLOUD_SPRITE, config.CLOUD_PIXEL)
        items.append(pygame.Rect(config.SCREEN_CENTER_X - w // 2, config.CLOUD_TOP_Y, w, h))
    else:
        w, h = sprite_size(config.CAP_SPRITE, config.CAP_PIXEL)
        items.append(pygame.Rect(config.SCREEN_CENTER_X - w // 2, config.CAP_TOP_Y, w, h))
        sw, sh = sprite_size(config.STAR_SPRITE, P)
        items += [pygame.Rect(x, y, sw, sh) for x, y, _ in config.ENDING_STARS]
    for i, a in enumerate(items):
        assert panel_inner.contains(a), (ending, a)
        for b in items[i + 1:]:
            assert not a.colliderect(b), (ending, a, b)


def test_cap_only_on_graduation_and_cloud_only_on_leave(game):
    press(game, pygame.K_RETURN)
    for ending, cap in ((config.ENDING_LEAVE, False), (config.ENDING_TOP, True),
                        (config.ENDING_NORMAL, True), (config.ENDING_BARELY, True)):
        game.end_game(ending)
        game.draw()
        pixels = [color(game.screen, x, y) for x in range(0, config.SCREEN_WIDTH, 2)
                  for y in range(0, config.SCREEN_HEIGHT, 2)]
        assert (config.COLOR_CAP in pixels) is cap
        assert (config.COLOR_TASSEL in pixels) is cap
        assert (config.COLOR_CLOUD in pixels) is (not cap)


def test_cap_and_cloud_colors_not_used_in_game_screen(game):
    press(game, pygame.K_RETURN)
    game.student.elapsed = 230.0
    game.draw()
    pixels = {color(game.screen, x, y) for x in range(config.SCREEN_WIDTH)
              for y in range(config.SCREEN_HEIGHT)}
    assert config.COLOR_CAP not in pixels and config.COLOR_TASSEL not in pixels


def test_button_class_still_button_only():
    """Button 클래스는 위치·글자·클릭 판정·쿨타임 표시만 맡는다.

    (B 단위) 호버·눌림·진행 막대는 새 메서드 없이 draw 인자로만 받는다:
    draw(screen, font, cooling_down, hovered=False, press_offset=0, cooldown_progress=None).
    """
    import inspect
    methods = {n for n in vars(Button) if not n.startswith("__")}
    assert methods == {"is_clicked", "get_colors", "draw"}
    params = inspect.signature(Button.draw).parameters
    assert list(params) == ["self", "screen", "font", "cooling_down", "hovered",
                            "press_offset", "cooldown_progress"]
    assert params["hovered"].default is False
    assert params["press_offset"].default == config.NO_OFFSET == 0
    assert params["cooldown_progress"].default is None
    # 기존 호출 방식 draw(screen, font, cooling_down) 도 그대로 동작한다
    pygame.init()
    try:
        surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        f = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
        b = Button(28, config.BUTTON_Y, config.BUTTON_WIDTH, config.BUTTON_HEIGHT, "x")
        b.draw(surf, f, False)
        assert color(surf, b.rect.left + 2 * P, b.rect.centery) == config.COLOR_BUTTON
    finally:
        pygame.quit()
