import unittest

import ghosts
from agent import DEFAULT_WEIGHTS, UtilityAgent
from game import GameState, Status
from levels import LEVELS, Direction, parse_level


def state_of(text, seed=0):
    return GameState(parse_level("test", text), seed=seed, ghost_policy=ghosts.policy)


class DecisionTests(unittest.TestCase):
    def test_eats_adjacent_pellet(self):
        state = state_of("""
###########
#   P.   G#
#        G#
###########
""")
        self.assertEqual(UtilityAgent().choose(state), Direction.RIGHT)

    def test_eats_pellet_even_if_next_one_is_far(self):
        # Sağdaki yemek yenince kalan tek yemek çok uzakta kalır; ajan yine de yemeli.
        # Yenen yemek ödülü olmasaydı sol (yemeğe 2 adım) sağdan (yemek, sonra 14 adım) iyi görünürdü.
        state = state_of("""
#####################
#.            P.    #
################### #
#                 GG#
#####################
""")
        self.assertEqual(UtilityAgent().choose(state), Direction.RIGHT)

    def test_does_not_walk_into_ghost(self):
        state = state_of("""
#########
#.  PG ##
#.  ## G#
#########
""")
        choice = UtilityAgent().choose(state)
        self.assertNotEqual(choice, Direction.RIGHT)

    def test_eats_power_pellet_when_chased(self):
        # Takipçi (1, 7) yaklaşıyor; Pacman'in solunda enerji topu var.
        state = state_of("""
##########
#   oP  G#
#.###### #
#.      G#
##########
""")
        self.assertEqual(UtilityAgent().choose(state), Direction.LEFT)

    def test_hunts_frightened_ghost(self):
        state = state_of("""
##########
#.  P G  #
#.     G #
##########
""")
        for ghost in state.ghosts:
            ghost.frightened = True
        state.power_left = 20
        self.assertEqual(UtilityAgent().choose(state), Direction.RIGHT)

    def test_choose_does_not_change_state(self):
        state = ghosts.new_game(LEVELS[1])
        snapshot = (state.pacman, state.score, state.steps, set(state.pellets),
                    [g.position for g in state.ghosts], state.rng.getstate())
        UtilityAgent().choose(state)
        self.assertEqual(snapshot, (state.pacman, state.score, state.steps, set(state.pellets),
                                    [g.position for g in state.ghosts], state.rng.getstate()))

    def test_does_not_peek_at_random_generator(self):
        # Yalnızca rastgele üretecin durumu farklı iki oyun: ajanın kararı ve
        # bütün hesapları aynı olmalı (ajan geleceği üreteçten okumaz).
        a, b = ghosts.new_game(LEVELS[1], seed=1), ghosts.new_game(LEVELS[1], seed=999)
        for _ in range(6):                        # gezginler Pacman'e yaklaşsın diye
            direction = UtilityAgent().choose(a)
            a.step(direction)
        b.pacman, b.direction, b.steps, b.score = a.pacman, a.direction, a.steps, a.score
        b.pellets, b.powers = set(a.pellets), set(a.powers)
        for ghost, other in zip(b.ghosts, a.ghosts):
            ghost.position, ghost.direction, ghost.frightened = other.position, other.direction, other.frightened
        agent_a, agent_b = UtilityAgent(), UtilityAgent()
        self.assertEqual(agent_a.choose(a), agent_b.choose(b))
        self.assertEqual([e.utility for e in agent_a.last_evaluations],
                         [e.utility for e in agent_b.last_evaluations])

    def test_evaluations_cover_legal_directions(self):
        state = ghosts.new_game(LEVELS[0])
        agent = UtilityAgent()
        agent.choose(state)
        self.assertEqual([e.direction for e in agent.last_evaluations], state.legal_directions())
        for evaluation in agent.last_evaluations:
            self.assertIn("puan", evaluation.parts)


class UtilityTests(unittest.TestCase):
    def test_loss_dominates(self):
        state = state_of("""
#######
#P.  G#
#    G#
#######
""")
        lost = state.clone()
        lost.status = Status.LOST
        agent = UtilityAgent()
        self.assertLess(agent.utility(state, lost), -DEFAULT_WEIGHTS.loss / 2)

    def test_eat_bonus_exceeds_largest_distance_jump(self):
        # Ağırlık gerekçesi: bir yemek yemenin faydası, en uzak yemeğe olan
        # mesafe sıçramasından büyük olmalı.
        for level in LEVELS:
            longest = max(max(level.distances_from(p).values()) for p in level.pellets)
            self.assertGreater(DEFAULT_WEIGHTS.eat + 10, DEFAULT_WEIGHTS.food * longest, level.name)


class PlayTests(unittest.TestCase):
    def test_completes_first_level(self):
        state = ghosts.new_game(LEVELS[0])
        agent = UtilityAgent()
        while not state.is_over and state.steps < 2000:
            state.step(agent.choose(state))
        self.assertIs(state.status, Status.WON)


if __name__ == "__main__":
    unittest.main()
