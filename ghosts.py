"""Hayalet stratejileri.

Her strateji ``(state, ghost) -> Direction`` biçiminde bir fonksiyondur ve
``game.GameState``'e ``ghost_policy`` olarak verilen fonksiyon tarafından
çağrılır. Bu modül grafik arayüzden bağımsızdır.

Ortak kural: hayalet **geri dönmez** (geldiği yöne dönmesi yasaktır); yalnızca
çıkmaz sokakta, başka yol yokken döner. Bu kural olmasaydı takipçi hayalet
Pacman'in her adımına anında tepki verip iki kare arasında ileri-geri
titreyebilir, rastgele hayalet de koridorda yerinde sayardı. Klasik
Pacman'deki hayaletler de geri dönmez.
"""

from game import DEFAULT_RULES, DEFAULT_SEED, GameState


def _options(state, ghost):
    """Geri dönüş hariç geçerli hareketler; başka yol yoksa geri dönüş."""
    moves = state.level.moves_from(ghost.position)
    if ghost.direction is not None:
        forward = [(d, target) for d, target in moves if d is not ghost.direction.opposite]
        if forward:
            return forward
    return moves


def chase(state, ghost):
    """Takipçi: Pacman'e BFS ile en kısa yolu kısaltan yönü seçer.

    Mesafeler Pacman'in karesinden hesaplanır (tek BFS bütün hayaletlere
    yeter, sonuç ``Level`` önbelleğinde tutulur). Eşit mesafede yön sırası
    ``levels.DIRECTIONS`` sırasıdır; bu yüzden karar her zaman aynıdır.
    """
    distances = state.level.distances_from(state.pacman)
    best = min(_options(state, ghost), key=lambda option: distances.get(option[1], float("inf")))
    return best[0]


def wander(state, ghost):
    """Gezgin: geri dönmeden, geçerli yönlerden birini rastgele seçer.

    Rastgelelik oyunun kendi üretecinden (``state.rng``) gelir. Aynı seed ve
    aynı oyuncu hamleleriyle hayalet her seferinde aynı yolu izler; bu da iki
    oyuncunun aynı koşullarda oynamasını sağlar. Ajanın kopyaladığı durum da
    üretecin kopyasını taşıdığı için ajan, hayaletin bir sonraki adımını
    gerçek oyundakiyle aynı biçimde simüle eder.
    """
    direction, _ = state.rng.choice(_options(state, ghost))
    return direction


def flee(state, ghost):
    """Korkmuş hayalet: Pacman'e BFS mesafesini en çok artıran yönü seçer.

    Diğer stratejilerden farklı olarak **geri dönebilir**. Enerji topu
    yendiği anda hayalet Pacman'e doğru ilerliyor olabilir; geri dönüş yasak
    olsaydı kaçmak yerine bir kare daha Pacman'e yaklaşmak zorunda kalırdı.
    Klasik Pacman'de de hayaletler korktuklarında yön değiştirir. Eşit
    mesafede geri dönmeyen yön tercih edilir ki hayalet ileri-geri titremesin.
    """
    distances = state.level.distances_from(state.pacman)
    reverse = ghost.direction.opposite if ghost.direction else None

    def preference(option):
        direction, target = option
        return -distances.get(target, 0), direction is reverse

    best = min(state.level.moves_from(ghost.position), key=preference)
    return best[0]


# ----------------------------------------------------------------------
# Hayaletlerin oyuna bağlanması
# ----------------------------------------------------------------------
# İlk hayalet takipçi, diğerleri gezgindir. Hepsi takipçi olsaydı aynı yolu
# izleyip tek bir hayalet gibi davranırlardı; hepsi gezgin olsaydı Pacman'i
# hiç kovalamazlardı. Karışım hem baskı hem öngörülemezlik yaratır.
STRATEGY_NAMES = ("Takipçi", "Gezgin")


def strategy_name(index):
    return STRATEGY_NAMES[0] if index == 0 else STRATEGY_NAMES[1]


def policy(state, ghost):
    """``GameState(ghost_policy=...)`` için: her hayaleti sırasına göre yönetir.

    Korkmuş hayalet yarı hızda hareket eder (tek numaralı adımlarda yerinde
    kalır). Aynı hızda kaçan bir hayaleti yakalamak çoğu zaman imkânsız
    olurdu; enerji topunun anlamı kalmazdı.
    """
    if ghost.frightened:
        return None if state.steps % 2 else flee(state, ghost)
    index = next(i for i, other in enumerate(state.ghosts) if other is ghost)
    return chase(state, ghost) if index == 0 else wander(state, ghost)


def new_game(level, rules=DEFAULT_RULES, seed=DEFAULT_SEED):
    """Standart hayaletlerle yeni oyun. İki oyuncu da bu fonksiyonla, aynı
    seviye, kurallar ve seed ile başlatılır."""
    return GameState(level, rules, seed, ghost_policy=policy)
