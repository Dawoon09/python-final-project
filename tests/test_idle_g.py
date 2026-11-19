"""G단위 검수: 자동 행동(2초) + 일과표 방침 3종, 쿨타임 제거, 방침 버튼·진행 막대 (기획서 10절, jeja-spec 15절).

이 파일은 conftest 의 AUTO_OFF_FILES 에 없으므로 자동 행동이 켜진 채로 돈다.
이벤트가 끼어들면 안 되는 테스트는 no_events 픽스처를 직접 쓴다.
"""

import ast
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
import game as game_module  # noqa: E402
from button import Button  # noqa: E402
from conftest import press  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402

ROOT = Path(config.__file__).parent
FRAME = 1 / 60
P = config.PIXEL_SIZE
FEED, REST, STUDY = config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY
SF, BAL, RF = config.POLICY_STUDY_FOCUS, config.POLICY_BALANCED, config.POLICY_REST_FOCUS


@pytest.fixture
def g(no_events):
    """이벤트를 끈 채 타이틀에서 Enter 를 눌러 게임 중인 Game."""
    game = Game()
    press(game, pygame.K_RETURN)
    assert game.state == config.STATE_PLAYING
    yield game
    pygame.quit()


@pytest.fixture
def seeded():
    """이벤트를 켠 채 seed 고정 Game 을 게임 중으로 만드는 함수."""
    made = []

    def factory(seed):
        game = Game(seed=seed)
        press(game, pygame.K_RETURN)
        made.append(game)
        return game
    yield factory
    pygame.quit()


def gauges(game):
    s = game.student
    return (s.health, s.mental, s.knowledge)


def record_actions(game, monkeypatch):
    """game.do_action 호출을 (게임 시각, 이름) 목록으로 기록한다(실제 실행은 그대로)."""
    log = []
    real = game.do_action

    def spy(name):
        log.append((round(game.student.elapsed, 6), name))
        return real(name)
    monkeypatch.setattr(game, "do_action", spy)
    return log


def color(surf, x, y):
    return tuple(surf.get_at((x, y)))[:3]


def body_point(game, name):
    r = game.buttons[name].rect
    return r.left + 2 * P, r.centery


# ======================= 1. config 수치 (jeja-spec 15절 표) =======================

def test_auto_interval_and_no_cooldown_constant():
    assert config.AUTO_ACTION_INTERVAL == 2.0
    assert not hasattr(config, "ACTION_COOLDOWN")


@pytest.mark.parametrize("name, key, threshold, k_ratio, c_ratio, text", [
    (SF, pygame.K_1, 30, 1.4, 1.6, "공부 위주 [1]"),
    (BAL, pygame.K_2, 50, 1.0, 1.0, "균형 [2]"),
    (RF, pygame.K_3, 70, 0.8, 0.7, "휴식 위주 [3]"),
])
def test_policy_table(name, key, threshold, k_ratio, c_ratio, text):
    p = config.POLICIES[name]
    assert p[config.POLICY_THRESHOLD] == threshold
    assert p[config.POLICY_KNOWLEDGE_RATIO] == k_ratio
    assert p[config.POLICY_COST_RATIO] == c_ratio
    assert p[config.POLICY_TEXT] == text
    assert game_module.POLICY_KEYS[key] == name


def test_policy_names_order_and_start():
    assert (SF, BAL, RF) == ("study_focus", "balanced", "rest_focus")
    assert config.POLICY_START == BAL
    assert config.POLICY_ORDER == [SF, BAL, RF]
    assert set(config.POLICIES) == {SF, BAL, RF}
    assert set(game_module.POLICY_KEYS) == {pygame.K_1, pygame.K_2, pygame.K_3}


# ======================= 2. 자동 행동 시각 =======================

def test_new_round_initial_values(g):
    assert g.policy == BAL
    assert g.auto_timer == config.AUTO_ACTION_INTERVAL
    assert g.last_action is None
    assert g.get_auto_progress() == 0


def test_first_action_at_2s_not_at_198(g, monkeypatch):
    log = record_actions(g, monkeypatch)
    g.update(1.98)
    assert log == [] and g.last_action is None
    assert g.auto_timer == pytest.approx(0.02)
    g.update(0.02)
    assert log == [(2.0, STUDY)]
    assert g.last_action == STUDY
    assert g.auto_timer == pytest.approx(config.AUTO_ACTION_INTERVAL)


def test_first_action_by_60fps_frames(g, monkeypatch):
    """119프레임(1.983초)에는 아직, 120프레임(2.0초, 부동소수 누적 오차 포함)에 첫 행동."""
    log = record_actions(g, monkeypatch)
    for _ in range(119):
        g.update(FRAME)
    assert log == []
    g.update(FRAME)
    assert len(log) == 1 and log[0][0] == pytest.approx(2.0)


def test_interval_every_2s(g, monkeypatch):
    log = record_actions(g, monkeypatch)
    for _ in range(int(10.5 * 60)):
        g.update(FRAME)
    assert [t for t, _ in log] == pytest.approx([2.0, 4.0, 6.0, 8.0, 10.0])


def test_progress_fraction(g):
    assert g.get_auto_progress() == 0
    g.update(0.5)
    assert g.get_auto_progress() == pytest.approx(0.25)
    g.update(1.0)
    assert g.get_auto_progress() == pytest.approx(0.75)
    g.update(0.5)                      # 행동 -> 다시 0
    assert g.get_auto_progress() == pytest.approx(0.0)


def test_do_action_does_not_refill_auto_timer(g):
    g.update(0.7)
    before = g.auto_timer
    assert g.do_action(FEED)
    assert g.do_action(STUDY)          # 쿨타임 없음: 바로 이어서도 실행
    assert g.auto_timer == pytest.approx(before)
    assert g.last_action == STUDY


def test_auto_action_follows_choose_rule(g, monkeypatch):
    log = record_actions(g, monkeypatch)
    g.student.health, g.student.mental = 45, 60
    g.update(2.0)                      # 자연 감소 2 -> 43, 58 -> 체력 < 50 -> 학식
    assert log[-1][1] == FEED and g.last_action == FEED
    assert g.student.health == 43 + config.FEED_HEALTH


# ======================= 3. 행동 고르기 (회복 기준, 동점, 경계) =======================

@pytest.mark.parametrize("policy, health, mental, expected", [
    # 균형: 기준 50
    (BAL, 50, 50, STUDY), (BAL, 100, 100, STUDY),
    (BAL, 49, 80, FEED), (BAL, 80, 49, REST),
    (BAL, 49, 49, FEED),                         # 동점 -> 학식
    (BAL, 30, 40, FEED), (BAL, 40, 30, REST),
    (BAL, 49, 50, FEED), (BAL, 50, 49, REST),
    (BAL, 10, 49, FEED),                         # 둘 다 미만, 체력이 더 낮음
    (BAL, 0, 0, FEED),
    # 공부 위주: 기준 30
    (SF, 30, 30, STUDY), (SF, 31, 30, STUDY), (SF, 29, 100, FEED), (SF, 100, 29, REST),
    (SF, 29, 29, FEED), (SF, 35, 35, STUDY), (SF, 49, 49, STUDY),
    # 휴식 위주: 기준 70
    (RF, 70, 70, STUDY), (RF, 69, 69, FEED), (RF, 69, 90, FEED), (RF, 90, 69, REST),
    (RF, 60, 50, REST), (RF, 50, 60, FEED), (RF, 69, 70, FEED), (RF, 70, 69, REST),
])
def test_choose_auto_action(g, policy, health, mental, expected):
    assert g.set_policy(policy)
    g.student.health, g.student.mental = health, mental
    assert g.choose_auto_action() == expected


@pytest.mark.parametrize("knowledge", [0, 449, 700, 5000])
def test_choose_ignores_knowledge_and_time(g, knowledge):
    g.student.knowledge = knowledge
    g.student.elapsed = 50.0           # 시험 기간이어도 같은 규칙
    assert g.choose_auto_action() == STUDY
    g.student.health = 49
    assert g.choose_auto_action() == FEED


# ======================= 4. 방침별 공부 수치 (기본값+보너스 -> 배수 -> 반올림) =======================
# 기대값은 기획서 10절 표로 손계산: 공부 위주 지식 10x1.4=14, 체력 -5x1.6=-8, 멘탈 -8x1.6=-12.8->-13
# 휴식 위주 지식 10x0.8=8, 체력 -5x0.7=-3.5->-4, 멘탈 -8x0.7=-5.6->-6
# 카페인(체력 -5+2=-3): 공부 위주 -4.8->-5, 휴식 위주 -2.1->-2

@pytest.mark.parametrize("policy, exam, caffeine, dk, dh, dm", [
    (SF, False, False, 14, -8, -13),
    (SF, True, False, 28, -8, -13),
    (SF, False, True, 14, -5, -13),
    (SF, True, True, 28, -5, -13),
    (BAL, False, False, 10, -5, -8),
    (BAL, True, False, 20, -5, -8),
    (BAL, False, True, 10, -3, -8),
    (RF, False, False, 8, -4, -6),
    (RF, True, False, 16, -4, -6),
    (RF, False, True, 8, -2, -6),
    (RF, True, True, 16, -2, -6),
])
def test_study_numbers_per_policy_via_game(g, policy, exam, caffeine, dk, dh, dm):
    g.set_policy(policy)
    s = g.student
    s.elapsed = 45.0 if exam else 10.0
    if caffeine:
        s.add_trait(config.TRAIT_CAFFEINE)
    s.health, s.mental, s.knowledge = 60, 60, 100
    assert g.do_action(STUDY)
    assert (s.knowledge - 100, s.health - 60, s.mental - 60) == (dk, dh, dm)


@pytest.mark.parametrize("policy", [SF, BAL, RF])
def test_student_study_ratios_match_game(policy):
    p = config.POLICIES[policy]
    a, b = Student(), Student()
    a.health = a.mental = b.health = b.mental = 60
    a.study(p[config.POLICY_KNOWLEDGE_RATIO], p[config.POLICY_COST_RATIO])
    b.study()
    assert b.knowledge == config.STUDY_KNOWLEDGE           # 기본값 1.0 = 예전과 같음
    assert (b.health, b.mental) == (60 + config.STUDY_HEALTH, 60 + config.STUDY_MENTAL)
    assert a.knowledge == round(config.STUDY_KNOWLEDGE * p[config.POLICY_KNOWLEDGE_RATIO])
    assert isinstance(a.health, int) and isinstance(a.mental, int)


@pytest.mark.parametrize("policy", [SF, BAL, RF])
def test_feed_and_rest_ignore_policy(g, policy):
    g.set_policy(policy)
    s = g.student
    s.health, s.mental, s.knowledge = 50, 50, 10
    assert g.do_action(FEED)
    assert (s.health, s.mental, s.knowledge) == (70, 50, 10)
    assert g.do_action(REST)
    assert (s.health, s.mental, s.knowledge) == (70, 70, 8)


def test_study_with_policy_clamped_and_leave(g):
    g.set_policy(SF)
    g.student.mental = 12              # -13 -> 0 에서 멈추고 바로 휴학
    assert g.do_action(STUDY)
    assert g.student.mental == 0
    assert g.state == config.STATE_ENDING and g.ending == config.ENDING_LEAVE


def test_auto_study_in_exam_uses_policy(g):
    g.set_policy(SF)
    s = g.student
    s.elapsed = 45.0
    s.health, s.mental, s.knowledge = 90, 90, 0
    g.auto_timer = 0.5
    g.update(0.5)
    assert g.last_action == STUDY
    assert s.knowledge == 28


# ======================= 5. 방침 바꾸기 (키 1/2/3, 클릭, set_policy) =======================

@pytest.mark.parametrize("key, policy", [(pygame.K_1, SF), (pygame.K_2, BAL), (pygame.K_3, RF)])
def test_keys_select_policy(g, key, policy):
    g.set_policy(RF if policy != RF else SF)
    before = gauges(g)
    press(g, key)
    assert g.policy == policy
    assert gauges(g) == before and g.last_action is None


@pytest.mark.parametrize("policy", [SF, BAL, RF])
def test_click_selects_policy(g, policy):
    g.set_policy(RF if policy != RF else SF)
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=pygame.BUTTON_LEFT,
                                      pos=g.buttons[policy].rect.center))
    assert g.policy == policy
    assert g.last_action is None


def test_buttons_keyed_by_policy_names(g):
    assert list(g.buttons) == config.POLICY_ORDER
    for name, button in g.buttons.items():
        assert button.text == config.POLICIES[name][config.POLICY_TEXT]


def test_set_policy_return_values(g):
    assert g.set_policy(SF) is True and g.policy == SF
    assert g.set_policy("lazy") is False and g.policy == SF
    assert g.set_policy(FEED) is False and g.policy == SF


def test_policy_change_applies_to_next_auto_action(g):
    g.update(1.0)
    press(g, pygame.K_1)
    g.student.health = g.student.mental = 90
    k = g.student.knowledge
    g.update(1.0)
    assert g.last_action == STUDY and g.student.knowledge == k + 14


def test_keys_in_title_and_ending_do_not_change_policy(no_events):
    game = Game()
    press(game, pygame.K_1)
    assert game.policy == BAL and game.state == config.STATE_TITLE
    press(game, pygame.K_RETURN)
    game.end_game(config.ENDING_NORMAL)
    press(game, pygame.K_3)
    assert game.policy == BAL and game.state == config.STATE_ENDING
    pygame.quit()


# ======================= 6. 대화창(STATE_EVENT): 키 1·2 선택, 3 무시, 시계 정지 =======================

def _mt_invite():
    return next(e for e in config.CHOICE_EVENTS if e[config.EVENT_ID] == "mt_invite")


def test_dialog_keys_choose_options_not_policy(g):
    g.update(1.0)
    g.start_event(_mt_invite())
    assert g.state == config.STATE_EVENT
    g.update(config.EVENT_INPUT_DELAY)
    press(g, pygame.K_3)               # 무시
    assert g.state == config.STATE_EVENT and g.policy == BAL
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=pygame.BUTTON_LEFT,
                                      pos=g.buttons[RF].rect.center))
    assert g.policy == BAL             # 방침 버튼 클릭도 무시
    press(g, pygame.K_1)               # 첫 번째 선택지
    assert g.state == config.STATE_PLAYING
    assert g.policy == BAL             # 키 1 이 방침(공부 위주)으로 새지 않음


def test_dialog_key2_chooses_second(g):
    g.start_event(_mt_invite())
    g.update(config.EVENT_INPUT_DELAY)
    before = gauges(g)
    press(g, pygame.K_2)
    assert g.state == config.STATE_PLAYING and g.policy == BAL
    assert gauges(g) != before


def test_auto_timer_paused_in_dialog_then_resumes(g, monkeypatch):
    g.update(1.2)
    g.start_event(_mt_invite())
    t, elapsed = g.auto_timer, g.student.elapsed
    log = record_actions(g, monkeypatch)
    for _ in range(600):
        g.update(FRAME)                # 10초
    g.update(50.0)
    assert (g.auto_timer, g.student.elapsed) == (t, elapsed)
    assert log == []
    press(g, pygame.K_1)
    assert g.state == config.STATE_PLAYING
    assert g.auto_timer == t           # 선택해도 시계를 다시 채우지 않음
    g.update(t - 0.01)
    assert log == []
    g.update(0.01)
    assert len(log) == 1               # 남은 시간(0.8초)이 지나야 다음 행동


def test_dialog_opened_by_auto_action_stops_rest_of_dt(seeded, monkeypatch):
    """큰 dt 중 자동 행동 직후 대화창이 뜨면 그 dt 의 남은 시간은 흐르지 않는다."""
    game = seeded(3)
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    monkeypatch.setattr(game, "pick_event", _mt_invite)
    game.student.last_event_time = None
    game.update(7.0)
    assert game.state == config.STATE_EVENT
    assert game.student.elapsed == pytest.approx(2.0)
    assert game.last_action is not None


@pytest.mark.parametrize("state", [config.STATE_TITLE, config.STATE_ENDING])
def test_auto_timer_paused_in_title_and_ending(no_events, monkeypatch, state):
    game = Game()
    if state == config.STATE_ENDING:
        press(game, pygame.K_RETURN)
        game.update(0.5)
        game.end_game(config.ENDING_NORMAL)
    t = game.auto_timer
    log = record_actions(game, monkeypatch)
    for _ in range(300):
        game.update(FRAME)
    game.update(100.0)
    assert game.auto_timer == t and log == []
    pygame.quit()


# ======================= 7. 큰 dt: 행동 시각마다 끊어서 처리 =======================

def test_large_dt_equals_frame_steps(no_events):
    a, b = Game(), Game()
    for game in (a, b):
        press(game, pygame.K_RETURN)
    a.update(7.0)
    for _ in range(7 * 60):
        b.update(FRAME)
    # 0~2초 감소 2 -> 78/78 -> 공부 73/70 k10, 2~4초 71/68 -> 66/60 k20,
    # 4~6초 64/58 -> 59/50 k30, 6~7초 58/49
    assert gauges(a) == gauges(b) == (58, 49, 30)
    assert a.auto_timer == pytest.approx(1.0) and b.auto_timer == pytest.approx(1.0, abs=1e-6)
    pygame.quit()


def test_large_dt_action_saves_student(g):
    """체력 3: 한 번에 5초를 흘려도 2초에 학식(1 -> 21), 4초에 학식(19 -> 39) 해서 산다."""
    g.student.health = 3
    g.update(5.0)
    assert g.state == config.STATE_PLAYING
    assert g.student.health == 38


def test_large_dt_leave_before_action_at_same_time(g, monkeypatch):
    """자연 감소로 2초 시점에 0이 되면 그 시각 자동 행동 없이 바로 휴학."""
    log = record_actions(g, monkeypatch)
    g.student.health = 2
    g.update(10.0)
    assert g.state == config.STATE_ENDING and g.ending == config.ENDING_LEAVE
    assert log == [] and g.student.elapsed == pytest.approx(2.0)


def test_large_dt_graduation_stops_actions(g, monkeypatch):
    g.student.elapsed = 236.5
    g.auto_timer = 0.5
    g.student.health = g.student.mental = 100
    log = record_actions(g, monkeypatch)
    g.update(100.0)
    assert g.state == config.STATE_ENDING and g.ending in (
        config.ENDING_TOP, config.ENDING_NORMAL, config.ENDING_BARELY)
    assert [t for t, _ in log] == pytest.approx([237.0, 239.0])
    assert g.student.elapsed == pytest.approx(config.TOTAL_SECONDS)


# ======================= 8. 이벤트는 자동 행동 직후에만 판정 =======================

def test_events_roll_only_after_auto_actions(seeded, monkeypatch):
    game = seeded(11)
    calls = []
    monkeypatch.setattr(game, "roll_event", lambda: calls.append(game.student.elapsed))
    game.update(1.99)
    assert calls == []
    for _ in range(int(8.1 * 60)):
        game.update(FRAME)
    assert calls == pytest.approx([2.0, 4.0, 6.0, 8.0, 10.0])   # 1.99 + 8.1 = 10.09초


def _idle_run(game, choose=config.CHOICE_FIRST, draw_every=0):
    """방치 플레이: 대화창이 뜨면 입력 대기 뒤 choose 번째를 고른다. (시각, 상태, 게이지) 기록."""
    log = []
    frames = 0
    while game.state in (config.STATE_PLAYING, config.STATE_EVENT):
        if game.state == config.STATE_EVENT and game.is_dialog_ready():
            game.choose_option(choose)
        game.update(FRAME)
        frames += 1
        if draw_every and frames % draw_every == 0:
            game.draw()
        s = game.student
        log.append((round(s.elapsed, 6), game.state, s.health, s.mental, s.knowledge,
                    game.last_action, dict(s.event_counts)))
        assert 0 <= s.health <= 100 and 0 <= s.mental <= 100 and s.knowledge >= 0
        assert frames < 20 * config.TOTAL_SECONDS * 60
    return log


def test_same_seed_same_idle_play(seeded):
    a, b = seeded(21), seeded(21)
    assert _idle_run(a) == _idle_run(b)
    assert a.ending == b.ending


@pytest.mark.parametrize("seed", range(6))
@pytest.mark.parametrize("policy", [SF, BAL, RF])
def test_idle_play_keeps_event_rules(seeded, seed, policy):
    """방치 플레이에서도 9절 규칙: 끝까지 간 학년은 이벤트 4~5회."""
    game = seeded(seed)
    game.set_policy(policy)
    _idle_run(game, choose=seed % 2)
    s = game.student
    last = s.get_grade() if game.ending == config.ENDING_LEAVE else config.MAX_GRADE + 1
    for grade in range(config.FIRST_GRADE, last):
        assert config.EVENT_MIN_PER_GRADE <= s.event_counts[grade] <= config.EVENT_MAX_PER_GRADE, \
            (seed, policy, dict(s.event_counts))


# ======================= 9. 새 판에서 방침 초기화 =======================

def test_policy_resets_on_restart(g):
    press(g, pygame.K_3)
    g.update(1.5)
    g.end_game(config.ENDING_NORMAL)
    assert g.policy == RF
    press(g, pygame.K_r)
    assert g.state == config.STATE_PLAYING
    assert g.policy == config.POLICY_START
    assert g.auto_timer == config.AUTO_ACTION_INTERVAL and g.last_action is None


def test_policy_resets_on_start_new_game(g):
    g.set_policy(SF)
    g.start_new_game()
    assert g.policy == BAL


# ======================= 10. 수치는 config 에서 온다 =======================

def test_interval_read_from_config(no_events, monkeypatch):
    monkeypatch.setattr(config, "AUTO_ACTION_INTERVAL", 3.0)
    game = Game()
    press(game, pygame.K_RETURN)
    log = record_actions(game, monkeypatch)
    game.update(2.99)
    assert log == []
    game.update(0.01)
    assert len(log) == 1
    assert game.auto_timer == pytest.approx(3.0)
    pygame.quit()


def test_threshold_and_ratios_read_from_config(g, monkeypatch):
    table = {name: dict(values) for name, values in config.POLICIES.items()}
    table[BAL][config.POLICY_THRESHOLD] = 90
    table[BAL][config.POLICY_KNOWLEDGE_RATIO] = 3.0
    table[BAL][config.POLICY_COST_RATIO] = 0.0
    monkeypatch.setattr(config, "POLICIES", table)
    g.student.health = g.student.mental = 89
    assert g.choose_auto_action() == FEED
    g.student.health = g.student.mental = 90
    assert g.choose_auto_action() == STUDY
    assert g.do_action(STUDY)
    assert gauges(g) == (90, 90, 30)


def test_policy_names_not_hardcoded_in_game_code():
    for name in ("game.py", "student.py", "button.py"):
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        literals = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                    and isinstance(n.value, str)}
        for policy in (SF, BAL, RF, "threshold", "knowledge_ratio", "cost_ratio"):
            assert policy not in literals, (name, policy)


def test_no_cooldown_left_in_game_code():
    for name in ("game.py", "button.py", "student.py"):
        src = (ROOT / name).read_text(encoding="utf-8")
        assert "ACTION_COOLDOWN" not in src and "self.cooldown" not in src, name


# ======================= 11. 그리기: 선택 강조, 진행 막대 =======================

def test_button_draw_selected_color():
    pygame.init()
    try:
        surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        font = pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE)
        b = Button(28, config.BUTTON_Y, config.BUTTON_WIDTH, config.BUTTON_HEIGHT, "x")
        pt = (b.rect.left + 2 * P, b.rect.centery)
        b.draw(surf, font, False)
        assert color(surf, *pt) == config.COLOR_BUTTON
        b.draw(surf, font, False, selected=True)
        assert color(surf, *pt) == config.COLOR_POLICY_SELECTED
        b.draw(surf, font, False, hovered=True, selected=True)
        assert color(surf, *pt) == config.COLOR_POLICY_SELECTED   # 선택이 호버보다 우선
        b.draw(surf, font, False, hovered=True)
        assert color(surf, *pt) == config.COLOR_BUTTON_BRIGHT
        assert config.COLOR_POLICY_SELECTED not in (config.COLOR_BUTTON, config.COLOR_BUTTON_BRIGHT,
                                                    config.COLOR_GRAY)
        r, gr, bl = config.COLOR_POLICY_SELECTED
        assert r > bl and gr > bl          # 노랑 계열
    finally:
        pygame.quit()


@pytest.mark.parametrize("key, policy", [(pygame.K_1, SF), (pygame.K_2, BAL), (pygame.K_3, RF)])
def test_selected_policy_button_highlighted_on_screen(g, key, policy):
    press(g, key)
    g.update(config.BUTTON_PRESS_TIME + FRAME)    # 눌림 연출이 끝난 뒤
    g.draw()
    for name in g.buttons:
        want = config.COLOR_POLICY_SELECTED if name == policy else config.COLOR_BUTTON
        assert color(g.screen, *body_point(g, name)) == want, name


def _bar_fill_count(game):
    bar = pygame.Rect(config.BUTTON_START_X, config.AUTO_BAR_Y,
                      config.POLICY_AREA_WIDTH, config.AUTO_BAR_HEIGHT)
    return sum(1 for x in range(bar.left, bar.right) for y in range(bar.top, bar.bottom)
               if color(game.screen, x, y) == config.COLOR_COOLDOWN_FILL)


def test_auto_progress_bar_pixels(g):
    bar_top = config.AUTO_BAR_Y
    assert bar_top >= config.BUTTON_Y + config.BUTTON_HEIGHT + P   # 버튼(받침 포함) 아래
    g.draw()
    assert _bar_fill_count(g) == 0
    counts = []
    for _ in range(119):
        g.update(FRAME)
        g.draw()
        counts.append(_bar_fill_count(g))
    assert counts == sorted(counts)                 # 차오르기만 한다
    full = counts[-1]
    assert full > 0
    half = counts[59]                               # 1.0초 = 절반
    assert abs(half / full - 0.5) < 0.05
    g.update(FRAME)                                 # 2초: 행동 -> 막대가 비워짐
    g.draw()
    assert _bar_fill_count(g) == 0


def test_auto_bar_drawn_in_dialog_but_frozen(g):
    g.update(1.0)
    g.start_event(_mt_invite())
    g.draw()
    a = pygame.image.tobytes(g.screen.subsurface(
        pygame.Rect(config.BUTTON_START_X, config.AUTO_BAR_Y, config.POLICY_AREA_WIDTH,
                    config.AUTO_BAR_HEIGHT)), "RGB")
    g.update(1.0)
    g.draw()
    b = pygame.image.tobytes(g.screen.subsurface(
        pygame.Rect(config.BUTTON_START_X, config.AUTO_BAR_Y, config.POLICY_AREA_WIDTH,
                    config.AUTO_BAR_HEIGHT)), "RGB")
    assert a == b


# ======================= 12. 연출은 결과에 영향 없음 (자동 행동 켠 채) =======================

def test_effects_do_not_change_idle_results(no_events, monkeypatch, tmp_path):
    def run(with_fx):
        game = Game(record_path=str(tmp_path / f"{with_fx}.json"))
        press(game, pygame.K_RETURN)
        game.set_policy(SF)
        log = _idle_run(game, draw_every=120 if with_fx else 0)
        pygame.quit()
        return log, game.ending
    with_fx = run(True)
    monkeypatch.setattr(Game, "start_action_effects", lambda self, name, before: None)
    monkeypatch.setattr(Game, "update_effects", lambda self, dt: None)
    assert run(False) == with_fx


@pytest.mark.parametrize("policy", [SF, BAL, RF])
def test_idle_full_play_reaches_ending(no_events, policy):
    """아무것도 안 해도(방치) 제자가 스스로 행동해 끝까지 간다(엔딩 종류는 밸런스 단계에서 본다)."""
    game = Game()
    press(game, pygame.K_RETURN)
    game.set_policy(policy)
    _idle_run(game)
    assert game.state == config.STATE_ENDING
    assert game.ending is not None
    pygame.quit()
