"""
main.py - run this file to play Simon's Sequence.

    python main.py              # 2D mode
    python main.py --opengl     # 3D OpenGL mode
"""
import argparse
from game import Game

if __name__ == "__main__":
    print("Thanks for playing Simon's Sequence!")
    print("If you enjoyed the game, please consider supporting the developer!")
    print("github check")
    parser = argparse.ArgumentParser(description="Simon's Sequence")
    parser.add_argument("--opengl", action="store_true", help="Run in OpenGL 3D mode")
    args = parser.parse_args()
    game = Game(use_opengl=args.opengl)
    game.run()