"""Karşılama ekranı: oyunun tanıtımı, kurallar ve "kim önce oynasın?" seçimi.

Ödev, iki oyuncudan hangisinin önce oynayacağının başlangıçta seçilmesini
ister. Seçim iki büyük düğmeyle yapılır; düğmeye basmak maçı başlatır.
"""

import tkinter as tk
from tkinter import ttk

import theme
from game import DEFAULT_RULES
from match import AI, HUMAN
from views import ghost_outline

C = theme.CANVAS_COLORS


class WelcomeScreen:
    def __init__(self, root, scale, on_start):
        self.root = root
        self.scale = scale
        self.on_start = on_start            # on_start(ilk_oyuncu)
        self.page = ttk.Frame(root, style="Page.TFrame", padding=self._px(theme.SPACING["page"]))
        self.page.pack(fill="both", expand=True)
        self.page.columnconfigure(0, weight=1)
        # İçerik sayfanın dikey ortasında durur; boş satırlar (0 ve 3) kalan yeri paylaşır.
        self.page.rowconfigure(0, weight=1)
        self.page.rowconfigure(3, weight=1)
        self._build_hero()
        self._build_info()

    def _px(self, value):
        return theme.px(value, self.scale)

    # ------------------------------------------------------------------
    def _build_hero(self):
        outer, card = theme.card(self.page, 24, self.scale)
        outer.grid(row=1, column=0, sticky="ew", pady=(0, self._px(theme.SPACING["gap"])))
        card.columnconfigure(1, weight=1)

        art = tk.Canvas(card, width=self._px(380), height=self._px(260), background=C["background"],
                        highlightthickness=0, **theme.tk_options())
        art.grid(row=0, column=0, sticky="w", padx=(0, self._px(32)))
        art.bind("<Configure>", lambda event: draw_illustration(art, event.width, event.height))

        text = ttk.Frame(card, style="Card.TFrame")
        text.grid(row=0, column=1, sticky="w")
        ttk.Label(text, text="Pacman", style="Card.TLabel", font=theme.font("hero_title", "bold"),
                  foreground=theme.COLORS["hero_title"], background=theme.COLORS["card"]).pack(anchor="w")
        ttk.Label(text, style="GuideBody.TLabel", wraplength=self._px(560), justify="left",
                  text="İnsan oyuncu ve fayda tabanlı yapay zekâ aynı haritada, aynı kurallarla sırayla "
                       "oynar. İkinci oyuncu için oyun sıfırlanır: harita, başlangıç konumları, yemekler "
                       "ve hayaletler birebir aynıdır.").pack(anchor="w", pady=(self._px(6), self._px(20)))
        ttk.Label(text, text="Kim önce oynasın?", style="GuideTitle.TLabel").pack(anchor="w")
        buttons = ttk.Frame(text, style="Card.TFrame")
        buttons.pack(anchor="w", pady=(self._px(10), 0))
        self.human_button = ttk.Button(buttons, text="İnsan başlasın", style="Hero.TButton",
                                       command=lambda: self.on_start(HUMAN))
        self.human_button.pack(side="left")
        self.ai_button = ttk.Button(buttons, text="Yapay zekâ başlasın", style="HeroAlt.TButton",
                                    command=lambda: self.on_start(AI))
        self.ai_button.pack(side="left", padx=(self._px(12), 0))

    def _build_info(self):
        row = ttk.Frame(self.page, style="Page.TFrame")
        row.grid(row=2, column=0, sticky="ew")
        for column in range(3):
            row.columnconfigure(column, weight=1, uniform="info")
        rules = DEFAULT_RULES
        seconds = rules.power_duration * rules.step_ms / 1000
        cards = [
            ("Puanlama", [
                ("Her hareket", f"{rules.move_cost:+d}"),
                ("Yemek", f"{rules.pellet:+d}"),
                ("Enerji topu", f"{rules.power:+d}"),
                ("Hayalet (enerji etkisinde)", f"{rules.ghost:+d}"),
                ("Enerji etkisi", f"{rules.power_duration} adım ({seconds:g} sn)"),
            ]),
            ("Kazanan nasıl belirlenir?", [
                ("1. Oyunu tamamlayan", ""),
                ("2. Eşitse yüksek puan", ""),
                ("3. Eşitse kısa süre", ""),
                ("Hepsi eşitse beraberlik", ""),
            ]),
            ("Oyun", [
                ("Seviyeler", "2 (giderek zorlaşır)"),
                ("Kontroller", "Oklar veya W A S D"),
                ("Duraklat", "Boşluk"),
                ("Normal hayalete çarpmak", "Oyun biter"),
                ("Süre", "Oyun içi adımla ölçülür"),
            ]),
        ]
        for column, (title, lines) in enumerate(cards):
            outer, card = theme.card(row, theme.SPACING["card"], self.scale)
            outer.grid(row=0, column=column, sticky="nsew",
                       padx=(0 if column == 0 else self._px(theme.SPACING["gap"]), 0))
            ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w", pady=(0, self._px(6)))
            for label, value in lines:
                line = ttk.Frame(card, style="Card.TFrame")
                line.pack(fill="x", pady=(self._px(3), 0))
                ttk.Label(line, text=label, style="Field.TLabel").pack(side="left")
                if value:
                    ttk.Label(line, text=value, style="Field.TLabel",
                              font=theme.font("body", "bold")).pack(side="right")

    def destroy(self):
        self.page.destroy()


def draw_illustration(canvas, width, height):
    """Karşılama görseli: enerji topuna doğru yemekleri yiyen Pacman ve peşindeki iki hayalet."""
    canvas.delete("all")
    r = width / 17                              # sahne yaklaşık 15 r genişliğinde, ortalanır
    cy = height * 0.45
    x = (width - 15 * r) / 2
    canvas.create_oval(x, cy - r * 0.3, x + r * 0.6, cy + r * 0.3, fill=C["power"], outline="")
    x += r * 1.5
    for _ in range(5):                          # yemek sırası
        canvas.create_oval(x - r * 0.12, cy - r * 0.12, x + r * 0.12, cy + r * 0.12, fill=C["pellet"], outline="")
        x += r * 1.2
    x += r * 0.4
    # Pacman sola bakar (ağız 180° yönünde, 70° açık).
    canvas.create_arc(x - r, cy - r, x + r, cy + r, start=180 + 35, extent=290,
                      fill=C["pacman"], outline="", style="pieslice")
    x += r * 2.6
    for i, color in enumerate(C["ghosts"][:2]):
        canvas.create_polygon(ghost_outline(x, cy, r, i), fill=color, outline="")
        for dx in (-0.35, 0.35):                # gözler Pacman'e (sola) bakar
            ex, ey = x + dx * r, cy - 0.15 * r
            canvas.create_oval(ex - 0.22 * r, ey - 0.26 * r, ex + 0.22 * r, ey + 0.26 * r,
                               fill=C["ghost_eye"], outline="")
            canvas.create_oval(ex - 0.2 * r, ey - 0.1 * r, ex + 0.02 * r, ey + 0.12 * r,
                               fill=C["ghost_pupil"], outline="")
        x += r * 2.3
    canvas.create_text(width / 2, height * 0.82, text="Fayda tabanlı rasyonel ajan",
                       fill=C["wall_edge"], font=(theme.FONT_FAMILY, max(9, int(r * 0.5)), "bold"))
