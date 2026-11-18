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
            "cooldown": self.game.cooldown,
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


def force_graduation(knowledge):
    """엔딩 강제 준비 함수: 지식을 정하고 경과 시간을 240초 직전으로 옮긴다(체력·멘탈은 넉넉히)."""
    def prepare(game):
        s = game.student
        s.knowledge = knowledge
        s.health = config.GAUGE_MAX
        s.mental = config.GAUGE_MAX
        s.elapsed = config.TOTAL_SECONDS - 1e-6
    return prepare


def set_health(value):
    """준비 함수: 체력을 value로 맞춘다."""
    def prepare(game):
        game.student.health = value
    return prepare


# ======================= 완료 기준: 실제 루프 한 바퀴 =======================

@pytest.mark.parametrize("knowledge, ending", [
    (520, config.ENDING_TOP),
    (300, config.ENDING_NORMAL),
    (120, config.ENDING_BARELY),
])
def test_real_loop_title_play_graduation_restart_esc(monkeypatch, isolated_record_path,
                                                    knowledge, ending):
    """Enter -> 1/2/3 키 -> 240초 강제 졸업 -> R -> ESC 를 실제 Game.run() 루프로 확인."""
    g = Game()
    steps = [
        ("enter", None, [key(pygame.K_RETURN)]),
        ("after_enter", None, []),
        ("key3", None, [key(pygame.K_3)]),
        ("after_key3", None, []),
        ("key1_in_cooldown", None, [key(pygame.K_1)]),
        ("after_key1", None, []),
        ("force_end", force_graduation(knowledge), []),
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
    assert after3["cooldown"] > 0
    # 쿨타임 안의 1키는 무시
    after1 = by_label(script, "after_key1")
    assert after1["health"] == after3["health"]
    # 강제 졸업 -> 엔딩 화면, 지식에 맞는 엔딩
    on_ending = by_label(script, "on_ending")
    assert on_ending["state"] == config.STATE_ENDING
    assert on_ending["ending"] == ending
    assert on_ending["best"] == knowledge
    # 엔딩 화면의 3키는 무시
    assert by_label(script, "r")["knowledge"] == knowledge
    # R -> 새 판, 모든 값 초기화
    after_r = by_label(script, "after_r")
    assert after_r["state"] == config.STATE_PLAYING
    assert after_r["ending"] is None
    assert after_r["knowledge"] == config.KNOWLEDGE_START
    assert after_r["health"] == config.HEALTH_START
    assert after_r["mental"] == config.MENTAL_START
    assert after_r["elapsed"] < config.DECAY_INTERVAL
    # 최고 기록은 유지되고 파일에도 저장됨
    assert after_r["best"] == knowledge
    with open(isolated_record_path, encoding="utf-8") as f:
        assert json.load(f) == {config.RECORD_KEY: knowledge}


def test_real_loop_leave_by_study_key_then_restart(monkeypatch, isolated_record_path):
    """체력 3에서 3키 공부 -> 그 프레임에 바로 휴학 엔딩 -> R -> ESC (실제 루프)."""
    g = Game()
    steps = [
        ("enter", None, [key(pygame.K_RETURN)]),
        ("key3", set_health(3), [key(pygame.K_3)]),
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
    assert after3["best"] == config.STUDY_KNOWLEDGE  # 휴학도 기록 저장
    after_r = by_label(script, "after_r")
    assert after_r["state"] == config.STATE_PLAYING
    assert after_r["health"] == config.HEALTH_START


def test_real_loop_click_button(monkeypatch):
    """실제 루프에서 마우스 왼쪽 클릭으로 학식 버튼을 누르면 체력 +20."""
    g = Game()
    feed_center = g.buttons[config.ACTION_FEED].rect.center
    steps = [
        ("enter", None, [key(pygame.K_RETURN)]),
        ("click", set_health(50), [pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, pos=feed_center, button=pygame.BUTTON_LEFT)]),
        ("after_click", None, []),
        ("esc", None, [key(pygame.K_ESCAPE)]),
    ]
    script = run_script(g, steps, monkeypatch)
    assert by_label(script, "after_click")["health"] == 50 + config.FEED_HEALTH


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
    ("SECONDS_PER_GRADE", 60), ("MAX_GRADE", 4), ("TOTAL_SECONDS", 240),
    ("EXAM_SECONDS", 15), ("FONT_NAME", "malgungothic"),
    ("GAUGE_MIN", 0), ("GAUGE_MAX", 100),
    ("HEALTH_START", 80), ("MENTAL_START", 80), ("KNOWLEDGE_START", 0),
    ("HEALTH_DECAY_PER_SEC", 1), ("MENTAL_DECAY_PER_SEC", 1), ("MENTAL_DECAY_PER_SEC_EXAM", 2),
    ("DECAY_INTERVAL", 1.0), ("LOW_GAUGE_LIMIT", 30),
    ("FEED_HEALTH", 20), ("REST_MENTAL", 20), ("REST_KNOWLEDGE", -2),
    ("STUDY_HEALTH", -5), ("STUDY_MENTAL", -8),
    ("STUDY_KNOWLEDGE", 10), ("STUDY_KNOWLEDGE_EXAM", 20), ("ACTION_COOLDOWN", 1.0),
    ("MENTAL_SMILE_MIN", 60), ("MENTAL_FLAT_MIN", 30),
    ("BASE_RADIUS", 40), ("RADIUS_PER_GRADE", 10), ("GLASSES_GRADE", 3),
    ("TOP_GRADUATE_KNOWLEDGE", 500), ("NORMAL_GRADUATE_KNOWLEDGE", 300),
    ("ENDING_LEAVE", "휴학"), ("ENDING_TOP", "수석 졸업"),
    ("ENDING_NORMAL", "무사 졸업"), ("ENDING_BARELY", "아슬아슬 졸업"),
    ("RECORD_FILENAME", "record.json"),
    ("FEED_BUTTON_TEXT", "학식 먹이기 [1]"), ("REST_BUTTON_TEXT", "쉬게 하기 [2]"),
    ("STUDY_BUTTON_TEXT", "공부시키기 [3]"),
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
    "Enter (타이틀 화면)",
    "R (엔딩 화면)",
    "| 학식 먹이기 | +20 | - | - |",
    "| 쉬게 하기 | - | +20 | -2 |",
    "| 공부시키기 | -5 | -8 | +10 (시험 기간 +20) |",
    "수석 졸업(500 이상) / 무사 졸업(300~499) / 아슬아슬 졸업(300 미만)",
    "쿨타임 1초",
    "마지막 15초",
])
def test_readme_mentions(text):
    """README 의 실행·빌드 명령, 조작키, 수치가 코드·기획서와 같다."""
    assert text in _readme(), text


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
