"""제자 키우기의 모든 수치 상수를 모아 둔 파일.

다른 파일에서는 숫자를 직접 쓰지 않고 여기 있는 상수를 가져다 쓴다.
값은 docs/기획서.md 와 jeja-spec 기준표를 따른다.
도트 스프라이트(문자열 격자)와 색 팔레트 같은 그림 데이터도 여기에 둔다.
"""

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
SECONDS_PER_GRADE = 60                      # 학년당 시간(초)
MAX_GRADE = 4                               # 마지막 학년
TOTAL_SECONDS = SECONDS_PER_GRADE * MAX_GRADE  # 전체 시간 240초
EXAM_SECONDS = 15                           # 각 학년 마지막 15초가 시험 기간
FIRST_GRADE = 1                             # 처음 학년
ZERO_TIME = 0.0                             # 시간 값의 시작값·하한(초): 타이머 초기값, 쿨타임 하한

# ---------------------------------------------------------------
# 4. 게이지
# ---------------------------------------------------------------
GAUGE_MIN = 0               # 체력·멘탈·지식의 최솟값
GAUGE_MAX = 100             # 체력·멘탈의 최댓값 (지식은 상한 없음)

HEALTH_START = 80           # 체력 시작값
MENTAL_START = 80           # 멘탈 시작값
KNOWLEDGE_START = 0         # 지식 시작값

HEALTH_DECAY_PER_SEC = 1        # 체력 자연 감소(1초마다)
MENTAL_DECAY_PER_SEC = 1        # 멘탈 자연 감소(1초마다)
MENTAL_DECAY_PER_SEC_EXAM = 2   # 시험 기간 멘탈 자연 감소(1초마다)
DECAY_INTERVAL = 1.0            # 자연 감소가 일어나는 간격(초)
TIME_EPSILON = 1e-9             # 소수 덧셈 오차 허용치 (0.1을 10번 더하면 0.9999999…가 되는 문제 방지)

LOW_GAUGE_LIMIT = 30        # 이 값 미만이면 막대가 빨간색, 체력은 다크서클

# ---------------------------------------------------------------
# 5. 행동 증감량과 쿨타임
# ---------------------------------------------------------------
FEED_HEALTH = 20            # 학식 먹이기: 체력 +20

REST_MENTAL = 20            # 쉬게 하기: 멘탈 +20
REST_KNOWLEDGE = -2         # 쉬게 하기: 지식 -2

STUDY_HEALTH = -5           # 공부시키기: 체력 -5
STUDY_MENTAL = -8           # 공부시키기: 멘탈 -8
STUDY_KNOWLEDGE = 10        # 공부시키기: 지식 +10
STUDY_KNOWLEDGE_EXAM = 20   # 시험 기간 공부시키기: 지식 +20

ACTION_COOLDOWN = 1.0       # 행동 후 쿨타임(초), 세 행동이 함께 쓴다

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
TOP_GRADUATE_KNOWLEDGE = 700    # 지식 700 이상: 수석 졸업 (랜덤 이벤트 반영, 기획서 2절)
NORMAL_GRADUATE_KNOWLEDGE = 450  # 지식 450 이상 699 이하: 무사 졸업, 미만: 아슬아슬 졸업

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


def get_base_dir():
    """record.json을 저장할 폴더를 돌려준다.

    PyInstaller로 만든 exe로 실행 중이면(sys.frozen) exe 파일이 있는 폴더,
    파이썬으로 실행 중이면 이 파일(config.py, main.py와 같은 폴더)이 있는 폴더다.
    --onefile exe는 임시 폴더에 풀려서 돌아가므로 __file__ 기준으로 저장하면 기록이 사라진다.
    """
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

# 버튼: 평소 하늘색, 밝은색(마우스 올림용), 쿨타임 회색
COLOR_BUTTON = (130, 188, 238)          # 평소 버튼 몸통
COLOR_BUTTON_LIGHT = (196, 226, 252)    # 버튼 위 하이라이트 줄
COLOR_BUTTON_DARK = (92, 146, 206)      # 버튼 아래 그림자 줄
COLOR_BUTTON_BRIGHT = (200, 234, 255)   # 밝은 버튼 몸통 (마우스를 올렸을 때 쓸 색, 평소색과 한눈에 구분)
COLOR_BUTTON_TEXT = COLOR_OUTLINE       # 버튼 글자 색
COLOR_GRAY = (184, 182, 194)            # 쿨타임 중 버튼 몸통
COLOR_GRAY_LIGHT = (214, 212, 222)
COLOR_GRAY_DARK = (148, 146, 162)
COLOR_BUTTON_TEXT_COOL = (78, 74, 104)  # 쿨타임 중 버튼 글자 색 (회색 몸통 위에서도 읽히게 진하게)

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

# 상단 정보바: 왼쪽 "N학년", 가운데 "남은 시간 N초", 오른쪽 "지식 N" (Game이 그린다)
INFO_BOX_X = 12             # 정보바 상자 왼쪽 x
INFO_BOX_Y = 8              # 정보바 상자 위쪽 y
INFO_BOX_WIDTH = SCREEN_WIDTH - INFO_BOX_X * 2  # 정보바 상자 가로 길이(좌우 여백 같게)
INFO_BOX_HEIGHT = 44        # 정보바 상자 세로 길이
INFO_BAR_HEIGHT = INFO_BOX_Y + INFO_BOX_HEIGHT + PIXEL_SIZE  # 정보바 구역 전체 높이(그림자 포함, 56)
INFO_TEXT_CENTER_Y = INFO_BOX_Y + INFO_BOX_HEIGHT // 2  # 정보바 글자의 세로 가운데
INFO_TIME_X = SCREEN_WIDTH // 2  # "남은 시간" 글자의 가운데 x (화면 가운데)
INFO_BAR_MARGIN = 32        # 정보바 글자와 창 가장자리 사이 여백
GRADE_TEXT = "{}학년"            # 학년 글자 틀
TIME_LEFT_TEXT = "남은 시간 {}초"  # 현재 학년 남은 시간 글자 틀
KNOWLEDGE_TEXT = "{} {}"         # 지식 글자 틀: "지식 120"

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
MENTAL_LABEL_Y = 320        # 멘탈 아이콘·라벨 줄의 위쪽 y
MENTAL_BAR_Y = 352          # 멘탈 막대 위쪽 y
GAUGE_LABEL_GAP = 8         # 아이콘과 라벨 글자 사이 간격

HEALTH_LABEL = "체력"
MENTAL_LABEL = "멘탈"
KNOWLEDGE_LABEL = "지식"

# ---------------------------------------------------------------
# 13. 행동 버튼 (화면 아래쪽에 가로로 3개)
# ---------------------------------------------------------------
# 행동 이름 (Game.do_action 에 넘기는 값)
ACTION_FEED = "feed"        # 학식 먹이기
ACTION_REST = "rest"        # 쉬게 하기
ACTION_STUDY = "study"      # 공부시키기

# 버튼 글자 (jeja-spec 3절, 기획서 화면 예시)
FEED_BUTTON_TEXT = "학식 먹이기 [1]"
REST_BUTTON_TEXT = "쉬게 하기 [2]"
STUDY_BUTTON_TEXT = "공부시키기 [3]"

BUTTON_COUNT = 3            # 행동 버튼 개수
BUTTON_WIDTH = 232          # 버튼 하나의 가로 길이
BUTTON_HEIGHT = 52          # 버튼 하나의 세로 길이 (아래 남색 받침 1칸은 별도)
BUTTON_GAP = 24             # 버튼 사이 간격
BUTTON_Y = 476              # 버튼 위쪽 y
# 버튼 3개를 가운데 정렬했을 때 첫 버튼의 왼쪽 x: (800 - (232*3 + 24*2)) / 2 = 28
BUTTON_START_X = (SCREEN_WIDTH - (BUTTON_WIDTH * BUTTON_COUNT
                                  + BUTTON_GAP * (BUTTON_COUNT - 1))) // 2

# 버튼 아래 쿨타임 안내 문구
COOLDOWN_HINT_TEXT = "누른 뒤 1초 동안 회색 (쿨타임)"
COOLDOWN_HINT_Y = 546       # 안내 문구 위쪽 y
COOLDOWN_HINT_X = SCREEN_WIDTH // 2  # 안내 문구 가운데 x (화면 가운데)

# ---------------------------------------------------------------
# 14. 시험 기간 배너 (상단 정보바 바로 아래, 패널 위)
# ---------------------------------------------------------------
EXAM_BANNER_TEXT = "시험 기간! 공부 효과 2배, 멘탈 감소 2배"
EXAM_BANNER_X = 12          # 배너 왼쪽 x
EXAM_BANNER_Y = 64          # 배너 위쪽 y (정보바 구역 56 아래)
EXAM_BANNER_WIDTH = SCREEN_WIDTH - EXAM_BANNER_X * 2  # 배너 가로 길이(좌우 여백 같게)
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
RESTART_HINT_TEXT = "R을 눌러 다시 하기"
RESTART_HINT_Y = 428        # 다시 하기 안내 가운데 y

# 휴학 엔딩 비구름 위치·크기
CLOUD_PIXEL = 5             # 비구름 도트 1칸 크기 -> 125 x 100 픽셀
CLOUD_TOP_Y = 200           # 비구름 위쪽 y -> 아래 끝 300 (누적 지식 배지 위)

# 학사모 (졸업 엔딩일 때만): CAP_SPRITE를 칸 크기 CAP_PIXEL로 찍는다 (196 x 100 픽셀)
CAP_PIXEL = PIXEL_SIZE      # 학사모 도트 1칸 크기(4)
CAP_TOP_Y = 196             # 학사모 위쪽 y -> 아래 끝 296 (누적 지식 배지 위)

# ---------------------------------------------------------------
# 16. 상호작용 효과 E1~E6 (jeja-spec 13절). 보기만 바꾸고 게임 결과에는 영향이 없다
# ---------------------------------------------------------------
FULL_RATIO = 1.0            # 진행률·비율의 끝값(100%). 진행률 p 의 나머지 = FULL_RATIO - p
NO_CHANGE = 0               # 게이지 변화량이 0 (늘지도 줄지도 않음)
BLINK_SHOW = 0              # 깜빡임 차례 번호 % 2 가 이 값이면 "보임"
BLINK_HIDE = 1              # 깜빡임 차례 번호 % 2 가 이 값이면 "숨김"

# E1 버튼 호버·눌림·쿨타임 진행 막대
BUTTON_PRESS_OFFSET = 4     # 행동이 실행되면 버튼이 내려가는 거리(픽셀) = 받침 1칸
BUTTON_PRESS_TIME = 0.12    # 버튼이 눌린 채로 있는 시간(초)
COOLDOWN_BAR_HEIGHT = PIXEL_SIZE * 2   # 쿨타임 진행 막대 세로 길이(도트 2칸, 버튼 안쪽 맨 아래)
COLOR_COOLDOWN_TRACK = COLOR_GRAY_DARK  # 진행 막대의 아직 안 찬 부분
COLOR_COOLDOWN_FILL = COLOR_BUTTON      # 진행 막대의 찬 부분 (다시 쓸 수 있게 되는 하늘색)

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
POPUP_OUTLINE_OFFSETS = [(1, 0), (0, 1), (1, 1)]  # 남색 그림자 글자를 찍을 위치(오른쪽·아래 1픽셀)
COLOR_POPUP_UP = COLOR_GREEN        # 늘어난 값 글자 색
COLOR_POPUP_DOWN = COLOR_RED        # 줄어든 값 글자 색

# E4 게이지 부드러운 변화
GAUGE_ANIM_TIME = 0.25      # 행동으로 바뀐 막대 길이가 새 값을 따라가는 시간(초)
GAUGE_HEALTH = "health"     # Student 의 체력 속성 이름 (표시값 사전의 키)
GAUGE_MENTAL = "mental"     # Student 의 멘탈 속성 이름
GAUGE_KNOWLEDGE = "knowledge"  # Student 의 지식 속성 이름
GAUGE_NAMES = [GAUGE_HEALTH, GAUGE_MENTAL]   # 막대가 있어서 부드럽게 움직이는 게이지
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
# 17. 랜덤 이벤트와 성장 (기획서 9절, jeja-spec 14절)
# ---------------------------------------------------------------
# 발생 규칙 수치
EVENT_CHANCE = 0.25                 # 행동이 실제로 실행된 직후 이벤트가 뜰 확률
EVENT_GUARANTEE_INTERVAL = 11.25    # 최소 보장 구간 길이(초): 학년 안 0~45초를 4구간으로 나눈다
EVENT_MIN_PER_GRADE = 4             # 학년당 최소 보장 이벤트 수 (보장 구간 개수)
EVENT_MAX_PER_GRADE = 5             # 학년당 최대 이벤트 수
EVENT_CHOICE_RATIO = 0.5            # 선택지형 후보가 있을 때 선택지형을 고를 확률
EVENT_NOTICE_TIME = 2.0             # 자동형 알림 배너가 보이는 시간(초)
# 최소 간격: 확률로 뜨는 이벤트는 직전 이벤트(같은 판, 학년이 바뀌어도 이어서 셈) 이후
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
EVENT_COUNT_STEP = 1                # 이벤트가 한 번 나올 때 학년 이벤트 수가 늘어나는 양
EVENT_COUNT_START = 0               # 학년별 이벤트 수의 시작값 (새 판에서는 0번)

# 특성 (얻으면 그 판 끝까지 유지). 값은 화면 배지에 쓸 이름이다
TRAIT_FITNESS = "체력 단련"          # 학식 먹이기 체력 +20 -> +25
TRAIT_MUSIC = "음악 힐링"            # 쉬게 하기 멘탈 +20 -> +25
TRAIT_CAFFEINE = "카페인"            # 공부시키기 체력 -5 -> -3
TRAIT_LOVE = "연애 중"               # 쉬게 하기에 체력 +5가 함께 붙음

# 특성 보정을 받는 행동 효과 이름
BONUS_FEED_HEALTH = "feed_health"   # 학식 먹이기 체력
BONUS_REST_MENTAL = "rest_mental"   # 쉬게 하기 멘탈
BONUS_REST_HEALTH = "rest_health"   # 쉬게 하기 체력 (기본 0)
BONUS_STUDY_HEALTH = "study_health"  # 공부시키기 체력
REST_HEALTH = 0                     # 쉬게 하기의 기본 체력 변화 (특성 없으면 0)
TRAIT_BONUS_START = 0               # 특성 보정 합계의 시작값 (특성이 없으면 0)

# 특성 -> {보정 받는 효과: 기본 수치에 더하는 양}. 여러 특성이 있으면 각각 더한다
TRAIT_BONUSES = {
    TRAIT_FITNESS: {BONUS_FEED_HEALTH: 5},     # +20 -> +25
    TRAIT_MUSIC: {BONUS_REST_MENTAL: 5},       # +20 -> +25
    TRAIT_CAFFEINE: {BONUS_STUDY_HEALTH: 2},   # -5 -> -3
    TRAIT_LOVE: {BONUS_REST_HEALTH: 5},        # 0 -> +5
}

# 외형 5종 (얻으면 그 판 끝까지 제자에게 붙어 있다. 그리기는 D단위)
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

# 선택지형 이벤트 10개 (연계 3개 포함, 한 판에 한 번씩)
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
]
ALL_EVENTS = AUTO_EVENTS + CHOICE_EVENTS   # 이벤트 표 전체 (자동형 5 + 선택지형 10)

# ---------------------------------------------------------------
# 18. 랜덤 이벤트 화면 (D단위, jeja-spec 14절 "화면"). 보기만 바꾸며 게임 결과에는 영향이 없다
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
TRAIT_BADGE_Y = 392                 # 첫 줄 위쪽 y (멘탈 막대 테두리 아래 끝 380 + 여백)
TRAIT_BADGE_WIDTH = 112             # 배지 가로 길이 -> 2열: 24~136, 144~256 (패널 안쪽 16~264)
TRAIT_BADGE_HEIGHT = 24             # 배지 세로 길이 (+그림자 1칸)
TRAIT_BADGE_GAP = 8                 # 배지 사이 간격(가로·세로)
TRAIT_BADGE_COLUMNS = 2             # 한 줄에 놓는 배지 수
# 특성 -> (몸통, 위 하이라이트 줄)
TRAIT_COLORS = {
    TRAIT_FITNESS: (COLOR_APRICOT, COLOR_WHITE),
    TRAIT_MUSIC: (COLOR_SKY, COLOR_SKY_LIGHT),
    TRAIT_CAFFEINE: (COLOR_YELLOW, COLOR_YELLOW_LIGHT),
    TRAIT_LOVE: (COLOR_PINK, COLOR_PINK_LIGHT),
}

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
