"""Bir oyuncunun turu: seviyeler arası geçiş ve toplam sonuç.

Bir tur Seviye 1'den başlar. Seviye tamamlanınca bir sonrakine, aynı kurallar
ve aynı seed ile geçilir; puan ve süre birikir. Pacman yakalanırsa ya da son
seviye tamamlanırsa tur biter.

Bu modül grafik arayüzden bağımsızdır.
"""

from dataclasses import dataclass

from game import DEFAULT_RULES, DEFAULT_SEED, Status
from ghosts import new_game
from levels import LEVELS

HUMAN = "İnsan"
AI = "Yapay Zekâ"


@dataclass(frozen=True)
class RunResult:
    """Bir turun sonucu (sonuç ekranında ve kazananı belirlemede kullanılır)."""

    player: str
    completed: bool             # bütün seviyeler tamamlandı mı
    score: int
    elapsed_ms: int             # oyun içi süre (adım × adım süresi)
    steps: int
    levels_completed: int
    level_count: int
    pellets_eaten: int
    ghosts_eaten: int


class Run:
    """Bir oyuncunun bütün seviyeler boyunca oyunu."""

    def __init__(self, player, levels=LEVELS, rules=DEFAULT_RULES, seed=DEFAULT_SEED):
        self.player = player
        self.levels = levels
        self.rules = rules
        self.seed = seed
        self.level_index = 0
        self.state = new_game(levels[0], rules, seed)
        # Tamamlanan seviyelerden biriken değerler.
        self._banked_score = 0
        self._banked_steps = 0
        self._banked_pellets = 0
        self._banked_ghosts = 0

    # ------------------------------------------------------------------
    @property
    def level(self):
        return self.levels[self.level_index]

    @property
    def score(self):
        return self._banked_score + self.state.score

    @property
    def steps(self):
        return self._banked_steps + self.state.steps

    @property
    def elapsed_ms(self):
        return self.steps * self.rules.step_ms

    @property
    def level_won(self):
        return self.state.status is Status.WON

    @property
    def has_next_level(self):
        return self.level_won and self.level_index + 1 < len(self.levels)

    @property
    def is_over(self):
        """Tur bitti mi: yakalandı ya da son seviye tamamlandı."""
        return self.state.status is Status.LOST or (self.level_won and not self.has_next_level)

    @property
    def completed(self):
        return self.is_over and self.state.status is Status.WON

    # ------------------------------------------------------------------
    def next_level(self):
        """Tamamlanan seviyeden sonrakine geçer; bu seviyenin değerleri birikir."""
        if not self.has_next_level:
            raise RuntimeError("Geçilecek seviye yok")
        state = self.state
        self._banked_score += state.score
        self._banked_steps += state.steps
        self._banked_pellets += len(state.level.pellets) - state.pellets_left
        self._banked_ghosts += state.ghosts_eaten
        self.level_index += 1
        self.state = new_game(self.level, self.rules, self.seed)

    def result(self):
        state = self.state
        levels_completed = self.level_index + (1 if self.level_won else 0)
        return RunResult(
            player=self.player,
            completed=self.completed,
            score=self.score,
            elapsed_ms=self.elapsed_ms,
            steps=self.steps,
            levels_completed=levels_completed,
            level_count=len(self.levels),
            pellets_eaten=self._banked_pellets + len(state.level.pellets) - state.pellets_left,
            ghosts_eaten=self._banked_ghosts + state.ghosts_eaten,
        )


# ----------------------------------------------------------------------
# Maç: iki tur ve kazanan
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Verdict:
    """Maçın sonucu. ``winner`` beraberlikte ``None``'dır."""

    winner: RunResult
    loser: RunResult
    criterion: str              # kazananı belirleyen ölçüt (ekranda gösterilir)

    @property
    def is_draw(self):
        return self.winner is None


def decide_winner(first, second):
    """Ödevin sırasıyla kazananı belirler.

    1. Oyunu tamamlama durumu: tamamlayan, tamamlayamayanı yener.
    2. Toplam puan: yüksek olan kazanır.
    3. Süre: eşitlikte daha kısa sürede bitiren kazanır.
    4. Bütün ölçütler eşitse beraberlik.
    """
    if first.completed != second.completed:
        winner, loser = (first, second) if first.completed else (second, first)
        return Verdict(winner, loser, "Oyunu tamamladı")
    if first.score != second.score:
        winner, loser = (first, second) if first.score > second.score else (second, first)
        return Verdict(winner, loser, "Daha yüksek puan")
    if first.elapsed_ms != second.elapsed_ms:
        winner, loser = (first, second) if first.elapsed_ms < second.elapsed_ms else (second, first)
        return Verdict(winner, loser, "Daha kısa süre")
    return Verdict(None, None, "Bütün ölçütler eşit")


class Match:
    """İki oyuncunun sırayla oynadığı maç. Sırayı kullanıcı seçer."""

    def __init__(self, first_player):
        if first_player not in (HUMAN, AI):
            raise ValueError(f"Bilinmeyen oyuncu: {first_player}")
        second_player = AI if first_player == HUMAN else HUMAN
        self.order = (first_player, second_player)
        self.results = []

    @property
    def is_over(self):
        return len(self.results) == len(self.order)

    @property
    def turn(self):
        """Sıradaki turun numarası (1 ya da 2)."""
        return len(self.results) + 1

    @property
    def current_player(self):
        return None if self.is_over else self.order[len(self.results)]

    def new_run(self):
        """Sıradaki oyuncu için sıfırdan bir tur. Her tur aynı seviyeler, kurallar ve seed ile başlar."""
        return Run(self.current_player)

    def record(self, result):
        if self.is_over:
            raise RuntimeError("Maç bitti")
        if result.player != self.current_player:
            raise ValueError(f"Sıra {self.current_player} oyuncusunda")
        self.results.append(result)

    def verdict(self):
        if not self.is_over:
            raise RuntimeError("Maç bitmedi")
        return decide_winner(*self.results)
