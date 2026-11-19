"""Tkinter ana penceresi ve ekranlar arası geçiş.

Oyun kuralları ve ajan bu modülü bilmez; arayüz yalnızca onları çağırır ve
sonuçlarını çizer.
"""

import sys
import tkinter as tk

import theme
from agent import UtilityAgent
from game_screen import GameScreen
from match import AI, Match
from results import IntermissionScreen, ResultsScreen
from welcome import WelcomeScreen

APP_TITLE = "Pacman — Fayda Tabanlı Ajan"
MIN_WINDOW_WIDTH = 960
MIN_WINDOW_HEIGHT = 720


def enable_windows_dpi_awareness():
    """Windows'ta yüksek DPI ekranlarda bulanık görüntüyü önler.

    Pencere oluşturulmadan önce çağrılmalıdır. Başarılı olursa True döner;
    diğer işletim sistemlerinde ya da hata durumunda hiçbir şey yapmaz.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # sistem DPI farkındalığı
        return True
    except (AttributeError, OSError):
        try:
            import ctypes
            return bool(ctypes.windll.user32.SetProcessDPIAware())
        except (AttributeError, OSError):
            return False


def ui_scale(root):
    """Ekran ölçeği: %100 -> 1.0, %150 -> 1.5 (en az 1.0)."""
    return max(1.0, root.winfo_fpixels("1i") / 96.0)


def configure_window_size(root, scale):
    """Başlangıç boyutu kullanılabilir ekrana göre ayarlanır."""
    width = min(round(1280 * scale), int(root.winfo_screenwidth() * 0.94))
    height = min(round(900 * scale), int(root.winfo_screenheight() * 0.90))
    root.geometry(f"{width}x{height}")
    root.minsize(min(round(MIN_WINDOW_WIDTH * scale), width), min(round(MIN_WINDOW_HEIGHT * scale), height))


class AppShell:
    """Tek ana pencerede ekranlar arası geçiş.

    Akış: karşılama (kim önce?) → 1. tur → ara ekran → 2. tur → sonuç → karşılama.

    Her geçişte önceki ekran tamamen kapatılır; yeni bir Tk kök penceresi
    oluşturulmaz. Bu sayede ttkbootstrap'ın tek ``Style`` nesnesi korunur.
    """

    def __init__(self, root):
        self.root = root
        self.scale = ui_scale(root)
        self.style = theme.setup(root, self.scale)
        self.screen = None
        self.match = None
        root.title(APP_TITLE)
        configure_window_size(root, self.scale)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.show_welcome()

    def show_welcome(self):
        self._clear()
        self.match = None
        self.screen = WelcomeScreen(self.root, self.scale, on_start=self.start_match)

    def start_match(self, first_player):
        self.match = Match(first_player)
        self.show_turn()

    def show_turn(self):
        """Sıradaki oyuncunun turunu sıfırdan başlatır."""
        self._clear()
        run = self.match.new_run()
        agent = UtilityAgent() if run.player == AI else None
        self.screen = GameScreen(self.root, self.scale, run, agent=agent,
                                 on_finish=self._turn_finished, on_home=self.show_welcome)

    def _turn_finished(self, result):
        self.match.record(result)
        self._clear()
        if self.match.is_over:
            self.screen = ResultsScreen(self.root, self.scale, self.match, on_new_match=self.show_welcome)
        else:
            self.screen = IntermissionScreen(self.root, self.scale, result, self.match.current_player,
                                             on_continue=self.show_turn)

    def _clear(self):
        if self.screen is not None:
            self.screen.destroy()
            self.screen = None

    def close(self):
        self._clear()
        self.root.destroy()


def run():
    enable_windows_dpi_awareness()
    root = tk.Tk()
    AppShell(root)
    root.mainloop()
