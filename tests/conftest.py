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
