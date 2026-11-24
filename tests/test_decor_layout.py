"""(배치 재설계) 장소마다 다른 장식 배치: 꽃·덤불·나무·풍선·흙길·무대와 겹치지 않음, 장식 사이 1칸, 뜻이 맞는 묶음."""

import pygame
import pytest

import config
from button import sprite_size
from game import Game

C = config.SCENE_CELL
PLACES = [config.PLACE_LAWN, config.PLACE_LECTURE, config.PLACE_LIBRARY, config.PLACE_CEREMONY,
          config.PLACE_LAB]
SOFT_PARTS = ("flower", "bush", "tree", "balloon_pink", "balloon_sky")


@pytest.fixture(scope="module")
def g():
    """장식 사각형 계산용 Game."""
    game = Game(seed=1)
    yield game
    pygame.quit()


def max_levels():
    """장식 10종 모두 최고 레벨."""
    return tuple(config.UPGRADES_BY_ID[u][config.UPGRADE_MAX_LEVEL] for u in config.DECOR_IDS)


def part_rect(name, col, row):
    """배경 스프라이트 조각의 무대 안쪽 픽셀 사각형."""
    w, h = sprite_size(config.SCENE_SPRITES[name][0], C)
    return pygame.Rect(col * C, row * C, w, h)


def soft_obstacles(place):
    """장식이 덮으면 안 되는 배경 소품(꽃·덤불·나무·풍선)과 1학년 흙길, 졸업식 무대."""
    out = []
    for part in config.PLACE_FRONT[place] + config.PLACE_BACK[place]:
        if part[0] == config.PART_SPRITE and part[1] in SOFT_PARTS:
            out.append((part[1], part_rect(part[1], part[2], part[3])))
        if part[0] == "rect" and part[1] == "path" and place == config.PLACE_LAWN:
            out.append(("trail", pygame.Rect(part[2] * C, part[3] * C, part[4] * C, part[5] * C)))
    if place == config.PLACE_CEREMONY:
        out.append(("stage", pygame.Rect(29 * C, 37 * C, 66 * C, 8 * C)))
    return out


def near(a, b, cells):
    """두 사각형 사이 거리가 cells칸 이하면 True."""
    return a.inflate(2 * cells * C, 2 * cells * C).colliderect(b)


@pytest.mark.parametrize("place", PLACES)
def test_not_on_flowers_bushes_trees_trail_stage(g, place):
    for uid, r in g.get_decor_rects(place, max_levels()).items():
        for name, o in soft_obstacles(place):
            assert not r.colliderect(o), (place, uid, name)


@pytest.mark.parametrize("place", PLACES)
def test_one_cell_gap_between_decor(g, place):
    items = list(g.get_decor_rects(place, max_levels()).items())
    for i, (a, ra) in enumerate(items):
        for b, rb in items[i + 1:]:
            assert not ra.inflate(2 * C, 2 * C).colliderect(rb), (place, a, b)


def test_every_place_has_its_own_layout():
    slots = [config.DECOR_SLOTS[p] for p in PLACES]
    for i, a in enumerate(slots):
        for b in slots[i + 1:]:
            assert a != b


def test_bottom_band_not_crowded(g):
    """제자 앞 아래 띠(행 72~)에 장식이 몰리지 않는다: 바깥 장소마다 4개 이하."""
    for place in PLACES[:4]:
        rects = g.get_decor_rects(place, max_levels())
        band = [u for u, r in rects.items() if r.top >= 72 * C and 34 * C <= r.left < 90 * C]
        assert len(band) <= 4, (place, band)
    ceremony = g.get_decor_rects(config.PLACE_CEREMONY, max_levels())
    assert len([u for u, r in ceremony.items() if r.top >= 72 * C]) <= 3


def facility(place, uid):
    """시설 건물 사각형."""
    x, bottom, cell = config.FACILITY_SLOTS[place][uid]
    w, h = sprite_size(config.SCENE_SPRITES[config.FACILITY_SPRITES[uid]][0], cell)
    return pygame.Rect(x, bottom - h, w, h)


def test_lawn_picnic_by_left_bench(g):
    rects = g.get_decor_rects(config.PLACE_LAWN, max_levels())
    bench = part_rect("bench", 4, 50)
    assert near(rects[config.UPGRADE_MENU], bench, 2)
    assert near(rects[config.UPGRADE_HEALTH_CARE], rects[config.UPGRADE_MENU], 12)


def test_lawn_exercise_items_together(g):
    rects = g.get_decor_rects(config.PLACE_LAWN, max_levels())
    assert near(rects[config.UPGRADE_SELF_CARE], rects[config.UPGRADE_HEALTH_MAX], 2)


@pytest.mark.parametrize("place", [config.PLACE_LECTURE, config.PLACE_LIBRARY])
def test_snacks_by_cafe(g, place):
    rects = g.get_decor_rects(place, max_levels())
    cafe = facility(place, config.UPGRADE_CAFE)
    assert near(rects[config.UPGRADE_MENU], cafe, 4)


def test_library_reading_corner(g):
    rects = g.get_decor_rects(config.PLACE_LIBRARY, max_levels())
    book = rects[config.UPGRADE_BOOK]
    assert near(book, rects[config.UPGRADE_BED], 2)
    assert book.right <= 34 * C      # 왼쪽 가로등 쪽


def test_ceremony_trophy_by_stage(g):
    rects = g.get_decor_rects(config.PLACE_CEREMONY, max_levels())
    stage = pygame.Rect(29 * C, 37 * C, 66 * C, 8 * C)
    assert near(rects[config.UPGRADE_SCHOLARSHIP], stage, 4)


@pytest.mark.parametrize("place", PLACES[:4])
def test_outdoor_items_stand_on_ground(g, place):
    for uid, r in g.get_decor_rects(place, max_levels()).items():
        assert r.top >= config.GROUND_ROW * C and r.bottom <= 84 * C, (place, uid)
