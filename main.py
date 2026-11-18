"""제자 키우기 실행 진입점. `py -3.12 main.py` 로 실행한다."""

from game import Game


def main():
    """Game을 만들고 실행한다."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
