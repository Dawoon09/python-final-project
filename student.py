"""제자(Student) 클래스가 들어 있는 파일."""

import pygame

import config


def clamp(value, low, high):
    """value를 low 이상 high 이하로 잘라서 돌려준다."""
    return max(low, min(value, high))


def judge_ending(knowledge):
    """240초를 버틴 제자의 누적 지식으로 졸업 엔딩 이름을 돌려준다.

    지식 500 이상 "수석 졸업", 300~499 "무사 졸업", 300 미만 "아슬아슬 졸업".
    (휴학은 체력·멘탈로 정하므로 여기서 다루지 않는다.)
    """
    if knowledge >= config.TOP_GRADUATE_KNOWLEDGE:
        return config.ENDING_TOP
    if knowledge >= config.NORMAL_GRADUATE_KNOWLEDGE:
        return config.ENDING_NORMAL
    return config.ENDING_BARELY


def draw_thick_arc(screen, color, rect, start, stop, thickness):
    """두께 thickness인 호를 그린다.

    pygame.draw.arc에 두께를 크게 주면 호 사이에 빈 점이 생겨서,
    두께 1짜리 호를 1픽셀씩 아래로 옮기며 thickness번 겹쳐 그린다.
    """
    for step in range(thickness):
        moved = rect.move(config.ARC_SHIFT_X, step * config.ARC_LINE_STEP)
        pygame.draw.arc(screen, color, moved, start, stop, config.ARC_LINE_STEP)


class Student:
    """교수가 돌보는 제자 한 명.

    체력·멘탈·지식 게이지와 지금까지 흐른 시간을 가지고 있다.
    로직은 화면 없이도 호출할 수 있도록 시간(dt)을 인자로 받는다.
    """

    def __init__(self):
        """게이지를 시작값으로 정하고 경과 시간을 0으로 둔다."""
        self.health = config.HEALTH_START
        self.mental = config.MENTAL_START
        self.knowledge = config.KNOWLEDGE_START
        self.elapsed = config.ZERO_TIME      # 게임 시작 후 흐른 시간(초)
        self.decay_timer = config.ZERO_TIME  # 다음 자연 감소까지 모아 둔 시간(초)

    # ------------------------------------------------------------
    # 게이지 값 바꾸기
    # ------------------------------------------------------------
    def change_health(self, amount):
        """체력을 amount만큼 바꾸고 0~100 안으로 맞춘다."""
        self.health = clamp(self.health + amount, config.GAUGE_MIN, config.GAUGE_MAX)

    def change_mental(self, amount):
        """멘탈을 amount만큼 바꾸고 0~100 안으로 맞춘다."""
        self.mental = clamp(self.mental + amount, config.GAUGE_MIN, config.GAUGE_MAX)

    def change_knowledge(self, amount):
        """지식을 amount만큼 바꾼다. 지식은 0 아래로 내려가지 않는다(상한 없음)."""
        self.knowledge = max(config.GAUGE_MIN, self.knowledge + amount)

    # ------------------------------------------------------------
    # 시간 흐름과 자연 감소
    # ------------------------------------------------------------
    def update(self, dt):
        """dt초만큼 시간을 흘려 게이지를 자연 감소시킨다.

        흐른 시간을 decay_timer에 모아 두었다가 1초가 찰 때마다 한 번씩 감소시킨다.
        그래서 프레임 속도와 상관없이 1초에 정확히 한 번 줄어들고,
        dt가 커서 여러 초가 한꺼번에 지나도 지난 초 수만큼 줄어든다.
        소수 덧셈 오차 때문에 1초를 놓치지 않도록 아주 작은 허용치(TIME_EPSILON)를 둔다.
        경과 시간은 전체 시간(240초)에서 멈춘다. dt가 커서 240초를 넘겨도
        240초까지만 흐르고, 그 뒤로는 자연 감소도 일어나지 않는다.
        감소가 일어날 때마다 경과 시간을 "그 감소가 일어난 시각"으로 맞춰 두어서,
        dt가 커도 감소마다 시험 기간인지(멘탈 -2) 정확히 판단한다.
        """
        time_left = max(config.ZERO_TIME, config.TOTAL_SECONDS - self.elapsed)
        dt = min(dt, time_left)
        end_time = self.elapsed + dt
        self.decay_timer += dt
        while self.decay_timer + config.TIME_EPSILON >= config.DECAY_INTERVAL:
            self.decay_timer -= config.DECAY_INTERVAL
            # 이번 1초 감소가 일어나는 시각 = 끝 시각 - 아직 남겨 둔 시간
            self.elapsed = end_time - self.decay_timer
            self.decay_once()
        self.elapsed = end_time
        if self.is_time_over():
            self.elapsed = config.TOTAL_SECONDS  # 소수 오차를 없애고 240에서 멈춘다

    def decay_once(self):
        """1초분 자연 감소를 한 번 적용한다: 체력 -1, 멘탈 -(멘탈 감소량)."""
        self.change_health(-config.HEALTH_DECAY_PER_SEC)
        self.change_mental(-self.get_mental_decay())

    def get_mental_decay(self):
        """1초마다 줄어드는 멘탈 양을 돌려준다: 평소 1, 시험 기간 2."""
        if self.is_exam_period():
            return config.MENTAL_DECAY_PER_SEC_EXAM
        return config.MENTAL_DECAY_PER_SEC

    def is_dropped_out(self):
        """체력이나 멘탈이 0이면 True(휴학 조건)를 돌려준다."""
        return self.health <= config.GAUGE_MIN or self.mental <= config.GAUGE_MIN

    # ------------------------------------------------------------
    # 시험 기간과 엔딩 (5일차)
    # ------------------------------------------------------------
    def is_time_over(self):
        """경과 시간이 전체 시간(240초)에 도달했으면 True(졸업 시점)를 돌려준다.

        1/60초를 14400번 더하면 239.9999…가 될 수 있어서 TIME_EPSILON 만큼 봐준다.
        """
        return self.elapsed + config.TIME_EPSILON >= config.TOTAL_SECONDS

    def is_exam_period(self):
        """지금이 시험 기간(각 학년 마지막 15초)이면 True를 돌려준다.

        학년 안에서 흐른 시간이 45초 이상이면 시험 기간이다(45~60초, 105~120초 …).
        60초가 되면 다음 학년이 시작되므로 시험 기간이 아니다.
        240초(졸업 시점)부터는 시험 기간이 아니다.
        get_grade와 똑같이 TIME_EPSILON 만큼 봐준다.
        """
        if self.is_time_over():
            return False
        grade_start = (self.get_grade() - config.FIRST_GRADE) * config.SECONDS_PER_GRADE
        time_in_grade = self.elapsed - grade_start
        exam_start = config.SECONDS_PER_GRADE - config.EXAM_SECONDS
        return time_in_grade + config.TIME_EPSILON >= exam_start

    def get_graduation_ending(self):
        """지금 지식으로 졸업 엔딩 이름을 돌려준다(judge_ending 사용)."""
        return judge_ending(self.knowledge)

    def get_ending(self):
        """지금 엔딩이 났는지 보고 엔딩 이름을 돌려준다. 아직 아니면 None.

        체력이나 멘탈이 0이면 휴학을 먼저 돌려준다(240초 시점과 겹쳐도 휴학 우선).
        그렇지 않고 240초가 되었으면 지식에 따른 졸업 엔딩을 돌려준다.
        """
        if self.is_dropped_out():
            return config.ENDING_LEAVE
        if self.is_time_over():
            return self.get_graduation_ending()
        return None

    # ------------------------------------------------------------
    # 행동 (3일차)
    # ------------------------------------------------------------
    def feed(self):
        """학식 먹이기: 체력 +20 (100을 넘지 않음)."""
        self.change_health(config.FEED_HEALTH)

    def rest(self):
        """쉬게 하기: 멘탈 +20 (100을 넘지 않음), 지식 -2 (0 아래로 내려가지 않음)."""
        self.change_mental(config.REST_MENTAL)
        self.change_knowledge(config.REST_KNOWLEDGE)

    def study(self):
        """공부시키기: 지식 +(공부 지식량), 체력 -5, 멘탈 -8 (0 아래로 내려가지 않음)."""
        self.change_knowledge(self.get_study_knowledge())
        self.change_health(config.STUDY_HEALTH)
        self.change_mental(config.STUDY_MENTAL)

    def get_study_knowledge(self):
        """공부시키기 한 번에 오르는 지식 양을 돌려준다: 평소 10, 시험 기간 20."""
        if self.is_exam_period():
            return config.STUDY_KNOWLEDGE_EXAM
        return config.STUDY_KNOWLEDGE

    # ------------------------------------------------------------
    # 학년과 성장 (4일차)
    # ------------------------------------------------------------
    def get_grade(self):
        """경과 시간으로 지금 학년(1~4)을 계산해 돌려준다.

        0~60초 미만 1학년, 60~120초 미만 2학년, 120~180초 미만 3학년, 180초부터 4학년.
        240초(졸업 시점)에도 4학년으로 둔다.
        1/60초를 3600번 더하면 59.9999…가 될 수 있어서 TIME_EPSILON 만큼 봐준다.
        """
        passed_grades = int((self.elapsed + config.TIME_EPSILON)
                            // config.SECONDS_PER_GRADE)
        return min(config.FIRST_GRADE + passed_grades, config.MAX_GRADE)

    def get_grade_time_left(self):
        """현재 학년의 남은 시간(정수 초, 60 -> 1)을 돌려준다.

        학년 안에서 흐른 시간의 정수 부분을 60에서 뺀다(= 남은 시간을 올림).
        그래서 학년이 막 시작하면 60, 59초가 지나 1초 미만이 남으면 1이 된다.
        4학년에서 240초가 지나면 0으로 둔다(음수가 되지 않음).
        """
        grade_start = (self.get_grade() - config.FIRST_GRADE) * config.SECONDS_PER_GRADE
        time_in_grade = self.elapsed - grade_start
        passed_seconds = int(time_in_grade + config.TIME_EPSILON)
        return max(config.GAUGE_MIN, config.SECONDS_PER_GRADE - passed_seconds)

    def get_radius(self):
        """캐릭터 반지름을 돌려준다: 40 + (학년-1) x 10 -> 40/50/60/70."""
        return (config.BASE_RADIUS
                + (self.get_grade() - config.FIRST_GRADE) * config.RADIUS_PER_GRADE)

    # ------------------------------------------------------------
    # 표정 (4일차)
    # ------------------------------------------------------------
    def get_mouth(self):
        """멘탈에 따른 입 모양 이름을 돌려준다.

        멘탈 60 이상 "smile"(웃는 입), 30~59 "flat"(일자 입), 30 미만 "cry"(우는 입).
        """
        if self.mental >= config.MENTAL_SMILE_MIN:
            return config.MOUTH_SMILE
        if self.mental >= config.MENTAL_FLAT_MIN:
            return config.MOUTH_FLAT
        return config.MOUTH_CRY

    def has_dark_circles(self):
        """체력이 30 미만이면 True(다크서클을 그린다)."""
        return self.health < config.LOW_GAUGE_LIMIT

    def has_glasses(self):
        """3학년부터 True(안경을 그린다)."""
        return self.get_grade() >= config.GLASSES_GRADE

    # ------------------------------------------------------------
    # 그리기
    # ------------------------------------------------------------
    def draw_gauges(self, screen, font):
        """왼쪽 게이지 구역에 체력·멘탈 막대를 그린다.

        지식 숫자는 4일차부터 상단 정보바에서 Game이 학년·남은 시간과 함께 그린다.
        """
        self.draw_bar(screen, font, config.HEALTH_LABEL, self.health,
                      config.HEALTH_LABEL_Y, config.HEALTH_BAR_Y)
        self.draw_bar(screen, font, config.MENTAL_LABEL, self.mental,
                      config.MENTAL_LABEL_Y, config.MENTAL_BAR_Y)

    def draw_bar(self, screen, font, label, value, label_y, bar_y):
        """라벨과 게이지 막대 하나를 그린다.

        배경(흰색)을 깔고 값 비율만큼 색을 채운 뒤 검은 테두리를 그린다.
        값이 30 미만이면 빨간색, 아니면 초록색으로 채운다.
        테두리는 막대 바깥쪽에 그려서 채움을 덮지 않는다.
        그래서 값이 1이어도 채움이 보이고, 채움 길이가 값에 정확히 비례한다.
        """
        label_text = font.render(label, True, config.COLOR_BLACK)
        screen.blit(label_text, (config.GAUGE_X, label_y))

        # 1) 막대 배경
        bar_rect = pygame.Rect(config.GAUGE_X, bar_y,
                               config.BAR_WIDTH, config.BAR_HEIGHT)
        # 테두리용 사각형: 막대보다 사방으로 테두리 두께만큼 크다
        border_rect = bar_rect.inflate(config.BAR_BORDER_GROW,
                                       config.BAR_BORDER_GROW)
        pygame.draw.rect(screen, config.COLOR_BAR_BG, bar_rect)

        # 2) 값 비율만큼 채우기
        if value < config.LOW_GAUGE_LIMIT:
            fill_color = config.COLOR_RED
        else:
            fill_color = config.COLOR_GREEN
        fill_width = int(config.BAR_WIDTH * value / config.GAUGE_MAX)
        fill_rect = pygame.Rect(config.GAUGE_X, bar_y,
                                fill_width, config.BAR_HEIGHT)
        pygame.draw.rect(screen, fill_color, fill_rect)

        # 3) 테두리 (막대 바깥쪽)
        pygame.draw.rect(screen, config.COLOR_BLACK, border_rect,
                         config.BAR_BORDER_WIDTH)

    def draw(self, screen):
        """오른쪽 제자 구역에 제자 얼굴을 그린다.

        얼굴(원 + 테두리), 눈 2개, 입을 그리고,
        체력 30 미만이면 다크서클, 3학년부터 안경을 더 그린다.
        모든 요소의 크기와 위치는 반지름에 비례하므로 학년이 오르면 함께 커진다.
        """
        radius = self.get_radius()
        cx = config.STUDENT_CENTER_X
        cy = config.STUDENT_CENTER_Y
        line = max(config.MIN_LINE_WIDTH, int(radius * config.FACE_BORDER_RATIO))

        # 1) 얼굴: 살구색 원 + 검은 테두리
        pygame.draw.circle(screen, config.COLOR_SKIN, (cx, cy), radius)
        pygame.draw.circle(screen, config.COLOR_FACE_LINE, (cx, cy), radius, line)

        # 2) 눈 2개 (왼쪽, 오른쪽)
        eye_dx = int(radius * config.EYE_OFFSET_X_RATIO)
        eye_y = cy - int(radius * config.EYE_OFFSET_Y_RATIO)
        eye_radius = max(config.MIN_LINE_WIDTH, int(radius * config.EYE_RADIUS_RATIO))
        eye_centers = [(cx - eye_dx, eye_y), (cx + eye_dx, eye_y)]
        for eye in eye_centers:
            pygame.draw.circle(screen, config.COLOR_FACE_LINE, eye, eye_radius)

        # 3) 다크서클 (체력 30 미만): 각 눈 아래 아래쪽 반원 호
        if self.has_dark_circles():
            self.draw_dark_circles(screen, radius, eye_centers, line)

        # 4) 안경 (3학년부터): 눈 둘레 원 2개 + 가운데 다리 + 양옆 다리
        if self.has_glasses():
            self.draw_glasses(screen, radius, eye_centers, line)

        # 5) 입
        self.draw_mouth(screen, radius, cx, cy, line)

    def draw_dark_circles(self, screen, radius, eye_centers, line):
        """각 눈 바로 아래에 다크서클(아래쪽 반원 호)을 그린다."""
        width = int(radius * config.DARK_CIRCLE_WIDTH_RATIO)
        height = int(radius * config.DARK_CIRCLE_HEIGHT_RATIO)
        offset_y = int(radius * config.DARK_CIRCLE_OFFSET_Y_RATIO)
        thickness = max(config.MIN_DARK_CIRCLE_LINE,
                        int(radius * config.DARK_CIRCLE_LINE_RATIO))
        for eye_x, eye_y in eye_centers:
            rect = pygame.Rect(config.ORIGIN, (width, height))
            rect.center = (eye_x, eye_y + offset_y)
            draw_thick_arc(screen, config.COLOR_DARK_CIRCLE, rect,
                           config.ARC_LOWER_START, config.ARC_LOWER_STOP, thickness)

    def draw_glasses(self, screen, radius, eye_centers, line):
        """눈 둘레에 안경알(원) 2개를 그리고, 안경알 사이와 양옆(얼굴 끝까지)에 다리 선을 그린다."""
        lens = int(radius * config.GLASSES_RADIUS_RATIO)
        (left_x, eye_y), (right_x, _) = eye_centers
        for eye in eye_centers:
            pygame.draw.circle(screen, config.COLOR_FACE_LINE, eye, lens, line)
        # 가운데 다리: 왼쪽 안경알 오른쪽 끝 -> 오른쪽 안경알 왼쪽 끝
        pygame.draw.line(screen, config.COLOR_FACE_LINE,
                         (left_x + lens, eye_y), (right_x - lens, eye_y), line)
        # 양옆 다리: 안경알 바깥쪽 끝 -> 얼굴 테두리 쪽
        cx = config.STUDENT_CENTER_X
        pygame.draw.line(screen, config.COLOR_FACE_LINE,
                         (left_x - lens, eye_y), (cx - radius, eye_y), line)
        pygame.draw.line(screen, config.COLOR_FACE_LINE,
                         (right_x + lens, eye_y), (cx + radius, eye_y), line)

    def draw_mouth(self, screen, radius, cx, cy, line):
        """멘탈에 따라 입을 그린다.

        웃는 입: 아래로 볼록한 호(타원의 아래쪽 반)
        일자 입: 가로 선
        우는 입: 위로 볼록한 호(타원의 위쪽 반)
        """
        width = int(radius * config.MOUTH_WIDTH_RATIO)
        height = int(radius * config.MOUTH_HEIGHT_RATIO)
        mouth_y = cy + int(radius * config.MOUTH_OFFSET_Y_RATIO)
        rect = pygame.Rect(config.ORIGIN, (width, height))
        rect.center = (cx, mouth_y)

        # 타원의 가운데 가로줄이 입 높이(mouth_y)다. 입꼬리 두 점이 이 줄 위에 있다.
        mouth = self.get_mouth()
        if mouth == config.MOUTH_SMILE:
            # 타원의 아래쪽 반만 그린다 -> 입꼬리에서 아래로 볼록
            draw_thick_arc(screen, config.COLOR_FACE_LINE, rect,
                           config.ARC_LOWER_START, config.ARC_LOWER_STOP, line)
        elif mouth == config.MOUTH_FLAT:
            pygame.draw.line(screen, config.COLOR_FACE_LINE,
                             (rect.left, mouth_y), (rect.right, mouth_y), line)
        else:
            # 타원의 위쪽 반만 그린다 -> 입꼬리에서 위로 볼록
            draw_thick_arc(screen, config.COLOR_FACE_LINE, rect,
                           config.ARC_UPPER_START, config.ARC_UPPER_STOP, line)
