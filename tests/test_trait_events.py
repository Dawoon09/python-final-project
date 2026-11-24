"""(특성 이벤트) 새 특성 4종과 그것을 주는 선택지형 이벤트 4개, 특성 배지 8개 배치 검수."""

import pygame
import pytest

import config
from conftest import reach_grade
from game import Game
from student import Student

P = config.PIXEL_SIZE
NEW = {
    "morning_class": (1, config.TRAIT_MORNING),
    "study_group": (2, config.TRAIT_STUDY_GROUP),
    "living_alone": (3, config.TRAIT_COOKING),
    "thesis_stress": (4, config.TRAIT_MEDITATION),
}


def event_by_id(event_id):
    """id로 이벤트 표의 항목을 찾는다."""
    return next(e for e in config.ALL_EVENTS if e[config.EVENT_ID] == event_id)


@pytest.fixture
def g():
    """게임 화면 Game (시드 고정)."""
    game = Game(seed=3)
    game.start_new_game()
    yield game
    pygame.quit()


def fresh_student(*traits):
    """업그레이드 없이 특성만 가진 학생 (시험 기간 아님)."""
    s = Student({})
    s.elapsed = 1.0
    for t in traits:
        s.add_trait(t)
    return s


# ----------------------------- 특성 효과 -----------------------------

def test_names():
    assert (config.TRAIT_MORNING, config.TRAIT_STUDY_GROUP, config.TRAIT_COOKING,
            config.TRAIT_MEDITATION) == ("아침형 인간", "스터디 그룹", "자취 요리", "명상")
    assert len(config.TRAIT_BONUSES) == 8


def test_morning_rest_bonus():
    base, s = fresh_student(), fresh_student(config.TRAIT_MORNING)
    for x in (base, s):
        x.health, x.mental = 50, 50
        x.rest()
    assert (s.health - base.health, s.mental - base.mental) == (3, 3)


def test_study_group_knowledge_bonus_and_ratio():
    base, s = fresh_student(), fresh_student(config.TRAIT_STUDY_GROUP)
    for x in (base, s):
        x.study()
    assert (base.knowledge, s.knowledge) == (10, 12)
    s2 = fresh_student(config.TRAIT_STUDY_GROUP)
    s2.study(1.8, 1.8)   # 공부 위주: (10 + 2) x 1.8 = 21.6 -> 22
    assert s2.knowledge == 22


def test_study_group_bonus_not_doubled_in_exam():
    s = fresh_student(config.TRAIT_STUDY_GROUP)
    s.elapsed = 50.0     # 시험 기간
    assert s.is_exam_period()
    s.study()
    assert s.knowledge == 22   # 20 + 2


def test_meditation_mental_cost():
    base, s = fresh_student(), fresh_student(config.TRAIT_MEDITATION)
    for x in (base, s):
        x.study()
    assert (80 - base.mental, 80 - s.mental) == (8, 6)
    s2 = fresh_student(config.TRAIT_MEDITATION)
    s2.study(1.0, 1.8)   # -6 x 1.8 = -10.8 -> -11
    assert 80 - s2.mental == 11


def test_cooking_full_time():
    assert fresh_student().get_full_duration() == 30
    assert fresh_student(config.TRAIT_COOKING).get_full_duration() == 35
    assert fresh_student(config.TRAIT_COOKING, config.TRAIT_FITNESS).get_full_duration() == 45


def test_tip_texts_for_new_traits(g):
    assert g.get_trait_tip_text(config.TRAIT_MORNING) == \
        "아침형 인간: 휴식 체력 +3, 휴식 멘탈 +3 (이번 판 끝까지)"
    assert g.get_trait_tip_text(config.TRAIT_STUDY_GROUP) == "스터디 그룹: 공부 지식 +2 (이번 판 끝까지)"
    assert g.get_trait_tip_text(config.TRAIT_COOKING) == "자취 요리: 학식 든든함 +5초 (이번 판 끝까지)"
    assert g.get_trait_tip_text(config.TRAIT_MEDITATION) == "명상: 공부 멘탈 소모 -2 (이번 판 끝까지)"


# ----------------------------- 이벤트 -----------------------------

@pytest.mark.parametrize("event_id", list(NEW))
def test_new_event_shape(event_id):
    grade, trait = NEW[event_id]
    e = event_by_id(event_id)
    assert e[config.EVENT_KIND] == config.EVENT_KIND_CHOICE
    assert e[config.EVENT_GRADES] == [grade] and e[config.EVENT_REQUIRES] is None
    first, second = e[config.EVENT_OPTIONS]
    assert first[config.OPTION_TRAIT] == trait and second[config.OPTION_TRAIT] is None
    assert first[config.OPTION_LOOK] is None and first[config.OPTION_FLAG] is None


@pytest.mark.parametrize("event_id", list(NEW))
def test_choose_first_gives_trait(g, event_id):
    grade, trait = NEW[event_id]
    reach_grade(g.student, grade)
    g.start_event(event_by_id(event_id))
    g.dialog_time = config.EVENT_INPUT_DELAY
    assert g.choose_option(config.CHOICE_FIRST)
    assert trait in g.student.traits
    assert g.state == config.STATE_PLAYING


@pytest.mark.parametrize("event_id", list(NEW))
def test_choose_second_gives_no_trait(g, event_id):
    grade, trait = NEW[event_id]
    reach_grade(g.student, grade)
    g.start_event(event_by_id(event_id))
    g.dialog_time = config.EVENT_INPUT_DELAY
    assert g.choose_option(config.CHOICE_SECOND)
    assert trait not in g.student.traits


@pytest.mark.parametrize("event_id", list(NEW))
def test_new_event_not_in_grad_school(g, event_id):
    g.student.knowledge = config.GRADUATION_KNOWLEDGE
    g.student.promote()
    g.student.enter_grad_school()
    assert g.student.is_in_grad_school()
    choices, _ = g.get_event_candidates()
    assert choices == []


# ----------------------------- 배지 8개 배치 -----------------------------

def test_eight_badges_fit_in_panel(g):
    for t in config.TRAIT_BONUSES:
        g.student.add_trait(t)
    panel_inner = pygame.Rect(config.STATUS_PANEL_X, config.PANEL_Y, config.STATUS_PANEL_WIDTH,
                              config.PANEL_HEIGHT).inflate(-2 * P, -2 * P)
    rects = [g.student.get_badge_rect(i, config.TRAIT_BADGE_Y) for i in range(8)]
    for i, r in enumerate(rects):
        with_drop = r.union(r.move(0, P))
        assert panel_inner.contains(with_drop), r
        assert r.top > config.MENTAL_BAR_Y + config.BAR_HEIGHT + P   # 멘탈 막대 아래
        for other in rects[i + 1:]:
            assert not with_drop.colliderect(other.union(other.move(0, P)))


def test_badge_names_fit(g):
    for t in config.TRAIT_BONUSES:
        g.student.add_trait(t)
    for i, t in enumerate(g.student.traits):
        r = g.student.get_badge_rect(i, config.TRAIT_BADGE_Y)
        w, _ = g.small_font.size(t)
        assert w <= r.width - 4 * P, t


def test_status_badges_still_above_health_label(g):
    rects = [g.student.get_badge_rect(i, config.STATUS_BADGE_Y) for i in range(4)]
    assert max(r.bottom for r in rects) + P <= config.HEALTH_LABEL_Y


def test_eight_badges_drawn_and_hoverable(g):
    for t in config.TRAIT_BONUSES:
        g.student.add_trait(t)
    g.draw()
    last = g.student.get_badge_rect(7, config.TRAIT_BADGE_Y)
    g.mouse_pos = last.center
    assert g.get_hovered_trait() == (7, config.TRAIT_MEDITATION)
    rect = g.draw_trait_tooltip()
    assert rect.bottom + P <= config.TOOLTIP_BOTTOM_MAX
