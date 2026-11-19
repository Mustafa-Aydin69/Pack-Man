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
        """Ekranlar eklenene kadar gösterilen geçici sayfa."""
        self._clear()
        page = ttk.Frame(self.root, style="Page.TFrame", padding=theme.px(theme.SPACING["page"], self.scale))
        page.pack(fill="both", expand=True)
        ttk.Label(page, text="Pacman", style="Title.TLabel").pack(anchor="w")
        ttk.Label(page, text="Fayda tabanlı rasyonel ajan — yapım aşamasında",
                  style="Subtitle.TLabel").pack(anchor="w")
        self.screen = page

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
