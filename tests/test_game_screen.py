import tkinter as tk
import unittest

import theme
from agent import UtilityAgent
from game_screen import GameScreen, format_time
from levels import Direction
from match import AI, HUMAN, Run


class FormatTimeTests(unittest.TestCase):
    def test_format(self):
        self.assertEqual(format_time(0), "00:00.0")
        self.assertEqual(format_time(1350), "00:01.3")
        self.assertEqual(format_time(75_250), "01:15.2")


class GameScreenTests(unittest.TestCase):
    """Gerçek bir Tk penceresiyle; ekran yoksa (ör. sunucu) atlanır."""

    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:          # görüntü sunucusu yok
            self.skipTest(f"Tk açılamadı: {exc}")
        self.root.withdraw()
        theme.setup(self.root)
        self.finished = []

    def tearDown(self):
        self.screen.destroy()
        self.root.destroy()

    def make(self, ai):
        run = Run(AI if ai else HUMAN)
        self.screen = GameScreen(self.root, 1.0, run, agent=UtilityAgent() if ai else None,
                                 on_finish=self.finished.append)
        self.root.update()
        return self.screen

    def press(self, keysym):
        event = tk.Event()
        event.keysym = keysym
        self.screen._on_key(event)

    def test_human_key_sets_direction(self):
        screen = self.make(ai=False)
        self.press("Left")
        self.assertIs(screen.requested, Direction.LEFT)
        self.press("W")                             # büyük harf de çalışır
        self.assertIs(screen.requested, Direction.UP)

    def test_tick_moves_pacman_and_updates_hud(self):
        screen = self.make(ai=False)
        screen.phase = "playing"
        self.press("Left")
        start = screen.run.state.pacman
        screen._tick()
        self.assertNotEqual(screen.run.state.pacman, start)
        self.assertEqual(screen.stats["score"].cget("text"), str(screen.run.score))

    def test_ai_tick_fills_decision_panel(self):
        screen = self.make(ai=True)
        screen.phase = "playing"
        screen._tick()
        rows = screen.ai_table.get_children()
        self.assertEqual(len(rows), len(screen.agent.last_evaluations))
        chosen = [row for row in rows if "chosen" in screen.ai_table.item(row, "tags")]
        self.assertEqual(len(chosen), 1)

    def test_ai_ignores_keyboard(self):
        screen = self.make(ai=True)
        self.press("Left")
        self.assertIsNone(screen.requested)

    def test_pause_and_resume(self):
        screen = self.make(ai=False)
        screen.phase = "playing"
        screen.timer.start(10_000)
        screen.toggle_pause()
        self.assertEqual(screen.phase, "paused")
        self.assertTrue(screen.timer.is_paused)
        steps = screen.run.steps
        screen.toggle_pause()
        self.assertEqual(screen.phase, "playing")
        self.assertEqual(screen.run.steps, steps)   # duraklatma süreye eklenmez

    def test_caught_run_reports_result(self):
        screen = self.make(ai=False)
        screen.phase = "playing"
        state = screen.run.state
        state.ghosts[0].position = Direction.LEFT.apply(state.pacman)
        self.press("Left")
        screen._tick()                              # hayalete yürür
        self.assertEqual(screen.phase, "message")
        screen._finish()
        self.assertEqual(len(self.finished), 1)
        self.assertFalse(self.finished[0].completed)

    def test_destroy_cancels_pending_jobs(self):
        screen = self.make(ai=False)               # geri sayım işi bekliyor
        self.assertTrue(screen._jobs)
        screen.destroy()
        self.assertFalse(screen._jobs)
        self.assertFalse(screen.timer.is_pending)
        self.screen = _Dummy()                       # tearDown ikinci kez kapatmasın


class _Dummy:
    def destroy(self):
        pass


if __name__ == "__main__":
    unittest.main()
