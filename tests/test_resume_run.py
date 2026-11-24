"""(이어하기) 하던 판 저장·불러오기: ESC·창 닫기·자동 저장, 엔딩·새 게임이면 지움, 이상한 값은 무시."""

import json

import pygame
import pytest

import config
from conftest import press, reach_grade
from game import Game


def read(path):
    """record.json 사전."""
    with open(path, encoding=config.RECORD_ENCODING) as f:
        return json.load(f)


def write(path, data):
    """record.json을 직접 쓴다."""
    with open(path, "w", encoding=config.RECORD_ENCODING) as f:
        json.dump(data, f)


@pytest.fixture
def g():
    """타이틀 Game (저장된 판 없음)."""
    game = Game(seed=4)
    yield game
    pygame.quit()


def play(g, seconds, dt=1 / 60):
    """게임 시간을 seconds만큼 흘린다(체력·멘탈은 넉넉히)."""
    for _ in range(int(seconds / dt)):
        g.student.health = g.student.mental = 90
        g.update(dt)
        if g.state == config.STATE_EVENT:
            g.dialog_time = config.EVENT_INPUT_DELAY
            g.choose_option(config.CHOICE_FIRST)


def set_up_run(g):
    """특징 있는 판을 만든다: 2학년, 특성·외형·플래그, 버프, 방침, 로그."""
    press(g, pygame.K_RETURN)
    g.student.elapsed = 75.5
    reach_grade(g.student, 2)
    g.student.knowledge = 450
    g.student.health, g.student.mental = 61.5, 42
    g.student.traits = [config.TRAIT_MUSIC, config.TRAIT_MORNING]
    g.student.looks = [config.LOOK_GUITAR]
    g.student.flags = {config.FLAG_BAND, config.FLAG_MT}
    g.student.seen_events = {"club_fair", "mt_invite"}
    g.student.event_counts = {1: 4, 2: 1}
    g.student.last_event_time = 70.0
    g.student.full_until = 90.0
    g.student.refresh_until = 80.0
    g.policy = config.POLICY_REST_FOCUS
    g.auto_timer = 1.25
    g.add_event_log("감기 기운이 돈다", "체력 -10")


def test_no_run_at_start(g, isolated_record_path):
    assert g.saved_run is None and g.get_resume_hint_text() is None
    press(g, pygame.K_RETURN)
    assert g.state == config.STATE_PLAYING and g.student.elapsed == 0


@pytest.mark.parametrize("how", ["esc", "quit"])
def test_quit_during_play_saves_and_resumes(g, isolated_record_path, how):
    set_up_run(g)
    if how == "esc":
        press(g, pygame.K_ESCAPE)
    else:
        g.handle_event(pygame.event.Event(pygame.QUIT))
    assert g.running is False
    assert config.RECORD_RUN_KEY in read(isolated_record_path)
    g2 = Game(seed=9)
    assert g2.state == config.STATE_TITLE
    assert g2.get_resume_hint_text() == "Enter를 눌러 이어하기 (2학년, 1분 15초)"
    press(g2, pygame.K_RETURN)
    s = g2.student
    assert g2.state == config.STATE_PLAYING
    assert (s.elapsed, s.grade, s.knowledge, s.health, s.mental) == (75.5, 2, 450, 61.5, 42)
    assert s.traits == [config.TRAIT_MUSIC, config.TRAIT_MORNING] and s.looks == [config.LOOK_GUITAR]
    assert s.flags == {config.FLAG_BAND, config.FLAG_MT}
    assert s.seen_events == {"club_fair", "mt_invite"} and s.event_counts == {1: 4, 2: 1}
    assert (s.last_event_time, s.full_until, s.refresh_until) == (70.0, 90.0, 80.0)
    assert g2.policy == config.POLICY_REST_FOCUS and g2.auto_timer == 1.25
    assert g2.event_log == [{"time": 75.5, "title": "감기 기운이 돈다", "result": "체력 -10"}]
    assert s.upgrades is g2.upgrades
    pygame.quit()


def test_resumed_run_keeps_going(g, isolated_record_path):
    set_up_run(g)
    press(g, pygame.K_ESCAPE)
    g2 = Game(seed=9)
    press(g2, pygame.K_RETURN)
    play(g2, 5)
    assert g2.student.elapsed == pytest.approx(80.5)
    assert g2.last_action is not None
    pygame.quit()


def test_resume_open_choice_dialog(g, isolated_record_path):
    press(g, pygame.K_RETURN)
    event = next(e for e in config.CHOICE_EVENTS if e[config.EVENT_ID] == "mt_invite")
    g.start_event(event)
    counts = dict(g.student.event_counts)
    press(g, pygame.K_ESCAPE)
    g2 = Game(seed=9)
    press(g2, pygame.K_RETURN)
    assert g2.state == config.STATE_EVENT and g2.current_event is event
    assert g2.student.event_counts == counts            # 다시 세지 않는다
    assert g2.choice_buttons[0].text.endswith("간다")
    g2.dialog_time = config.EVENT_INPUT_DELAY
    assert g2.choose_option(config.CHOICE_FIRST)
    assert config.FLAG_MT in g2.student.flags
    pygame.quit()


def test_autosave_every_10_seconds(g, isolated_record_path):
    press(g, pygame.K_RETURN)
    play(g, 9.5)
    import os
    assert not os.path.exists(isolated_record_path)   # 10초 전에는 아직 저장 안 함
    play(g, 1.0)
    run = read(isolated_record_path)[config.RECORD_RUN_KEY]
    assert run["elapsed"] == pytest.approx(10.0, abs=0.1)
    play(g, 10.0)
    assert read(isolated_record_path)[config.RECORD_RUN_KEY]["elapsed"] == pytest.approx(20.0,
                                                                                         abs=0.1)


def test_ending_clears_run(g, isolated_record_path):
    press(g, pygame.K_RETURN)
    play(g, 11)
    assert config.RECORD_RUN_KEY in read(isolated_record_path)
    g.student.health = 0
    g.check_ending()
    assert g.state == config.STATE_ENDING
    assert g.saved_run is None and config.RECORD_RUN_KEY not in read(isolated_record_path)
    press(g, pygame.K_ESCAPE)            # 엔딩에서 꺼도 판은 저장하지 않는다
    assert config.RECORD_RUN_KEY not in read(isolated_record_path)


def test_esc_on_title_keeps_saved_run(g, isolated_record_path):
    set_up_run(g)
    press(g, pygame.K_ESCAPE)
    before = read(isolated_record_path)
    g2 = Game(seed=9)
    press(g2, pygame.K_ESCAPE)
    assert read(isolated_record_path) == before
    pygame.quit()


def test_new_game_clears_run(g, isolated_record_path):
    set_up_run(g)
    press(g, pygame.K_ESCAPE)
    g2 = Game(seed=9)
    g2.money = g2.fame = 0
    for u in g2.upgrades:
        g2.upgrades[u] = 0
    assert g2.has_progress()                   # 하던 판만 있어도 진행이 있다
    press(g2, pygame.K_n)
    assert g2.new_game_confirm
    press(g2, pygame.K_y)
    assert g2.saved_run is None and g2.student.elapsed == 0
    assert config.RECORD_RUN_KEY not in read(isolated_record_path)
    pygame.quit()


def test_grad_school_run(g, isolated_record_path):
    press(g, pygame.K_RETURN)
    g.student.knowledge = config.GRADUATION_KNOWLEDGE
    g.check_promotion()
    g.check_ending()
    press(g, pygame.K_c)
    assert g.grad_year == 1
    entry = g.student.grad_entry_time
    press(g, pygame.K_ESCAPE)
    g2 = Game(seed=9)
    assert g2.get_resume_hint_text().startswith("Enter를 눌러 이어하기 (대학원 1년차,")
    press(g2, pygame.K_RETURN)
    assert g2.grad_year == 1 and g2.student.grad_entry_time == entry
    assert g2.student.is_in_grad_school()
    pygame.quit()


def good_run(g):
    """올바른 하던 판 사전 하나."""
    press(g, pygame.K_RETURN)
    return g.capture_run()


@pytest.mark.parametrize("change", [
    lambda r: r.update(health=0), lambda r: r.update(mental=-3), lambda r: r.update(health="80"),
    lambda r: r.update(elapsed=True), lambda r: r.update(grade=5), lambda r: r.update(grade=1.0),
    lambda r: r.update(grad_year=-1), lambda r: r.update(traits=["슈퍼맨"]),
    lambda r: r.update(looks="guitar"), lambda r: r.update(flags=["없는 플래그"]),
    lambda r: r.update(seen_events=["nope"]), lambda r: r.update(event_counts={"a": 1}),
    lambda r: r.update(event_counts={"1": -1}), lambda r: r.update(policy="sleep"),
    lambda r: r.update(auto_timer=None), lambda r: r.update(event_log=[{"time": 1}]),
    lambda r: r.update(event="side_dish"), lambda r: r.update(full_until="soon"),
    lambda r: r.pop("knowledge"),
])
def test_bad_runs_ignored(g, isolated_record_path, change):
    run = good_run(g)
    assert g.parse_run(dict(run)) is not None
    change(run)
    assert g.parse_run(run) is None
    write(isolated_record_path, {config.RECORD_KEY: 0, config.RECORD_RUN_KEY: run})
    g2 = Game(seed=9)
    assert g2.saved_run is None
    press(g2, pygame.K_RETURN)
    assert g2.student.elapsed == 0            # 새 판으로 시작
    pygame.quit()


@pytest.mark.parametrize("value", [None, [], "run", 3])
def test_non_dict_run_ignored(g, value):
    assert g.parse_run(value) is None


def test_hint_and_stars(g, isolated_record_path):
    set_up_run(g)
    g.student.elapsed = 3725.0
    reach_grade(g.student, 4)
    press(g, pygame.K_ESCAPE)
    g2 = Game(seed=9)
    text = g2.get_resume_hint_text()
    assert text == "Enter를 눌러 이어하기 (4학년, 62분 5초)"
    rect = g2.get_key_hint_rect(text, config.START_HINT_Y)
    panel = pygame.Rect(config.MENU_PANEL_RECT).inflate(-2 * config.PIXEL_SIZE, 0)
    assert panel.contains(rect)
    from button import sprite_size
    sw, sh = sprite_size(config.STAR_SPRITE, config.PIXEL_SIZE)
    for x, y, _ in g2.get_title_stars():
        assert not rect.colliderect((x, y, sw, sh))
    assert len(g2.get_title_stars()) < len(config.TITLE_STARS)
    pygame.quit()


def test_title_without_run_shows_start_hint(g):
    assert g.get_title_stars() == config.TITLE_STARS
