import unittest

from game import GameState, Rules, Status
from levels import Direction, parse_level

# Pacman (1, 1)'de; sağında yemek koridoru, altında duvar.
CORRIDOR = """
#########
#P...o.G#
#.#####.#
#......G#
#########
"""


def new_state(text=CORRIDOR, **rules):
    return GameState(parse_level("test", text), Rules(**rules))


class MovementTests(unittest.TestCase):
    def test_move_changes_position(self):
        state = new_state()
        result = state.step(Direction.RIGHT)
        self.assertTrue(result.moved)
        self.assertEqual(state.pacman, (1, 2))
        self.assertEqual(state.steps, 1)
        self.assertEqual(state.direction, Direction.RIGHT)

    def test_wall_blocks_and_costs_nothing(self):
        state = new_state()
        result = state.step(Direction.UP)
        self.assertFalse(result.moved)
        self.assertEqual(state.pacman, (1, 1))
        self.assertEqual(state.score, 0)
        self.assertEqual(state.steps, 1)          # süre yine de işler

    def test_keeps_last_direction_when_request_blocked(self):
        state = new_state()
        state.step(Direction.RIGHT)
        state.step(Direction.UP)                  # yukarısı duvar: sağa devam
        self.assertEqual(state.pacman, (1, 3))
        self.assertEqual(state.direction, Direction.RIGHT)

    def test_continues_without_request(self):
        state = new_state()
        state.step(Direction.RIGHT)
        state.step()
        self.assertEqual(state.pacman, (1, 3))

    def test_legal_directions(self):
        state = new_state()
        self.assertEqual(set(state.legal_directions()), {Direction.RIGHT, Direction.DOWN})

    def test_elapsed_time_counts_steps(self):
        state = new_state(step_ms=100)
        for _ in range(5):
            state.step(Direction.UP)
        self.assertEqual(state.elapsed_ms, 500)


class CloneTests(unittest.TestCase):
    def test_clone_is_independent(self):
        state = new_state()
        copy = state.clone()
        copy.step(Direction.RIGHT)
        copy.ghosts[0].frightened = True
        copy.pellets.clear()
        self.assertEqual(state.pacman, (1, 1))
        self.assertFalse(state.ghosts[0].frightened)
        self.assertTrue(state.pellets)
        self.assertEqual(state.steps, 0)

    def test_clone_repeats_random_sequence(self):
        state = new_state()
        state.rng.random()
        copy = state.clone()
        self.assertEqual([state.rng.random() for _ in range(5)], [copy.rng.random() for _ in range(5)])


class StatusTests(unittest.TestCase):
    def test_new_game_is_playing(self):
        self.assertIs(new_state().status, Status.PLAYING)


if __name__ == "__main__":
    unittest.main()
