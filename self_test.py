"""Grafik arayüz açmadan çalışan doğrulama testi (``main.py --self-test``).

EXE'nin Python kurulu olmayan bir bilgisayarda doğru paketlendiğini
doğrulamak için kontroller çalıştırır ve sonucu çıkış koduyla bildirir:
0 = başarılı, 1 = başarısız. Oyun çekirdeği ve ajan eklendikçe kontroller
genişletilir.

Pencereli (konsolsuz) EXE'de ekrana yazı basılamadığı için sonuçlar
``--report DOSYA`` ile bir dosyaya da yazılabilir.
"""

import sys


def _check_tkinter_available():
    """Tkinter ve Tcl/Tk kitaplıkları paketlenmiş mi? (Pencere açmaz.)"""
    import tkinter
    interpreter = tkinter.Tcl()
    version = interpreter.eval("info patchlevel")
    return f"Tkinter/Tcl {version} kullanılabilir"


def _check_theme():
    """Arayüz teması yüklenebiliyor mu? (Pencere açmaz; kullanılan temayı bildirir.)"""
    import theme
    return f"Arayüz teması: {theme.theme_description()}"


CHECKS = [
    _check_tkinter_available,
    _check_theme,
]


def run_self_test(report_path=None):
    """Bütün kontrolleri çalıştırır; başarılıysa 0, değilse 1 döndürür."""
    lines, failed = [], 0
    for check in CHECKS:
        try:
            lines.append(f"[TAMAM] {check()}")
        except Exception as exc:  # noqa: BLE001  (her hata raporlanmalı)
            failed += 1
            lines.append(f"[HATA]  {check.__name__}: {type(exc).__name__}: {exc}")
    lines.append(f"Sonuç: {len(CHECKS) - failed}/{len(CHECKS)} kontrol başarılı.")
    text = "\n".join(lines) + "\n"
    if report_path:
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write(text)
    if sys.stdout is not None:      # pencereli EXE'de stdout yoktur
        _write_console(text)
    return 0 if failed == 0 else 1


def _write_console(text):
    """Metni konsola yazar; kodlamada olmayan harfler (ör. ğ, ş) "?" olarak yazılır.

    Çıktı Türkçe harfleri desteklemeyen bir kodlamaya yönlendirildiğinde
    sonucun tamamen kaybolmaması içindir.
    """
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        try:
            sys.stdout.write(text.encode(encoding, "replace").decode(encoding))
        except (OSError, LookupError, UnicodeError):
            pass
    except OSError:
        pass
