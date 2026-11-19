"""Karşılama ekranı: oyuncu seçimi ve puan tablosu.

Ödev, iki oyuncudan hangisinin önce oynayacağının başlangıçta seçilmesini
ister. Seçim arcade makinelerindeki "oyuncu seçimi" gibi iki büyük kartla
yapılır; karta tıklamak (ya da 1 / 2 tuşu, ok tuşlarıyla seçip Enter) maçı
başlatır. Altta, orijinal makinenin tanıtım ekranındaki gibi her nesnenin
puanı kendi çizimiyle gösterilir.
"""

import tkinter as tk

import theme
from game import DEFAULT_RULES
from game_screen import label, player_color, player_sprite
from levels import Direction
from match import AI, HUMAN
from views import draw_ghost, draw_pacman, ghost_color

COLORS = theme.COLORS
C = theme.CANVAS_COLORS


class PlayerTile(tk.Canvas):
    """Oyuncu seçim kartı: oyuncunun simgesi, adı, açıklaması ve kısayol tuşu."""

    WIDTH, HEIGHT = 340, 168

    def __init__(self, parent, player, title, description, key, command):
        super().__init__(parent, width=theme.px(self.WIDTH), height=theme.px(self.HEIGHT),
                         background=COLORS["bg"], highlightthickness=0, cursor="hand2", takefocus=1)
        self.player, self.title, self.description, self.key = player, title, description, key
        self.command = command
        self.lit = False
        for sequence, handler in (("<Enter>", lambda _e: self._light(True)),
                                  ("<Leave>", lambda _e: self._light(self.focus_get() is self)),
                                  ("<FocusIn>", lambda _e: self._light(True)),
                                  ("<FocusOut>", lambda _e: self._light(False)),
                                  ("<ButtonRelease-1>", lambda _e: self.invoke()),
                                  ("<Return>", lambda _e: self.invoke()),
                                  ("<space>", lambda _e: self.invoke())):
            self.bind(sequence, handler)
        self._draw()

    def invoke(self):
        self.command()

    def _light(self, lit):
        if lit != self.lit:
            self.lit = lit
            self._draw()

    def _draw(self):
        self.delete("all")
        w, h = theme.px(self.WIDTH), theme.px(self.HEIGHT)
        color = player_color(self.player)
        # Seçilince kart oyuncunun rengiyle dolar; değilse yalnızca çerçeve.
        fill = color if self.lit else COLORS["surface"]
        ink = COLORS["on_accent"] if self.lit else COLORS["text"]
        self.create_rectangle(2, 2, w - 2, h - 2, fill=fill, outline=color, width=3)
        pad = theme.px(22)
        sx, sy, sr = pad + theme.px(22), pad + theme.px(22), theme.px(22)
        if not self.lit:
            player_sprite(self, sx, sy, sr, self.player)
        elif self.player == AI:
            draw_ghost(self, sx, sy, sr, COLORS["on_accent"], Direction.LEFT)
        else:
            draw_pacman(self, sx, sy, sr, Direction.RIGHT, 60, color=COLORS["on_accent"])
        self.create_text(w - pad, pad, anchor="ne", text=self.key, fill=ink if self.lit else color,
                         font=theme.display_font("number"))
        self.create_text(pad, h - pad - theme.px(26), anchor="sw", text=self.title, fill=ink,
                         font=theme.ui_font("heading", "bold"))
        self.create_text(pad, h - pad, anchor="sw", text=self.description,
                         fill=ink if self.lit else COLORS["muted"], font=theme.ui_font("body"))


class WelcomeScreen:
    def __init__(self, root, scale, on_start):
        self.root = root
        self.scale = scale
        self.on_start = on_start            # on_start(ilk_oyuncu)
        self.page = tk.Frame(root, background=COLORS["bg"])
        self.page.pack(fill="both", expand=True)
        # İçerik sayfanın ortasında durur.
        self.page.columnconfigure(0, weight=1)
        self.page.rowconfigure(0, weight=1)
        self.page.rowconfigure(2, weight=1)
        column = tk.Frame(self.page, background=COLORS["bg"])
        column.grid(row=1, column=0)
        self._build_title(column)
        self._build_choice(column)
        self._build_points(column)
        self._build_rules(column)
        self._keys = root.bind("<KeyPress>", self._on_key, add="+")

    def _build_title(self, column):
        tk.Label(column, text="PACMAN", font=theme.display_font("hero"),
                 foreground=COLORS["human"], background=COLORS["bg"]).pack()
        label(column, "İnsan ve yapay zekâ aynı labirentte, aynı kurallarla sırayla oynar.", "lead", "muted").pack(
            pady=(theme.px(18), 0))
        label(column, "Kim önce oynasın?", "heading", bold=True).pack(pady=(theme.px(28), theme.px(14)))

    def _build_choice(self, column):
        row = tk.Frame(column, background=COLORS["bg"])
        row.pack()
        self.human_button = PlayerTile(row, HUMAN, "İnsan başlasın", "Klavyeyle sen oynarsın", "1",
                                       lambda: self.on_start(HUMAN))
        self.human_button.pack(side="left")
        self.ai_button = PlayerTile(row, AI, "Yapay zekâ başlasın", "Fayda tabanlı ajan oynar", "2",
                                    lambda: self.on_start(AI))
        self.ai_button.pack(side="left", padx=(theme.px(20), 0))

    def _build_points(self, column):
        """Her nesnenin puanı, oyundaki çizimiyle (orijinal makinenin tanıtım ekranı gibi)."""
        rules = DEFAULT_RULES
        width, height = theme.px(700), theme.px(96)
        canvas = tk.Canvas(column, width=width, height=height, background=COLORS["bg"], highlightthickness=0)
        canvas.pack(pady=(theme.px(36), 0))
        items = [
            ("pellet", f"{rules.pellet:+d}", "Yemek"),
            ("power", f"{rules.power:+d}", "Enerji topu"),
            ("ghost", f"{rules.ghost:+d}", "Korkmuş hayalet"),
            ("move", f"{rules.move_cost:+d}", "Her hareket"),
        ]
        slot = width / len(items)
        r = theme.px(13)
        for i, (kind, points, caption) in enumerate(items):
            cx, cy = slot * i + slot / 2, theme.px(20)
            if kind == "pellet":
                canvas.create_oval(cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3, fill=C["pellet"], outline="")
            elif kind == "power":
                canvas.create_oval(cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7, fill=C["power"], outline="")
            elif kind == "ghost":
                draw_ghost(canvas, cx, cy, r, ghost_color(0), frightened=True)
            else:
                draw_pacman(canvas, cx, cy, r, Direction.RIGHT, 60)
            canvas.create_text(cx, theme.px(56), text=points, font=theme.display_font("number"),
                               fill=COLORS["danger"] if points.startswith("-") else COLORS["text"])
            canvas.create_text(cx, theme.px(84), text=caption, font=theme.ui_font("body"), fill=COLORS["muted"])

    def _build_rules(self, column):
        rules = DEFAULT_RULES
        seconds = rules.power_duration * rules.step_ms / 1000
        lines = (
            f"Enerji topu hayaletleri {rules.power_duration} adım ({seconds:g} saniye) korkutur; "
            "korkmuş hayaleti yakalarsın, normal hayalete çarpınca tur biter.",
            "Kazanan: önce bütün seviyeleri tamamlayan, eşitlikte yüksek puanlı, o da eşitse daha kısa süren.",
        )
        for i, text in enumerate(lines):
            label(column, text, "body", "muted", wraplength=theme.px(700), justify="center").pack(
                pady=(theme.px(28) if i == 0 else theme.px(6), 0))

    def _on_key(self, event):
        key = event.keysym
        if key == "1":
            self.human_button.invoke()
        elif key == "2":
            self.ai_button.invoke()
        elif key in ("Left", "Right"):
            (self.human_button if key == "Left" else self.ai_button).focus_set()

    def destroy(self):
        self.root.unbind("<KeyPress>", self._keys)
        self.page.destroy()
