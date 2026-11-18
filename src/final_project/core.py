"""핵심 로직을 작성하는 모듈.

예시 함수는 과제 주제에 맞게 바꾸거나 지우세요.
"""


def greet(name: str) -> str:
    """이름을 받아 인사말을 돌려줍니다."""
    name = name.strip()
    if not name:
        raise ValueError("이름이 비어 있습니다.")
    return f"안녕하세요, {name}님!"
