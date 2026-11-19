PACMAN - FAYDA TABANLI RASYONEL AJAN
Mustafa Aydın - Bireysel proje

Grafik arayüzlü bir Pacman oyunu ve oyunu bağımsız olarak oynayan fayda
tabanlı rasyonel ajan (utility-based rational agent). İnsan ve yapay zekâ
aynı haritada, aynı kurallarla sırayla oynar; kazanan ekranda gösterilir.


ÇALIŞTIRMA
----------
Pacman.exe dosyasına çift tıklayın. Python gerekmez.

Kaynak koddan çalıştırmak için (Python 3.9 veya üzeri, ek paket gerekmez):
    cd "Kaynak Kodlar"
    python main.py

Pencere açmadan doğrulama:  python main.py --self-test
Testler:                     python -m unittest discover -s tests
Ajan ölçümü:                 python tools/benchmark_agent.py


OYNANIŞ
-------
1. Karşılama ekranında kimin önce oynayacağını seçin
   ("İnsan başlasın" / "Yapay zekâ başlasın" ya da 1 / 2 tuşları).
2. Her tur Seviye 1'den başlar, tamamlanınca Seviye 2'ye geçilir.
3. Ara ekrandan sonra ikinci oyuncunun turu sıfırdan, aynı koşullarla başlar:
   aynı haritalar, başlangıç konumları, yemekler, enerji topları, hayalet
   davranışı (sabit seed) ve kurallar.
4. Sonuç ekranında iki oyuncunun sonucu ve kazanan gösterilir.

Tuşlar: Oklar veya W A S D = yön, Boşluk = duraklat, Enter = devam.


KURALLAR VE PUANLAMA
--------------------
Her hareket                        -1
Yemek                             +10
Enerji topu                       +50  (hayaletler 40 adım / 6 sn korkar)
Korkmuş hayaleti yakalamak       +200
Normal hayalete çarpmak            tur biter
Seviyeyi tamamlamak                bütün yemekleri toplamak

Oyun her 150 ms'de bir adım ilerler; hız iki oyuncu için aynıdır. Süre oyun
içi adımla ölçülür, duraklatma süreye eklenmez.

Kazanan sırasıyla: bütün seviyeleri tamamlayan; eşitse yüksek toplam puan;
o da eşitse daha kısa süre; hepsi eşitse beraberlik.

Hayaletler: Takipçi (kırmızı) Pacman'e en kısa yoldan gider, 30 adım kovalayıp
8 adım çekilir. Gezginler kavşaklarda rastgele (seed'li) yön seçer. Korkmuş
hayaletler yarı hızda kaçar.
Seviyeler: Seviye 1'de 2 hayalet, çıkmazsız geniş koridorlar. Seviye 2'de
3 hayalet, daha sık duvarlar ve 4 çıkmaz sokak. Bütün yemeklerin
erişilebilirliği harita yüklenirken BFS ile denetlenir.


YAPAY ZEKÂ
----------
Ajan (agent.py) her adımda beklenen faydayı en büyükleyen yönü seçer. Her
geçerli yön için oyun durumunu kopyalar, hayaletlerin olası her cevabını
olasılığıyla birlikte simüle eder ve sonuçları fayda fonksiyonuyla puanlar:

  U = puan değişimi (hareket maliyeti dahil)
    + 100 x yenen yemek
    - 2 x en yakın güvenli yemeğe BFS mesafesi
    - hayalet tehlikesi (yakın normal hayalet)
    - kaçış alanı cezası (hayaletlerden önce varılabilen kare azsa)
    + korkmuş hayalete yaklaşma ödülü
    +/- kazanma / yakalanma

Karar iki adım ileri bakılarak verilir (expectimax). Ajan hayaletlerin
rastgele sayı üretecine bakmaz; yalnızca olasılıkları bilir. Bileşenler ve
ağırlıkların gerekçeleri agent.py içindeki Weights sınıfında açıklanmıştır.
Oyun ekranındaki "Yapay zekânın kararı" paneli her yönün beklenen faydasını
canlı gösterir.

Ölçüm (her seviye 100 seed): Seviye 1'de %98, Seviye 2'de %84 tamamlama.


DOSYALAR
--------
Pacman.exe        Oyun (Windows, tek dosya)
Kaynak Kodlar/    Kaynak kod, testler, yazı tipi ve README.md (ayrıntılı belge)

Skorlarda kullanılan Press Start 2P yazı tipi SIL Open Font License ile
dağıtılır (Kaynak Kodlar/assets/fonts/OFL.txt).
