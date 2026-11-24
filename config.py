"""제자 키우기의 모든 수치 상수를 모아 둔 파일."""

import os
import sys

# ---------------------------------------------------------------
# 1. 창과 화면
# ---------------------------------------------------------------
SCREEN_WIDTH = 800          # 창 가로 크기(픽셀)
SCREEN_HEIGHT = 600         # 창 세로 크기(픽셀)
FPS = 60                    # 1초에 화면을 몇 번 그릴지
WINDOW_TITLE = "제자 키우기"  # 창 제목
FONT_NAME = "malgungothic"  # 한글 폰트 이름 (SysFont 용)
MS_PER_SECOND = 1000        # 밀리초 -> 초 변환에 쓰는 값

# ---------------------------------------------------------------
# 2. 화면 상태 이름
# ---------------------------------------------------------------
STATE_TITLE = "title"       # 타이틀 화면
STATE_PLAYING = "playing"   # 게임 화면
STATE_ENDING = "ending"     # 엔딩 화면
STATE_EVENT = "event"       # 선택지형 이벤트 대화창 (게임 진행이 멈춘 상태)

# 게임을 켰을 때 처음 보여 줄 화면: 타이틀 화면
START_STATE = STATE_TITLE

# ---------------------------------------------------------------
# 3. 시간
# ---------------------------------------------------------------
# 기획서 2절: 판에 시간 제한이 없다. 학년은 누적 지식으로 오르고,
# 60초 "주기"는 계절·낮밤·시험 기간·이벤트 횟수를 세는 보기용 시계로만 쓴다.
CYCLE_SECONDS = 60                          # 주기 하나의 길이(초): 봄·여름·가을·겨울 한 바퀴
CYCLE_INDEX_START = 1                       # 첫 주기 번호 (0~60초 = 1번 주기)
MAX_GRADE = 4                               # 마지막 학년
EXAM_SECONDS = 15                           # 각 주기 마지막 15초(45~60초)가 시험 기간
FIRST_GRADE = 1                             # 처음 학년
GRADE_STEP = 1                              # 진급 목표를 넘을 때마다 오르는 학년
PROMOTION_COUNT_START = 0                   # 한 번 판정에서 오른 횟수(진급 수)의 시작값
SECONDS_PER_MINUTE = 60                     # "3분 12초"처럼 보일 때 1분 = 60초
ZERO_TIME = 0.0                             # 시간 값의 시작값·하한(초): 타이머 초기값·하한

# ---------------------------------------------------------------
# 4. 게이지
# ---------------------------------------------------------------
GAUGE_MIN = 0               # 체력·멘탈·지식의 최솟값
GAUGE_MAX = 100             # 체력·멘탈의 기본 최댓값 (지식은 상한 없음)
# 체력 증진·멘탈 관리 업그레이드로 최댓값이 레벨마다 +10 오른다(기획서 3절):
# 체력 최대 = GAUGE_MAX + 10 x 체력 증진 Lv, 멘탈 최대 = GAUGE_MAX + 10 x 멘탈 관리 Lv

HEALTH_START = 80           # 체력 시작값
MENTAL_START = 80           # 멘탈 시작값
KNOWLEDGE_START = 0         # 지식 시작값

HEALTH_DECAY_PER_SEC = 1        # 체력 자연 감소(1초마다)
MENTAL_DECAY_PER_SEC = 1        # 멘탈 자연 감소(1초마다)
MENTAL_DECAY_PER_SEC_EXAM = 2   # 시험 기간 멘탈 자연 감소(1초마다)
DECAY_INTERVAL = 1.0            # 자연 감소가 일어나는 간격(초)
TIME_EPSILON = 1e-9             # 소수 덧셈 오차 허용치 (0.1을 10번 더하면 0.9999999…가 되는 문제 방지)

LOW_GAUGE_LIMIT = 30        # 이 값 미만이면 막대가 빨간색, 체력은 다크서클 (최댓값과 상관없이 30)

# 디버프 (기획서 2절 "디버프와 버프"): 게이지가 LOW_GAUGE_LIMIT(30) 미만인 동안 붙는다
DEBUFF_TIRED = "피곤"           # 체력 30 미만: 공부 지식 x0.7
DEBUFF_DEPRESSED = "우울"       # 멘탈 30 미만: 버는 연구비 x0.7
TIRED_KNOWLEDGE_RATIO = 0.7     # 피곤일 때 공부 지식 배수 (보너스·방침 배수 다음에 곱한다)
DEPRESSED_MONEY_RATIO = 0.7     # 우울일 때 지식으로 버는 연구비 배수

# 버프 '든든함' (기획서 2절): 학식을 먹으면 붙는다
BUFF_FULL = "든든함"
FULL_DURATION = 30.0            # 든든함 기본 지속 시간(초, 게임 시간). 다시 먹으면 처음부터 다시 잰다
FULL_HEALTH_DECAY_RATIO = 0.5   # 든든함인 동안 체력 자연 감소 배수

# 버프 '개운함' (기획서 2절, 2026-11-24 추가): 쉬게 하기를 하면 붙는다(든든함의 멘탈 짝)
BUFF_REFRESH = "개운함"
REFRESH_DURATION = 20.0         # 개운함 지속 시간(초, 게임 시간). 다시 쉬면 처음부터 다시 잰다
REFRESH_MENTAL_DECAY_RATIO = 0.5  # 개운함인 동안 멘탈 자연 감소 배수

# 휴식 위주 방침의 "컨디션 좋음" (기획서 2절): 체력·멘탈이 모두 70 이상이면 연구비 +50%
CONDITION_GOOD = "컨디션 좋음"
CONDITION_GOOD_MIN = 70         # 체력·멘탈이 둘 다 이 값 이상이어야 한다

# ---------------------------------------------------------------
# 5. 행동 증감량과 자동 행동 (방치형: 쿨타임 대신 자동 행동 간격)
# ---------------------------------------------------------------
# 학식 먹이기는 게이지를 바로 채우지 않고 버프 '든든함'만 준다(FULL_DURATION)

REST_HEALTH = 15            # 쉬게 하기: 체력 +15
REST_MENTAL = 20            # 쉬게 하기: 멘탈 +20
REST_KNOWLEDGE = -2         # 쉬게 하기: 지식 -2

STUDY_HEALTH = -5           # 공부시키기: 체력 -5
STUDY_MENTAL = -8           # 공부시키기: 멘탈 -8
STUDY_KNOWLEDGE = 10        # 공부시키기: 지식 +10
STUDY_KNOWLEDGE_EXAM = 20   # 시험 기간 공부시키기: 지식 +20

# 방치형(기획서 2절 "자동 행동과 일과표 방침"): 쿨타임 없이 제자가 이 간격마다 스스로 행동한다.
AUTO_ACTION_INTERVAL = 2.0  # 자동 행동 간격(초, 게임 시간). 게임 시작 후 첫 행동도 2초 뒤

# 일과표 방침 이름 (Game.set_policy 에 넘기는 값)
POLICY_STUDY_FOCUS = "study_focus"  # 공부 위주
POLICY_BALANCED = "balanced"        # 균형
POLICY_REST_FOCUS = "rest_focus"    # 휴식 위주
POLICY_START = POLICY_BALANCED      # 새 게임의 시작 방침
POLICY_ORDER = [POLICY_STUDY_FOCUS, POLICY_BALANCED, POLICY_REST_FOCUS]  # 버튼·키 1/2/3 순서

# 방침 사전의 키
POLICY_THRESHOLD = "threshold"            # 회복 기준: 체력이나 멘탈이 이 값 미만이면 휴식한다
POLICY_KNOWLEDGE_RATIO = "knowledge_ratio"  # 공부 지식 배수
POLICY_COST_RATIO = "cost_ratio"          # 공부 체력·멘탈 소모 배수
POLICY_REST_RATIO = "rest_ratio"          # 휴식 체력·멘탈 회복 배수 (보너스 포함 회복량에 곱한다)
POLICY_CONDITION_BONUS = "condition_bonus"  # 컨디션 좋음(체력·멘탈 70 이상)일 때 연구비에 더하는 비율
POLICY_TEXT = "text"                      # 방침 버튼 글자

# 방침 3가지 (기획서 2절 방침 표)
POLICIES = {
    POLICY_STUDY_FOCUS: {POLICY_THRESHOLD: 25, POLICY_KNOWLEDGE_RATIO: 1.8,
                         POLICY_COST_RATIO: 1.8, POLICY_REST_RATIO: 1.0,
                         POLICY_CONDITION_BONUS: 0.0, POLICY_TEXT: "공부 위주 [1]"},
    POLICY_BALANCED: {POLICY_THRESHOLD: 50, POLICY_KNOWLEDGE_RATIO: 1.0,
                      POLICY_COST_RATIO: 1.0, POLICY_REST_RATIO: 1.0,
                      POLICY_CONDITION_BONUS: 0.0, POLICY_TEXT: "균형 [2]"},
    POLICY_REST_FOCUS: {POLICY_THRESHOLD: 70, POLICY_KNOWLEDGE_RATIO: 0.7,
                        POLICY_COST_RATIO: 0.7, POLICY_REST_RATIO: 1.5,
                        POLICY_CONDITION_BONUS: 0.5, POLICY_TEXT: "휴식 위주 [3]"},
}
NO_RATIO = 1.0              # 배수를 곱하지 않을 때의 값(×1.0). Student.study 의 기본값

# ---------------------------------------------------------------
# 6. 표정 기준
# ---------------------------------------------------------------
MENTAL_SMILE_MIN = 60       # 멘탈이 이 값 이상이면 웃는 입
MENTAL_FLAT_MIN = 30        # 멘탈이 이 값 이상(60 미만)이면 일자 입, 미만이면 우는 입

# ---------------------------------------------------------------
# 7. 캐릭터 크기
# ---------------------------------------------------------------
BASE_RADIUS = 40            # 1학년 반지름
RADIUS_PER_GRADE = 10       # 학년이 오를 때마다 늘어나는 반지름
GLASSES_GRADE = 3           # 이 학년부터 안경을 쓴다

# 표정 이름 (Student.get_mouth 가 돌려주는 값)
MOUTH_SMILE = "smile"       # 웃는 입 (입꼬리가 올라간 U자)
MOUTH_FLAT = "flat"         # 일자 입 (가로 한 줄)
MOUTH_CRY = "cry"           # 우는 입 (입꼬리가 내려간 ∩자)

# ---------------------------------------------------------------
# 8. 엔딩 기준
# ---------------------------------------------------------------
# 진급과 졸업 (기획서 2절): 누적 지식이 목표 "이상"이 되면 진급한다. 학년은 내려가지 않는다.
GRADE_GOALS = [400, 900, 1500]  # 2학년·3학년·4학년 진급 목표(누적 지식)
GRADUATION_KNOWLEDGE = 2200     # 4학년에서 누적 지식 2200 이상이면 졸업
# 졸업 등급은 졸업까지 걸린 게임 시간(대화창 정지 시간은 빼고 센다)으로 정한다.
# (밸런스 B안, 2026-11-24: 업그레이드를 모아 4번째 판쯤 첫 수석, 업그레이드 없는 첫 판은 무사)
TOP_GRADUATE_SECONDS = 330      # 330초 이하: 수석 졸업
NORMAL_GRADUATE_SECONDS = 720   # 330초 초과 720초 이하: 무사 졸업, 초과: 아슬아슬 졸업

ENDING_LEAVE = "휴학"
ENDING_TOP = "수석 졸업"
ENDING_NORMAL = "무사 졸업"
ENDING_BARELY = "아슬아슬 졸업"

# ---------------------------------------------------------------
# 9. 최고 기록
# ---------------------------------------------------------------
RECORD_FILENAME = "record.json"  # 최고 기록을 저장할 파일 이름
RECORD_KEY = "best_knowledge"    # record.json 안에서 최고 지식을 담는 키: {"best_knowledge": 520}
RECORD_ENCODING = "utf-8"        # record.json 을 읽고 쓸 때 쓰는 글자 인코딩
# 방치형(기획서 3절·9절): 최고 기록과 함께 연구비·명성·업그레이드 레벨도 저장한다
# {"best_knowledge": 520, "money": 340, "fame": 0, "upgrades": {"menu": 1, ...}}
# 예전 형식({"best_knowledge": n})이나 깨진 파일도 읽을 수 있고, 없는 값은 0으로 본다.
RECORD_MONEY_KEY = "money"       # 연구비
RECORD_FAME_KEY = "fame"         # 명성
RECORD_UPGRADES_KEY = "upgrades"  # 업그레이드 레벨 {업그레이드 id: 레벨}


def get_base_dir():
    """record.json을 저장할 폴더를 돌려준다."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


RECORD_PATH = os.path.join(get_base_dir(), RECORD_FILENAME)  # 최고 기록 파일 전체 경로

# ---------------------------------------------------------------
# 10. 도트(픽셀) 스타일과 색 팔레트 (R, G, B) - 파스텔 레트로
# ---------------------------------------------------------------
PIXEL_SIZE = 4                  # 도트 1칸 = 4 x 4 픽셀
BOX_INSET = PIXEL_SIZE * 2      # 상자 안쪽이 바깥보다 가로·세로로 작아지는 양(양쪽 1칸씩)
NO_OFFSET = 0                   # 옮기거나 늘이지 않는 방향의 값 (rect.move / inflate 에 쓴다)
FIRST_ROW = 0                   # 스프라이트 격자의 첫 줄 번호

COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_OUTLINE = (46, 42, 82)            # 진한 남색 외곽선 (모든 도트 상자·스프라이트 테두리)
COLOR_TEXT = COLOR_OUTLINE              # 기본 글자 색 (남색)
COLOR_TEXT_SOFT = (108, 100, 140)       # 안내 문구처럼 덜 중요한 글자 색

COLOR_BACKDROP = (240, 228, 208)        # 창 전체 배경 (조금 진한 크림)
COLOR_BACKDROP_DOT = (232, 218, 196)    # 배경에 은은하게 찍는 도트 무늬 색
COLOR_BG = (253, 248, 236)              # 크림 배경 (패널·제자 무대 안쪽)
COLOR_PANEL_LIGHT = (255, 253, 246)     # 패널 위 하이라이트 줄
COLOR_PANEL_SHADOW = (238, 226, 206)    # 패널 아래 그림자 줄
COLOR_DROP = (218, 202, 178)            # 상자 아래로 깔리는 그림자(1칸)
COLOR_STAGE_SHADOW = (234, 222, 200)    # 제자 발밑 그림자

# 포인트 색 (민트·하늘·살구·연분홍·노랑)
COLOR_MINT = (168, 226, 204)
COLOR_MINT_LIGHT = (206, 242, 228)
COLOR_MINT_DARK = (124, 196, 172)
COLOR_SKY = (150, 202, 240)
COLOR_SKY_LIGHT = (204, 230, 250)
COLOR_SKY_DARK = (92, 150, 210)         # 휴식 파티클(Zzz·구름 그림자)처럼 크림 바탕에서 또렷해야 하는 하늘색
COLOR_APRICOT = (250, 190, 146)
COLOR_PINK = (246, 166, 188)
COLOR_PINK_LIGHT = (253, 214, 224)
COLOR_PINK_DARK = (222, 120, 150)
COLOR_YELLOW = (255, 220, 104)          # 시험 기간 배너 색 (노랑)
COLOR_YELLOW_LIGHT = (255, 238, 170)
COLOR_YELLOW_DARK = (232, 184, 64)

# 게이지 막대: 30 미만 빨강 / 30 이상 초록 (확실히 구분되는 색)
COLOR_GREEN = (88, 196, 120)            # 정상 게이지 채움
COLOR_GREEN_LIGHT = (150, 228, 166)     # 채움 위 하이라이트 줄
COLOR_GREEN_DARK = (56, 152, 92)        # 채움 아래 그림자 줄
COLOR_RED = (232, 82, 90)               # 30 미만 게이지 채움
COLOR_RED_LIGHT = (250, 150, 150)
COLOR_RED_DARK = (178, 50, 70)
COLOR_BAR_BG = (232, 222, 208)          # 게이지 막대의 빈 부분 색
COLOR_BAR_BG_SHADE = (216, 204, 188)    # 빈 부분 맨 위 줄(안쪽 그림자)

# 버튼: 평소 하늘색, 밝은색(마우스 올림용), 회색(대화창 입력 대기)
COLOR_BUTTON = (130, 188, 238)          # 평소 버튼 몸통
COLOR_BUTTON_LIGHT = (196, 226, 252)    # 버튼 위 하이라이트 줄
COLOR_BUTTON_DARK = (92, 146, 206)      # 버튼 아래 그림자 줄
COLOR_BUTTON_BRIGHT = (200, 234, 255)   # 밝은 버튼 몸통 (마우스를 올렸을 때 쓸 색, 평소색과 한눈에 구분)
COLOR_BUTTON_TEXT = COLOR_OUTLINE       # 버튼 글자 색
COLOR_GRAY = (184, 182, 194)            # 회색 버튼 몸통 (입력 대기 중)
COLOR_GRAY_LIGHT = (214, 212, 222)
COLOR_GRAY_DARK = (148, 146, 162)
COLOR_BUTTON_TEXT_COOL = (78, 74, 104)  # 회색 버튼 글자 색 (회색 몸통 위에서도 읽히게 진하게)

COLOR_INFO_BAR = COLOR_MINT             # 상단 정보바 몸통

# 제자 스프라이트 색
COLOR_SKIN = (255, 216, 180)            # 얼굴(피부)
COLOR_SKIN_SHADOW = (240, 180, 150)     # 얼굴 아래쪽 그림자
COLOR_HAIR = (104, 74, 92)              # 머리카락
COLOR_HAIR_LIGHT = (150, 112, 128)      # 머리카락 윤기
COLOR_FACE_LINE = COLOR_OUTLINE         # 눈·입·안경 색
COLOR_DARK_CIRCLE = (150, 112, 180)     # 다크서클(보라)
COLOR_BLUSH = (248, 160, 172)           # 볼 홍조
COLOR_GLASS = (208, 230, 250)           # 안경알 유리(아주 연한 하늘색)

# 학사모 색
COLOR_CAP = (72, 66, 118)               # 학사모 몸통(짙은 남보라)
COLOR_CAP_LIGHT = (108, 102, 156)       # 학사모 윗면 밝은 부분
COLOR_CAP_DARK = (52, 46, 92)           # 학사모 띠 아래 그림자
COLOR_TASSEL = (244, 194, 72)           # 술(금색)
COLOR_TASSEL_DARK = (204, 146, 44)      # 술 끝 그림자

# 휴학 엔딩 비구름 색
COLOR_CLOUD = (228, 226, 238)           # 구름
COLOR_CLOUD_SHADE = (196, 192, 214)     # 구름 아래 그림자

# 배경 도트 무늬: STEP 간격마다 도트 1칸
BACKDROP_DOT_START = 8      # 첫 도트의 x, y
BACKDROP_DOT_STEP = 16      # 도트 사이 간격(픽셀)

# ---------------------------------------------------------------
# 11. 도트 스프라이트 (문자열 격자: 글자 1개 = 도트 1칸, "." = 투명)
# ---------------------------------------------------------------
# 제자 얼굴: 20 x 20 칸. 칸 크기 = 반지름 // FACE_CELL_DIVISOR -> 4/5/6/7 픽셀이라
# 얼굴 지름 = 20칸 x 칸 크기 = 80/100/120/140 = 2 x 반지름(40/50/60/70).
# O 외곽선, h 머리카락, k 머리 윤기, S 피부, D 피부 그림자
FACE_SPRITE = [
    "......OOOOOOOO......",
    "....OOhhhhhhhhOO....",
    "...OhhhkkhhhhhhhO...",
    "..OhhhkkhhhhhhhhhO..",
    ".OhhhkhhhhhhhhhhhhO.",
    ".OhhhhhhhhhhhhhhhhO.",
    "OhhhhhhhhhhhhhhhhhhO",
    "OhhSShhhSSSShhhSShhO",
    "OhSSSSSSSSSSSSSSSShO",
    "OSSSSSSSSSSSSSSSSSSO",
    "OSSSSSSSSSSSSSSSSSSO",
    "OSSSSSSSSSSSSSSSSSSO",
    "OSSSSSSSSSSSSSSSSSSO",
    "OSSSSSSSSSSSSSSSSSDO",
    ".OSSSSSSSSSSSSSSSDO.",
    ".OSSSSSSSSSSSSSSSDO.",
    "..ODSSSSSSSSSSSSDDO.",
    "...ODDSSSSSSSSDDO...",
    "....OODDDDDDDDOO....",
    "......OOOOOOOO......",
]
FACE_GRID_SIZE = len(FACE_SPRITE)           # 얼굴 격자 칸 수(20)
FACE_CELL_DIVISOR = FACE_GRID_SIZE // 2     # 칸 크기 = 반지름 // 이 값

# 얼굴 위에 덧그리는 부품: (열, 행) 위치와 격자. 위치는 얼굴 격자 기준 칸 번호.
# E 눈·입(남색), W 눈 반짝임(흰색), C 다크서클, P 볼 홍조, G 안경테, L 안경알 유리
EYE_SPRITE = ["WE", "EE"]
EYE_POSITIONS = [(5, 9), (13, 9)]           # 왼눈, 오른눈 (각 2 x 2칸)
BLUSH_SPRITE = ["PP"]
BLUSH_POSITIONS = [(2, 12), (16, 12)]       # 양쪽 볼
DARK_CIRCLE_SPRITE = ["CC"]
DARK_CIRCLE_POSITIONS = [(5, 12), (13, 12)]  # 눈 바로 아래 (안경알 아래)
GLASSES_LENS_SPRITE = [     # 둥근 안경알 6 x 4칸: 테두리 + 양옆 유리, 가운데 2칸(눈 자리)은 투명
    ".GGGG.",
    "GL..LG",
    "GL..LG",
    ".GGGG.",
]
GLASSES_PARTS = [
    ((3, 8), GLASSES_LENS_SPRITE),          # 왼쪽 안경알 (눈을 둘러쌈)
    ((11, 8), GLASSES_LENS_SPRITE),         # 오른쪽 안경알
    ((9, 9), ["GG"]),                       # 가운데 다리 (두 눈 사이)
    ((1, 9), ["GG"]),                       # 왼쪽 다리 (얼굴 끝까지)
    ((17, 9), ["GG"]),                      # 오른쪽 다리
]
# 입: 표정 이름 -> ((열, 행), 격자)
MOUTH_SPRITES = {
    MOUTH_SMILE: ((7, 14), ["E....E", ".EEEE."]),  # 입꼬리가 올라간 웃는 입
    MOUTH_FLAT: ((8, 15), ["EEEE"]),               # 일자 입
    MOUTH_CRY: ((7, 14), [".EEEE.", "E....E"]),    # 입꼬리가 내려간 우는 입
}
FACE_COLORS = {
    "O": COLOR_OUTLINE, "h": COLOR_HAIR, "k": COLOR_HAIR_LIGHT,
    "S": COLOR_SKIN, "D": COLOR_SKIN_SHADOW,
    "E": COLOR_FACE_LINE, "W": COLOR_WHITE, "C": COLOR_DARK_CIRCLE,
    "P": COLOR_BLUSH, "G": COLOR_FACE_LINE, "L": COLOR_GLASS,
}

# 학사모: 49 x 25칸, 칸 크기 CAP_PIXEL. 윗판(납작한 마름모) + 띠 + 금색 술
# O 외곽선, l 윗판 밝은 면, c 몸통, d 띠 그림자, Y 술, t 술 끝 그림자
CAP_SPRITE = [
    "........................O........................",
    "....................OOOOlOOOO....................",
    "................OOOOlllllllllOOOO................",
    "............OOOOlllllllllllllllllOOOO............",
    "........OOOOlllllllllllllllllllllllllOOOO........",
    "....OOOOllllllllllllllllYllllllllllllllllOOOO....",
    "OOOOccccccccccccccccccccYYYYYYYYYYYYYYYYYYYYYOOOO",
    "....OOOOcccccccccccccccccccccccccccccccccOOOY....",
    "........OOOOcccccccccccccccccccccccccOOOO...Y....",
    "............OOOOcccccccccccccccccOOOO.......Y....",
    ".............OllOOOOcccccccccOOOOccO........Y....",
    ".............OllccccOOOOcOOOOccccccO........Y....",
    ".............OllccccccccOccccccccccO........Y....",
    ".............OllcccccccccccccccccccO........Y....",
    ".............OllcccccccccccccccccccO........Y....",
    ".............OllcccccccccccccccccccO........Y....",
    ".............OllcccccccccccccccccccO........Y....",
    ".............OdddddddddddddddddddddO........Y....",
    ".............OdddddddddddddddddddddO........Y....",
    ".............OOOOOOOOOOOOOOOOOOOOOOO........Y....",
    "...........................................YYY...",
    "...........................................YYY...",
    "...........................................YYY...",
    "...........................................YYY...",
    "...........................................ttt...",
]
CAP_COLORS = {
    "O": COLOR_OUTLINE, "l": COLOR_CAP_LIGHT, "c": COLOR_CAP, "d": COLOR_CAP_DARK,
    "Y": COLOR_TASSEL, "t": COLOR_TASSEL_DARK,
}

# 휴학 엔딩 장식: 비구름 (학사모 자리에 대신 찍는다). 25 x 20칸, 칸 크기 CLOUD_PIXEL
# O 외곽선, w 구름, W 구름 반짝임, g 구름 아래 그림자, r 빗방울
CLOUD_SPRITE = [
    "...........OOO...........",
    ".........OOwwwOO.........",
    "........OwWWwwwwO........",
    ".......OwWwwwwwwwO.......",
    "....OOOwwwwwwwwwwwOOO....",
    "..OOwwwwwwwwwwwwwwwwwOO..",
    ".OwwwwwwwwwwwwwwwwwwwwwO.",
    ".OwwwwwwwwwwwwwwwwwwwwwO.",
    "OwwwwwwwwwwwwwwwwwwwwwwwO",
    "OwwwwwwwwwwwwwwwwwwwwwwwO",
    "OgggggggggggggggggggggggO",
    ".OgggggggggggggggggggggO.",
    "..OOOOOOOOOOOOOOOOOOOOO..",
    ".........................",
    ".....r.........r.........",
    ".....r.........r.........",
    "..........r.........r....",
    "..........r.........r....",
    ".......r.........r.......",
    ".......r.........r.......",
]
CLOUD_COLORS = {
    "O": COLOR_OUTLINE, "w": COLOR_CLOUD, "W": COLOR_WHITE,
    "g": COLOR_CLOUD_SHADE, "r": COLOR_SKY,
}

# 작은 아이콘·장식 (칸 크기 PIXEL_SIZE)
HEART_SPRITE = [            # 체력 아이콘: 하트
    ".OO.OO.",
    "OWpOppO",
    "OpppppO",
    ".OpppO.",
    "..OpO..",
    "...O...",
]
HEART_COLORS = {"O": COLOR_OUTLINE, "p": COLOR_PINK, "W": COLOR_WHITE}
STAR_SPRITE = [             # 멘탈 아이콘·화면 장식: 반짝이는 별
    "...x...",
    "...x...",
    "..xxx..",
    "xxxxxxx",
    "..xxx..",
    "...x...",
    "...x...",
]
SPRITE_INK = "x"            # 한 가지 색으로 칠하는 스프라이트의 글자
ARROW_SPRITE = [            # 시작·다시 하기 안내 앞의 화살표
    "x...",
    "xx..",
    "xxx.",
    "xx..",
    "x...",
]
EXCLAIM_SPRITE = [          # 시험 기간 배너 양옆 느낌표
    "xx",
    "xx",
    "xx",
    "xx",
    "..",
    "xx",
]

# ---------------------------------------------------------------
# 12. 게임 화면 배치 - 글자 크기, 상단 정보바, 패널
# ---------------------------------------------------------------
FONT_SIZE = 22              # 기본 글자 크기
ORIGIN = (0, 0)             # 창 왼쪽 위 꼭짓점. 사각형을 만든 뒤 center 등으로 옮길 때 임시 위치로도 쓴다
SCREEN_CENTER_X = SCREEN_WIDTH // 2  # 화면 가운데 x
HALF = 2                    # 절반을 구할 때 나누는 값

# 상단 정보바: 왼쪽 "N학년", 그 오른쪽 "다음 학년까지 지식 N", 오른쪽 "연구비 N  지식 N" (Game이 그린다)
INFO_BOX_X = 12             # 정보바 상자 왼쪽 x
INFO_BOX_Y = 8              # 정보바 상자 위쪽 y
INFO_BOX_WIDTH = SCREEN_WIDTH - INFO_BOX_X * 2  # 정보바 상자 가로 길이(좌우 여백 같게)
INFO_BOX_HEIGHT = 44        # 정보바 상자 세로 길이
INFO_BAR_HEIGHT = INFO_BOX_Y + INFO_BOX_HEIGHT + PIXEL_SIZE  # 정보바 구역 전체 높이(그림자 포함, 56)
INFO_TEXT_CENTER_Y = INFO_BOX_Y + INFO_BOX_HEIGHT // 2  # 정보바 글자의 세로 가운데
INFO_BAR_MARGIN = 32        # 정보바 글자와 창 가장자리 사이 여백
# 목표 글자의 왼쪽 x. 가장 긴 학년 글자("대학원 12년차", 약 142px)가 32~174를 쓰므로 그 오른쪽에 둔다.
# 가장 긴 목표 글자(약 248px) -> 200~448, 오른쪽 "연구비 12345  지식 1234"(약 250px)는 518부터라 겹치지 않는다
INFO_GOAL_X = 200
GRADE_TEXT = "{}학년"            # 학년 글자 틀
KNOWLEDGE_TEXT = "{} {}"         # 지식 글자 틀: "지식 120"
NEXT_GRADE_TEXT = "다음 학년까지 지식 {}"     # 1~3학년 목표 글자
GRADUATION_GOAL_TEXT = "졸업까지 지식 {}"     # 4학년 목표 글자
NEXT_GRAD_YEAR_TEXT = "다음 년차까지 지식 {}"  # 대학원 목표 글자

# 목표 진행 막대 (정보바 바로 아래 왼쪽, 상태 패널 위). 시험 기간 배너는 그 오른쪽(무대 위)에 뜬다
GOAL_BOX_X = 12             # 목표 상자 왼쪽 x (상태 패널과 같은 줄)
GOAL_BOX_Y = 64             # 목표 상자 위쪽 y (정보바 구역 56 아래)
GOAL_BOX_WIDTH = 256        # 목표 상자 가로 길이 (상태 패널과 같다) -> 오른쪽 끝 268
GOAL_BOX_HEIGHT = 40        # 목표 상자 세로 길이 -> 아래 끝 104 (+그림자 1칸), 패널(116)과 겹치지 않음
GOAL_LABEL_TEXT = "목표"     # 막대 앞 글자
GOAL_LABEL_GAP = 8          # 글자와 막대 사이 간격
GOAL_BAR_PAD = 8            # 상자 안쪽 왼쪽·오른쪽 여백
GOAL_BAR_HEIGHT = 16        # 막대 세로 길이(도트 4칸)
GOAL_PROGRESS_MIN = 0.0     # 진행률 최솟값 (목표 시작점 아래로 지식이 줄면 0)
GOAL_PROGRESS_MAX = 1.0     # 진행률 최댓값

# 경과 시간 ("경과 3분 12초"): 오른쪽 아래, [업그레이드 U] 버튼 밑 (자동 행동 막대와 같은 높이)
ELAPSED_TEXT = "경과 {}"
TIME_TEXT = "{}분 {}초"      # 시간 글자 틀: "3분 12초"

# 가운데 구역: 왼쪽 상태 패널(게이지) + 오른쪽 제자 무대
PANEL_Y = 116               # 두 패널의 위쪽 y (시험 기간 배너 아래)
PANEL_HEIGHT = 344          # 두 패널의 세로 길이 -> 아래 끝 460 (버튼 위)
STATUS_PANEL_X = 12         # 상태 패널 왼쪽 x
STATUS_PANEL_WIDTH = 256    # 상태 패널 가로 길이 -> 오른쪽 끝 268
STAGE_X = 284               # 제자 무대 왼쪽 x
STAGE_WIDTH = 504           # 제자 무대 가로 길이 -> 오른쪽 끝 788, 가운데 536

# 제자 얼굴 중심: 제자 무대의 가운데
STUDENT_CENTER_X = STAGE_X + STAGE_WIDTH // 2    # 536
STUDENT_CENTER_Y = PANEL_Y + PANEL_HEIGHT // 2   # 288
SHADOW_GAP = 8              # 얼굴 아래 끝과 발밑 그림자 사이 간격
SHADOW_HEIGHT = 8           # 발밑 그림자 세로 길이(도트 2칸)
SHADOW_WIDTH_RATIO = 1.2    # 발밑 그림자 가로 길이 = 반지름 x 이 비율

# 왼쪽 게이지 구역: 아이콘 + 라벨("체력"/"멘탈")과 막대. 막대 테두리는 막대 바깥 1칸
GAUGE_X = 40                # 아이콘과 막대의 왼쪽 x (막대 채움이 여기서 시작)
BAR_WIDTH = 200             # 막대 전체 가로 길이(값 100일 때)
BAR_HEIGHT = 24             # 막대 세로 길이(도트 6칸)
HEALTH_LABEL_Y = 200        # 체력 아이콘·라벨 줄의 위쪽 y (게이지 묶음 200~380: 패널 안쪽 위아래 여백 80/76)
HEALTH_BAR_Y = 232          # 체력 막대 위쪽 y
MENTAL_LABEL_Y = 280        # 멘탈 아이콘·라벨 줄의 위쪽 y (특성 배지 4줄 자리를 위해 320 -> 280)
MENTAL_BAR_Y = 312          # 멘탈 막대 위쪽 y (테두리 아래 끝 340)
GAUGE_LABEL_GAP = 8         # 아이콘과 라벨 글자 사이 간격

HEALTH_LABEL = "체력"
MENTAL_LABEL = "멘탈"
KNOWLEDGE_LABEL = "지식"

# ---------------------------------------------------------------
# 13. 방침 버튼 (화면 아래쪽 왼편에 가로로 3개, 오른편은 [업그레이드 U] 자리로 비워 둔다)
# ---------------------------------------------------------------
# 행동 이름 (Game.do_action 에 넘기는 값, Game.choose_auto_action 이 돌려주는 값)
ACTION_FEED = "feed"        # 학식 먹이기
ACTION_REST = "rest"        # 쉬게 하기
ACTION_STUDY = "study"      # 공부시키기

BUTTON_COUNT = 3            # 방침 버튼 개수
BUTTON_WIDTH = 176          # 버튼 하나의 가로 길이
BUTTON_HEIGHT = 52          # 버튼 하나의 세로 길이 (아래 남색 받침 1칸은 별도)
BUTTON_GAP = 16             # 버튼 사이 간격
BUTTON_Y = 476              # 버튼 위쪽 y
BUTTON_START_X = 24         # 첫 버튼의 왼쪽 x
# 방침 버튼 3개가 차지하는 가로 길이: 176*3 + 16*2 = 560 (x 24 ~ 584).
# 오른쪽 x 600 ~ 776 은 [업그레이드 U] 버튼 자리다.
POLICY_AREA_WIDTH = BUTTON_WIDTH * BUTTON_COUNT + BUTTON_GAP * (BUTTON_COUNT - 1)

# 고른 방침 버튼 색: 노랑 계열로 밝게 강조 (평소 하늘색과 한눈에 구분, 반투명 없이)
COLOR_POLICY_SELECTED = (255, 220, 104)        # 몸통 (시험 배너 노랑과 같은 색)
COLOR_POLICY_SELECTED_LIGHT = (255, 238, 170)  # 위 하이라이트 줄
COLOR_POLICY_SELECTED_DARK = (232, 184, 64)    # 아래 그림자 줄

# 버튼 아래 자동 행동 진행 막대 (다음 자동 행동까지 남은 시간)
AUTO_BAR_Y = 540            # 진행 막대 상자 위쪽 y
AUTO_BAR_HEIGHT = 16        # 진행 막대 상자 세로 길이 (외곽선 1칸 + 막대 2칸)
AUTO_HINT_TEXT = "다음 자동 행동까지"   # 진행 막대 아래 안내 문구
AUTO_HINT_Y = 566           # 안내 문구 위쪽 y

# ---------------------------------------------------------------
# 14. 시험 기간 배너 (상단 정보바 바로 아래, 패널 위)
# ---------------------------------------------------------------
EXAM_BANNER_TEXT = "시험 기간! 공부 효과 2배, 멘탈 감소 2배"
EXAM_BANNER_X = 284         # 배너 왼쪽 x (무대와 같은 줄. 왼쪽은 목표 진행 막대 자리)
EXAM_BANNER_Y = 64          # 배너 위쪽 y (정보바 구역 56 아래)
EXAM_BANNER_WIDTH = 504     # 배너 가로 길이 (무대와 같다) -> 오른쪽 끝 788
EXAM_BANNER_HEIGHT = 40     # 배너 세로 길이 -> 아래 끝 104 (+그림자 1칸), 패널(116)과 겹치지 않음
EXAM_ICON_MARGIN = 24       # 배너 양 끝에서 느낌표 아이콘까지 거리

# ---------------------------------------------------------------
# 15. 타이틀·엔딩 화면 (가운데 크림 패널 위에 그린다)
# ---------------------------------------------------------------
TITLE_FONT_SIZE = 64        # 큰 제목 글자 크기
TITLE_SHADOW_OFFSET = 4     # 큰 제목 아래·오른쪽으로 깔리는 그림자 글자 거리
COLOR_TITLE_SHADOW = COLOR_APRICOT  # 큰 제목 그림자 글자 색
MENU_PANEL_RECT = (96, 64, 608, 432)  # 타이틀·엔딩 가운데 패널 (x, y, 가로, 세로)

TITLE_TEXT = "제자 키우기"   # 게임 제목
TITLE_TEXT_Y = 172          # 제목 가운데 y
TITLE_LINE_Y = 232          # 제목 아래 도트 장식 줄의 위쪽 y
TITLE_LINE_DOTS = 23        # 장식 줄의 도트 수(가운데 정렬)
TITLE_LINE_COLORS = [COLOR_PINK, COLOR_APRICOT, COLOR_MINT_DARK, COLOR_SKY]  # 장식 줄 색 순서
BEST_RECORD_TEXT = "최고 기록: 지식 {}"  # 최고 기록 글자 틀
BEST_RECORD_Y = 312         # 최고 기록 가운데 y
BEST_RECORD_START = 0       # 최고 기록 기본값 (record.json 이 없거나 깨졌을 때)
BADGE_PADDING_X = 24        # 글자 배지 상자의 좌우 여백
BADGE_HEIGHT = 48           # 글자 배지 상자의 세로 길이
START_HINT_TEXT = "Enter를 눌러 시작"
START_HINT_Y = 408          # 시작 안내 가운데 y
HINT_ARROW_GAP = 12         # 안내 글자와 앞 화살표 사이 간격

# 새 게임(N): 타이틀 시작 안내 아래 둘째 줄 안내, 진행이 있으면 확인 상자(기획서 5·6절)
NEW_GAME_HINT_TEXT = "Enter 이어하기 · N 새 게임 (처음부터)"
NEW_GAME_HINT_Y = 448       # 둘째 줄 가운데 y (시작 안내 408 아래, 패널 아래 끝 496 안)
NEW_GAME_CONFIRM_RECT = (148, 382, 504, 104)  # 확인 상자 (x, y, 가로, 세로): 시작 안내 자리를 덮음
NEW_GAME_CONFIRM_TITLE = "새 게임을 시작할까요?"
NEW_GAME_CONFIRM_TITLE_Y = 406      # 확인 상자 첫 줄 가운데 y
NEW_GAME_CONFIRM_WARNING = "업그레이드·연구비·명성이 모두 사라져요"  # 최고 기록은 남는다(기획서 3절)
NEW_GAME_CONFIRM_WARNING_Y = 436    # 둘째 줄(경고) 가운데 y, 대화창 글자 크기
NEW_GAME_CONFIRM_KEYS = "Y: 시작 · N 또는 Backspace: 취소"
NEW_GAME_CONFIRM_KEYS_Y = 462       # 셋째 줄(키 안내) 가운데 y
NEW_GAME_CONFIRM_BOX = (COLOR_PINK_LIGHT, COLOR_WHITE, COLOR_PINK)  # 확인 상자 (몸통, 위 하이라이트, 아래 그림자)
COLOR_NEW_GAME_WARNING = COLOR_RED_DARK  # 경고 글자 색

# 장식 별: (x, y, 색). 별 하나는 7 x 7칸 x PIXEL_SIZE = 28 x 28 픽셀
TITLE_STARS = [
    (140, 104, COLOR_PINK), (628, 116, COLOR_SKY),
    (168, 388, COLOR_MINT_DARK), (604, 376, COLOR_APRICOT),
    (128, 228, COLOR_APRICOT), (644, 232, COLOR_PINK),
]
ENDING_STARS = [
    (232, 204, COLOR_PINK), (540, 192, COLOR_SKY),
    (192, 272, COLOR_APRICOT), (584, 264, COLOR_MINT_DARK),
]

ENDING_NAME_Y = 136         # 엔딩 이름 가운데 y
ENDING_KNOWLEDGE_TEXT = "누적 지식 {}"  # 누적 지식 글자 틀
ENDING_KNOWLEDGE_Y = 356    # 누적 지식 가운데 y
ENDING_TIME_TEXT = "졸업까지 {}"   # 졸업 엔딩에서 걸린 시간 글자 틀: "졸업까지 3분 52초"
ENDING_TIME_Y = 320         # 걸린 시간 가운데 y (학사모 아래 끝 296과 누적 지식 배지 사이)
RESTART_HINT_TEXT = "R을 눌러 다시 하기"
RESTART_HINT_Y = 428        # 다시 하기 안내 가운데 y

# 휴학 엔딩 비구름 위치·크기
CLOUD_PIXEL = 5             # 비구름 도트 1칸 크기 -> 125 x 100 픽셀
CLOUD_TOP_Y = 200           # 비구름 위쪽 y -> 아래 끝 300 (누적 지식 배지 위)

# 학사모 (졸업 엔딩일 때만): CAP_SPRITE를 칸 크기 CAP_PIXEL로 찍는다 (196 x 100 픽셀)
CAP_PIXEL = PIXEL_SIZE      # 학사모 도트 1칸 크기(4)
CAP_TOP_Y = 196             # 학사모 위쪽 y -> 아래 끝 296 (누적 지식 배지 위)

# ---------------------------------------------------------------
# 16. 상호작용 효과 E1~E6 (기획서·jeja-spec 6절 "화면 연출"). 보기만 바꾸고 게임 결과에는 영향이 없다
# ---------------------------------------------------------------
FULL_RATIO = 1.0            # 진행률·비율의 끝값(100%). 진행률 p 의 나머지 = FULL_RATIO - p
NO_CHANGE = 0               # 게이지 변화량이 0 (늘지도 줄지도 않음)
BLINK_SHOW = 0              # 깜빡임 차례 번호 % 2 가 이 값이면 "보임"
BLINK_HIDE = 1              # 깜빡임 차례 번호 % 2 가 이 값이면 "숨김"

# E1 버튼 호버·눌림·진행 막대 (자동 행동 막대, 대화창 입력 대기 막대)
BUTTON_PRESS_OFFSET = 4     # 행동이 실행되면 버튼이 내려가는 거리(픽셀) = 받침 1칸
BUTTON_PRESS_TIME = 0.12    # 버튼이 눌린 채로 있는 시간(초)
COOLDOWN_BAR_HEIGHT = PIXEL_SIZE * 2   # 진행 막대 세로 길이(도트 2칸, 상자 안쪽 맨 아래)
COLOR_COOLDOWN_TRACK = COLOR_GRAY_DARK  # 진행 막대의 아직 안 찬 부분
COLOR_COOLDOWN_FILL = COLOR_BUTTON      # 진행 막대의 찬 부분 (하늘색)

# E2 행동별 파티클 (random 대신 정해진 표를 차례로 쓴다)
PARTICLE_COUNT = 10         # 행동 한 번에 나오는 파티클 수 (8~12개)
# 퍼지는 방향 (가로, 세로). 세로가 음수면 위쪽. 길이가 대략 1인 방향 표
# 머리 위는 수치 팝업 글자 자리라서 위쪽으로 가는 방향은 쓰지 않는다:
# 옆(살짝 위 포함)과 비스듬한 아래로만 왼쪽·오른쪽 번갈아 퍼진다
PARTICLE_DIRECTIONS = [
    (-1.0, -0.2), (1.0, -0.2), (-0.9, 0.4), (0.9, 0.4), (-0.6, 0.8),
    (0.6, 0.8), (-0.95, -0.35), (0.95, -0.35), (-0.8, 0.6), (0.8, 0.6),
]
PARTICLE_SPEEDS = [60, 80, 50, 70, 75]      # 퍼지는 속도(픽셀/초), 차례로 돌려 쓴다
PARTICLE_LIFETIMES = [0.6, 0.7, 0.8]        # 파티클 수명(초), 차례로 돌려 쓴다
PARTICLE_RISE_SPEED = 40    # 모든 파티클이 함께 위로 떠오르는 속도(픽셀/초)
PARTICLE_START_RATIO = 1.1  # 파티클이 생기는 거리 = 반지름 x 이 비율 (얼굴 가장자리 바로 바깥)
PARTICLE_SHRINK_RATIO = 0.65  # 수명의 이 비율이 지나면 도트가 반 크기로 줄어들며 사라진다

# 파티클 도트 스프라이트 (칸 크기 PIXEL_SIZE)
PARTICLE_HEART = [          # 학식: 하트
    "xx.xx",
    "xwxxx",
    "xxxxx",
    ".xxx.",
    "..x..",
]
PARTICLE_RICE = [           # 학식: 밥알 (흰색은 크림 바탕에서 안 보이므로 남색 테두리)
    ".OO.",
    "OWWO",
    ".OO.",
]
PARTICLE_ZZZ = [            # 휴식: Z
    "xxxx",
    "..x.",
    ".x..",
    "xxxx",
]
PARTICLE_CLOUD = [          # 휴식: 작은 구름
    "..ll..",
    ".lxxx.",
    "xxxxxx",
    "dddddd",
]
PARTICLE_STAR = [           # 공부: 반짝이 별
    "..d..",
    ".dyd.",
    "dyyyd",
    ".dyd.",
    "..d..",
]
PARTICLE_PENCIL = [         # 공부: 연필 (분홍 지우개, 노란 몸통, 남색 심)
    "...pp",
    "..yyp",
    ".yyy.",
    "Oyy..",
    "OO...",
]
# 행동 이름 -> [(스프라이트, 색 사전), ...]. 파티클 번호 순서대로 번갈아 쓴다
PARTICLE_KINDS = {
    ACTION_FEED: [
        (PARTICLE_HEART, {"x": COLOR_PINK_DARK, "w": COLOR_PINK_LIGHT}),
        (PARTICLE_RICE, {"O": COLOR_OUTLINE, "W": COLOR_WHITE}),
    ],
    ACTION_REST: [
        (PARTICLE_ZZZ, {"x": COLOR_SKY_DARK}),
        (PARTICLE_CLOUD, {"x": COLOR_SKY, "l": COLOR_SKY_LIGHT, "d": COLOR_SKY_DARK}),
    ],
    ACTION_STUDY: [
        (PARTICLE_STAR, {"y": COLOR_YELLOW, "d": COLOR_YELLOW_DARK}),
        (PARTICLE_PENCIL, {"p": COLOR_PINK, "y": COLOR_YELLOW_DARK, "O": COLOR_OUTLINE}),
    ],
}

# E3 수치 팝업 ("체력 +20")
POPUP_FONT_SIZE = 18        # 팝업 글자 크기
POPUP_FONT_BOLD = True      # 팝업은 굵은 글씨 (가는 획은 그림자에 묻혀 안 읽힌다)
POPUP_TEXT = "{} {:+d}"     # 팝업 글자 틀: 라벨 + 부호 붙은 변화량
POPUP_TIME = 0.8            # 팝업이 보이는 시간(초)
POPUP_RISE_SPEED = 15       # 팝업이 떠오르는 속도(픽셀/초) -> 0.8초에 12픽셀
POPUP_LINE_HEIGHT = 22     # 팝업 여러 개를 세로로 쌓을 때 줄 간격
POPUP_HEAD_GAP = 0          # 제자 머리(점프·숨쉬기 최고점)와 맨 아래 팝업 글자 상자 사이 간격
                            # (글자 상자 안에 위아래 여백이 있어 0이어도 머리와 닿지 않는다)
POPUP_BLINK_START = 0.5     # 이 시각(초)부터 깜빡이며 사라진다
POPUP_BLINK_STEP = 0.075    # 깜빡임 한 번(보임 또는 숨김)의 길이(초)
POPUP_OUTLINE_OFFSETS = [(2, 1), (1, 2), (2, 2)]  # 남색 그림자 글자를 찍을 위치(오른쪽·아래 2픽셀)
# 크림색 테두리 글자를 찍을 위치(사방 1픽셀). 남색 밤하늘 위에서도 글자 둘레가 밝게 보이고,
# 밝은 낮 하늘 위에서는 남색 그림자가 글자를 받쳐 준다(반투명 없이 어떤 하늘에서도 읽힌다)
POPUP_RIM_OFFSETS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
COLOR_POPUP_RIM = (255, 250, 236)   # 팝업 글자 테두리 색(크림)
COLOR_POPUP_UP = COLOR_GREEN        # 늘어난 값 글자 색
COLOR_POPUP_DOWN = COLOR_RED        # 줄어든 값 글자 색

# E4 게이지 부드러운 변화
GAUGE_ANIM_TIME = 0.25      # 행동으로 바뀐 막대 길이가 새 값을 따라가는 시간(초)
GAUGE_HEALTH = "health"     # Student 의 체력 속성 이름 (표시값 사전의 키)
GAUGE_MENTAL = "mental"     # Student 의 멘탈 속성 이름
GAUGE_KNOWLEDGE = "knowledge"  # Student 의 지식 속성 이름
GAUGE_NAMES = [GAUGE_HEALTH, GAUGE_MENTAL]   # 막대가 있어서 부드럽게 움직이는 게이지
# 게이지 속성 이름 -> 그 최댓값 속성 이름 (Student.max_health / max_mental)
GAUGE_MAX_NAMES = {GAUGE_HEALTH: "max_health", GAUGE_MENTAL: "max_mental"}
# 수치 팝업을 띄울 게이지와 라벨 (위에서부터 이 순서로 쌓인다)
POPUP_GAUGES = [(GAUGE_HEALTH, HEALTH_LABEL), (GAUGE_MENTAL, MENTAL_LABEL),
                (GAUGE_KNOWLEDGE, KNOWLEDGE_LABEL)]

# E5 제자 반응 (점프·숨쉬기). 높이는 PIXEL_SIZE 단위로 끊어 도트 느낌을 낸다
JUMP_TIME = 0.3             # 점프 한 번 시간(초)
JUMP_HEIGHT = 8             # 점프 최고 높이(픽셀)
JUMP_CURVE = 4              # 포물선 4 x p x (1 - p) 의 4: 가운데(p=0.5)에서 1이 된다
BREATH_PERIOD = 1.5         # 숨쉬기 한 주기(초)
BREATH_HEIGHT = 4           # 숨쉬기 최고 높이(픽셀)
SHADOW_SHRINK_PER_LIFT = 1  # 제자가 1픽셀 뜰 때마다 발밑 그림자 가로가 줄어드는 양(픽셀)

# E6 안내 문구 깜빡임: 화살표가 보였다 숨었다 하고, 숨을 때 글자 색이 살짝 옅어진다
BLINK_INTERVAL = 0.5        # 깜빡임 간격(초)
COLOR_HINT_DIM = COLOR_TEXT_SOFT   # 화살표가 숨었을 때의 안내 글자 색

# ---------------------------------------------------------------
# 17. 랜덤 이벤트와 성장 (기획서·jeja-spec 4절)
# ---------------------------------------------------------------
# 발생 규칙 수치
EVENT_CHANCE = 0.25                 # 행동이 실제로 실행된 직후 이벤트가 뜰 확률
EVENT_GUARANTEE_INTERVAL = 11.25    # 최소 보장 구간 길이(초): 60초 주기 안 0~45초를 4구간으로 나눈다
# (이름은 _PER_GRADE지만 값은 60초 주기당 횟수다)
EVENT_MIN_PER_GRADE = 4             # 주기당 최소 보장 이벤트 수 (보장 구간 개수)
EVENT_MAX_PER_GRADE = 5             # 주기당 최대 이벤트 수
EVENT_CHOICE_RATIO = 0.5            # 선택지형 후보가 있을 때 선택지형을 고를 확률
EVENT_NOTICE_TIME = 2.0             # 자동형 알림 배너가 보이는 시간(초)
# 최소 간격: 확률로 뜨는 이벤트는 직전 이벤트(같은 판, 주기·학년이 바뀌어도 이어서 셈) 이후
# 게임 시간이 이만큼 지나야 뜰 수 있다. 최소 보장으로 뜨는 이벤트는 예외.
# 대화창이 떠 있는 동안은 게임 시간이 멈추므로 간격에 들어가지 않는다.
EVENT_MIN_GAP = 8.0

# 이벤트 종류
EVENT_KIND_AUTO = "auto"            # 자동형(작은 사건): 게임이 멈추지 않고 효과가 바로 적용된다
EVENT_KIND_CHOICE = "choice"        # 선택지형(큰 사건): 게임이 멈추고 대화창에서 둘 중 하나를 고른다

ALL_GRADES = [1, 2, 3, 4]           # 모든 학년 (자동형 이벤트가 나오는 학년)

# 선택지 번호 (대화창의 선택 1 / 선택 2). 키 1 -> 첫 번째, 키 2 -> 두 번째
CHOICE_FIRST = 0                    # 첫 번째 선택지 번호(리스트 위치)
CHOICE_SECOND = 1                   # 두 번째 선택지 번호(리스트 위치)
CHOICE_NUMBER_START = 1             # 화면에 보이는 선택지 번호는 1부터 센다: "[1] …", "[2] …"
EVENT_COUNT_STEP = 1                # 이벤트가 한 번 나올 때 그 주기 이벤트 수가 늘어나는 양
EVENT_COUNT_START = 0               # 주기별 이벤트 수의 시작값 (아직 안 나온 주기는 0번)

# 특성 (얻으면 그 판 끝까지 유지). 값은 화면 배지에 쓸 이름이다
TRAIT_FITNESS = "체력 단련"          # 든든함 지속 시간 +10초
TRAIT_MUSIC = "음악 힐링"            # 쉬게 하기 멘탈 +20 -> +25
TRAIT_CAFFEINE = "카페인"            # 공부시키기 체력 -5 -> -3
TRAIT_LOVE = "연애 중"               # 쉬게 하기 체력 +15 -> +20
TRAIT_MORNING = "아침형 인간"        # 쉬게 하기 체력·멘탈 각각 +3
TRAIT_STUDY_GROUP = "스터디 그룹"    # 공부시키기 지식 +2
TRAIT_COOKING = "자취 요리"          # 든든함 지속 시간 +5초
TRAIT_MEDITATION = "명상"            # 공부시키기 멘탈 -8 -> -6

# 특성 보정을 받는 행동 효과 이름
BONUS_FULL_TIME = "full_time"       # 학식 먹이기로 붙는 든든함 지속 시간(초)
BONUS_REST_MENTAL = "rest_mental"   # 쉬게 하기 멘탈
BONUS_REST_HEALTH = "rest_health"   # 쉬게 하기 체력
BONUS_STUDY_HEALTH = "study_health"  # 공부시키기 체력
BONUS_STUDY_KNOWLEDGE = "study_knowledge"  # 공부시키기 지식 (방침 배수 전에 더한다, 시험 기간 2배 없음)
BONUS_STUDY_MENTAL = "study_mental"  # 공부시키기 멘탈
TRAIT_BONUS_START = 0               # 특성 보정 합계의 시작값 (특성이 없으면 0)

# 특성 -> {보정 받는 효과: 기본 수치에 더하는 양}. 여러 특성이 있으면 각각 더한다
TRAIT_BONUSES = {
    TRAIT_FITNESS: {BONUS_FULL_TIME: 10},      # 든든함 30초 -> 40초
    TRAIT_MUSIC: {BONUS_REST_MENTAL: 5},       # +20 -> +25
    TRAIT_CAFFEINE: {BONUS_STUDY_HEALTH: 2},   # -5 -> -3
    TRAIT_LOVE: {BONUS_REST_HEALTH: 5},        # +15 -> +20
    TRAIT_MORNING: {BONUS_REST_HEALTH: 3, BONUS_REST_MENTAL: 3},  # 체력 +15 -> +18, 멘탈 +20 -> +23
    TRAIT_STUDY_GROUP: {BONUS_STUDY_KNOWLEDGE: 2},  # 지식 +10 -> +12
    TRAIT_COOKING: {BONUS_FULL_TIME: 5},       # 든든함 30초 -> 35초
    TRAIT_MEDITATION: {BONUS_STUDY_MENTAL: 2},  # -8 -> -6
}

# 외형 5종 (얻으면 그 판 끝까지 제자에게 붙어 있다)
LOOK_GUITAR = "guitar"              # 기타(등 뒤)
LOOK_HEADBAND = "headband"          # 헬스 머리띠
LOOK_COFFEE = "coffee"              # 커피잔(손)
LOOK_HEART_PIN = "heart_pin"        # 하트 머리핀
LOOK_SUNGLASSES = "sunglasses"      # 선글라스(머리 위)
LOOK_IDS = [LOOK_GUITAR, LOOK_HEADBAND, LOOK_COFFEE, LOOK_HEART_PIN, LOOK_SUNGLASSES]

# 연계 플래그 (연계 이벤트가 나오기 위한 조건)
FLAG_MT = "MT 참석"
FLAG_BAND = "밴드부"
FLAG_LOVE = "연애 중"

# 이벤트 dict 키
EVENT_ID = "id"                     # 이벤트 이름표 (선택지형 한 판 1회 기록용)
EVENT_KIND = "kind"                 # 종류: EVENT_KIND_AUTO / EVENT_KIND_CHOICE
EVENT_GRADES = "grades"             # 나올 수 있는 학년 목록 (표에 적힌 학년에서만)
EVENT_REQUIRES = "requires"         # 필요한 연계 플래그 (없으면 None)
EVENT_TITLE = "title"               # 제목 (이벤트 이름)
EVENT_TEXT = "text"                 # 상황 한 줄 (선택지형)
EVENT_EFFECTS = "effects"           # 게이지 효과 {게이지 속성 이름: 변화량}
EVENT_OPTIONS = "options"           # 선택지 2개 (선택지형)
OPTION_TEXT = "text"                # 선택지 글자
OPTION_EFFECTS = "effects"          # 선택지 게이지 효과
OPTION_TRAIT = "trait"              # 얻는 특성 (없으면 None)
OPTION_LOOK = "look"                # 얻는 외형 (없으면 None)
OPTION_FLAG = "flag"                # 얻는 연계 플래그 (없으면 None)


def make_option(text, effects, trait=None, look=None, flag=None):
    """선택지 하나를 dict로 만들어 돌려준다(이벤트 표를 짧게 쓰기 위한 도우미)."""
    return {OPTION_TEXT: text, OPTION_EFFECTS: effects, OPTION_TRAIT: trait,
            OPTION_LOOK: look, OPTION_FLAG: flag}


# 자동형 이벤트 5개 (모든 학년, 반복 가능)
AUTO_EVENTS = [
    {EVENT_ID: "side_dish", EVENT_KIND: EVENT_KIND_AUTO, EVENT_GRADES: ALL_GRADES,
     EVENT_REQUIRES: None, EVENT_TITLE: "엄마가 반찬을 보내셨다",
     EVENT_EFFECTS: {GAUGE_HEALTH: 15}},
    {EVENT_ID: "group_chat_praise", EVENT_KIND: EVENT_KIND_AUTO, EVENT_GRADES: ALL_GRADES,
     EVENT_REQUIRES: None, EVENT_TITLE: "단톡방에서 칭찬받았다",
     EVENT_EFFECTS: {GAUGE_MENTAL: 10}},
    {EVENT_ID: "deadline_alarm", EVENT_KIND: EVENT_KIND_AUTO, EVENT_GRADES: ALL_GRADES,
     EVENT_REQUIRES: None, EVENT_TITLE: "과제 마감 알림이 울렸다",
     EVENT_EFFECTS: {GAUGE_MENTAL: -10}},
    {EVENT_ID: "cold", EVENT_KIND: EVENT_KIND_AUTO, EVENT_GRADES: ALL_GRADES,
     EVENT_REQUIRES: None, EVENT_TITLE: "감기 기운이 돈다",
     EVENT_EFFECTS: {GAUGE_HEALTH: -10}},
    {EVENT_ID: "professor_praise", EVENT_KIND: EVENT_KIND_AUTO, EVENT_GRADES: ALL_GRADES,
     EVENT_REQUIRES: None, EVENT_TITLE: "교수님께 칭찬받았다",
     EVENT_EFFECTS: {GAUGE_KNOWLEDGE: 15, GAUGE_MENTAL: 5}},
]

# 선택지형 이벤트 14개 (연계 3개, 특성 이벤트 4개 포함, 한 판에 한 번씩)
CHOICE_EVENTS = [
    {EVENT_ID: "mt_invite", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [1],
     EVENT_REQUIRES: None, EVENT_TITLE: "MT 초대",
     EVENT_TEXT: "과 선배가 이번 주말 MT에 같이 가자고 한다.",
     EVENT_OPTIONS: [
         make_option("간다", {GAUGE_MENTAL: 15, GAUGE_HEALTH: -10}, flag=FLAG_MT),
         make_option("공부한다", {GAUGE_KNOWLEDGE: 10, GAUGE_MENTAL: -5}),
     ]},
    {EVENT_ID: "club_fair", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [1],
     EVENT_REQUIRES: None, EVENT_TITLE: "동아리 박람회",
     EVENT_TEXT: "동아리 박람회가 열렸다. 어디에 들어갈까?",
     EVENT_OPTIONS: [
         make_option("밴드부", {}, trait=TRAIT_MUSIC, look=LOOK_GUITAR, flag=FLAG_BAND),
         make_option("헬스부", {}, trait=TRAIT_FITNESS, look=LOOK_HEADBAND),
     ]},
    {EVENT_ID: "free_rider", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [2],
     EVENT_REQUIRES: None, EVENT_TITLE: "조별과제 무임승차자",
     EVENT_TEXT: "조원 한 명이 연락도 없이 사라졌다.",
     EVENT_OPTIONS: [
         make_option("혼자 다 한다",
                     {GAUGE_KNOWLEDGE: 20, GAUGE_HEALTH: -15, GAUGE_MENTAL: -10}),
         make_option("교수님께 말한다", {GAUGE_MENTAL: 5}),
     ]},
    {EVENT_ID: "all_nighter", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [2],
     EVENT_REQUIRES: None, EVENT_TITLE: "밤샘의 유혹",
     EVENT_TEXT: "내일 마감인 과제가 아직 반이나 남았다.",
     EVENT_OPTIONS: [
         make_option("커피로 버틴다", {GAUGE_KNOWLEDGE: 10},
                     trait=TRAIT_CAFFEINE, look=LOOK_COFFEE),
         make_option("그냥 잔다", {GAUGE_HEALTH: 10}),
     ]},
    {EVENT_ID: "confession", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [3],
     EVENT_REQUIRES: None, EVENT_TITLE: "고백을 받았다",
     EVENT_TEXT: "같은 과 친구가 좋아한다고 고백했다.",
     EVENT_OPTIONS: [
         make_option("사귄다", {GAUGE_MENTAL: 15},
                     trait=TRAIT_LOVE, look=LOOK_HEART_PIN, flag=FLAG_LOVE),
         make_option("공부에 집중", {GAUGE_KNOWLEDGE: 20, GAUGE_MENTAL: -10}),
     ]},
    {EVENT_ID: "exchange_student", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [3],
     EVENT_REQUIRES: None, EVENT_TITLE: "교환학생 공고",
     EVENT_TEXT: "해외 교환학생 모집 공고가 올라왔다.",
     EVENT_OPTIONS: [
         make_option("지원한다", {GAUGE_KNOWLEDGE: 25, GAUGE_HEALTH: -10}),
         make_option("다음에", {GAUGE_MENTAL: 5}),
     ]},
    {EVENT_ID: "job_fair", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [4],
     EVENT_REQUIRES: None, EVENT_TITLE: "취업 박람회",
     EVENT_TEXT: "학교에서 취업 박람회가 열렸다.",
     EVENT_OPTIONS: [
         make_option("대기업 지원", {GAUGE_KNOWLEDGE: 20, GAUGE_MENTAL: -15}),
         make_option("대학원 상담", {GAUGE_KNOWLEDGE: 10, GAUGE_MENTAL: 5}),
     ]},
    {EVENT_ID: "senior_notes", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [2, 3, 4],
     EVENT_REQUIRES: FLAG_MT, EVENT_TITLE: "선배가 족보를 준다",
     EVENT_TEXT: "MT에서 친해진 선배가 족보를 건넨다.",
     EVENT_OPTIONS: [
         make_option("받는다", {GAUGE_KNOWLEDGE: 15}),
         make_option("거절한다", {GAUGE_MENTAL: 5}),
     ]},
    {EVENT_ID: "festival_stage", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [3, 4],
     EVENT_REQUIRES: FLAG_BAND, EVENT_TITLE: "축제 무대 제안",
     EVENT_TEXT: "밴드부에서 축제 무대에 서 보자고 한다.",
     EVENT_OPTIONS: [
         make_option("무대에 선다", {GAUGE_MENTAL: 25, GAUGE_HEALTH: -10},
                     look=LOOK_SUNGLASSES),
         make_option("연습만 한다", {GAUGE_MENTAL: 5}),
     ]},
    {EVENT_ID: "graduation_date", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [4],
     EVENT_REQUIRES: FLAG_LOVE, EVENT_TITLE: "졸업 전 데이트",
     EVENT_TEXT: "졸업하기 전에 둘이서 데이트하자고 한다.",
     EVENT_OPTIONS: [
         make_option("데이트한다", {GAUGE_MENTAL: 20, GAUGE_HEALTH: -5}),
         make_option("도서관에 간다", {GAUGE_KNOWLEDGE: 15}),
     ]},
    # 특성 이벤트 4개 (2026-11-24 추가): 학년마다 하나씩, 새 특성 4종을 준다
    {EVENT_ID: "morning_class", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [1],
     EVENT_REQUIRES: None, EVENT_TITLE: "1교시 시간표",
     EVENT_TEXT: "수강 신청에서 1교시 수업만 남았다.",
     EVENT_OPTIONS: [
         make_option("1교시를 듣는다", {GAUGE_HEALTH: -5}, trait=TRAIT_MORNING),
         make_option("다음 학기에", {GAUGE_MENTAL: 5}),
     ]},
    {EVENT_ID: "study_group", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [2],
     EVENT_REQUIRES: None, EVENT_TITLE: "스터디 모집",
     EVENT_TEXT: "전공 스터디원을 모집한다는 글이 올라왔다.",
     EVENT_OPTIONS: [
         make_option("들어간다", {GAUGE_KNOWLEDGE: 10, GAUGE_MENTAL: -5},
                     trait=TRAIT_STUDY_GROUP),
         make_option("혼자 한다", {GAUGE_KNOWLEDGE: 5}),
     ]},
    {EVENT_ID: "living_alone", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [3],
     EVENT_REQUIRES: None, EVENT_TITLE: "자취 시작",
     EVENT_TEXT: "학교 앞 원룸으로 이사했다. 밥은 어떻게 할까?",
     EVENT_OPTIONS: [
         make_option("직접 해 먹는다", {GAUGE_HEALTH: 5}, trait=TRAIT_COOKING),
         make_option("배달시킨다", {GAUGE_MENTAL: 5}),
     ]},
    {EVENT_ID: "thesis_stress", EVENT_KIND: EVENT_KIND_CHOICE, EVENT_GRADES: [4],
     EVENT_REQUIRES: None, EVENT_TITLE: "졸업 논문 스트레스",
     EVENT_TEXT: "졸업 논문 마감이 다가와 머리가 복잡하다.",
     EVENT_OPTIONS: [
         make_option("명상을 배운다", {GAUGE_MENTAL: 10}, trait=TRAIT_MEDITATION),
         make_option("밤새 쓴다", {GAUGE_KNOWLEDGE: 20, GAUGE_HEALTH: -10}),
     ]},
]
ALL_EVENTS = AUTO_EVENTS + CHOICE_EVENTS   # 이벤트 표 전체 (자동형 5 + 선택지형 14)

# ---------------------------------------------------------------
# 18. 랜덤 이벤트 화면 (기획서·jeja-spec 4절). 보기만 바꾸며 게임 결과에는 영향이 없다
# ---------------------------------------------------------------
EVENT_FONT_SIZE = 18                # 대화창 상황 글자·선택 버튼 글자 크기
SMALL_FONT_SIZE = 14                # 작은 글자 크기: 효과 미리보기, 특성 배지 (자동형 알림은 EVENT_NOTICE_FONT_SIZE)
TEXT_SEPARATOR = " "                # 상황 글자를 줄바꿈할 때 끊는 자리(띄어쓰기)
TEXT_ELLIPSIS = "…"                 # 줄 수를 넘는 글자를 줄였다는 표시

# 대화창 입력 대기: 대화창이 뜬 직후 이 시간 동안은 선택 입력(키·클릭)을 무시한다
# (행동 키를 연타하다가 그 키가 선택으로 들어가는 것을 막는다. 대화창 시계로 잰다, 게임 시간은 정지)
EVENT_INPUT_DELAY = 0.3

# 대화창 뒤 "멈춤" 표시: 화면 전체에 3칸 간격 남색 점무늬를 덮는다 (Surface 알파 대신 도트)
# 점 1칸(4픽셀) + 빈칸 2칸이라 뒤의 정보바·버튼 글자가 읽힐 만큼 옅다
PAUSE_DOT_STEP = PIXEL_SIZE * 3     # 점 사이 간격(12픽셀 = 3칸). 한 줄 건너 한 칸씩 엇갈려 찍는다
PAUSE_DOT_SHIFT = PIXEL_SIZE        # 홀수 줄의 점을 옆으로 밀어 찍는 거리(체크무늬 느낌)
COLOR_PAUSE_DOT = COLOR_OUTLINE     # 점 색(진한 남색)

# 대화창 등장 연출: 위에서 PIXEL_SIZE씩 계단처럼 내려오며 나타난다
EVENT_DIALOG_SLIDE_TIME = 0.15      # 등장에 걸리는 시간(초)
EVENT_DIALOG_SLIDE_DISTANCE = 16    # 처음에 원래 자리보다 위에 있는 거리(픽셀, 4칸)

# 대화창 상자: 제자 무대 패널 위 가운데 (무대 x 284~788, y 116~460)
EVENT_DIALOG_RECT = (300, 132, 472, 264)    # (x, y, 가로, 세로) -> 아래 끝 396 (+그림자 1칸)
EVENT_DIALOG_CENTER_X = STUDENT_CENTER_X    # 대화창 글자 가운데 x (무대 가운데, 536)
EVENT_TITLE_BAND_RECT = (316, 144, 440, 36)  # 제목 띠 (x, y, 가로, 세로): 상자 안쪽 위
EVENT_TITLE_ICON_MARGIN = 16        # 제목 띠 양 끝에서 별 아이콘까지 거리
EVENT_TEXT_TOP = 188                # 상황 글자 구역 위쪽 y (제목 띠 아래)
EVENT_TEXT_LINE_HEIGHT = 24         # 상황 글자 한 줄 높이
EVENT_TEXT_MAX_LINES = 2            # 상황 글자는 2줄까지 (넘치면 줄임표)
EVENT_TEXT_MAX_WIDTH = 416          # 상황 글자 한 줄 최대 가로 길이 (상자 안쪽 좌우 여백 24씩)

# 선택 버튼 2개 (버튼 아래에 작은 효과 미리보기 한 줄)
CHOICE_BUTTON_TEXT = "[{}] {}"      # 선택 버튼 글자 틀: "[1] 간다"
CHOICE_BUTTON_X = 324               # 선택 버튼 왼쪽 x
CHOICE_BUTTON_WIDTH = 424           # 선택 버튼 가로 길이
CHOICE_BUTTON_HEIGHT = 40           # 선택 버튼 세로 길이 (아래 남색 받침 1칸은 별도)
CHOICE_BUTTON_YS = [244, 316]       # 선택 버튼 1, 2의 위쪽 y
CHOICE_PREVIEW_GAP = 16             # 버튼 아래 끝과 미리보기 글자 가운데 사이 거리
PREVIEW_SEPARATOR = " · "           # 미리보기 항목 사이 구분 글자
PREVIEW_TRAIT_TEXT = "특성: {}"      # 미리보기의 특성 항목
PREVIEW_LOOK_TEXT = "외형: {}"       # 미리보기의 외형 항목
PREVIEW_NONE_TEXT = "변화 없음"      # 미리보기에 보일 것이 없을 때
COLOR_PREVIEW_UP = COLOR_GREEN_DARK     # 미리보기: 늘어나는 값 (크림 바탕에서 또렷한 초록)
COLOR_PREVIEW_DOWN = COLOR_RED_DARK     # 미리보기: 줄어드는 값
COLOR_PREVIEW_OTHER = (72, 64, 112)     # 미리보기: 특성·외형·구분 글자 (크림 바탕에서 또렷한 진한 보라회색)

# 외형 이름 (미리보기 글자)
LOOK_NAMES = {
    LOOK_GUITAR: "기타", LOOK_HEADBAND: "헬스 머리띠", LOOK_COFFEE: "커피잔",
    LOOK_HEART_PIN: "하트 머리핀", LOOK_SUNGLASSES: "선글라스",
}

# 자동형 알림(토스트): 무대 위쪽 왼쪽 구석. 가운데 위(행동 팝업 자리)와 겹치지 않는다
EVENT_NOTICE_TEXT = "{}"            # 자동형 알림 글자 틀: 이벤트 제목
EVENT_NOTICE_X = STAGE_X + PIXEL_SIZE * 2   # 알림 상자 왼쪽 x (292)
EVENT_NOTICE_Y = PANEL_Y + PIXEL_SIZE * 3   # 알림 상자 위쪽 y (128)
EVENT_NOTICE_HEIGHT = 56            # 알림 상자 세로 길이(글자 2줄 자리) -> 아래 끝 184 (+그림자 1칸)
EVENT_NOTICE_FONT_SIZE = 16         # 알림 글자 크기 (작은 글자 14보다 크게, 잘 읽히게)
EVENT_NOTICE_LINE_HEIGHT = 20       # 알림 글자 한 줄 높이 (2줄까지)
FULL_LINE = 1                       # 줄 사이 간격 수 = 줄 수 - FULL_LINE (줄들을 세로 가운데에 놓을 때)
# 알림 글자 한 줄 최대 가로 길이. 넘으면 띄어쓰기 자리에서 2줄로 나눈다.
# 상자 오른쪽 끝 = 292 + 44 + 160 = 496 -> 머리 위 행동 팝업(왼쪽 끝 약 500)과 겹치지 않는다
EVENT_NOTICE_TEXT_MAX_WIDTH = 160
EVENT_NOTICE_PAD = PIXEL_SIZE       # 상자 안쪽 왼쪽 여백(아이콘 앞)
EVENT_NOTICE_ICON_GAP = PIXEL_SIZE  # 아이콘과 글자 사이 간격
EVENT_NOTICE_PAD_RIGHT = PIXEL_SIZE * 2  # 글자 뒤 오른쪽 여백
EVENT_NOTICE_SLIDE_TIME = 0.15      # 알림이 내려오며 나타나는 시간(초)
EVENT_NOTICE_SLIDE_DISTANCE = 12    # 처음에 원래 자리보다 위에 있는 거리(픽셀, 3칸)
NOTICE_GOOD_ICON = [                # 좋은 일 아이콘: 하트
    "qq.qq",
    "qpWpq",
    "qpppq",
    ".qpq.",
    "..q..",
]
NOTICE_BAD_ICON = [                 # 나쁜 일 아이콘: 느낌표
    ".qq.",
    ".qq.",
    ".qq.",
    "....",
    ".qq.",
]
NOTICE_GOOD_COLORS = {"q": COLOR_PINK_DARK, "p": COLOR_PINK, "W": COLOR_WHITE}
NOTICE_BAD_COLORS = {"q": COLOR_RED_DARK}
# 알림 색: (몸통, 위 하이라이트 줄, 아래 그림자 줄). 효과 합이 0 이상이면 좋은 일
NOTICE_GOOD_BOX = (COLOR_MINT_LIGHT, COLOR_WHITE, COLOR_MINT)
NOTICE_BAD_BOX = (COLOR_PINK_LIGHT, COLOR_WHITE, COLOR_PINK)

# 이벤트 수치 팝업: 무대 왼쪽 위 칸에 위에서 아래로 쌓는다
# (가운데 머리 위는 행동 팝업 자리, 얼굴 양옆은 파티클 자리라서 겹치지 않는 왼쪽 구석을 쓴다)
EVENT_POPUP_X = 336                 # 이벤트 팝업 글자 가운데 x (글자 왼쪽 끝 ~299, 오른쪽 끝 ~374)
                                    # 알림이 있으면 첫 줄 가운데 y = 184 + 28 = 212 (3줄째 256, 무대 안)
EVENT_POPUP_TOP_MARGIN = 28         # 위 경계(무대 위 끝 또는 알림 아래 끝)와 첫 줄 가운데 사이 거리
                                    # (글자 위 여백 + 0.8초 동안 떠오르는 12픽셀을 포함)

# 특성 배지: 상태 패널 안 아래쪽(멘탈 막대 아래), 얻은 순서대로 2열
TRAIT_BADGE_X = 24                  # 첫 열 왼쪽 x
TRAIT_BADGE_Y = 344                 # 첫 줄 위쪽 y (멘탈 막대 테두리 아래 끝 340 + 여백). 특성 8종 = 2열 4줄 -> 아래 끝 452, 그림자 456
TRAIT_BADGE_WIDTH = 112             # 배지 가로 길이 -> 2열: 24~136, 144~256 (패널 안쪽 16~264)
TRAIT_BADGE_HEIGHT = 24             # 배지 세로 길이 (+그림자 1칸)
TRAIT_BADGE_GAP = 4                 # 배지 사이 간격(가로·세로)
TRAIT_BADGE_COLUMNS = 2             # 한 줄에 놓는 배지 수
# 특성 -> (몸통, 위 하이라이트 줄)
TRAIT_COLORS = {
    TRAIT_FITNESS: (COLOR_APRICOT, COLOR_WHITE),
    TRAIT_MUSIC: (COLOR_SKY, COLOR_SKY_LIGHT),
    TRAIT_CAFFEINE: (COLOR_YELLOW, COLOR_YELLOW_LIGHT),
    TRAIT_LOVE: (COLOR_PINK, COLOR_PINK_LIGHT),
    TRAIT_MORNING: (COLOR_MINT, COLOR_MINT_LIGHT),
    TRAIT_STUDY_GROUP: (COLOR_SKY_LIGHT, COLOR_WHITE),
    TRAIT_COOKING: (COLOR_GREEN_LIGHT, COLOR_WHITE),
    TRAIT_MEDITATION: (COLOR_GRAY_LIGHT, COLOR_WHITE),
}

# 상태 배지: 상태 패널 위쪽(체력 라벨 줄 200 위)에
# 지금 붙어 있는 디버프·버프를 특성 배지와 같은 모양으로 2열로 보인다
STATUS_BADGE_Y = 128                # 첫 줄 위쪽 y (두 줄이면 아래 끝 128 + 24 + 4 + 24 = 180, 그림자 184)
# 상태 이름 -> (몸통, 위 하이라이트 줄). 디버프는 분홍·회색, 버프는 민트·노랑
STATUS_COLORS = {
    DEBUFF_TIRED: (COLOR_PINK, COLOR_PINK_LIGHT),
    DEBUFF_DEPRESSED: (COLOR_GRAY, COLOR_GRAY_LIGHT),
    BUFF_FULL: (COLOR_MINT, COLOR_MINT_LIGHT),
    BUFF_REFRESH: (COLOR_SKY, COLOR_SKY_LIGHT),
    CONDITION_GOOD: (COLOR_YELLOW, COLOR_YELLOW_LIGHT),
}
# 게이지 라벨 줄 오른쪽 끝(막대 오른쪽 끝과 같은 x)에 "지금/최대" 글자를 쓴다: "80/100"
GAUGE_VALUE_TEXT = "{}/{}"

# 외형 5종 도트 스프라이트. 위치는 얼굴 격자(20 x 20칸) 기준 (열, 행)이고 칸 크기는 얼굴과 같다
# (반지름 // 10) -> 학년마다 얼굴과 함께 커지고, 점프·숨쉬기 때 얼굴과 함께 움직인다.
# 자리 나눔: 선글라스 = 머리 꼭대기(열 4~15, 행 -1~2), 하트 머리핀 = 머리 왼쪽 옆(열 -3~1, 행 2~6),
# 머리띠 = 이마 위 머리카락(행 5~6, 매듭 꼬리는 오른쪽 행 6~8), 커피잔 = 얼굴 오른쪽 아래 바깥(행 11~18),
# 기타 = 얼굴 뒤(몸통은 왼쪽 아래, 넥은 오른쪽 위로 비스듬히). 서로 칸이 겹치지 않는다.
COLOR_GUITAR_BODY = (120, 176, 228)       # 기타 몸통(하늘색, 피부색과 또렷이 구분)
COLOR_GUITAR_SHADE = (92, 146, 206)       # 기타 몸통 아래 그림자
COLOR_GUITAR_NECK = (150, 104, 76)        # 기타 넥(나무)
COLOR_GUITAR_NECK_LIGHT = (196, 150, 108)  # 넥 밝은 쪽
COLOR_GUITAR_HEAD = (110, 76, 64)         # 기타 헤드
COLOR_HEADBAND = (232, 82, 90)            # 헬스 머리띠(빨강)
COLOR_HEADBAND_LIGHT = (250, 150, 150)    # 머리띠 위 밝은 줄
COLOR_MUG = COLOR_WHITE                   # 커피잔
COLOR_COFFEE = (150, 100, 70)             # 커피
COLOR_STEAM = (196, 192, 214)             # 김
COLOR_SUNGLASS = (64, 60, 96)             # 선글라스 알(짙은 남보라)
COLOR_SUNGLASS_SHINE = (150, 160, 220)    # 선글라스 알 반짝임

GUITAR_SPRITE = [           # 35 x 33칸, 얼굴 격자 (-6, -6)부터. 얼굴보다 먼저(뒤에) 그린다
    "..............................OOOO.",
    ".............................OhhhhO",
    "............................WhhhhW.",
    "...........................OhhhhO..",
    "..........................WhhhhW...",
    "..........................OnmO.....",
    ".........................OnmO......",
    "........................OnmO.......",
    ".......................OnmO........",
    "......................OnmO.........",
    ".....................OnmO..........",
    "....................OnmO...........",
    "...................OnmO............",
    "..................OnmO.............",
    ".................OnmO..............",
    "................OnmO...............",
    "...............OnmO................",
    "........OOOOO.OnmO.................",
    ".......ObbbbbOnmO..................",
    "......ObbbbbOnmO...................",
    "......ObbbbOnmO....................",
    "......ObbbOnmOO....................",
    "...OOObbbOnmObO....................",
    "..ObbbbbbbbbbO.....................",
    ".ObbbbbOObbbO......................",
    "ObbbbbbOObbO.......................",
    "ObbbbbbbbbbO.......................",
    "ObbbbbbbbbbO.......................",
    "OBbbbbbbbbBO.......................",
    "OBbbddddbbBO.......................",
    ".OBbbbbbbBO........................",
    "..OBbbbbBO.........................",
    "...OOOOOO..........................",
]
HEADBAND_SPRITE = [         # 22 x 4칸, 얼굴 격자 (0, 5)부터: 이마 위 띠 + 오른쪽 매듭 꼬리
    "..RRRRRRRRRRRRRRRR....",  # (얼굴 외곽선 칸은 비워 두어 외곽선이 그대로 보인다)
    ".rrrrrrrrrrrrrrrrrr.rr",
    "....................r.",
    ".....................r",
]
COFFEE_SPRITE = [           # 7 x 8칸, 얼굴 격자 (20, 11)부터: 김 + 손잡이 달린 잔
    "..s.s..",
    ".s.s...",
    "OOOOO..",
    "OcccO..",
    "OwwwOOO",
    "OwwwO.O",
    "OwwwOOO",
    ".OOO...",
]
HEART_PIN_SPRITE = [        # 5 x 5칸, 얼굴 격자 (-3, 2)부터: 머리 왼쪽 옆 하트 핀 (선글라스와 2칸 띄움)
    "qq.qq",
    "qpWpq",
    "qpppq",
    ".qpq.",
    "..q..",
]
SUNGLASSES_SPRITE = [       # 12 x 4칸, 얼굴 격자 (4, -1)부터: 머리 꼭대기에 걸친 선글라스
    "OOOOOOOOOOOO",
    "OkkgO..OkkgO",
    "OkkkO..OkkkO",
    ".OOO....OOO.",
]
LOOK_COLORS = {
    "O": COLOR_OUTLINE, "W": COLOR_WHITE,
    "b": COLOR_GUITAR_BODY, "B": COLOR_GUITAR_SHADE, "d": COLOR_GUITAR_HEAD,
    "n": COLOR_GUITAR_NECK, "m": COLOR_GUITAR_NECK_LIGHT, "h": COLOR_GUITAR_HEAD,
    "R": COLOR_HEADBAND_LIGHT, "r": COLOR_HEADBAND,
    "s": COLOR_STEAM, "c": COLOR_COFFEE, "w": COLOR_MUG,
    "q": COLOR_PINK_DARK, "p": COLOR_PINK,
    "k": COLOR_SUNGLASS, "g": COLOR_SUNGLASS_SHINE,
}
# 외형 id -> ((열, 행), 격자). 그리는 차례: LOOKS_BEHIND는 얼굴보다 먼저, LOOKS_FRONT는 입 다음
LOOK_SPRITES = {
    LOOK_GUITAR: ((-6, -6), GUITAR_SPRITE),
    LOOK_HEADBAND: ((0, 5), HEADBAND_SPRITE),
    LOOK_COFFEE: ((20, 11), COFFEE_SPRITE),
    LOOK_HEART_PIN: ((-3, 2), HEART_PIN_SPRITE),
    LOOK_SUNGLASSES: ((4, -1), SUNGLASSES_SPRITE),
}
LOOKS_BEHIND = [LOOK_GUITAR]
LOOKS_FRONT = [LOOK_HEADBAND, LOOK_HEART_PIN, LOOK_SUNGLASSES, LOOK_COFFEE]

# ---------------------------------------------------------------
# 19. 재화(연구비·명성)와 업그레이드 (기획서 3절)
# ---------------------------------------------------------------
MONEY_START = 0             # 연구비 기본값 (record.json 에 없으면 0)
LEVEL_START = 0             # 업그레이드 레벨 기본값 (사지 않았으면 0)
FAME_START = 0              # 명성 기본값 (새 게임 N으로 처음부터 시작할 때)
LEVEL_STEP = 1              # 업그레이드를 한 번 사면 오르는 레벨
FAME_MONEY_BONUS = 0.1      # 명성 1당 연구비 획득 배수 +0.1: 배수 = 1 + 0.1 x 명성
MONEY_EPSILON = 1e-9        # 내림(int) 전에 더하는 아주 작은 값 (1.6 x 80 = 127.999… 처럼 곱셈 결과가 정수 바로 아래로 나오는 소수 오차 방지)
GAUGE_DECIMALS = 6          # 체력·멘탈을 이 자리에서 반올림해 소수 오차가 쌓이지 않게 한다

# 졸업 보너스 (x 명성 배수, 내림). 휴학이면 없음
GRADUATION_BONUS = {ENDING_TOP: 200, ENDING_NORMAL: 100, ENDING_BARELY: 50}

# 업그레이드 가격 = 내림(기본 가격 x 2.0 ^ 현재 레벨)
UPGRADE_COST_GROWTH = 2.0

# 업그레이드 id
UPGRADE_MENU = "menu"                   # 학식 메뉴 개선
UPGRADE_BED = "bed"                     # 푹신한 침대
UPGRADE_BOOK = "reference_book"         # 참고서
UPGRADE_TIME = "time_management"        # 시간 관리
UPGRADE_HEALTH_CARE = "health_care"     # 건강 관리
UPGRADE_LIBRARY = "library"             # 도서관
UPGRADE_CAFE = "cafe"                   # 카페
UPGRADE_GYM = "gym"                     # 헬스장
UPGRADE_CHARM = "lucky_charm"           # 행운 부적
UPGRADE_SCHOLARSHIP = "scholarship"     # 장학금 제도
UPGRADE_HEALTH_MAX = "health_max"       # 체력 증진
UPGRADE_MENTAL_MAX = "mental_max"       # 멘탈 관리
UPGRADE_SELF_CARE = "self_care"         # 자기 관리

# 업그레이드 dict 키
UPGRADE_ID = "id"
UPGRADE_NAME = "name"               # 패널에 보일 이름
UPGRADE_CATEGORY = "category"       # 분류 (행동 효율 / 자동화 속도 / 시설 / 이벤트 / 컨디션)
UPGRADE_MAX_LEVEL = "max_level"     # 최대 레벨
UPGRADE_BASE_COST = "base_cost"     # 기본 가격
UPGRADE_PER_LEVEL = "per_level"     # 레벨 1당 효과 크기 (효과 = 레벨 x 이 값)
UPGRADE_EFFECT_TEXT = "effect"      # 패널에 보일 효과 설명

# 업그레이드 13종 (기획서 3절 표 순서). 시설·장학금은 최대 레벨 1이라 "레벨 x 효과"로 똑같이 계산한다
UPGRADES = [
    {UPGRADE_ID: UPGRADE_MENU, UPGRADE_NAME: "학식 메뉴 개선", UPGRADE_CATEGORY: "행동 효율",
     UPGRADE_MAX_LEVEL: 5, UPGRADE_BASE_COST: 240, UPGRADE_PER_LEVEL: 6,
     UPGRADE_EFFECT_TEXT: "든든함 +6초"},
    {UPGRADE_ID: UPGRADE_BED, UPGRADE_NAME: "푹신한 침대", UPGRADE_CATEGORY: "행동 효율",
     UPGRADE_MAX_LEVEL: 5, UPGRADE_BASE_COST: 240, UPGRADE_PER_LEVEL: 4,
     UPGRADE_EFFECT_TEXT: "휴식 체력·멘탈 +4"},
    {UPGRADE_ID: UPGRADE_BOOK, UPGRADE_NAME: "참고서", UPGRADE_CATEGORY: "행동 효율",
     UPGRADE_MAX_LEVEL: 5, UPGRADE_BASE_COST: 360, UPGRADE_PER_LEVEL: 2,
     UPGRADE_EFFECT_TEXT: "공부 지식 +2"},
    {UPGRADE_ID: UPGRADE_TIME, UPGRADE_NAME: "시간 관리", UPGRADE_CATEGORY: "자동화 속도",
     UPGRADE_MAX_LEVEL: 5, UPGRADE_BASE_COST: 450, UPGRADE_PER_LEVEL: 0.2,
     UPGRADE_EFFECT_TEXT: "행동 간격 -0.2초"},
    {UPGRADE_ID: UPGRADE_HEALTH_CARE, UPGRADE_NAME: "건강 관리", UPGRADE_CATEGORY: "자동화 속도",
     UPGRADE_MAX_LEVEL: 5, UPGRADE_BASE_COST: 450, UPGRADE_PER_LEVEL: 0.1,
     UPGRADE_EFFECT_TEXT: "자연 감소 -10%"},
    {UPGRADE_ID: UPGRADE_LIBRARY, UPGRADE_NAME: "도서관", UPGRADE_CATEGORY: "시설",
     UPGRADE_MAX_LEVEL: 1, UPGRADE_BASE_COST: 900, UPGRADE_PER_LEVEL: 3,
     UPGRADE_EFFECT_TEXT: "공부 지식 +3"},
    {UPGRADE_ID: UPGRADE_CAFE, UPGRADE_NAME: "카페", UPGRADE_CATEGORY: "시설",
     UPGRADE_MAX_LEVEL: 1, UPGRADE_BASE_COST: 900, UPGRADE_PER_LEVEL: 5,
     UPGRADE_EFFECT_TEXT: "휴식 때 체력 +5"},
    {UPGRADE_ID: UPGRADE_GYM, UPGRADE_NAME: "헬스장", UPGRADE_CATEGORY: "시설",
     UPGRADE_MAX_LEVEL: 1, UPGRADE_BASE_COST: 900, UPGRADE_PER_LEVEL: 2,
     UPGRADE_EFFECT_TEXT: "공부 체력 소모 -2"},
    {UPGRADE_ID: UPGRADE_CHARM, UPGRADE_NAME: "행운 부적", UPGRADE_CATEGORY: "이벤트",
     UPGRADE_MAX_LEVEL: 3, UPGRADE_BASE_COST: 600, UPGRADE_PER_LEVEL: 0.05,
     UPGRADE_EFFECT_TEXT: "이벤트 확률 +5%p"},
    {UPGRADE_ID: UPGRADE_SCHOLARSHIP, UPGRADE_NAME: "장학금 제도", UPGRADE_CATEGORY: "이벤트",
     UPGRADE_MAX_LEVEL: 1, UPGRADE_BASE_COST: 750, UPGRADE_PER_LEVEL: 30,
     UPGRADE_EFFECT_TEXT: "장학금 이벤트 추가"},
    {UPGRADE_ID: UPGRADE_HEALTH_MAX, UPGRADE_NAME: "체력 증진", UPGRADE_CATEGORY: "컨디션",
     UPGRADE_MAX_LEVEL: 5, UPGRADE_BASE_COST: 300, UPGRADE_PER_LEVEL: 10,
     UPGRADE_EFFECT_TEXT: "체력 최대 +10"},
    {UPGRADE_ID: UPGRADE_MENTAL_MAX, UPGRADE_NAME: "멘탈 관리", UPGRADE_CATEGORY: "컨디션",
     UPGRADE_MAX_LEVEL: 5, UPGRADE_BASE_COST: 300, UPGRADE_PER_LEVEL: 10,
     UPGRADE_EFFECT_TEXT: "멘탈 최대 +10"},
    {UPGRADE_ID: UPGRADE_SELF_CARE, UPGRADE_NAME: "자기 관리", UPGRADE_CATEGORY: "컨디션",
     UPGRADE_MAX_LEVEL: 5, UPGRADE_BASE_COST: 400, UPGRADE_PER_LEVEL: 0.2,
     UPGRADE_EFFECT_TEXT: "체력·멘탈 +0.2/초"},
]
UPGRADE_IDS = [upgrade[UPGRADE_ID] for upgrade in UPGRADES]          # 패널 순서
UPGRADES_BY_ID = {upgrade[UPGRADE_ID]: upgrade for upgrade in UPGRADES}

# 장학금 제도를 사면 자동형 후보에 들어가는 이벤트 (연구비 +30 x 학년, 게이지 변화 없음)
EVENT_MONEY_PER_GRADE = "money_per_grade"   # 이벤트 dict 키: 학년당 연구비
SCHOLARSHIP_EVENT = {
    EVENT_ID: "scholarship", EVENT_KIND: EVENT_KIND_AUTO, EVENT_GRADES: ALL_GRADES,
    EVENT_REQUIRES: None, EVENT_TITLE: "장학금을 받았다", EVENT_EFFECTS: {},
    EVENT_MONEY_PER_GRADE: UPGRADES_BY_ID[UPGRADE_SCHOLARSHIP][UPGRADE_PER_LEVEL],
}

# ---------------------------------------------------------------
# 20. 업그레이드 화면 (버튼·패널·정보바·타이틀 글자)
# ---------------------------------------------------------------
MONEY_LABEL = "연구비"
MONEY_TEXT = "{} {}"                # 정보바·패널의 연구비 글자: "연구비 340"
INFO_ITEM_GAP = 28                  # 정보바에서 연구비 글자와 지식 글자 사이 간격
TITLE_WALLET_TEXT = "{} · 명성 {} · 연구비 {}"  # 타이틀 화면 최고 기록 아래 글자 (칭호 · 명성 · 연구비)
TITLE_WALLET_Y = 364                # 그 글자 가운데 y (최고 기록 배지 아래, 시작 안내 위)
GRADUATION_BONUS_TEXT = "졸업 보너스: 연구비 +{}"  # 엔딩 화면 누적 지식 아래 글자
GRADUATION_BONUS_Y = 398            # 그 글자 가운데 y

# [업그레이드 U] 버튼: 게임 화면에서는 방침 버튼 오른쪽(x 600~776),
# 엔딩 화면에서는 가운데 패널(아래 끝 496) 아래 같은 x 자리
UPGRADE_BUTTON_TEXT = "업그레이드 U"
UPGRADE_BUTTON_X = BUTTON_START_X + POLICY_AREA_WIDTH + BUTTON_GAP   # 600
UPGRADE_BUTTON_Y = BUTTON_Y                                          # 476
UPGRADE_BUTTON_ENDING_Y = 516
# 경과 시간 글자 가운데: [업그레이드 U] 버튼 가운데 x, 자동 행동 진행 막대 가운데 y
ELAPSED_CENTER_X = UPGRADE_BUTTON_X + BUTTON_WIDTH // 2   # 688
ELAPSED_CENTER_Y = AUTO_BAR_Y + AUTO_BAR_HEIGHT // 2      # 548

# 업그레이드 패널: 왼쪽 상태 패널 자리(x 12~268, y 116~468)에 겹쳐 그린다.
# 그래서 패널이 열려 있어도 오른쪽 제자 무대(제자·배경)는 그대로 보인다. 반투명 없이 도트 상자
UPGRADE_PANEL_RECT = (STATUS_PANEL_X, PANEL_Y, STATUS_PANEL_WIDTH, 352)  # 아래 끝 468 (방침 버튼 476 위)
UPGRADE_PANEL_TITLE = "업그레이드"
UPGRADE_HEADER_Y = 132              # 머리 줄(제목·연구비) 가운데 y (제목 글자 120~144)
UPGRADE_HEADER_LEFT = 28            # 제목 글자 왼쪽 x
UPGRADE_HEADER_RIGHT = 252          # 연구비 글자 오른쪽 끝 x
UPGRADE_ROW_X = 24                  # 항목 줄 상자 왼쪽 x
UPGRADE_ROW_WIDTH = 232             # 항목 줄 상자 가로 길이 -> 오른쪽 끝 256 (패널 안쪽 20~260)
UPGRADE_ROW_TOP = 166               # 첫 항목 줄 위쪽 y (머리 줄과 미니 게이지 줄 아래)
# 항목이 13줄이라 줄을 얇게 만든다: 외곽선 없는 계단형 모서리 띠 한 줄 = 작은 글자 한 줄(19)
UPGRADE_ROW_HEIGHT = 20             # 항목 줄 띠 세로 길이
UPGRADE_ROW_STEP = 21               # 항목 줄 사이 거리 (13줄 -> 마지막 아래 끝 166 + 12 x 21 + 20 = 438)
# 패널 머리 줄 아래 미니 게이지 줄: 패널이 상태 패널의 체력·멘탈 막대를 가리므로
# 작은 막대 2개를 한 줄에 나란히 보여 준다. 길이는 표시값(E4), 색(30 미만 빨강)은 실제 값 기준
UPGRADE_GAUGE_Y = 154               # 미니 게이지 줄 가운데 y (라벨 글자 145~164, 막대 테두리 146~162)
# (Student 속성 이름, 라벨, 라벨 글자 왼쪽 x)
UPGRADE_GAUGES = [(GAUGE_HEALTH, HEALTH_LABEL, 28), (GAUGE_MENTAL, MENTAL_LABEL, 144)]
UPGRADE_GAUGE_BAR_GAP = 6           # 라벨 글자와 막대 테두리 사이 간격
UPGRADE_GAUGE_BAR_WIDTH = 64       # 미니 막대 가로 길이(값 100일 때)
UPGRADE_GAUGE_BAR_HEIGHT = 8        # 미니 막대 세로 길이(도트 2칸, 테두리 제외)
UPGRADE_CURSOR_X = 28               # 고른 줄 표시 화살표 왼쪽 x
UPGRADE_NAME_X = 48                 # 이름 글자 왼쪽 x
UPGRADE_LEVEL_X = 148               # "Lv 0/5" 글자 왼쪽 x
UPGRADE_COST_RIGHT = 248            # 가격 글자 오른쪽 끝 x
UPGRADE_FOOTER_X = 28               # 바닥 줄(고른 항목 효과) 글자 왼쪽 x
UPGRADE_FOOTER_Y = 454              # 바닥 줄 가운데 y (글자 445~464: 마지막 줄 아래 끝 438 아래, 꼬리까지 외곽선 안)
UPGRADE_FOOTER_TEXT = "효과: {}"     # 바닥 줄 글자 틀: 고른 줄(↑↓)의 레벨당 효과

# 이벤트 로그 패널 (L키, 게임 화면): 업그레이드 패널과 같은 자리에 이번 판 이벤트를 새것부터 보인다
EVENT_LOG_PANEL_RECT = UPGRADE_PANEL_RECT   # 패널 자리 (12, 116, 256, 352)
EVENT_LOG_TITLE = "이벤트 로그"
EVENT_LOG_CLOSE_TEXT = "L 닫기"         # 머리 줄 오른쪽 안내
EVENT_LOG_EMPTY_TEXT = "아직 이벤트가 없어요"
EVENT_LOG_LINE_TEXT = "{time} · {title}"   # 첫 줄: 일어난 게임 시간 · 이벤트 이름
EVENT_LOG_CHOICE_TEXT = "{option} → {result}"  # 선택지형 둘째 줄: 고른 선택지 → 결과
EVENT_LOG_MAX = 30                     # 이번 판에 기억하는 항목 수 (넘으면 오래된 것부터 지움)
EVENT_LOG_ROWS = 7                     # 패널에 보이는 항목 수 (새것부터)
EVENT_LOG_X = 24                       # 항목 상자 왼쪽 x
EVENT_LOG_WIDTH = 232                  # 항목 상자 가로 길이 -> 오른쪽 끝 256
EVENT_LOG_TOP = 156                    # 첫 항목 상자 위쪽 y (머리 줄 아래)
EVENT_LOG_HEIGHT = 40                  # 항목 상자 세로 길이 (글자 2줄)
EVENT_LOG_STEP = 42                    # 항목 사이 거리 (7개 -> 마지막 아래 끝 156 + 6 x 42 + 40 = 448)
EVENT_LOG_PAD_X = 8                    # 상자 왼쪽 끝에서 글자까지 여백
EVENT_LOG_LINE1_DY = 12                # 상자 위 끝에서 첫 줄 가운데까지
EVENT_LOG_LINE2_DY = 28                # 상자 위 끝에서 둘째 줄 가운데까지
EVENT_LOG_ELLIPSIS = "…"               # 상자보다 긴 글자는 잘라서 끝에 붙인다
EVENT_LOG_HINT_TEXT = "L: 이벤트 로그"  # 게임 화면 오른쪽 아래(경과 시간 밑) 안내
EVENT_LOG_HINT_Y = 577                 # 안내 가운데 y (경과 시간 548 아래, 화면 600 안)
UPGRADE_LEVEL_TEXT = "Lv {}/{}"
UPGRADE_COST_TEXT = "{}"                # 가격 글자(숫자만, 단위 연구비는 머리 줄에 보인다)
UPGRADE_MAX_TEXT = "MAX"
UPGRADE_CURSOR_START = 0            # 패널을 처음 열었을 때 고른 줄 번호
UPGRADE_CURSOR_STEP = 1             # ↑↓ 한 번에 움직이는 줄 수
# 항목 줄 색: 살 수 있음(민트) / 살 수 없음(회색) / 마우스 올림(밝은 하늘)
COLOR_UPGRADE_ROW = COLOR_MINT_LIGHT
COLOR_UPGRADE_ROW_LIGHT = COLOR_WHITE
COLOR_UPGRADE_ROW_HOVER = COLOR_BUTTON_BRIGHT
COLOR_UPGRADE_ROW_OFF = COLOR_GRAY
COLOR_UPGRADE_ROW_OFF_LIGHT = COLOR_GRAY_LIGHT
COLOR_UPGRADE_TEXT_OFF = COLOR_BUTTON_TEXT_COOL
COLOR_UPGRADE_CURSOR = COLOR_PINK_DARK  # 고른 줄 화살표 색

# ---------------------------------------------------------------
# 21. 졸업 후: 환생과 대학원 (기획서 3절)
# ---------------------------------------------------------------
GRAD_YEAR_UNDERGRAD = 0     # 대학원 년차 값: 0이면 학부(1~4학년)
GRAD_FIRST_YEAR = 1         # 대학원에 들어가면 1년차부터
GRAD_YEAR_STEP = 1          # 년차 목표를 넘을 때마다 대학원 년차가 오르는 양 (끝없이)
# 대학원 n년차 -> n+1년차 목표(누적 지식) = 졸업 지식 2200 + (800 + 200 x (k-1))를 k = 1..n까지 더한 값
# -> 1년차 3000, 2년차 4000, 3년차 5200, 4년차 6600 … (기획서 3절)
GRAD_GOAL_FIRST_STEP = 800  # 1년차에 더 모아야 하는 지식
GRAD_GOAL_STEP_GROWTH = 200  # 해마다 더 모아야 하는 지식이 늘어나는 양
# 대학원 자연 감소 배수 = 1 + 1.0 x n + 1.5 x c
#   n = 대학원 년차, c = 대학원에 들어간 뒤 다 채운 60초 주기 수 (대학원에서만 시간 압박)
GRAD_DECAY_BONUS = 1.0      # 년차 하나마다 더하는 자연 감소 배수
GRAD_CYCLE_DECAY_BONUS = 2.5  # 대학원에서 60초 주기를 하나 다 채울 때마다 더하는 자연 감소 배수 (개운함 추가로 1.5 -> 2.5)
GRAD_CYCLES_NONE = 0        # 학부이거나 대학원 진입 시각이 없을 때의 대학원 주기 수
GRAD_MONEY_BONUS = 1.0      # n년차 연구비 획득 배수 = 1 + 1.0 x n
FAME_STEP = 1               # 졸업한 판에서 환생하면 오르는 명성
# 명성 칭호 (2026-11-24 추가): (이 명성 이상, 칭호). 보여 주기용이라 게임 수치에는 영향이 없다.
# 업그레이드를 모두 채우는 데 환생 약 20번이 걸려서 명예교수 = 사실상 완주
FAME_TITLES = [(0, "시간강사"), (2, "조교수"), (5, "부교수"), (10, "정교수"), (20, "명예교수")]
FAME_TITLE_PROMOTION_TEXT = "{} 승진!"   # 환생으로 칭호가 오르면 새 판 무대 오른쪽 위 알림

GRAD_YEAR_TEXT = "대학원 {}년차"        # 정보바 왼쪽 글자 (학부는 GRADE_TEXT)
PROMOTION_TEXT = "{}학년 진급!"          # 진급 알림 글자 (2초, 자동형 알림과 같은 모양)
GRAD_PROMOTION_TEXT = "대학원 {}년차!"   # 대학원 년차가 오를 때 알림 글자
PROMOTION_NOTICE_RIGHT = 780             # 진급 알림 상자 오른쪽 끝 x (무대 안쪽 오른쪽 위 구석)
ENDING_GRAD_TEXT = "대학원 {}년차 수료"  # 대학원에서 체력·멘탈 0이 되면 엔딩 이름
REINCARNATE_HINT_TEXT = "R: 환생 (명성 +1)"   # 졸업·수료 엔딩 안내 첫 줄
GRAD_SCHOOL_HINT_TEXT = "C: 대학원 진학"      # 졸업 엔딩 안내 둘째 줄
GRAD_SCHOOL_HINT_Y = 460    # 둘째 줄 가운데 y (첫 줄 RESTART_HINT_Y 428 아래, 패널 아래 끝 496 안)

# 엔딩 이름이 길면(예: "대학원 12년차 수료") 큰 글씨 대신 조금 작은 글씨로 그린다
ENDING_NAME_MAX_WIDTH = 520     # 큰 글씨 엔딩 이름이 넘으면 안 되는 가로 길이 (패널 608 안)
ENDING_LONG_FONT_SIZE = 44      # 긴 엔딩 이름 글자 크기
# 엔딩 화면에서 업그레이드 패널(왼쪽 x 12~268)을 열면 가운데 패널이 엔딩 이름을 가리지 않도록
# 가운데 패널과 엔딩 글자·그림을 오른쪽 무대 자리(x 284~788, 가운데 536)로 옮겨 그린다
ENDING_PANEL_OPEN_RECT = (STAGE_X, MENU_PANEL_RECT[1], STAGE_WIDTH, MENU_PANEL_RECT[3])
ENDING_OPEN_CENTER_X = STAGE_X + STAGE_WIDTH // 2      # 536
ENDING_NAME_MAX_WIDTH_OPEN = 456  # 옮겨 그릴 때 큰 글씨 엔딩 이름의 최대 가로 길이 (패널 504 안)

# ---------------------------------------------------------------
# 22. 무대 배경 4겹 (기획서 6절 "무대 배경 4겹")
#   1) 장소(학년) 2) 하늘(계절·시간대) 3) 행동 소품(마지막 자동 행동) 4) 시설(산 시설)
#   배경은 제자 무대 안쪽(x 288~784, y 120~456)에 그리고, 제자·파티클·팝업·알림보다 먼저 그린다.
#   좌표는 무대 안쪽 왼쪽 위를 (0, 0)으로 하는 도트 칸(4 x 4 픽셀) 단위다(가로 124칸, 세로 84칸).
# ---------------------------------------------------------------
# 계절: 60초 주기 안 0~15초 봄, 15~30초 여름, 30~45초 가을, 45~60초 겨울(시험 기간) (기획서 2절)
SEASON_SPRING = "spring"
SEASON_SUMMER = "summer"
SEASON_AUTUMN = "autumn"
SEASON_WINTER = "winter"
SEASONS = [SEASON_SPRING, SEASON_SUMMER, SEASON_AUTUMN, SEASON_WINTER]  # 주기 안 순서
SEASON_SECONDS = CYCLE_SECONDS // len(SEASONS)   # 계절 하나의 길이 15초 (= 시험 기간 길이)
INDEX_STEP = 1                     # 목록에서 다음 칸까지의 거리 (마지막 칸 번호 = 길이 - 1)
SINGLE_COUNT = 1                   # 사각형 조각 하나를 그릴 때의 개수

# 시간대: 계절 15초 안에서 낮(0~9초) -> 저녁(9~12초) -> 밤(12~15초)
TIME_DAY = "day"
TIME_EVENING = "evening"
TIME_NIGHT = "night"
DAY_END = 9.0                      # 계절 안에서 낮이 끝나는 시각(초)
EVENING_END = 12.0                 # 계절 안에서 저녁이 끝나는 시각(초). 그 뒤 15초까지 밤

# 하늘색이 부드럽게 바뀌는 기준점: (계절 안 시각(초), 시간대 색, 몇 계절 뒤의 색인지)
# 두 기준점 사이는 직선으로 섞는다(선형 보간). 낮색은 7.5초까지 그대로 -> 9.5초 저녁색
# -> 11초까지 그대로 -> 12.5초 밤색 -> 14초까지 그대로 -> 15초에 "다음 계절의 낮색".
# 그래서 계절·학년이 바뀌는 순간에도 하늘색이 끊기지 않는다(밤 -> 다음 날 아침).
SKY_KEYFRAMES = [
    (0.0, TIME_DAY, 0),
    (7.5, TIME_DAY, 0),
    (9.5, TIME_EVENING, 0),
    (11.0, TIME_EVENING, 0),
    (12.5, TIME_NIGHT, 0),
    (14.0, TIME_NIGHT, 0),
    (15.0, TIME_DAY, 1),
]
# 계절별 하늘색 {시간대: RGB}. 파스텔 레트로 팔레트
SKY_COLORS = {
    SEASON_SPRING: {TIME_DAY: (178, 222, 246), TIME_EVENING: (250, 196, 172),
                    TIME_NIGHT: (64, 66, 124)},
    SEASON_SUMMER: {TIME_DAY: (132, 202, 246), TIME_EVENING: (252, 172, 132),
                    TIME_NIGHT: (46, 54, 112)},
    SEASON_AUTUMN: {TIME_DAY: (192, 214, 236), TIME_EVENING: (242, 162, 122),
                    TIME_NIGHT: (58, 52, 102)},
    SEASON_WINTER: {TIME_DAY: (214, 226, 242), TIME_EVENING: (214, 184, 206),
                    TIME_NIGHT: (40, 44, 86)},
}

# 장소 id (학년별, 대학원은 연구실)
PLACE_LAWN = "lawn"                # 1학년 캠퍼스 잔디
PLACE_LECTURE = "lecture"          # 2학년 강의동
PLACE_LIBRARY = "library"          # 3학년 도서관 앞
PLACE_CEREMONY = "ceremony"        # 4학년 졸업식장
PLACE_LAB = "lab"                  # 대학원 연구실 (실내, 창문으로 하늘이 보인다)
PLACE_BY_GRADE = {1: PLACE_LAWN, 2: PLACE_LECTURE, 3: PLACE_LIBRARY, 4: PLACE_CEREMONY}

# 배경 그림을 미리 그려 두는 Surface에서 "비어 있음(하늘이 비침)"을 뜻하는 색.
# 이 색은 set_colorkey로 통째로 빼고 붙인다(반투명 아님). 다른 그림에는 쓰지 않는 자홍색
COLOR_KEY = (255, 0, 255)
SCENE_CELL = PIXEL_SIZE            # 배경 도트 1칸 크기(픽셀)

# 계절별 땅·나무 색. snow는 겨울에만 있는 눈(지붕·창틀 위). None이면 그리지 않는다
SEASON_COLORS = {
    SEASON_SPRING: {"ground": (156, 214, 146), "ground_light": (190, 232, 172),
                    "ground_dark": (118, 182, 116), "leaf": (246, 178, 200),
                    "leaf_light": (253, 214, 226), "leaf_dark": (222, 136, 168),
                    "accent": (253, 206, 222), "snow": None},
    SEASON_SUMMER: {"ground": (116, 198, 116), "ground_light": (152, 222, 142),
                    "ground_dark": (76, 158, 94), "leaf": (90, 178, 106),
                    "leaf_light": (142, 212, 132), "leaf_dark": (58, 138, 82),
                    "accent": (255, 220, 104), "snow": None},
    SEASON_AUTUMN: {"ground": (210, 190, 124), "ground_light": (228, 208, 152),
                    "ground_dark": (176, 146, 94), "leaf": (242, 152, 82),
                    "leaf_light": (250, 192, 122), "leaf_dark": (202, 106, 62),
                    "accent": (226, 88, 84), "snow": None},
    SEASON_WINTER: {"ground": (236, 240, 248), "ground_light": (255, 255, 255),
                    "ground_dark": (204, 210, 228), "leaf": (240, 244, 252),
                    "leaf_light": (255, 255, 255), "leaf_dark": (196, 204, 226),
                    "accent": (255, 255, 255), "snow": (255, 255, 255)},
}

# 저녁·밤 그늘: 바깥 장소의 땅·나무·건물 색을 밤 남색 쪽으로 조금 섞어 어둡게 그린다.
# 반투명 없이 색 값 자체를 바꿔 다시 그린다. 매 프레임 섞지 않고 몇 단계로만 바꾸며,
# 단계가 바뀔 때만 배경 그림을 새로 그린다(장소·계절·시설·단계 열쇠로 캐시).
# 단계가 바뀌는 시각은 하늘색이 바뀌는 구간(SKY_KEYFRAMES)의 가운데쯤에 맞춘다.
SCENE_SHADE_STEPS = [(0.0, 0), (8.5, 1), (11.75, 2), (14.5, 1)]  # (계절 안 시각(초), 그늘 단계)
SCENE_SHADE_RATIOS = [0.0, 0.12, 0.3]   # 단계별로 밤 남색을 섞는 비율 (0 = 원래 색)
SCENE_SHADE_COLOR = (30, 32, 74)        # 섞는 밤 남색
SCENE_SHADE_NONE = 0                    # 그늘 없음 단계(낮, 실내)
# 그늘을 넣는 장소: 바깥 장소만. 연구실은 실내라 불이 켜져 있으므로 넣지 않는다(창밖 하늘만 밤)
SCENE_SHADE_PLACES = [PLACE_LAWN, PLACE_LECTURE, PLACE_LIBRARY, PLACE_CEREMONY]

# 계절과 상관없는 배경 색 (이름 -> RGB)
SCENE_COLORS = {
    "outline": COLOR_OUTLINE,
    "white": COLOR_WHITE,
    "key": COLOR_KEY,
    "far": (206, 212, 236), "far_dark": (172, 180, 216),          # 먼 건물
    "glass": (204, 230, 250), "glass_dark": (132, 168, 214),      # 창문 유리
    "path": (234, 222, 198), "path_dark": (212, 196, 170),        # 길·광장 바닥
    "wood": (198, 152, 110), "wood_dark": (150, 104, 78),         # 나무(목재)
    "brick": (236, 178, 152), "brick_dark": (204, 140, 120),      # 벽돌 건물
    "roof": (150, 108, 128),                                      # 지붕
    "stone": (238, 234, 226), "stone_dark": (204, 198, 192),      # 돌 건물
    "door": (150, 104, 78),
    "banner": COLOR_PINK, "banner_light": COLOR_PINK_LIGHT,       # 졸업식 현수막
    "gold": (250, 210, 96),     # 금색 장식 (엔딩 학사모 술 색과 겹치지 않게 조금 다르게)
    "flag_mint": COLOR_MINT, "flag_sky": COLOR_SKY,
    "balloon_pink": COLOR_PINK_DARK, "balloon_sky": COLOR_SKY_DARK,
    "wall": (236, 232, 220), "wall_dark": (214, 206, 190),        # 연구실 벽
    "floor": (214, 178, 140), "floor_dark": (186, 146, 110),      # 연구실 바닥
    "board": (250, 250, 246), "board_frame": (160, 160, 182),     # 화이트보드
    "book_pink": COLOR_PINK, "book_mint": COLOR_MINT_DARK, "book_sky": COLOR_SKY_DARK,
    "book_yellow": COLOR_YELLOW,
    "plant": (96, 172, 112), "pot": (226, 150, 120),
    "lamp": (250, 236, 170),
    "cafe_wall": (252, 236, 214), "gym_wall": (178, 210, 244), "gym_dark": (110, 150, 210),
    "cup": COLOR_WHITE, "coffee": (150, 100, 70),
}

# 배경 조각 종류
PART_RECT = "rect"        # ("rect", 색 이름, 열, 행, 가로 칸, 세로 칸)
PART_WINDOWS = "windows"  # ("windows", 색 이름, 열, 행, 가로 개수, 세로 개수, 가로 칸, 세로 칸, 가로 간격, 세로 간격)
PART_SPRITE = "sprite"    # ("sprite", 스프라이트 이름, 열, 행)

# 배경 스프라이트: 이름 -> (문자열 격자, {글자: 색 이름}). "." 은 비어 있음
SCENE_SPRITES = {
    "tree": ([                                   # 나무 (잎 색이 계절 따라 바뀐다)
        "....oooooo....",
        "..ooLLLLLLoo..",
        ".oLLllLLLLLLo.",
        ".oLllLLLLaLdo.",
        "oLLlLLLLLLLLLo",
        "oLaLLLLLLLLdLo",
        "oLLLLLLLdLLLLo",
        "oLdLLLLaLLLLdo",
        ".oLLLLdLLLLLo.",
        ".oLLLLLLLLLdo.",
        "..oddLLLLddo..",
        "...ooddddoo...",
        ".....oTto.....",
        ".....oTto.....",
        ".....oTto.....",
        ".....oTto.....",
        ".....oTto.....",
        "....ooTtoo....",
    ], {"o": "outline", "L": "leaf", "l": "leaf_light", "d": "leaf_dark", "a": "accent",
        "T": "wood", "t": "wood_dark"}),
    "bush": ([                                   # 작은 덤불
        "..oooooo..",
        ".oLLlLLLo.",
        "oLlLLLaLLo",
        "oLLLLLLLdo",
        "oooooooooo",
    ], {"o": "outline", "L": "leaf", "l": "leaf_light", "d": "leaf_dark", "a": "accent"}),
    "bench": ([                                  # 벤치 (겨울에는 위에 눈)
        "ssssssssssssss",
        "oooooooooooooo",
        "oWWWWWWWWWWWWo",
        "oooooooooooooo",
        "oWWWWWWWWWWWWo",
        "oooooooooooooo",
        ".o..........o.",
        ".o..........o.",
    ], {"o": "outline", "W": "wood", "s": "snow"}),
    "flower": ([                                 # 꽃 (겨울에는 눈덩이)
        ".a.",
        "aya",
        ".g.",
    ], {"a": "accent", "y": "gold", "g": "leaf_dark"}),
    "lamp": ([                                   # 가로등
        "oooo",
        "oYYo",
        "oYYo",
        "oooo",
        ".oo.",
        ".oo.",
        ".oo.",
        ".oo.",
        ".oo.",
        ".oo.",
        ".oo.",
        ".oo.",
        ".oo.",
        "oooo",
    ], {"o": "outline", "Y": "lamp"}),
    "book": ([                                   # 도서관 박공의 펼친 책 표시
        ".oo..oo.",
        "oWWooWWo",
        "oWWooWWo",
        "oooooooo",
    ], {"o": "outline", "W": "white"}),
    "cap": ([                                    # 현수막 가운데 학사모
        "...oo...",
        ".oooooo.",
        "oooooooo",
        ".oooooy.",
        "..oooo.y",
    ], {"o": "outline", "y": "gold"}),
    "balloon_pink": ([                           # 풍선 (분홍)
        ".oooo.",
        "oBWBBo",
        "oBBBBo",
        "oBBBBo",
        ".oBBo.",
        "..oo..",
        "...o..",
        "..o...",
        "...o..",
        "..o...",
    ], {"o": "outline", "B": "balloon_pink", "W": "white"}),
    "balloon_sky": ([                            # 풍선 (하늘)
        ".oooo.",
        "oBWBBo",
        "oBBBBo",
        "oBBBBo",
        ".oBBo.",
        "..oo..",
        "...o..",
        "..o...",
        "...o..",
        "..o...",
    ], {"o": "outline", "B": "balloon_sky", "W": "white"}),
    "chair": ([                                  # 졸업식 의자
        "oooo..",
        "oCCo..",
        "oCCo..",
        "oCCooo",
        "oCCCCo",
        "oooooo",
        "o....o",
        "o....o",
    ], {"o": "outline", "C": "far_dark"}),
    "plant": ([                                  # 연구실 화분
        "..o..o..",
        ".oPo.oPo",
        "oPPooPPo",
        ".oPPPPo.",
        "..oPPo..",
        "...oo...",
        ".oooooo.",
        ".oRRRRo.",
        ".oRRRRo.",
        "..oRRo..",
        "..oooo..",
    ], {"o": "outline", "P": "plant", "R": "pot"}),
    # 시설 3개 (가로 16칸, 세로 18칸). s는 겨울 지붕 눈
    "library": ([
        "......ssss......",
        "......oooo......",
        "....ooRRRRoo....",
        "..ooRRRRRRRRoo..",
        "ooRRRRRRRRRRRRoo",
        "oooooooooooooooo",
        "oSSSSSoBBoSSSSSo",
        "oSSSSSoBBoSSSSSo",
        "oooooooooooooooo",
        "oScSScSSSScSScSo",
        "oScSScSooScSScSo",
        "oScSScoDDoScSSco",
        "oScSScoDDoScSSco",
        "oScSScoDDoScSSco",
        "oScSScoDDoScSSco",
        "oooooooooooooooo",
        "oSSSSSSSSSSSSSSo",
        "oooooooooooooooo",
    ], {"o": "outline", "R": "roof", "S": "stone", "c": "stone_dark", "B": "book_sky",
        "D": "door", "s": "snow"}),
    "cafe": ([
        "ssssssssssssssss",
        "oooooooooooooooo",
        "oWWWWWWWWWWWWWWo",
        "oWWWWoCCoWWWWWWo",
        "oWWWWoKKooWWWWWo",
        "oWWWWoKKoWWWWWWo",
        "oWWWWWooWWWWWWWo",
        "oooooooooooooooo",
        "oPWPWPWPWPWPWPWo",
        "oPWPWPWPWPWPWPWo",
        ".oooooooooooooo.",
        ".oWWWWWWWWWWWWo.",
        ".oGGGGGWoDDDDWo.",
        ".oGGGGGWoDDDDWo.",
        ".oGGGGGWoDDDDWo.",
        ".oWWWWWWoDDDDWo.",
        ".oWWWWWWoDDDDWo.",
        ".oooooooooooooo.",
    ], {"o": "outline", "W": "cafe_wall", "C": "cup", "K": "coffee", "P": "banner",
        "G": "glass", "D": "door", "s": "snow"}),
    "gym": ([
        "ssssssssssssssss",
        "oooooooooooooooo",
        "oNNNNNNNNNNNNNNo",
        "oNooNNNNNNNNooNo",
        "oNooooooooooooNo",
        "oNooNNNNNNNNooNo",
        "oNNNNNNNNNNNNNNo",
        "oooooooooooooooo",
        "oBBBBBBBBBBBBBBo",
        "oBGGGBGGGBGGGBBo",
        "oBGGGBGGGBGGGBBo",
        "oBBBBBBBBBBBBBBo",
        "oBGGGBBoDDDDoBBo",
        "oBGGGBBoDDDDoBBo",
        "oBBBBBBoDDDDoBBo",
        "oBBBBBBoDDDDoBBo",
        "oBBBBBBoDDDDoBBo",
        "oooooooooooooooo",
    ], {"o": "outline", "N": "gym_dark", "B": "gym_wall", "G": "glass", "D": "door",
        "s": "snow"}),
}

GROUND_ROW = 45                     # 바깥 장소의 땅이 시작하는 행 (무대 안쪽 y 180, 화면 y 300)
OUTDOOR_GROUND = [                  # 바깥 장소 공통 땅(계절 색)
    (PART_RECT, "ground", 0, GROUND_ROW, 124, 39),
    (PART_RECT, "ground_light", 0, GROUND_ROW, 124, 1),
    (PART_WINDOWS, "ground_dark", 4, 50, 8, 4, 2, 1, 16, 9),   # 풀잎 무늬
]

# 장소별 배경 조각: back(시설보다 뒤), front(시설보다 앞, 주로 땅 위 물건)
PLACE_BACK = {
    PLACE_LAWN: OUTDOOR_GROUND + [
        (PART_RECT, "far", 34, 28, 56, 17),                      # 먼 강의동
        (PART_RECT, "far_dark", 34, 26, 56, 2),
        (PART_RECT, "snow", 34, 25, 56, 1),
        (PART_WINDOWS, "glass", 37, 30, 8, 3, 4, 3, 6, 5),
        # 강의동 왼쪽에서 왼쪽 아래 구석으로 비스듬히 넓어지는 길.
        # 제자(무대 가운데, 열 52~72) 바로 아래로 내려오면 몸통처럼 보여서 왼쪽으로 비켜 둔다
        (PART_RECT, "path", 36, 45, 6, 3),
        (PART_RECT, "path", 33, 48, 7, 3),
        (PART_RECT, "path", 30, 51, 8, 3),
        (PART_RECT, "path", 26, 54, 9, 4),
        (PART_RECT, "path", 21, 58, 11, 4),
        (PART_RECT, "path", 15, 62, 13, 5),
        (PART_RECT, "path", 8, 67, 15, 6),
        (PART_RECT, "path", 0, 73, 17, 11),
        (PART_SPRITE, "tree", 20, 27),
        (PART_SPRITE, "tree", 76, 27),
    ],
    PLACE_LECTURE: OUTDOOR_GROUND + [
        (PART_RECT, "path", 18, 45, 88, 6),                      # 건물 앞 광장
        (PART_RECT, "path_dark", 18, 45, 88, 1),
        (PART_RECT, "brick", 22, 10, 80, 35),                    # 강의동 벽돌 건물
        (PART_RECT, "brick_dark", 22, 42, 80, 3),
        (PART_RECT, "roof", 20, 7, 84, 3),
        (PART_RECT, "snow", 20, 6, 84, 1),
        (PART_WINDOWS, "glass", 26, 13, 9, 2, 6, 5, 8, 9),
        (PART_WINDOWS, "glass_dark", 26, 17, 9, 2, 6, 1, 8, 9),
        (PART_RECT, "outline", 55, 31, 14, 14),                  # 현관
        (PART_RECT, "door", 56, 32, 12, 13),
        (PART_RECT, "glass", 57, 34, 4, 6),
        (PART_RECT, "glass", 63, 34, 4, 6),
        (PART_WINDOWS, "brick_dark", 22, 10, 2, 1, 2, 32, 78, 0),  # 양 끝 기둥
        (PART_SPRITE, "bush", 24, 40),
        (PART_SPRITE, "bush", 90, 40),
    ],
    PLACE_LIBRARY: OUTDOOR_GROUND + [
        (PART_RECT, "path", 22, 45, 80, 8),                      # 앞마당
        (PART_RECT, "stone", 26, 18, 72, 27),                    # 도서관 본관
        (PART_RECT, "stone_dark", 22, 16, 80, 2),                # 박공(계단 모양 지붕)
        (PART_RECT, "stone", 30, 13, 64, 3),
        (PART_RECT, "stone", 40, 10, 44, 3),
        (PART_RECT, "stone", 52, 7, 20, 3),
        (PART_RECT, "snow", 52, 6, 20, 1),
        (PART_RECT, "snow", 40, 9, 12, 1),
        (PART_RECT, "snow", 72, 9, 12, 1),
        (PART_SPRITE, "book", 58, 10),
        (PART_WINDOWS, "stone_dark", 28, 19, 8, 1, 3, 26, 9, 0),  # 기둥
        (PART_WINDOWS, "glass_dark", 33, 23, 7, 1, 3, 10, 9, 0),  # 긴 창
        (PART_RECT, "stone_dark", 20, 45, 84, 2),                # 계단
        (PART_RECT, "stone", 18, 47, 88, 2),
        (PART_RECT, "stone_dark", 18, 49, 88, 1),
        (PART_SPRITE, "lamp", 20, 31),
        (PART_SPRITE, "lamp", 100, 31),
    ],
    PLACE_CEREMONY: OUTDOOR_GROUND + [
        (PART_RECT, "wood_dark", 22, 8, 2, 37),                  # 현수막 기둥
        (PART_RECT, "wood_dark", 100, 8, 2, 37),
        (PART_RECT, "outline", 23, 7, 78, 12),                   # 현수막
        (PART_RECT, "banner", 24, 8, 76, 10),
        (PART_RECT, "banner_light", 24, 8, 76, 1),
        (PART_WINDOWS, "gold", 28, 12, 6, 1, 2, 2, 6, 0),
        (PART_WINDOWS, "gold", 62, 12, 6, 1, 2, 2, 6, 0),
        (PART_SPRITE, "cap", 58, 10),
        (PART_WINDOWS, "flag_mint", 26, 19, 7, 1, 3, 3, 12, 0),  # 깃발 줄
        (PART_WINDOWS, "flag_sky", 32, 19, 6, 1, 3, 3, 12, 0),
        (PART_RECT, "outline", 29, 37, 66, 8),                   # 단상
        (PART_RECT, "wood", 30, 38, 64, 7),
        (PART_RECT, "wood_dark", 30, 43, 64, 2),
        (PART_RECT, "banner", 54, 38, 16, 4),
        (PART_SPRITE, "balloon_pink", 12, 18),
        (PART_SPRITE, "balloon_sky", 106, 20),
    ],
    PLACE_LAB: [
        (PART_RECT, "wall", 0, 0, 124, 62),                      # 벽
        (PART_RECT, "wall_dark", 0, 56, 124, 6),
        (PART_RECT, "floor", 0, 62, 124, 22),                    # 바닥
        (PART_RECT, "floor_dark", 0, 62, 124, 1),
        (PART_WINDOWS, "floor_dark", 6, 63, 8, 1, 1, 21, 16, 0),
        (PART_RECT, "wood", 68, 6, 44, 32),                      # 창틀
        (PART_RECT, "key", 70, 8, 19, 28),                       # 창유리(하늘이 비친다)
        (PART_RECT, "key", 91, 8, 19, 28),
        (PART_RECT, "ground", 70, 30, 19, 6),                    # 창밖 땅
        (PART_RECT, "ground", 91, 30, 19, 6),
        (PART_RECT, "ground_light", 70, 30, 40, 1),
        (PART_SPRITE, "bush", 72, 25),
    ],
}
PLACE_FRONT = {
    PLACE_LAWN: [
        # 벤치는 길·행동 소품(열 86~110, 행 62~75)과 겹치지 않는 자리에 둔다
        (PART_SPRITE, "bench", 4, 50),
        (PART_SPRITE, "bench", 106, 49),
        (PART_SPRITE, "flower", 42, 52),
        (PART_SPRITE, "flower", 40, 72),
        (PART_SPRITE, "flower", 80, 56),
        (PART_SPRITE, "flower", 94, 78),
        (PART_SPRITE, "flower", 26, 78),
        (PART_SPRITE, "flower", 116, 62),
    ],
    PLACE_LECTURE: [
        (PART_SPRITE, "flower", 12, 60),
        (PART_SPRITE, "flower", 30, 74),
        (PART_SPRITE, "flower", 96, 58),
        (PART_SPRITE, "flower", 110, 76),
    ],
    PLACE_LIBRARY: [
        (PART_SPRITE, "flower", 8, 62),
        (PART_SPRITE, "flower", 26, 76),
        (PART_SPRITE, "flower", 100, 60),
        (PART_SPRITE, "flower", 114, 74),
    ],
    PLACE_CEREMONY: [
        (PART_SPRITE, "chair", 4, 64),                           # 왼쪽 의자 줄
        (PART_SPRITE, "chair", 12, 64),
        (PART_SPRITE, "chair", 20, 64),
        (PART_SPRITE, "chair", 28, 64),
        (PART_SPRITE, "chair", 4, 75),
        (PART_SPRITE, "chair", 12, 75),
        (PART_SPRITE, "chair", 20, 75),
        (PART_SPRITE, "chair", 28, 75),
        (PART_SPRITE, "chair", 90, 75),                          # 오른쪽 의자 줄
        (PART_SPRITE, "chair", 98, 75),
        (PART_SPRITE, "chair", 106, 75),
        (PART_SPRITE, "chair", 114, 75),
    ],
    PLACE_LAB: [
        (PART_RECT, "wood", 89, 6, 2, 32),                       # 창 가운데 살
        (PART_RECT, "wood_dark", 66, 38, 48, 2),                 # 창턱
        (PART_RECT, "snow", 68, 37, 44, 1),
        (PART_RECT, "wood_dark", 4, 12, 24, 50),                 # 책장
        (PART_RECT, "wood", 6, 14, 20, 46),
        (PART_WINDOWS, "wood_dark", 6, 25, 1, 3, 20, 1, 0, 12),
        (PART_WINDOWS, "book_pink", 7, 16, 3, 4, 2, 9, 6, 12),
        (PART_WINDOWS, "book_sky", 9, 17, 3, 4, 2, 8, 6, 12),
        (PART_WINDOWS, "book_yellow", 11, 18, 3, 4, 2, 7, 6, 12),
        (PART_RECT, "board_frame", 32, 10, 32, 20),              # 화이트보드
        (PART_RECT, "board", 33, 11, 30, 18),
        (PART_RECT, "book_sky", 36, 14, 12, 1),
        (PART_RECT, "book_sky", 36, 17, 16, 1),
        (PART_RECT, "book_pink", 36, 20, 9, 1),
        (PART_RECT, "book_mint", 50, 23, 2, 4),
        (PART_RECT, "book_mint", 53, 21, 2, 6),
        (PART_RECT, "book_mint", 56, 18, 2, 9),
        (PART_RECT, "board_frame", 38, 30, 20, 1),
        (PART_SPRITE, "plant", 114, 51),
    ],
}

# 시설: 업그레이드 id -> 스프라이트 이름. 레벨 1 이상이면 무대 뒤쪽에 건물이 생긴다
FACILITY_SPRITES = {
    UPGRADE_LIBRARY: "library",
    UPGRADE_CAFE: "cafe",
    UPGRADE_GYM: "gym",
}
FACILITY_IDS = [UPGRADE_LIBRARY, UPGRADE_CAFE, UPGRADE_GYM]
FACILITY_OWNED_LEVEL = 1           # 이 레벨 이상이면 시설이 있다
# 시설 자리: 장소 -> {업그레이드 id: (왼쪽 x 픽셀, 아래 끝 y 픽셀, 도트 칸 크기)} (무대 안쪽 기준)
# 바깥 장소는 땅 시작선(y 180) 위 양옆, 연구실은 창밖에 작게(칸 2픽셀) 보인다
OUTDOOR_FACILITY_SLOTS = {
    UPGRADE_LIBRARY: (4, GROUND_ROW * SCENE_CELL, SCENE_CELL),
    UPGRADE_CAFE: (360, GROUND_ROW * SCENE_CELL, SCENE_CELL),
    UPGRADE_GYM: (428, GROUND_ROW * SCENE_CELL, SCENE_CELL),
}
LAB_FACILITY_CELL = 2
FACILITY_SLOTS = {
    PLACE_LAWN: OUTDOOR_FACILITY_SLOTS,
    PLACE_LECTURE: OUTDOOR_FACILITY_SLOTS,
    PLACE_LIBRARY: OUTDOOR_FACILITY_SLOTS,
    PLACE_CEREMONY: OUTDOOR_FACILITY_SLOTS,
    PLACE_LAB: {
        UPGRADE_LIBRARY: (318, 124, LAB_FACILITY_CELL),
        UPGRADE_CAFE: (368, 124, LAB_FACILITY_CELL),
        UPGRADE_GYM: (402, 124, LAB_FACILITY_CELL),
    },
}

# 해·달·별 (하늘 겹, 매 프레임 그린다). 위치는 무대 안쪽 기준 픽셀
SUN_SPRITE = [
    "..YYYY..",
    ".YyyYYY.",
    "YyyYYYYY",
    "YyYYYYYY",
    "YYYYYYYY",
    "YYYYYYYY",
    ".YYYYYY.",
    "..YYYY..",
]
MOON_SPRITE = [
    "..MMM...",
    ".MMm....",
    "MMm.....",
    "MMm.....",
    "MMm.....",
    "MMMm....",
    ".MMMMMM.",
    "..MMMM..",
]
SUN_COLORS = {"Y": (255, 220, 104), "y": (255, 244, 196)}           # 낮 해
EVENING_SUN_COLORS = {"Y": (246, 140, 96), "y": (252, 196, 150)}    # 저녁 해(노을)
MOON_COLORS = {"M": (255, 244, 196), "m": (226, 214, 160)}
COLOR_STAR_NIGHT = (255, 244, 196)  # 밤하늘 별 도트
# 장소 -> {시간대: 해·달 왼쪽 위 (x, y)}. 연구실은 창유리 안쪽에 보이게
OUTDOOR_SKY_POS = {TIME_DAY: (440, 16), TIME_EVENING: (440, 64), TIME_NIGHT: (440, 16)}
SKY_OBJECT_POS = {
    PLACE_LAWN: OUTDOOR_SKY_POS,
    PLACE_LECTURE: OUTDOOR_SKY_POS,
    PLACE_LIBRARY: OUTDOOR_SKY_POS,
    PLACE_CEREMONY: OUTDOOR_SKY_POS,
    PLACE_LAB: {TIME_DAY: (288, 40), TIME_EVENING: (288, 80), TIME_NIGHT: (288, 40)},
}
STAR_POSITIONS = [(40, 20), (120, 44), (200, 12), (260, 56), (332, 24), (396, 100),
                  (152, 84), (476, 104), (64, 96), (300, 92), (336, 44), (380, 56),
                  (420, 72), (424, 40)]

# 행동 소품: 마지막 자동 행동 -> 스프라이트. 다음 행동 전까지 제자 오른쪽 땅에 보인다
PROP_SPRITES = {
    ACTION_STUDY: [                    # 책상과 책
        "....oooooo.......oo...",
        "....oPPPPo......oYYo..",
        "...oooooooo....oYYo...",
        "...oSSSSSSo...oYYo....",
        "...oooooooo..ooo......",
        "oooooooooooooooooooooo",
        "oWWWWWWWWWWWWWWWWWWWWo",
        "oooooooooooooooooooooo",
        ".oDo..............oDo.",
        ".oDo..............oDo.",
        ".oDo..............oDo.",
        ".oDo..............oDo.",
        ".ooo..............ooo.",
    ],
    ACTION_REST: [                     # 이불과 베개
        "..........oooooooooooooo",
        "oooooo...oSSSSSSSSSSSSSo",
        "oCCCCCo.oSSsSSSSsSSSSsSo",
        "oCCCCCCooSSSSSSSSSSSSSSo",
        "oCCCCCCCoSSSsSSSSsSSSSso",
        "oooooooooooooooooooooooo",
        "oWWWWWWWWWWWWWWWWWWWWWWo",
        "oooooooooooooooooooooooo",
    ],
    ACTION_FEED: [                     # 식판 (밥·국·반찬)
        "...ooo......ooo...",
        "..oCCCo....oAAAo..",
        ".oCCCCCo..oAAAAAo.",
        ".oCCCCCo..oAAAAAo.",
        "..ooooo....ooooo..",
        "oooooooooooooooooo",
        "oTGGoTTTTTTTToRRTo",
        "oTGGoTTTTTTTToRRTo",
        "oooooooooooooooooo",
    ],
}
PROP_COLORS = {
    "o": COLOR_OUTLINE, "P": COLOR_PINK, "S": COLOR_SKY, "s": COLOR_SKY_LIGHT,
    "Y": COLOR_YELLOW, "W": (198, 152, 110), "D": (150, 104, 78),
    "C": COLOR_WHITE, "A": COLOR_APRICOT, "T": COLOR_MINT, "G": (120, 196, 120),
    "R": COLOR_PINK_DARK,
}
PROP_X = 344                        # 소품 왼쪽 x (무대 안쪽 기준, 제자 오른쪽)
PROP_BOTTOM = 300                   # 소품 아래 끝 y (무대 안쪽 기준)

# ---------------------------------------------------------------
# 23. 화면 다듬기: 업그레이드 툴팁, 무대 장식 13종, 상태 아이콘
# ---------------------------------------------------------------
# 툴팁 공통: 패널(업그레이드·상태) 오른쪽 무대 위에 뜨는 크림색 도트 상자(반투명 없음).
# 패널 오른쪽 끝 268 + 그림자·간격 8 = 276부터 그려서 패널과 겹치지 않는다.
# 위로는 무대 위 끝(116)보다 올라가지 않으므로 정보바·목표 막대·시험 배너를 가리지 않고,
# 아래로는 무대 아래 끝(460)을 넘지 않는다(방침 버튼을 가리지 않음).
TOOLTIP_X = STATUS_PANEL_X + STATUS_PANEL_WIDTH + PIXEL_SIZE * 2   # 276
TOOLTIP_TOP_MIN = PANEL_Y                    # 툴팁 상자 위쪽 y의 최솟값 (116)
TOOLTIP_BOTTOM_MAX = PANEL_Y + PANEL_HEIGHT  # 툴팁 상자 아래 끝(그림자 포함)의 최댓값 (460)
TOOLTIP_RIGHT_MAX = SCREEN_WIDTH - PIXEL_SIZE * 2   # 툴팁 상자 오른쪽 끝의 최댓값 (792)
TOOLTIP_PAD_X = PIXEL_SIZE * 3               # 상자 바깥 끝에서 글자까지 왼쪽·오른쪽 여백 (외곽선 포함 12)
TOOLTIP_PAD_Y = PIXEL_SIZE * 2               # 상자 바깥 끝에서 글자까지 위·아래 여백 (외곽선 포함 8)
TOOLTIP_LINE_HEIGHT = 19                     # 툴팁 글자 한 줄 높이 (작은 글자 14)
TOOLTIP_MIN_WIDTH = 168                      # 툴팁 상자 최소 가로 길이
COLOR_TOOLTIP = COLOR_BG                     # 툴팁 몸통 (크림)
COLOR_TOOLTIP_LIGHT = COLOR_PANEL_LIGHT      # 툴팁 위 하이라이트 줄
COLOR_TOOLTIP_TITLE = COLOR_TEXT             # 첫 줄(이름·레벨) 글자 색
COLOR_TOOLTIP_TEXT = COLOR_TEXT_SOFT         # 보통 줄 글자 색
COLOR_TOOLTIP_WARN = COLOR_RED_DARK          # "연구비가 모자라요" 글자 색

# 업그레이드 툴팁 글자 (모두 config 값으로 계산해 채운다)
UPGRADE_TIP_TITLE = "{}  Lv {}/{}"           # 이름, 지금 레벨, 최대 레벨
UPGRADE_TIP_NOW = "지금: {}"                 # 지금 레벨의 효과
UPGRADE_TIP_NOW_NONE = "지금: 아직 없음"      # 0레벨
UPGRADE_TIP_NEXT = "다음: {}"                # 다음 레벨의 효과
UPGRADE_TIP_MAXED = "다음: 최고 레벨"          # 최고 레벨이면
UPGRADE_TIP_COST = "가격: 연구비 {}"
UPGRADE_TIP_COST_MAX = "가격: MAX"
UPGRADE_TIP_POOR = "연구비가 모자라요"
# 업그레이드 id -> 레벨 효과 글자 틀. 채우는 값 = 레벨 x 레벨당 효과(UPGRADE_PER_LEVEL).
# 방침 배수는 곱하지 않은 기본 효과다. "{:.0%}"는 0.15 -> "15%" 처럼 쓴다
UPGRADE_LEVEL_EFFECTS = {
    UPGRADE_MENU: "든든함 지속 +{:g}초",
    UPGRADE_BED: "휴식 체력·멘탈 +{:g}",
    UPGRADE_BOOK: "공부 지식 +{:g}",
    UPGRADE_TIME: "자동 행동 간격 -{:g}초",
    UPGRADE_HEALTH_CARE: "자연 감소 -{:.0%}",
    UPGRADE_LIBRARY: "공부 지식 +{:g}",
    UPGRADE_CAFE: "휴식 체력 +{:g}",
    UPGRADE_GYM: "공부 체력 소모 -{:g}",
    UPGRADE_CHARM: "이벤트 확률 +{:.0%}p",
    UPGRADE_SCHOLARSHIP: "장학금 이벤트 (연구비 {:g} x 학년)",
    UPGRADE_HEALTH_MAX: "체력 최대 +{:g}",
    UPGRADE_MENTAL_MAX: "멘탈 최대 +{:g}",
    UPGRADE_SELF_CARE: "1초마다 체력·멘탈 +{:g}",
}
# 업그레이드 id -> 무대 장식 한 줄 설명 (툴팁 4번째 줄)
UPGRADE_DECOR_TEXTS = {
    UPGRADE_MENU: "무대: 도시락이 생겨요",
    UPGRADE_BED: "무대: 쿠션이 생겨요",
    UPGRADE_BOOK: "무대: 책장이 생겨요 (책 = Lv)",
    UPGRADE_TIME: "무대: 벽시계가 생겨요",
    UPGRADE_HEALTH_CARE: "무대: 비타민 병이 생겨요",
    UPGRADE_LIBRARY: "무대: 도서관 건물이 생겨요",
    UPGRADE_CAFE: "무대: 카페 건물이 생겨요",
    UPGRADE_GYM: "무대: 헬스장 건물이 생겨요",
    UPGRADE_CHARM: "무대: 부적 걸이 (부적 = Lv)",
    UPGRADE_SCHOLARSHIP: "무대: 트로피가 생겨요",
    UPGRADE_HEALTH_MAX: "무대: 덤벨이 생겨요",
    UPGRADE_MENTAL_MAX: "무대: 화분이 생겨요",
    UPGRADE_SELF_CARE: "무대: 요가 매트가 생겨요",
}

# 상태 배지 아이콘: 배지 안 왼쪽에 작은 도트 아이콘(8 x 6칸, 칸 2픽셀 = 16 x 12픽셀) + 이름.
# 배지 안쪽 높이가 16픽셀이라 아이콘은 12픽셀로 세로 가운데에 둔다
STATUS_ICON_CELL = PIXEL_SIZE // 2           # 아이콘 도트 1칸 크기(2픽셀)
STATUS_ICON_GAP = PIXEL_SIZE                 # 아이콘과 이름 글자 사이 간격
STATUS_ICON_PAD = PIXEL_SIZE                 # 배지 안쪽 왼쪽 끝과 아이콘 사이 여백
STATUS_ICONS = {
    DEBUFF_TIRED: [                          # 피곤: 졸음 표시 Zz
        "zzzz....",
        "...z....",
        "..z.zzz.",
        ".z....z.",
        "zzzz.z..",
        "....zzz.",
    ],
    DEBUFF_DEPRESSED: [                      # 우울: 비구름
        "..ooo...",
        ".occcoo.",
        "occcccco",
        ".oooooo.",
        "..r..r..",
        ".r..r...",
    ],
    BUFF_FULL: [                             # 든든함: 김 나는 밥그릇
        ".s..s...",
        ".wwwwww.",
        "oooooooo",
        "obbbbbbo",
        ".obbbbo.",
        "..oooo..",
    ],
    BUFF_REFRESH: [                          # 개운함: 물방울 (푹 쉬고 난 맑은 기분)
        "...o....",
        "..oWo...",
        ".oWrro..",
        ".orrro..",
        ".orrro..",
        "..ooo...",
    ],
    CONDITION_GOOD: [                        # 컨디션 좋음: 반짝 별
        "...o....",
        "..oWo...",
        "ooWWWoo.",
        ".oWWWo..",
        ".oWoWo..",
        ".o...o..",
    ],
}
STATUS_ICON_COLORS = {
    "o": COLOR_OUTLINE, "z": COLOR_OUTLINE, "c": COLOR_CLOUD, "r": COLOR_SKY_DARK,
    "s": COLOR_CLOUD_SHADE, "w": COLOR_WHITE, "b": COLOR_PINK_DARK, "W": COLOR_WHITE,
}
# 상태 배지 툴팁 글자 틀 (값은 config 상수와 지금 상태로 채운다)
STATUS_TIP_TEXTS = {
    DEBUFF_TIRED: "{name}: 체력 {limit} 미만 — 공부 지식 ×{ratio:g}",
    DEBUFF_DEPRESSED: "{name}: 멘탈 {limit} 미만 — 버는 연구비 ×{ratio:g}",
    BUFF_FULL: "{name}: 남은 시간 {left}초 — 체력 감소 ×{ratio:g}",
    BUFF_REFRESH: "{name}: 남은 시간 {left}초 — 멘탈 감소 ×{ratio:g}",
    CONDITION_GOOD: "{name}: 휴식 위주, 체력·멘탈 {limit} 이상 — 버는 연구비 ×{ratio:g}",
}
# 특성 배지 툴팁: "{이름}: {효과들} (이번 판 끝까지)". 효과 = TRAIT_BONUSES의 보정 이름별 글자 틀
TRAIT_TIP_TEXT = "{name}: {effects} (이번 판 끝까지)"
TRAIT_TIP_EFFECTS = {
    BONUS_FULL_TIME: "학식 든든함 +{bonus}초",
    BONUS_REST_MENTAL: "휴식 멘탈 +{bonus}",
    BONUS_REST_HEALTH: "휴식 체력 +{bonus}",
    BONUS_STUDY_HEALTH: "공부 체력 소모 -{bonus}",
    BONUS_STUDY_KNOWLEDGE: "공부 지식 +{bonus}",
    BONUS_STUDY_MENTAL: "공부 멘탈 소모 -{bonus}",
}
TRAIT_TIP_JOIN = ", "               # 효과가 여럿이면 사이에 넣는 글자

# 무대 장식: 시설이 아닌 업그레이드 10종은 레벨 1부터 무대에 작은 도트 소품이 생긴다.
# 시설 3종(도서관·카페·헬스장)은 예전처럼 건물(FACILITY_SPRITES)이다.
# 장식은 배경 그림(make_scenery)에 함께 그려 캐시한다(열쇠에 장식 레벨이 들어간다).
# 그래서 바깥 장소에서는 저녁·밤 그늘도 배경과 똑같이 받는다(시설과 같은 규칙).
SCENE_COLORS.update({
    "lunch_lid": COLOR_PINK, "lunch_lid2": COLOR_MINT_DARK, "lunch_box": COLOR_APRICOT,
    "rice": COLOR_WHITE, "nori": (64, 84, 72),
    "cushion_sky": COLOR_SKY, "cushion_sky_light": COLOR_SKY_LIGHT,
    "cushion_pink": COLOR_PINK, "cushion_pink_light": COLOR_PINK_LIGHT,
    "cushion_yellow": COLOR_YELLOW, "cushion_yellow_light": COLOR_YELLOW_LIGHT,
    "shelf_back": (150, 104, 78), "book_apricot": COLOR_APRICOT,
    "clock_face": COLOR_WHITE, "clock_window": (110, 76, 64),
    "vitamin_orange": (246, 156, 72), "vitamin_green": (120, 196, 120),
    "vitamin_pink": COLOR_PINK_DARK,
    "charm_red": (226, 88, 84), "charm_sky": COLOR_SKY_DARK,
    "trophy_light": (255, 244, 196),
    "dumbbell": (92, 96, 130), "kettle": (232, 82, 90),
    "bloom": COLOR_PINK_DARK, "mat": COLOR_MINT_DARK, "mat_light": COLOR_MINT,
    "mat_roll": COLOR_PINK, "water": COLOR_SKY,
})
DECOR_BOOK = ["PP", "PP", "ww", "PP", "PP"]        # 책장에 꽂힌 책 한 권 (2 x 5)
DECOR_CUSHION = [".ooooo.", "oClCCCo", "oCCClCo", ".ooooo."]   # 쿠션 (7 x 4)
DECOR_LUNCHBOX = ["oooooooo", "oPPPPPPo", "oooooooo", "oBBBBBBo", "oooooooo"]  # 도시락 (8 x 5)
DECOR_VITAMIN = ["oooo", "oCCo", "oooo", "oVVo", "oLVo", "oooo"]   # 비타민 병 (4 x 6)
DECOR_CHARM = [".o.", "ooo", "oRo", "oYo", "oRo", "ooo"]           # 부적 (3 x 6)
SCENE_SPRITES.update({
    "decor_lunchbox": (DECOR_LUNCHBOX, {"o": "outline", "P": "lunch_lid", "B": "lunch_box"}),
    "decor_lunchbox2": (DECOR_LUNCHBOX, {"o": "outline", "P": "lunch_lid2", "B": "lunch_box"}),
    "decor_riceball": ([                         # 주먹밥 (5 x 5)
        "..o..",
        ".oWo.",
        "oWWWo",
        "oNNNo",
        "ooooo",
    ], {"o": "outline", "W": "rice", "N": "nori"}),
    "decor_cushion_sky": (DECOR_CUSHION,
                          {"o": "outline", "C": "cushion_sky", "l": "cushion_sky_light"}),
    "decor_cushion_pink": (DECOR_CUSHION,
                           {"o": "outline", "C": "cushion_pink", "l": "cushion_pink_light"}),
    "decor_cushion_yellow": (DECOR_CUSHION, {"o": "outline", "C": "cushion_yellow",
                                             "l": "cushion_yellow_light"}),
    "decor_shelf": ([                            # 낮은 책장 (14 x 9), 안쪽 10칸에 책이 꽂힌다
        "oooooooooooooo",
        "oWWWWWWWWWWWWo",
        "oWKKKKKKKKKKWo",
        "oWKKKKKKKKKKWo",
        "oWKKKKKKKKKKWo",
        "oWKKKKKKKKKKWo",
        "oWKKKKKKKKKKWo",
        "oWWWWWWWWWWWWo",
        "oooooooooooooo",
    ], {"o": "outline", "W": "wood", "K": "shelf_back"}),
    "decor_book_pink": (DECOR_BOOK, {"P": "book_pink", "w": "white"}),
    "decor_book_mint": (DECOR_BOOK, {"P": "book_mint", "w": "white"}),
    "decor_book_sky": (DECOR_BOOK, {"P": "book_sky", "w": "white"}),
    "decor_book_yellow": (DECOR_BOOK, {"P": "book_yellow", "w": "white"}),
    "decor_book_apricot": (DECOR_BOOK, {"P": "book_apricot", "w": "white"}),
    "decor_clock": ([                            # 벽시계(괘종시계) (7 x 13): 시계판 + 추 상자
        "..ooo..",
        ".oWWWo.",
        "oWWoWWo",
        "oWWooWo",
        "oWWWWWo",
        ".oWWWo.",
        "..ooo..",
        ".ooooo.",
        ".oTTTo.",
        ".oKKKo.",
        ".oKKKo.",
        ".oTTTo.",
        ".ooooo.",
    ], {"o": "outline", "W": "clock_face", "T": "wood", "K": "clock_window"}),
    "decor_pendulum": ([".o.", "oYo"], {"o": "outline", "Y": "gold"}),   # 추 (Lv3)
    "decor_clock_bells": ([                      # 시계 위 종 두 개 (Lv5)
        "YY...YY",
        ".o...o.",
    ], {"o": "outline", "Y": "gold"}),
    "decor_vitamin_orange": (DECOR_VITAMIN, {"o": "outline", "C": "white",
                                             "V": "vitamin_orange", "L": "white"}),
    "decor_vitamin_green": (DECOR_VITAMIN, {"o": "outline", "C": "white",
                                            "V": "vitamin_green", "L": "white"}),
    "decor_vitamin_pink": (DECOR_VITAMIN, {"o": "outline", "C": "white",
                                           "V": "vitamin_pink", "L": "white"}),
    "decor_charm_rack": ([                       # 부적 걸이 (11 x 10): 나무 막대 + 기둥 2개
        "ooooooooooo",
        "oTTTTTTTTTo",
        "ooooooooooo",
        "o.........o",
        "o.........o",
        "o.........o",
        "o.........o",
        "o.........o",
        "o.........o",
        "o.........o",
    ], {"o": "outline", "T": "wood"}),
    "decor_charm_red": (DECOR_CHARM, {"o": "outline", "R": "charm_red", "Y": "gold"}),
    "decor_charm_sky": (DECOR_CHARM, {"o": "outline", "R": "charm_sky", "Y": "gold"}),
    "decor_trophy": ([                           # 트로피 (6 x 7)
        "oooooo",
        "oYyYYo",
        ".oYYo.",
        "..oo..",
        ".oooo.",
        ".oWWo.",
        ".oooo.",
    ], {"o": "outline", "Y": "gold", "y": "trophy_light", "W": "wood"}),
    "decor_dumbbell": ([                         # 덤벨 (9 x 4)
        ".oo...oo.",
        "oGGoooGGo",
        "oGGoooGGo",
        ".oo...oo.",
    ], {"o": "outline", "G": "dumbbell"}),
    "decor_kettlebell": ([                       # 케틀벨 (5 x 5, Lv5)
        ".ooo.",
        "o...o",
        "ooooo",
        "oKKKo",
        ".ooo.",
    ], {"o": "outline", "K": "kettle"}),
    "decor_pot": ([                              # 화분 (6 x 4)
        "oooooo",
        "oRRRRo",
        ".oRRo.",
        ".oooo.",
    ], {"o": "outline", "R": "pot"}),
    "decor_sprout": ([                           # 새싹 (Lv1)
        ".o..o.",
        "oPooPo",
        "..oo..",
    ], {"o": "outline", "P": "plant"}),
    "decor_leaves": ([                           # 큰 잎 (Lv3)
        "oo..oo",
        "oPooPo",
        "oPPPPo",
        ".oPPo.",
    ], {"o": "outline", "P": "plant"}),
    "decor_bloom": ([".oo.", "oAAo", ".oo."], {"o": "outline", "A": "bloom"}),  # 꽃 (Lv5)
    "decor_mat": ([                              # 요가 매트 (14 x 3, 바닥에 깔림)
        "oooooooooooooo",
        "oMmMmMmMmMmMmo",
        "oooooooooooooo",
    ], {"o": "outline", "M": "mat", "m": "mat_light"}),
    "decor_mat_roll": ([".oo.", "oNNo", "oNNo", ".oo."],   # 말아 둔 매트 (Lv3)
                       {"o": "outline", "N": "mat_roll"}),
    "decor_water": ([".o.", "oBo", "oBo", "ooo"],          # 물병 (Lv5)
                    {"o": "outline", "B": "water"}),
})
# 장식이 있는 업그레이드 id (시설 3종 제외, 패널 순서)
DECOR_IDS = [UPGRADE_MENU, UPGRADE_BED, UPGRADE_BOOK, UPGRADE_TIME, UPGRADE_HEALTH_CARE,
             UPGRADE_CHARM, UPGRADE_SCHOLARSHIP, UPGRADE_HEALTH_MAX, UPGRADE_MENTAL_MAX,
             UPGRADE_SELF_CARE]
# 업그레이드 id -> 장식 조각 목록 [(이 레벨 이상이면 보임, 스프라이트 이름, 열 차이, 행 차이)].
# 열·행 차이는 장식 자리(DECOR_SLOTS)의 왼쪽 위 칸에서 잰다. 목록 순서대로 그린다.
# 레벨이 오를수록 조각이 늘어난다: 대개 Lv1 기본, Lv3·Lv5에 하나씩 더(책장 책·부적은 레벨마다 하나)
DECOR_PIECES = {
    UPGRADE_MENU: [(1, "decor_lunchbox", 0, 4), (3, "decor_lunchbox2", 0, 0),
                   (5, "decor_riceball", 9, 4)],                         # 14 x 9칸
    UPGRADE_BED: [(1, "decor_cushion_sky", 0, 6), (3, "decor_cushion_pink", 0, 3),
                  (5, "decor_cushion_yellow", 0, 0)],                    # 7 x 10칸
    UPGRADE_BOOK: [(1, "decor_shelf", 0, 0), (1, "decor_book_pink", 2, 2),
                   (2, "decor_book_mint", 4, 2), (3, "decor_book_sky", 6, 2),
                   (4, "decor_book_yellow", 8, 2), (5, "decor_book_apricot", 10, 2)],  # 14 x 9칸
    UPGRADE_TIME: [(1, "decor_clock", 0, 2), (3, "decor_pendulum", 2, 11),
                   (5, "decor_clock_bells", 0, 0)],                      # 7 x 15칸
    UPGRADE_HEALTH_CARE: [(1, "decor_vitamin_orange", 0, 0), (3, "decor_vitamin_green", 3, 0),
                          (5, "decor_vitamin_pink", 6, 0)],              # 10 x 6칸
    UPGRADE_CHARM: [(1, "decor_charm_rack", 0, 0), (1, "decor_charm_red", 1, 3),
                    (2, "decor_charm_sky", 4, 3), (3, "decor_charm_red", 7, 3)],  # 11 x 10칸
    UPGRADE_SCHOLARSHIP: [(1, "decor_trophy", 0, 0)],                    # 6 x 7칸
    UPGRADE_HEALTH_MAX: [(1, "decor_dumbbell", 0, 4), (3, "decor_dumbbell", 0, 0),
                         (5, "decor_kettlebell", 10, 3)],                # 15 x 8칸
    UPGRADE_MENTAL_MAX: [(1, "decor_pot", 0, 9), (1, "decor_sprout", 0, 6),
                         (3, "decor_leaves", 0, 3), (5, "decor_bloom", 1, 0)],  # 6 x 13칸
    UPGRADE_SELF_CARE: [(1, "decor_mat", 0, 4), (3, "decor_mat_roll", 1, 0),
                        (5, "decor_water", 10, 0)],                      # 14 x 7칸
}
# 장식 자리: 장소 -> {업그레이드 id: (왼쪽 열, 위 행)} (무대 안쪽 칸 좌표, 가로 124 x 세로 84칸).
# (2026-11-24 배치 재설계) 장소마다 따로, 뜻이 맞는 것끼리 모은다(소풍·간식·독서·운동·무대 옆).
# 지키는 것: 바깥은 땅(행 45) 위, 제자(4학년 + 외형 + 점프 열 34~95 행 11~71)·행동 소품(열 86~109 행 62~74)·
# 벤치·졸업식 의자·가로등·시설 건물·알림/팝업 자리와 겹치지 않고,
# 꽃·덤불·나무·풍선, 1학년 흙길, 졸업식 무대와도 겹치지 않으며, 장식끼리는 1칸 이상 띄운다.
DECOR_SLOTS = {
    PLACE_LAWN: {   # 1학년 잔디: 왼쪽 벤치 = 소풍, 오른쪽 벤치 = 쉼·운동
        UPGRADE_MENTAL_MAX: (18, 45),    # 왼쪽 벤치 옆 화분
        UPGRADE_MENU: (1, 58),    # 벤치 아래 소풍 도시락
        UPGRADE_HEALTH_CARE: (24, 68),    # 도시락 옆 비타민
        UPGRADE_BED: (109, 57),    # 오른쪽 벤치 아래 쉬는 쿠션
        UPGRADE_SELF_CARE: (110, 68),    # 그 옆 운동 매트
        UPGRADE_HEALTH_MAX: (108, 76),    # 매트 아래 덤벨
        UPGRADE_BOOK: (44, 75),    # 제자 앞 책장
        UPGRADE_SCHOLARSHIP: (60, 76),    # 책장 옆 트로피
        UPGRADE_TIME: (96, 45),    # 카페 앞에 선 시계
        UPGRADE_CHARM: (70, 74),    # 트로피 옆 부적 걸이
    },
    PLACE_LECTURE: {   # 2학년 강의동: 왼쪽 건물 앞 = 시계·책장, 카페 앞 = 간식
        UPGRADE_TIME: (2, 45),    # 왼쪽 건물 앞 시계
        UPGRADE_MENTAL_MAX: (22, 46),    # 덤불 옆 화분
        UPGRADE_CHARM: (10, 46),    # 시계 옆 부적 걸이
        UPGRADE_BOOK: (16, 60),    # 건물 앞 책장
        UPGRADE_SCHOLARSHIP: (2, 62),    # 책장 옆 트로피
        UPGRADE_MENU: (100, 46),    # 카페 앞 도시락
        UPGRADE_BED: (115, 46),    # 카페 앞 쿠션
        UPGRADE_HEALTH_CARE: (112, 58),    # 쿠션 아래 비타민
        UPGRADE_SELF_CARE: (40, 76),    # 제자 앞 운동 매트
        UPGRADE_HEALTH_MAX: (58, 75),    # 매트 옆 덤벨
    },
    PLACE_LIBRARY: {   # 3학년 도서관 앞: 가로등 아래 = 독서 자리, 카페 앞 = 간식
        UPGRADE_BOOK: (6, 53),    # 가로등 아래 책장(독서 자리)
        UPGRADE_BED: (0, 63),    # 책장 옆 쿠션
        UPGRADE_MENTAL_MAX: (24, 54),    # 책장 옆 화분
        UPGRADE_SCHOLARSHIP: (12, 72),    # 쿠션 아래 트로피
        UPGRADE_TIME: (112, 45),    # 헬스장 앞 시계
        UPGRADE_CHARM: (112, 62),    # 시계 아래 부적 걸이
        UPGRADE_MENU: (97, 46),    # 카페 앞 도시락
        UPGRADE_HEALTH_CARE: (110, 77),    # 오른쪽 아래 비타민
        UPGRADE_SELF_CARE: (40, 76),    # 제자 앞 운동 매트
        UPGRADE_HEALTH_MAX: (58, 75),    # 매트 옆 덤벨
    },
    PLACE_CEREMONY: {   # 4학년 졸업식장: 무대 옆 = 트로피·시계, 왼쪽 = 손님 자리
        UPGRADE_SCHOLARSHIP: (98, 46),    # 무대 오른쪽 트로피
        UPGRADE_MENTAL_MAX: (114, 46),    # 무대 옆 화분
        UPGRADE_TIME: (106, 45),    # 무대 옆 시계
        UPGRADE_CHARM: (112, 62),    # 시계 아래 부적 걸이
        UPGRADE_BED: (1, 46),    # 왼쪽 손님 쿠션
        UPGRADE_HEALTH_CARE: (10, 45),    # 쿠션 옆 비타민
        UPGRADE_BOOK: (20, 52),    # 의자 위쪽 책장
        UPGRADE_MENU: (34, 72),    # 의자 줄 옆 도시락
        UPGRADE_SELF_CARE: (49, 76),    # 제자 앞 운동 매트
        UPGRADE_HEALTH_MAX: (68, 75),    # 매트 옆 덤벨
    },
    PLACE_LAB: {   # 대학원 연구실: 벽 = 시계·트로피, 바닥 = 나머지
        UPGRADE_TIME: (97, 42),    # 벽시계
        UPGRADE_SCHOLARSHIP: (105, 55),    # 벽 앞 트로피
        UPGRADE_CHARM: (23, 64),    # 큰 책장 옆 부적 걸이
        UPGRADE_BOOK: (44, 72),    # 바닥 책장
        UPGRADE_SELF_CARE: (29, 77),    # 바닥 매트
        UPGRADE_HEALTH_MAX: (59, 75),    # 매트 옆 덤벨
        UPGRADE_MENU: (75, 75),    # 바닥 도시락
        UPGRADE_HEALTH_CARE: (2, 77),    # 왼쪽 아래 비타민
        UPGRADE_BED: (110, 70),    # 화분 옆 쿠션
        UPGRADE_MENTAL_MAX: (118, 66),    # 화분 옆 작은 화분
    },
}
