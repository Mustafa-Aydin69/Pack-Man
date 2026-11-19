# Pacman — Fayda Tabanlı Rasyonel Ajan

Grafik arayüzlü bir Pacman oyunu ve oyunu bağımsız olarak oynayan **fayda
tabanlı rasyonel ajan** (utility-based rational agent). İnsan oyuncu ve yapay
zekâ aynı haritada, aynı kurallarla sırayla oynar; iki turun sonunda kazanan
ekranda gösterilir.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Arayüz](https://img.shields.io/badge/aray%C3%BCz-Tkinter-2E5BFF)
![Bağımlılık](https://img.shields.io/badge/d%C4%B1%C5%9F%20ba%C4%9F%C4%B1ml%C4%B1l%C4%B1k-yok-3FE0D0)
![Testler](https://img.shields.io/badge/testler-unittest-FFD23F)

## İçindekiler

- [Çalıştırma](#çalıştırma)
- [Oyun kuralları](#oyun-kuralları)
- [Maç akışı ve kazanan](#maç-akışı-ve-kazanan)
- [Hayaletler ve seviyeler](#hayaletler-ve-seviyeler)
- [Yapay zekâ: fayda tabanlı ajan](#yapay-zekâ-fayda-tabanlı-ajan)
- [Arayüz](#arayüz)
- [Proje mimarisi](#proje-mimarisi)
- [Testler ve doğrulama](#testler-ve-doğrulama)
- [EXE derleme ve teslim](#exe-derleme-ve-teslim)

## Çalıştırma

**EXE ile:** `Pacman.exe` dosyasına çift tıklayın. Python gerekmez.

**Kaynak koddan:** Python 3.9 veya üzeri yeterlidir (Tkinter, Python'un Windows
kurulumuyla gelir). Ek paket kurmak gerekmez.

```bat
python main.py
```

| Komut | İşlev |
|---|---|
| `python main.py` | Oyunu açar |
| `python main.py --self-test` | Pencere açmadan doğrulama (çıkış kodu 0 = başarılı) |
| `python -m unittest discover -s tests -v` | Bütün testler |
| `python tools/benchmark_agent.py` | Ajanı her seviyede 100 seed ile ölçer |

## Oyun kuralları

| Kural | Değer |
|---|---|
| Hareket | Yalnızca yukarı, aşağı, sol, sağ; duvarlardan geçilemez |
| Her hareket | **−1** puan |
| Yemek | **+10** puan |
| Enerji topu | **+50** puan; hayaletleri **40 adım** (6 sn) korkutur |
| Korkmuş hayaleti yakalamak | **+200** puan; hayalet başlangıç karesine döner |
| Normal hayalete çarpmak | Tur biter (yakalandı) |
| Seviyeyi tamamlamak | Bütün yemekleri (`.`) toplamak; enerji topları zorunlu değildir |
| Oyun hızı | 1 adım = 150 ms, iki oyuncu için aynı |
| Süre | Oyun içi adımla ölçülür (adım × 150 ms); duraklatma süreye eklenmez |

Değerlerin gerekçeleri `game.py` içindeki `Rules` sınıfında açıklanmıştır.
Karşılaşma kuralı: önce Pacman, sonra hayaletler hareket eder ve her yarım
adımdan sonra aynı kare denetlenir; bu sırayla kafa kafaya yer değiştirme de
yakalanma sayılır, karakterler birbirinin içinden geçemez.

## Maç akışı ve kazanan

1. Karşılama ekranında kimin önce oynayacağı seçilir (**İnsan başlasın** /
   **Yapay zekâ başlasın**, ya da 1 / 2 tuşları).
2. İlk oyuncu Seviye 1'den başlar; seviye tamamlanınca Seviye 2'ye geçer.
   Yakalanırsa ya da son seviyeyi bitirirse tur biter. Puan ve süre seviyeler
   boyunca birikir.
3. Ara ekrandan sonra ikinci oyuncunun turu **sıfırdan** başlar: aynı
   haritalar, başlangıç konumları, yemekler, enerji topları, hayalet seed'i
   ve kurallar.
4. Sonuç ekranı iki oyuncuyu karşılaştırır. Kazanan ödevin sırasıyla
   belirlenir: **önce bütün seviyeleri tamamlama**, eşitse **toplam puan**,
   o da eşitse **daha kısa süre**; hepsi eşitse **beraberlik**. Ekranda
   belirleyici ölçüt de yazılır.

## Hayaletler ve seviyeler

| Hayalet | Davranış |
|---|---|
| Takipçi (kırmızı) | Pacman'e BFS ile en kısa yoldan gider. 30 adım kovalar, 8 adım başlangıcına çekilir (klasik Pacman'deki dağılma modu). |
| Gezgin (diğerleri) | Kavşaklarda rastgele yön seçer; rastgelelik oyunun seed'inden gelir. |
| Korkmuş (enerji etkisinde) | Pacman'den en çok uzaklaşan yöne, yarı hızda kaçar. |

Hayaletler geri dönmez (yalnızca çıkmaz sokakta döner). Seed sabit olduğu
için iki oyuncu aynı hayalet davranışıyla karşılaşır.

| | Seviye 1 | Seviye 2 |
|---|---|---|
| Harita | 19 × 13 | 21 × 15 |
| Hayalet | 2 | 3 |
| Yemek / enerji topu | 116 / 4 | 147 / 4 |
| Çıkmaz sokak | yok | 4 |

Haritalar yüklenirken BFS ile Pacman'in **bütün yemeklere ulaşabildiği**
denetlenir; bu şartı sağlamayan bir harita oyuna giremez.

## Yapay zekâ: fayda tabanlı ajan

Ajan (`agent.py`) her adımda **beklenen faydayı en büyükleyen** yönü seçer:

1. Geçerli her yön için oyun durumu kopyalanır ve hamle kopyada oynatılır.
2. Hayaletlerin o adımdaki **olası her cevabı** olasılığıyla birlikte ayrı
   bir kopyada oynatılır: takipçi ve korkmuş hayaletler deterministiktir
   (olasılık 1), gezginler her geçerli yöne eşit olasılıkla gider.
3. Her sonuç fayda fonksiyonuyla puanlanır; beklenen fayda
   `EU(yön) = Σ P(sonuç) × U(sonuç)` olur.
4. Bu iki adım ileriye kadar sürdürülür (expectimax) ve en yüksek beklenen
   faydalı yön seçilir.

Ajan oyunun kurallarını ve hayaletlerin davranış kurallarını bilir, ama
hayaletlerin rastgele sayı üretecine **hiç bakmaz**: gezginin ne seçeceğini
bilmez, yalnızca olasılıkları bilir (bu bir testle doğrulanır).

### Fayda fonksiyonu

```
U(s) = W_SCORE × (puan değişimi)                    hareket maliyeti (−1) dahil
     + W_EAT   × (yenen yemek sayısı)
     − W_FOOD  × (en yakın güvenli yemeğe BFS mesafesi)
     − Σ tehlike(normal hayalet)
     − kapan(güvenli kare sayısı)
     + Σ av(korkmuş hayalet)
     ± kazanma / yakalanma
```

| Ağırlık | Değer | Gerekçe |
|---|---|---|
| `score` | 1 | Ölçek oyunun puanıdır; yemek, enerji topu, hayalet ve hareket maliyeti buradan gelir |
| `eat` | 100 | Bir yemek yendiğinde "en yakın yemek" uzağa sıçrayabilir (~45 adım × 2 = 90). Ödül bundan büyük tutulur; yoksa ajan son yemeklerin çevresinde yemeden dolaşır |
| `food` | 2 / adım | Ajanı en yakın güvenli yemeğe çeker. Güvenli yemek: Pacman'in hayaletlerden önce varabildiği yemek |
| `unsafe_food` | 20 adım | Güvenli yemek kalmadıysa en yakın yemeğe eklenen sanal mesafe |
| `danger` | 150, yarıçap 5 | Normal hayalet yaklaştıkça karesel artan ceza: `150 × ((5 − d + 1) / 5)²` |
| `trap` | 400, eşik 10 | Pacman'in hayaletlerden önce varabildiği kare sayısı 10'un altına inerse karesel ceza. İki hayalet arasında sıkışmayı (sandviç) yakalar |
| `hunt` | 60 | Korkmuş hayalete yaklaşma ödülü `60 / (d + 1)`; yalnızca enerji etkisi hayalete ulaşmaya yetiyorsa |
| `reverse` | 2 | Sebepsiz geri dönmeyi (ileri-geri salınımı) önleyen küçük ceza |
| `win` / `loss` | ±10 000 | Kesin sonuçlar her şeyden önemlidir |

Bileşenlerin ve ağırlıkların ayrıntılı açıklaması `agent.py` içindeki `Weights`
sınıfının yorumlarındadır.

### Ölçüm

`tools/benchmark_agent.py` ile her seviye 100 farklı seed'de arayüzsüz oynatıldı:

| | Tamamlama | Tamamlanan oyunlarda ortalama adım |
|---|---|---|
| Seviye 1 | %98 | 199 |
| Seviye 2 | %84 | 285 |

Maçta kullanılan seed (2026) ile ajan iki seviyeyi de tamamlar: Seviye 1'i 191
adımda (1369 puan), Seviye 2'yi 246 adımda (1824 puan). Ortalama karar süresi
1 ms'nin altındadır; arayüzde takılma olmaz.

## Arayüz

- **Karşılama:** iki büyük oyuncu seçim kartı ve orijinal arcade makinesinin
  tanıtım ekranı gibi, her nesnenin puanı kendi çizimiyle.
- **Oyun:** üstte skor, süre ve seviye; ortada labirent; altta kalan yemek,
  enerji etkisi ve her hayaletin durumu (kovalıyor / çekiliyor / geziyor /
  kaçıyor). Karakterler kareler arasında saniyede ~60 kareyle kayarak
  hareket eder; oyun mantığı yine her 150 ms'de bir adım ilerler.
- **Yapay zekânın kararı (AI pusulası):** Pacman'in çevresinde her geçerli yön
  bir ok; okun uzunluğu o yönün beklenen faydası, seçilen yön turkuaz, bu
  adımda yakalanma riski yüksek yön kırmızı. Altında seçilen yönün fayda
  bileşenleri yazar.
- **İnsan oynarken:** ok tuşu şeması, son basılan yönü gösterir.
- **Sonuç:** skor tablosu; kazanan üstte ve kendi renginde, belirleyici ölçüt
  açıklamasıyla.

| Tuş | İşlev |
|---|---|
| Oklar / W A S D | Yön |
| Boşluk | Duraklat / devam |
| 1 / 2 | Karşılamada ilk oyuncuyu seç |
| Enter | Ara ekranda ve sonuçta devam |

Skor ve başlıklarda kullanılan Press Start 2P yazı tipi SIL Open Font License
ile dağıtılır (`assets/fonts/OFL.txt`); bilgisayara kurulmaz, yalnızca program
açıkken kullanılır.

## Proje mimarisi

Oyun çekirdeği, hayaletler, ajan ve maç kuralları Tkinter kullanmaz; arayüz
olmadan çalıştırılıp test edilebilir.

| Dosya | İçerik |
|---|---|
| `levels.py` | Harita biçimi, yönler, BFS, erişilebilirlik denetimi, iki seviye |
| `game.py` | Kurallar ve puanlar (`Rules`), oyun durumu ve bir adım (`GameState`) |
| `ghosts.py` | Takipçi, gezgin ve korkmuş hayalet stratejileri |
| `agent.py` | Fayda tabanlı ajan, fayda fonksiyonu ve ağırlıklar |
| `match.py` | Bir oyuncunun turu (seviye geçişi), maç sırası, kazanan kuralı |
| `gui.py` | Ana pencere ve ekranlar arası geçiş |
| `welcome.py`, `game_screen.py`, `results.py` | Karşılama, oyun, ara ve sonuç ekranları |
| `views.py`, `widgets.py` | Tahta çizimi, sprite'lar, düğme, enerji çubuğu, AI pusulası, tuş şeması |
| `theme.py`, `fonts.py`, `timers.py` | Renkler ve yazı tipleri, yazı tipi yükleme, duraklatılabilen zamanlayıcı |
| `self_test.py` | `--self-test` doğrulaması |
| `tools/benchmark_agent.py` | Ajan ölçüm aracı |

## Testler ve doğrulama

```bat
python -m unittest discover -s tests -v
python main.py --self-test
```

Testler kuralları (hareket, puan, enerji, çarpışma, kazanma), hayalet
stratejilerini, seed ile tekrarlanabilirliği, ajanın kararlarını ve rastgele
üretece bakmadığını, kazanan kuralının bütün dallarını ve ekran akışını kapsar.
Arayüz testleri gerçek bir Tk penceresiyle çalışır; ekran yoksa atlanır.

## EXE derleme ve teslim

```bat
build_exe.bat
```

Betik PyInstaller'ı projeye özel `.venv-build` sanal ortamına kurar, kaynak
kodu `--self-test` ile doğrular ve `dist\Pacman.exe` dosyasını üretir. Aynı
derleme her `main` gönderiminde GitHub Actions üzerinde Windows'ta da
çalıştırılır ve EXE kendi self-test'inden geçirilir.

LMS teslim paketi: `README.txt`, `Pacman.exe` ve `Kaynak Kodlar/`.
