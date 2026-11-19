"""Turlar arası ekran ve maç sonucu ekranı.

* **Ara ekran**: ilk turun sonucunu gösterir ve ikinci oyuncunun turunu
  başlatır. İkinci tur tamamen sıfırdan, aynı koşullarla başlar.
* **Sonuç ekranı**: arcade makinesindeki skor tablosu gibi iki oyuncuyu
  sıralı gösterir; kazananı ve kazananı belirleyen ölçütü yazar.
"""

import tkinter as tk

import theme
from game_screen import format_time, label, number, player_color, player_sprite
from widgets import ArcadeButton

COLORS = theme.COLORS

# Tablo sütunları: (başlık, değer, sayı mı). Sayılar piksel yazı tipiyle yazılır.
COLUMNS = (
    ("Durum", lambda r: "Tamamladı" if r.completed else "Yakalandı", False),
    ("Puan", lambda r: str(r.score), True),
    ("Süre", lambda r: format_time(r.elapsed_ms), True),
    ("Seviye", lambda r: f"{r.levels_completed}/{r.level_count}", True),
    ("Yemek", lambda r: str(r.pellets_eaten), True),
    ("Hayalet", lambda r: str(r.ghosts_eaten), True),
)
# Kazananı belirleyen ölçütün sütunu (başlığı vurgulanır).
CRITERION_COLUMN = {"Oyunu tamamladı": "Durum", "Daha yüksek puan": "Puan", "Daha kısa süre": "Süre"}
CRITERION_TEXT = {
    "Oyunu tamamladı": "bütün seviyeleri tamamladı, diğeri yakalandı",
    "Daha yüksek puan": "ikisinin de tamamlama durumu aynı; puanı daha yüksek",
    "Daha kısa süre": "tamamlama ve puan eşit; daha kısa sürede bitirdi",
    "Bütün ölçütler eşit": "tamamlama, puan ve süre birebir aynı",
}


def outcome_text(result):
    return "bütün seviyeleri tamamladı" if result.completed else "yakalandı"


class _Screen:
    def __init__(self, root):
        self.root = root
        self.page = tk.Frame(root, background=COLORS["bg"])
        self.page.pack(fill="both", expand=True)
        self.page.columnconfigure(0, weight=1)
        self.page.rowconfigure(0, weight=1)
        self.page.rowconfigure(2, weight=1)
        self.column = tk.Frame(self.page, background=COLORS["bg"])
        self.column.grid(row=1, column=0)
        self._return_binding = None

    def _bind_return(self, button):
        # Enter ana düğmeye basar.
        self._return_binding = self.root.bind("<Return>", lambda _event: button.invoke(), add="+")

    def destroy(self):
        if self._return_binding is not None:
            self.root.unbind("<Return>", self._return_binding)
        self.page.destroy()


class IntermissionScreen(_Screen):
    """İlk tur bitti; sıradaki oyuncunun turunu başlatır."""

    def __init__(self, root, scale, result, next_player, on_continue):
        super().__init__(root)
        col = self.column
        label(col, "1. tur bitti", "lead", "muted").pack(anchor="w")
        first = tk.Frame(col, background=COLORS["bg"])
        first.pack(anchor="w", pady=(theme.px(10), 0))
        self._sprite(first, result.player).pack(side="left", padx=(0, theme.px(14)))
        label(first, f"{result.player} {outcome_text(result)}", "title", player_color(result.player),
              bold=True).pack(side="left")
        numbers = tk.Frame(col, background=COLORS["bg"])
        numbers.pack(anchor="w", pady=(theme.px(16), 0))
        for i, (caption, value) in enumerate((("Puan", str(result.score)), ("Süre", format_time(result.elapsed_ms)))):
            block = tk.Frame(numbers, background=COLORS["bg"])
            block.pack(side="left", padx=(0 if i == 0 else theme.px(40), 0))
            label(block, caption, "caption", "muted").pack(anchor="w")
            number(block, value, "big").pack(anchor="w", pady=(theme.px(6), 0))

        tk.Frame(col, background=COLORS["line_soft"], height=2, width=theme.px(560)).pack(
            anchor="w", pady=theme.px(28))
        label(col, "Sırada", "lead", "muted").pack(anchor="w")
        second = tk.Frame(col, background=COLORS["bg"])
        second.pack(anchor="w", pady=(theme.px(10), 0))
        self._sprite(second, next_player).pack(side="left", padx=(0, theme.px(14)))
        label(second, next_player, "title", player_color(next_player), bold=True).pack(side="left")
        label(col, "Oyun sıfırlandı: aynı harita, aynı başlangıç konumları, aynı yemekler ve enerji topları, "
                   "aynı hayalet davranışı, aynı kurallar.", "body", "muted", wraplength=theme.px(560),
              justify="left").pack(anchor="w", pady=(theme.px(12), 0))
        kind = "ai" if player_color(next_player) == COLORS["ai"] else "human"
        self.continue_button = ArcadeButton(col, "2. turu başlat", on_continue, kind=kind, size="lead")
        self.continue_button.pack(anchor="w", pady=(theme.px(26), 0))
        label(col, "ya da Enter", "caption", "muted").pack(anchor="w", pady=(theme.px(6), 0))
        self._bind_return(self.continue_button)
        self.continue_button.focus_set()

    def _sprite(self, parent, player):
        canvas = tk.Canvas(parent, width=theme.px(44), height=theme.px(44), background=COLORS["bg"],
                           highlightthickness=0)
        player_sprite(canvas, theme.px(22), theme.px(22), theme.px(18), player)
        return canvas


class ResultsScreen(_Screen):
    """Maç sonucu: iki oyuncunun skor tablosu ve kazanan."""

    def __init__(self, root, scale, match, on_new_match):
        super().__init__(root)
        verdict = match.verdict()
        self.verdict = verdict
        col = self.column

        label(col, "Maç sonucu", "lead", "muted").pack(anchor="w")
        if verdict.is_draw:
            headline, color = "Berabere", COLORS["text"]
        else:
            headline, color = f"{verdict.winner.player} kazandı", player_color(verdict.winner.player)
        self.headline = label(col, headline, "title", color, bold=True)
        self.headline.configure(font=theme.display_font("big"))
        self.headline.pack(anchor="w", pady=(theme.px(10), 0))
        reason = CRITERION_TEXT[verdict.criterion]
        label(col, f"Belirleyici ölçüt: {verdict.criterion.lower()} ({reason})", "body", "muted").pack(
            anchor="w", pady=(theme.px(12), theme.px(24)))

        self._build_table(col, match, verdict)

        self.new_button = ArcadeButton(col, "Yeni maç", on_new_match, kind="human", size="lead")
        self.new_button.pack(anchor="w", pady=(theme.px(28), 0))
        label(col, "ya da Enter", "caption", "muted").pack(anchor="w", pady=(theme.px(6), 0))
        self._bind_return(self.new_button)
        self.new_button.focus_set()

    def _build_table(self, parent, match, verdict):
        """Skor tablosu: kazanan üstte, satırı kendi renginde vurgulu."""
        table = tk.Frame(parent, background=COLORS["bg"])
        table.pack(anchor="w")
        rows = list(match.results)
        if verdict.winner is not None:
            rows.sort(key=lambda r: r is not verdict.winner)
        decisive = CRITERION_COLUMN.get(verdict.criterion)
        cell_x, cell_y = theme.px(16), theme.px(12)

        # Başlık satırı: belirleyici ölçütün sütunu beyaz, diğerleri soluk.
        label(table, "", "caption").grid(row=0, column=0)
        # Başlıklar hücrelerle aynı iç boşlukla (ipadx) yerleşir ki değerlerin tam üstünde dursun.
        label(table, "Oyuncu", "caption", "muted", anchor="w").grid(row=0, column=1, columnspan=2, sticky="ew",
                                                                     ipadx=cell_x)
        for c, (title, _, _) in enumerate(COLUMNS, start=3):
            label(table, title, "caption", "text" if title == decisive else "muted", bold=title == decisive,
                  anchor="w").grid(row=0, column=c, sticky="ew", ipadx=cell_x, pady=(0, theme.px(6)))

        for i, result in enumerate(rows, start=1):
            winner = result is verdict.winner
            background = COLORS["surface_hi"] if winner else COLORS["surface"]
            color = player_color(result.player)
            # Satırın solunda oyuncu renginde bir şerit; kazananın satırı daha açık.
            tk.Frame(table, background=color if winner else COLORS["line_soft"], width=theme.px(4)).grid(
                row=i, column=0, sticky="ns", pady=(0, 2))
            rank = number(table, f"{i}.", "number", color if winner else "muted", background)
            rank.grid(row=i, column=1, sticky="nsew", ipadx=cell_x, pady=(0, 2))
            who = tk.Frame(table, background=background)
            who.grid(row=i, column=2, sticky="nsew", pady=(0, 2))
            sprite = tk.Canvas(who, width=theme.px(30), height=theme.px(30), background=background,
                               highlightthickness=0)
            player_sprite(sprite, theme.px(15), theme.px(15), theme.px(12), result.player)
            sprite.pack(side="left", padx=(theme.px(4), theme.px(8)), pady=cell_y)
            label(who, result.player, "lead", color, background, bold=True).pack(side="left", padx=(0, cell_x))
            for c, (title, value, numeric) in enumerate(COLUMNS, start=3):
                text = value(result)
                if numeric:
                    widget = number(table, text, "number", "text", background)
                else:
                    tint = "text" if result.completed else "danger"
                    widget = label(table, text, "body", tint, background, bold=True)
                widget.grid(row=i, column=c, sticky="nsew", ipadx=cell_x, ipady=cell_y, pady=(0, 2))
                widget.configure(anchor="w")
