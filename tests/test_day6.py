"""6일차 검수: 최고 기록(기능 13), 경로 처리, 밸런스(엔딩 3종 + 휴학 실제 도달).

완료 기준: 엔딩 3종을 모두 볼 수 있음.
conftest.py의 autouse 픽스처가 config.RECORD_PATH를 임시 폴더로 돌려 두었다.
"""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import ast  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
from conftest import PROJECT_ROOT, press  # noqa: E402
from game import Game  # noqa: E402
from student import judge_ending  # noqa: E402

# (M단위) 졸업 등급 시간 기준은 config 상수라 '무사 졸업' 시각은 두 기준의 가운데로 잡는다
NORMAL_SECONDS = (config.TOP_GRADUATE_SECONDS + config.NORMAL_GRADUATE_SECONDS) / 2

FRAME = 1 / 60


class RecordingFont:
    """render에 넘긴 글자를 기록하는 폰트 래퍼."""

    def __init__(self, font):
        self.font = font
        self.texts = []

    def render(self, text, *args, **kwargs):
        self.texts.append(text)
        return self.font.render(text, *args, **kwargs)


def title_texts(g):
    """타이틀 화면을 그리고 그려진 글자 목록을 돌려준다."""
    assert g.state == config.STATE_TITLE
    small, big = RecordingFont(g.font), RecordingFont(g.title_font)
    g.font, g.title_font = small, big
    g.draw()
    return small.texts + big.texts


def write_raw(path, text):
    Path(path).write_text(text, encoding="utf-8")


def read_record(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# (H단위) record.json 은 이제 4개 키 {"best_knowledge", "money", "fame", "upgrades"} 를 저장한다
# (기획서 10절). 예전 테스트의 "최고 기록" 의미는 best_knowledge 값으로 그대로 확인한다.
RECORD_KEYS = {config.RECORD_KEY, config.RECORD_MONEY_KEY, config.RECORD_FAME_KEY,
               config.RECORD_UPGRADES_KEY}


def best_in_file(path):
    """record.json 이 4개 키 형식인지 확인하고 최고 기록(best_knowledge)을 돌려준다."""
    data = read_record(path)
    assert set(data) == RECORD_KEYS, data
    return data[config.RECORD_KEY]


def graduate_with(g, knowledge, seconds=200.0):
    """게임 중 g를 지식 knowledge로 seconds초 무렵 졸업시킨다(update 경로).

    (L단위, 기획서 11절) 졸업은 4학년에서 누적 지식이 1100 이상이 되는 순간이라
    knowledge는 졸업 지식 이상이어야 한다. 등급은 걸린 시간(기본 200초 -> 수석)으로 정해진다.
    """
    assert g.state == config.STATE_PLAYING
    assert knowledge >= config.GRADUATION_KNOWLEDGE
    g.student.knowledge = knowledge
    g.student.elapsed = seconds - FRAME
    g.update(FRAME)
    assert g.state == config.STATE_ENDING
    assert g.ending != config.ENDING_LEAVE


def leave_with(g, knowledge):
    """게임 중 g를 지식 knowledge로 휴학시킨다(자연 감소로 체력 0)."""
    assert g.state == config.STATE_PLAYING
    g.student.knowledge = knowledge
    g.student.health = 1
    g.update(1.0)
    assert g.ending == config.ENDING_LEAVE
    assert g.student.knowledge == knowledge


@pytest.fixture
def rec(isolated_record_path):
    """conftest가 정한 임시 record.json 경로(아직 파일 없음)."""
    assert not os.path.exists(isolated_record_path)
    yield isolated_record_path
    pygame.quit()


# ======================= 기능 13: 최고 기록 =======================

def test_record_path_is_redirected_by_conftest(rec):
    g = Game()
    assert g.record_path == rec
    assert os.path.dirname(rec) != PROJECT_ROOT


def test_no_file_means_zero(rec):
    g = Game()
    assert g.best_record == 0
    assert "최고 기록: 지식 0" in title_texts(g)
    assert not os.path.exists(rec)  # 읽기만 하고 파일을 만들지 않는다


def test_record_path_argument_used(tmp_path):
    p = tmp_path / "other.json"
    write_raw(p, '{"best_knowledge": 77}')
    g = Game(record_path=str(p))
    assert g.best_record == 77
    pygame.quit()


@pytest.mark.parametrize("finish", ["leave", "graduate"])
def test_saved_on_any_ending(rec, finish):
    g = Game()
    g.start_new_game()
    if finish == "leave":
        leave_with(g, 120)
    else:   # (L단위) 졸업하려면 지식 1100 이상 (M단위 2200 이상)
        graduate_with(g, 2320)
    knowledge = 120 if finish == "leave" else 2320
    assert best_in_file(rec) == knowledge
    assert g.best_record == knowledge


def test_leave_by_study_action_saves(rec):
    g = Game()
    g.start_new_game()
    g.student.knowledge = 40
    g.student.health = 5
    assert g.do_action(config.ACTION_STUDY)
    assert g.ending == config.ENDING_LEAVE
    # (M단위) 체력 5는 피곤(30 미만) -> 공부 지식 10 x 0.7 = 7
    assert best_in_file(rec) == 47


def test_save_format_exact(rec):
    g = Game()
    g.start_new_game()
    graduate_with(g, 2920, seconds=NORMAL_SECONDS)   # 수석 기준 초과 무사 기준 이하 = 무사 졸업
    assert g.ending == config.ENDING_NORMAL
    data = read_record(rec)
    # (H단위) 4개 키 형식. 무사 졸업 보너스 100(명성 0), 업그레이드는 모두 0레벨
    assert data == {"best_knowledge": 2920, "money": 100, "fame": 0,
                    "upgrades": {uid: 0 for uid in config.UPGRADE_IDS}}
    assert type(data["best_knowledge"]) is int


# (H단위) 판이 끝나면 연구비 등과 함께 언제나 저장하므로 파일은 항상 다시 쓰인다(팀장 승인).
# 최고 기록은 여전히 더 클 때만 바뀐다.
# (L단위) 졸업 지식이 1100 이상이므로 기준 기록을 1300으로 올렸다. 지식 0은 휴학으로 끝낸다
@pytest.mark.parametrize("new, expected_best, rewritten", [
    (1299, 1300, True), (1300, 1300, True), (1301, 1301, True), (0, 1300, True),
])
def test_only_higher_updates(rec, new, expected_best, rewritten):
    original = '{"best_knowledge":   1300}'  # 일부러 공백을 넣어 다시 쓰였는지 구별
    write_raw(rec, original)
    g = Game()
    assert g.best_record == 1300
    g.start_new_game()
    if new >= config.GRADUATION_KNOWLEDGE:
        graduate_with(g, new)
    else:
        leave_with(g, new)
    assert g.best_record == expected_best
    assert best_in_file(rec) == expected_best
    assert (Path(rec).read_text(encoding="utf-8") != original) is rewritten


def test_new_game_loads_and_title_shows(rec):
    g = Game()
    g.start_new_game()
    graduate_with(g, 2445)
    pygame.quit()
    g2 = Game()
    assert g2.best_record == 2445
    texts = title_texts(g2)
    assert "최고 기록: 지식 2445" in texts


def test_restart_many_rounds_keeps_max(rec):
    g = Game()
    g.start_new_game()
    # (L단위) 졸업(짝수 번째)은 지식 1100 이상이어야 하므로 값을 올렸다
    # (M단위) 졸업 지식 2200 이상
    sequence = [2200, 450, 2300, 2450, 2230, 2600, 2210]
    expected = 0
    for i, k in enumerate(sequence):
        if i % 2:
            leave_with(g, k)
        else:
            graduate_with(g, k)
        expected = max(expected, k)
        assert g.best_record == expected
        assert best_in_file(rec) == expected
        press(g, pygame.K_r)
        assert g.state == config.STATE_PLAYING
        assert g.student.knowledge == 0  # 새 판은 초기화
    assert g.best_record == 2600
    pygame.quit()
    assert Game().best_record == 2600


@pytest.mark.parametrize("content", [
    "",                                   # 빈 파일
    "{",                                  # 깨진 JSON
    "not json at all",
    "[1, 2, 3]",                          # 리스트
    "500",                                # 숫자만
    '"500"',                              # 문자열만
    "null",
    "{}",                                 # 키 없음
    '{"best": 500}',                      # 다른 키
    '{"best_knowledge": "500"}',          # 문자열 값
    '{"best_knowledge": -5}',             # 음수
    '{"best_knowledge": true}',           # bool
    '{"best_knowledge": false}',
    '{"best_knowledge": 12.5}',           # float
    '{"best_knowledge": null}',
    '{"best_knowledge": [500]}',
    '{"best_knowledge": {"v": 1}}',
    '{"best_knowledge": NaN}',            # json 모듈이 허용하는 float
    '{"best_knowledge": Infinity}',
])
def test_invalid_record_is_zero(rec, content):
    write_raw(rec, content)
    g = Game()
    assert g.best_record == 0
    assert "최고 기록: 지식 0" in title_texts(g)


def test_invalid_bytes_and_bom_are_zero(rec):
    Path(rec).write_bytes(b"\xff\xfe\x00garbage")
    assert Game().best_record == 0
    Path(rec).write_bytes(b'\xef\xbb\xbf{"best_knowledge": 10}')  # BOM이 붙은 UTF-8
    assert Game().best_record in (0, 10)  # 크래시만 없으면 된다


def test_broken_file_is_overwritten_by_next_record(rec):
    write_raw(rec, "{broken")
    g = Game()
    g.start_new_game()
    graduate_with(g, 2250)
    assert best_in_file(rec) == 2250


def test_record_path_is_directory_no_crash(tmp_path):
    """record_path가 폴더(읽기·쓰기 모두 OSError) -> 0, 저장 실패해도 크래시 없음."""
    g = Game(record_path=str(tmp_path))
    assert g.best_record == 0
    g.start_new_game()
    graduate_with(g, config.GRADUATION_KNOWLEDGE + 50, seconds=NORMAL_SECONDS)
    assert g.ending == config.ENDING_NORMAL
    assert g.save_best_record() is False
    g.draw()
    press(g, pygame.K_r)
    assert g.state == config.STATE_PLAYING
    pygame.quit()


def test_record_dir_missing_no_crash(tmp_path):
    p = tmp_path / "no_such_dir" / "record.json"
    g = Game(record_path=str(p))
    assert g.best_record == 0
    g.start_new_game()
    leave_with(g, 70)
    assert g.state == config.STATE_ENDING
    assert not p.exists()
    pygame.quit()


def test_save_returns_true_on_success(rec):
    g = Game()
    g.best_record = 9
    assert g.save_best_record() is True
    assert best_in_file(rec) == 9


def test_update_best_record_return_values(rec):
    g = Game()
    assert g.update_best_record(0) is False
    assert not os.path.exists(rec)  # 0판은 저장하지 않음(더 클 때만)
    assert g.update_best_record(5) is True
    assert g.update_best_record(5) is False
    assert best_in_file(rec) == 5


def test_update_best_record_only_called_from_end_game():
    src = (Path(PROJECT_ROOT) / "game.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    callers = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "update_best_record"):
                    callers.append(node.name)
    assert callers == ["end_game"]


def test_record_not_written_during_play(rec):
    g = Game()
    g.start_new_game()
    for _ in range(120):
        g.update(FRAME)
    g.do_action(config.ACTION_STUDY)
    assert not os.path.exists(rec)


# ======================= 경로 처리 =======================

def test_base_dir_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    base = config.get_base_dir()
    assert os.path.normcase(os.path.abspath(base)) == os.path.normcase(PROJECT_ROOT)
    assert os.path.exists(os.path.join(base, "main.py"))


def test_base_dir_frozen_uses_executable_folder(monkeypatch, tmp_path):
    exe_dir = tmp_path / "dist"
    exe_dir.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "main.exe"))
    assert os.path.normcase(config.get_base_dir()) == os.path.normcase(str(exe_dir))


def test_frozen_false_is_not_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python.exe"))
    assert os.path.normcase(config.get_base_dir()) == os.path.normcase(PROJECT_ROOT)


def test_record_constants():
    assert config.RECORD_FILENAME == "record.json"
    assert config.RECORD_KEY == "best_knowledge"
    # 원래 값(conftest가 바꾸기 전)은 루트/record.json 이어야 한다: 같은 식으로 다시 계산
    expected = os.path.join(config.get_base_dir(), config.RECORD_FILENAME)
    assert os.path.normcase(expected) == os.path.normcase(
        os.path.join(PROJECT_ROOT, "record.json"))


def test_default_record_path_read_at_construction(monkeypatch, tmp_path):
    """record_path=None이면 Game을 만드는 시점의 config.RECORD_PATH를 쓴다."""
    p = tmp_path / "late.json"
    write_raw(p, '{"best_knowledge": 31}')
    monkeypatch.setattr(config, "RECORD_PATH", str(p))
    g = Game()
    assert g.record_path == str(p)
    assert g.best_record == 31
    pygame.quit()


def test_gitignore_has_record_json():
    text = (Path(PROJECT_ROOT) / ".gitignore").read_text(encoding="utf-8")
    assert "record.json" in text.split()


# ======================= 완료 기준: 엔딩 3종 실제 도달 =======================

LEGACY_ACTION_GAP = 1.0   # 예전 쿨타임(1초). 사람이 행동하는 최소 간격으로만 쓴다


def play(g, policy, interval=LEGACY_ACTION_GAP, cap_seconds=1800):
    """타이틀에서 Enter -> 1/60초씩 update, interval초마다 policy(student)의 행동을 한다.

    policy가 None을 돌려주면 그 프레임엔 아무것도 안 한다. 엔딩이 나면 끝.
    (L단위) 시간 제한이 없으므로 cap_seconds(기본 30분)까지 엔딩이 없으면 멈춘다.
    """
    press(g, pygame.K_RETURN)
    assert g.state == config.STATE_PLAYING
    frames = 0
    # (G단위) 쿨타임은 없어졌지만 이 시나리오는 "1초(예전 쿨타임)마다 행동 가능"한 사람을 흉내 낸다
    wait = 0.0
    while g.state == config.STATE_PLAYING and frames < cap_seconds * 60:
        if wait <= 1e-9:
            action = policy(g.student)
            if action is not None:
                assert g.do_action(action)
                wait = interval
        if g.state != config.STATE_PLAYING:
            break
        g.update(FRAME)
        wait -= FRAME
        frames += 1
    return frames


def greedy(s):
    """탐욕: 체력·멘탈이 위험하면 회복, 아니면 공부.

    (M단위) 회복은 휴식에서만 되므로 체력이 위험해도 휴식한다(학식은 든든함 버프만 준다).
    """
    if s.health <= 30 or s.mental <= 30:
        return config.ACTION_REST
    return config.ACTION_STUDY


def make_steady(stop_at):
    """지식이 stop_at 이상이 되면 공부를 멈추고, 이후엔 낮은 쪽만 가끔 회복(휴식 -2 고려)."""
    def policy(s):
        if s.knowledge < stop_at:
            return greedy(s)
        if s.health <= 30 or s.mental <= 30:   # (M단위) 회복은 휴식에서만
            return config.ACTION_REST
        return None
    return policy


def care_only(s):
    """학식·휴식만: 지식은 0에서 늘지 않는다.

    (M단위) 회복은 휴식에서만 된다. 학식은 든든함이 끝났을 때만 먹인다(체력 감소 x0.5).
    """
    if s.health <= 50 or s.mental <= 50:
        return config.ACTION_REST
    if not s.is_full_buff_active():
        return config.ACTION_FEED
    return None


def assert_graduation(g, frames, ending):
    """(L단위) 졸업 엔딩: 등급은 졸업까지 걸린 시간, 그 순간 지식은 1100 이상."""
    assert g.ending == ending, (g.ending, g.student.graduation_time, g.student.knowledge)
    assert g.student.knowledge >= config.GRADUATION_KNOWLEDGE
    assert abs(g.student.graduation_time - frames * FRAME) <= FRAME + 1e-6
    assert g.student.health > 0 and g.student.mental > 0
    assert g.best_record == g.student.knowledge
    texts = []
    rec_font = RecordingFont(g.title_font)
    g.title_font = rec_font
    g.draw()  # 엔딩 화면(학사모 포함)이 그려진다
    texts += rec_font.texts
    assert ending in texts
    # (도트 재디자인) 학사모 몸통 점: 화면 가운데 열, 학사모 스프라이트 14번째 행
    cap_body = (config.SCREEN_CENTER_X, config.CAP_TOP_Y + 14 * config.CAP_PIXEL + 2)
    assert tuple(g.screen.get_at(cap_body))[:3] == config.COLOR_CAP


# (L단위) 실측(이벤트·자동 행동 끔, 탐욕 수동 행동): 1초 간격 176초 수석, 1.5초 286.5초 무사,
# 2.0초 420초 아슬아슬, 2.5초 570초 아슬아슬.
# (M단위) 회복 규칙·진급 기준·시간 기준(임시)이 바뀌어 어느 간격이 어느 등급인지는 밸런스 단위에서
# 다시 정한다. 그래서 여기서는 등급 분포를 고정하지 않고 불변식만 본다:
# 크래시 없이 졸업 엔딩으로 끝나고, 등급은 judge_ending(걸린 시간)과 같고, 자주 행동할수록 빨리 졸업한다.
def test_reach_top_graduate_greedy(rec):
    g = Game()
    t = time.perf_counter()
    frames = play(g, greedy)
    assert_graduation(g, frames, judge_ending(g.student.graduation_time))
    assert time.perf_counter() - t < 6


def test_reach_normal_graduate(rec):
    """(L단위) 1.5초마다 행동해도 졸업한다. (M단위) 등급은 걸린 시간 기준과 일치하는지만 본다."""
    g = Game()
    frames = play(g, greedy, interval=1.5)
    assert_graduation(g, frames, judge_ending(g.student.graduation_time))


def test_care_only_never_graduates(rec):
    """(L단위, 예전 '학식·휴식만 해도 아슬아슬 졸업') 지식이 0이면 30분이 지나도 졸업하지 않는다."""
    g = Game()
    frames = play(g, care_only, cap_seconds=1800)
    assert frames == 1800 * 60
    assert g.state == config.STATE_PLAYING and g.ending is None
    assert g.student.knowledge == 0 and g.student.get_grade() == 1


def test_reach_barely_graduate_slow_study(rec):
    """(L단위) 2초마다만 행동해도 졸업한다. (M단위) 1초 간격보다 늦게 졸업한다(등급은 걸린 시간 기준)."""
    fast = Game(record_path=rec + ".fast.json")   # 비교용 판은 다른 기록 파일에
    play(fast, greedy, interval=1.0)
    fast_time = fast.student.graduation_time
    pygame.quit()
    g = Game()
    frames = play(g, greedy, interval=2.0)
    assert_graduation(g, frames, judge_ending(g.student.graduation_time))
    assert g.student.graduation_time > fast_time


def test_reach_leave_by_only_study(rec):
    g = Game()
    play(g, lambda s: config.ACTION_STUDY)
    assert g.ending == config.ENDING_LEAVE
    assert g.student.elapsed < config.CYCLE_SECONDS
    assert g.student.health == 0 or g.student.mental == 0
    assert best_in_file(rec) == g.student.knowledge


def test_reach_leave_by_idle(rec):
    g = Game()
    frames = play(g, lambda s: None)
    assert g.ending == config.ENDING_LEAVE
    assert frames == 65 * 60
    # (H단위) 판이 끝나면 언제나 저장한다. 지식 0 -> 최고 기록은 0 그대로
    assert best_in_file(rec) == 0


def test_all_endings_in_one_session_with_restart(rec):
    """한 세션에서 R로 이어서 휴학 -> 졸업 -> 졸업 -> 졸업을 보고 최고 기록이 유지된다.

    (L단위) 등급이 걸린 시간으로 바뀌어 행동 간격(2.0 / 1.5 / 1.0초)으로 등급을 나눈다.
    (M단위) 등급 분포는 밸런스 단위에서 다시 정하므로, 각 판의 등급이 걸린 시간 기준과 같고
    간격이 짧을수록 빨리 졸업하는 것만 본다. 수석·무사·아슬아슬 3종 자체는 judge_ending 경계 테스트로 본다.
    """
    g = Game()
    seen = []
    times = []
    best = 0
    for policy, interval in ((lambda s: config.ACTION_STUDY, 1.0), (greedy, 2.0),
                             (greedy, 1.5), (greedy, 1.0)):
        if g.state == config.STATE_ENDING:
            press(g, pygame.K_r)
            g.state = config.STATE_TITLE  # play()가 Enter부터 시작하므로 타이틀로 맞춘다
        play(g, policy, interval=interval)
        seen.append(g.ending)
        times.append(g.student.graduation_time)
        best = max(best, g.student.knowledge)
        assert g.best_record == best
    assert seen[0] == config.ENDING_LEAVE
    for ending, seconds in zip(seen[1:], times[1:]):
        assert ending == judge_ending(seconds)
    assert times[1] > times[2] > times[3]
    assert best_in_file(rec) == best


@pytest.mark.parametrize("interval", [1.0, 1.5, 2.0, 2.5, 3.0, 4.0])
def test_balance_human_like_interval(rec, interval):
    """사람처럼 interval초마다 한 번만 행동하는 탐욕 전략도 졸업한다(개발팀 시뮬레이션 대조).

    (L단위) 실측 1.0초 176초 … 4.0초 1308초. (M단위) 분포는 고정하지 않고 졸업·등급 일치만 본다.
    """
    g = Game()
    press(g, pygame.K_RETURN)
    wait = 0.0
    while g.state == config.STATE_PLAYING:
        if wait <= 1e-9:   # (G단위) 쿨타임 없음: interval(>=1.0초)마다 행동
            g.do_action(greedy(g.student))
            wait = interval
        if g.state != config.STATE_PLAYING:
            break
        g.update(FRAME)
        wait -= FRAME
    assert g.student.has_graduated()
    assert g.ending == judge_ending(g.student.graduation_time), (interval, g.ending)


# ======================= 정적 검사 =======================

GAME_FILES = ["main.py", "config.py", "game.py", "student.py", "button.py"]
ALLOWED_IMPORTS = {"pygame", "json", "sys", "os", "random", "config", "game", "student", "button"}


@pytest.mark.parametrize("name", GAME_FILES)
def test_only_allowed_imports(name):
    tree = ast.parse((Path(PROJECT_ROOT) / name).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in ALLOWED_IMPORTS, (name, alias.name)
        elif isinstance(node, ast.ImportFrom):
            assert node.module.split(".")[0] in ALLOWED_IMPORTS, (name, node.module)


def test_game_py_docstrings_and_no_magic_numbers():
    tree = ast.parse((Path(PROJECT_ROOT) / "game.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            assert ast.get_docstring(node), node.name
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            assert node.value in (0, 1), node.value


def test_config_get_base_dir_docstring():
    assert config.get_base_dir.__doc__


def test_no_image_or_sound_loading():
    for name in GAME_FILES:
        src = (Path(PROJECT_ROOT) / name).read_text(encoding="utf-8")
        for bad in ("image.load", "mixer", "Sound(", "pygame.draw.polygon",
                    "pygame.draw.ellipse", "pygame.draw.lines", "pygame.draw.aaline"):
            assert bad not in src, (name, bad)


def test_project_root_has_no_record_json_from_tests():
    """테스트는 루트에 record.json을 만들지 않는다(conftest autouse 픽스처)."""
    assert not os.path.exists(os.path.join(PROJECT_ROOT, "record.json"))
