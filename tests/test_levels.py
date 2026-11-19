import unittest

from levels import LEVELS, Direction, LevelError, bfs_distances, parse_level

SMALL = """
#######
#P.o.G#
#.###.#
#....G#
#######
"""


class ParseLevelTests(unittest.TestCase):
    def test_parses_positions(self):
        level = parse_level("small", SMALL)
        self.assertEqual((level.width, level.height), (7, 5))
        self.assertEqual(level.pacman_start, (1, 1))
        self.assertEqual(level.ghost_starts, ((1, 5), (3, 5)))
        self.assertEqual(level.powers, {(1, 3)})
        self.assertIn((1, 2), level.pellets)
        self.assertNotIn(level.pacman_start, level.pellets)

    def test_rejects_ragged_rows(self):
        with self.assertRaises(LevelError):
            parse_level("x", "#####\n#P.G#\n####\n")

    def test_rejects_open_border(self):
        with self.assertRaises(LevelError):
            parse_level("x", "######\n.P.GG#\n######\n")

    def test_requires_single_pacman(self):
        with self.assertRaises(LevelError):
            parse_level("x", "#######\n#PP.GG#\n#######\n")

    def test_requires_two_ghosts(self):
        with self.assertRaises(LevelError):
            parse_level("x", "######\n#P..G#\n######\n")

    def test_rejects_unreachable_pellet(self):
        text = """
#########
#P..GG#.#
#########
"""
        with self.assertRaises(LevelError) as ctx:
            parse_level("x", text)
        self.assertIn("(1, 7)", str(ctx.exception))

    def test_rejects_unknown_character(self):
        with self.assertRaises(LevelError):
            parse_level("x", "#######\n#P.xGG#\n#######\n")


class BfsTests(unittest.TestCase):
    def test_distance_goes_around_walls(self):
        level = parse_level("small", SMALL)
        distances = bfs_distances(level, (1, 1))
        # (3, 1) Manhattan'a göre 2 adım; aradaki kare açık olduğu için BFS de 2 bulur.
        self.assertEqual(distances[(3, 1)], 2)
        # (3, 5)'e üst ya da alt koridordan 6 adımda gidilir.
        self.assertEqual(distances[(3, 5)], 6)
        self.assertNotIn((2, 3), distances)       # duvar

    def test_distances_from_is_cached(self):
        level = parse_level("small", SMALL)
        first = level.distances_from((1, 1))
        self.assertEqual(first, bfs_distances(level, (1, 1)))
        self.assertIs(level.distances_from((1, 1)), first)

    def test_moves_from_respects_walls(self):
        level = parse_level("small", SMALL)
        moves = dict(level.moves_from((1, 1)))
        self.assertEqual(set(moves), {Direction.RIGHT, Direction.DOWN})


class BuiltInLevelTests(unittest.TestCase):
    def test_levels_get_harder(self):
        first, second = LEVELS
        self.assertGreater(len(second.ghost_starts), len(first.ghost_starts))
        self.assertGreater(len(second.walls), len(first.walls))

    def test_first_level_has_no_dead_ends(self):
        level = LEVELS[0]
        open_squares = [(r, c) for r in range(level.height) for c in range(level.width) if level.is_open((r, c))]
        self.assertTrue(all(len(level.moves_from(square)) >= 2 for square in open_squares))

    def test_every_level_has_reachable_food_and_power(self):
        for level in LEVELS:
            reachable = bfs_distances(level, level.pacman_start)
            self.assertTrue(level.pellets <= reachable.keys(), level.name)
            self.assertTrue(level.powers, level.name)


class DirectionTests(unittest.TestCase):
    def test_opposites(self):
        for direction in Direction:
            self.assertEqual(direction.opposite.opposite, direction)
            self.assertEqual(direction.opposite.apply(direction.apply((5, 5))), (5, 5))


if __name__ == "__main__":
    unittest.main()
