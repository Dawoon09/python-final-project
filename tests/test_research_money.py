"""(연구비 요소) 업그레이드 '연구 과제 수주'(버는 연구비 +10%/Lv)와 자동형 '공모전에 입상했다'(+40 x 학년)."""

import pygame
import pytest

import config
from conftest import reach_grade
from game import Game

R = config.UPGRADE_RESEARCH
CONTEST = next(e for e in config.AUTO_EVENTS if e[config.EVENT_ID] == "contest_prize")


@pytest.fixture
def g():
    """게임 화면 Game."""
    game = Game(seed=11)
    game.start_new_game()
    yield game
    pygame.quit()


def test_upgrade_row():
    u = config.UPGRADES_BY_ID[R]
    assert (u[config.UPGRADE_NAME], u[config.UPGRADE_CATEGORY], u[config.UPGRADE_MAX_LEVEL],
            u[config.UPGRADE_BASE_COST], u[config.UPGRADE_PER_LEVEL]) == \
        ("연구 과제 수주", "연구비", 5, 500, 0.1)
    assert config.UPGRADE_IDS[-1] == R and len(config.UPGRADE_IDS) == 14


@pytest.mark.parametrize("level, ratio", [(0, 1.0), (1, 1.1), (3, 1.3), (5, 1.5)])
def test_ratio(g, level, ratio):
    g.upgrades[R] = level
    assert g.get_research_money_ratio() == pytest.approx(ratio)


@pytest.mark.parametrize("level, gain, expected", [(0, 10, 10), (1, 10, 11), (3, 10, 13),
                                                  (5, 10, 15), (5, 7, 10), (2, 18, 21)])
def test_knowledge_money(g, level, gain, expected):
    g.upgrades[R] = level
    g.student.health = g.student.mental = 50     # 컨디션 배수 1
    before = g.student.knowledge
    g.student.knowledge += gain
    assert g.earn_knowledge_money(before) == expected


def test_stacks_with_fame_and_grad(g):
    g.upgrades[R] = 5
    g.fame = 10
    g.student.health = g.student.mental = 50
    g.student.knowledge = 0
    g.student.knowledge = 100
    assert g.earn_knowledge_money(0) == 300    # 100 x 2.0 x 1.5


def test_not_on_graduation_bonus_or_scholarship(g):
    g.upgrades[R] = 5
    g.upgrades[config.UPGRADE_SCHOLARSHIP] = 1
    money = g.money
    g.start_event(config.SCHOLARSHIP_EVENT)
    assert g.money == money + 30


def test_upgrade_effect_text_and_tooltip(g):
    assert g.get_upgrade_effect_text(R, 3) == "버는 연구비 +30%"
    rows = [t for t, _ in g.get_upgrade_tooltip_rows(R)]
    assert rows[0].startswith("연구 과제 수주") and "무대: 연구 서류가 쌓여요" in rows


def test_buy_and_save(g, isolated_record_path):
    import json
    g.money = 500
    assert g.buy_upgrade(R)
    with open(isolated_record_path, encoding=config.RECORD_ENCODING) as f:
        assert json.load(f)[config.RECORD_UPGRADES_KEY][R] == 1


def test_panel_14_rows_fit(g):
    panel = pygame.Rect(config.UPGRADE_PANEL_RECT).inflate(-2 * config.PIXEL_SIZE,
                                                           -2 * config.PIXEL_SIZE)
    last = g.get_upgrade_row_rect(13)
    assert panel.contains(last)
    footer_top = config.UPGRADE_FOOTER_Y - g.small_font.get_height() // 2
    assert last.bottom <= footer_top + 1
    assert g.get_upgrade_row_rect(0).top > config.UPGRADE_GAUGE_Y + config.UPGRADE_GAUGE_BAR_HEIGHT


# ----------------------------- 공모전 -----------------------------

def test_contest_event_shape():
    assert CONTEST[config.EVENT_KIND] == config.EVENT_KIND_AUTO
    assert CONTEST[config.EVENT_TITLE] == "공모전에 입상했다"
    assert CONTEST[config.EVENT_EFFECTS] == {}
    assert CONTEST[config.EVENT_MONEY_PER_GRADE] == config.CONTEST_MONEY_PER_GRADE == 40
    assert CONTEST in config.AUTO_EVENTS


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
def test_contest_money_by_grade(g, grade):
    reach_grade(g.student, grade)
    g.fame = 10
    g.upgrades[R] = 5          # 배수는 붙지 않는다
    money = g.money
    g.start_event(CONTEST)
    assert g.money == money + 40 * grade
    assert g.notice["good"] is True
    assert g.event_log[-1]["result"] == "연구비 +{}".format(40 * grade)


def test_contest_in_grad_school_uses_4(g):
    g.student.knowledge = config.GRADUATION_KNOWLEDGE
    g.check_promotion()
    g.check_ending()
    g.enter_grad_school()
    money = g.money
    g.start_event(CONTEST)
    assert g.money == money + 160


def test_contest_always_candidate(g):
    _, autos = g.get_event_candidates()
    assert CONTEST in autos


def test_long_money_popup_stays_in_stage(g):
    reach_grade(g.student, 4)
    g.start_event(CONTEST)
    stage = g.get_stage_inner()
    for p in g.popups:
        w = g.popup_font.size(p["text"])[0]
        assert p["x"] - w // 2 >= stage.left + config.PIXEL_SIZE


def test_research_decor_every_level(g):
    counts = [len(g.get_decor_pieces(R, lv)) for lv in range(6)]
    assert counts == [0, 1, 2, 3, 4, 5]
