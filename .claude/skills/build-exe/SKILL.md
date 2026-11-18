---
name: build-exe
description: PyInstaller로 Windows 실행 파일을 만들 때 사용.
---

# 실행 파일 빌드 (PyInstaller)

## 1. 준비

```
py -3.12 -m pip install pyinstaller
```

이 PC는 Python 3.14도 있으므로 반드시 3.12로 빌드한다(pygame 2.6은 3.12용). `pyinstaller.exe`가 PATH에 없을 수 있어 `py -3.12 -m PyInstaller` 형태로 실행한다.

## 2. 빌드 명령

프로젝트 루트(`main.py`가 있는 폴더)에서:

```
py -3.12 -m PyInstaller --onefile --noconsole main.py
```

- 일반 환경에서는 `pyinstaller --onefile --noconsole main.py`와 같다.
- 실행 파일 이름을 바꾸려면 `--name 제자키우기`를 추가할 수 있다(선택).
- 결과: `dist/main.exe` (또는 `--name`으로 지정한 이름). `build/`, `main.spec`은 중간 산출물.

## 3. record.json 경로 처리

`--onefile` exe는 실행할 때 임시 폴더(`sys._MEIPASS`)에 풀려서 돌아간다. `__file__` 기준으로 저장하면 임시 폴더에 저장되어 다음 실행 때 기록이 사라진다. 그래서 다음처럼 처리한다(config.py 또는 game.py):

```python
import os
import sys

def get_base_dir():
    """record.json을 저장할 폴더를 돌려준다. exe면 exe 옆, 아니면 main.py 옆."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

RECORD_PATH = os.path.join(get_base_dir(), "record.json")
```

- `__file__`은 `main.py`와 같은 폴더(루트)에 있는 모듈 기준이어야 한다.
- 읽을 때 파일이 없거나 JSON이 깨지면 최고 기록 0으로 처리한다(`FileNotFoundError`, `json.JSONDecodeError`, `ValueError`).
- `record.json`은 `.gitignore`에 넣는다.

## 4. 빌드 후 dist/ 확인 항목

- [ ] `dist/` 안에 exe 파일 하나만 있다(--onefile).
- [ ] exe를 더블클릭하면 콘솔 창 없이 800×600 게임 창이 뜬다(--noconsole).
- [ ] 타이틀·게임·엔딩 화면의 한글이 네모(□)로 깨지지 않는다.
- [ ] 한 판을 끝낸 뒤 exe와 **같은 폴더**에 `record.json`이 생긴다.
- [ ] exe를 다시 실행하면 타이틀에 최고 기록이 그대로 보인다.
- [ ] exe를 다른 폴더로 복사해 실행해도 동작한다(그 폴더에 새 record.json).
- [ ] (7일차) 파이썬이 없는 PC에서도 실행된다 — 사용자가 직접 확인.

## 5. 자주 나는 오류와 해결법

| 증상 | 원인 | 해결 |
|---|---|---|
| `'pyinstaller'은(는) 내부 또는 외부 명령...이 아닙니다` | Scripts 폴더가 PATH에 없음 | `py -3.12 -m PyInstaller ...`로 실행 |
| exe 실행 직후 바로 꺼짐 | 예외 발생, --noconsole이라 메시지가 안 보임 | `--noconsole` 없이 다시 빌드해 콘솔에서 오류 확인 |
| `ModuleNotFoundError: pygame` (빌드 중/실행 중) | 다른 파이썬(3.14)으로 빌드했거나 그 파이썬에 pygame 없음 | `py -3.12 -m pip install pygame==2.6.1` 후 `py -3.12 -m PyInstaller`로 다시 빌드 |
| 기록이 저장 안 되거나 매번 0 | `__file__` 기준 경로라 임시 폴더에 저장됨 | 3절의 `sys.frozen` / `sys.executable` 처리 |
| 한글이 네모로 나옴 | `Font(None)` 사용 또는 폰트 이름 오타 | `pygame.font.SysFont("malgungothic", 크기)` |
| 백신이 exe를 차단/삭제 | --onefile exe의 오탐 | 백신 예외 처리 또는 사용자에게 안내(코드 문제 아님) |
| `PermissionError` 빌드 실패 | 이전 exe가 실행 중이라 덮어쓰기 불가 | 실행 중인 게임을 끄고 `dist/`, `build/` 삭제 후 재빌드 |
| 경로가 너무 길다는 오류 | 프로젝트 폴더 경로가 김 | 짧은 경로(예: `C:\jeja-game`)로 옮겨 빌드 |

## 6. Git

- `build/`, `dist/`, `*.spec`, `record.json`은 커밋하지 않는다(`.gitignore`).
- 제출용 exe가 필요하면 GitHub Release 첨부 등은 사용자가 결정한다.
