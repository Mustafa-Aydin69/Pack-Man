"""Arayüzün kendi çizdiği bileşenler: düğme, çubuk, AI pusulası ve tuş şeması.

Hepsi düz Tkinter'dır (``Label``, ``Canvas``); renkleri ve yazı tiplerini
``theme`` modülünden alır.
"""

import tkinter as tk

import theme
from levels import Direction
from views import draw_pacman

COLORS = theme.COLORS

# Pusula ve tuş şemasındaki yönlerin ekran vektörleri (x sağa, y aşağı).
SCREEN_VECTORS = {Direction.UP: (0, -1), Direction.DOWN: (0, 1), Direction.LEFT: (-1, 0), Direction.RIGHT: (1, 0)}


class ArcadeButton(tk.Label):
    """Düz, renkli düğme. Fareyle, Enter ya da Boşluk tuşuyla çalışır; klavye odağı beyaz çerçeveyle görünür.

    ``kind``: ``"human"`` (sarı), ``"ai"`` (turkuaz) ya da ``"quiet"`` (koyu zemin, ince çerçeve).
    """

    KINDS = {
        "human": (COLORS["human"], COLORS["on_accent"], "#FFE27A"),
        "ai": (COLORS["ai"], COLORS["on_accent"], "#86EEE4"),
        "quiet": (COLORS["surface"], COLORS["text"], COLORS["surface_hi"]),
    }

    def __init__(self, parent, text, command, kind="quiet", size="body"):
        self._background, self._foreground, self._hover = self.KINDS[kind]
        self._command = command
        self._enabled = True
        border = COLORS["line_soft"] if kind == "quiet" else self._background
        super().__init__(parent, text=text, background=self._background, foreground=self._foreground,
                         font=theme.ui_font(size, "bold"), padx=theme.px(18), pady=theme.px(8),
                         cursor="hand2", takefocus=1, highlightthickness=2,
                         highlightbackground=border, highlightcolor=COLORS["text"])
        self.bind("<Enter>", lambda _e: self._paint(self._hover))
        self.bind("<Leave>", lambda _e: self._paint(self._background))
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Return>", lambda _e: self.invoke())
        self.bind("<space>", lambda _e: self.invoke())

    def _paint(self, color):
        if self._enabled:
            self.configure(background=color)

    def _on_release(self, event):
        inside = 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        if inside:
            self.invoke()

    def invoke(self):
        if self._enabled and self._command is not None:
            self._command()
        return "break"

    def set_enabled(self, enabled):
        self._enabled = enabled
        self.configure(background=self._background if enabled else COLORS["surface"],
                       foreground=self._foreground if enabled else COLORS["muted"],
                       cursor="hand2" if enabled else "arrow")


class Meter(tk.Canvas):
    """Yatay ilerleme çubuğu (enerji etkisinin kalan süresi)."""

    def __init__(self, parent, width, height, color, background):
        super().__init__(parent, width=width, height=height, background=background, highlightthickness=0)
        self._color = color
        self._fraction = 0.0
        self.bind("<Configure>", lambda _e: self._draw())

    def set(self, fraction):
        fraction = min(1.0, max(0.0, fraction))
        if fraction != self._fraction:
            self._fraction = fraction
            self._draw()

    def _draw(self):
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        self.create_rectangle(0, 0, width, height, fill=COLORS["line_soft"], outline="")
        if self._fraction > 0:
            self.create_rectangle(0, 0, width * self._fraction, height, fill=self._color, outline="")


class Compass(tk.Canvas):
    """Yapay zekânın kararı: Pacman'in çevresinde dört yön.

    Her geçerli yönde bir ok vardır; okun uzunluğu o yönün beklenen faydasını
    (o andaki seçenekler arasında) gösterir, ucunda değeri yazar. Seçilen yön
    turkuaz, bu adımda yakalanma olasılığı yüksek yön kırmızıdır. Duvara
    çıkan yönlerde ok yoktur.
    """

    RISKY = 0.2         # bu olasılıktan yüksek yakalanma riski kırmızı gösterilir

    def __init__(self, parent, size, background):
        super().__init__(parent, width=size, height=size, background=background, highlightthickness=0)
        self.size = size
        self.background = background
        self.chosen = None
        self._evaluations = []
        self._risks = {}
        self._draw()

    def show(self, evaluations, chosen, risks):
        """``evaluations``: ajanın son değerlendirmeleri; ``risks``: yön -> yakalanma olasılığı."""
        self._evaluations = list(evaluations)
        self.chosen = chosen
        self._risks = risks
        self._draw()

    def _draw(self):
        self.delete("all")
        center = self.size / 2
        inner, outer = self.size * 0.14, self.size * 0.40
        # Çevrede ince bir halka: dört yönün ortak ölçeği.
        self.create_oval(center - outer, center - outer, center + outer, center + outer,
                         outline=COLORS["line_soft"], width=1)
        draw_pacman(self, center, center, self.size * 0.08, self.chosen or Direction.RIGHT, mouth=60)
        if not self._evaluations:
            return
        utilities = [e.utility for e in self._evaluations]
        low, high = min(utilities), max(utilities)
        by_direction = {e.direction: e for e in self._evaluations}
        for direction, (vx, vy) in SCREEN_VECTORS.items():
            evaluation = by_direction.get(direction)
            if evaluation is None:
                x, y = center + vx * inner * 1.6, center + vy * inner * 1.6
                self.create_text(x, y, text="duvar", fill=COLORS["muted"], font=theme.ui_font("caption"))
                continue
            share = 1.0 if high == low else (evaluation.utility - low) / (high - low)
            length = inner + (outer - inner) * (0.2 + 0.8 * share)
            if direction is self.chosen:
                color = COLORS["ai"]
            elif self._risks.get(direction, 0.0) >= self.RISKY:
                color = COLORS["danger"]
            else:
                color = COLORS["line"]
            x0, y0 = center + vx * inner, center + vy * inner
            x1, y1 = center + vx * length, center + vy * length
            width = theme.px(9)
            self.create_line(x0, y0, x1, y1, fill=color, width=width, capstyle="round",
                             arrow="last", arrowshape=(width * 1.4, width * 1.4, width * 0.9))
            label_gap = theme.px(16)
            anchor = {(0, -1): "s", (0, 1): "n", (-1, 0): "e", (1, 0): "w"}[(vx, vy)]
            self.create_text(x1 + vx * label_gap * 0.6, y1 + vy * label_gap * 0.6, anchor=anchor,
                             text=f"{evaluation.utility:.0f}", fill=color, font=theme.display_font("small"))


class KeyPad(tk.Canvas):
    """Ok tuşları şeması; insan oyuncunun son bastığı yön sarı yanar."""

    def __init__(self, parent, key_size, background):
        gap = theme.px(6)
        width, height = key_size * 3 + gap * 2, key_size * 2 + gap
        super().__init__(parent, width=width, height=height, background=background, highlightthickness=0)
        self.key_size, self.gap = key_size, gap
        self.active = None
        self._draw()

    def show(self, direction):
        if direction is not self.active:
            self.active = direction
            self._draw()

    def _draw(self):
        self.delete("all")
        k, g = self.key_size, self.gap
        slots = {Direction.UP: (1, 0), Direction.LEFT: (0, 1), Direction.DOWN: (1, 1), Direction.RIGHT: (2, 1)}
        letters = {Direction.UP: "W", Direction.LEFT: "A", Direction.DOWN: "S", Direction.RIGHT: "D"}
        for direction, (col, row) in slots.items():
            x0, y0 = col * (k + g), row * (k + g)
            lit = direction is self.active
            self.create_rectangle(x0 + 1, y0 + 1, x0 + k - 1, y0 + k - 1,
                                  fill=COLORS["human"] if lit else COLORS["surface"],
                                  outline=COLORS["human"] if lit else COLORS["line_soft"], width=2)
            ink = COLORS["on_accent"] if lit else COLORS["text"]
            cx, cy = x0 + k / 2, y0 + k * 0.42
            vx, vy = SCREEN_VECTORS[direction]
            s = k * 0.16                      # ok başı: yöne bakan üçgen
            tip = (cx + vx * s, cy + vy * s)
            back = (cx - vx * s, cy - vy * s)
            side = (-vy * s, vx * s)
            self.create_polygon(*tip, back[0] + side[0], back[1] + side[1], back[0] - side[0], back[1] - side[1],
                                fill=ink, outline="")
            self.create_text(cx, y0 + k * 0.8, text=letters[direction], fill=ink, font=theme.display_font("small"))
