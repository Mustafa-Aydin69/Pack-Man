import unittest

import ghosts
from game import DEFAULT_SEED, GameState
from levels import LEVELS, Direction, parse_level

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


class FleeTests(unittest.TestCase):
    def test_turns_around_to_escape(self):
        state = loop_state()
        ghost = state.ghosts[1]
        ghost.position, ghost.direction = (2, 5), Direction.UP   # Pacman'e doğru gidiyordu
        state.pacman = (1, 4)
        self.assertEqual(ghosts.flee(state, ghost), Direction.DOWN)

    def test_prefers_not_to_reverse_on_tie(self):
        # Hayalet (1, 4) Pacman'in (3, 4) tam karşısında: sol da sağ da 7 adım uzaklaştırır.
        text = """
#########
#...G...#
#.#####.#
#...P..G#
#########
"""
        state = GameState(parse_level("tie", text))
        ghost = state.ghosts[0]                   # (1, 4)
        ghost.direction = Direction.LEFT
        self.assertEqual(ghosts.flee(state, ghost), Direction.LEFT)
        ghost.direction = Direction.RIGHT
        self.assertEqual(ghosts.flee(state, ghost), Direction.RIGHT)


class WanderTests(unittest.TestCase):
    def walk(self, seed, steps=40):
        state = GameState(parse_level("loop", LOOP), seed=seed, ghost_policy=ghosts.wander)
        state.pacman = (1, 3)                     # yakalanmasın diye hayaletlerden uzakta
        path = []
        for _ in range(steps):
            state.step()
            if state.is_over:
                break
            path.append(tuple(ghost.position for ghost in state.ghosts))
        return path

    def test_same_seed_same_path(self):
        self.assertEqual(self.walk(7), self.walk(7))

    def test_never_reverses_on_loop(self):
        # Döngüde çıkmaz yok; hayalet hiç geri dönmemeli.
        state = GameState(parse_level("loop", LOOP), seed=3)
        ghost = state.ghosts[1]
        previous = None
        for _ in range(30):
            direction = ghosts.wander(state, ghost)
            self.assertIsNot(direction, previous.opposite if previous else None)
            ghost.position, ghost.direction, previous = direction.apply(ghost.position), direction, direction

    def test_uses_game_rng(self):
        state = GameState(parse_level("loop", LOOP), seed=11)
        ghost = state.ghosts[0]
        copy = state.clone()
        self.assertEqual(ghosts.wander(state, ghost), ghosts.wander(copy, copy.ghosts[0]))


class PolicyTests(unittest.TestCase):
    def test_first_ghost_chases_others_wander(self):
        self.assertEqual(ghosts.strategy_name(0), "Takipçi")
        self.assertEqual(ghosts.strategy_name(1), "Gezgin")
        self.assertEqual(ghosts.strategy_name(2), "Gezgin")

    def test_first_ghost_follows_chase(self):
        state = loop_state(policy=ghosts.policy)
        for _ in range(5):
            expected = ghosts.chase(state, state.ghosts[0])
            self.assertEqual(ghosts.policy(state, state.ghosts[0]), expected)
            state.step()

    def test_frightened_ghost_moves_every_other_step(self):
        state = loop_state(policy=ghosts.policy)
        ghost = state.ghosts[1]
        ghost.frightened = True
        state.steps = 0
        self.assertIsNotNone(ghosts.policy(state, ghost))
        state.steps = 1
        self.assertIsNone(ghosts.policy(state, ghost))

    def test_new_game_wires_policy_and_seed(self):
        state = ghosts.new_game(LEVELS[0])
        self.assertIs(state.ghost_policy, ghosts.policy)
        self.assertEqual(state.rng.random(), GameState(LEVELS[0], seed=DEFAULT_SEED).rng.random())


class DeterminismTests(unittest.TestCase):
    """İki oyuncunun aynı koşullarda oynaması: aynı seed + aynı hamleler = aynı oyun."""

    MOVES = (Direction.LEFT, Direction.UP, Direction.RIGHT, Direction.DOWN)

    def play(self, level, seed, steps=400):
        state = ghosts.new_game(level, seed=seed)
        trace = []
        for i in range(steps):
            if state.is_over:
                break
            state.step(self.MOVES[i // 5 % 4])
            trace.append((state.pacman, state.score, tuple(g.position for g in state.ghosts)))
        return trace, state.status

    def test_same_seed_same_game_on_every_level(self):
        for level in LEVELS:
            self.assertEqual(self.play(level, 1), self.play(level, 1), level.name)

    def test_different_seeds_change_wanderers(self):
        traces = {tuple(self.play(LEVELS[1], seed, steps=30)[0]) for seed in range(5)}
        self.assertGreater(len(traces), 1)


if __name__ == "__main__":
    unittest.main()
