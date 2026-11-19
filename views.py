"""Oyun tahtasının Tkinter Canvas üzerine çizimi.

Çizim üç katmandadır:

* **Sabit katman** (``static``): zemin ve duvarlar. Yalnızca seviye
  değiştiğinde ya da tuval yeniden boyutlandığında çizilir.
* **Yemekler**: her yemek ayrı bir şekildir; yendiğinde yalnızca o şekil
  silinir. Her adımda yüzlerce şekli baştan çizmek gereksiz yere yavaş olurdu.
* **Hareketli katman** (``dynamic``): Pacman ve hayaletler; saniyede ~60
  kez silinip yeniden çizilir.

Akıcı hareket: oyun mantığı kareden kareye, her ``Rules.step_ms``'de bir
adım ilerler. Çizim ise karakterleri bir önceki karelerinden yeni
karelerine doğru ``progress`` (0'dan 1'e) oranında kaydırır (ara kare,
"interpolation"). Mantık değişmez; yalnızca görüntü akıcılaşır.

Bu modül oyun durumunu yalnızca okur, değiştirmez.
"""

import math

import theme
from game import Status
from levels import Direction

C = theme.CANVAS_COLORS

# Pacman'in ağız açısı (derece): her karede bir kez açılıp kapanır.
MOUTH_OPEN, MOUTH_CLOSED = 70, 12
# Tk'de açılar saat 3 yönünden saat yönünün tersine ölçülür.
FACING_ANGLE = {Direction.RIGHT: 0, Direction.UP: 90, Direction.LEFT: 180, Direction.DOWN: 270}
# Enerji etkisinin son bu kadar adımında korkmuş hayaletler yanıp söner.
FLASH_STEPS = 10


class BoardView:
    """Bir ``tk.Canvas`` üzerinde oyun tahtası."""

    def __init__(self, canvas):
        self.canvas = canvas
        self.level = None
        self.cell = 0
        self.origin = (0, 0)
        self._pellet_items = {}         # konum -> tuval şekli
        self._power_items = {}
        self._state = None
        self._overlay = None            # (başlık, alt başlık)
        self._previous = None           # son adımdan önceki konumlar: (pacman, [hayaletler])
        self._progress = 1.0            # son adımın çizimde ne kadarı gösterildi (0..1)
        self._frame = 0
        canvas.configure(background=C["background"], highlightthickness=0)
        canvas.bind("<Configure>", lambda _event: self._relayout())

    # ------------------------------------------------------------------
    # Genel arayüz
    # ------------------------------------------------------------------
    def show(self, state, frame=0, previous=None):
        """Yeni bir oyun adımını çizmeye başlar.

        ``previous`` adımdan önceki konumlardır (``positions(state)`` ile
        alınır); verilirse karakterler oradan kayarak gelir. ``frame`` adım
        sayacıdır (yanıp sönme efektleri için).
        """
        if state.level is not self.level:
            self.level = state.level
            self._state = state
            previous = None             # yeni seviyede kaydırılacak önceki konum yok
            self._relayout()
        self._state = state
        self._frame = frame
        self._previous = previous
        self._progress = 0.0 if previous is not None else 1.0
        self._sync_food(state, frame)
        self._draw_actors(state, frame)
        self._raise_overlay()

    def animate(self, progress):
        """Son adımın ``progress`` (0..1) kadarını çizer; saniyede ~60 kez çağrılır."""
        if self._state is None or self._previous is None:
            return
        progress = min(1.0, max(0.0, progress))
        crossed_middle = self._progress < 0.5 <= progress
        self._progress = progress
        if crossed_middle:              # Pacman karenin ortasına vardı: yemek artık yendi
            self._sync_food(self._state, self._frame)
        self._draw_actors(self._state, self._frame)
        self._raise_overlay()

    def finish_motion(self):
        """Kaydırmayı bitirir; karakterler mantıktaki karelerinde çizilir."""
        self.animate(1.0)

    def overlay(self, title, subtitle=None):
        """Tahtanın üstünde karartılmış bir mesaj gösterir (ör. "Seviye 2", "Yakalandın")."""
        self._overlay = (title, subtitle)
        self._draw_overlay()

    def clear_overlay(self):
        self._overlay = None
        self.canvas.delete("overlay")

    # ------------------------------------------------------------------
    # Yerleşim
    # ------------------------------------------------------------------
    def _relayout(self):
        if self.level is None:
            return
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 10 or height < 10:   # pencere henüz çizilmedi
            return
        self.cell = max(4, min(width // self.level.width, height // self.level.height))
        self.origin = ((width - self.cell * self.level.width) // 2,
                       (height - self.cell * self.level.height) // 2)
        self.canvas.delete("all")
        self._pellet_items.clear()
        self._power_items.clear()
        self._draw_walls()
        if self._state is not None:
            self._sync_food(self._state, 0)
            self._draw_actors(self._state, 0)
        self._draw_overlay()

    def _box(self, position, inset=0.0):
        """Karenin piksel dikdörtgeni; ``inset`` hücre oranı kadar içe çekilir."""
        row, col = position
        x0 = self.origin[0] + col * self.cell
        y0 = self.origin[1] + row * self.cell
        pad = self.cell * inset
        return x0 + pad, y0 + pad, x0 + self.cell - pad, y0 + self.cell - pad

    def _center(self, position):
        x0, y0, x1, y1 = self._box(position)
        return (x0 + x1) / 2, (y0 + y1) / 2

    # ------------------------------------------------------------------
    # Duvarlar
    # ------------------------------------------------------------------
    def _draw_walls(self):
        """Duvar karelerini doldurur ve yalnızca koridora bakan kenarlarını çizer.

        Böylece bitişik duvarlar tek bir blok gibi görünür ve klasik Pacman'deki
        gibi labirentin yalnızca dış hatları parlar.
        """
        canvas, level = self.canvas, self.level
        width = max(2, self.cell // 8)
        for wall in level.walls:
            x0, y0, x1, y1 = self._box(wall)
            canvas.create_rectangle(x0, y0, x1, y1, fill=C["wall_fill"], outline="", tags="static")
        for wall in level.walls:
            x0, y0, x1, y1 = self._box(wall)
            row, col = wall
            edges = {
                (row - 1, col): (x0, y0, x1, y0),
                (row + 1, col): (x0, y1, x1, y1),
                (row, col - 1): (x0, y0, x0, y1),
                (row, col + 1): (x1, y0, x1, y1),
            }
            for neighbour, line in edges.items():
                if self._inside(neighbour) and level.is_open(neighbour):
                    canvas.create_line(*line, fill=C["wall_edge"], width=width, capstyle="round", tags="static")

    def _inside(self, position):
        row, col = position
        return 0 <= row < self.level.height and 0 <= col < self.level.width

    # ------------------------------------------------------------------
    # Yemekler
    # ------------------------------------------------------------------
    def _sync_food(self, state, frame):
        canvas = self.canvas
        # Pacman yeni karesine henüz yarı yoldan az kaydıysa oradaki yemek
        # görüntüde biraz daha durur; yoksa yemek Pacman varmadan kaybolurdu.
        arriving = state.pacman if self._previous is not None and self._progress < 0.5 else None
        for position in list(self._pellet_items):
            if position not in state.pellets and position != arriving:
                canvas.delete(self._pellet_items.pop(position))
        for position in list(self._power_items):
            if position not in state.powers and position != arriving:
                canvas.delete(self._power_items.pop(position))
        for position in state.pellets:
            if position not in self._pellet_items:
                x, y = self._center(position)
                r = max(2.0, self.cell * 0.1)
                self._pellet_items[position] = canvas.create_oval(
                    x - r, y - r, x + r, y + r, fill=C["pellet"], outline="", tags="food")
        for position in state.powers:
            if position not in self._power_items:
                self._power_items[position] = canvas.create_oval(
                    *self._box(position, 0.22), fill=C["power"], outline="", tags="food")
        # Enerji topları dikkat çeksin diye yavaşça yanıp söner.
        visible = "normal" if frame % 6 < 4 else "hidden"
        for item in self._power_items.values():
            canvas.itemconfigure(item, state=visible)

    # ------------------------------------------------------------------
    # Karakterler
    # ------------------------------------------------------------------
    def _draw_actors(self, state, frame):
        self.canvas.delete("dynamic")
        previous_pacman, previous_ghosts = self._previous or (None, [None] * len(state.ghosts))
        for index, ghost in enumerate(state.ghosts):
            before = previous_ghosts[index] if index < len(previous_ghosts) else None
            self._draw_ghost(ghost, index, state, frame, self._slide(before, ghost.position))
        moved = previous_pacman is not None and previous_pacman != state.pacman
        self._draw_pacman(state, self._slide(previous_pacman, state.pacman), moved)

    def _slide(self, before, after):
        """İki kare arasında ``progress`` oranındaki piksel konumu.

        Komşu olmayan karelere geçiş (yenen hayaletin başlangıca dönmesi) kaydırılmaz.
        """
        end = self._center(after)
        if before is None or abs(before[0] - after[0]) + abs(before[1] - after[1]) != 1:
            return end
        start = self._center(before)
        t = self._progress
        return start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t

    def _draw_pacman(self, state, center, moved):
        if state.status is Status.LOST:
            # Yakalanınca ağız tamamen açık, kapanmayan bir "pasta dilimi".
            mouth = 300
        elif moved:
            # Her karede bir kez açılıp kapanır (yarı yolda kapalı).
            mouth = MOUTH_CLOSED + (MOUTH_OPEN - MOUTH_CLOSED) * abs(math.cos(math.pi * self._progress))
        else:
            mouth = (MOUTH_OPEN + MOUTH_CLOSED) / 2
        draw_pacman(self.canvas, *center, self.cell * 0.42, state.direction or Direction.RIGHT, mouth,
                    tags="dynamic")

    def _draw_ghost(self, ghost, index, state, frame, center):
        flashing = ghost.frightened and state.power_left <= FLASH_STEPS and frame % 2 == 1
        # Etek her karede iki kez kıpırdar.
        wave = frame * 2 + (1 if self._progress >= 0.5 else 0)
        draw_ghost(self.canvas, *center, self.cell * 0.42, ghost_color(index), ghost.direction,
                   frightened=ghost.frightened, flashing=flashing, wave=wave, tags="dynamic")

    # ------------------------------------------------------------------
    # Mesaj katmanı
    # ------------------------------------------------------------------
    def _draw_overlay(self):
        canvas = self.canvas
        canvas.delete("overlay")
        if self._overlay is None or self.level is None:
            return
        title, subtitle = self._overlay
        x0, y0 = self.origin
        x1, y1 = x0 + self.cell * self.level.width, y0 + self.cell * self.level.height
        # Tk yarı saydam renk desteklemez; noktalı (stipple) bir örtü karartma etkisi verir.
        canvas.create_rectangle(x0, y0, x1, y1, fill=theme.COLORS["bg"], stipple="gray75", outline="",
                                tags="overlay")
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # Başlık arcade yazı tipiyle; tek karakterlik geri sayım iri yazılır.
        size = "hero" if len(title) <= 2 else "big"
        canvas.create_text(cx, cy - (theme.px(18) if subtitle else 0), text=title, fill=C["overlay_text"],
                           font=theme.display_font(size), tags="overlay")
        if subtitle:
            canvas.create_text(cx, cy + theme.px(30), text=subtitle, fill=theme.COLORS["text"],
                               font=theme.ui_font("lead"), tags="overlay")

    def _raise_overlay(self):
        self.canvas.tag_raise("overlay")


def ghost_color(index):
    colors = C["ghosts"]
    return colors[index % len(colors)]


def draw_pacman(canvas, cx, cy, r, direction=Direction.RIGHT, mouth=MOUTH_OPEN, color=None, tags=()):
    """Pacman: ``direction`` yönüne bakan, ağzı ``mouth`` derece açık bir pasta dilimi."""
    facing = FACING_ANGLE[direction]
    return canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=facing + mouth / 2, extent=360 - mouth,
                             fill=color or C["pacman"], outline="", style="pieslice", tags=tags)


def draw_ghost(canvas, cx, cy, r, body, direction=None, frightened=False, flashing=False, wave=0, tags=()):
    """Hayalet: gövde, gözler (gidiş yönüne bakar); korkmuşsa mavi gövde ve titrek ağız."""
    if frightened:
        body = C["ghost_flash"] if flashing else C["ghost_frightened"]
    canvas.create_polygon(ghost_outline(cx, cy, r, wave), fill=body, outline="", tags=tags)
    if frightened:
        face = C["ghost_pupil"] if flashing else C["ghost_eye"]
        for dx in (-0.3, 0.3):
            ex, ey = cx + dx * r, cy - 0.2 * r
            canvas.create_oval(ex - 0.1 * r, ey - 0.1 * r, ex + 0.1 * r, ey + 0.1 * r,
                               fill=face, outline="", tags=tags)
        points = []
        for i in range(7):
            points += [cx - 0.5 * r + i * r / 6, cy + 0.3 * r + (0.1 * r if i % 2 else -0.1 * r)]
        canvas.create_line(points, fill=face, width=max(1, round(r / 7)), tags=tags)
        return
    d_row, d_col = (direction or Direction.DOWN).value
    for dx in (-0.35, 0.35):
        ex, ey = cx + dx * r, cy - 0.15 * r
        canvas.create_oval(ex - 0.22 * r, ey - 0.26 * r, ex + 0.22 * r, ey + 0.26 * r,
                           fill=C["ghost_eye"], outline="", tags=tags)
        px, py = ex + d_col * 0.1 * r, ey + d_row * 0.12 * r
        canvas.create_oval(px - 0.11 * r, py - 0.11 * r, px + 0.11 * r, py + 0.11 * r,
                           fill=C["ghost_pupil"], outline="", tags=tags)


def positions(state):
    """Kaydırma için bir adımdan önceki konumlar: ``(pacman, [hayaletler])``."""
    return state.pacman, [ghost.position for ghost in state.ghosts]


def ghost_outline(cx, cy, r, frame):
    """Hayalet gövdesi: üstte yarım daire, altta dalgalı etek (etek adım başına kıpırdar)."""
    points = []
    for i in range(13):                         # üst yarım daire (soldan sağa)
        angle = math.pi - math.pi * i / 12
        points += [cx + r * math.cos(angle), cy - r * 0.1 - r * math.sin(angle)]
    bottom = cy + r
    points += [cx + r, bottom]
    waves = 4
    shift = 0.5 if frame % 2 else 0.0
    for i in range(waves * 2, -1, -1):          # etek (sağdan sola)
        x = cx - r + 2 * r * (i / (waves * 2))
        up = (i + shift * 2) % 2 == 1
        points += [x, bottom - (r * 0.25 if up else 0)]
    return points
