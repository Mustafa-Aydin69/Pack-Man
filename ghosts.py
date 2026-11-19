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
