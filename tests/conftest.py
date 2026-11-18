"""검수팀 테스트 공통 설정: 화면 없는 드라이버와 프로젝트 루트 import 경로."""

import os
import sys

# pygame을 import하기 전에 화면 없는(dummy) 드라이버를 쓰도록 설정
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
