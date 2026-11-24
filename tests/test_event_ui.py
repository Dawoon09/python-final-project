"""검수 단위 D: 랜덤 이벤트 화면 (jeja-spec 14절 "화면", 기획서 9절).

이 파일에는 conftest 의 no_events 픽스처가 적용되지 않는다. 다만 행동 직후 무작위
이벤트가 끼어들면 화면 검사가 흔들리므로, 필요한 테스트는 EVENT_MAX_PER_GRADE=0 으로
"자동 판정"만 끄고 start_event 로 이벤트를 직접 띄운다(start_event 는 최대값을 보지 않는다).

- 대화창: 위치·글자(제목/상황/선택/미리보기)·넘침·색·호버·등장 슬라이드
- 입력 대기 EVENT_INPUT_DELAY(0.3초)
- 자동형 알림: 좋은/나쁜 일 색, 2초, 슬라이드, 무대 안쪽, 팝업·파티클과 비겹침
- 이벤트 팝업 열(EVENT_POPUP_X): 순서, 무대 안쪽, 행동 팝업·파티클·알림과 비겹침
- 외형 5종: 얻었을 때만, 학년 비례, lift, 레이어, 서로·얼굴 부품 비가림, 무대 안쪽
- 특성 배지, 멈춤 점무늬, 정적 검사(알파 금지·docstring)
"""

import ast
import os
import pathlib

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
import game as game_module  # noqa: E402
from button import sprite_size  # noqa: E402
from conftest import press, reach_grade  # noqa: E402
from game import Game  # noqa: E402
from student import Student  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = config.PIXEL_SIZE
CX, CY = config.STUDENT_CENTER_X, config.STUDENT_CENTER_Y
FRAME = 1 / 60
H, M, K = config.GAUGE_HEALTH, config.GAUGE_MENTAL, config.GAUGE_KNOWLEDGE
FEED, REST, STUDY = config.ACTION_FEED, config.ACTION_REST, config.ACTION_STUDY
GRADE_STARTS = [0.0, 60.0, 120.0, 180.0]   # (L단위) 이제는 n번째 60초 주기의 시작 시각


def grade_of_old_time(elapsed):
    """(L단위) 예전 "elapsed초 = (elapsed // 60 + 1)학년" 규칙으로 학년을 구한다(4학년까지)."""
    return min(config.MAX_GRADE, int(elapsed // config.CYCLE_SECONDS) + config.FIRST_GRADE)
STAGE_INNER = pygame.Rect(config.STAGE_X, config.PANEL_Y, config.STAGE_WIDTH,
                          config.PANEL_HEIGHT).inflate(-2 * P, -2 * P)
STATUS_INNER = pygame.Rect(config.STATUS_PANEL_X, config.PANEL_Y, config.STATUS_PANEL_WIDTH,
                           config.PANEL_HEIGHT).inflate(-2 * P, -2 * P)
DIALOG = pygame.Rect(config.EVENT_DIALOG_RECT)
DIALOG_WITH_DROP = DIALOG.union(DIALOG.move(0, P))
DIALOG_INNER = DIALOG.inflate(-2 * P, -2 * P)
GAUGE_ORDER = [H, M, K]
LABEL_ORDER = [label for _, label in config.POPUP_GAUGES]


# ======================= 도우미 =======================

@pytest.fixture
def make_game(monkeypatch):
    """seed 고정 Game 을 게임 진행 중으로 만든다. 자동 이벤트 판정은 끈다(start_event 로 직접 띄움)."""
    monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 0)

    def factory(elapsed=0.0, seed=0):
        """(L단위) 경과 시간(주기·시험 기간)은 elapsed, 학년은 예전 시간 규칙의 학년을 지식으로 맞춘다."""
        g = Game(seed=seed)
        press(g, pygame.K_RETURN)
        assert g.state == config.STATE_PLAYING
        g.student.elapsed = elapsed
        reach_grade(g.student, grade_of_old_time(elapsed))
        return g

    yield factory
    pygame.quit()


@pytest.fixture
def surface():
    pygame.init()
    s = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    yield s
    pygame.quit()


def event_by_id(event_id):
    for event in config.ALL_EVENTS:
        if event[config.EVENT_ID] == event_id:
            return event
    raise KeyError(event_id)


def click(g, pos):
    g.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=pygame.BUTTON_LEFT, pos=pos))


def gauges(g):
    s = g.student
    return (s.health, s.mental, s.knowledge)


def frozen_state(g):
    s = g.student
    return (s.elapsed, s.decay_timer, s.health, s.mental, s.knowledge, g.auto_timer,
            s.get_grade())


def color(surf, x, y):
    return tuple(surf.get_at((x, y)))[:3]


class RecFont:
    """render 결과 Surface 를 (글자, 색, 글꼴 이름)으로 기억하는 폰트 래퍼."""

    def __init__(self, font, name, book):
        self.font = font
        self.name = name
        self.book = book

    def render(self, text, antialias, color=config.COLOR_TEXT, *args):
        surf = self.font.render(text, antialias, color, *args)
        self.book[id(surf)] = (text, tuple(color)[:3], self.name, surf)
        return surf

    def size(self, text):
        return self.font.size(text)

    def get_linesize(self):
        return self.font.get_linesize()


class RecSurface(pygame.Surface):
    """blit 된 글자 Surface 의 자리(글자 픽셀 사각형)를 기록하는 화면."""

    def __init__(self, size, book):
        super().__init__(size)
        self.book = book
        self.texts = []
        self.tag = None

    def blit(self, source, dest, *args, **kwargs):
        info = self.book.get(id(source))
        if info is not None:
            topleft = pygame.Rect(dest).topleft if isinstance(dest, pygame.Rect) else dest
            glyph = source.get_bounding_rect().move(topleft)
            self.texts.append({"text": info[0], "color": info[1], "font": info[2],
                               "glyph": glyph, "tag": self.tag})
        return super().blit(source, dest, *args, **kwargs)


def record_draw(g, monkeypatch):
    """g 의 화면·글꼴을 기록용으로 바꾸고 draw 한 번. 대화창/알림 안에서 그린 글자에 tag 를 단다."""
    book = {}
    screen = RecSurface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), book)
    g.screen = screen
    g.font = RecFont(g.font, "font", book)
    g.event_font = RecFont(g.event_font, "event", book)
    g.small_font = RecFont(g.small_font, "small", book)
    g.notice_font = RecFont(g.notice_font, "notice", book)   # E단위: 알림 전용 16px 글꼴
    for method, tag in (("draw_event_dialog", "dialog"), ("draw_event_notice", "notice")):
        real = getattr(g, method)

        def tagged(*args, _real=real, _tag=tag, **kwargs):
            screen.tag = _tag
            try:
                return _real(*args, **kwargs)
            finally:
                screen.tag = None
        monkeypatch.setattr(g, method, tagged)
    g.draw()
    return screen.texts


def spy_boxes(monkeypatch):
    """game 모듈의 draw_pixel_box 호출 rect 를 기록한다."""
    calls = []
    real = game_module.draw_pixel_box

    def spy(screen, rect, *args, **kwargs):
        calls.append(pygame.Rect(rect))
        return real(screen, rect, *args, **kwargs)
    monkeypatch.setattr(game_module, "draw_pixel_box", spy)
    return calls


def open_dialog(g, event, ready=True):
    g.start_event(event)
    assert g.state == config.STATE_EVENT and g.current_event is event
    if ready:
        g.update(config.EVENT_INPUT_DELAY)
        assert g.is_dialog_ready()


def expected_preview(option):
    labels = dict(config.POPUP_GAUGES)
    parts = []
    for key, amount in option[config.OPTION_EFFECTS].items():
        c = config.COLOR_PREVIEW_UP if amount > 0 else config.COLOR_PREVIEW_DOWN
        parts.append((f"{labels[key]} {amount:+d}", tuple(c)))
    if option[config.OPTION_TRAIT] is not None:
        parts.append((f"특성: {option[config.OPTION_TRAIT]}", tuple(config.COLOR_PREVIEW_OTHER)))
    if option[config.OPTION_LOOK] is not None:
        parts.append((f"외형: {config.LOOK_NAMES[option[config.OPTION_LOOK]]}",
                      tuple(config.COLOR_PREVIEW_OTHER)))
    if not parts:
        parts.append(("변화 없음", tuple(config.COLOR_PREVIEW_OTHER)))
    return parts


def popup_rect(g, popup, age=None):
    """draw_popup 과 같은 계산: 팝업 글자(남색 그림자 포함)의 글자 픽셀 사각형."""
    if age is None:
        age = popup["age"]
    surf = g.popup_font.render(popup["text"], False, (0, 0, 0))
    glyph = surf.get_bounding_rect()
    rect = surf.get_rect()
    rect.center = (popup.get("x", CX), round(popup["y"] - config.POPUP_RISE_SPEED * age))
    gr = glyph.move(rect.topleft)
    return gr.unionall([gr.move(dx, dy) for dx, dy in config.POPUP_OUTLINE_OFFSETS])


def particle_rect(g, p):
    """draw_particle 과 같은 계산: 파티클 스프라이트 전체 사각형(투명 칸 포함, 보수적)."""
    age = p["age"]
    cell = P
    if age >= p["life"] * config.PARTICLE_SHRINK_RATIO:
        cell = P // 2
    w, h = sprite_size(p["sprite"], cell)
    left = g.snap_to_pixel(p["x"] + p["vx"] * age - w / 2)
    top = g.snap_to_pixel(p["y"] + p["vy"] * age - h / 2)
    return pygame.Rect(left, top, w, h)


def notice_lines(font, text, max_width=None):
    """(E단위) 알림 글자를 띄어쓰기 자리에서 max_width(EVENT_NOTICE_TEXT_MAX_WIDTH) 이하 줄들로 나눈다.

    게임의 wrap_text 를 쓰지 않고 검수팀이 따로 계산한 기대값(줄 수 제한 없음: 2줄 초과 여부도 잡는다).
    """
    if max_width is None:
        max_width = config.EVENT_NOTICE_TEXT_MAX_WIDTH
    lines, current = [], ""
    for word in text.split(" "):
        cand = word if not current else current + " " + word
        if current and font.size(cand)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = cand
    lines.append(current)
    return lines


def notice_rect(g):
    """draw_event_notice 와 같은 계산: 알림 상자(아래 그림자 1칸 포함) 사각형. 없으면 None.

    (E단위) 글자는 notice_font(16px)로, 길면 2줄로 나눠 가장 긴 줄 폭이 상자 폭을 정한다.
    """
    if g.notice is None:
        return None
    icon = config.NOTICE_GOOD_ICON if g.notice["good"] else config.NOTICE_BAD_ICON
    icon_w, _ = sprite_size(icon, P)
    font = getattr(g.notice_font, "font", g.notice_font)
    text_w = max(font.size(line)[0] for line in notice_lines(font, g.notice["text"]))
    width = (config.BOX_INSET + config.EVENT_NOTICE_PAD + icon_w + config.EVENT_NOTICE_ICON_GAP
             + text_w + config.EVENT_NOTICE_PAD_RIGHT)
    age = config.EVENT_NOTICE_TIME - g.notice["timer"]
    slide = g.get_slide_offset(age, config.EVENT_NOTICE_SLIDE_TIME,
                               config.EVENT_NOTICE_SLIDE_DISTANCE)
    box = pygame.Rect(config.EVENT_NOTICE_X, config.EVENT_NOTICE_Y - slide, width,
                      config.EVENT_NOTICE_HEIGHT)
    return box.union(box.move(0, P))


def is_event_popup(p):
    return p.get("x", CX) == config.EVENT_POPUP_X


def check_frames(g, max_time, tag):
    """max_time 초 동안 프레임마다 행동 팝업·이벤트 팝업·파티클·알림 상자가 서로 겹치지 않고
    무대 안쪽인지 확인한다. (깜빡여 숨은 프레임도 자리로는 검사: 더 엄격)"""
    t = 0.0
    frames = 0
    while t < max_time + 1e-9:
        pops = [(p, popup_rect(g, p)) for p in g.popups]
        parts = [particle_rect(g, p) for p in g.particles]
        note = notice_rect(g)
        for p, r in pops:
            assert STAGE_INNER.contains(r), (tag, frames, p["text"], r)
            for pr in parts:
                assert not r.colliderect(pr), (tag, frames, p["text"], r, pr)
            if note is not None:
                assert not r.colliderect(note), (tag, frames, p["text"], r, note)
        for i, (p, r) in enumerate(pops):
            for q, r2 in pops[i + 1:]:
                assert not r.colliderect(r2), (tag, frames, p["text"], q["text"], r, r2)
        if note is not None:
            # 슬라이드 중 위로 올라간 부분은 무대 안쪽으로 잘라 그리므로, 제자리(최종) 기준으로 무대 안쪽
            assert note.bottom <= STAGE_INNER.bottom and note.right <= STAGE_INNER.right, (tag, note)
            for pr in parts:
                assert not note.colliderect(pr), (tag, frames, note, pr)
        g.update(FRAME)
        t += FRAME
        frames += 1
    return frames


# ======================= 0. 상수 =======================

def test_d_unit_constants():
    assert config.EVENT_INPUT_DELAY == 0.3
    assert config.EVENT_NOTICE_TIME == 2.0
    assert config.EVENT_COUNT_START == 0
    assert config.TRAIT_BONUS_START == 0
    assert config.EVENT_DIALOG_SLIDE_TIME == 0.15
    assert config.EVENT_NOTICE_SLIDE_TIME == 0.15
    assert config.EVENT_DIALOG_SLIDE_TIME < config.EVENT_INPUT_DELAY
    assert tuple(config.EVENT_DIALOG_RECT) == (300, 132, 472, 264)
    # 새 제자: (L단위) 주기별 이벤트 수는 빈 사전(없는 주기 0), 특성 보정 0
    s = Student()
    assert s.event_counts == {} and s.get_cycle_event_count() == 0
    # (M단위) BONUS_FEED_HEALTH -> BONUS_FULL_TIME (체력 단련: 든든함 +10초)
    for bonus in (config.BONUS_FULL_TIME, config.BONUS_REST_MENTAL,
                  config.BONUS_REST_HEALTH, config.BONUS_STUDY_HEALTH):
        assert s.get_trait_bonus(bonus) == 0


# ======================= 1. 입력 대기 (EVENT_INPUT_DELAY) =======================

def test_input_ignored_right_after_dialog_opens(make_game):
    """뜬 직후: 키 1·2, 선택 버튼 클릭, choose_option 직접 호출 모두 무시."""
    g = make_game(5.0)
    open_dialog(g, event_by_id("mt_invite"), ready=False)
    assert not g.is_dialog_ready()
    snap = gauges(g)
    press(g, pygame.K_1)
    press(g, pygame.K_2)
    for b in g.choice_buttons:
        click(g, b.rect.center)
    assert g.choose_option(0) is False
    assert g.choose_option(1) is False
    assert g.state == config.STATE_EVENT and g.current_event is event_by_id("mt_invite")
    assert gauges(g) == snap and g.student.flags == set()


def test_action_key_mash_does_not_choose(make_game, monkeypatch):
    """행동 직후 이벤트가 뜬 바로 다음 프레임부터 키 1·2 를 연타해도 선택으로 들어가지 않는다.

    (G단위) 키 1 은 이제 방침 키라서 행동은 do_action 으로 시킨다. 방침 키를 연타하던 중
    자동 행동으로 대화창이 떠도 같은 키가 선택으로 들어가면 안 된다는 뜻은 그대로다.
    """
    g = make_game(5.0)
    monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 5)
    monkeypatch.setattr(config, "EVENT_CHANCE", 1.0)
    monkeypatch.setattr(g, "pick_event", lambda: event_by_id("mt_invite"))
    press(g, pygame.K_1)                     # 방침 키(공부 위주)
    assert g.do_action(config.ACTION_FEED)   # 행동 직후 대화창
    assert g.state == config.STATE_EVENT
    policy = g.policy
    snap = gauges(g)
    for _ in range(int(config.EVENT_INPUT_DELAY / FRAME) - 1):
        g.update(FRAME)
        press(g, pygame.K_1)
        press(g, pygame.K_2)
    assert g.state == config.STATE_EVENT and gauges(g) == snap
    assert g.policy == policy                # 대화창 중 키 1·2 는 방침도 바꾸지 않는다


@pytest.mark.parametrize("how", ["key1", "key2", "click0", "click1", "call0", "call1"])
def test_input_boundary(make_game, how):
    """0.29초까지는 무시, 0.3초가 되면 허용."""
    g = make_game(5.0)
    open_dialog(g, event_by_id("mt_invite"), ready=False)
    index = int(how[-1]) - (1 if how.startswith("key") else 0)

    def attempt():
        if how.startswith("key"):
            press(g, pygame.K_1 if index == 0 else pygame.K_2)
        elif how.startswith("click"):
            click(g, g.choice_buttons[index].rect.center)
        else:
            g.choose_option(index)

    g.update(config.EVENT_INPUT_DELAY - 0.01)
    attempt()
    assert g.state == config.STATE_EVENT
    g.update(0.01)
    assert g.is_dialog_ready()
    attempt()
    assert g.state == config.STATE_PLAYING and g.current_event is None


def test_input_allowed_with_frame_steps(make_game):
    """1/60초 프레임으로 흘러도 0.3초 근처(소수 오차 허용)에서 정확히 풀린다."""
    g = make_game(5.0)
    open_dialog(g, event_by_id("mt_invite"), ready=False)
    frames = 0
    while not g.is_dialog_ready():
        g.update(FRAME)
        frames += 1
        assert frames < 100
    assert abs(frames * FRAME - config.EVENT_INPUT_DELAY) < FRAME + 1e-9
    assert frames * FRAME >= config.EVENT_INPUT_DELAY - 1e-6


def test_game_time_frozen_during_input_delay(make_game):
    g = make_game(30.5)
    g.do_action(STUDY)            # 쿨타임 1초 시작
    open_dialog(g, event_by_id("mt_invite"), ready=False)
    snap = frozen_state(g)
    for _ in range(10):
        g.update(FRAME)
    assert not g.is_dialog_ready()
    assert frozen_state(g) == snap
    g.update(config.EVENT_INPUT_DELAY)
    assert frozen_state(g) == snap
    assert g.is_dialog_ready()


@pytest.mark.parametrize("kind", ["esc", "quit"])
def test_esc_quit_work_during_input_delay(make_game, kind):
    g = make_game(5.0)
    open_dialog(g, event_by_id("mt_invite"), ready=False)
    assert not g.is_dialog_ready()
    if kind == "esc":
        press(g, pygame.K_ESCAPE)
    else:
        g.handle_event(pygame.event.Event(pygame.QUIT))
    assert g.running is False


def test_input_delay_restarts_for_each_dialog(make_game):
    """두 번째 대화창이 떠도 대기 시간이 처음부터 다시 적용된다."""
    g = make_game(5.0)
    open_dialog(g, event_by_id("mt_invite"))
    press(g, pygame.K_2)
    assert g.state == config.STATE_PLAYING
    g.update(1.0)
    open_dialog(g, event_by_id("club_fair"), ready=False)
    assert g.dialog_time == 0.0 and not g.is_dialog_ready()
    press(g, pygame.K_1)
    assert g.state == config.STATE_EVENT and g.student.looks == []
    g.update(config.EVENT_INPUT_DELAY)
    press(g, pygame.K_1)
    assert g.student.looks == [config.LOOK_GUITAR]


def test_dialog_clock_only_runs_in_dialog(make_game):
    g = make_game(5.0)
    g.update(1.0)
    assert g.dialog_time == 0.0
    open_dialog(g, event_by_id("mt_invite"), ready=False)
    g.update(0.1)
    assert g.dialog_time == pytest.approx(0.1)


# ======================= 2. 대화창 =======================

def test_dialog_box_inside_stage_and_screen():
    box = DIALOG_WITH_DROP
    assert STAGE_INNER.contains(box)
    assert box.centerx == CX
    band = pygame.Rect(config.EVENT_TITLE_BAND_RECT)
    assert DIALOG_INNER.contains(band)
    for y in config.CHOICE_BUTTON_YS:
        b = pygame.Rect(config.CHOICE_BUTTON_X, y, config.CHOICE_BUTTON_WIDTH,
                        config.CHOICE_BUTTON_HEIGHT)
        assert DIALOG_INNER.contains(b.union(b.move(0, P)))
        assert b.centerx == CX
    # 등장 중(가장 위)에도 화면 안
    top = DIALOG.move(0, -config.EVENT_DIALOG_SLIDE_DISTANCE)
    assert pygame.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT).contains(top)


def test_choice_and_action_areas_do_not_overlap(make_game):
    g = make_game()
    for b in g.buttons.values():
        action_area = b.rect.union(b.rect.move(0, P)).union(b.rect.move(0, config.BUTTON_PRESS_OFFSET))
        assert not DIALOG_WITH_DROP.colliderect(action_area)
        for cb in g.choice_buttons:
            assert not cb.rect.union(cb.rect.move(0, P)).colliderect(action_area)
    a, b = (cb.rect.union(cb.rect.move(0, P)) for cb in g.choice_buttons)
    assert not a.colliderect(b)


CHOICE_IDS = [e[config.EVENT_ID] for e in config.CHOICE_EVENTS]


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
@pytest.mark.parametrize("event_id", CHOICE_IDS)
def test_dialog_texts_match_config_and_fit(make_game, monkeypatch, event_id, grade):
    """선택지형 10개 x 1~4학년(3학년부터 안경): 제목·상황·선택·미리보기 글자가 config 와 같고
    각자 자기 칸 안에 들어간다(서로·상자 밖으로 넘치지 않음)."""
    g = make_game(GRADE_STARTS[grade - 1] + 5.0)
    assert g.student.has_glasses() == (grade >= 3)
    event = event_by_id(event_id)
    open_dialog(g, event)
    texts = [t for t in record_draw(g, monkeypatch) if t["tag"] == "dialog"]

    # 제목: 기본 글꼴, 띠 안쪽, 양끝 별과 겹치지 않음
    band = pygame.Rect(config.EVENT_TITLE_BAND_RECT)
    band_inner = band.inflate(-2 * P, -2 * P)
    titles = [t for t in texts if t["font"] == "font"]
    assert [t["text"] for t in titles] == [event[config.EVENT_TITLE]]
    title = titles[0]["glyph"]
    assert band_inner.contains(title)
    star_w, star_h = sprite_size(config.STAR_SPRITE, P)
    for sx in (band.left + config.EVENT_TITLE_ICON_MARGIN,
               band.right - config.EVENT_TITLE_ICON_MARGIN - star_w):
        assert not title.colliderect(pygame.Rect(sx, band_inner.centery - star_h // 2,
                                                 star_w, star_h))

    # 상황: 2줄 이하, 이어 붙이면 원문, 각 줄 폭 <= 416, 띠 아래·첫 버튼 위
    buttons = [cb.rect for cb in g.choice_buttons]
    lines = [t for t in texts if t["font"] == "event" and not t["text"].startswith("[")]
    assert 1 <= len(lines) <= config.EVENT_TEXT_MAX_LINES
    assert " ".join(t["text"] for t in lines) == event[config.EVENT_TEXT]
    for t in lines:
        assert t["glyph"].width <= config.EVENT_TEXT_MAX_WIDTH
        assert DIALOG_INNER.contains(t["glyph"])
        assert t["glyph"].top >= band.bottom and t["glyph"].bottom <= buttons[0].top
        assert abs(t["glyph"].centerx - CX) <= 2

    # 선택 버튼 글자: "[1] …", "[2] …" 가 각 버튼 안쪽에
    options = event[config.EVENT_OPTIONS]
    choices = [t for t in texts if t["font"] == "event" and t["text"].startswith("[")]
    assert [t["text"] for t in choices] == [f"[{i + 1}] {o[config.OPTION_TEXT]}"
                                            for i, o in enumerate(options)]
    for t, rect in zip(choices, buttons):
        assert rect.inflate(-2 * P, -2 * P).contains(t["glyph"])

    # 미리보기: 버튼 아래 한 줄, 항목·색이 config 와 같고 상자 안·다음 버튼 위
    small = [t for t in texts if t["font"] == "small"]
    limits = [buttons[1].top, DIALOG_INNER.bottom]
    for i, option in enumerate(options):
        row = [t for t in small if buttons[i].bottom + P <= t["glyph"].top < limits[i]]
        items = [(t["text"], t["color"]) for t in row if t["text"] != config.PREVIEW_SEPARATOR]
        assert items == expected_preview(option), (event_id, i)
        seps = [t for t in row if t["text"] == config.PREVIEW_SEPARATOR]
        assert len(seps) == len(items) - 1
        for t in row:
            assert DIALOG_INNER.contains(t["glyph"]), (t["text"], t["glyph"])
            assert t["glyph"].bottom <= limits[i]
        whole = row[0]["glyph"].unionall([t["glyph"] for t in row])
        assert abs(whole.centerx - CX) <= 4
        # 항목끼리 겹치지 않음
        rects = [t["glyph"] for t in row]
        for a in range(len(rects)):
            for b in range(a + 1, len(rects)):
                assert not rects[a].colliderect(rects[b])
    assert len(small) == sum(2 * len(expected_preview(o)) - 1 for o in options)


def test_dialog_pixels_stay_inside_box(make_game, monkeypatch):
    """대화창이 바꾸는 픽셀은 대화창 상자(아래 그림자 포함) 안뿐이다(글자 넘침 없음)."""
    for event in config.CHOICE_EVENTS:
        g = make_game(185.0)
        open_dialog(g, event)
        g.draw()
        with_dialog = g.screen.copy()
        monkeypatch.setattr(g, "draw_event_dialog", lambda: None)
        g.draw()
        without = g.screen.copy()
        for surf in (with_dialog, without):
            surf.fill((1, 2, 3), DIALOG_WITH_DROP)
        assert pygame.image.tobytes(with_dialog, "RGB") == pygame.image.tobytes(without, "RGB"), \
            event[config.EVENT_ID]
        monkeypatch.undo()
        monkeypatch.setattr(config, "EVENT_MAX_PER_GRADE", 0)


def test_preview_sign_and_color_rules():
    """증가는 '+' 초록, 감소는 '-' 빨강. 특성·외형은 이름으로, 연계 플래그는 숨김."""
    up, down = config.COLOR_PREVIEW_UP, config.COLOR_PREVIEW_DOWN
    assert up[1] > up[0] and up[1] > up[2]          # 초록 계열
    assert down[0] > down[1] and down[0] > down[2]  # 빨강 계열
    g = Game(seed=0)
    for event in config.CHOICE_EVENTS:
        for option in event[config.EVENT_OPTIONS]:
            parts = g.get_option_preview(option)
            assert [(t, tuple(c)) for t, c in parts] == expected_preview(option)
            for text, c in parts:
                if text.endswith(tuple("0123456789")):
                    sign = text.split()[-1][0]
                    assert sign in "+-"
                    assert tuple(c) == tuple(up if sign == "+" else down)
            flag = option[config.OPTION_FLAG]
            if flag is not None and flag != option[config.OPTION_TRAIT]:
                # ("연애 중"은 특성 이름과 플래그 이름이 같아서 특성 항목으로 보인다)
                assert all(flag not in t for t, _ in parts)
    pygame.quit()


def test_preview_traits_and_looks_shown():
    g = Game(seed=0)
    band, gym = event_by_id("club_fair")[config.EVENT_OPTIONS]
    assert [t for t, _ in g.get_option_preview(band)] == ["특성: 음악 힐링", "외형: 기타"]
    assert [t for t, _ in g.get_option_preview(gym)] == ["특성: 체력 단련", "외형: 헬스 머리띠"]
    coffee = event_by_id("all_nighter")[config.EVENT_OPTIONS][0]
    assert [t for t, _ in g.get_option_preview(coffee)] == ["지식 +10", "특성: 카페인", "외형: 커피잔"]
    stage = event_by_id("festival_stage")[config.EVENT_OPTIONS][0]
    assert [t for t, _ in g.get_option_preview(stage)] == ["멘탈 +25", "체력 -10", "외형: 선글라스"]
    assert set(config.LOOK_NAMES) == set(config.LOOK_IDS)
    pygame.quit()


@pytest.mark.parametrize("flag", [None, "MT 참석"])
def test_preview_no_change(flag):
    g = Game(seed=0)
    option = {config.OPTION_TEXT: "가만히", config.OPTION_EFFECTS: {},
              config.OPTION_TRAIT: None, config.OPTION_LOOK: None, config.OPTION_FLAG: flag}
    parts = g.get_option_preview(option)
    assert [(t, tuple(c)) for t, c in parts] == [("변화 없음", tuple(config.COLOR_PREVIEW_OTHER))]
    pygame.quit()


def test_wrap_text_long_text_two_lines_with_ellipsis(make_game):
    """2줄을 넘는 상황 글자는 2줄로 자르고 끝에 '…'. 짧은 글은 그대로 한 줄."""
    g = make_game()
    font = g.event_font
    short = event_by_id("mt_invite")[config.EVENT_TEXT]
    assert g.wrap_text(font, short, config.EVENT_TEXT_MAX_WIDTH) == [short]
    long_text = " ".join(["교수님이"] * 40)
    lines = g.wrap_text(font, long_text, config.EVENT_TEXT_MAX_WIDTH)
    assert len(lines) == config.EVENT_TEXT_MAX_LINES
    assert lines[-1].endswith(config.TEXT_ELLIPSIS)
    assert font.size(lines[0])[0] <= config.EVENT_TEXT_MAX_WIDTH
    # 줄임표를 붙인 줄도 대화창 안쪽 폭을 넘지 않는다
    assert font.size(lines[-1])[0] <= DIALOG_INNER.width


def body_color(g, index):
    rect = g.choice_buttons[index].rect
    return color(g.screen, rect.left + 2 * P, rect.centery)


def bar_color(g, index):
    inner = g.choice_buttons[index].rect.inflate(-2 * P, -2 * P)
    return color(g.screen, inner.right - 2, inner.bottom - 2)


def test_choice_button_hover_after_delay(make_game):
    g = make_game(5.0)
    open_dialog(g, event_by_id("free_rider"))
    g.draw()
    assert body_color(g, 0) == config.COLOR_BUTTON and body_color(g, 1) == config.COLOR_BUTTON
    for idx in (0, 1):
        g.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=g.choice_buttons[idx].rect.center,
                                          rel=(0, 0), buttons=(0, 0, 0)))
        g.draw()
        assert body_color(g, idx) == config.COLOR_BUTTON_BRIGHT
        assert body_color(g, 1 - idx) == config.COLOR_BUTTON
        assert bar_color(g, idx) != config.COLOR_COOLDOWN_TRACK
    g.handle_event(pygame.event.Event(pygame.WINDOWLEAVE, window=None))
    g.draw()
    assert body_color(g, 0) == config.COLOR_BUTTON and body_color(g, 1) == config.COLOR_BUTTON


def test_choice_buttons_gray_with_bar_while_waiting(make_game):
    g = make_game(5.0)
    open_dialog(g, event_by_id("free_rider"), ready=False)
    g.update(config.EVENT_DIALOG_SLIDE_TIME + 0.02)    # 슬라이드는 끝, 대기는 남음
    g.mouse_pos = g.choice_buttons[0].rect.center      # 호버해도 회색
    g.draw()
    for idx in (0, 1):
        assert body_color(g, idx) == config.COLOR_GRAY
        assert bar_color(g, idx) == config.COLOR_COOLDOWN_TRACK
    # 진행 막대가 시간에 따라 차오른다(하늘색 칸 수 증가)
    inner = g.choice_buttons[0].rect.inflate(-2 * P, -2 * P)

    def filled():
        y = inner.bottom - 2
        return sum(1 for x in range(inner.left, inner.right)
                   if color(g.screen, x, y) == config.COLOR_COOLDOWN_FILL)
    first = filled()
    g.update(0.1)
    g.draw()
    assert filled() > first
    g.update(config.EVENT_INPUT_DELAY)
    g.draw()
    assert body_color(g, 0) == config.COLOR_BUTTON_BRIGHT
    assert bar_color(g, 0) != config.COLOR_COOLDOWN_TRACK


def test_dialog_slide_in(make_game, monkeypatch):
    """대화창은 0.15초 동안 위에서 한 칸씩 내려오고, 그 뒤에는 제자리에 고정."""
    g = make_game(5.0)
    open_dialog(g, event_by_id("mt_invite"), ready=False)
    calls = spy_boxes(monkeypatch)
    ys = []
    t = 0.0
    for step in [0.0, 0.03, 0.03, 0.03, 0.03, 0.03, 0.05, 0.2, 1.0]:
        g.update(step)
        t += step
        calls.clear()
        g.draw()
        boxes = [r for r in calls if r.size == DIALOG.size]
        assert len(boxes) == 1
        ys.append((round(t, 3), boxes[0].y))
    assert ys[0][1] == DIALOG.y - config.EVENT_DIALOG_SLIDE_DISTANCE
    values = [y for _, y in ys]
    assert values == sorted(values)
    assert len(set(values)) >= 3                 # 실제로 움직임
    for t, y in ys:
        assert (DIALOG.y - y) % P == 0
        if t >= config.EVENT_DIALOG_SLIDE_TIME - 1e-9:
            assert y == DIALOG.y, (t, y)
        else:
            assert y < DIALOG.y, (t, y)


def test_choice_buttons_drawn_on_click_rect_after_slide(make_game):
    g = make_game(5.0)
    open_dialog(g, event_by_id("mt_invite"))
    g.draw()
    for cb in g.choice_buttons:
        r = cb.rect
        assert color(g.screen, r.left + P, r.top) == config.COLOR_OUTLINE   # 위 외곽선
        assert color(g.screen, r.left + 2 * P, r.centery) == config.COLOR_BUTTON
        assert color(g.screen, r.left + 2 * P, r.top - 2) != config.COLOR_BUTTON


# ======================= 3. 멈춤 점무늬 =======================

def test_pause_dots_only_in_dialog_state(make_game, monkeypatch):
    g = make_game(5.0)
    count = []
    real = g.draw_pause_dots
    monkeypatch.setattr(g, "draw_pause_dots", lambda: (count.append(1), real()))
    g.draw()
    assert count == []
    open_dialog(g, event_by_id("mt_invite"))
    g.draw()
    assert count == [1]
    press(g, pygame.K_1)
    g.draw()
    assert count == [1]
    g.state = config.STATE_TITLE
    g.draw()
    g.end_game(config.ENDING_LEAVE)
    g.draw()
    assert count == [1]


def test_pause_dots_cover_outside_but_not_dialog(make_game, monkeypatch):
    g = make_game(5.0)
    open_dialog(g, event_by_id("mt_invite"))
    g.draw()
    dotted = g.screen.copy()
    monkeypatch.setattr(g, "draw_pause_dots", lambda: None)
    g.draw()
    plain = g.screen.copy()
    # 대화창 안쪽(그림자 포함)은 완전히 같다
    a = dotted.subsurface(DIALOG_WITH_DROP).copy()
    b = plain.subsurface(DIALOG_WITH_DROP).copy()
    assert pygame.image.tobytes(a, "RGB") == pygame.image.tobytes(b, "RGB")
    # 바깥(무대·상태 패널·버튼 쪽)에는 점이 있다
    diff_outside = 0
    for y in range(0, config.SCREEN_HEIGHT, 2):
        for x in range(0, config.SCREEN_WIDTH, 2):
            if DIALOG_WITH_DROP.collidepoint(x, y):
                continue
            if dotted.get_at((x, y)) != plain.get_at((x, y)):
                diff_outside += 1
    assert diff_outside > 1000
    # 점무늬 색은 도트(단색)이고 알파 Surface 를 쓰지 않는다
    assert len(config.COLOR_PAUSE_DOT) == 3


# ======================= 4. 자동형 알림 =======================

AUTO_IDS = [e[config.EVENT_ID] for e in config.AUTO_EVENTS]
SPEC_GOOD = {"엄마가 반찬을 보내셨다": True, "단톡방에서 칭찬받았다": True,
             "과제 마감 알림이 울렸다": False, "감기 기운이 돈다": False,
             "교수님께 칭찬받았다": True}


@pytest.mark.parametrize("event_id", AUTO_IDS)
def test_notice_good_bad_colors(make_game, monkeypatch, event_id):
    g = make_game(5.0)
    event = event_by_id(event_id)
    g.start_event(event)
    good = sum(event[config.EVENT_EFFECTS].values()) >= 0
    assert g.notice["good"] is good is SPEC_GOOD[event[config.EVENT_TITLE]]
    g.update(config.EVENT_NOTICE_SLIDE_TIME)
    calls = spy_boxes(monkeypatch)
    texts = record_draw(g, monkeypatch)
    box = [r for r in calls if r.x == config.EVENT_NOTICE_X
           and r.height == config.EVENT_NOTICE_HEIGHT]
    assert len(box) == 1
    box = box[0]
    assert box.union(box.move(0, P)) == notice_rect(g)
    inner = box.inflate(-2 * P, -2 * P)
    fill = (config.NOTICE_GOOD_BOX if good else config.NOTICE_BAD_BOX)[0]
    other = (config.NOTICE_BAD_BOX if good else config.NOTICE_GOOD_BOX)[0]
    assert color(g.screen, inner.right - 2, inner.centery) == fill
    region = {color(g.screen, x, y) for x in range(inner.left, inner.right)
              for y in range(inner.top, inner.bottom)}
    assert other not in region
    if good:
        assert config.COLOR_PINK_DARK in region and config.COLOR_PINK in region   # 하트
    else:
        assert config.COLOR_RED_DARK in region                                    # 느낌표
    # (E단위) 알림 글자: notice_font(16px), 길면 띄어쓰기 자리에서 2줄로 나눔, 모두 상자 안
    words = [t for t in texts if t["tag"] == "notice"]
    font = g.notice_font.font
    expected = notice_lines(font, event[config.EVENT_TITLE])
    assert len(expected) <= config.EVENT_TEXT_MAX_LINES
    assert [t["text"] for t in words] == expected
    assert " ".join(t["text"] for t in words) == event[config.EVENT_TITLE]
    assert all(t["font"] == "notice" for t in words)
    for t in words:
        assert inner.contains(t["glyph"]), (t["text"], t["glyph"], inner)
        assert font.size(t["text"])[0] <= config.EVENT_NOTICE_TEXT_MAX_WIDTH or " " not in t["text"]
    for a, b in zip(words, words[1:]):
        assert a["glyph"].bottom <= b["glyph"].top, (a, b)   # 줄끼리 세로로 겹치지 않음
    assert STAGE_INNER.contains(notice_rect(g))


def test_notice_lasts_two_seconds_on_screen(make_game, monkeypatch):
    g = make_game(5.0)
    g.start_event(event_by_id("mom_side_dish") if "mom_side_dish" in AUTO_IDS
                  else config.AUTO_EVENTS[0])
    calls = spy_boxes(monkeypatch)

    def shown():
        calls.clear()
        g.draw()
        return any(r.x == config.EVENT_NOTICE_X and r.height == config.EVENT_NOTICE_HEIGHT
                   for r in calls)
    assert shown()
    t = 0.0
    while t < config.EVENT_NOTICE_TIME - 0.02:
        g.update(FRAME)
        t += FRAME
        assert shown(), t
    while t < config.EVENT_NOTICE_TIME + 0.02:
        g.update(FRAME)
        t += FRAME
    assert not shown() and g.notice is None


def test_notice_slide_in(make_game, monkeypatch):
    g = make_game(5.0)
    g.start_event(config.AUTO_EVENTS[0])
    calls = spy_boxes(monkeypatch)
    ys = []
    for step in [0.0, 0.04, 0.04, 0.04, 0.04, 0.5, 1.0]:
        g.update(step)
        calls.clear()
        g.draw()
        box = [r for r in calls if r.x == config.EVENT_NOTICE_X
               and r.height == config.EVENT_NOTICE_HEIGHT]
        ys.append(box[0].y)
    assert ys[0] == config.EVENT_NOTICE_Y - config.EVENT_NOTICE_SLIDE_DISTANCE
    assert ys == sorted(ys) and len(set(ys)) >= 3
    assert ys[-3:] == [config.EVENT_NOTICE_Y] * 3


def test_notice_drawn_only_inside_stage(make_game, monkeypatch):
    """등장 중(위로 올라가 있음)에도 알림 픽셀은 무대 안쪽에서만 바뀐다(잘라 그림)."""
    for age in (0.0, 0.05, 1.0):
        g = make_game(5.0)
        g.start_event(event_by_id(AUTO_IDS[2]))
        g.update(age)
        g.draw()
        with_notice = g.screen.copy()
        note = g.notice
        g.notice = None
        g.draw()
        without = g.screen.copy()
        g.notice = note
        for surf in (with_notice, without):
            surf.fill((1, 2, 3), STAGE_INNER)
        assert pygame.image.tobytes(with_notice, "RGB") == pygame.image.tobytes(without, "RGB")


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
@pytest.mark.parametrize("action", [FEED, REST, STUDY])
@pytest.mark.parametrize("exam", [False, True])
def test_notice_with_action_effects_no_overlap(make_game, grade, action, exam):
    """행동(팝업 1~3줄 + 파티클) 직후 자동형 이벤트 5종: 알림 상자·이벤트 팝업·행동 팝업·파티클이
    2초 동안 매 프레임 서로 겹치지 않고 무대 안쪽."""
    for event in config.AUTO_EVENTS:
        g = make_game(GRADE_STARTS[grade - 1] + (50.0 if exam else 5.0))
        g.student.health, g.student.mental, g.student.knowledge = 60, 60, 10
        assert g.do_action(action)
        g.start_event(event)
        assert g.notice is not None
        assert any(is_event_popup(p) for p in g.popups)
        check_frames(g, config.EVENT_NOTICE_TIME, (grade, action, exam, event[config.EVENT_ID]))


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
def test_action_while_notice_alive_no_overlap(make_game, grade):
    """알림이 떠 있는 동안(1초 뒤) 다음 행동(공부 3줄)을 해도 팝업·파티클이 알림과 겹치지 않는다."""
    g = make_game(GRADE_STARTS[grade - 1] + 5.0)
    g.student.health, g.student.mental, g.student.knowledge = 60, 60, 10
    assert g.do_action(STUDY)
    g.start_event(event_by_id(AUTO_IDS[4]))
    g.update(1.0)
    assert g.notice is not None
    assert g.do_action(STUDY)
    check_frames(g, 1.0, grade)


# ======================= 5. 이벤트 팝업 열 =======================

def event_popups_order_ok(g):
    pops = sorted([p for p in g.popups if is_event_popup(p)], key=lambda p: p["y"])
    labels = [p["text"].split()[0] for p in pops]
    assert labels == [lb for lb in LABEL_ORDER if lb in labels], labels
    return pops


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
@pytest.mark.parametrize("with_notice", [False, True])
@pytest.mark.parametrize("event_id, index", [("free_rider", 0), ("mt_invite", 0),
                                             ("job_fair", 1), ("exchange_student", 0)])
def test_event_popup_column(make_game, grade, with_notice, event_id, index):
    """선택 결과 팝업(2~3줄)은 EVENT_POPUP_X 열에 체력·멘탈·지식 순으로 위->아래,
    (알림이 있으면 알림 아래), 행동 팝업 3줄·파티클·알림과 겹치지 않고 무대 안쪽."""
    g = make_game(GRADE_STARTS[grade - 1] + 5.0)
    g.student.health, g.student.mental, g.student.knowledge = 60, 60, 10
    if with_notice:
        assert g.do_action(STUDY)
        g.start_event(event_by_id(AUTO_IDS[4]))         # 교수님께 칭찬: 이벤트 팝업 2줄
        event_popups_order_ok(g)
        g.update(1.0)
        assert g.notice is not None
    assert g.do_action(STUDY)                            # 행동 팝업 3줄 + 파티클
    open_dialog(g, event_by_id(event_id))
    n_before = len(g.popups)
    assert g.choose_option(index)
    new = g.popups[n_before:]
    effects = event_by_id(event_id)[config.EVENT_OPTIONS][index][config.OPTION_EFFECTS]
    assert len(new) == len(effects) >= 2
    assert all(p["x"] == config.EVENT_POPUP_X for p in new)
    pops = sorted(new, key=lambda p: p["y"])
    labels = [p["text"].split()[0] for p in pops]
    assert labels == [lb for lb in LABEL_ORDER if lb in labels]
    top = config.PANEL_Y
    if with_notice:
        assert g.notice is not None
        top = config.EVENT_NOTICE_Y + config.EVENT_NOTICE_HEIGHT
        assert popup_rect(g, pops[0], config.POPUP_TIME).top > notice_rect(g).bottom
    assert pops[0]["y"] == top + config.EVENT_POPUP_TOP_MARGIN
    check_frames(g, config.POPUP_TIME, (grade, with_notice, event_id))


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
def test_auto_event_popups_column_order(make_game, grade):
    g = make_game(GRADE_STARTS[grade - 1] + 5.0)
    g.student.health, g.student.mental, g.student.knowledge = 60, 60, 10
    g.start_event(event_by_id(AUTO_IDS[4]))
    pops = event_popups_order_ok(g)
    assert [p["text"] for p in pops] == ["멘탈 +5", "지식 +15"]
    assert pops[0]["y"] == config.EVENT_NOTICE_Y + config.EVENT_NOTICE_HEIGHT \
        + config.EVENT_POPUP_TOP_MARGIN


# ======================= 6. 외형 5종 =======================

def render_student(s, lift=0):
    surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    surf.fill(config.COLOR_BG)
    s.draw(surf, lift)
    return surf


def diff_set(a, b, area=STAGE_INNER):
    """area 안에서 색이 다른 픽셀 좌표 집합."""
    sa = pygame.image.tobytes(a.subsurface(area).copy(), "RGB")
    sb = pygame.image.tobytes(b.subsurface(area).copy(), "RGB")
    out = set()
    w = area.width
    for i in range(0, len(sa), 3):
        if sa[i:i + 3] != sb[i:i + 3]:
            n = i // 3
            out.add((area.left + n % w, area.top + n // w))
    return out


def student(grade, looks=(), health=80, mental=80):
    s = Student()
    s.elapsed = GRADE_STARTS[grade - 1] + 5.0
    reach_grade(s, grade)   # (L단위) 학년은 지식으로
    s.health, s.mental = health, mental
    for look in looks:
        s.add_look(look)
    return s


def look_cells(look):
    (col, row), grid = config.LOOK_SPRITES[look]
    return {(col + c, row + r) for r, line in enumerate(grid) for c, ch in enumerate(line)
            if ch in config.LOOK_COLORS}


def bbox(points):
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def test_look_config_complete():
    assert set(config.LOOK_SPRITES) == set(config.LOOK_IDS)
    assert sorted(config.LOOKS_BEHIND + config.LOOKS_FRONT) == sorted(config.LOOK_IDS)
    assert config.LOOKS_BEHIND == [config.LOOK_GUITAR]
    for look, (_, grid) in config.LOOK_SPRITES.items():
        assert len({len(line) for line in grid}) == 1, look
        assert set("".join(grid)) <= set(config.LOOK_COLORS) | {"."}, look


@pytest.mark.parametrize("look", config.LOOK_IDS)
def test_look_drawn_only_when_owned(surface, look):
    """얻은 외형만 그려진다. 다른 외형만 가진 제자 그림에는 이 외형 고유 색이 없다."""
    base = render_student(student(4))
    own = render_student(student(4, [look]))
    d = diff_set(base, own)
    assert d, look
    own_colors = {color(own, x, y) for x, y in d}
    _, grid = config.LOOK_SPRITES[look]
    sprite_colors = {tuple(config.LOOK_COLORS[ch]) for ch in "".join(grid) if ch != "."}
    assert own_colors <= sprite_colors | set(map(tuple, config.FACE_COLORS.values()))
    # 고유 색(다른 외형·얼굴에 없는 색)이 실제로 찍힌다
    others = set(map(tuple, config.FACE_COLORS.values()))
    for other in config.LOOK_IDS:
        if other != look:
            _, og = config.LOOK_SPRITES[other]
            others |= {tuple(config.LOOK_COLORS[ch]) for ch in "".join(og) if ch != "."}
    unique = sprite_colors - others - {tuple(config.COLOR_BG)}
    if unique:
        assert own_colors & unique, look
    without = render_student(student(4, [x for x in config.LOOK_IDS if x != look]))
    present = {color(without, x, y) for x in range(STAGE_INNER.left, STAGE_INNER.right, 1)
               for y in range(STAGE_INNER.top, STAGE_INNER.bottom, 1)}
    assert not (present & unique), look


@pytest.mark.parametrize("look", config.LOOK_IDS)
def test_look_scales_with_grade_and_position(surface, look):
    """학년마다 칸 크기(반지름//10 = 4/5/6/7)에 비례해 커지고, 얼굴 격자 위치에 놓인다."""
    sizes = {}
    for grade in (1, 2, 3, 4):
        s = student(grade)
        cell = s.get_radius() // 10
        assert cell == s.get_cell_size() == 3 + grade
        d = diff_set(render_student(s), render_student(student(grade, [look])))
        left, top, right, bottom = bbox(d)
        (col, row), grid = config.LOOK_SPRITES[look]
        w, h = sprite_size(grid, cell)
        face_left = CX - s.get_radius()
        face_top = CY - s.get_radius()
        sprite_rect = pygame.Rect(face_left + col * cell, face_top + row * cell, w, h)
        assert sprite_rect.contains(pygame.Rect(left, top, right - left, bottom - top)), \
            (look, grade)
        sizes[grade] = (right - left, bottom - top, cell)
    w1, h1, c1 = sizes[1]
    for grade, (w, h, c) in sizes.items():
        assert w * c1 == w1 * c and h * c1 == h1 * c, (look, grade, sizes)


@pytest.mark.parametrize("grade", [1, 4])
@pytest.mark.parametrize("lift", [4, 8, 12])
def test_looks_move_with_lift(surface, grade, lift):
    """점프·숨쉬기로 lift 만큼 뜨면 외형도 정확히 lift 만큼 함께 올라간다."""
    for look in config.LOOK_IDS:
        d0 = diff_set(render_student(student(grade)), render_student(student(grade, [look])))
        d1 = diff_set(render_student(student(grade), lift),
                      render_student(student(grade, [look]), lift))
        assert d1 == {(x, y - lift) for x, y in d0}, (look, grade, lift)


def face_cells_pixels(s, cells, lift=0):
    cell = s.get_cell_size()
    left = CX - s.get_radius()
    top = CY - s.get_radius() - lift
    out = set()
    for c, r in cells:
        for dx in range(cell):
            for dy in range(cell):
                out.add((left + c * cell + dx, top + r * cell + dy))
    return out


def sprite_cells(grid, pos):
    col, row = pos
    return {(col + c, row + r) for r, line in enumerate(grid) for c, ch in enumerate(line)
            if ch in config.FACE_COLORS}


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
def test_guitar_behind_face(surface, grade):
    """기타는 얼굴 뒤: 얼굴 스프라이트의 칸 픽셀은 기타가 있어도 하나도 바뀌지 않는다."""
    s = student(grade)
    face = sprite_cells(config.FACE_SPRITE, (0, 0))
    d = diff_set(render_student(s), render_student(student(grade, [config.LOOK_GUITAR])))
    assert d
    assert not (d & face_cells_pixels(s, face))
    # 기타는 얼굴 밖에서 실제로 보인다(몸통 색)
    g_surf = render_student(student(grade, [config.LOOK_GUITAR]))
    assert any(color(g_surf, x, y) == config.COLOR_GUITAR_BODY for x, y in d)


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
@pytest.mark.parametrize("mental", [80, 45, 10])
def test_looks_never_hide_eyes_glasses_mouth_dark_circles(surface, grade, mental):
    """외형 5종을 모두 가져도 눈·볼·다크서클·안경·입 칸 픽셀은 그대로다."""
    s = student(grade, health=10, mental=mental)
    cells = set()
    for pos in config.EYE_POSITIONS:
        cells |= sprite_cells(config.EYE_SPRITE, pos)
    for pos in config.DARK_CIRCLE_POSITIONS:
        cells |= sprite_cells(config.DARK_CIRCLE_SPRITE, pos)
    for pos in config.BLUSH_POSITIONS:
        cells |= sprite_cells(config.BLUSH_SPRITE, pos)
    if s.has_glasses():
        for pos, grid in config.GLASSES_PARTS:
            cells |= sprite_cells(grid, pos)
    pos, grid = config.MOUTH_SPRITES[s.get_mouth()]
    cells |= sprite_cells(grid, pos)
    d = diff_set(render_student(s), render_student(student(grade, config.LOOK_IDS,
                                                           health=10, mental=mental)))
    assert not (d & face_cells_pixels(s, cells)), (grade, mental)


def test_looks_cells_do_not_overlap_each_other():
    """앞에 그리는 외형끼리 칸이 겹치지 않는다. 기타와 앞 외형이 겹치는 칸은 얼굴 안(가려짐)뿐이다."""
    front = config.LOOKS_FRONT
    for i, a in enumerate(front):
        for b in front[i + 1:]:
            assert not (look_cells(a) & look_cells(b)), (a, b)
    face = sprite_cells(config.FACE_SPRITE, (0, 0))
    for b in front:
        shared = look_cells(config.LOOK_GUITAR) & look_cells(b)
        assert shared <= face, (b, sorted(shared - face))


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
def test_each_look_fully_visible_with_all_looks(surface, grade):
    """5종을 모두 가졌을 때도 각 외형이 혼자일 때 보이던 픽셀이 그대로 보인다(서로 안 가림)."""
    base = render_student(student(grade))
    everything = render_student(student(grade, config.LOOK_IDS))
    for look in config.LOOK_IDS:
        alone = render_student(student(grade, [look]))
        d = diff_set(base, alone)
        bad = [(x, y) for x, y in d if color(everything, x, y) != color(alone, x, y)]
        assert not bad, (grade, look, bad[:5])


@pytest.mark.parametrize("grade", [1, 2, 3, 4])
@pytest.mark.parametrize("lift", [0, 12])
def test_all_looks_inside_stage(surface, grade, lift):
    """5종 + 최대 lift(점프 8 + 숨쉬기 4)에서도 외형 스프라이트 전체가 무대 안쪽."""
    s = student(grade, config.LOOK_IDS)
    cell = s.get_cell_size()
    left = CX - s.get_radius()
    top = CY - s.get_radius() - lift
    for look in config.LOOK_IDS:
        (col, row), grid = config.LOOK_SPRITES[look]
        w, h = sprite_size(grid, cell)
        assert STAGE_INNER.contains(pygame.Rect(left + col * cell, top + row * cell, w, h)), \
            (grade, look)
    # 무대 밖 픽셀은 바뀌지 않는다
    full = pygame.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
    a = render_student(student(grade), lift)
    b = render_student(s, lift)
    for surf in (a, b):
        surf.fill((1, 2, 3), STAGE_INNER)
    assert pygame.image.tobytes(a.subsurface(full), "RGB") == \
        pygame.image.tobytes(b.subsurface(full), "RGB")


def test_looks_from_choices_drawn_in_game(make_game):
    g = make_game(5.0)
    g.draw()
    before = g.screen.copy()
    open_dialog(g, event_by_id("club_fair"))
    press(g, pygame.K_1)
    g.breath_time = 0.0
    g.update(0.0)
    g.draw()
    d = diff_set(before, g.screen)
    assert any(color(g.screen, x, y) == config.COLOR_GUITAR_BODY for x, y in d)


# ======================= 7. 특성 배지 =======================

def badge_rect(index):
    row, col = divmod(index, config.TRAIT_BADGE_COLUMNS)
    return pygame.Rect(
        config.TRAIT_BADGE_X + col * (config.TRAIT_BADGE_WIDTH + config.TRAIT_BADGE_GAP),
        config.TRAIT_BADGE_Y + row * (config.TRAIT_BADGE_HEIGHT + config.TRAIT_BADGE_GAP),
        config.TRAIT_BADGE_WIDTH, config.TRAIT_BADGE_HEIGHT)


def draw_badges(traits):
    pygame.init()
    book = {}
    surf = RecSurface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), book)
    surf.fill(config.COLOR_BG)
    font = RecFont(pygame.font.SysFont(config.FONT_NAME, config.SMALL_FONT_SIZE), "small", book)
    s = Student()
    for t in traits:
        s.add_trait(t)
    s.draw_traits(surf, font)
    return surf


def test_no_traits_no_badges(surface):
    surf = draw_badges([])
    assert surf.texts == []
    blank = pygame.Surface(surf.get_size())
    blank.fill(config.COLOR_BG)
    assert pygame.image.tobytes(surf, "RGB") == pygame.image.tobytes(blank, "RGB")


ALL_TRAITS = [config.TRAIT_FITNESS, config.TRAIT_MUSIC, config.TRAIT_CAFFEINE, config.TRAIT_LOVE]


@pytest.mark.parametrize("traits", [
    ALL_TRAITS[:1], ALL_TRAITS[2:3], [ALL_TRAITS[3], ALL_TRAITS[0]],
    [ALL_TRAITS[1], ALL_TRAITS[2], ALL_TRAITS[0]], ALL_TRAITS, list(reversed(ALL_TRAITS)),
])
def test_badges_order_color_text(surface, traits):
    surf = draw_badges(traits)
    assert [t["text"] for t in surf.texts] == traits
    for i, trait in enumerate(traits):
        box = badge_rect(i)
        inner = box.inflate(-2 * P, -2 * P)
        fill, light = config.TRAIT_COLORS[trait]
        assert color(surf, inner.left + 1, inner.bottom - 2) == fill
        assert color(surf, inner.left + 1, inner.top) == light
        assert color(surf, box.left + P, box.top) == config.COLOR_OUTLINE
        assert inner.contains(surf.texts[i]["glyph"]), (trait, surf.texts[i]["glyph"])
    # 다음 자리에는 배지가 없다
    if len(traits) < 4:
        nxt = badge_rect(len(traits)).inflate(-2 * P, -2 * P)
        assert color(surf, nxt.centerx, nxt.centery) == config.COLOR_BG


def test_badge_colors_distinct_per_trait():
    assert set(config.TRAIT_COLORS) == set(ALL_TRAITS)
    fills = [config.TRAIT_COLORS[t][0] for t in ALL_TRAITS]
    assert len(set(map(tuple, fills))) == 4


def test_four_badges_2x2_inside_panel_without_overlap():
    rects = [badge_rect(i) for i in range(4)]
    with_drop = [r.union(r.move(0, P)) for r in rects]
    assert len({r.x for r in rects}) == 2 and len({r.y for r in rects}) == 2
    for r in with_drop:
        assert STATUS_INNER.contains(r), r
    for i in range(4):
        for j in range(i + 1, 4):
            assert not with_drop[i].colliderect(with_drop[j])
    gauge_area = pygame.Rect(config.GAUGE_X, config.HEALTH_LABEL_Y, config.BAR_WIDTH,
                             config.MENTAL_BAR_Y + config.BAR_HEIGHT - config.HEALTH_LABEL_Y)
    gauge_area = gauge_area.inflate(2 * P, 2 * P)   # 막대 테두리 1칸
    for r in with_drop:
        assert not r.colliderect(gauge_area)
        assert r.top > config.MENTAL_BAR_Y + config.BAR_HEIGHT + P


def test_badges_in_game_screen_with_labels_not_overlapping(make_game, monkeypatch):
    g = make_game(5.0)
    for t in ALL_TRAITS:
        g.student.add_trait(t)
    texts = record_draw(g, monkeypatch)
    badge_texts = [t for t in texts if t["text"] in ALL_TRAITS and t["font"] == "small"]
    assert [t["text"] for t in badge_texts] == ALL_TRAITS
    others = [t for t in texts if t["glyph"].colliderect(STATUS_INNER) and t not in badge_texts]
    assert {t["text"] for t in others} >= {config.HEALTH_LABEL, config.MENTAL_LABEL}
    for b in badge_texts:
        for o in others:
            assert not b["glyph"].colliderect(o["glyph"])


def test_trait_badge_from_choice_in_game(make_game, monkeypatch):
    g = make_game(5.0)
    open_dialog(g, event_by_id("club_fair"))
    press(g, pygame.K_2)
    texts = record_draw(g, monkeypatch)
    assert [t["text"] for t in texts if t["text"] in ALL_TRAITS] == [config.TRAIT_FITNESS]


# ======================= 8. 정적 검사 =======================

GAME_FILES = ["game.py", "student.py", "button.py", "main.py", "config.py"]


@pytest.mark.parametrize("name", GAME_FILES)
def test_no_surface_alpha(name):
    src = (ROOT / name).read_text(encoding="utf-8")
    for bad in ("set_alpha", "SRCALPHA", "convert_alpha", "BLEND_", "gfxdraw"):
        assert bad not in src, (name, bad)


@pytest.mark.parametrize("name", ["game.py", "student.py", "button.py", "main.py"])
def test_every_function_and_class_has_docstring(name):
    tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
    missing = [n.name for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not ast.get_docstring(n)]
    assert not missing, (name, missing)


def test_new_ui_methods_exist_and_three_classes():
    tree = ast.parse((ROOT / "game.py").read_text(encoding="utf-8"))
    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert classes == ["Game"]
    for name in ("draw_event_dialog", "draw_event_notice", "draw_pause_dots", "is_dialog_ready",
                 "get_option_preview", "wrap_text"):
        assert hasattr(Game, name)
    assert hasattr(Student, "draw_traits") and hasattr(Student, "draw_looks")
