import pytest

from final_project.core import greet


def test_greet():
    assert greet("철수") == "안녕하세요, 철수님!"


def test_greet_strips_whitespace():
    assert greet("  영희 ") == "안녕하세요, 영희님!"


def test_greet_empty_raises():
    with pytest.raises(ValueError):
        greet("   ")
