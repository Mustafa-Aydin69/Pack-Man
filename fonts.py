"""Programla birlikte gelen yazı tiplerinin yüklenmesi.

Skor, süre ve başlıklar için arcade makinelerini anımsatan "Press Start 2P"
piksel yazı tipi kullanılır (SIL Open Font License; lisans metni
``assets/fonts/OFL.txt``). Yazı tipi bilgisayara kurulmaz: Windows'ta program
açılırken ``AddFontResourceEx`` ile yalnızca bu işleme özel (``FR_PRIVATE``)
yüklenir ve program kapanınca kendiliğinden kalkar.

Yükleme başarısız olursa (ör. dosya eksik, Windows dışı sistem) tema yedek
bir yazı tipine geçer; program yine çalışır.
"""

import os
import sys

FONT_DIR = os.path.join("assets", "fonts")
BUNDLED_FONTS = ("PressStart2P-Regular.ttf",)
FR_PRIVATE = 0x10


def resource_path(*parts):
    """Kaynak dosyanın yolu: kaynak koddan çalışırken proje klasörü, EXE'de PyInstaller'ın açtığı klasör."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def load_bundled_fonts():
    """Yazı tiplerini bu işleme yükler; yüklenen dosya sayısını döndürür.

    Tk penceresi oluşturulmadan önce çağrılmalıdır. Windows dışında bir şey
    yapmaz (oralarda yazı tipi sisteme kuruluysa zaten görünür).
    """
    if sys.platform != "win32":
        return 0
    try:
        import ctypes
        add_font = ctypes.windll.gdi32.AddFontResourceExW
    except (AttributeError, OSError):
        return 0
    loaded = 0
    for name in BUNDLED_FONTS:
        path = resource_path(FONT_DIR, name)
        if os.path.exists(path) and add_font(path, FR_PRIVATE, 0) > 0:
            loaded += 1
    return loaded
