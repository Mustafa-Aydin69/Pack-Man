"""Oyun ekranı: skor şeridi, tahta, karar paneli ve oyun döngüsü.

Ekran bir ``match.Run``'ı (bir oyuncunun turu) oynatır. Oyuncu insansa yön
klavyeden gelir; yapay zekâysa her adımda ``UtilityAgent.choose`` çağrılır.
Kurallar ve zamanlama iki oyuncu için birebir aynıdır: oyun her
``Rules.step_ms`` milisaniyede bir adım ilerler.

Yerleşim arcade makinesini izler: skor ve süre üst şeritte, labirent ekranın
hâkimi, ayrıntılar alt şeritte. Sağdaki panel yapay zekâ oynarken "AI
pusulasını" (her yönün beklenen faydası), insan oynarken basılan yönü
gösteren tuş şemasını içerir.

Akış: geri sayım (3-2-1) → oyun → seviye bitince geçiş mesajı ve sonraki
seviyenin geri sayımı → tur bitince sonuç mesajı → ``on_finish(RunResult)``.
"""

import tkinter as tk

import ghosts
import theme
from levels import Direction
from match import AI
from timers import PausableTimer
from views import BoardView, draw_ghost, draw_pacman, ghost_color, positions
from widgets import ArcadeButton, Compass, KeyPad, Meter

COLORS = theme.COLORS
KEY_DIRECTIONS = {
    "Up": Direction.UP, "Down": Direction.DOWN, "Left": Direction.LEFT, "Right": Direction.RIGHT,
    "w": Direction.UP, "s": Direction.DOWN, "a": Direction.LEFT, "d": Direction.RIGHT,
}
COUNTDOWN_MS = 600          # geri sayımın her rakamı
LEVEL_MESSAGE_MS = 1600     # "Seviye tamamlandı" mesajının süresi
FINISH_MESSAGE_MS = 2200    # tur sonu mesajının süresi
# Çizim aralığı (~60 kare/sn). Oyun mantığı Rules.step_ms'de bir ilerler;
# aradaki karelerde karakterler kayarak çizilir.
ANIMATION_MS = 16
PANEL_WIDTH = 300

# Karar panelinde gösterilen fayda bileşenleri: (gösterilen ad, ajanın bileşen adları).
DECISION_PARTS = (
    ("Yemek", ("yenen yemek", "yemek mesafesi")),
    ("Puan", ("puan",)),
    ("Hayalet tehlikesi", ("tehlike",)),
    ("Kaçış alanı", ("kaçış alanı",)),
    ("Hayalet avı", ("av",)),
)


def format_time(ms):
    """Oyun içi süre: ``dd:ss.d``."""
    seconds, tenths = divmod(int(ms) // 100, 10)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{seconds:02d}.{tenths}"


def player_color(player):
    return COLORS["ai"] if player == AI else COLORS["human"]


def player_sprite(canvas, cx, cy, r, player):
    """Oyuncunun simgesi: insan Pacman, yapay zekâ turkuaz hayalet."""
    if player == AI:
        draw_ghost(canvas, cx, cy, r, COLORS["ai"], Direction.LEFT)
    else:
        draw_pacman(canvas, cx, cy, r, Direction.RIGHT, mouth=60)


def label(parent, text="", size="body", color="text", background="bg", bold=False, **options):
    return tk.Label(parent, text=text, font=theme.ui_font(size, "bold") if bold else theme.ui_font(size),
                    foreground=COLORS.get(color, color), background=COLORS.get(background, background), **options)


def number(parent, text="", size="number", color="text", background="bg", **options):
    """Piksel yazı tipinde sayı (skor, süre)."""
    return tk.Label(parent, text=text, font=theme.display_font(size), foreground=COLORS.get(color, color),
                    background=COLORS.get(background, background), **options)


class GameScreen:
    """Bir oyuncunun turunu oynatan ekran."""

    def __init__(self, root, scale, run, agent=None, on_finish=None, on_home=None, turn=None):
        self.root = root
        self.scale = scale
        self.run = run
        self.agent = agent                  # None: insan oyuncu
        self.on_finish = on_finish
        self.on_home = on_home
        self.turn = turn                    # maçtaki tur numarası (1 ya da 2), bilinmiyorsa None
        self.requested = None               # insan oyuncunun son bastığı yön
        self.frame = 0                      # adım sayacı (yanıp sönme efektleri)
        self.phase = "countdown"            # countdown | playing | paused | message | finished
        self._jobs = []                     # bekleyen root.after işleri (kapatılırken iptal edilir)
        self._animation_job = None
        self.timer = PausableTimer(root, self._tick)

        pad = theme.px(20)
        self.page = tk.Frame(root, background=COLORS["bg"], padx=pad, pady=theme.px(14))
        self.page.pack(fill="both", expand=True)
        self.page.columnconfigure(0, weight=1)
        self.page.rowconfigure(1, weight=1)
        self._build_score_strip()
        self._build_body()
        self._build_bottom_strip()
        self._key_binding = root.bind("<KeyPress>", self._on_key, add="+")
        # Klavye olayları odaktaki pencereye gelir; ekran açılır açılmaz oyuna gitsin.
        root.focus_force()

        self.board.show(run.state, self.frame)
        self._refresh_hud()
        self._after(50, self._countdown, 3)
        self._animate()

    @property
    def is_ai(self):
        return self.agent is not None

    # ------------------------------------------------------------------
    # Yerleşim
    # ------------------------------------------------------------------
    def _build_score_strip(self):
        """Üst şerit: oyuncu, skor, süre, seviye (arcade makinesindeki skor satırı gibi)."""
        strip = tk.Frame(self.page, background=COLORS["bg"])
        strip.grid(row=0, column=0, sticky="ew", pady=(0, theme.px(12)))
        strip.columnconfigure(1, weight=1)
        color = player_color(self.run.player)

        who = tk.Frame(strip, background=COLORS["bg"])
        who.grid(row=0, column=0, sticky="w")
        icon = tk.Canvas(who, width=theme.px(40), height=theme.px(40), background=COLORS["bg"], highlightthickness=0)
        player_sprite(icon, theme.px(20), theme.px(20), theme.px(16), self.run.player)
        icon.pack(side="left", padx=(0, theme.px(12)))
        names = tk.Frame(who, background=COLORS["bg"])
        names.pack(side="left")
        label(names, self.run.player, "heading", color, bold=True).pack(anchor="w")
        caption = f"{self.turn}. tur" if self.turn else "Tek tur"
        self.level_caption = label(names, caption, "caption", "muted")
        self.level_caption.pack(anchor="w")

        self.stats = {}
        for column, (key, caption, tint) in enumerate(
                (("score", "Skor", color), ("time", "Süre", "text"), ("level", "Seviye", "text")), start=2):
            block = tk.Frame(strip, background=COLORS["bg"])
            block.grid(row=0, column=column, sticky="e", padx=(theme.px(36), 0))
            label(block, caption, "caption", "muted").pack(anchor="e")
            value = number(block, "0", "big" if key == "score" else "number", tint)
            value.pack(anchor="e", pady=(theme.px(4), 0))
            self.stats[key] = value

    def _build_body(self):
        body = tk.Frame(self.page, background=COLORS["bg"])
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        # Labirent çerçevesizdir: dış duvarların parlayan kenarı sınırı zaten çizer.
        canvas = tk.Canvas(body, width=theme.px(560), height=theme.px(420), highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        self.board = BoardView(canvas)

        self.panel = tk.Frame(body, background=COLORS["surface"], width=theme.px(PANEL_WIDTH),
                              padx=theme.px(18), pady=theme.px(16))
        self.panel.grid(row=0, column=1, sticky="ns", padx=(theme.px(16), 0))
        self.panel.grid_propagate(False)
        self.panel.columnconfigure(0, weight=1)
        if self.is_ai:
            self._build_decision_panel(self.panel)
        else:
            self._build_controls_panel(self.panel)

    def _build_decision_panel(self, panel):
        label(panel, "Yapay zekânın kararı", "lead", background="surface", bold=True).grid(row=0, column=0, sticky="w")
        label(panel, "Ok uzunluğu: o yönün beklenen faydası", "caption", "muted", "surface").grid(
            row=1, column=0, sticky="w")
        self.compass = Compass(panel, theme.px(250), COLORS["surface"])
        self.compass.grid(row=2, column=0, pady=(theme.px(8), theme.px(4)))
        self.decision_text = label(panel, "", "body", "ai", "surface", bold=True)
        self.decision_text.grid(row=3, column=0, sticky="w")
        parts = tk.Frame(panel, background=COLORS["surface"])
        parts.grid(row=4, column=0, sticky="ew", pady=(theme.px(8), 0))
        parts.columnconfigure(0, weight=1)
        self.part_values = {}
        rows = [name for name, _ in DECISION_PARTS] + ["Yakalanma riski"]
        for row, name in enumerate(rows):
            label(parts, name, "body", "muted", "surface").grid(row=row, column=0, sticky="w", pady=theme.px(1))
            value = number(parts, "–", "small", "text", "surface")
            value.grid(row=row, column=1, sticky="e")
            self.part_values[name] = value
        label(panel, "Değerler seçilen yönün bu adımdaki olası sonuçlarının ortalamasıdır; karar 2 adım "
                     "ileri bakılarak verilir.", "caption", "muted", "surface",
              wraplength=theme.px(PANEL_WIDTH - 40), justify="left").grid(row=5, column=0, sticky="w",
                                                                         pady=(theme.px(12), 0))

    def _build_controls_panel(self, panel):
        label(panel, "Kontroller", "lead", background="surface", bold=True).grid(row=0, column=0, sticky="w")
        self.keypad = KeyPad(panel, theme.px(56), COLORS["surface"])
        self.keypad.grid(row=1, column=0, pady=(theme.px(16), theme.px(14)))
        label(panel, "Ok tuşları ya da W A S D ile yön verirsin. Pacman o yönde ilerlemeye devam eder; "
                     "dönüşe kavşaktan önce basabilirsin, ilk uygun yerde döner.", "body", "muted", "surface",
              wraplength=theme.px(PANEL_WIDTH - 40), justify="left").grid(row=2, column=0, sticky="w")
        label(panel, "Boşluk: duraklat ve devam et", "body", "text", "surface").grid(
            row=3, column=0, sticky="w", pady=(theme.px(12), 0))

    def _build_bottom_strip(self):
        """Alt şerit: kalan yemek, enerji, hayaletlerin durumu ve düğmeler."""
        strip = tk.Frame(self.page, background=COLORS["bg"])
        strip.grid(row=2, column=0, sticky="ew", pady=(theme.px(12), 0))
        strip.columnconfigure(3, weight=1)

        food = tk.Frame(strip, background=COLORS["bg"])
        food.grid(row=0, column=0, sticky="w")
        label(food, "Kalan yemek", "caption", "muted").pack(anchor="w")
        self.stats["food"] = number(food, "", "number")
        self.stats["food"].pack(anchor="w", pady=(theme.px(4), 0))

        power = tk.Frame(strip, background=COLORS["bg"])
        power.grid(row=0, column=1, sticky="w", padx=(theme.px(32), 0))
        self.power_caption = label(power, "Enerji etkisi yok", "caption", "muted")
        self.power_caption.pack(anchor="w")
        self.power_meter = Meter(power, theme.px(150), theme.px(10), COLORS["human"], COLORS["bg"])
        self.power_meter.pack(anchor="w", pady=(theme.px(8), 0))

        self.ghost_strip = tk.Frame(strip, background=COLORS["bg"])
        self.ghost_strip.grid(row=0, column=2, sticky="w", padx=(theme.px(32), 0))
        self._ghost_labels = []

        buttons = tk.Frame(strip, background=COLORS["bg"])
        buttons.grid(row=0, column=4, sticky="e")
        self.pause_button = ArcadeButton(buttons, "Duraklat", self.toggle_pause)
        self.pause_button.pack(side="left", padx=(0, theme.px(8)))
        ArcadeButton(buttons, "Ana menü", self._go_home).pack(side="left")

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
        before = positions(state)
        state.step(direction)
        self.frame += 1
        self.board.show(state, self.frame, previous=before)
        self._refresh_hud()
        if self.is_ai:
            self._refresh_decision(direction)
        if self.run.has_next_level:
            self._show_message("Seviye tamam", f"Sıradaki: {self.run.levels[self.run.level_index + 1].name}")
            self._after(LEVEL_MESSAGE_MS, self._start_next_level)
        elif self.run.is_over:
            if self.run.completed:
                self._show_message("Tebrikler", f"Bütün seviyeler tamamlandı, {self.run.score} puan")
            else:
                self._show_message("Yakalandın", f"{self.run.score} puan")
            self._after(FINISH_MESSAGE_MS, self._finish)
        else:
            self.timer.start(self.run.rules.step_ms)

    def _animate(self):
        """Saniyede ~60 kez: son adımı zamanlayıcının ilerlemesine göre kaydırarak çizer.

        İlerleme, bir sonraki adıma kalan süreden hesaplanır. Duraklatınca
        zamanlayıcının kalan süresi donduğu için görüntü de olduğu yerde durur.
        """
        self._animation_job = self.root.after(ANIMATION_MS, self._animate)
        if self.phase == "playing" and self.timer.is_pending:
            step_ms = self.run.rules.step_ms
            self.board.animate(1.0 - self.timer.remaining_ms / step_ms)

    def _show_message(self, title, subtitle):
        self.phase = "message"
        self.board.finish_motion()
        self.board.overlay(title, subtitle)
        self.pause_button.set_enabled(False)

    def _start_next_level(self):
        self.run.next_level()
        self.requested = None
        self.frame = 0
        self.pause_button.set_enabled(True)
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
            return "break"              # odaktaki düğme Boşluk'u ayrıca işlemesin
        if not self.is_ai and key in KEY_DIRECTIONS and self.phase in ("countdown", "playing"):
            # Geri sayım sırasında basılan yön de saklanır: oyun başlar başlamaz uygulanır.
            self.requested = KEY_DIRECTIONS[key]
            self.keypad.show(self.requested)
        return None

    def toggle_pause(self):
        if self.phase == "playing":
            self.timer.pause()
            self.phase = "paused"
            self.board.overlay("Durdu", "Devam etmek için Boşluk")
            self.pause_button.configure(text="Devam et")
        elif self.phase == "paused":
            self.board.clear_overlay()
            self.phase = "playing"
            self.pause_button.configure(text="Duraklat")
            self.timer.resume()

    def _go_home(self):
        if self.on_home is not None:
            self.on_home()

    # ------------------------------------------------------------------
    # Gösterge paneli
    # ------------------------------------------------------------------
    def _refresh_hud(self):
        run, state = self.run, self.run.state
        self.stats["score"].configure(text=f"{run.score:05d}" if run.score >= 0 else str(run.score))
        self.stats["time"].configure(text=format_time(run.elapsed_ms))
        self.stats["level"].configure(text=f"{run.level_index + 1}/{len(run.levels)}")
        self.stats["food"].configure(text=f"{state.pellets_left}/{len(state.level.pellets)}")
        duration = run.rules.power_duration
        self.power_meter.set(state.power_left / duration)
        self.power_caption.configure(
            text=f"Enerji etkisi: {state.power_left} adım" if state.powered else "Enerji etkisi yok",
            foreground=COLORS["human"] if state.powered else COLORS["muted"])
        self._refresh_ghosts(state)

    def _refresh_ghosts(self, state):
        if len(self._ghost_labels) != len(state.ghosts):
            for widget in self.ghost_strip.winfo_children():
                widget.destroy()
            self._ghost_labels = []
            for index in range(len(state.ghosts)):
                item = tk.Frame(self.ghost_strip, background=COLORS["bg"])
                item.pack(side="left", padx=(0 if index == 0 else theme.px(18), 0))
                icon = tk.Canvas(item, width=theme.px(22), height=theme.px(22), background=COLORS["bg"],
                                 highlightthickness=0)
                icon.pack(side="left", padx=(0, theme.px(6)))
                text = tk.Frame(item, background=COLORS["bg"])
                text.pack(side="left")
                label(text, ghosts.strategy_name(index), "caption", "muted").pack(anchor="w")
                mode = label(text, "", "body")
                mode.pack(anchor="w")
                self._ghost_labels.append((icon, mode))
        for index, (ghost, (icon, mode)) in enumerate(zip(state.ghosts, self._ghost_labels)):
            if ghost.frightened:
                text, color = "kaçıyor", COLORS["muted"]
            elif index == 0 and ghosts.is_scattering(state):
                text, color = "çekiliyor", COLORS["text"]
            elif index == 0:
                text, color = "kovalıyor", COLORS["danger"]
            else:
                text, color = "geziyor", COLORS["text"]
            mode.configure(text=text, foreground=color)
            icon.delete("all")
            draw_ghost(icon, theme.px(11), theme.px(11), theme.px(9), ghost_color(index), Direction.LEFT,
                       frightened=ghost.frightened)

    def _refresh_decision(self, chosen):
        evaluations = self.agent.last_evaluations
        loss = self.agent.weights.loss
        # max(0, ...): yakalanma terimi yokken "-0" yazılmasın.
        risks = {e.direction: max(0.0, -e.parts.get("yakalanma", 0.0) / loss) for e in evaluations}
        self.compass.show(evaluations, chosen, risks)
        self.decision_text.configure(text=f"Seçilen yön: {chosen.label}")
        parts = next(e.parts for e in evaluations if e.direction is chosen)
        for name, keys in DECISION_PARTS:
            value = sum(parts.get(key, 0.0) for key in keys)
            shown = round(value)
            self.part_values[name].configure(
                text=f"{shown:+d}" if shown else "0",
                foreground=COLORS["ai"] if shown > 0 else COLORS["danger"] if shown < 0 else COLORS["muted"])
        risk = risks[chosen]
        self.part_values["Yakalanma riski"].configure(
            text=f"%{100 * risk:.0f}", foreground=COLORS["danger"] if risk >= Compass.RISKY else COLORS["muted"])

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
        if self._animation_job is not None:
            self.root.after_cancel(self._animation_job)
            self._animation_job = None
        for job in self._jobs:
            self.root.after_cancel(job)
        self._jobs.clear()
        self.root.unbind("<KeyPress>", self._key_binding)
        self.page.destroy()
