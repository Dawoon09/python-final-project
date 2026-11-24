# 제자 키우기

pygame 방치형 육성 게임(대학교 1학년 과제). 교수가 제자를 누적 지식으로 진급·졸업시키고, 졸업 뒤 환생하거나 대학원에 간다.

## 기준

- 규칙·수치의 유일한 기준: `docs/기획서.md`. 빠른 기준표·테스트 계약 이름: 스킬 `jeja-spec`. 변경 기록: 기획서 부록 "변경 이력".
- 기획서와 다르게 구현할 이유가 생기면 바꾸기 전에 사용자에게 묻는다. 기획서에 없는 기능은 추가하지 않는다.

## 실행

- 게임: `py -3.12 main.py` (이 PC에는 3.14도 있으니 3.12를 지정)
- 테스트: `py -3.12 -m pytest -q` (`tests/`, `SDL_VIDEODRIVER=dummy`, 약 3분)
- 빌드: 스킬 `build-exe`

## 제약

- Python 3.12, pygame 2.6, 표준 라이브러리 json·sys·os·random만. 예외: 개발 도구 pytest, PyInstaller.
- random은 랜덤 이벤트 전용, Game의 `random.Random(시드)` 인스턴스만 쓴다.
- 이미지·사운드 파일 금지, 그림은 `pygame.draw`만(예외: README 스크린샷 `docs/images/`).
- 폰트 `pygame.font.SysFont("malgungothic", 크기)` (`Font(None)`은 한글이 깨짐).
- 클래스는 Student(`student.py`), Button(`button.py`), Game(`game.py`) 3개. 진입점 `main.py`. 모든 수치·문구는 `config.py` 상수(다른 파일에 매직 넘버 금지).
- 모든 클래스·함수에 한국어 docstring(한두 줄). 읽기 쉬운 코드.
- `.py` 파일은 CRLF 줄바꿈을 유지한다.
- `src/final_project/`, `tests/test_core.py`, `pyproject.toml`은 과제 템플릿 예제다. 지우지 않는다.

## 작업 방식

- 개발: 에이전트 `dev-team` / 검수: 에이전트 `qa-team`(`tests/`만 수정).
- 단위 하나씩 개발 → 검수 → (불통과면 수정 → 재검수). 같은 단위 3회 불통과면 멈춘다.
- 커밋: 검수 통과한 단위마다 한국어 메시지로, 리드가 한다. push는 사용자 확인 뒤.
- 작업 브랜치: `feat/idle-depth` (지난 브랜치는 PR #1~#4로 main에 합쳐짐).
