---
name: jeja-spec
description: 제자 키우기의 수치·규칙·조작키를 확인할 때 사용. 구현과 검수 모두 이 기준을 따른다.
---

# 제자 키우기 기준표 (최종)

출처: `docs/기획서.md` (최종 게임 한 문서, 2026-11-23 정리, M·N단위와 밸런스 B안(2026-11-24) 반영). 절 번호는 기획서와 같다.
이 표와 기획서가 다르면 기획서가 우선이고, 차이를 발견하면 리드에게 보고한다. 수치는 모두 `config.py` 상수와 같다.
"확정 해석" 표시는 기획서가 모호해서 사용자와 합의한 내용이다.

## 1. 기본

| 항목 | 값 | config.py 상수 |
|---|---|---|
| 창 크기 | 800×600 | `SCREEN_WIDTH`, `SCREEN_HEIGHT` |
| 장르 | 방치형. 판에 시간 제한 없음 | - |
| 60초 주기 | 계절·낮밤·시험 기간·이벤트 횟수용 시계 | `CYCLE_SECONDS` 60 |
| 시험 기간 | 주기 마지막 15초 (주기 안 45 이상 ~ 60 미만) | `EXAM_SECONDS` 15 |
| 폰트 | `pygame.font.SysFont("malgungothic", 크기)` | `FONT_NAME` |
| 화면 상태 | title / playing / event(대화창) / ending | `STATE_*` |

## 2. 게임 규칙

### 게이지

| 게이지 | 범위 | 시작값 | 자연 감소 (1초마다) | 0이 되면 |
|---|---|---|---|---|
| 체력 | 0~`max_health` (100 + 10 × 체력 증진 Lv) | 80 | -1 (든든함이면 -0.5) | 즉시 휴학 (대학원이면 수료) |
| 멘탈 | 0~`max_mental` (100 + 10 × 멘탈 관리 Lv) | 80 | -1 (시험 기간 -2) | 즉시 휴학 (대학원이면 수료) |
| 지식 | 0 이상, 상한 없음 | 0 | 없음 | 진급·졸업 기준 |

- clamp: 체력 0~`Student.max_health`, 멘탈 0~`Student.max_mental`(property, `GAUGE_MAX` 100 + 업그레이드), 지식 0 미만 금지. 휴학 판정은 `<= 0`.
- **회복은 휴식에서만.** 학식은 게이지를 바로 바꾸지 않고 버프 든든함만 준다. 랜덤 이벤트는 예외(예전처럼 게이지를 바로 바꾼다).
- 1초마다(`decay_once`): 체력 += 자기 관리 회복 − 체력 감소, 멘탈 += 자기 관리 회복 − 멘탈 감소.
  - 감소 = 기본 × (1 − 0.1 × 건강 관리 Lv) × 대학원 배수, 체력은 든든함이면 × 0.5 (`FULL_HEALTH_DECAY_RATIO`).
  - 자기 관리 회복 = 0.2 × 자기 관리 Lv (`get_self_care_regen`, 0레벨이면 정수 0). 행동과 상관없이 늘 더한다.
  - 소수 가능(`GAUGE_DECIMALS` 6자리 반올림). 업그레이드 0레벨·학부·든든함 없음이면 정수 그대로.
- "0이 되면 즉시": 자연 감소·공부·이벤트 무엇으로 0이 되어도 바로 엔딩.

### 자동 행동과 방침

- `AUTO_ACTION_INTERVAL` 2.0초마다 자동 행동, 첫 행동도 2초 뒤. 간격 = 2.0 − 0.2 × 시간 관리 Lv (최소 1.0). 대화창(STATE_EVENT) 중 정지.
- 고르기(`choose_auto_action`): health < 기준 or mental < 기준 → rest, 아니고 `not student.is_full_buff_active()` → feed, 아니면 study.

| 방침 (`POLICY_*`) | 키 | 버튼 글자 | 회복 기준 | 공부 지식 | 공부 소모 | 휴식 회복 (`POLICY_REST_RATIO`) | 컨디션 보너스 (`POLICY_CONDITION_BONUS`) |
|---|---|---|---|---|---|---|---|
| study_focus | 1 | 공부 위주 [1] | 25 | ×1.8 | ×1.8 | ×1.0 | 0 |
| balanced (시작값) | 2 | 균형 [2] | 50 | ×1.0 | ×1.0 | ×1.0 | 0 |
| rest_focus | 3 | 휴식 위주 [3] | 70 | ×0.7 | ×0.7 | ×1.5 | 0.5 (체력·멘탈 ≥ 70이면 연구비 ×1.5) |

- 방침은 새 판마다(start_new_game: 타이틀 Enter·다시 하기·환생) 균형. 대학원 진학은 방침 유지.

### 행동 효과

| 행동 | 체력 | 멘탈 | 지식 |
|---|---|---|---|
| 학식 먹이기 (feed) | - | - | - |
| 쉬게 하기 (rest) | +15 (+연애 중 5, +카페 5, +침대 4/Lv) | +20 (+음악 힐링 5, +침대 4/Lv) | -2 |
| 공부시키기 (study) | -5 (+카페인 2, +헬스장 2) | -8 | +10, 시험 +20 (+참고서 2/Lv, +도서관 3) |

- 학식: `full_until = elapsed + get_full_duration()`, 지속 = 30 (`FULL_DURATION`) + 6 × 학식 메뉴 Lv + 체력 단련 10. 다시 먹으면 새 지속 시간으로 다시 채움(쌓이지 않음). `is_full_buff_active()` = 남은 시간(`get_full_time_left()`) > 0. elapsed 기준이라 대화창 동안 멈춘다. 대학원 진학 시 유지, 새 판에서 None.
- 휴식: `rest(recovery_ratio)`, 체력·멘탈 각각 round((기본 + 보너스) × 방침 휴식 회복 배수). 지식 -2는 배수 없음. 15×1.5 = 22.5 → 22, 20×1.5 = 30.
- 공부 계산: (기본 + 특성·업그레이드) → × 방침 배수 → (피곤이면 × 0.7) → Python `round()`. .5 예: 휴식 위주 체력 -5×0.7 = -3.5 → -4.
- 방침만 적용한 공부 1회: 공부 위주 지식 +18(시험 +36)·체력 -9·멘탈 -14 / 균형 +10(+20)·-5·-8 / 휴식 위주 +7(+14)·-4·-6.

### 디버프와 버프

| 이름 (config) | 조건 | 효과 | 이름(코드) |
|---|---|---|---|
| 피곤 (`DEBUFF_TIRED`) | 체력 < 30 (`LOW_GAUGE_LIMIT`, 최댓값과 상관없음) | 공부 지식 ×0.7 (`TIRED_KNOWLEDGE_RATIO`), 공부 직전 체력으로 판정 | `Student.is_tired()`, `has_debuff(name)` |
| 우울 (`DEBUFF_DEPRESSED`) | 멘탈 < 30 | 지식으로 버는 연구비 ×0.7 (`DEPRESSED_MONEY_RATIO`), 연구비를 쌓는 순간(효과 적용 뒤) 판정 | `Student.is_depressed()`, `has_debuff(name)` |
| 든든함 (`BUFF_FULL`) | 학식 뒤 지속 시간 동안 | 체력 자연 감소 ×0.5 | `Student.is_full_buff_active()`, `full_until`, `get_full_time_left()` |
| 컨디션 좋음 (`CONDITION_GOOD`) | 방침 rest_focus, 체력·멘탈 ≥ 70 (`CONDITION_GOOD_MIN`) | 지식으로 버는 연구비 ×1.5 | `Game.is_good_condition()` |

- 연구비 배수 `Game.get_money_multiplier()` = 명성 배수 × 대학원 배수 × `get_condition_money_ratio()`(우울 0.7 / 컨디션 좋음 1.5 / 그 밖 1.0). 졸업 보너스는 `get_fame_multiplier()`만 곱한다. 장학금은 배수 없음.
- 상태 배지: `Student.get_statuses()`(피곤·우울·든든함 순) + 컨디션 좋음 = `Game.get_status_names()`, 상태 패널 위쪽(`STATUS_BADGE_Y` 128)에 2열. 배지 = 도트 아이콘(`STATUS_ICONS`, 8×6칸·칸 2픽셀: 피곤 Zz, 우울 비구름, 든든함 밥그릇, 컨디션 좋음 반짝 별) + 이름. 배지 자리 `Student.get_badge_rect(index, top)`.
- 상태 배지 툴팁(N단위): 게임 화면·패널 닫힘·배지에 마우스 → `Game.get_status_tip_text(name)` 한 줄(`STATUS_TIP_TEXTS`, config 값으로 채움). 예 "피곤: 체력 30 미만 — 공부 지식 ×0.7", "든든함: 남은 시간 12초 — 체력 감소 ×0.5"(남은 시간 올림), "컨디션 좋음: 휴식 위주, 체력·멘탈 70 이상 — 버는 연구비 ×1.5".
- **확정 해석 (시험 기간):** 멘탈 **자연 감소만** 2배, 공부 기본 지식 20. 공부의 체력 -5·멘탈 -8은 그대로. 보너스는 2배 아님.

### 진급과 졸업 (누적 지식 이상)

| 단계 | 목표 | 경계 |
|---|---|---|
| 2학년 | 400 (`GRADE_GOALS[0]`) | 399 → 1학년, 400 → 2학년 |
| 3학년 | 900 | 899 / 900 |
| 4학년 | 1500 | 1499 / 1500 |
| 졸업 | 2200 (`GRADUATION_KNOWLEDGE`) | 2199 → 4학년, 2200 → 졸업 |

- 한 번에 여러 목표를 넘으면 그만큼 오른다. 학년은 내려가지 않는다. 0이 된 순간과 겹치면 휴학이 먼저.
- 진급 알림 "n학년 진급!" / "대학원 n년차!" 2초(`EVENT_NOTICE_TIME`).
- 반지름 40 + (학년 − 1) × 10 → 40/50/60/70, 대학원 70. 안경 3학년부터.

### 졸업 등급 (걸린 게임 시간, 대화창 정지 시간 제외)

| 등급 | 조건 | 졸업 보너스 | 경계 |
|---|---|---|---|
| 수석 졸업 | ≤ 330초 (`TOP_GRADUATE_SECONDS`) | 200 | 330 → 수석 |
| 무사 졸업 | 330초 초과 ≤ 720초 (`NORMAL_GRADUATE_SECONDS`) | 100 | 330.0001 → 무사, 720 → 무사 |
| 아슬아슬 졸업 | 720초 초과 | 50 | 720.0001 → 아슬아슬 |

- 330 / 720초는 밸런스 B안(2026-11-24)으로 확정한 값이다(M단위 임시 값 400 / 720초 → 330 / 720초).

- 보너스 × (1 + 0.1 × 명성), 내림. 휴학·수료 0. `judge_ending(seconds)`는 `TIME_EPSILON`만큼 봐준다.

### 엔딩

| 엔딩 | 조건 | R | C |
|---|---|---|---|
| 휴학 | 학부에서 체력·멘탈 0 | 다시 하기 (명성 그대로) | - |
| 수석/무사/아슬아슬 졸업 | 4학년 누적 지식 ≥ 2200 | 환생 (명성 +1) | 대학원 진학 |
| 대학원 n년차 수료 | 대학원에서 체력·멘탈 0 | 환생 (명성 +1) | - |

### 60초 주기

- 주기 번호 = elapsed // 60 + 1, 주기 안 시간 = elapsed % 60 (`TIME_EPSILON` 허용).
- 계절: 0~15 봄, 15~30 여름, 30~45 가을, 45~60 겨울(시험). 계절 안 0~9 낮, 9~12 저녁, 12~15 밤.
- 경계: 14.99 봄 / 15 여름, 44.99 시험 아님 / 45 시험, 59.99 시험·주기 1 / 60 주기 2·봄·시험 아님. 104.99 / 105 (주기 2 시험 시작).
- 대학원 진학 때 주기 시계는 이어서 흐른다.

## 3. 성장

- 연구비 += floor(지식 증가량 × (1 + 0.1 × 명성) × (1 + 1.0 × 대학원 년차) × 컨디션 배수). 지식 감소 시 0. (`FAME_MONEY_BONUS` 0.1, `GRAD_MONEY_BONUS` 1.0, 컨디션 배수는 2절 디버프와 버프)
- 명성: 졸업·수료 엔딩에서 환생하면 +1 (`FAME_STEP`).
- record.json 저장: 판이 끝날 때마다(휴학·졸업·수료), 업그레이드를 살 때, 환생할 때.
- 업그레이드 가격 = floor(기본가 × 2.0^레벨) (`UPGRADE_COST_GROWTH` 2.0). 13종 전부 최대까지 합계 92,590 (예전 10종 61,590 + 컨디션 31,000).

| id | 이름 | 분류 | 최대 Lv | 기본가 | 레벨당 효과 |
|---|---|---|---|---|---|
| menu | 학식 메뉴 개선 | 행동 효율 | 5 | 240 | 든든함 지속 +6초 |
| bed | 푹신한 침대 | 행동 효율 | 5 | 240 | 휴식 체력·멘탈 각각 +4 |
| reference_book | 참고서 | 행동 효율 | 5 | 360 | 공부 지식 +2 |
| time_management | 시간 관리 | 자동화 속도 | 5 | 450 | 간격 -0.2초 (2.0 → 1.0) |
| health_care | 건강 관리 | 자동화 속도 | 5 | 450 | 자연 감소 -10% |
| library | 도서관 | 시설 | 1 | 900 | 공부 지식 +3, 배경 |
| cafe | 카페 | 시설 | 1 | 900 | 휴식 체력 +5, 배경 |
| gym | 헬스장 | 시설 | 1 | 900 | 공부 체력 소모 -2, 배경 |
| lucky_charm | 행운 부적 | 이벤트 | 3 | 600 | 이벤트 확률 +5%p (25% → 40%) |
| scholarship | 장학금 제도 | 이벤트 | 1 | 750 | 자동형 "장학금을 받았다" 추가 |
| health_max | 체력 증진 | 컨디션 | 5 | 300 | 체력 최대 +10 |
| mental_max | 멘탈 관리 | 컨디션 | 5 | 300 | 멘탈 최대 +10 |
| self_care | 자기 관리 | 컨디션 | 5 | 400 | 1초마다 체력·멘탈 +0.2 (늘, 휴식 중에도) |

- 예: 학식 메뉴 240/480/960/1920/3840, 행운 부적 600/1200/2400.
- 시간 관리 구매 시 auto_timer = min(auto_timer, 새 간격).
- 장학금 이벤트: 연구비 +30 × 학년(대학원 4). 명성·대학원 배수 없음.
- 업그레이드 패널: U 또는 [업그레이드 U], 게임·엔딩 화면에서만. ↑↓(순환)·Enter, 항목 클릭 = 고르고 바로 사기. 게임 화면에서 패널이 열려도 시간은 흐른다. 13줄: `UPGRADE_ROW_TOP` 166, `UPGRADE_ROW_HEIGHT` 20, `UPGRADE_ROW_STEP` 21 (마지막 줄 아래 끝 438), 줄은 외곽선 없는 띠.
- 바닥 줄 "효과: …"(레벨당 효과)는 N단위에서도 그대로 둔다.
- **업그레이드 툴팁(N단위):** 패널이 열려 있고 마우스가 항목 줄 위에 있을 때만(게임·엔딩 모두, `get_hovered_upgrade_index`; 키보드로 고른 줄은 바닥 줄 "효과: …"로 본다) 그 줄의 툴팁을 x `TOOLTIP_X` 276부터, 그 줄 위쪽 y에 맞춰 그린다(y 116 ~ 460 안으로 밀어 넣음, 오른쪽 끝 ≤ 792). 패널·정보바·목표 막대·방침 버튼과 겹치지 않는다. 줄: "이름  Lv l/max" / "지금: 효과"(0레벨 "지금: 아직 없음") / "다음: 효과" 또는 "다음: 최고 레벨" / "무대: …"(`UPGRADE_DECOR_TEXTS`) / "가격: 연구비 n" 또는 "가격: MAX" / (연구비 < 가격) 빨간 "연구비가 모자라요". 효과 = `UPGRADE_LEVEL_EFFECTS[id].format(round(레벨 × per_level, 6))`, 방침 배수 없음. 예: 참고서 Lv2 "지금: 공부 지식 +4", "다음: 공부 지식 +6"; 건강 관리 Lv3 "자연 감소 -30%"; 행운 부적 Lv1 "이벤트 확률 +5%p".
- record.json: 모르는 id는 무시, 없는 id(예전 10종 파일의 새 3종)는 0.

### 환생과 대학원

- 대학원 n년차 → n+1 목표 누적: 2200 + Σ_{k=1..n}(800 + 200(k−1)) → 3000, 4000, 5200, 6600, 8200 … (경계 2999/3000, 3999/4000, 5199/5200). (`GRAD_GOAL_FIRST_STEP` 800, `GRAD_GOAL_STEP_GROWTH` 200)
- 대학원 자연 감소 배수 = 1 + 1.0n + 1.5c (`GRAD_DECAY_BONUS` 1.0, `GRAD_CYCLE_DECAY_BONUS` 1.5). c = floor((elapsed − grad_entry_time) / 60). 진학 직후 ×2.0, 60초 뒤 ×3.5, 120초 뒤 ×5.0 (1년차 기준). 건강 관리 배수와 곱한다. 학부는 1.
- 대학원: 선택지형 없음(자동형만), get_grade() = 4, 장소 연구실, 정보바 "대학원 n년차", 목표 "다음 년차까지 지식 n".
- 진학 시 게이지·지식·특성·외형·플래그·last_event_time·elapsed·full_until 유지, auto_timer = get_auto_interval()로 다시 채움, 바로 check_promotion.

## 4. 랜덤 이벤트와 성장 요소

| 항목 | 값 | 상수 |
|---|---|---|
| 자동 행동 후 확률 | 0.25 (+0.05/행운 부적 Lv) | `EVENT_CHANCE` |
| 보장 구간 | 11.25초 (주기 안 0~45초를 4구간) | `EVENT_GUARANTEE_INTERVAL` |
| 주기당 최소 보장 | 4 | `EVENT_MIN_PER_GRADE` (이름만 예전, 값은 주기당) |
| 주기당 최대 | 5 | `EVENT_MAX_PER_GRADE` |
| 선택지형 비율 | 0.5 (후보 있을 때) | `EVENT_CHOICE_RATIO` |
| 알림 표시 | 2.0초 | `EVENT_NOTICE_TIME` |
| 확률 이벤트 최소 간격 | 8.0초 (게임 시간, 주기·학년 넘어 이어서, 보장은 예외) | `EVENT_MIN_GAP` |
| 대화창 입력 대기 | 0.3초 | `EVENT_INPUT_DELAY` |

### 판정 순서 (do_action 안)

1. 게임 화면이 아니면 무시.
2. 행동 효과 → last_action → 연구비 → 연출 → check_promotion → check_ending.
3. 엔딩이면 이벤트 없음. 아니면 roll_event.
4. roll_event: 주기 이벤트 수 ≥ 5면 없음. 보장 조건(주기 안 경과 ≥ 11.25k인 가장 큰 k(≤4)에 대해 수 < k)이면 반드시. 아니면 간격(직전 이벤트 이후 ≥ 8초, 없으면 통과)이 지났고 rng.random() < 확률일 때. 간격이 안 찼으면 rng를 뽑지 않는다.
5. 뜨면 count_event(주기 수 +1, last_event_time 기록). 자동형: 효과·연구비·알림·팝업 → check_promotion → check_ending. 선택지형: seen 기록 → STATE_EVENT(게임 정지).

- 보장 경계(주기 안): 11.24 → k=0, 11.25 → k=1, 22.5 → 2, 33.75 → 3, 45 이후 → 4.
- 선택지형 학년 조건은 지금 학년(get_grade). 한 판 1회. 대학원에서는 선택지형 없음.
- 대화 상태: 키 1·2 또는 선택 버튼 클릭. 방침 키·버튼·U 무시, 패널 숨김. ESC/QUIT 동작. 선택 후 효과·특성·외형·플래그 → 연구비 → 팝업 → 진급 → 휴학 판정.

### 특성 보정

| 특성 | 학식 | 휴식 멘탈 | 휴식 체력 | 공부 체력 |
|---|---|---|---|---|
| 없음 | 든든함 30초 | +20 | +15 | -5 |
| 체력 단련 | 든든함 40초 (`BONUS_FULL_TIME` +10) | | | |
| 음악 힐링 | | +25 | | |
| 연애 중 | | | +20 | |
| 카페인 | | | | -3 |

- 이벤트 목록·외형 5종(기타·헬스 머리띠·커피잔·하트 머리핀·선글라스)·연계 3종(MT 참석·밴드부·연애 중)은 기획서 4절 표 그대로 config에 있다.
- 특성·외형·플래그·seen_events·event_counts(주기 번호 키)·last_event_time은 Student에 둔다. 새 판에서 초기화.
- 난수: Game이 `random.Random(seed)`를 가진다. Game(seed=None)으로 테스트에서 고정. random은 이벤트 전용.

## 5. 조작키

| 조작 | 마우스 | 키보드 | 화면 |
|---|---|---|---|
| 게임 시작 | - | Enter | 타이틀 |
| 방침 공부 위주 / 균형 / 휴식 위주 | 방침 버튼 | 1 / 2 / 3 | 게임 |
| 업그레이드 패널 | [업그레이드 U] | U | 게임·엔딩 |
| 업그레이드 고르기·사기 | 항목 클릭 | ↑↓, Enter | 패널 열림 |
| 이벤트 선택 | 선택 버튼 | 1 / 2 | 대화창 |
| 환생 / 다시 하기 | - | R | 엔딩 |
| 대학원 진학 | - | C | 졸업 엔딩 |
| 종료 | 창 닫기 | ESC | 모든 화면 |

- 숫자판 키는 쓰지 않는다.

## 6. 화면

| 화면 | 표시 내용 |
|---|---|
| 타이틀 | "제자 키우기", "최고 기록: 지식 n", "명성 n · 연구비 n", "Enter를 눌러 시작" |
| 게임 | 정보바("n학년"/"대학원 n년차", 목표 글자, "연구비 n  지식 n"), 목표 막대(12~268, 64~104), 시험 배너(284~788, 64~104, "시험 기간! 공부 효과 2배, 멘탈 감소 2배"), 상태 패널(12~268, 116~460) 또는 업그레이드 패널(12~268, 116~468), 무대(284~788, 116~460), 방침 버튼 3개(y 476) + [업그레이드 U](x 600), 자동 행동 막대(y 540) + "다음 자동 행동까지", "경과 m분 s초" |
| 대화창 | 점무늬 멈춤 표시, 대화창(300, 132, 472, 264), "[1] …"/"[2] …" + 효과 미리보기 |
| 엔딩 | 엔딩 이름, 학사모(졸업·수료)/비구름(휴학), "졸업까지 m분 s초"(졸업), "누적 지식 n", "졸업 보너스: 연구비 +n"(졸업), 안내("R을 눌러 다시 하기" / "R: 환생 (명성 +1)" + "C: 대학원 진학"), [업그레이드 U]. 패널을 열면 가운데 패널을 오른쪽(284~788)으로 옮김 |

- 게이지 막대 30 미만 빨강(실제 값 기준), 막대 전체 = 지금 최댓값, 라벨 줄 오른쪽 "지금/최대"(`GAUGE_VALUE_TEXT`, 반올림). 표정: 멘탈 ≥ 60 웃음, 30~59 일자, < 30 울음. 다크서클 체력 < 30.
- 상태 패널 위쪽 상태 배지(피곤·우울·든든함·컨디션 좋음, 아이콘 + 이름 배지 2열, y 128~, 마우스 올리면 효과 툴팁).
- 목표 글자: 1~3학년 "다음 학년까지 지식 n", 4학년 "졸업까지 지식 n", 대학원 "다음 년차까지 지식 n".
- 배경 4겹: 장소(학년: lawn/lecture/library/ceremony, 대학원 lab) → 하늘(계절·시간대: `get_season()`, `get_time_of_day()`, `get_sky_color()`) → 행동 소품(`last_action`) → 시설(산 시설) + 업그레이드 장식(N단위). 바깥 장소는 저녁·밤 그늘 단계, 연구실 제외.
- **업그레이드 장식(N단위):** 시설 3종은 건물, 나머지 10종(`DECOR_IDS`)은 Lv1부터 장식: 학식 메뉴 도시락(Lv3 2단, Lv5 주먹밥), 침대 쿠션(Lv3 2개, Lv5 3개), 참고서 책장(책 수 = Lv), 시간 관리 벽시계(Lv3 추, Lv5 종), 건강 관리 비타민 병(Lv3 2병, Lv5 3병), 행운 부적 부적 걸이(부적 수 = Lv), 장학금 트로피, 체력 증진 덤벨(Lv3 2개, Lv5 케틀벨), 멘탈 관리 화분(Lv3 잎, Lv5 꽃), 자기 관리 요가 매트(Lv3 말아 둔 매트, Lv5 물병). 조각 표 `DECOR_PIECES`(min_level, 스프라이트, 열·행 차이), 자리 `DECOR_SLOTS[장소]`(칸 좌표; 바깥 4곳 공통, 연구실 따로). 제자(4학년+외형 5종+점프)·행동 소품·벤치·졸업식 의자·시설 건물·서로와 겹치지 않고, 땅 시작 행(45) 위 팝업·알림 자리에도 없다(연구실 벽시계·트로피는 창 아래 벽).
- 장식은 배경 그림에 함께 그려 캐시: `scenery_key` = (장소, 계절, 시설 튜플, 그늘 단계, `get_decor_levels()`). `make_scenery(place, season, facilities, shade=0, decor_levels=None)` — 앞 4개 인자 위치는 그대로. 장식도 그늘을 받는다(시설과 같은 규칙). Game 도우미: `get_decor_levels`, `get_decor_pieces(id, level)`, `get_decor_rects(place, levels)`(무대 안쪽 픽셀 Rect), `draw_decorations`.

### 도트 스타일과 효과 (보기만 바꾼다)

- 도트 1칸 = `PIXEL_SIZE`(4). 남색 외곽선, 계단형 모서리. 파스텔 레트로 팔레트. 글자 `antialias=False`. Surface 알파(반투명) 금지.

| # | 효과 | 기준 |
|---|---|---|
| E1 | 버튼 | 호버 밝은 색, 방침 고르면 `BUTTON_PRESS_OFFSET`(4px) 눌림 `BUTTON_PRESS_TIME`(0.12초), 고른 방침 노랑, 자동 행동 진행 막대. 대화창 선택 버튼은 입력 대기 중 회색 + 진행 막대 |
| E2 | 파티클 | 행동마다 10개, 0.6~0.8초. 학식 하트·밥알, 휴식 Zzz·구름, 공부 별·연필. 결정적 표(random 금지) |
| E3 | 수치 팝업 | 실제 변화량(clamp 반영, 반올림 정수), 0이면 없음, 0.8초. 행동은 머리 위, 이벤트는 무대 왼쪽 위 |
| E4 | 부드러운 게이지 | `GAUGE_ANIM_TIME` 0.25초, 색은 실제 값 기준, 새 판에서 표시값 = 실제 값 |
| E5 | 제자 반응 | 점프 0.3초·최대 8px, 숨쉬기 1.5초·4px. 반지름 불변 |
| E6 | 안내 깜빡임 | 타이틀·엔딩 키 안내 화살표 0.5초 간격 |

- 엔딩 진입·새 판에서 파티클·팝업·알림을 비운다.

## 7. 기능 체크리스트 (기획서 7절)

- [ ] 1. 자동 행동 2초 / 2. 방침 1·2·3 / 3. 행동 효과 / 4. 자동 행동 진행 막대
- [ ] 5. 자연 감소 / 6. 게이지 막대(30 미만 빨강) / 7. 표정·다크서클 / 8. 학점 진급·성장·안경·진급 알림
- [ ] 9. 휴학 엔딩 / 10. 화면 전환(Enter / R / C / ESC)
- [ ] 11. 시험 기간 / 12. 졸업 엔딩 3종(걸린 시간) / 13. record.json
- [ ] 14. 도트·E1~E6 / 15. 랜덤 이벤트 / 16. 특성·외형·연계 / 17. 연구비·명성
- [ ] 18. 업그레이드 13종 / 19. 환생 / 20. 대학원 / 21. 배경 4겹 / 22. 목표 막대·경과 시간
- [ ] 23. 디버프와 버프(피곤·우울·든든함·컨디션 좋음, 상태 배지)

## 8. 개발 과정 (루프 단위)

- 지난 단위: 원래 1~7일차, 연출 A·B, 이벤트 C~E, 방치형 G~K, 시간 제한 제거 L, 밸런스 확정 A안. 모두 main에 합쳐졌다(기획서 8절 표).
- M단위(`feat/idle-depth`): 회복은 휴식에서만·든든함·새 자동 행동 규칙·최댓값·디버프·방침 수치·업그레이드 13종·진급 기준 2배.
- N단위(`feat/idle-depth`): 업그레이드 툴팁, 업그레이드 장식(13종 모두 무대에 보임), 상태 배지 아이콘·툴팁. 규칙·수치 변화 없음.
- 밸런스 B안(2026-11-24, `feat/idle-depth`): 수석 330초, 공부 위주 기준 25·지식 ×1.8, 컨디션 좋음 ×1.5, 대학원 감소 1 + 1.0n + 1.5c.
- 새 작업도 같은 방식: 단위 하나 → 개발 → 검수 → (불통과면 수정 → 재검수), 같은 단위 3회 불통과면 멈춘다.

## 9. 구조와 기록

| 클래스 | 파일 | 담당 |
|---|---|---|
| Student | student.py | 게이지, 자연 감소, 행동, 진급·졸업, 주기·시험 기간, 대학원, 이벤트 기록, 엔딩 판정, 제자 그리기 |
| Button | button.py | 버튼 위치·글자, 클릭 판정, 호버·눌림·강조·회색 + 도트 그리기 도우미 |
| Game | game.py | 메인 루프, 화면 전환, 자동 행동·방침, 이벤트, 연구비·업그레이드, 환생·대학원, 기록, 배경, 연출 |

- 모든 수치는 `config.py` 상수. 다른 파일에 숫자를 직접 쓰지 않는다.
- record.json = {"best_knowledge", "money", "fame", "upgrades": {id: 레벨}}. 예전 형식·깨진 파일·잘못된 값은 0. 저장 위치: exe면 `sys.executable` 폴더, 아니면 `main.py` 폴더.

### 테스트하기 쉬운 구조 (개발·검수 공통 약속)

- Student 로직은 화면 없이 호출할 수 있다. 시간은 인자로 받는다(`update(dt)`), `pygame.time.get_ticks()`에 묶지 않는다.
- 졸업 등급 판정은 `judge_ending(seconds)` 함수.

### 테스트가 쓰는 이름 (바꾸지 않는다)

- 모듈 함수: `student.judge_ending`, `game.format_time`, `button.sprite_size`·`draw_pixel_box`·`draw_cut_rect`·`render_text`
- Game 상태: `state`, `running`, `student`, `policy`, `auto_timer`, `last_action`, `ending`, `current_event`, `dialog_time`, `money`, `fame`, `upgrades`, `best_record`, `record_path`, `rng`, `graduation_bonus`, `grad_year`(property), `upgrade_panel_open`, `upgrade_cursor`, `notice`, `promotion_notice`, `particles`, `popups`, `press_timers`, `jump_timer`, `gauge_lag`, `buttons`, `choice_buttons`, `upgrade_button`, `ending_upgrade_button`, `mouse_pos`, `blink_time`, `screen`, `scenery_key`
- Game 메서드: `handle_event`, `update`, `draw`, `start_new_game`, `reset_round`, `set_policy`, `choose_auto_action`, `do_action`, `get_auto_interval`, `get_auto_progress`, `get_event_chance`, `check_promotion`, `check_ending`, `end_game`, `roll_event`, `pick_event`, `start_event`, `get_event_candidates`, `choose_option`, `is_dialog_ready`, `earn_knowledge_money`, `get_money_multiplier`, `get_fame_multiplier`, `get_condition_money_ratio`, `is_good_condition`, `get_status_names`, `get_grad_money_multiplier`, `get_upgrade_cost`, `can_buy_upgrade`, `buy_upgrade`, `is_upgrade_maxed`, `get_upgrade_row_rect`, `reincarnate`, `enter_grad_school`, `can_reincarnate`, `is_graduation_ending`, `is_grad_school_ending`, `load_record`, `save_record`, `load_best_record`, `save_best_record`, `update_best_record`, `get_season`, `get_time_of_day`, `get_sky_color`, `get_place`, `get_owned_facilities`, `get_scene_shade`, `get_goal_text`, `get_ending_layout`, `get_shown_gauge`, `get_gauge_values`, `get_student_lift`, `is_blink_on`, `clear_effects`
- Game 메서드(N단위): `get_upgrade_effect_text(id, level)`, `get_upgrade_tooltip_rows(id)`(→ [(글자, 색)]), `get_hovered_upgrade_index`(마우스가 올라간 줄, 없으면 None), `get_tooltip_rect(rows, anchor_top)`, `draw_tooltip`, `draw_upgrade_tooltip`(→ 상자 Rect 또는 None), `get_status_tip_text(name)`, `get_hovered_status`, `draw_status_tooltip`, `get_decor_levels`, `get_decor_pieces`, `get_decor_rects`, `draw_decorations`. Student: `get_badge_rect(index, top)`
- Student 상태: `health`, `mental`, `knowledge`, `elapsed`, `decay_timer`, `grade`, `grad_year`, `graduation_time`(졸업 순간 elapsed, 없으면 None), `grad_entry_time`(대학원 진입 elapsed, 학부면 None), `traits`, `looks`, `flags`, `seen_events`, `event_counts`, `last_event_time`, `upgrades`, `full_until`(든든함 끝 elapsed, 없으면 None), `max_health`·`max_mental`(property)
- Student 메서드: `update(dt)`, `feed`, `rest(recovery_ratio)`, `study(knowledge_ratio, cost_ratio)`, `is_tired`, `is_depressed`, `has_debuff(name)`, `is_full_buff_active`, `get_full_time_left`, `get_full_duration`, `get_statuses`, `get_self_care_regen`, `decay_once`, `promote`, `get_grade`, `get_next_goal`, `get_goal_start`, `get_goal_progress`, `get_knowledge_to_goal`, `has_graduated`, `get_cycle_index`, `get_cycle_time`, `is_exam_period`, `is_in_grad_school`, `enter_grad_school`, `get_grad_goal(year)`, `get_grad_cycles`, `get_grad_decay_ratio`, `get_health_decay`, `get_mental_decay`, `get_study_knowledge`, `get_upgrade_bonus`, `get_trait_bonus`, `is_dropped_out`, `get_ending`, `get_graduation_ending`, `get_radius`, `get_mouth`, `has_dark_circles`, `has_glasses`, `get_cycle_event_count`, `count_event`, `is_event_gap_passed`, `can_have_event`, `needs_guaranteed_event`, `can_see_event`, `apply_effects`, `add_trait`, `add_look`, `add_flag`, `change_health`, `change_mental`, `change_knowledge`
- Button: `rect`, `text`, `is_clicked(pos)`, `draw(...)`

## 10. 밸런스

- 지금(밸런스 B안, 2026-11-24 사용자 승인): 진급 400/900/1500, 졸업 2200, 수석 ≤ 330초·무사 ≤ 720초, 공부 위주 기준 25·지식 ×1.8·소모 ×1.8, 휴식 위주 컨디션 좋음 연구비 ×1.5, 가격 ×2.0(13종 합계 92,590), 대학원 감소 1 + 1.0n + 1.5c, 대학원 연구비 1 + 1.0n.
- 목표(시뮬레이션, 기획서 10절): 업그레이드 없는 첫 판 공부 위주 무사·휴학 10~30%·가장 빠름, 균형 무사, 휴식 위주 가장 느리고 안전·연구비 많음. 첫 수석 4번째 판(약 27분), 전부 최고 레벨 약 71분, 대학원 수료 약 5~22분.
- (예전 A안 시뮬레이션 수치는 M단위 이전 규칙 기준이라 지금과 맞지 않는다. 기획서 부록 참고.)
- **확정 해석 (밸런스 변경):** 수치를 바꿀 이유가 생기면 바로 바꾸지 않는다. 근거(시뮬레이션 결과)와 조정안을 리드에게 보고하고, 사용자 승인 후 config.py와 기획서를 함께 바꾼다.
