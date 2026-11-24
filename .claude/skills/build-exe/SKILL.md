---
name: build-exe
description: PyInstaller로 Windows 실행 파일을 만들 때 사용.
---

# 실행 파일 빌드 (PyInstaller)

프로젝트 루트에서 반드시 Python 3.12로(pygame 2.6은 3.12용, `pyinstaller.exe`는 PATH에 없을 수 있음):

```
py -3.12 -m pip install pyinstaller
py -3.12 -m PyInstaller --onefile --noconsole main.py
```

- 결과 `dist/main.exe`(`--name 제자키우기`로 이름 변경 가능). `build/`, `dist/`, `*.spec`, `record.json`은 커밋하지 않는다(`.gitignore`).
- record.json 경로는 이미 `config.get_base_dir()`/`RECORD_PATH`가 처리한다: `sys.frozen`이면 `sys.executable` 폴더(`--onefile`은 임시 폴더 `sys._MEIPASS`에서 돌기 때문), 아니면 `main.py` 폴더. 없거나 깨진 파일은 모두 0으로 읽는다.

## 빌드 후 확인

- [ ] `dist/`에 exe 하나, 더블클릭 시 콘솔 없이 800×600 창, 한글이 □로 깨지지 않음
- [ ] 한 판 뒤 exe와 같은 폴더에 `record.json`, 다시 실행하면 최고 기록·명성·연구비·업그레이드 유지
- [ ] 다른 폴더로 복사해도 동작(그 폴더에 새 record.json), 파이썬 없는 PC 실행은 사용자가 확인

## 자주 나는 오류

| 증상 | 해결 |
|---|---|
| `pyinstaller` 명령 없음 | `py -3.12 -m PyInstaller …` |
| exe가 바로 꺼짐 | `--noconsole` 없이 빌드해 콘솔 오류 확인 |
| `ModuleNotFoundError: pygame` | 3.14로 빌드함 → `py -3.12 -m pip install pygame==2.6.1` 후 다시 빌드 |
| 기록이 매번 0 | `__file__` 기준 경로 사용 → 위 `sys.frozen` 처리 |
| 한글이 네모 | `SysFont("malgungothic", 크기)` 사용 |
| 백신이 exe 차단 | `--onefile` 오탐, 예외 처리 안내 |
| `PermissionError` | 실행 중인 게임 종료, `dist/`·`build/` 지우고 재빌드 |
| 경로가 너무 김 | 짧은 경로(예: `C:\jeja-game`)로 옮겨 빌드 |
