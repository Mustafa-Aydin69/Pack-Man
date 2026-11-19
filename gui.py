"""Tkinter ana penceresi ve ekranlar arası geçiş.

Oyun kuralları ve ajan bu modülü bilmez; arayüz yalnızca onları çağırır ve
sonuçlarını çizer.
"""

import sys
import tkinter as tk
from tkinter import ttk

import theme

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

    Her geçişte önceki ekran tamamen kapatılır; yeni bir Tk kök penceresi
    oluşturulmaz. Bu sayede ttkbootstrap'ın tek ``Style`` nesnesi korunur.
    """

    def __init__(self, root):
        self.root = root
        self.scale = ui_scale(root)
        self.style = theme.setup(root, self.scale)
        self.screen = None
        root.title(APP_TITLE)
        configure_window_size(root, self.scale)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.show_placeholder()

    def show_placeholder(self):
        """Geçici başlangıç ekranı: karşılama ve maç akışı eklenene kadar tek tur oynatır."""
        self._clear()
        page = ttk.Frame(self.root, style="Page.TFrame", padding=theme.px(theme.SPACING["page"], self.scale))
        page.pack(fill="both", expand=True)
        ttk.Label(page, text="Pacman", style="Title.TLabel").pack(anchor="w")
        ttk.Label(page, text="Fayda tabanlı rasyonel ajan", style="Subtitle.TLabel").pack(anchor="w")
        buttons = ttk.Frame(page, style="Page.TFrame")
        buttons.pack(anchor="w", pady=(theme.px(16, self.scale), 0))
        ttk.Button(buttons, text="İnsan olarak oyna", command=lambda: self.show_game(ai=False),
                   **theme.button_options("primary")).pack(side="left")
        ttk.Button(buttons, text="Yapay zekâyı izle", command=lambda: self.show_game(ai=True),
                   **theme.button_options("outline")).pack(side="left", padx=(theme.px(8, self.scale), 0))
        self.screen = page

    def show_game(self, ai):
        from agent import UtilityAgent
        from game_screen import GameScreen
        from match import AI, HUMAN, Run

        self._clear()
        run = Run(AI if ai else HUMAN)
        self.screen = GameScreen(self.root, self.scale, run, agent=UtilityAgent() if ai else None,
                                 on_finish=lambda _result: self.show_placeholder(),
                                 on_home=self.show_placeholder)

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
