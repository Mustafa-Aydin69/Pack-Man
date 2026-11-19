"""Oyun ekranı: tahta, gösterge paneli (HUD), klavye ve oyun döngüsü.

Ekran bir ``match.Run``'ı (bir oyuncunun turu) oynatır. Oyuncu insansa yön
klavyeden gelir; yapay zekâysa her adımda ``UtilityAgent.choose`` çağrılır.
Kurallar ve zamanlama iki oyuncu için birebir aynıdır: oyun her
``Rules.step_ms`` milisaniyede bir adım ilerler.

Akış: geri sayım (3-2-1) → oyun → seviye bitince geçiş mesajı ve sonraki
seviyenin geri sayımı → tur bitince sonuç mesajı → ``on_finish(RunResult)``.
"""

import tkinter as tk
from tkinter import ttk

import ghosts
import theme
from levels import Direction
from timers import PausableTimer
from views import BoardView

KEY_DIRECTIONS = {
    "Up": Direction.UP, "Down": Direction.DOWN, "Left": Direction.LEFT, "Right": Direction.RIGHT,
    "w": Direction.UP, "s": Direction.DOWN, "a": Direction.LEFT, "d": Direction.RIGHT,
}
COUNTDOWN_MS = 600          # geri sayımın her rakamı
LEVEL_MESSAGE_MS = 1600     # "Seviye tamamlandı" mesajının süresi
FINISH_MESSAGE_MS = 2200    # tur sonu mesajının süresi


def format_time(ms):
    """Oyun içi süre: ``dd:ss.d``."""
    seconds, tenths = divmod(int(ms) // 100, 10)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}.{tenths}"


class GameScreen:
    """Bir oyuncunun turunu oynatan ekran."""

    def __init__(self, root, scale, run, agent=None, on_finish=None, on_home=None):
        self.root = root
        self.scale = scale
        self.run = run
        self.agent = agent                  # None: insan oyuncu
        self.on_finish = on_finish
        self.on_home = on_home
        self.requested = None               # insan oyuncunun son bastığı yön
        self.frame = 0                      # animasyon sayacı
        self.phase = "countdown"            # countdown | playing | paused | message | finished
        self._jobs = []                     # bekleyen root.after işleri (kapatılırken iptal edilir)
        self.timer = PausableTimer(root, self._tick)

        self.page = ttk.Frame(root, style="Page.TFrame", padding=self._px(theme.SPACING["page"]))
        self.page.pack(fill="both", expand=True)
        self.page.columnconfigure(0, weight=1)
        self.page.rowconfigure(1, weight=1)
        self._build_header()
        self._build_body()
        self._key_binding = root.bind("<KeyPress>", self._on_key, add="+")
        # Klavye olayları odaktaki pencereye gelir; ekran açılır açılmaz oyuna gitsin.
        root.focus_force()

        self.board.show(run.state, self.frame)
        self._refresh_hud()
        self._after(50, self._countdown, 3)

    # ------------------------------------------------------------------
    # Yerleşim
    # ------------------------------------------------------------------
    def _px(self, value):
        return theme.px(value, self.scale)

    @property
    def is_ai(self):
        return self.agent is not None

    def _build_header(self):
        header = ttk.Frame(self.page, style="Page.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, self._px(theme.SPACING["gap"])))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Pacman", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.subtitle = ttk.Label(header, style="Subtitle.TLabel")
        self.subtitle.grid(row=1, column=0, sticky="w")
        self.pause_button = ttk.Button(header, text=theme.button_text("pause", "Duraklat"),
                                       command=self.toggle_pause, takefocus=False,
                                       **theme.button_options("secondary"))
        self.pause_button.grid(row=0, column=1, rowspan=2, padx=(0, self._px(8)))
        ttk.Button(header, text=theme.button_text("home", "Ana Menü"), command=self._go_home,
                   takefocus=False, **theme.button_options("outline")).grid(row=0, column=2, rowspan=2)

    def _build_body(self):
        body = ttk.Frame(self.page, style="Page.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        board_outer, board_body = theme.card(body, 10, self.scale)
        board_outer.grid(row=0, column=0, sticky="nsew", padx=(0, self._px(theme.SPACING["gap"])))
        canvas = tk.Canvas(board_body, width=self._px(560), height=self._px(420), **theme.tk_options())
        canvas.pack(fill="both", expand=True)
        self.board = BoardView(canvas)

        side = ttk.Frame(body, style="Page.TFrame", width=self._px(360))
        side.grid(row=0, column=1, sticky="ns")
        side.columnconfigure(0, weight=1)
        side.rowconfigure(1, weight=1)
        self._build_stats(side)
        if self.is_ai:
            self._build_ai_panel(side)
        else:
            self._build_controls_help(side)

    def _section_title(self, parent, text):
        return ttk.Label(parent, text=text, style="CardTitle.TLabel")

    def _build_stats(self, parent):
        outer, card = theme.card(parent, theme.SPACING["card"], self.scale)
        outer.grid(row=0, column=0, sticky="ew", pady=(0, self._px(theme.SPACING["gap"])))
        self._section_title(card, "Oyun durumu").grid(row=0, column=0, columnspan=2, sticky="w")
        self.stats = {}
        tiles = [("score", "Puan"), ("time", "Süre"), ("food", "Kalan yemek"), ("level", "Seviye"),
                 ("ghosts_eaten", "Yenen hayalet"), ("player", "Oyuncu")]
        for i, (key, caption) in enumerate(tiles):
            row, col = 1 + (i // 2) * 2, i % 2
            ttk.Label(card, text=caption, style="StatCaption.TLabel").grid(
                row=row, column=col, sticky="w", pady=(self._px(8), 0), padx=(0, self._px(24)))
            label = ttk.Label(card, text="–", style="StatValue.TLabel")
            label.grid(row=row + 1, column=col, sticky="w", padx=(0, self._px(24)))
            self.stats[key] = label

        ttk.Label(card, text="Enerji etkisi", style="StatCaption.TLabel").grid(
            row=7, column=0, sticky="w", pady=(self._px(10), 0))
        self.power_text = ttk.Label(card, text="Yok", style="Muted.TLabel")
        self.power_text.grid(row=7, column=1, sticky="e", pady=(self._px(10), 0))
        self.power_bar = ttk.Progressbar(card, maximum=self.run.rules.power_duration, mode="determinate",
                                         **theme.widget_options("warning"))
        self.power_bar.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(self._px(4), 0))

        ttk.Label(card, text="Hayaletler", style="StatCaption.TLabel").grid(
            row=9, column=0, sticky="w", pady=(self._px(10), 0))
        self.ghost_rows = ttk.Frame(card, style="Card.TFrame")
        self.ghost_rows.grid(row=10, column=0, columnspan=2, sticky="ew")
        self._ghost_labels = []

    def _build_controls_help(self, parent):
        outer, card = theme.card(parent, theme.SPACING["card"], self.scale)
        outer.grid(row=1, column=0, sticky="new")
        self._section_title(card, "Kontroller").pack(anchor="w")
        lines = [
            ("← ↑ → ↓  veya  W A S D", "Yön değiştir"),
            ("Boşluk", "Duraklat / Devam"),
        ]
        for keys, meaning in lines:
            row = ttk.Frame(card, style="Card.TFrame")
            row.pack(fill="x", pady=(self._px(8), 0))
            ttk.Label(row, text=keys, style="Field.TLabel", font=theme.font("body", "bold")).pack(side="left")
            ttk.Label(row, text=meaning, style="Muted.TLabel").pack(side="right")
        ttk.Label(card, style="CardNote.TLabel", wraplength=self._px(320), justify="left",
                  text="Pacman bastığın yönde ilerlemeye devam eder. Dönüş tuşuna kavşaktan "
                       "önce basabilirsin; Pacman ilk uygun yerde döner.").pack(anchor="w", pady=(self._px(12), 0))

    def _build_ai_panel(self, parent):
        outer, card = theme.card(parent, theme.SPACING["card"], self.scale)
        outer.grid(row=1, column=0, sticky="nsew")
        self._section_title(card, "Yapay zekânın kararı").pack(anchor="w")
        self.decision_text = ttk.Label(card, text="–", style="CardNote.TLabel", wraplength=self._px(330))
        self.decision_text.pack(anchor="w", pady=(self._px(4), self._px(8)))
        columns = ("dir", "utility", "risk", "food", "danger", "trap", "hunt")
        headings = ("Yön", "Fayda", "Risk", "Yemek", "Tehlike", "Kaçış", "Av")
        widths = (64, 64, 50, 54, 58, 52, 40)
        self.ai_table = ttk.Treeview(card, columns=columns, show="headings", height=4, selectmode="none",
                                     style="Log.Treeview")
        for column, heading, width in zip(columns, headings, widths):
            self.ai_table.heading(column, text=heading)
            self.ai_table.column(column, width=self._px(width), anchor="e" if column != "dir" else "w",
                                 stretch=False)
        self.ai_table.tag_configure("chosen", background=theme.COLORS["select_bg"])
        self.ai_table.pack(fill="x")
        ttk.Label(card, style="Muted.TLabel", wraplength=self._px(330), justify="left",
                  text="Fayda: 2 adım ileri bakışla beklenen fayda; en yükseği seçilir. Diğer sütunlar "
                       "bu adımın olası sonuçları üzerinden fayda bileşenlerinin ortalamasıdır. "
                       "Risk: bu adımda yakalanma olasılığı.").pack(anchor="w", pady=(self._px(8), 0))

    # ------------------------------------------------------------------
    # Oyun döngüsü
    # ------------------------------------------------------------------
    def _countdown(self, value):
        self.phase = "countdown"
        if value > 0:
            self.board.overlay(str(value), self.run.level.name)
            self._after(COUNTDOWN_MS, self._countdown, value - 1)
        else:
            self.board.clear_overlay()
            self.phase = "playing"
            self.timer.start(self.run.rules.step_ms)

    def _tick(self):
        state = self.run.state
        direction = self.agent.choose(state) if self.is_ai else self.requested
        state.step(direction)
        self.frame += 1
        self.board.show(state, self.frame)
        self._refresh_hud()
        if self.is_ai:
            self._refresh_ai_panel(direction)
        if self.run.has_next_level:
            self._show_message("Seviye tamamlandı!", f"Sıradaki: {self.run.levels[self.run.level_index + 1].name}")
            self._after(LEVEL_MESSAGE_MS, self._start_next_level)
        elif self.run.is_over:
            if self.run.completed:
                self._show_message("Tebrikler!", f"Bütün seviyeler tamamlandı · {self.run.score} puan")
            else:
                self._show_message("Yakalandın!", f"{self.run.score} puan")
            self._after(FINISH_MESSAGE_MS, self._finish)
        else:
            self.timer.start(self.run.rules.step_ms)

    def _show_message(self, title, subtitle):
        self.phase = "message"
        self.board.overlay(title, subtitle)
        self.pause_button.state(["disabled"])

    def _start_next_level(self):
        self.run.next_level()
        self.requested = None
        self.frame = 0
        self.pause_button.state(["!disabled"])
        self.board.show(self.run.state, self.frame)
        self._refresh_hud()
        self._countdown(3)

    def _finish(self):
        self.phase = "finished"
        if self.on_finish is not None:
            self.on_finish(self.run.result())

    # ------------------------------------------------------------------
    # Girdi
    # ------------------------------------------------------------------
    def _on_key(self, event):
        key = event.keysym if len(event.keysym) > 1 else event.keysym.lower()
        if key == "space":
            self.toggle_pause()
        elif not self.is_ai and key in KEY_DIRECTIONS and self.phase in ("countdown", "playing"):
            # Geri sayım sırasında basılan yön de saklanır: oyun başlar başlamaz uygulanır.
            self.requested = KEY_DIRECTIONS[key]

    def toggle_pause(self):
        if self.phase == "playing":
            self.timer.pause()
            self.phase = "paused"
            self.board.overlay("Duraklatıldı", "Devam etmek için Boşluk")
            self.pause_button.configure(text=theme.button_text("resume", "Devam"))
        elif self.phase == "paused":
            self.board.clear_overlay()
            self.phase = "playing"
            self.pause_button.configure(text=theme.button_text("pause", "Duraklat"))
            self.timer.resume()

    def _go_home(self):
        if self.on_home is not None:
            self.on_home()

    # ------------------------------------------------------------------
    # Gösterge paneli
    # ------------------------------------------------------------------
    def _refresh_hud(self):
        run, state = self.run, self.run.state
        self.subtitle.configure(text=f"Oyuncu: {run.player}  ·  {run.level.name}")
        self.stats["score"].configure(text=str(run.score))
        self.stats["time"].configure(text=format_time(run.elapsed_ms))
        self.stats["food"].configure(text=f"{state.pellets_left} / {len(state.level.pellets)}")
        self.stats["level"].configure(text=f"{run.level_index + 1} / {len(run.levels)}")
        self.stats["ghosts_eaten"].configure(text=str(run.result().ghosts_eaten))
        self.stats["player"].configure(text=run.player)
        self.power_bar.configure(value=state.power_left)
        self.power_text.configure(text=f"{state.power_left} adım" if state.powered else "Yok")
        self._refresh_ghosts(state)

    def _refresh_ghosts(self, state):
        if len(self._ghost_labels) != len(state.ghosts):
            for widget in self.ghost_rows.winfo_children():
                widget.destroy()
            self._ghost_labels = []
            colors = theme.CANVAS_COLORS["ghosts"]
            for index in range(len(state.ghosts)):
                row = ttk.Frame(self.ghost_rows, style="Card.TFrame")
                row.pack(fill="x", pady=(self._px(3), 0))
                tk.Label(row, text="●", foreground=colors[index % len(colors)], background=theme.COLORS["card"],
                         font=theme.font("body"), **theme.tk_options()).pack(side="left")
                label = ttk.Label(row, style="Field.TLabel")
                label.pack(side="left", padx=(self._px(6), 0))
                self._ghost_labels.append(label)
        for index, (ghost, label) in enumerate(zip(state.ghosts, self._ghost_labels)):
            if ghost.frightened:
                mode = "korkmuş, kaçıyor"
            elif index == 0:
                mode = "çekiliyor" if ghosts.is_scattering(state) else "kovalıyor"
            else:
                mode = "geziyor"
            label.configure(text=f"{ghosts.strategy_name(index)} — {mode}")

    def _refresh_ai_panel(self, chosen):
        table = self.ai_table
        table.delete(*table.get_children())
        loss = self.agent.weights.loss
        for evaluation in self.agent.last_evaluations:
            parts = evaluation.parts
            # max(0, ...): yakalanma terimi yokken "-0" yazılmasın.
            risk = max(0.0, -parts.get("yakalanma", 0.0) / loss)
            food = parts.get("yenen yemek", 0.0) + parts.get("yemek mesafesi", 0.0)
            values = (evaluation.direction.label, f"{evaluation.utility:.0f}", f"%{100 * risk:.0f}",
                      f"{food:.0f}", f"{parts.get('tehlike', 0.0):.0f}", f"{parts.get('kaçış alanı', 0.0):.0f}",
                      f"{parts.get('av', 0.0):.0f}")
            tags = ("chosen",) if evaluation.direction is chosen else ()
            table.insert("", "end", values=values, tags=tags)
        self.decision_text.configure(text=f"Seçilen yön: {chosen.label} (beklenen faydası en yüksek)")

    # ------------------------------------------------------------------
    # Kapatma
    # ------------------------------------------------------------------
    def _after(self, delay_ms, callback, *args):
        job = None

        def run():
            if job in self._jobs:
                self._jobs.remove(job)
            callback(*args)
        job = self.root.after(delay_ms, run)
        self._jobs.append(job)

    def destroy(self):
        """Zamanlayıcıları ve klavye bağlantısını kaldırıp ekranı kapatır."""
        self.timer.cancel()
        for job in self._jobs:
            self.root.after_cancel(job)
        self._jobs.clear()
        self.root.unbind("<KeyPress>", self._key_binding)
        self.page.destroy()
