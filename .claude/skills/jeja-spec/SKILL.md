---
name: jeja-spec
description: 제자 키우기의 수치·규칙·조작키를 확인할 때 사용. 구현과 검수 모두 이 기준을 따른다.
---

# 제자 키우기 빠른 기준표

- 완전한 규칙·표·문구는 `docs/기획서.md`(절 번호 같음). 이 표와 다르면 기획서가 우선, 차이는 리드에게 보고.
- 수치는 모두 `config.py` 상수. 아래 `이름`은 config 상수, 값은 지금 값(밸런스 B안, 2026-11-24).
- **확정 해석** = 기획서가 모호해 사용자와 합의한 내용.

## 1. 기본

창 800×600(`SCREEN_WIDTH`/`HEIGHT`), 폰트 `FONT_NAME`, 상태 `STATE_TITLE/PLAYING/EVENT/ENDING`. 시간 제한 없음. 60초 주기(`CYCLE_SECONDS`), 시험 기간 = 주기 마지막 15초(`EXAM_SECONDS`).

## 2. 게임 규칙

### 게이지와 시간

- 체력·멘탈 시작 80, 범위 0~`max_health`/`max_mental`(property: `GAUGE_MAX` 100 + 10×체력 증진/멘탈 관리 Lv). 지식 ≥ 0, 상한 없음. 0 판정은 `<= 0` → 즉시 휴학(대학원이면 수료), 원인 무관.
- `decay_once`(1초마다): 게이지 += `get_self_care_regen()`(0.2×Lv, 0레벨이면 정수 0) − 감소. 감소 = 기본(체력 1, 멘탈 1/시험 2) × (1 − 0.1×건강 관리 Lv) × `get_grad_decay_ratio()`, 체력은 든든함이면 × `FULL_HEALTH_DECAY_RATIO` 0.5. `GAUGE_DECIMALS` 6자리 반올림, 업그레이드 0·학부·든든함 없음이면 정수 유지.
- **회복은 휴식에서만.** 학식은 버프만. 랜덤 이벤트는 게이지를 바로 바꾼다.
- **확정 해석 (시험 기간):** 멘탈 *자연 감소만* 2배, 공부 기본 지식 20(보너스는 2배 아님). 공부 체력·멘탈 소모는 그대로.

### 자동 행동과 방침

- 간격 `AUTO_ACTION_INTERVAL` 2.0 − 0.2×시간 관리 Lv(최소 1.0), 첫 행동도 2초 뒤, STATE_EVENT 중 정지. 시간 관리 구매 시 `auto_timer = min(auto_timer, 새 간격)`.
- `choose_auto_action`: health < 기준 or mental < 기준 → rest / 아니고 `not is_full_buff_active()` → feed / 아니면 study.
- 방침은 새 판(`start_new_game`: Enter·다시 하기·환생)마다 balanced, 대학원 진학은 유지.

| 방침 | 키·버튼 | 기준 | 지식 | 소모 | 휴식 `POLICY_REST_RATIO` | `POLICY_CONDITION_BONUS` |
|---|---|---|---|---|---|---|
| study_focus | 1 "공부 위주 [1]" | 25 | ×1.8 | ×1.8 | ×1.0 | 0 |
| balanced | 2 "균형 [2]" | 50 | ×1.0 | ×1.0 | ×1.0 | 0 |
| rest_focus | 3 "휴식 위주 [3]" | 70 | ×0.7 | ×0.7 | ×1.5 | 0.5 |

### 행동 계산

- feed: `full_until = elapsed + get_full_duration()`(30 + 6×메뉴 Lv + 체력 단련 10), 다시 먹으면 덮어씀. elapsed 기준(대화창 동안 멈춤), 대학원 유지, 새 판 None.
- rest(ratio): 체력 round((15 + 연애 5 + 카페 5 + 침대 4/Lv) × ratio), 멘탈 round((20 + 음악 5 + 침대 4/Lv) × ratio), 지식 −2(배수 없음).
- study(k, c): 지식 round((10|시험 20 + 참고서 2/Lv + 도서관 3) × k × (피곤이면 0.7)), 체력 round((−5 + 카페인 2 + 헬스장 2) × c), 멘탈 round(−8 × c). Python `round()`(−3.5 → −4, 22.5 → 22).
- 방침만 적용한 공부 1회: 공부 위주 +18(시험 +36)/−9/−14, 균형 +10(+20)/−5/−8, 휴식 위주 +7(+14)/−4/−6.

### 디버프와 버프

| 이름 | 조건 | 효과 | 코드 |
|---|---|---|---|
| 피곤 `DEBUFF_TIRED` | 체력 < `LOW_GAUGE_LIMIT` 30 (공부 직전) | 공부 지식 × `TIRED_KNOWLEDGE_RATIO` 0.7 | `is_tired`, `has_debuff` |
| 우울 `DEBUFF_DEPRESSED` | 멘탈 < 30 (연구비 쌓는 순간) | 지식 연구비 × `DEPRESSED_MONEY_RATIO` 0.7 | `is_depressed`, `has_debuff` |
| 든든함 `BUFF_FULL` | 학식 뒤 지속 시간 | 체력 감소 ×0.5 | `is_full_buff_active`, `get_full_time_left` |
| 컨디션 좋음 `CONDITION_GOOD` | rest_focus, 체력·멘탈 ≥ `CONDITION_GOOD_MIN` 70 | 지식 연구비 ×1.5 | `Game.is_good_condition` |

- 배지 순서: `Student.get_statuses()`(피곤·우울·든든함) + 컨디션 좋음 = `Game.get_status_names()`. 툴팁 `get_status_tip_text(name)` ← `STATUS_TIP_TEXTS`(든든함 남은 시간 올림).

### 진급과 졸업 (누적 지식 이상)

| 단계 | 목표 | 경계 |
|---|---|---|
| 2학년 | 400 (`GRADE_GOALS[0]`) | 399 / 400 |
| 3학년 | 900 | 899 / 900 |
| 4학년 | 1500 | 1499 / 1500 |
| 졸업 | 2200 (`GRADUATION_KNOWLEDGE`) | 2199 / 2200 |

- 한 번에 여러 단계 가능, 학년은 안 내려감, 0과 겹치면 휴학 우선. 알림 2초(`EVENT_NOTICE_TIME`). 반지름 40 + 10×(학년−1), 대학원 70, 안경 3학년부터.

### 졸업 등급 (걸린 게임 시간, `judge_ending(seconds)`, `TIME_EPSILON` 허용)

| 등급 | 조건 | 보너스 | 경계 |
|---|---|---|---|
| 수석 | ≤ 330초 (`TOP_GRADUATE_SECONDS`) | 200 | 330 → 수석 |
| 무사 | 330초 초과 ≤ 720초 (`NORMAL_GRADUATE_SECONDS`) | 100 | 330.0001 → 무사, 720 → 무사 |
| 아슬아슬 | 720초 초과 | 50 | 720.0001 → 아슬아슬 |

- 보너스 × (1 + 0.1×명성) 내림, 휴학·수료 0. 엔딩 키: 휴학 R(다시 하기), 졸업 R(환생)·C(대학원), 수료 R(환생).

### 60초 주기

- 주기 번호 = elapsed // 60 + 1, 주기 안 시간 = elapsed % 60. 봄 0–15, 여름 15–30, 가을 30–45, 겨울(시험) 45–60. 계절 안 낮 0–9, 저녁 9–12, 밤 12–15.
- 경계: 14.99 봄 / 15 여름, 44.99 시험 아님 / 45 시험, 59.99 주기 1 / 60 주기 2·봄, 104.99 / 105 (주기 2 시험). 대학원에서도 이어서 흐름.

## 3. 성장

- 연구비 += floor(지식 증가량 × (1 + `FAME_MONEY_BONUS` 0.1×명성) × (1 + `GRAD_MONEY_BONUS` 1.0×년차) × 컨디션 배수(우울 0.7/좋음 1.5/1.0)). 감소 시 0. `get_money_multiplier` = 명성 × 대학원 × `get_condition_money_ratio`. 졸업 보너스는 명성 배수만, 장학금(+30×학년, 대학원 4)은 배수 없음.
- 명성 +1(`FAME_STEP`): 졸업·수료 뒤 환생. 저장: 판 끝·업그레이드 구매·환생·새 게임(N).
- 가격 = floor(기본가 × `UPGRADE_COST_GROWTH` 2.0^Lv). 13종 전부 92,590.

| id | 최대 | 기본가 | 레벨당 | id | 최대 | 기본가 | 레벨당 |
|---|---|---|---|---|---|---|---|
| menu | 5 | 240 | 든든함 +6초 | cafe | 1 | 900 | 휴식 체력 +5 |
| bed | 5 | 240 | 휴식 +4/+4 | gym | 1 | 900 | 공부 체력 +2 |
| reference_book | 5 | 360 | 지식 +2 | lucky_charm | 3 | 600 | 확률 +5%p |
| time_management | 5 | 450 | 간격 −0.2 | scholarship | 1 | 750 | 장학금 이벤트 |
| health_care | 5 | 450 | 감소 −10% | health_max / mental_max | 5 | 300 | 최대 +10 |
| library | 1 | 900 | 지식 +3 | self_care | 5 | 400 | 0.2/초 회복 |

- 패널: U·[업그레이드 U], 게임·엔딩에서만, ↑↓ 순환·Enter, 클릭 = 고르고 사기, 게임 시간은 흐름. 줄 `UPGRADE_ROW_TOP` 166 / `HEIGHT` 20 / `STEP` 21.
- 툴팁(마우스 줄만, `TOOLTIP_X` 276, y 116~460 안): "이름  Lv l/max" / "지금: 효과"(0레벨 "지금: 아직 없음") / "다음: 효과"|"다음: 최고 레벨" / "무대: …" / "가격: 연구비 n"|"가격: MAX" / (부족) 빨간 "연구비가 모자라요". 효과 = `UPGRADE_LEVEL_EFFECTS[id].format(round(Lv×per_level, 6))`.
- 대학원 년차 목표 = 2200 + Σ_{k=1..n}(`GRAD_GOAL_FIRST_STEP` 800 + `GRAD_GOAL_STEP_GROWTH` 200×(k−1)) → 3000/4000/5200/6600 (경계 2999/3000, 3999/4000, 5199/5200).
- 대학원 감소 배수 = 1 + `GRAD_DECAY_BONUS` 1.0×n + `GRAD_CYCLE_DECAY_BONUS` 1.5×c, c = floor((elapsed − `grad_entry_time`)/60) → 진학 직후 ×2.0, 60초 ×3.5, 120초 ×5.0. 학부 1.
- 진학 시 게이지·지식·특성·외형·플래그·last_event_time·elapsed·full_until 유지, auto_timer 다시 채움, 바로 check_promotion. 대학원은 선택지형 없음, get_grade() = 4.
- **새 게임(N, 2026-11-24 사용자 승인):** `Game.reset_progress()` = upgrades 13종 0(같은 사전을 고침)·money 0·fame 0(`FAME_START`) 후 save_record, best_record는 유지. `has_progress()` = money·fame·업그레이드 중 0보다 큰 값이 있으면 True → `new_game_confirm = True`(state는 STATE_TITLE 그대로), 아니면 바로 `start_fresh_game()`(= reset_progress + start_new_game). 문구 `NEW_GAME_HINT_TEXT`(y 448)·`NEW_GAME_CONFIRM_*`, 상자 `NEW_GAME_CONFIRM_RECT` (148, 382, 504, 104).
- record.json = {"best_knowledge", "money", "fame", "upgrades": {id: Lv}}. 없거나 깨진·잘못된 값 0, 모르는 id 무시. 위치: exe면 `sys.executable` 폴더, 아니면 `main.py` 폴더.

## 4. 랜덤 이벤트와 성장 요소

| 항목 | 값 |
|---|---|
| `EVENT_CHANCE` | 0.25 (+0.05/행운 부적 Lv) |
| `EVENT_GUARANTEE_INTERVAL` | 11.25초 (주기 안 0~45를 4구간) |
| `EVENT_MIN_PER_GRADE` / `EVENT_MAX_PER_GRADE` | 4 / 5 (이름만 예전, 값은 주기당) |
| `EVENT_CHOICE_RATIO` | 0.5 (선택지형 후보 있을 때) |
| `EVENT_MIN_GAP` | 8.0초 (주기·학년 넘어 이어서, 보장은 예외) |
| `EVENT_INPUT_DELAY` | 0.3초 |

- do_action 순서: 행동 → last_action → 연구비 → 연출 → check_promotion → check_ending → (엔딩 아니면) roll_event.
- roll_event: 주기 수 ≥ 5 없음 / 보장(주기 안 경과 ≥ 11.25k인 최대 k ≤ 4에 대해 수 < k) 반드시 / 아니면 간격 지났을 때만 `rng.random() < 확률`(간격 미달이면 rng 안 뽑음). 보장 경계 11.24 → 0, 11.25 → 1, 22.5 → 2, 33.75 → 3, 45 → 4.
- 선택지형: 지금 학년 조건, 한 판 1회, STATE_EVENT(정지, 키 1·2/클릭, 방침·U 무시, ESC 동작). 선택 후 효과 → 연구비 → 팝업 → 진급 → 휴학 판정.
- 특성 보정: 체력 단련 든든함 +10초(`BONUS_FULL_TIME`), 음악 힐링 휴식 멘탈 +5, 연애 중 휴식 체력 +5, 카페인 공부 체력 +2. 이벤트·외형·연계 표는 기획서 4절 = config.
- 난수: Game의 `random.Random(seed)`만(이벤트 전용).

## 5~6. 조작과 화면

- 키: Enter 시작(이어하기), N 새 게임(진행 있으면 확인 상자: Y 시작, N·Backspace 취소, 그 밖의 키 무시), 1/2/3 방침, U 패널, ↑↓·Enter 사기, 1/2 선택지, R 환생/다시 하기, C 대학원, ESC 종료. 숫자판 키 안 씀.
- 화면 문구·배치·장식·연출(E1~E6) 기준은 기획서 6절. 도트 1칸 `PIXEL_SIZE` 4, `antialias=False`, Surface 알파 금지, 연출은 random 금지.

## 9. 구조와 테스트 계약

- Student(student.py): 게이지·행동·진급·주기·대학원·이벤트 기록·엔딩·제자 그리기. Button(button.py): 버튼 + 도트 도우미. Game(game.py): 루프·화면·자동 행동·이벤트·연구비·업그레이드·기록·배경·연출.
- Student 로직은 화면 없이 `update(dt)`로 호출 가능(`get_ticks()`에 묶지 않음).

### 테스트가 쓰는 이름 (바꾸지 않는다)

- 모듈: `student.judge_ending`, `game.format_time`, `button.sprite_size`·`draw_pixel_box`·`draw_cut_rect`·`render_text`
- Game 상태: `state`, `running`, `new_game_confirm`, `student`, `policy`, `auto_timer`, `last_action`, `ending`, `current_event`, `dialog_time`, `money`, `fame`, `upgrades`, `best_record`, `record_path`, `rng`, `graduation_bonus`, `grad_year`(property), `upgrade_panel_open`, `upgrade_cursor`, `notice`, `promotion_notice`, `particles`, `popups`, `press_timers`, `jump_timer`, `gauge_lag`, `buttons`, `choice_buttons`, `upgrade_button`, `ending_upgrade_button`, `mouse_pos`, `blink_time`, `screen`, `scenery_key`
- Game 메서드: `handle_event`, `update`, `draw`, `start_new_game`, `has_progress`, `reset_progress`, `start_fresh_game`, `handle_title_key(key)`, `draw_new_game_confirm`, `reset_round`, `set_policy`, `choose_auto_action`, `do_action`, `get_auto_interval`, `get_auto_progress`, `get_event_chance`, `check_promotion`, `check_ending`, `end_game`, `roll_event`, `pick_event`, `start_event`, `get_event_candidates`, `choose_option`, `is_dialog_ready`, `earn_knowledge_money`, `get_money_multiplier`, `get_fame_multiplier`, `get_condition_money_ratio`, `is_good_condition`, `get_status_names`, `get_grad_money_multiplier`, `get_upgrade_cost`, `can_buy_upgrade`, `buy_upgrade`, `is_upgrade_maxed`, `get_upgrade_row_rect`, `reincarnate`, `enter_grad_school`, `can_reincarnate`, `is_graduation_ending`, `is_grad_school_ending`, `load_record`, `save_record`, `load_best_record`, `save_best_record`, `update_best_record`, `get_season`, `get_time_of_day`, `get_sky_color`, `get_place`, `get_owned_facilities`, `get_scene_shade`, `get_goal_text`, `get_ending_layout`, `get_shown_gauge`, `get_gauge_values`, `get_student_lift`, `is_blink_on`, `clear_effects`, `get_upgrade_effect_text(id, level)`, `get_upgrade_tooltip_rows(id)`, `get_hovered_upgrade_index`, `get_tooltip_rect(rows, anchor_top)`, `draw_tooltip`, `draw_upgrade_tooltip`, `get_status_tip_text(name)`, `get_hovered_status`, `draw_status_tooltip`, `get_decor_levels`, `get_decor_pieces`, `get_decor_rects`, `draw_decorations`, `make_scenery(place, season, facilities, shade=0, decor_levels=None)`
- Student 상태: `health`, `mental`, `knowledge`, `elapsed`, `decay_timer`, `grade`, `grad_year`, `graduation_time`, `grad_entry_time`, `traits`, `looks`, `flags`, `seen_events`, `event_counts`, `last_event_time`, `upgrades`, `full_until`, `max_health`·`max_mental`(property)
- Student 메서드: `update(dt)`, `feed`, `rest(recovery_ratio)`, `study(knowledge_ratio, cost_ratio)`, `is_tired`, `is_depressed`, `has_debuff(name)`, `is_full_buff_active`, `get_full_time_left`, `get_full_duration`, `get_statuses`, `get_self_care_regen`, `decay_once`, `promote`, `get_grade`, `get_next_goal`, `get_goal_start`, `get_goal_progress`, `get_knowledge_to_goal`, `has_graduated`, `get_cycle_index`, `get_cycle_time`, `is_exam_period`, `is_in_grad_school`, `enter_grad_school`, `get_grad_goal(year)`, `get_grad_cycles`, `get_grad_decay_ratio`, `get_health_decay`, `get_mental_decay`, `get_study_knowledge`, `get_upgrade_bonus`, `get_trait_bonus`, `is_dropped_out`, `get_ending`, `get_graduation_ending`, `get_radius`, `get_mouth`, `has_dark_circles`, `has_glasses`, `get_cycle_event_count`, `count_event`, `is_event_gap_passed`, `can_have_event`, `needs_guaranteed_event`, `can_see_event`, `apply_effects`, `add_trait`, `add_look`, `add_flag`, `change_health`, `change_mental`, `change_knowledge`, `get_badge_rect(index, top)`, `draw_traits`, `draw_looks`, `draw_status_badges`
- Button: `rect`, `text`, `is_clicked(pos)`, `draw(...)`

## 10. 밸런스

- **확정 해석:** 수치를 바꿀 이유가 생기면 바로 바꾸지 않는다. 시뮬레이션 근거와 조정안을 리드에게 보고하고, 사용자 승인 후 config.py와 기획서를 함께 바꾼다. 목표·시뮬레이션 결과는 기획서 10절.
