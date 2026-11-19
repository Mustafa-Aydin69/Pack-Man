import unittest

from game import Rules, Status
from levels import Direction, parse_level
from match import HUMAN, Run

# İki küçük seviye: her birinde Pacman'in sağında tek yemek var.
FIRST = parse_level("A", """
#######
#P.  G#
#    G#
#######
""")
SECOND = parse_level("B", """
#######
#P..  #
#   GG#
#######
""")


def run(**rules):
    return Run(HUMAN, levels=(FIRST, SECOND), rules=Rules(**rules))


class RunTests(unittest.TestCase):
    def test_starts_on_first_level(self):
        r = run()
        self.assertEqual(r.level, FIRST)
        self.assertFalse(r.is_over)

    def test_level_win_moves_to_next_level(self):
        r = run()
        r.state.step(Direction.RIGHT)             # tek yemek: seviye biter
        self.assertTrue(r.level_won)
        self.assertTrue(r.has_next_level)
        self.assertFalse(r.is_over)
        r.next_level()
        self.assertEqual(r.level, SECOND)
        self.assertIs(r.state.status, Status.PLAYING)

    def test_score_and_time_accumulate(self):
        r = run(step_ms=100)
        r.state.step(Direction.RIGHT)             # +9, 1 adım
        r.next_level()
        r.state.step(Direction.RIGHT)             # +9, 1 adım
        self.assertEqual(r.score, 18)
        self.assertEqual(r.steps, 2)
        self.assertEqual(r.elapsed_ms, 200)

    def test_finishing_last_level_completes_run(self):
        r = run()
        r.state.step(Direction.RIGHT)
        r.next_level()
        r.state.step(Direction.RIGHT)
        r.state.step(Direction.RIGHT)
        self.assertTrue(r.is_over)
        self.assertTrue(r.completed)
        result = r.result()
        self.assertTrue(result.completed)
        self.assertEqual((result.levels_completed, result.level_count), (2, 2))
        self.assertEqual(result.pellets_eaten, 3)
        with self.assertRaises(RuntimeError):
            r.next_level()

    def test_caught_run_is_over_but_not_completed(self):
        r = run()
        r.state.status = Status.LOST
        self.assertTrue(r.is_over)
        self.assertFalse(r.completed)
        self.assertEqual(r.result().levels_completed, 0)

    def test_each_level_uses_same_seed(self):
        r = run()
        first_draw = r.state.rng.random()
        r.state.rng.random()
        r.state.step(Direction.RIGHT)
        r.next_level()
        self.assertEqual(r.state.rng.random(), first_draw)


if __name__ == "__main__":
    unittest.main()
