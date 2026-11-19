import unittest

import ghosts
from game import GameState
from levels import Direction, parse_level

# Bir döngü: Pacman (1, 1), hayaletler (3, 4) ve (3, 5) (satır sırasıyla okunur).
LOOP = """
#######
#P....#
#.###.#
#...GG#
#######
"""


def loop_state(policy=None):
    return GameState(parse_level("loop", LOOP), ghost_policy=policy)


class ChaseTests(unittest.TestCase):
    def test_moves_along_shortest_path(self):
        state = loop_state()
        ghost = state.ghosts[1]                   # (3, 5): yukarı da sola da 5 adım
        self.assertEqual(ghosts.chase(state, ghost), Direction.UP)
        state.pacman = (3, 1)                     # sol alt: sol yol daha kısa
        self.assertEqual(ghosts.chase(state, ghost), Direction.LEFT)

    def test_does_not_reverse(self):
        state = loop_state()
        ghost = state.ghosts[0]
        ghost.position, ghost.direction = (2, 5), Direction.DOWN
        state.pacman = (1, 4)                     # en kısa yol geri (yukarı) ama yasak
        self.assertEqual(ghosts.chase(state, ghost), Direction.DOWN)

    def test_reverses_in_dead_end(self):
        text = """
#######
#P...G#
#####G#
#######
"""
        state = GameState(parse_level("dead", text))
        ghost = state.ghosts[1]                   # (2, 5): yalnızca yukarı açık
        ghost.direction = Direction.DOWN
        self.assertEqual(ghosts.chase(state, ghost), Direction.UP)

    def test_chaser_catches_still_pacman(self):
        state = loop_state(policy=ghosts.chase)
        for _ in range(10):
            if state.is_over:
                break
            state.step()                          # Pacman yerinde durur
        self.assertTrue(state.is_over)


if __name__ == "__main__":
    unittest.main()
