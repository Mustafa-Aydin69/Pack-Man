"""Seviye (level) haritaları: ASCII biçimi, doğrulama ve BFS mesafeleri.

Harita karakterleri:

    #   duvar (geçilemez)
    .   yemek
    o   enerji topu
    P   Pacman'in başlangıç karesi (altında yemek yoktur)
    G   bir hayaletin başlangıç karesi (altında yemek yoktur)
    ' ' boş koridor

Konumlar ``(satır, sütun)`` biçimindedir; ``(0, 0)`` sol üst köşedir.

Bu modül grafik arayüzden bağımsızdır. Harita yüklenirken ödevin "tüm
yemekler erişilebilir olmalıdır" şartı BFS ile denetlenir; şartı sağlamayan
bir harita hiç oluşturulamaz.
"""

from collections import deque
from dataclasses import dataclass, field
from enum import Enum

WALL, PELLET, POWER, PACMAN, GHOST, EMPTY = "#", ".", "o", "P", "G", " "
MIN_GHOSTS = 2


class Direction(Enum):
    """Dört hareket yönü; değer ``(satır farkı, sütun farkı)``."""

    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)

    @property
    def label(self):
        return DIRECTION_LABELS[self]

    @property
    def opposite(self):
        return OPPOSITES[self]

    def apply(self, position):
        row, col = position
        d_row, d_col = self.value
        return row + d_row, col + d_col


# Komşular her zaman bu sırayla gezilir. Sıra sabit olduğu için eşit uzunlukta
# birden fazla yol varsa hep aynısı seçilir; bu da oyunun tekrarlanabilir
# (deterministik) olmasının bir parçasıdır.
DIRECTIONS = (Direction.UP, Direction.LEFT, Direction.DOWN, Direction.RIGHT)
DIRECTION_LABELS = {Direction.UP: "Yukarı", Direction.DOWN: "Aşağı",
                    Direction.LEFT: "Sol", Direction.RIGHT: "Sağ"}
OPPOSITES = {Direction.UP: Direction.DOWN, Direction.DOWN: Direction.UP,
             Direction.LEFT: Direction.RIGHT, Direction.RIGHT: Direction.LEFT}


class LevelError(ValueError):
    """Harita ödevin kurallarını ya da biçimi sağlamıyor."""


@dataclass(frozen=True)
class Level:
    """Değişmez seviye tanımı. Oyun sırasındaki durum ``game.GameState``'tedir.

    İki oyuncu aynı ``Level`` nesnesinden başladığı için harita, başlangıç
    konumları, yemekler ve enerji topları her iki tur için birebir aynıdır.
    """

    name: str
    width: int
    height: int
    walls: frozenset
    pellets: frozenset
    powers: frozenset
    pacman_start: tuple
    ghost_starts: tuple
    # Harita değişmediği için bir kareden BFS sonucu da değişmez; hayaletler ve
    # ajan aynı kareden defalarca mesafe sorduğu için sonuçlar saklanır.
    # Eşitlik ve hash hesabına katılmaz.
    _distance_cache: dict = field(default_factory=dict, compare=False, hash=False, repr=False)

    def distances_from(self, position):
        """``position``'dan bütün erişilebilir karelere BFS mesafesi (önbellekli, salt okunur kullanın)."""
        distances = self._distance_cache.get(position)
        if distances is None:
            distances = bfs_distances(self, position)
            self._distance_cache[position] = distances
        return distances

    def is_open(self, position):
        """Karede duvar yoksa True. Harita kenarı duvarla kapalı olduğu için sınır dışı kare oluşmaz."""
        return position not in self.walls

    def moves_from(self, position):
        """``position``'dan geçerli hareketler: ``[(yön, yeni konum), ...]``."""
        result = []
        for direction in DIRECTIONS:
            target = direction.apply(position)
            if self.is_open(target):
                result.append((direction, target))
        return result


def bfs_distances(level, start):
    """``start``'tan her erişilebilir kareye en kısa adım sayısı: ``{konum: mesafe}``.

    Labirentte iki kare arasındaki gerçek mesafe duvarlar yüzünden Manhattan
    mesafesinden uzun olabilir; ajan ve hayaletler bu yüzden BFS kullanır.
    """
    distances = {start: 0}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for _, target in level.moves_from(current):
            if target not in distances:
                distances[target] = distances[current] + 1
                queue.append(target)
    return distances


def parse_level(name, text):
    """ASCII haritayı ``Level``'a çevirir; kurallara uymayan haritada ``LevelError`` fırlatır."""
    rows = [line for line in text.strip("\n").splitlines()]
    if not rows:
        raise LevelError(f"{name}: harita boş")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise LevelError(f"{name}: bütün satırlar aynı uzunlukta olmalı")

    walls, pellets, powers, ghosts, pacman = set(), set(), set(), [], []
    for r, row in enumerate(rows):
        for c, char in enumerate(row):
            position = (r, c)
            if char == WALL:
                walls.add(position)
            elif char == PELLET:
                pellets.add(position)
            elif char == POWER:
                powers.add(position)
            elif char == PACMAN:
                pacman.append(position)
            elif char == GHOST:
                ghosts.append(position)
            elif char != EMPTY:
                raise LevelError(f"{name}: bilinmeyen karakter {char!r} ({r}, {c})")

    height = len(rows)
    border = [(r, c) for r in range(height) for c in range(width)
              if r in (0, height - 1) or c in (0, width - 1)]
    if any(position not in walls for position in border):
        raise LevelError(f"{name}: haritanın kenarı tamamen duvar olmalı")
    if len(pacman) != 1:
        raise LevelError(f"{name}: tam olarak bir Pacman başlangıcı (P) olmalı")
    if len(ghosts) < MIN_GHOSTS:
        raise LevelError(f"{name}: en az {MIN_GHOSTS} hayalet (G) olmalı")
    if not pellets:
        raise LevelError(f"{name}: en az bir yemek olmalı")

    level = Level(name, width, height, frozenset(walls), frozenset(pellets), frozenset(powers),
                  pacman[0], tuple(ghosts))
    reachable = bfs_distances(level, level.pacman_start)
    unreachable = sorted((pellets | powers | set(ghosts)) - reachable.keys())
    if unreachable:
        raise LevelError(f"{name}: Pacman'in ulaşamadığı kareler var: {unreachable}")
    return level


# ----------------------------------------------------------------------
# Hazır seviyeler
# ----------------------------------------------------------------------
# Seviye 1: 2 hayalet, geniş ve çoğunlukla döngülü koridorlar; yalnızca iki
# kısa çıkmaz var. Hayaletler Pacman'den 15–16 adım uzakta başlar.
LEVEL_1 = """
###################
#o.......#.......o#
#.##.###.#.###.##.#
#.......GG........#
#.##.#.#####.#.##.#
#....#...#...#....#
####.###.#.###.####
#....#.......#....#
##.#.#.#####.#.#.##
#..#.....P.....#..#
#.##.###.#.###.##.#
#o.......#.......o#
###################
"""

# Seviye 2: 3 hayalet, daha büyük ve daha sık duvarlı harita. Dört çıkmaz
# sokak (kaçış yolu olmayan koridor) var ve iki hayalet Pacman'e 9 adım
# yakınlıkta başlar; bu yüzden Seviye 1'den zordur.
LEVEL_2 = """
#####################
#o.....#.....#.....o#
#.###.##.###.##.###.#
#.#.......G.......#.#
#.#.###.#####.###.#.#
#...#.....#.....#...#
###.#.###.#.###.#.###
#.....#..G.G..#.....#
#.###.#.#####.#.###.#
#...#...........#...#
###.#.##.###.##.#.###
#.....#...P...#.....#
#.###.#.#####.#.###.#
#o........#........o#
#####################
"""

LEVELS = (parse_level("Seviye 1", LEVEL_1), parse_level("Seviye 2", LEVEL_2))
