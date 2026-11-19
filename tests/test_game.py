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


def scripted(*moves_per_ghost):
    """Hayalet i, her adımda moves_per_ghost[i] listesinden sıradaki yönü seçer."""
    queues = [list(moves) for moves in moves_per_ghost]

    def policy(state, ghost):
        # dataclass eşitliği değere göredir; aynı karedeki iki hayalet karışmasın
        # diye kimlikle (is) aranır.
        index = next(i for i, other in enumerate(state.ghosts) if other is ghost)
        queue = queues[index] if index < len(queues) else []
        return queue.pop(0) if queue else None
    return policy


# Pacman (1, 1); hayaletler (1, 4) ve (1, 7). (1, 2) ve (1, 3)'te yemek var.
LANE = """
#########
#P..G..G#
#.......#
#########
"""


def lane_state(*moves, **rules):
    level = parse_level("lane", LANE)
    return GameState(level, Rules(**rules), ghost_policy=scripted(*moves))


class CollisionTests(unittest.TestCase):
    def test_walking_into_ghost_loses(self):
        state = lane_state()
        state.step(Direction.RIGHT)
        state.step(Direction.RIGHT)
        result = state.step(Direction.RIGHT)      # (1, 4): hayalet
        self.assertTrue(result.caught)
        self.assertIs(state.status, Status.LOST)

    def test_near_misses_do_not_lose(self):
        state = lane_state([Direction.LEFT, Direction.LEFT])
        state.step(Direction.RIGHT)               # Pacman (1, 2), hayalet (1, 3)
        result = state.step(Direction.DOWN)       # Pacman (2, 2), hayalet (1, 2)
        self.assertFalse(result.caught)
        state = lane_state([Direction.LEFT, Direction.LEFT])
        state.step(Direction.RIGHT)
        result = state.step(Direction.LEFT)       # Pacman (1, 1), hayalet (1, 2)
        self.assertFalse(result.caught)
        state = lane_state([Direction.LEFT, Direction.LEFT])
        state.step()                              # Pacman yerinde, hayalet (1, 3)
        state.step()                              # hayalet (1, 2)
        result = state.step()                     # politika boş: hayalet durur
        self.assertFalse(result.caught)

    def test_ghost_steps_onto_pacman(self):
        state = lane_state([Direction.LEFT, Direction.LEFT, Direction.LEFT])
        state.step()
        state.step()
        result = state.step()                     # hayalet (1, 1): Pacman'in karesi
        self.assertTrue(result.caught)
        self.assertIs(state.status, Status.LOST)

    def test_head_on_swap_is_caught(self):
        # Pacman (1, 2)'den sağa, hayalet (1, 3)'ten sola: birbirinin içinden geçemezler.
        state = lane_state([Direction.LEFT, Direction.LEFT])
        state.step(Direction.RIGHT)               # Pacman (1, 2), hayalet (1, 3)
        result = state.step(Direction.RIGHT)
        self.assertTrue(result.caught)

    def test_caught_pacman_does_not_eat(self):
        state = lane_state([Direction.LEFT])
        state.step()                              # hayalet (1, 3)'te, yemeğin üstünde
        state.step(Direction.RIGHT)               # Pacman (1, 2)
        before = state.score
        state.step(Direction.RIGHT)               # (1, 3): hayalete yürür
        self.assertIs(state.status, Status.LOST)
        self.assertIn((1, 3), state.pellets)
        self.assertEqual(state.score, before - 1)

    def test_game_over_freezes_state(self):
        state = lane_state()
        for _ in range(3):
            state.step(Direction.RIGHT)
        snapshot = (state.pacman, state.score, state.steps)
        state.step(Direction.DOWN)
        self.assertEqual((state.pacman, state.score, state.steps), snapshot)


class EatGhostTests(unittest.TestCase):
    def test_frightened_ghost_is_eaten_and_respawns(self):
        state = lane_state([Direction.LEFT])
        for ghost in state.ghosts:
            ghost.frightened = True
        state.power_left = 10
        state.step(Direction.RIGHT)               # Pacman (1, 2), hayalet (1, 3)
        result = state.step(Direction.RIGHT)      # hayaleti yer
        self.assertEqual(result.ghosts_eaten, 1)
        self.assertIs(state.status, Status.PLAYING)
        self.assertEqual(state.ghosts[0].position, (1, 4))
        self.assertFalse(state.ghosts[0].frightened)
        self.assertEqual(state.ghosts_eaten, 1)
        # 2 hareket (-2) + 2 yemek (+20) + hayalet (+200)
        self.assertEqual(state.score, 218)

    def test_respawned_ghost_is_dangerous_again(self):
        state = lane_state([Direction.LEFT])
        state.ghosts[0].frightened = True
        state.power_left = 10
        state.step(Direction.RIGHT)
        state.step(Direction.RIGHT)               # hayalet yenir, (1, 4)'e döner
        result = state.step(Direction.RIGHT)      # (1, 4)'e yürür
        self.assertTrue(result.caught)

    def test_respawned_ghost_can_catch_in_same_step(self):
        # Hayalet yenip başlangıcına döner ve aynı adımda Pacman'in karesine yürür.
        state = lane_state([Direction.LEFT, Direction.LEFT])
        state.ghosts[0].frightened = True
        state.power_left = 10
        state.step(Direction.RIGHT)
        result = state.step(Direction.RIGHT)
        self.assertEqual(result.ghosts_eaten, 1)
        self.assertTrue(result.caught)


class WinTests(unittest.TestCase):
    def test_eating_last_pellet_wins(self):
        text = """
#######
#P.  G#
#    G#
#######
"""
        state = GameState(parse_level("win", text))
        result = state.step(Direction.RIGHT)
        self.assertTrue(result.ate_pellet)
        self.assertIs(state.status, Status.WON)
        self.assertEqual(state.score, 9)

    def test_power_pellets_are_not_required(self):
        text = """
#######
#P.o G#
#    G#
#######
"""
        state = GameState(parse_level("win", text))
        state.step(Direction.RIGHT)
        self.assertIs(state.status, Status.WON)
        self.assertEqual(len(state.powers), 1)

    def test_win_stops_ghosts(self):
        text = """
######
#P.G #
#   G#
######
"""
        state = GameState(parse_level("win", text), ghost_policy=scripted([Direction.LEFT]))
        state.step(Direction.RIGHT)               # son yemek: hayalet artık gelmez
        self.assertIs(state.status, Status.WON)
        self.assertEqual(state.ghosts[0].position, (1, 3))


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
