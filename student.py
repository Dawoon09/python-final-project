"""제자(Student) 클래스가 들어 있는 파일."""

import config


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
        self.elapsed = 0.0  # 게임 시작 후 흐른 시간(초)

    def update(self, dt):
        """dt초만큼 시간을 흘려 게이지를 자연 감소시킨다. (2일차에 구현)"""
        pass

    def feed(self):
        """학식 먹이기: 체력을 올린다. (3일차에 구현)"""
        pass

    def rest(self):
        """쉬게 하기: 멘탈을 올리고 지식을 조금 내린다. (3일차에 구현)"""
        pass

    def study(self):
        """공부시키기: 지식을 올리고 체력·멘탈을 내린다. (3일차에 구현)"""
        pass

    def draw(self, screen):
        """제자를 화면에 그린다. (4일차에 구현)"""
        pass
