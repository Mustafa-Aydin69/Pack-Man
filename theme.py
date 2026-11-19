"""Arayüz teması: renkler, yazı tipleri ve boşluklar.

Görsel kimlik 1980'lerin arcade makinesinden gelir: lacivert "labirent gecesi"
zemin, duvar mavisi çizgiler ve oyunun kendi karakter renkleri. Oyuncular da
bu renklerle tanınır: **insan Pacman sarısı**, **yapay zekâ hayalet
turkuazı**. Skor, süre ve başlıklar piksel yazı tipiyle, geri kalan metinler
dar ve okunaklı bir yazı tipiyle yazılır.

Arayüz yalnızca Tkinter ile çizilir; dış bağımlılık yoktur. Oyun kuralları ve
ajanla hiçbir ilgisi yoktur.
"""

# ----------------------------------------------------------------------
# Renkler
# ----------------------------------------------------------------------
COLORS = {
    "bg": "#10183A",          # labirent gecesi: pencere zemini
    "surface": "#18224D",     # şeritler ve paneller
    "surface_hi": "#22306A",  # üzerine gelinen düğme / seçili satır
    "line": "#2E5BFF",        # duvar mavisi: yapı çizgileri, çerçeveler
    "line_soft": "#2A3A78",   # ikincil ayırıcılar
    "text": "#E8ECFF",
    "muted": "#8A93C2",
    "human": "#FFD23F",       # Pacman sarısı = insan oyuncu
    "ai": "#3FE0D0",          # hayalet turkuazı = yapay zekâ
    "danger": "#FF4F5E",      # kiraz kırmızısı: risk, yakalanma
    "on_accent": "#10183A",   # sarı / turkuaz zemin üstündeki yazı
}

CANVAS_COLORS = {
    "background": "#0C1433",
    "wall_fill": "#152056",
    "wall_edge": COLORS["line"],
    "pellet": "#F7D9A8",
    "power": "#F7D9A8",
    "pacman": COLORS["human"],
    # Hayaletler sırayla bu renkleri alır: takipçi kırmızı, ilk gezgin turkuaz.
    "ghosts": (COLORS["danger"], COLORS["ai"], "#FF8FD1", "#FFA94D"),
    "ghost_frightened": "#3352FF",
    "ghost_flash": COLORS["text"],  # enerji etkisi bitmek üzereyken yanıp söner
    "ghost_eye": "#FFFFFF",
    "ghost_pupil": "#1A2BB8",
    "overlay_text": "#FFFFFF",
}

# ----------------------------------------------------------------------
# Yazı tipleri
# ----------------------------------------------------------------------
# İlk bulunan aile kullanılır. Bahnschrift Windows 10/11 ile gelir; piksel yazı
# tipi programla birlikte gelir (fonts.py).
UI_FAMILIES = ("Bahnschrift", "Segoe UI", "DejaVu Sans")
DISPLAY_FAMILIES = ("Press Start 2P", "Consolas", "DejaVu Sans Mono")

# Okunur metin ölçeği (punto): 9 / 11 / 14 / 18 / 24.
UI_SIZES = {"caption": 9, "body": 11, "lead": 14, "heading": 18, "title": 24}
# Piksel yazı tipi 8 pikselin katlarında keskin görünür; Tk'de eksi boyut piksel demektir.
DISPLAY_PIXELS = {"small": 8, "number": 16, "big": 24, "hero": 48}

_families = {"ui": UI_FAMILIES[-1], "display": DISPLAY_FAMILIES[-1]}
_scale = 1.0


def ui_font(size="body", *style):
    return (_families["ui"], UI_SIZES[size], *style)


def display_font(size="number"):
    return (_families["display"], -round(DISPLAY_PIXELS[size] * _scale))


def px(value, scale=None):
    """%100 ölçekteki piksel değerini ekran ölçeğine çevirir."""
    return round(value * (_scale if scale is None else scale))


def setup(root, scale=1.0):
    """Temayı ``root`` penceresine uygular: zemin rengi ve kullanılabilir yazı tipleri."""
    from tkinter import font as tkfont

    global _scale
    _scale = scale
    available = set(tkfont.families(root))
    _families["ui"] = next((f for f in UI_FAMILIES if f in available), UI_FAMILIES[-1])
    _families["display"] = next((f for f in DISPLAY_FAMILIES if f in available), DISPLAY_FAMILIES[-1])
    root.configure(background=COLORS["bg"])
    # Tk'nin varsayılan yazı tipleri de temaya uysun (ör. sistem iletişim kutuları dışındaki her şey).
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
        try:
            tkfont.nametofont(name, root=root).configure(family=_families["ui"], size=UI_SIZES["body"])
        except Exception:  # noqa: BLE001  (yazı tipi bulunamazsa varsayılan kalır)
            pass
    return _families.copy()


def describe():
    """Kullanılan yazı tipleri (self-test raporu için)."""
    return f"arayüz: {_families['ui']}, skor/başlık: {_families['display']}"
