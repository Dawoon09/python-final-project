"""최종 검수: 실제 메인 루프(Game.run)로 타이틀 -> 게임 -> 엔딩 -> R -> 종료, 완료 기준 정적 검사."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import ast  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
import main as main_module  # noqa: E402
from game import Game  # noqa: E402

ROOT = Path(config.__file__).parent
GAME_FILES = ["main.py", "student.py", "button.py", "game.py"]


# ======================= 프레임 단위 이벤트 대본 =======================

class FrameScript:
    """pygame.event.get 대신 들어가서, 한 프레임에 한 단계씩 이벤트를 돌려준다.

    각 단계는 (설명, 준비 함수 또는 None, 이벤트 목록)이다. 단계를 꺼낼 때마다
    직전 프레임(update·draw까지 끝난 뒤)의 게임 상태를 snapshots에 기록한다.
    대본이 다 떨어지면 안전장치로 ESC를 돌려준다(무한 루프 방지).
    """

    def __init__(self, game, steps):
        """game과 단계 목록을 받는다."""
        self.game = game
        self.steps = list(steps)
        self.snapshots = []

    def snapshot(self, label):
        """지금 게임 상태를 기록한다."""
        s = self.game.student
        self.snapshots.append({
            "label": label,
            "state": self.game.state,
            "ending": self.game.ending,
            "health": s.health,
            "mental": s.mental,
            "knowledge": s.knowledge,
            "elapsed": s.elapsed,
            "policy": self.game.policy,   # G단위: 쿨타임 대신 일과표 방침을 기록
            "last_action": self.game.last_action,
            "best": self.game.best_record,
        })

    def __call__(self, *args, **kwargs):
        """pygame.event.get 처럼 이벤트 목록을 돌려준다."""
        if not self.steps:
            self.snapshot("(대본 끝)")
            return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)]
        label, prepare, events = self.steps.pop(0)
        self.snapshot(label)
        if prepare is not None:
            prepare(self.game)
        return events


def key(k):
    """KEYDOWN 이벤트 하나."""
    return pygame.event.Event(pygame.KEYDOWN, key=k)


def by_label(script, label):
    """label 단계 직전(= 그 앞 프레임이 끝난 뒤)의 상태."""
    for snap in script.snapshots:
        if snap["label"] == label:
            return snap
    raise AssertionError(label)


def run_script(game, steps, monkeypatch):
    """game.run()을 대본대로 돌리고 SystemExit까지 확인한 뒤 대본 객체를 돌려준다."""
    script = FrameScript(game, steps)
    monkeypatch.setattr(pygame.event, "get", script)
    with pytest.raises(SystemExit):
        game.run()
    assert game.running is False
    return script


def force_graduation(seconds, knowledge):
    """엔딩 강제 준비 함수: 경과 시간을 seconds 직전으로 옮기고 4학년 + 지식 knowledge(1100 이상)로 맞춘다.

    (L단위, 기획서 11절) 다음 프레임의 update 진급 판정에서 졸업하고, 등급은 걸린 시간으로 정해진다.
    """
    def prepare(game):
        s = game.student
        # 학년은 1학년 그대로: 진급 판정이 한 번에 4학년까지 올리고 졸업시킨다
        s.knowledge = knowledge
        s.health = config.GAUGE_MAX
        s.mental = config.GAUGE_MAX
        s.elapsed = seconds - 1e-6
    return prepare


def do(name):
    """(G단위) 준비 함수: 행동 name을 game.do_action으로 바로 실행한다(키 1/2/3은 이제 방침 선택)."""
    def prepare(game):
        assert game.do_action(name)
    return prepare


def set_health(value):
    """준비 함수: 체력을 value로 맞춘다."""
    def prepare(game):
        game.student.health = value
    return prepare


# ======================= 완료 기준: 실제 루프 한 바퀴 =======================

@pytest.mark.parametrize("seconds, knowledge, ending", [
    # E단위 700/450, K단위 1000/750 (지식) -> L단위: 걸린 시간 240/360초 (기획서 11절)
    # -> 11절 A안 200/360초. 강제 졸업 시각에 프레임 몇 개가 더해지므로 수석 사례는 150초로 둔다.
    # (M단위) 시간 기준은 임시 값이라 config 상수 기준으로 시각을 잡는다
    (config.TOP_GRADUATE_SECONDS - 50.0, config.GRADUATION_KNOWLEDGE + 20, config.ENDING_TOP),
    ((config.TOP_GRADUATE_SECONDS + config.NORMAL_GRADUATE_SECONDS) / 2,
     config.GRADUATION_KNOWLEDGE, config.ENDING_NORMAL),
    (config.NORMAL_GRADUATE_SECONDS + 40.0, config.GRADUATION_KNOWLEDGE + 120,
     config.ENDING_BARELY),
])
def test_real_loop_title_play_graduation_restart_esc(monkeypatch, isolated_record_path,
                                                    seconds, knowledge, ending):
    """Enter -> 공부 행동 + 3키(방침) -> 학식 + 1키 -> 강제 졸업 -> R -> ESC 를 실제 Game.run() 루프로 확인.

    G단위: 키 1/2/3은 방침 선택이고 행동은 do_action으로 직접 시킨다(자동 행동은 conftest no_auto로 끔).
    """
    g = Game()
    steps = [
        ("enter", None, [key(pygame.K_RETURN)]),
        ("after_enter", None, []),
        ("key3", do(config.ACTION_STUDY), [key(pygame.K_3)]),
        ("after_key3", None, []),
        ("key1_in_cooldown", do(config.ACTION_FEED), [key(pygame.K_1)]),
        ("after_key1", None, []),
        ("force_end", force_graduation(seconds, knowledge), []),
        ("on_ending", None, []),
        ("key3_on_ending", None, [key(pygame.K_3)]),
        ("r", None, [key(pygame.K_r)]),
        ("after_r", None, []),
        ("esc", None, [key(pygame.K_ESCAPE)]),
    ]
    script = run_script(g, steps, monkeypatch)

    # 타이틀에서 시작
    assert by_label(script, "enter")["state"] == config.STATE_TITLE
    # Enter -> 게임
    after_enter = by_label(script, "after_enter")
    assert after_enter["state"] == config.STATE_PLAYING
    # 3키 공부 한 번: 지식 +10, 체력 -5, 멘탈 -8 (자연 감소 0~1초 사이라 아직 없음)
    after3 = by_label(script, "after_key3")
    assert after3["knowledge"] == config.STUDY_KNOWLEDGE
    assert after3["health"] == config.HEALTH_START + config.STUDY_HEALTH
    assert after3["mental"] == config.MENTAL_START + config.STUDY_MENTAL
    assert after3["policy"] == config.POLICY_REST_FOCUS   # 3키 -> 휴식 위주
    # 쿨타임 없음: 바로 다음 프레임의 학식도 실행되고, 1키 -> 공부 위주
    after1 = by_label(script, "after_key1")
    # (M단위) 학식은 게이지를 바로 바꾸지 않고 든든함만 붙인다
    assert after1["health"] == after3["health"]
    assert after1["last_action"] == config.ACTION_FEED
    assert after1["policy"] == config.POLICY_STUDY_FOCUS
    # 강제 졸업 -> 엔딩 화면, 걸린 시간에 맞는 엔딩
    on_ending = by_label(script, "on_ending")
    assert on_ending["state"] == config.STATE_ENDING
    assert on_ending["ending"] == ending
    assert seconds - 1e-6 <= on_ending["elapsed"] < seconds + 1.0
    assert on_ending["best"] == knowledge
    # 엔딩 화면의 3키는 무시(방침도 그대로)
    assert by_label(script, "r")["knowledge"] == knowledge
    assert by_label(script, "r")["policy"] == config.POLICY_STUDY_FOCUS
    # R -> 새 판, 모든 값 초기화
    after_r = by_label(script, "after_r")
    assert after_r["state"] == config.STATE_PLAYING
    assert after_r["ending"] is None
    assert after_r["knowledge"] == config.KNOWLEDGE_START
    assert after_r["health"] == config.HEALTH_START
    assert after_r["mental"] == config.MENTAL_START
    assert after_r["elapsed"] < config.DECAY_INTERVAL
    assert after_r["policy"] == config.POLICY_START   # 새 판은 균형으로
    # 최고 기록은 유지되고 파일에도 저장됨
    assert after_r["best"] == knowledge
    with open(isolated_record_path, encoding="utf-8") as f:
        data = json.load(f)
    # (H단위) 4개 키 형식. 최고 기록은 그대로 확인한다
    assert set(data) == {config.RECORD_KEY, config.RECORD_MONEY_KEY, config.RECORD_FAME_KEY,
                         config.RECORD_UPGRADES_KEY}
    assert data[config.RECORD_KEY] == knowledge


def test_real_loop_leave_by_study_key_then_restart(monkeypatch, isolated_record_path):
    """체력 3에서 공부 -> 그 프레임에 바로 휴학 엔딩 -> R -> ESC (실제 루프). G단위: 공부는 do_action."""
    g = Game()
    steps = [
        ("enter", None, [key(pygame.K_RETURN)]),
        ("key3", lambda game: (set_health(3)(game), do(config.ACTION_STUDY)(game)), []),
        ("after_key3", None, []),
        ("r", None, [key(pygame.K_r)]),
        ("after_r", None, []),
        ("esc", None, [key(pygame.K_ESCAPE)]),
    ]
    script = run_script(g, steps, monkeypatch)
    after3 = by_label(script, "after_key3")
    assert after3["state"] == config.STATE_ENDING
    assert after3["ending"] == config.ENDING_LEAVE
    assert after3["health"] == 0
    # 휴학도 기록 저장. (M단위) 체력 3은 피곤(30 미만)이라 공부 지식 x0.7
    assert after3["best"] == round(config.STUDY_KNOWLEDGE * config.TIRED_KNOWLEDGE_RATIO)
    after_r = by_label(script, "after_r")
    assert after_r["state"] == config.STATE_PLAYING
    assert after_r["health"] == config.HEALTH_START


def test_real_loop_click_button(monkeypatch):
    """실제 루프에서 마우스 왼쪽 클릭으로 방침 버튼을 누르면 그 방침이 된다(G단위: 행동 버튼 -> 방침 버튼).

    클릭만으로는 행동하지 않으므로 체력은 그대로다.
    """
    g = Game()
    feed_center = g.buttons[config.POLICY_REST_FOCUS].rect.center
    steps = [
        ("enter", None, [key(pygame.K_RETURN)]),
        ("click", set_health(50), [pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, pos=feed_center, button=pygame.BUTTON_LEFT)]),
        ("after_click", None, []),
        ("esc", None, [key(pygame.K_ESCAPE)]),
    ]
    script = run_script(g, steps, monkeypatch)
    after = by_label(script, "after_click")
    assert after["policy"] == config.POLICY_REST_FOCUS
    assert after["health"] == 50
    assert after["last_action"] is None


def test_main_entry_runs_game_loop(monkeypatch):
    """main.main() (python main.py 와 같은 경로)가 Game을 만들어 루프를 돌리고 ESC로 끝난다."""
    calls = []
    original_run = Game.run

    def spy_run(self):
        calls.append(self)
        script = FrameScript(self, [
            ("enter", None, [key(pygame.K_RETURN)]),
            ("esc", None, [key(pygame.K_ESCAPE)]),
        ])
        monkeypatch.setattr(pygame.event, "get", script)
        original_run(self)

    monkeypatch.setattr(Game, "run", spy_run)
    with pytest.raises(SystemExit):
        main_module.main()
    assert len(calls) == 1
    assert calls[0].state == config.STATE_PLAYING


def test_main_py_has_entry_guard():
    """main.py 는 `if __name__ == "__main__": main()` 으로 실행된다."""
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in src
    assert "main()" in src


# ======================= 완료 기준: 수치·파일 =======================

@pytest.mark.parametrize("name", GAME_FILES)
def test_no_numeric_literals_other_than_0_1(name):
    """게임 코드 4개 파일에는 0, 1 이외의 숫자 리터럴이 없다(음수 리터럴 포함)."""
    tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
    bad = [(n.lineno, n.value) for n in ast.walk(tree)
           if isinstance(n, ast.Constant) and type(n.value) in (int, float, complex)
           and n.value not in (0, 1)]
    assert not bad, f"{name}: {bad}"


@pytest.mark.parametrize("name, expected", [
    ("SCREEN_WIDTH", 800), ("SCREEN_HEIGHT", 600),
    ("CYCLE_SECONDS", 60), ("MAX_GRADE", 4),   # L단위: SECONDS_PER_GRADE·TOTAL_SECONDS 삭제
    ("EXAM_SECONDS", 15), ("FONT_NAME", "malgungothic"),
    ("GAUGE_MIN", 0), ("GAUGE_MAX", 100),
    ("HEALTH_START", 80), ("MENTAL_START", 80), ("KNOWLEDGE_START", 0),
    ("HEALTH_DECAY_PER_SEC", 1), ("MENTAL_DECAY_PER_SEC", 1), ("MENTAL_DECAY_PER_SEC_EXAM", 2),
    ("DECAY_INTERVAL", 1.0), ("LOW_GAUGE_LIMIT", 30),
    # M단위: FEED_HEALTH 삭제(학식 = 든든함 30초), 휴식 체력 +15
    ("FULL_DURATION", 30), ("REST_HEALTH", 15), ("REST_MENTAL", 20), ("REST_KNOWLEDGE", -2),
    ("STUDY_HEALTH", -5), ("STUDY_MENTAL", -8),
    ("STUDY_KNOWLEDGE", 10), ("STUDY_KNOWLEDGE_EXAM", 20),  # G단위: ACTION_COOLDOWN 삭제(기획서 10절)
    ("MENTAL_SMILE_MIN", 60), ("MENTAL_FLAT_MIN", 30),
    ("BASE_RADIUS", 40), ("RADIUS_PER_GRADE", 10), ("GLASSES_GRADE", 3),
    # L단위(기획서 11절): 졸업 등급은 걸린 시간, 진급 목표 200/450/750, 졸업 지식 1100
    # M단위: 진급 기준 2배 400/900/1500, 졸업 2200. 시간 기준(400/720)은 임시 값이라 고정하지 않는다
    ("GRADE_GOALS", [400, 900, 1500]), ("GRADUATION_KNOWLEDGE", 2200),
    ("ENDING_LEAVE", "휴학"), ("ENDING_TOP", "수석 졸업"),
    ("ENDING_NORMAL", "무사 졸업"), ("ENDING_BARELY", "아슬아슬 졸업"),
    ("RECORD_FILENAME", "record.json"),
    # G단위: 행동 버튼 글자 3개 -> 방침 버튼 글자(기획서 10절 화면: 공부 위주 [1] / 균형 [2] / 휴식 위주 [3])
    ("EXAM_BANNER_TEXT", "시험 기간! 공부 효과 2배, 멘탈 감소 2배"),
    ("START_HINT_TEXT", "Enter를 눌러 시작"), ("RESTART_HINT_TEXT", "R을 눌러 다시 하기"),
])
def test_config_matches_spec(name, expected):
    """config.py 수치가 기획서·jeja-spec 과 같다."""
    assert getattr(config, name) == expected


@pytest.mark.parametrize("path", [
    "CLAUDE.md",
    ".claude/skills/jeja-spec/SKILL.md",
    ".claude/skills/build-exe/SKILL.md",
    ".claude/agents/dev-team.md",
    ".claude/agents/qa-team.md",
    "README.md",
    "docs/기획서.md",
    "tests",
    "main.py", "config.py", "student.py", "button.py", "game.py",
])
def test_deliverables_exist(path):
    """완료 기준 산출물이 저장소에 있다."""
    assert (ROOT / path).exists(), path


def test_dist_exe_exists_not_run():
    """빌드 결과 dist/main.exe 가 있다(실행하지 않음)."""
    exe = ROOT / "dist" / "main.exe"
    assert exe.is_file()
    assert exe.stat().st_size > 0


def test_record_path_handles_frozen_in_config():
    """build-exe 스킬 3절: sys.frozen 이면 sys.executable 폴더, 아니면 config.py(=main.py) 폴더."""
    src = (ROOT / "config.py").read_text(encoding="utf-8")
    assert 'getattr(sys, "frozen", False)' in src
    assert "os.path.dirname(sys.executable)" in src
    assert "os.path.dirname(os.path.abspath(__file__))" in src
    assert (ROOT / "config.py").parent == (ROOT / "main.py").parent


# ======================= README 대조 =======================

def _readme():
    return (ROOT / "README.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("text", [
    "python main.py",
    "py -3.12 main.py",
    "py -3.12 -m pytest",
    "py -3.12 -m PyInstaller --onefile --noconsole main.py",
    "dist/main.exe",
    # 방치형 README 3절 조작표(화면 열 추가)
    "| 게임 시작 | - | Enter | 타이틀 |",
    "| 환생 (졸업·대학원 수료) / 다시 하기 (휴학) | - | R | 엔딩 |",
    "| 학식 먹이기 | +20 | - | - |",
    "| 쉬게 하기 | - | +20 | -2 |",
    "| 공부시키기 | -5 | -8 | +10 (시험 기간 +20) |",
    # (L단위) 지식 기준 졸업 문구("수석 졸업(1000 이상)…", "엔딩 경계값(749/750/999/1000)")는
    # 기획서 11절로 규칙이 없어져 뺐다. 새 규칙 문구는 test_readme_describes_no_time_limit에서 본다.
    "제자는 2초마다(첫 행동은 시작 2초 뒤)",   # G단위: 쿨타임 1초 대신 자동 행동 간격 2초
    "마지막 15초",
])
def test_readme_mentions(text):
    """README 의 실행·빌드 명령, 조작키, 수치가 코드·기획서와 같다."""
    assert text in _readme(), text


@pytest.mark.parametrize("old, new", [
    ("240초(1~4학년, 학년당 60초)", "누적 지식"),
    ("60초마다 학년이 오르고", "200"),
    ("수석 졸업(1000 이상)", "200초"),
])
def test_readme_describes_no_time_limit(old, new):
    """(L단위) README가 예전 시간 제한 규칙을 말하지 않고 새 규칙(지식 진급·걸린 시간 등급)을 설명한다.

    (11절 A안) 수석 기준은 200초다. 팀장 결정으로 README에는 "240초"가 어디에도 남지 않는다.
    """
    text = _readme()
    assert old not in text and new in text
    assert "240초" not in text



@pytest.mark.parametrize("name", ["main.py", "config.py", "student.py", "button.py",
                                  "game.py", "requirements.txt", "CLAUDE.md"])
def test_readme_folder_structure_files_exist(name):
    """README 폴더 구조에 적힌 파일이 실제로 있다."""
    assert name in _readme()
    assert (ROOT / name).exists()


def test_requirements_pin_pygame_26():
    """requirements.txt 의 pygame 이 2.6 이다."""
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "pygame==2.6" in req
