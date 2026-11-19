import tkinter as tk
import unittest

from game import GameState
from levels import Direction, parse_level
from views import BoardView, positions

LANE = """
#########
#P...  G#
#      G#
#########
"""


class SlideTests(unittest.TestCase):
    """Gerçek bir Tk tuvaliyle; ekran yoksa atlanır."""

    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk açılamadı: {exc}")
        self.canvas = tk.Canvas(self.root, width=450, height=200)
        self.canvas.pack()
        self.root.update()
        self.board = BoardView(self.canvas)
        self.state = GameState(parse_level("lane", LANE))

    def tearDown(self):
        self.root.destroy()

    def pacman_center(self):
        arc = next(item for item in self.canvas.find_withtag("dynamic") if self.canvas.type(item) == "arc")
        x0, y0, x1, y1 = self.canvas.coords(arc)
        return (x0 + x1) / 2, (y0 + y1) / 2

    def test_pacman_slides_between_squares(self):
        self.board.show(self.state)
        start = self.pacman_center()
        before = positions(self.state)
        self.state.step(Direction.RIGHT)
        self.board.show(self.state, 1, previous=before)
        self.assertAlmostEqual(self.pacman_center()[0], start[0])         # ilerleme 0: eski karede
        self.board.animate(0.5)
        self.assertAlmostEqual(self.pacman_center()[0], start[0] + self.board.cell / 2)
        self.board.finish_motion()
        self.assertAlmostEqual(self.pacman_center()[0], start[0] + self.board.cell)

    def test_pellet_disappears_when_pacman_reaches_it(self):
        self.board.show(self.state)
        before = positions(self.state)
        self.state.step(Direction.RIGHT)                                  # (1, 2)'deki yemek yendi
        self.board.show(self.state, 1, previous=before)
        self.assertIn((1, 2), self.board._pellet_items)                   # Pacman henüz varmadı
        self.board.animate(0.6)
        self.assertNotIn((1, 2), self.board._pellet_items)

    def test_teleport_is_not_slid(self):
        self.board.show(self.state)
        ghost = self.state.ghosts[0]
        before = positions(self.state)
        before[1][0] = (1, 2)                                             # komşu olmayan eski konum
        self.board.show(self.state, 1, previous=before)
        self.board.animate(0.5)
        self.assertEqual(self.board._slide((1, 2), ghost.position), self.board._center(ghost.position))


if __name__ == "__main__":
    unittest.main()
