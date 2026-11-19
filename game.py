"""Oyun çekirdeği: kurallar, oyun durumu ve bir oyun adımı (tick).

Bu modül grafik arayüzden bağımsızdır. Aynı ``GameState`` sınıfı hem ekranda
oynanan oyunu hem de yapay zekânın kafasında denediği hamleleri temsil eder:
ajan durumu ``clone()`` ile kopyalar, kopyada bir hamle oynatır ve sonucu
değerlendirir. Gerçek oyun bu sırada değişmez.

Zaman adım (tick) ile ölçülür: her ``step()`` çağrısı oyun içinde
``Rules.step_ms`` milisaniye geçmesi demektir. Süre duvar saatiyle değil
adımla ölçüldüğü için duraklatma süreye eklenmez ve insanla yapay zekâ aynı
ölçüyle karşılaştırılır.
"""

import random
from dataclasses import dataclass
from enum import Enum

from levels import Direction


@dataclass(frozen=True)
class Rules:
    """Puan değerleri ve süreler. İki oyuncu aynı ``Rules`` nesnesiyle oynar.

    Ödev puan değerlerini geliştiriciye bırakır; seçilen değerlerin gerekçesi:

    * ``move_cost`` (-1): Her hareket puan kaybettirir; böylece aynı yemekleri
      daha kısa yoldan toplayan oyuncu daha yüksek puan alır.
    * ``pellet`` (+10): Bir yemek 10 hareketin maliyetini karşılar; yemeğe
      giden makul her yol kârlıdır.
    * ``power`` (+50): Enerji topu az sayıdadır ve hayalet avlamayı açar.
    * ``ghost`` (+200): Enerji etkisindeyken hayalete yaklaşmak risklidir
      (etki bitebilir); yüksek ödül bu riski karşılar.
    * ``power_duration`` (40 adım): Haritanın yarısını geçmeye yetecek kadar
      uzun, hayaletleri haritanın her yerinde kovalamaya yetmeyecek kadar kısa.
    * ``step_ms`` (150 ms): İnsanın tepki verebileceği bir hız.
    """

    move_cost: int = -1
    pellet: int = 10
    power: int = 50
    ghost: int = 200
    power_duration: int = 40
    step_ms: int = 150


DEFAULT_RULES = Rules()


class Status(Enum):
    PLAYING = "Oynanıyor"
    WON = "Tamamlandı"
    LOST = "Yakalandı"


@dataclass
class Ghost:
    """Bir hayaletin değişen durumu."""

    position: tuple
    start: tuple
    direction: Direction = None     # son hareket yönü (henüz hareket etmediyse None)
    frightened: bool = False        # enerji etkisinde mi (yenebilir ve kaçar)

    def copy(self):
        return Ghost(self.position, self.start, self.direction, self.frightened)


@dataclass
class StepResult:
    """Bir adımda olanlar; arayüz bunları HUD ve bildirimler için kullanır."""

    moved: bool = False


class GameState:
    """Tek bir seviyenin oyun durumu."""

    def __init__(self, level, rules=DEFAULT_RULES, seed=0):
        self.level = level
        self.rules = rules
        self.pacman = level.pacman_start
        self.direction = None           # Pacman'in son hareket yönü
        self.pellets = set(level.pellets)
        self.powers = set(level.powers)
        self.ghosts = [Ghost(start, start) for start in level.ghost_starts]
        self.score = 0
        self.steps = 0
        self.status = Status.PLAYING
        # Hayaletlerin rastgele kararları bu üreteçten gelir. Seed aynı olduğu
        # sürece iki oyuncu aynı rastgele dizilerle karşılaşır.
        self.rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Sorgular
    # ------------------------------------------------------------------
    @property
    def elapsed_ms(self):
        return self.steps * self.rules.step_ms

    @property
    def is_over(self):
        return self.status is not Status.PLAYING

    def legal_directions(self):
        """Pacman'in bulunduğu kareden geçerli yönler (duvara doğru olanlar hariç)."""
        return [direction for direction, _ in self.level.moves_from(self.pacman)]

    # ------------------------------------------------------------------
    # Adım
    # ------------------------------------------------------------------
    def step(self, requested=None):
        """Oyunu bir adım ilerletir.

        ``requested`` oyuncunun istediği yöndür. O yön duvara çıkıyorsa Pacman
        son yönünde ilerlemeye devam eder (klasik Pacman'deki gibi dönüş tuşu
        önceden basılabilir); o da kapalıysa yerinde durur. Yerinde durmak
        hareket sayılmaz ve puan kaybettirmez, ama süre işler.
        """
        result = StepResult()
        if self.is_over:
            return result
        self._move_pacman(requested, result)
        self.steps += 1
        return result

    def _move_pacman(self, requested, result):
        for direction in (requested, self.direction):
            if direction is None:
                continue
            target = direction.apply(self.pacman)
            if self.level.is_open(target):
                self.pacman = target
                self.direction = direction
                self.score += self.rules.move_cost
                result.moved = True
                return

    # ------------------------------------------------------------------
    # Kopyalama
    # ------------------------------------------------------------------
    def clone(self):
        """Bağımsız kopya. Ajan hamleleri kopyada dener; asıl oyun değişmez.

        ``copy.deepcopy`` yerine elle kopyalanır: değişmez ``Level`` ve
        ``Rules`` paylaşılır, yalnızca değişen alanlar kopyalanır. Ajan her
        adımda birçok kopya ürettiği için bu belirgin biçimde daha hızlıdır.
        """
        other = GameState.__new__(GameState)
        other.__dict__.update(self.__dict__)
        other.pellets = set(self.pellets)
        other.powers = set(self.powers)
        other.ghosts = [ghost.copy() for ghost in self.ghosts]
        other.rng = random.Random()
        other.rng.setstate(self.rng.getstate())
        return other
