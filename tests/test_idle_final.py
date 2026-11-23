"""방치형 최종 검수(K단위 2차): 실제 메인 루프 한 바퀴 + 기획서 10절·README 핵심 수치 대조.

- 실제 Game.run() 루프에 이벤트를 넣어(pygame.event.get 대체, 시계는 0.1초 고정):
  타이틀 Enter -> 방치 플레이(방침 1·2 변경, 연구비로 업그레이드 구매) -> 지식 1100 졸업
  -> C 대학원 -> 2년차(누적 1500) -> 휴학(수료) -> R 환생 -> ESC, 새 Game 이 명성·업그레이드를 읽는다.
  (L단위, 기획서 11절: 졸업은 지식 목표, 등급은 걸린 시간, 대학원 년차는 지식 목표)
- 기획서 10절·README 의 업그레이드 표(최대 레벨·기본 가격·레벨별 가격·총합), 방침 표,
  졸업 기준, 대학원 배수, 가격 증가율이 config·Game 계산과 같다.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import json  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

import config  # noqa: E402
from conftest import doc_section, read_doc, spec_appendix, spec_rule_text  # noqa: E402
from game import Game  # noqa: E402

ROOT = Path(config.__file__).parent
TICK_MS = 100            # 가짜 시계: 한 프레임 0.1초
MAX_FRAMES = 20_000      # 안전장치


def key(k):
    """KEYDOWN 이벤트 하나."""
    return pygame.event.Event(pygame.KEYDOWN, key=k)


class FakeClock:
    """clock.tick 이 언제나 TICK_MS 를 돌려준다(실제 시간을 기다리지 않음)."""

    def tick(self, fps):
        return TICK_MS


class IdleScript:
    """pygame.event.get 대신: 매 프레임 게임 상태를 보고 넣을 이벤트를 정한다."""

    def __init__(self, game):
        self.game = game
        self.frames = 0
        self.log = []          # 일어난 일 (이름, 값)
        self.done = set()

    def once(self, name):
        """name 단계를 처음 하는 것이면 True."""
        if name in self.done:
            return False
        self.done.add(name)
        return True

    def __call__(self, *args, **kwargs):
        g = self.game
        s = g.student
        self.frames += 1
        assert self.frames < MAX_FRAMES, self.log
        if g.state == config.STATE_TITLE:
            if self.once("enter"):
                return [key(pygame.K_RETURN)]
            return [key(pygame.K_ESCAPE)]              # 환생 뒤에는 타이틀이 아니라 게임이어야 한다
        if g.state == config.STATE_EVENT:
            return [key(pygame.K_1)]                   # 선택지형 이벤트: 첫 번째
        if g.state == config.STATE_PLAYING and g.grad_year == 0 and "c" not in self.done:
            self.log.append(("policy", g.policy))
            if s.elapsed >= 5 and self.once("key1"):
                return [key(pygame.K_1)]
            if s.elapsed >= 30 and self.once("key2"):
                self.log.append(("policy_before_key2", g.policy))
                return [key(pygame.K_2)]
            if "key2" in self.done and g.money >= g.get_upgrade_cost(config.UPGRADE_MENU) \
                    and self.once("buy"):
                self.log.append(("money_before_buy", g.money))
                return [key(pygame.K_u), key(pygame.K_RETURN), key(pygame.K_u)]
            return []
        if g.state == config.STATE_ENDING and g.is_graduation_ending() and self.once("c"):
            self.log.append(("graduated", g.ending, s.knowledge, g.money, g.graduation_bonus,
                             s.graduation_time))
            return [key(pygame.K_c)]
        if g.state == config.STATE_PLAYING and g.grad_year >= 1:
            if g.grad_year >= 2 and self.once("year2"):
                self.log.append(("year2", s.elapsed))
                s.health = 0.5                         # 2년차에서 휴학(수료)시키기
            return []
        if g.state == config.STATE_ENDING and g.is_grad_school_ending() and self.once("r"):
            self.log.append(("grad_end", g.ending, g.grad_year))
            return [key(pygame.K_r)]
        if g.state == config.STATE_PLAYING and "r" in self.done and self.once("reincarnated"):
            self.log.append(("reborn", g.fame, g.grad_year, s.elapsed, g.policy))
            return [key(pygame.K_ESCAPE)]
        return [key(pygame.K_ESCAPE)]


def test_idle_end_to_end_real_loop(monkeypatch, isolated_record_path):
    g = Game(seed=3)
    g.clock = FakeClock()
    script = IdleScript(g)
    monkeypatch.setattr(pygame.event, "get", script)
    with pytest.raises(SystemExit):
        g.run()
    log = dict((item[0], item[1:]) for item in script.log)
    assert {"enter", "key1", "key2", "buy", "c", "year2", "r", "reincarnated"} <= script.done, script.log

    # 방침: 시작은 균형, 1키로 공부 위주, 2키로 균형
    assert script.log[0] == ("policy", config.POLICY_BALANCED)
    assert log["policy_before_key2"] == (config.POLICY_STUDY_FOCUS,)
    # 업그레이드: 학식 메뉴 개선 240 을 연구비로 샀다
    assert config.UPGRADE_MENU in g.upgrades and g.upgrades[config.UPGRADE_MENU] == 1
    assert log["money_before_buy"][0] >= 240
    # 방치(자동 행동)로 지식 1100 졸업, 등급은 걸린 시간(200초 이하 수석 / 360초 이하 무사, 11절 A안)
    ending, knowledge, money, bonus, seconds = log["graduated"]
    assert ending in (config.ENDING_TOP, config.ENDING_NORMAL, config.ENDING_BARELY)
    assert knowledge >= config.GRADUATION_KNOWLEDGE
    assert ending == (config.ENDING_TOP if seconds <= 200 else
                      config.ENDING_NORMAL if seconds <= 360 else config.ENDING_BARELY)
    assert bonus == config.GRADUATION_BONUS[ending]          # 명성 0
    # 대학원 2년차에서 끝 -> "대학원 2년차 수료"
    assert log["grad_end"] == (config.ENDING_GRAD_TEXT.format(2), 2)
    # R 환생: 명성 1, 학부 1학년 처음, 방침은 균형
    fame, grad_year, elapsed, policy = log["reborn"]
    assert (fame, grad_year, policy) == (1, 0, config.POLICY_START)
    assert elapsed < 1.0

    # 기록 파일과 새 Game: 명성·업그레이드·연구비가 이어진다
    data = json.loads(Path(isolated_record_path).read_text(encoding="utf-8"))
    assert data["fame"] == 1 and data["upgrades"][config.UPGRADE_MENU] == 1
    assert data["best_knowledge"] >= knowledge
    other = Game()
    assert other.fame == 1 and other.upgrades[config.UPGRADE_MENU] == 1
    assert other.money == data["money"] == g.money
    pygame.quit()


# ======================= 문서 대조 =======================

def spec10():
    """기획서에서 지금 규칙을 적은 부분(1~10절, 개발 과정 기록·부록 변경 이력 제외).

    (문서 정리) 예전에는 10절 이후가 방치형 규칙이었지만, 기획서가 최종 게임 한 문서로
    다시 쓰여 업그레이드 표는 3절, 방침 표는 2절에 있다. 절 번호 대신 제목으로 찾는다.
    """
    return spec_rule_text()


def spec_part(*headings):
    """기획서에서 제목 headings를 차례로 따라 들어간 구역 (예: "게임 규칙", "진급과 졸업")."""
    text = read_doc()
    for heading in headings:
        text = doc_section(text, heading)
    return text


def readme():
    return (ROOT / "README.md").read_text(encoding="utf-8")


def table_rows(text, first_header):
    """first_header 로 시작하는 마크다운 표의 데이터 줄들을 칸 목록으로 돌려준다."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| " + first_header))
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def game_costs(uid):
    g = Game()
    out = []
    for level in range(config.UPGRADES_BY_ID[uid][config.UPGRADE_MAX_LEVEL]):
        g.upgrades[uid] = level
        out.append(g.get_upgrade_cost(uid))
    return out


NAME_TO_ID = {u[config.UPGRADE_NAME]: u[config.UPGRADE_ID] for u in config.UPGRADES}


@pytest.mark.parametrize("source", ["spec", "readme"])
def test_upgrade_tables_match_config(source):
    text = spec_part("업그레이드") if source == "spec" else readme()
    rows = table_rows(text, "분류 | 항목")
    assert [NAME_TO_ID[r[1]] for r in rows] == config.UPGRADE_IDS
    for row in rows:
        u = config.UPGRADES_BY_ID[NAME_TO_ID[row[1]]]
        assert row[0] == u[config.UPGRADE_CATEGORY]
        assert int(row[3]) == u[config.UPGRADE_MAX_LEVEL], row
        assert int(row[4]) == u[config.UPGRADE_BASE_COST], row
        # (11절 A안) README 표에도 레벨별 가격 칸이 생겨 둘 다 Game 계산(×2.0)과 대조한다
        listed = [int(x) for x in row[5].split("/")]
        assert listed == game_costs(u[config.UPGRADE_ID]), row
    pygame.quit()


def test_total_cost_61590_matches_game():
    """(11절 A안, 가격 증가 ×2.0) 전부 최고 레벨 합계 61,590 이 기획서·README·Game 계산에서 같다."""
    assert "61,590" in spec_part("업그레이드") and "61,590" in readme()
    assert sum(sum(game_costs(uid)) for uid in config.UPGRADE_IDS) == 61590
    pygame.quit()


@pytest.mark.parametrize("source", ["spec", "readme"])
def test_policy_tables_match_config(source):
    text = spec_part("게임 규칙", "자동 행동과 일과표 방침") if source == "spec" else readme()
    rows = table_rows(text, "방침 | 키")
    expected = {"공부 위주": (config.POLICY_STUDY_FOCUS, "1"), "균형": (config.POLICY_BALANCED, "2"),
                "휴식 위주": (config.POLICY_REST_FOCUS, "3")}
    assert len(rows) == 3
    for index, row in enumerate(rows):
        name = row[0].replace("(시작값)", "").strip()
        policy, key_text = expected[name]
        assert config.POLICY_ORDER[index] == policy and row[1] == key_text
        p = config.POLICIES[policy]
        assert int(row[2]) == p[config.POLICY_THRESHOLD]
        assert float(row[3].lstrip("×")) == p[config.POLICY_KNOWLEDGE_RATIO]
        assert float(row[4].lstrip("×")) == p[config.POLICY_COST_RATIO]


def test_key_numbers_in_spec_and_readme():
    """(문서 정리) 최종 수치가 기획서 규칙 절(제목으로 찾음)과 README에 있고 config와 같다."""
    s, r = spec10(), readme()
    grade_rules = spec_part("게임 규칙", "졸업 등급과 졸업 보너스") + spec_part("게임 규칙", "진급과 졸업")
    grad_rules = spec_part("환생과 대학원")
    # 졸업 기준 (A안: 걸린 시간 200/360초, 졸업 지식 1100)
    for text in (grade_rules, r):
        assert "| 수석 졸업 | 200초 이하" in text and "| 아슬아슬 졸업 | 360초 초과" in text
        assert "| 무사 졸업 | 200초 초과 360초 이하" in text
        assert "| 졸업 | 1100 |" in text
    assert (config.TOP_GRADUATE_SECONDS, config.NORMAL_GRADUATE_SECONDS) == (200, 360)
    assert config.GRADUATION_KNOWLEDGE == 1100
    # 가격 증가율 (11절 A안: 1.8 -> 2.0)
    assert "기본 가격 × **2.0**^(현재 레벨)" in spec_part("업그레이드")
    assert "기본 가격 × 2.0^(현재 레벨)" in r
    assert config.UPGRADE_COST_GROWTH == 2.0
    # 대학원 배수 (11절 A안: 자연 감소 1 + 0.5n + 1.0c, 연구비 1 + 1.0n)
    for text in (grad_rules, r):
        assert "×(1 + 0.5n + 1.0c)" in text
    assert "연구비 ×(1 + **1.0**n)" in grad_rules and "×(1 + 1.0n)" in r
    # 예전 수치(1.8배 가격, 대학원 0.25n, 수석 240초)는 규칙 절에 없고 부록 변경 이력에만 있다
    history = spec_appendix()
    for old in ("×1.8", "0.25n", "240초"):
        assert old not in s, old
        assert old in history, old
    assert (config.GRAD_DECAY_BONUS, config.GRAD_CYCLE_DECAY_BONUS, config.GRAD_MONEY_BONUS) \
        == (0.5, 1.0, 1.0)

    # 졸업 보너스, 명성, 자동 행동 간격, 이벤트 확률
    for text in (s, r):
        assert "수석 +200, 무사 +100, 아슬아슬 +50" in text
        assert "1 + 0.1 × 명성" in text
        assert "25% → 최대 40%" in text
        assert "2.0 → 1.0" in text
    assert config.GRADUATION_BONUS == {config.ENDING_TOP: 200, config.ENDING_NORMAL: 100,
                                       config.ENDING_BARELY: 50}
    assert config.FAME_MONEY_BONUS == 0.1 and config.AUTO_ACTION_INTERVAL == 2.0
    charm = config.UPGRADES_BY_ID[config.UPGRADE_CHARM]
    assert config.EVENT_CHANCE + charm[config.UPGRADE_PER_LEVEL] * charm[config.UPGRADE_MAX_LEVEL] \
        == pytest.approx(0.40)
    time_mgmt = config.UPGRADES_BY_ID[config.UPGRADE_TIME]
    assert config.AUTO_ACTION_INTERVAL - time_mgmt[config.UPGRADE_PER_LEVEL] \
        * time_mgmt[config.UPGRADE_MAX_LEVEL] == pytest.approx(1.0)


def test_readme_controls_match_game():
    """README 3절 조작표의 키가 실제 Game 에서 그 일을 한다."""
    rows = {r[0]: r for r in table_rows(readme(), "조작 | 마우스")}
    assert rows["게임 시작"][2] == "Enter"
    assert [rows["방침: " + n][2] for n in ("공부 위주", "균형", "휴식 위주")] == ["1", "2", "3"]
    assert rows["업그레이드 패널 열기·닫기"][2] == "U"
    assert rows["대학원 진학"][2] == "C"
    g = Game()
    g.handle_event(key(pygame.K_RETURN))
    assert g.state == config.STATE_PLAYING
    for k, policy in zip((pygame.K_1, pygame.K_2, pygame.K_3), config.POLICY_ORDER):
        g.handle_event(key(k))
        assert g.policy == policy
    g.handle_event(key(pygame.K_u))
    assert g.upgrade_panel_open
    g.handle_event(key(pygame.K_u))
    assert not g.upgrade_panel_open
    pygame.quit()


def test_spec_section2_idle_balance_note_present():
    """(문서 정리) 밸런스 기록이 있다: 10절에 최종 A안 표와 첫 판 시뮬레이션, 부록에 지난 기준.

    예전 "2절 변경 메모(방치형 1000/750)"는 부록 변경 이력의 K단위 줄로 옮겨졌다.
    분포 자체는 아래 시뮬레이션 테스트와 수동 확인 목록에서 본다.
    """
    balance = spec_part("밸런스")
    assert "| 진급·졸업 목표 | 200 / 450 / 750 / 1100 |" in balance
    assert "| 수석 졸업 | 200초 이하 |" in balance and "| 무사 졸업 | 360초 이하 |" in balance
    assert re.search(r"\| 없음 \| 무사 29 \+ 휴학 1, 평균 \d+초 \| 무사 30, 평균 \d+초 \| "
                     r"무사 15 \+ 아슬아슬 15, 평균 \d+초 \|", balance)
    assert re.search(r"1000 / 750", spec_appendix())


# ======================= 방치형 밸런스 (기획서 2절 변경 메모) =======================

def idle_round(seed, policy_key, dt=0.25):
    """업그레이드 없이 방침 하나로 방치한 한 판. 선택지형 이벤트는 시드 짝/홀로 1번/2번."""
    g = Game(seed=seed)
    g.handle_event(key(pygame.K_RETURN))
    g.handle_event(key(policy_key))
    for _ in range(5000):
        if g.state == config.STATE_EVENT:
            if not g.choose_option(config.CHOICE_FIRST if seed % 2 == 0 else config.CHOICE_SECOND):
                g.update(dt)
        elif g.state == config.STATE_PLAYING:
            g.update(dt)
        else:
            break
    assert g.state == config.STATE_ENDING
    return g.ending


def test_idle_first_round_distribution_matches_spec_note():
    """기획서 2절: 업그레이드 없이 첫 판은 공부 위주면 무사~수석, 균형이면 무사, 휴식 위주면 대부분 아슬아슬.

    검수팀 실측(시드 20개): 공부 위주 18 무사 + 2 수석, 균형 12 무사 + 8 아슬아슬, 휴식 위주 18 아슬아슬 + 2 무사.
    """
    seeds = range(20)
    counts = {}
    for name, k in (("study", pygame.K_1), ("balanced", pygame.K_2), ("rest", pygame.K_3)):
        c = {}
        for seed in seeds:
            ending = idle_round(seed, k)
            c[ending] = c.get(ending, 0) + 1
        counts[name] = c
    assert set(counts["study"]) <= {config.ENDING_NORMAL, config.ENDING_TOP}, counts
    assert max(counts["balanced"], key=counts["balanced"].get) == config.ENDING_NORMAL, counts
    assert config.ENDING_TOP not in counts["balanced"], counts
    assert counts["rest"].get(config.ENDING_BARELY, 0) > len(seeds) // 2, counts
    assert config.ENDING_TOP not in counts["rest"], counts
    for c in counts.values():
        assert config.ENDING_LEAVE not in c, counts
    pygame.quit()
