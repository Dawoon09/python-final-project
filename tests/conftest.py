"""검수팀 테스트 공통 설정: 화면 없는 드라이버와 프로젝트 루트 import 경로."""

import os
import sys

# pygame을 import하기 전에 화면 없는(dummy) 드라이버를 쓰도록 설정
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pygame  # noqa: E402
import pytest  # noqa: E402


def press(game, key):
    """game에 키 하나를 누른 KEYDOWN 이벤트를 넣는다."""
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


@pytest.fixture(autouse=True)
def isolated_record_path(tmp_path, monkeypatch):
    """(6일차) 모든 테스트에서 최고 기록 파일을 임시 폴더로 돌린다.

    어떤 테스트도 프로젝트 루트에 실제 record.json을 만들거나 읽지 않게 한다.
    Game(record_path=None)은 생성 시점의 config.RECORD_PATH를 쓰므로 이것으로 충분하다.
    """
    import config

    path = str(tmp_path / "record.json")
    monkeypatch.setattr(config, "RECORD_PATH", path)
    yield path


@pytest.fixture
def no_events(monkeypatch):
    """(C단위) 랜덤 이벤트를 완전히 끈다: 학년당 최대 이벤트 수를 0으로.

    EVENT_CHANCE=0만으로는 최소 보장(학년 안 11.25초마다) 때문에 이벤트가 뜨므로
    최대값을 0으로 막는다. 이벤트가 생기기 전 단위(1~6일차, 연출)의 테스트가
    예전 규칙 그대로 돌게 하는 용도다.
    """
    import config

    monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 0)


# 이벤트가 없다고 가정하고 쓴 기존 테스트 파일들. 이 파일들에는 no_events가 자동 적용된다.
# 새 이벤트 테스트(test_events.py)는 여기 없으므로 이벤트가 켜진 채로 돈다.
EVENTS_OFF_FILES = {
    "test_day1.py", "test_day2.py", "test_day3.py", "test_day4.py", "test_day5.py",
    "test_day6.py", "test_final.py", "test_pixel_ui.py", "test_effects.py",
}


@pytest.fixture(autouse=True)
def _events_off_for_legacy_tests(request):
    """기존 테스트 파일(EVENTS_OFF_FILES)이면 no_events 픽스처를 자동으로 켠다."""
    if os.path.basename(str(request.node.fspath)) in EVENTS_OFF_FILES:
        request.getfixturevalue("no_events")


@pytest.fixture
def no_auto(monkeypatch):
    """(G단위) 자동 행동을 끈다: 자동 행동 간격을 아주 크게(게임 한 판보다 길게) 바꾼다.

    방치형 전환(기획서 10절) 전에 쓴 테스트는 "행동은 테스트가 직접 시킨다"고 가정한다.
    이 픽스처를 켜면 update가 자동 행동을 하지 않으므로, 테스트는 game.do_action(name)으로
    원하는 행동만 실행해 게이지·자연 감소·이벤트 규칙을 예전처럼 확인할 수 있다.
    Game을 만들기 전에 적용되어야 한다(reset_round가 이 값으로 auto_timer를 채운다).
    """
    import config

    monkeypatch.setattr(config, "AUTO_ACTION_INTERVAL", NO_AUTO_INTERVAL)


NO_AUTO_INTERVAL = 1.0e9   # 자동 행동을 끌 때 쓰는 간격(초). 어떤 테스트의 게임 시간보다 길다

# 자동 행동이 없다고 가정하고 쓴 기존 테스트 파일들. 이 파일들에는 no_auto가 자동 적용된다.
# 새 G단위 테스트(test_idle_g.py)는 여기 없으므로 자동 행동이 켜진 채로 돈다.
AUTO_OFF_FILES = EVENTS_OFF_FILES | {
    "test_events.py", "test_event_ui.py", "test_balance_events.py",
}


@pytest.fixture(autouse=True)
def _auto_off_for_legacy_tests(request):
    """기존 테스트 파일(AUTO_OFF_FILES)이면 no_auto 픽스처를 자동으로 켠다."""
    if os.path.basename(str(request.node.fspath)) in AUTO_OFF_FILES:
        request.getfixturevalue("no_auto")


def act(game, name):
    """(G단위) 행동 name(feed/rest/study)을 game.do_action으로 바로 실행하고 결과를 돌려준다.

    예전 테스트의 "키 1/2/3을 눌러 행동" 자리에 쓴다(키 1/2/3은 이제 방침 선택이다).
    """
    return game.do_action(name)


@pytest.fixture
def playing_game():
    """(5일차부터 타이틀에서 시작) Game을 만들고 타이틀에서 Enter를 눌러 게임 진행 중으로 만든다."""
    import config
    from game import Game

    g = Game()
    assert g.state == config.STATE_TITLE
    press(g, pygame.K_RETURN)
    assert g.state == config.STATE_PLAYING
    yield g
    pygame.quit()


# ---------------------------------------------------------------
# (L단위, 기획서 11절) 학년은 시간이 아니라 누적 지식으로 오른다.
# 예전 테스트의 "elapsed = 60 x (학년-1)로 학년 맞추기" 자리에 쓰는 도우미.
# ---------------------------------------------------------------
def grade_knowledge(grade):
    """grade학년이 되는 최소 누적 지식을 돌려준다: 1학년 0, 2학년 200, 3학년 450, 4학년 750."""
    import config

    if grade <= config.FIRST_GRADE:
        return config.KNOWLEDGE_START
    return config.GRADE_GOALS[grade - config.FIRST_GRADE - 1]


def reach_grade(student, grade):
    """student의 지식을 grade학년 목표까지 올리고 진급 판정(promote)으로 학년을 올린다.

    지식이 이미 그보다 많으면 지식은 그대로 둔다. 실제 진급 규칙(지식 기준)을 그대로 거친다.
    """
    student.knowledge = max(student.knowledge, grade_knowledge(grade))
    student.promote()
    assert student.get_grade() == grade
    return student


def graduate(student, seconds):
    """student를 seconds초에 졸업시킨다: 경과 시간을 맞추고 지식을 졸업 목표까지 올려 promote."""
    import config

    student.elapsed = seconds
    student.knowledge = max(student.knowledge, config.GRADUATION_KNOWLEDGE)
    student.promote()
    assert student.has_graduated()
    return student


# ---------------------------------------------------------------
# (문서 정리, docs/final-spec) 기획서는 최종 게임 한 문서(1~10절 + 부록 변경 이력)다.
# 문서 검사는 절 번호 대신 제목 글자로 구역을 찾는다(절 번호가 바뀌어도 의도가 그대로 남게).
# ---------------------------------------------------------------
SPEC_PATH = os.path.join(PROJECT_ROOT, "docs", "기획서.md")
JEJA_SPEC_PATH = os.path.join(PROJECT_ROOT, ".claude", "skills", "jeja-spec", "SKILL.md")
APPENDIX_HEADING = "부록: 변경 이력"  # 기획서 맨 아래 "## 부록: 변경 이력"
DEV_HISTORY_HEADING = "개발 과정"  # 기획서 "## 8. 개발 과정" (예전 수치가 기록으로 남는 절)


def read_doc(path=SPEC_PATH):
    """문서 전체 글자를 utf-8로 읽어 돌려준다."""
    with open(path, encoding="utf-8") as f:
        return f.read()


def doc_section(text, heading):
    """제목이 heading인 첫 마크다운 구역(제목 줄 포함)을 돌려준다.

    제목 앞 절 번호("2. ")는 없어도 된다: "게임 규칙"은 "## 2. 게임 규칙"을 찾는다.
    제목 뒤 괄호 설명도 없어도 된다: "졸업 등급"은 "### 졸업 등급 (걸린 게임 시간, …)"을 찾는다.

    "## …"이면 다음 "## " 제목 전까지, "### …"이면 다음 "## "/"### " 제목 전까지다.
    해당 제목이 없으면 AssertionError.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        title = line.lstrip("#").strip()
        name = title.split(" ", 1)[-1] if title[:1].isdigit() else title
        if line.startswith("#") and (name == heading or name.startswith(heading + " (")):
            level = len(line) - len(line.lstrip("#"))
            end = len(lines)
            for j in range(i + 1, len(lines)):
                other = lines[j]
                if other.startswith("#"):
                    other_level = len(other) - len(other.lstrip("#"))
                    if other_level <= level and other[other_level:other_level + 1] == " ":
                        end = j
                        break
            return "\n".join(lines[i:end])
    raise AssertionError("제목 없음: " + heading)


def spec_rule_text(text=None):
    """기획서에서 '지금 규칙'을 적은 부분: 1절부터 부록 전까지, 단 개발 과정(기록) 절은 뺀다."""
    if text is None:
        text = read_doc()
    body = text[text.index("## 1."):text.index("## " + APPENDIX_HEADING)]
    # 1절 앞의 머리말(원래 PDF 기획 소개)도 기록이라 뺀다
    return body.replace(doc_section(body, DEV_HISTORY_HEADING), "")


def spec_appendix(text=None):
    """기획서의 부록 변경 이력 구역."""
    if text is None:
        text = read_doc()
    return doc_section(text, APPENDIX_HEADING)
