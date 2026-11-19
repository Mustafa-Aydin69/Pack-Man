import tkinter as tk
import unittest

import gui
from game_screen import GameScreen
from match import AI, HUMAN, Match, RunResult
from results import IntermissionScreen, ResultsScreen
from welcome import WelcomeScreen


def result(player, completed=True, score=1000, elapsed_ms=60_000):
    return RunResult(player, completed, score, elapsed_ms, elapsed_ms // 150, 2 if completed else 1, 2, 200, 1)


class _TkTestCase(unittest.TestCase):
    """Gerçek bir Tk penceresiyle; ekran yoksa (ör. sunucu) atlanır."""

    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk açılamadı: {exc}")
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()


class ShellFlowTests(_TkTestCase):
    def setUp(self):
        super().setUp()
        self.shell = gui.AppShell(self.root)

    def tearDown(self):
        self.shell._clear()
        super().tearDown()

    def test_starts_on_welcome(self):
        self.assertIsInstance(self.shell.screen, WelcomeScreen)

    def test_welcome_buttons_choose_first_player(self):
        self.shell.screen.ai_button.invoke()
        self.assertEqual(self.shell.match.order, (AI, HUMAN))
        self.assertIsInstance(self.shell.screen, GameScreen)
        self.assertTrue(self.shell.screen.is_ai)
        self.shell.show_welcome()
        self.shell.screen.human_button.invoke()
        self.assertEqual(self.shell.match.order, (HUMAN, AI))
        self.assertFalse(self.shell.screen.is_ai)

    def test_full_match_flow(self):
        self.shell.start_match(HUMAN)
        self.shell._turn_finished(result(HUMAN, score=900))
        self.assertIsInstance(self.shell.screen, IntermissionScreen)
        self.shell.screen.continue_button.invoke()
        self.assertIsInstance(self.shell.screen, GameScreen)
        self.assertEqual(self.shell.screen.run.player, AI)
        self.assertEqual(self.shell.screen.run.steps, 0)        # ikinci tur sıfırdan başlar
        self.shell._turn_finished(result(AI, score=1200))
        self.assertIsInstance(self.shell.screen, ResultsScreen)
        self.assertEqual(self.shell.screen.verdict.winner.player, AI)
        self.shell.screen.new_button.invoke()
        self.assertIsInstance(self.shell.screen, WelcomeScreen)
        self.assertIsNone(self.shell.match)

    def test_home_button_abandons_match(self):
        self.shell.start_match(AI)
        self.shell.screen._go_home()
        self.assertIsInstance(self.shell.screen, WelcomeScreen)
        self.assertIsNone(self.shell.match)


class ResultsScreenTests(_TkTestCase):
    def finished_match(self, first, second):
        match = Match(first.player)
        match.record(first)
        match.record(second)
        return match

    def test_headline_names_winner(self):
        match = self.finished_match(result(AI, completed=False, score=5000), result(HUMAN, completed=True))
        screen = ResultsScreen(self.root, 1.0, match, on_new_match=lambda: None)
        self.assertEqual(screen.headline.cget("text"), "Kazanan: İnsan")
        screen.destroy()

    def test_draw(self):
        match = self.finished_match(result(HUMAN), result(AI))
        screen = ResultsScreen(self.root, 1.0, match, on_new_match=lambda: None)
        self.assertEqual(screen.headline.cget("text"), "Berabere!")
        screen.destroy()

    def test_enter_binding_is_removed_on_destroy(self):
        match = self.finished_match(result(HUMAN), result(AI, score=1))
        screen = ResultsScreen(self.root, 1.0, match, on_new_match=lambda: None)
        self.assertTrue(self.root.bind("<Return>"))
        screen.destroy()
        self.assertFalse(self.root.bind("<Return>"))   # kapanan ekran Enter'ı dinlememeli

if __name__ == "__main__":
    unittest.main()
