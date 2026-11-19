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
