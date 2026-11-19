"""Turlar arası ekran ve maç sonucu ekranı.

* **Ara ekran**: ilk turun sonucunu gösterir ve ikinci oyuncunun turunu
  başlatır. İkinci tur tamamen sıfırdan, aynı koşullarla başlar.
* **Sonuç ekranı**: iki oyuncunun sonuçlarını yan yana gösterir, kazananı ve
  kazananı belirleyen ölçütü yazar.
"""

import tkinter as tk
from tkinter import ttk

import theme
from game_screen import format_time
from match import AI

ROWS = [
    ("Durum", lambda r: "Tamamladı" if r.completed else "Yakalandı"),
    ("Toplam puan", lambda r: str(r.score)),
    ("Süre", lambda r: format_time(r.elapsed_ms)),
    ("Tamamlanan seviye", lambda r: f"{r.levels_completed} / {r.level_count}"),
    ("Yenen yemek", lambda r: str(r.pellets_eaten)),
    ("Yenen hayalet", lambda r: str(r.ghosts_eaten)),
    ("Adım", lambda r: str(r.steps)),
]

# Kazananı belirleyen ölçütün tablodaki satırı (vurgulanır).
CRITERION_ROW = {"Oyunu tamamladı": "Durum", "Daha yüksek puan": "Toplam puan", "Daha kısa süre": "Süre"}


def player_color(player):
    return theme.COLORS["ai"] if player == AI else theme.COLORS["human"]


class _Screen:
    def __init__(self, root, scale):
        self.root = root
        self.scale = scale
        self.page = ttk.Frame(root, style="Page.TFrame", padding=self._px(theme.SPACING["page"]))
        self.page.pack(fill="both", expand=True)
        self.page.columnconfigure(0, weight=1)
        self.page.rowconfigure(0, weight=1)
        self._return_binding = None

    def _px(self, value):
        return theme.px(value, self.scale)

    def _centered_card(self, width):
        holder = ttk.Frame(self.page, style="Page.TFrame")
        holder.grid(row=0, column=0)
        outer, card = theme.card(holder, 28, self.scale)
        outer.pack()
        card.configure(width=self._px(width))
        return card

    def _bind_return(self, command):
        # Enter ana düğmeye basar.
        self._return_binding = self.root.bind("<Return>", lambda _event: command(), add="+")

    def destroy(self):
        if self._return_binding is not None:
            self.root.unbind("<Return>", self._return_binding)
        self.page.destroy()


class IntermissionScreen(_Screen):
    """İlk tur bitti; sıradaki oyuncunun turunu başlatır."""

    def __init__(self, root, scale, result, next_player, on_continue):
        super().__init__(root, scale)
        card = self._centered_card(560)
        ttk.Label(card, text="1. tur bitti", style="GuideTitle.TLabel").pack(anchor="w")
        outcome = "bütün seviyeleri tamamladı" if result.completed else "yakalandı"
        ttk.Label(card, style="GuideBody.TLabel", wraplength=self._px(520), justify="left",
                  text=f"{result.player} {outcome}: {result.score} puan, "
                       f"{format_time(result.elapsed_ms)}.").pack(anchor="w", pady=(self._px(6), 0))
        ttk.Separator(card).pack(fill="x", pady=self._px(18))
        ttk.Label(card, text=f"Sıradaki oyuncu: {next_player}", style="CardTitle.TLabel",
                  foreground=player_color(next_player)).pack(anchor="w")
        ttk.Label(card, style="CardNote.TLabel", wraplength=self._px(520), justify="left",
                  text="Oyun sıfırlandı: aynı harita, aynı başlangıç konumları, aynı yemekler ve enerji "
                       "topları, aynı hayalet davranışı ve aynı kurallar.").pack(anchor="w", pady=(self._px(4), 0))
        self.continue_button = ttk.Button(card, text="2. turu başlat  (Enter)", style="Hero.TButton",
                                          command=on_continue)
        self.continue_button.pack(anchor="w", pady=(self._px(22), 0))
        self._bind_return(on_continue)


class ResultsScreen(_Screen):
    """Maç sonucu: iki oyuncunun karşılaştırması ve kazanan."""

    def __init__(self, root, scale, match, on_new_match):
        super().__init__(root, scale)
        verdict = match.verdict()
        self.verdict = verdict
        card = self._centered_card(720)

        if verdict.is_draw:
            headline, color = "Berabere!", theme.COLORS["warning"]
        else:
            headline, color = f"Kazanan: {verdict.winner.player}", player_color(verdict.winner.player)
        ttk.Label(card, text="Maç sonucu", style="CardNote.TLabel").pack(anchor="w")
        self.headline = ttk.Label(card, text=headline, style="GuideTitle.TLabel", foreground=color,
                                  font=theme.font("hero_subtitle", "bold"))
        self.headline.pack(anchor="w")
        ttk.Label(card, text=f"Belirleyici ölçüt: {verdict.criterion}", style="CardNote.TLabel").pack(
            anchor="w", pady=(self._px(2), self._px(16)))

        self._build_table(card, match, verdict)

        ttk.Label(card, style="Muted.TLabel", wraplength=self._px(660), justify="left",
                  text="Kazanan sırasıyla şu ölçütlerle belirlenir: oyunu tamamlama, toplam puan, "
                       "daha kısa süre. Bütün ölçütler eşitse maç berabere biter.").pack(
            anchor="w", pady=(self._px(14), 0))
        self.new_button = ttk.Button(card, text="Yeni maç  (Enter)", style="Hero.TButton", command=on_new_match)
        self.new_button.pack(anchor="w", pady=(self._px(20), 0))
        self._bind_return(on_new_match)

    def _build_table(self, card, match, verdict):
        table = tk.Frame(card, background=theme.COLORS["border"], **theme.tk_options())
        table.pack(fill="x")
        results = match.results
        highlight_row = CRITERION_ROW.get(verdict.criterion)
        cell = dict(padx=self._px(14), pady=self._px(7), anchor="w")

        def put(row, column, text, bold=False, fg=None, bg=None):
            label = tk.Label(table, text=text, background=bg or theme.COLORS["card"],
                             foreground=fg or theme.COLORS["text"],
                             font=theme.font("body", "bold") if bold else theme.font("body"),
                             **cell, **theme.tk_options())
            label.grid(row=row, column=column, sticky="nsew", padx=(0, 1), pady=(0, 1))
            return label

        put(0, 0, "", bg=theme.COLORS["heading_bg"])
        for column, result in enumerate(results, start=1):
            tag = f"{column}. tur · {result.player}"
            if verdict.winner is result:
                # ★ (U+2605) Tk 8.6'nın çizebildiği bir karakterdir; emoji (ör. kupa) çizilemez.
                tag += "  ★"
            put(0, column, tag, bold=True, fg=player_color(result.player), bg=theme.COLORS["heading_bg"])
        for row, (name, getter) in enumerate(ROWS, start=1):
            emphasised = name == highlight_row
            background = theme.COLORS["select_bg"] if emphasised else None
            put(row, 0, name, bold=emphasised, bg=background)
            for column, result in enumerate(results, start=1):
                winner_cell = emphasised and verdict.winner is result
                put(row, column, getter(result), bold=winner_cell, bg=background)
        for column in range(3):
            table.columnconfigure(column, weight=1, uniform="results")
