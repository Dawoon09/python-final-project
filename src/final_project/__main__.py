"""`python -m final_project` 로 실행되는 진입점."""

from final_project.core import greet


def main() -> None:
    name = input("이름을 입력하세요: ")
    try:
        print(greet(name))
    except ValueError as e:
        print(f"오류: {e}")


if __name__ == "__main__":
    main()
