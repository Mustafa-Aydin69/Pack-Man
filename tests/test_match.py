import unittest

from game import Rules, Status
from levels import Direction, parse_level
from match import AI, HUMAN, Match, Run, RunResult, decide_winner

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


def result(player=HUMAN, completed=True, score=1000, elapsed_ms=60_000):
    return RunResult(player=player, completed=completed, score=score, elapsed_ms=elapsed_ms,
                     steps=elapsed_ms // 150, levels_completed=2 if completed else 1, level_count=2,
                     pellets_eaten=200, ghosts_eaten=1)


class DecideWinnerTests(unittest.TestCase):
    def test_completion_beats_higher_score(self):
        done = result(HUMAN, completed=True, score=100)
        caught = result(AI, completed=False, score=5000)
        verdict = decide_winner(done, caught)
        self.assertIs(verdict.winner, done)
        self.assertEqual(verdict.criterion, "Oyunu tamamladı")
        self.assertIs(decide_winner(caught, done).winner, done)   # sıra fark etmez

    def test_score_decides_when_completion_equal(self):
        low, high = result(HUMAN, score=900), result(AI, score=1100)
        verdict = decide_winner(low, high)
        self.assertIs(verdict.winner, high)
        self.assertIs(verdict.loser, low)
        self.assertEqual(verdict.criterion, "Daha yüksek puan")

    def test_score_decides_between_two_caught_players(self):
        a, b = result(HUMAN, completed=False, score=300), result(AI, completed=False, score=200)
        self.assertIs(decide_winner(a, b).winner, a)

    def test_shorter_time_breaks_score_tie(self):
        slow, fast = result(HUMAN, elapsed_ms=70_000), result(AI, elapsed_ms=65_000)
        verdict = decide_winner(slow, fast)
        self.assertIs(verdict.winner, fast)
        self.assertEqual(verdict.criterion, "Daha kısa süre")

    def test_draw_when_everything_equal(self):
        verdict = decide_winner(result(HUMAN), result(AI))
        self.assertTrue(verdict.is_draw)
        self.assertIsNone(verdict.winner)
        self.assertEqual(verdict.criterion, "Bütün ölçütler eşit")


class MatchTests(unittest.TestCase):
    def test_order_follows_choice(self):
        self.assertEqual(Match(AI).order, (AI, HUMAN))
        self.assertEqual(Match(HUMAN).order, (HUMAN, AI))
        with self.assertRaises(ValueError):
            Match("Biri")

    def test_turns_and_verdict(self):
        match = Match(AI)
        self.assertEqual((match.turn, match.current_player), (1, AI))
        with self.assertRaises(RuntimeError):
            match.verdict()
        with self.assertRaises(ValueError):
            match.record(result(HUMAN))                  # sıra yapay zekâda
        match.record(result(AI, score=10))
        self.assertEqual((match.turn, match.current_player), (2, HUMAN))
        match.record(result(HUMAN, score=20))
        self.assertTrue(match.is_over)
        self.assertIsNone(match.current_player)
        self.assertEqual(match.verdict().winner.player, HUMAN)
        with self.assertRaises(RuntimeError):
            match.record(result(AI))

    def test_each_turn_starts_from_identical_conditions(self):
        match = Match(HUMAN)
        first = match.new_run()
        first.state.step(first.state.legal_directions()[0])
        match.record(first.result())
        second = match.new_run()
        self.assertEqual(second.player, AI)
        self.assertEqual(second.level_index, 0)
        self.assertEqual(second.state.pellets, set(second.level.pellets))
        self.assertEqual(second.state.pacman, second.level.pacman_start)
        self.assertEqual(second.state.rng.getstate(), Run(HUMAN).state.rng.getstate())


if __name__ == "__main__":
    unittest.main()
