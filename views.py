"""Oyun tahtasının Tkinter Canvas üzerine çizimi.

Çizim üç katmandadır:

* **Sabit katman** (``static``): zemin ve duvarlar. Yalnızca seviye
  değiştiğinde ya da tuval yeniden boyutlandığında çizilir.
* **Yemekler**: her yemek ayrı bir şekildir; yendiğinde yalnızca o şekil
  silinir. Her adımda yüzlerce şekli baştan çizmek gereksiz yere yavaş olurdu.
* **Hareketli katman** (``dynamic``): Pacman ve hayaletler; her adımda
  silinip yeniden çizilir.

Bu modül oyun durumunu yalnızca okur, değiştirmez.
"""

import math

import theme
from game import Status
from levels import Direction

C = theme.CANVAS_COLORS

# Pacman'in ağız açısı (derece): adım başına açık / kapalı arasında geçer.
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
        canvas.configure(background=C["background"], highlightthickness=0)
        canvas.bind("<Configure>", lambda _event: self._relayout())

    # ------------------------------------------------------------------
    # Genel arayüz
    # ------------------------------------------------------------------
    def show(self, state, frame=0):
        """``state``'i çizer. ``frame`` animasyon sayacıdır (ağız, yanıp sönme)."""
        if state.level is not self.level:
            self.level = state.level
            self._state = state
            self._relayout()
        self._state = state
        self._sync_food(state, frame)
        self._draw_actors(state, frame)
        self._raise_overlay()

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
        for position in list(self._pellet_items):
            if position not in state.pellets:
                canvas.delete(self._pellet_items.pop(position))
        for position in list(self._power_items):
            if position not in state.powers:
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
        for index, ghost in enumerate(state.ghosts):
            self._draw_ghost(ghost, index, state, frame)
        self._draw_pacman(state, frame)

    def _draw_pacman(self, state, frame):
        x0, y0, x1, y1 = self._box(state.pacman, 0.08)
        if state.status is Status.LOST:
            # Yakalanınca ağız tamamen açık, kapanmayan bir "pasta dilimi".
            mouth = 300
        else:
            mouth = MOUTH_OPEN if frame % 2 == 0 else MOUTH_CLOSED
        facing = FACING_ANGLE[state.direction or Direction.RIGHT]
        self.canvas.create_arc(x0, y0, x1, y1, start=facing + mouth / 2, extent=360 - mouth,
                               fill=C["pacman"], outline="", style="pieslice", tags="dynamic")

    def _draw_ghost(self, ghost, index, state, frame):
        canvas = self.canvas
        cx, cy = self._center(ghost.position)
        r = self.cell * 0.42
        if ghost.frightened:
            flashing = state.power_left <= FLASH_STEPS and frame % 2 == 1
            body = C["ghost_flash"] if flashing else C["ghost_frightened"]
        else:
            colors = C["ghosts"]
            body = colors[index % len(colors)]
        canvas.create_polygon(_ghost_outline(cx, cy, r, frame), fill=body, outline="", tags="dynamic")

        if ghost.frightened:
            # Korkmuş yüz: küçük gözler ve titrek ağız.
            face = C["ghost_pupil"] if body == C["ghost_flash"] else C["ghost_eye"]
            for dx in (-0.3, 0.3):
                ex, ey = cx + dx * r, cy - 0.2 * r
                canvas.create_oval(ex - 0.1 * r, ey - 0.1 * r, ex + 0.1 * r, ey + 0.1 * r,
                                   fill=face, outline="", tags="dynamic")
            points = []
            for i in range(7):
                points += [cx - 0.5 * r + i * r / 6, cy + 0.3 * r + (0.1 * r if i % 2 else -0.1 * r)]
            canvas.create_line(points, fill=face, width=max(1, self.cell // 16), tags="dynamic")
            return

        # Normal yüz: gözbebekleri hareket yönüne bakar.
        d_row, d_col = (ghost.direction or Direction.DOWN).value
        for dx in (-0.35, 0.35):
            ex, ey = cx + dx * r, cy - 0.15 * r
            canvas.create_oval(ex - 0.22 * r, ey - 0.26 * r, ex + 0.22 * r, ey + 0.26 * r,
                               fill=C["ghost_eye"], outline="", tags="dynamic")
            px, py = ex + d_col * 0.1 * r, ey + d_row * 0.12 * r
            canvas.create_oval(px - 0.11 * r, py - 0.11 * r, px + 0.11 * r, py + 0.11 * r,
                               fill=C["ghost_pupil"], outline="", tags="dynamic")

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
        canvas.create_rectangle(x0, y0, x1, y1, fill="#000000", stipple="gray50", outline="", tags="overlay")
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        size = max(14, self.cell)
        canvas.create_text(cx, cy - (size * 0.5 if subtitle else 0), text=title, fill=C["overlay_text"],
                           font=(theme.FONT_FAMILY, size, "bold"), tags="overlay")
        if subtitle:
            canvas.create_text(cx, cy + size * 0.6, text=subtitle, fill=C["overlay_text"],
                               font=(theme.FONT_FAMILY, max(10, size // 2)), tags="overlay")

    def _raise_overlay(self):
        self.canvas.tag_raise("overlay")


def _ghost_outline(cx, cy, r, frame):
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
