"""방치형 최종 검수(K단위 2차): 실제 메인 루프 한 바퀴 + 기획서 핵심 수치 대조(README는 요약 문구만).

- 실제 Game.run() 루프에 이벤트를 넣어(pygame.event.get 대체, 시계는 0.1초 고정):
  타이틀 Enter -> 방치 플레이(방침 1·2 변경, 연구비로 업그레이드 구매) -> 지식 1100 졸업
  -> C 대학원 -> 2년차(누적 1500) -> 휴학(수료) -> R 환생 -> ESC, 새 Game 이 명성·업그레이드를 읽는다.
  (L단위, 기획서 11절: 졸업은 지식 목표, 등급은 걸린 시간, 대학원 년차는 지식 목표)
- 기획서의 업그레이드 표(최대 레벨·기본 가격·레벨별 가격·총합), 방침 표,
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
            # (M단위) 대학원 1년차 목표가 3000(2배)이라 방치로는 2년차 전에 수료하기 쉽다.
            # 년차 오름 흐름을 보려고 진학 직후 지식을 목표 10 앞까지 채운다(다음 공부로 2년차).
            if g.grad_year == 1 and self.once("boost"):
                s.knowledge = max(s.knowledge, s.get_next_goal() - 10)
                s.health = s.max_health
                s.mental = s.max_mental
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
    # 방치(자동 행동)로 졸업 지식(M단위 2200) 졸업, 등급은 걸린 시간(시간 기준은 config 상수라 config 상수로)
    ending, knowledge, money, bonus, seconds = log["graduated"]
    assert ending in (config.ENDING_TOP, config.ENDING_NORMAL, config.ENDING_BARELY)
    assert knowledge >= config.GRADUATION_KNOWLEDGE
    assert ending == (config.ENDING_TOP if seconds <= config.TOP_GRADUATE_SECONDS else
                      config.ENDING_NORMAL if seconds <= config.NORMAL_GRADUATE_SECONDS
                      else config.ENDING_BARELY)
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


# (토큰 정리) README는 사용자용 소개가 되어 업그레이드·방침·등급 표가 빠졌다.
# 표-config 대조는 기획서만 하고, README는 요약 문구가 config와 맞는지만 본다.


def test_upgrade_tables_match_config():
    """기획서 3절 업그레이드 표(분류·최대 레벨·기본 가격·레벨별 가격)가 config·Game 계산과 같다."""
    text = spec_part("업그레이드")
    rows = table_rows(text, "분류 | 항목")
    assert [NAME_TO_ID[r[1]] for r in rows] == config.UPGRADE_IDS
    for row in rows:
        u = config.UPGRADES_BY_ID[NAME_TO_ID[row[1]]]
        assert row[0] == u[config.UPGRADE_CATEGORY]
        assert int(row[3]) == u[config.UPGRADE_MAX_LEVEL], row
        assert int(row[4]) == u[config.UPGRADE_BASE_COST], row
        # (11절 A안) 레벨별 가격 칸을 Game 계산(×2.0)과 대조한다
        listed = [int(x) for x in row[5].split("/")]
        assert listed == game_costs(u[config.UPGRADE_ID]), row
    pygame.quit()


def test_total_cost_92590_matches_game():
    """(11절 A안, 가격 증가 ×2.0) 전부 최고 레벨 합계가 기획서와 Game 계산에서 같다.

    (M단위) 업그레이드 13종(컨디션 3종 31,000 추가) -> 61,590 + 31,000 = 92,590.
    """
    assert "108,090" in spec_part("업그레이드")   # (연구비) 92,590 + 연구 과제 수주 15,500
    assert sum(sum(game_costs(uid)) for uid in config.UPGRADE_IDS) == 108090
    condition = (config.UPGRADE_HEALTH_MAX, config.UPGRADE_MENTAL_MAX, config.UPGRADE_SELF_CARE)
    assert sum(sum(game_costs(uid)) for uid in condition) == 31000
    pygame.quit()


def test_policy_tables_match_config():
    """기획서 2절 방침 표(키·회복 기준·지식·소모 배수)가 config와 같다."""
    text = spec_part("게임 규칙", "자동 행동과 일과표 방침")
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


def grade_rows(top, normal):
    """졸업 등급 표 줄(시간 기준은 config 상수로 만든다, B안 330/720초)."""
    return ["| 수석 졸업 | {}초 이하".format(top),
            "| 무사 졸업 | {}초 초과 {}초 이하".format(top, normal),
            "| 아슬아슬 졸업 | {}초 초과".format(normal)]


def grad_decay_text():
    """대학원 자연 감소 배수 글자 "×(1 + 1.0n + 1.5c)"를 config 값으로 만든다."""
    return "×(1 + {:.1f}n + {:.1f}c)".format(config.GRAD_DECAY_BONUS, config.GRAD_CYCLE_DECAY_BONUS)


def test_key_numbers_in_spec():
    """(문서 정리) 최종 수치가 기획서 규칙 절(제목으로 찾음)에 있고 config와 같다.

    (M단위) 졸업 지식 2200. (B안) 시간 기준 330/720초, 대학원 감소 1 + 1.0n + 1.5c. 표 줄은 config 값으로 만든다.
    README 쪽은 요약 문구만 본다(test_key_numbers_in_readme).
    """
    s = spec10()
    grade_rules = spec_part("게임 규칙", "졸업 등급과 졸업 보너스") + spec_part("게임 규칙", "진급과 졸업")
    grad_rules = spec_part("환생과 대학원")
    for line in grade_rows(config.TOP_GRADUATE_SECONDS, config.NORMAL_GRADUATE_SECONDS):
        assert line in grade_rules, line
    assert "| 졸업 | {} |".format(config.GRADUATION_KNOWLEDGE) in grade_rules
    assert config.GRADUATION_KNOWLEDGE == 2200
    # 가격 증가율 (11절 A안: 1.8 -> 2.0)
    assert "기본 가격 × **2.0**^(현재 레벨)" in spec_part("업그레이드")
    assert config.UPGRADE_COST_GROWTH == 2.0
    # 대학원 배수 (B안: 자연 감소 1 + 1.0n + 1.5c, 연구비 1 + 1.0n)
    assert grad_decay_text() in grad_rules
    assert "연구비 ×(1 + **1.0**n)" in grad_rules
    # 예전 수치(1.8배 가격, 대학원 0.25n, 수석 240초)는 규칙 절에 없고 부록 변경 이력에만 있다
    # (M단위) 방침 공부 위주 소모가 ×1.8이 되어 가격 증가율은 "증가 ×1.8"로 찾는다
    history = spec_appendix()
    for old in ("증가 ×1.8", "0.25n", "240초"):
        assert old not in s, old
        assert old in history, old
    assert (config.GRAD_DECAY_BONUS, config.GRAD_CYCLE_DECAY_BONUS, config.GRAD_MONEY_BONUS) \
        == (1.0, 2.5, 1.0)   # 개운함 조정으로 c 항 1.5 -> 2.5

    # 졸업 보너스, 명성, 자동 행동 간격, 이벤트 확률
    assert "수석 +200, 무사 +100, 아슬아슬 +50" in s
    assert "1 + 0.1 × 명성" in s
    assert "25% → 최대 40%" in s
    assert "2.0 → 1.0" in s
    assert config.GRADUATION_BONUS == {config.ENDING_TOP: 200, config.ENDING_NORMAL: 100,
                                       config.ENDING_BARELY: 50}
    assert config.FAME_MONEY_BONUS == 0.1 and config.AUTO_ACTION_INTERVAL == 2.0
    charm = config.UPGRADES_BY_ID[config.UPGRADE_CHARM]
    assert config.EVENT_CHANCE + charm[config.UPGRADE_PER_LEVEL] * charm[config.UPGRADE_MAX_LEVEL] \
        == pytest.approx(0.40)
    time_mgmt = config.UPGRADES_BY_ID[config.UPGRADE_TIME]
    assert config.AUTO_ACTION_INTERVAL - time_mgmt[config.UPGRADE_PER_LEVEL] \
        * time_mgmt[config.UPGRADE_MAX_LEVEL] == pytest.approx(1.0)


def test_key_numbers_in_readme():
    """README 규칙 요약의 진급·졸업 지식, 등급 시간 기준이 config와 같다(표는 기획서에만 있다)."""
    r = readme()
    assert "누적 지식 {}".format(" / ".join(str(g) for g in config.GRADE_GOALS)) in r
    assert "{}이면 졸업".format(config.GRADUATION_KNOWLEDGE) in r
    assert "{}초 이하면 수석".format(config.TOP_GRADUATE_SECONDS) in r
    assert "{}초 이하면 무사".format(config.NORMAL_GRADUATE_SECONDS) in r
    assert "](docs/기획서.md)" in r


def test_readme_describes_m_rules():
    """(M단위) README 요약이 M단위 규칙(회복은 휴식, 학식 든든함, 디버프·버프, 업그레이드 13종)을 말한다."""
    r = readme()
    for word in (config.BUFF_FULL, config.DEBUFF_TIRED, config.DEBUFF_DEPRESSED,
                 config.CONDITION_GOOD, "회복은 휴식에서만"):
        assert word in r, word
    assert "업그레이드 {}종".format(len(config.UPGRADE_IDS)) in r and len(config.UPGRADE_IDS) == 14   # (연구비) 13 -> 14
    assert "| 학식 먹이기 | +20 |" not in r
    # 컨디션 업그레이드 3종 이름은 기획서 업그레이드 표에 있다
    for word in ("체력 증진", "멘탈 관리", "자기 관리"):
        assert word in spec_part("업그레이드"), word


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
    (M단위) A안 표·시뮬레이션은 "M단위 이전 규칙" 기록으로 남는다.
    (B안) 지금 수치는 B안 표로 확정되어 "임시 값" 안내는 없어졌다.
    """
    balance = spec_part("밸런스")
    assert "| 진급·졸업 목표 | 200 / 450 / 750 / 1100 |" in balance
    assert "| 수석 졸업 | 200초 이하 |" in balance and "| 무사 졸업 | 360초 이하 |" in balance
    assert re.search(r"\| 없음 \| 무사 29 \+ 휴학 1, 평균 \d+초 \| 무사 30, 평균 \d+초 \| "
                     r"무사 15 \+ 아슬아슬 15, 평균 \d+초 \|", balance)
    assert re.search(r"1000 / 750", spec_appendix())
    assert "임시 값" not in balance and "400 / 900 / 1500 / 2200" in balance
    assert "B안" in balance
    assert "| 수석 졸업 | {}초 이하 |".format(config.TOP_GRADUATE_SECONDS) in balance
    assert "| 무사 졸업 | {}초 이하 |".format(config.NORMAL_GRADUATE_SECONDS) in balance
    assert grad_decay_text() in balance


# ======================= 방치형 밸런스 (기획서 2절 변경 메모) =======================

def idle_round(seed, policy_key, dt=0.25):
    """업그레이드 없이 방침 하나로 방치한 한 판. 선택지형 이벤트는 시드 짝/홀로 1번/2번.

    (M단위) 엔딩 이름과 함께 졸업 시각(휴학이면 None)·지식·경과 시간을 돌려준다.
    """
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
    s = g.student
    return g.ending, s.graduation_time, s.knowledge, s.elapsed


def test_idle_first_round_distribution_matches_spec_note():
    """업그레이드 없는 첫 판 방치: 불변식만 본다(M단위, 분포는 밸런스 단위에서 다시 정함).

    예전(A안): 공부 위주 무사~수석, 균형 무사, 휴식 위주 대부분 아슬아슬처럼 분포를 고정했다.
    M단위 뒤로는 수치가 임시라 분포를 고정하지 않고 다음만 확인한다.
    - 모든 판이 크래시 없이 엔딩(휴학 또는 졸업)으로 끝난다.
    - 졸업 엔딩 등급은 judge_ending(걸린 시간)과 같고, 휴학이면 졸업 시각이 없다.
    - 지식을 버는 속도(전체 지식 / 전체 시간)는 공부 위주 > 균형 > 휴식 위주.
    - 졸업한 판의 평균 졸업 시각은 (졸업이 있는 방침끼리) 공부 위주 < 균형 < 휴식 위주.
    """
    from student import judge_ending

    seeds = range(20)
    rates = {}
    mean_times = {}
    for name, k in (("study", pygame.K_1), ("balanced", pygame.K_2), ("rest", pygame.K_3)):
        knowledge_sum = 0
        time_sum = 0.0
        grad_times = []
        for seed in seeds:
            ending, grad_time, knowledge, elapsed = idle_round(seed, k)
            if grad_time is None:
                assert ending == config.ENDING_LEAVE, (name, seed, ending)
            else:
                assert ending == judge_ending(grad_time), (name, seed, ending, grad_time)
                assert knowledge >= config.GRADUATION_KNOWLEDGE
                grad_times.append(grad_time)
            knowledge_sum += knowledge
            time_sum += elapsed
        rates[name] = knowledge_sum / time_sum
        if grad_times:
            mean_times[name] = sum(grad_times) / len(grad_times)
    assert rates["study"] > rates["balanced"] > rates["rest"], rates
    ordered = [mean_times[n] for n in ("study", "balanced", "rest") if n in mean_times]
    assert ordered == sorted(ordered), mean_times
    assert len(ordered) >= 2, mean_times
    pygame.quit()
