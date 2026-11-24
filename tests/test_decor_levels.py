"""(장식 변화) 업그레이드 레벨마다 무대 장식이 달라지고, 최고 레벨이면 반짝이(시설은 사면 바로)."""

import pygame
import pytest

import config
from button import sprite_size
from game import Game

C = config.SCENE_CELL
MAXLV = {u: config.UPGRADES_BY_ID[u][config.UPGRADE_MAX_LEVEL] for u in config.DECOR_IDS}
PLACES = [config.PLACE_LAWN, config.PLACE_LECTURE, config.PLACE_LIBRARY, config.PLACE_CEREMONY,
          config.PLACE_LAB]


@pytest.fixture(scope="module")
def g():
    """장식 계산·그림용 Game."""
    game = Game(seed=1)
    yield game
    pygame.quit()


def levels_of(**kw):
    """DECOR_IDS 순서의 레벨 튜플."""
    return tuple(kw.get(u, 0) for u in config.DECOR_IDS)


@pytest.mark.parametrize("uid", config.DECOR_IDS)
def test_pieces_grow_every_level(g, uid):
    counts = [len(g.get_decor_pieces(uid, lv)) for lv in range(MAXLV[uid] + 1)]
    assert counts[0] == 0
    assert all(a < b for a, b in zip(counts, counts[1:])), (uid, counts)


@pytest.mark.parametrize("uid", config.DECOR_IDS)
def test_sparkle_only_at_max(g, uid):
    for lv in range(MAXLV[uid] + 1):
        names = [n for n, _, _ in g.get_decor_pieces(uid, lv)]
        assert (config.DECOR_SPARKLE in names) is (lv == MAXLV[uid]), (uid, lv)


@pytest.mark.parametrize("uid", config.DECOR_IDS)
def test_sparkle_at_top_right_inside_box(g, uid):
    pieces = g.get_decor_pieces(uid, MAXLV[uid])
    box = None
    for name, col, row in pieces:
        w, h = sprite_size(config.SCENE_SPRITES[name][0], 1)
        r = pygame.Rect(col, row, w, h)
        box = r if box is None else box.union(r)
    name, col, row = next(p for p in pieces if p[0] == config.DECOR_SPARKLE)
    assert (col + config.DECOR_SPARKLE_SIZE, row) == (box.right, box.top)


@pytest.mark.parametrize("place", PLACES)
@pytest.mark.parametrize("uid", config.DECOR_IDS)
def test_each_level_draws_differently(g, place, uid):
    shots = []
    for lv in range(MAXLV[uid] + 1):
        s = g.make_scenery(place, config.SEASON_SPRING, (), decor_levels=levels_of(**{uid: lv}))
        shots.append(pygame.image.tobytes(s, "RGB"))
    assert len(set(shots)) == len(shots), (place, uid)


@pytest.mark.parametrize("place", PLACES)
@pytest.mark.parametrize("uid", [config.UPGRADE_LIBRARY, config.UPGRADE_CAFE, config.UPGRADE_GYM])
def test_facility_has_sparkle(g, place, uid):
    """시설 건물 오른쪽 위 3 x 3칸에 금색 반짝이 가운데 칸(흰색)이 찍힌다."""
    x, bottom, cell = config.FACILITY_SLOTS[place][uid]
    w, h = sprite_size(config.SCENE_SPRITES[config.FACILITY_SPRITES[uid]][0], cell)
    s = g.make_scenery(place, config.SEASON_SPRING, (uid,))
    sw, _ = sprite_size(config.SCENE_SPRITES[config.DECOR_SPARKLE][0], cell)
    center = (x + w - sw + cell + cell // 2, bottom - h + cell + cell // 2)
    assert tuple(s.get_at(center))[:3] == tuple(config.SCENE_COLORS["white"])[:3]


def test_sparkle_sprite_shape():
    grid = config.SCENE_SPRITES[config.DECOR_SPARKLE][0]
    assert len(grid) == len(grid[0]) == config.DECOR_SPARKLE_SIZE
