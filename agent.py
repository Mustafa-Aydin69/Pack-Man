"""Fayda tabanlı rasyonel ajan (utility-based rational agent).

Ajan her adımda **beklenen faydayı en büyükleyen** (maximum expected
utility) yönü seçer:

1. Pacman'in bulunduğu kareden geçerli her yön için oyun durumunu kopyalar
   (``GameState.clone``) ve hamleyi kopyada oynatır. Gerçek oyun değişmez.
2. Hayaletlerin o adımdaki **olası her cevabını**, olasılığıyla birlikte
   ayrı bir kopyada oynatır (aşağıya bakın).
3. Her sonucu **fayda fonksiyonu** ile puanlar ve olasılıklarla ağırlıklı
   ortalamasını alır: ``EU(yön) = toplam[ P(sonuç) * U(sonuç) ]``.
4. Bunu ``depth`` adım ileriye kadar sürdürür (expectimax: Pacman'in
   sırasında en iyi yön, hayaletlerin sırasında olasılık ağırlıklı ortalama)
   ve beklenen faydası en yüksek yönü seçer.

Ajanın bildikleri ve bilmedikleri
---------------------------------
Ajan oyunun kurallarını bilir: haritayı, yemekleri, puan değerlerini, enerji
süresini ve hayaletlerin davranış kurallarını:

* **Takipçi** (ilk hayalet) Pacman'e en kısa yolu izler; kuralı
  deterministiktir, cevabı olasılık 1 ile bilinir.
* **Gezgin** hayaletler geri dönmeden geçerli yönlerden birini rastgele
  seçer; her yön ``1 / seçenek sayısı`` olasılıklıdır.
* **Korkmuş** hayaletler yarı hızda Pacman'den uzaklaşır (deterministik).

Ajan rastgele seçimin **sonucunu bilmez**. Oyun durumu hayaletlerin rastgele
sayı üretecini de taşır; ajan bu üretece hiç dokunmaz, geleceği okumaz.
Yalnızca olasılıkları bilir; bu yüzden kararı "olası sonuçların" beklenen
faydasına dayanır.

Fayda fonksiyonu
----------------
Ulaşılan bir durum ``s`` (kökteki durum ``s0``) için:

    U(s) = W_SCORE * (s.puan - s0.puan)            puan değişimi (hareket maliyeti dahil)
         + W_EAT   * (yenen yemek sayısı)
         - W_FOOD  * (en yakın güvenli yemeğe BFS mesafesi)
         - toplam tehlike(normal hayalet)           hayalet riski
         - kapan(güvenli kare sayısı)               kaçış alanı
         + toplam av(korkmuş hayalet)               enerji etkisi
    U(s) = s Pacman'in yakalandığı durumsa  -LOSS + puan değişimi
    U(s) = s seviyenin tamamlandığı durumsa  +WIN + puan değişimi

Seçilen yön son yönün tersiyse ayrıca ``W_REVERSE`` düşülür (salınım
cezası). Hareket maliyeti ayrı bir terim değildir: oyunun kendi kuralı (her
hareket -1) puan değişiminin içindedir; yerinde durmak da seçenek değildir
(ödevde yalnızca dört yön vardır). Bileşenlerin ve ağırlıkların gerekçesi
``Weights`` sınıfındadır.

Bu modül grafik arayüzden bağımsızdır.
"""

from dataclasses import dataclass
from itertools import product

import ghosts
from game import Status


@dataclass(frozen=True)
class Weights:
    """Fayda fonksiyonunun ağırlıkları.

    Ölçek oyunun puanıdır: 1 birim = 1 puan. Değerler
    ``tools/benchmark_agent.py`` ile birçok seed'de ölçülerek ayarlanmıştır.
    """

    # Puan değişimi (yemek +10, enerji topu +50, hayalet +200, hareket -1).
    # Oyunun asıl hedefi puan olduğu için 1'dir; diğer ağırlıklar buna göre
    # ölçeklenir.
    score: float = 1.0

    # En yakın güvenli yemeğe her BFS adımı. Yemek uzaktayken puan değişimi
    # her yönde aynıdır (-1); ajanı yemeğe çeken bu terimdir. Yemek ödülünden
    # (10) küçük tutulur ki ajan bir yemeği yemek yerine "başka bir yemeğe
    # yaklaşmayı" seçmesin.
    food: float = 2.0
    # Yenen her yemek için ek fayda (oyunun +10 puanına ek olarak). Yemek
    # yendiğinde "en yakın yemek" başka bir yemeğe geçer ve mesafe birden
    # artabilir (haritanın öbür ucuna kadar, ~45 adım = 90 fayda). Bu terim
    # o sıçramadan büyük tutulur; yoksa ajan son yemeklerin etrafında yemeden
    # dolaşır, çünkü yemek "mesafeyi büyüttüğü" için kötü görünür.
    eat: float = 100.0
    # Güvenli yemek kalmadıysa en yakın yemeğin mesafesine eklenen sanal
    # adım sayısı: güvenli bir yemeğe uzak olmak, bir hayaletin önce varacağı
    # yemeğe yakın olmaktan iyidir.
    unsafe_food: int = 20

    # Normal hayalet tehlikesi. Hayalet ``danger_radius`` BFS adımından
    # yakınsa ceza ``danger * ((R - d + 1) / R) ** 2``: uzakta neredeyse sıfır,
    # yaklaştıkça hızla büyür. Yakalanma ihtimali zaten sonuçların içinde
    # olduğu için bu terim yalnızca "yakın gelecekte" riski temsil eder.
    danger: float = 150.0
    danger_radius: int = 5

    # Kaçış alanı: Pacman'in hayaletlerden önce varabildiği kare sayısı
    # ``trap_threshold``'un altına inince ``trap * (eksik / eşik) ** 2`` ceza.
    # İki hayalet arasında koridora sıkışmak (sandviç) bu sayıyı hızla
    # düşürür; mesafe cezası bu durumu tek başına göremez.
    trap: float = 400.0
    trap_threshold: int = 10

    # Korkmuş hayalete yaklaşma ödülü: ``hunt / (d + 1)``. Yalnızca enerji
    # etkisi hayalete ulaşmaya yetecek kadar sürecekse verilir; yetmeyecekse
    # kovalamak boşa adım ve risktir.
    hunt: float = 60.0

    # Son yönün tersine dönmek. Tehlike yokken ajanın iki kare arasında
    # gidip gelmesini önleyen küçük bir eğilim; tehlike cezasının yanında
    # önemsizdir, kaçmayı engellemez.
    reverse: float = 2.0

    # Kesin sonuçlar: kazanmak ve yakalanmak her şeyden önemlidir.
    win: float = 10_000.0
    loss: float = 10_000.0


DEFAULT_WEIGHTS = Weights()

# Kaç adım ileri bakılır. 2 adım hem tuzakları görmeye yeter hem de arayüzün
# bir oyun adımı (150 ms) içinde rahatça hesaplanır.
DEFAULT_DEPTH = 2


@dataclass(frozen=True)
class Evaluation:
    """Bir yönün değerlendirmesi (arayüzde gösterilir).

    ``utility`` ileri bakışla hesaplanan beklenen faydadır. ``parts``, bu
    adımın olası sonuçları üzerinden fayda bileşenlerinin beklenen
    değerleridir; kararın "neden"ini göstermek içindir.
    """

    direction: object
    utility: float
    parts: dict


class UtilityAgent:
    """Her adımda beklenen faydası en yüksek yönü seçen ajan."""

    name = "Yapay Zekâ"

    def __init__(self, weights=DEFAULT_WEIGHTS, depth=DEFAULT_DEPTH):
        self.weights = weights
        self.depth = depth
        self.last_evaluations = []      # son kararın bütün seçenekleri (arayüz için)

    def choose(self, state):
        """``state`` için en iyi yönü döndürür. ``state`` değişmez."""
        evaluations = []
        for direction in state.legal_directions():
            outcomes = self._outcomes(state, direction)
            utility = sum(p * self._value(state, after, self.depth - 1) for p, after in outcomes)
            parts = self._expected_parts(state, outcomes)
            if state.direction is not None and direction is state.direction.opposite:
                parts["geri dönüş"] = -self.weights.reverse
                utility -= self.weights.reverse
            evaluations.append(Evaluation(direction, utility, parts))
        self.last_evaluations = evaluations
        # Eşit faydada ``legal_directions`` sırası korunur: karar deterministiktir.
        return max(evaluations, key=lambda evaluation: evaluation.utility).direction

    # ------------------------------------------------------------------
    # Expectimax
    # ------------------------------------------------------------------
    def _value(self, root, state, depth):
        """Pacman'in sırası: en iyi yönün beklenen faydası (ya da yaprakta fayda)."""
        if depth == 0 or state.is_over:
            return self.utility(root, state)
        return max(sum(p * self._value(root, after, depth - 1) for p, after in self._outcomes(state, d))
                   for d in state.legal_directions())

    def _outcomes(self, state, direction):
        """Pacman ``direction``'a giderse olası sonuçlar: ``[(olasılık, durum), ...]``.

        Her senaryoda gezgin hayaletlerin seçimi önceden sabitlenir ve oyunun
        kendi ``step`` fonksiyonu o seçimlerle oynatılır; böylece çarpışma,
        yemek ve enerji kuralları gerçek oyunla birebir aynı işler.
        """
        choices = []
        for index, ghost in enumerate(state.ghosts):
            count = len(ghosts.allowed_moves(state, ghost))
            if index == 0 or ghost.frightened or count == 1 or self._is_far(state, ghost):
                # Deterministik hayalet ya da Pacman'i bu bakış ufkunda
                # etkileyemeyecek kadar uzak gezgin: tek senaryo yeter.
                choices.append([(1.0, 0)])
            else:
                choices.append([(1.0 / count, i) for i in range(count)])

        outcomes = []
        for scenario in product(*choices):
            probability = 1.0
            for p, _ in scenario:
                probability *= p
            after = state.clone()
            after.ghost_policy = _scenario_policy([i for _, i in scenario])
            after.step(direction)
            outcomes.append((probability, after))
        return outcomes

    def _is_far(self, state, ghost):
        # Pacman ve hayalet her adımda birer kare yaklaşabilir. Aradaki mesafe
        # bakış ufkunun iki katından büyükse bu hayaletin seçimi sonucu
        # değiştiremez; dallanmayı küçültmek için tek senaryo kullanılır.
        distance = state.level.distances_from(state.pacman).get(ghost.position, 0)
        return distance > 2 * self.depth + 2

    # ------------------------------------------------------------------
    # Fayda fonksiyonu
    # ------------------------------------------------------------------
    def utility(self, root, state):
        """Durumun faydası (bileşenler ``parts``'ta)."""
        return sum(self.parts(root, state).values())

    def parts(self, root, state):
        """Fayda fonksiyonunun bileşenleri: ``{ad: değer}``."""
        w = self.weights
        result = {"puan": w.score * (state.score - root.score)}
        if state.status is Status.LOST:
            result["yakalanma"] = -w.loss
        elif state.status is Status.WON:
            result["kazanma"] = w.win
        else:
            safe = self._safe_squares(state)
            result["yenen yemek"] = w.eat * (root.pellets_left - state.pellets_left)
            result["yemek mesafesi"] = -w.food * self._food_distance(state, safe)
            result["tehlike"] = -self._danger(state)
            result["kaçış alanı"] = -self._trap(len(safe))
            result["av"] = self._hunt(state)
        return result

    def _expected_parts(self, root, outcomes):
        expected = {}
        for probability, state in outcomes:
            for name, value in self.parts(root, state).items():
                expected[name] = expected.get(name, 0.0) + probability * value
        return expected

    @staticmethod
    def _safe_squares(state):
        """Pacman'in bütün normal hayaletlerden **önce** varabildiği kareler.

        Pacman bir kareye k. hamlesinde varana kadar her hayalet de k hamle
        yapmış olabilir (önce Pacman, sonra hayaletler hareket eder). Kare bu
        yüzden ancak ``d_pacman < d_hayalet`` ise güvenlidir. Hayaletin geri
        dönme yasağı hesaba katılmaz (temkinli tahmin).
        """
        pacman = state.level.distances_from(state.pacman)
        threats = [state.level.distances_from(g.position) for g in state.ghosts if not g.frightened]
        if not threats:
            return set(pacman)
        return {square for square, d in pacman.items()
                if all(d < threat.get(square, float("inf")) for threat in threats)}

    def _food_distance(self, state, safe):
        """En yakın **güvenli** yemeğe mesafe; güvenli yemek yoksa en yakın yemeğe + ceza.

        Bir hayaletin Pacman'den önce varacağı yemeğe koşmak boşunadır; ajan
        bu yüzden önce güvenli yemekleri hedefler.
        """
        distances = state.level.distances_from(state.pacman)
        reachable = [distances[pellet] for pellet in state.pellets if pellet in safe]
        if reachable:
            return min(reachable)
        return min(distances[pellet] for pellet in state.pellets) + self.weights.unsafe_food

    def _danger(self, state):
        w = self.weights
        distances = state.level.distances_from(state.pacman)
        total = 0.0
        for ghost in state.ghosts:
            if ghost.frightened:
                continue
            d = distances[ghost.position]
            if d <= w.danger_radius:
                total += w.danger * ((w.danger_radius - d + 1) / w.danger_radius) ** 2
        return total

    def _trap(self, safe_count):
        """Güvenli kare sayısı ``trap_threshold``'un altına indikçe karesel artan ceza."""
        w = self.weights
        shortage = max(0, w.trap_threshold - safe_count)
        return w.trap * (shortage / w.trap_threshold) ** 2

    def _hunt(self, state):
        w = self.weights
        distances = state.level.distances_from(state.pacman)
        total = 0.0
        for ghost in state.ghosts:
            if not ghost.frightened:
                continue
            d = distances[ghost.position]
            # Korkmuş hayalet yarı hızda kaçar: Pacman her iki adımda en az bir
            # kare yaklaşır. Etki bu sürede bitecekse kovalamaya değmez.
            if 2 * d < state.power_left:
                total += w.hunt / (d + 1)
        return total


def _scenario_policy(wanderer_choices):
    """Bir senaryonun hayalet politikası.

    Takipçi ve korkmuş hayaletler oyunun kendi kuralıyla (``ghosts.policy``)
    hareket eder; bu kurallar rastgelelik içermez. Gezgin hayaletler rastgele
    üreteç yerine senaryoda sabitlenen seçeneği (``wanderer_choices[i]``.
    sıradaki geçerli yön) uygular.
    """
    def policy(state, ghost):
        index = next(i for i, other in enumerate(state.ghosts) if other is ghost)
        if index == 0 or ghost.frightened:
            return ghosts.policy(state, ghost)
        options = ghosts.allowed_moves(state, ghost)
        return options[wanderer_choices[index] % len(options)][0]
    return policy
