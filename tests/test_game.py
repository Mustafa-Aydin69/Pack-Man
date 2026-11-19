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


class ScoringTests(unittest.TestCase):
    def test_move_onto_empty_square_costs_one(self):
        state = new_state()
        state.step(Direction.RIGHT)
        before = state.score
        state.step(Direction.LEFT)                # başlangıç karesinde yemek yok
        self.assertEqual(state.score - before, -1)

    def test_pellet_adds_points(self):
        state = new_state()
        result = state.step(Direction.RIGHT)
        self.assertTrue(result.ate_pellet)
        self.assertEqual(state.score, -1 + 10)
        self.assertNotIn((1, 2), state.pellets)

    def test_pellet_is_eaten_once(self):
        state = new_state()
        state.step(Direction.RIGHT)
        state.step(Direction.LEFT)
        result = state.step(Direction.RIGHT)
        self.assertFalse(result.ate_pellet)
        self.assertEqual(state.score, 9 - 1 - 1)

    def test_custom_rules_are_used(self):
        state = new_state(move_cost=-2, pellet=7)
        state.step(Direction.RIGHT)
        self.assertEqual(state.score, 5)

    def test_pellets_left(self):
        state = new_state()
        total = state.pellets_left
        state.step(Direction.RIGHT)
        self.assertEqual(state.pellets_left, total - 1)


class PowerTests(unittest.TestCase):
    def eat_power(self, **rules):
        state = new_state(**rules)
        for _ in range(3):
            state.step(Direction.RIGHT)
        result = state.step(Direction.RIGHT)     # (1, 5) enerji topu
        return state, result

    def test_power_adds_points_and_frightens(self):
        state, result = self.eat_power()
        self.assertTrue(result.ate_power)
        self.assertEqual(state.score, 3 * 9 - 1 + 50)
        self.assertTrue(state.powered)
        self.assertTrue(all(ghost.frightened for ghost in state.ghosts))

    def test_power_lasts_exactly_duration_steps(self):
        state, _ = self.eat_power(power_duration=5)
        # Yendiği adım 1. adımdı; 4 adım daha sürer, 5. adımın sonunda biter.
        self.assertEqual(state.power_left, 4)
        for _ in range(3):
            state.step(Direction.LEFT)
        self.assertTrue(state.powered)
        state.step(Direction.LEFT)
        self.assertFalse(state.powered)
        self.assertFalse(any(ghost.frightened for ghost in state.ghosts))


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
