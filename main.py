# Pacman — Fayda Tabanlı Rasyonel Ajan
#
# Gereksinimler : Python 3.9 veya üzeri ve Tkinter (Python'un Windows kurulumuyla gelir).
#                 Arayüz teması için ttkbootstrap 1.14.7 (requirements.txt):
#                     pip install -r requirements.txt
#                 ttkbootstrap kurulu değilse program standart ttk temasıyla, aynı
#                 işlevlerle çalışır; yalnızca görünüm sadeleşir.
# Çalıştırma    : python main.py
# Doğrulama     : python main.py --self-test   (pencere açmadan; çıkış kodu 0 = başarılı)
# Testler       : python -m unittest discover -s tests -v
# Ajan ölçümü   : python tools/benchmark_agent.py
#
# Dosyalar (hepsi aynı klasörde olmalıdır):
#   main.py       giriş noktası
#   levels.py     seviye haritaları, yönler, BFS ve harita doğrulaması
#   game.py       oyun kuralları, puanlama ve oyun durumu (arayüzden bağımsız)
#   ghosts.py     hayalet stratejileri: takipçi, gezgin, korkmuş (kaçan)
#   agent.py      fayda tabanlı rasyonel ajan (fayda fonksiyonu ve ağırlıklar)
#   match.py      bir oyuncunun turu: seviye geçişi ve toplam sonuç
#   gui.py        Tkinter ana penceresi ve ekranlar arası geçiş
#   game_screen.py oyun ekranı: oyun döngüsü, gösterge paneli, klavye, AI karar paneli
#   views.py      oyun tahtasının çizimi (labirent, yemekler, Pacman, hayaletler)
#   theme.py      arayüz teması: renkler, yazı tipleri, ttkbootstrap stilleri
#   timers.py     duraklatılabilen zamanlayıcı (oyun adımı)
#   self_test.py  --self-test doğrulaması
"""Uygulamanın giriş noktası."""

import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--self-test" in argv:
        from self_test import run_self_test

        report = None
        if "--report" in argv:
            index = argv.index("--report")
            report = argv[index + 1] if index + 1 < len(argv) else None
        return run_self_test(report)

    from gui import run

    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
