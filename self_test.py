"""Grafik arayüz açmadan çalışan doğrulama testi (``main.py --self-test``).

EXE'nin Python kurulu olmayan bir bilgisayarda doğru paketlendiğini
doğrulamak için kontroller çalıştırır ve sonucu çıkış koduyla bildirir:
0 = başarılı, 1 = başarısız. Oyun çekirdeği ve ajan eklendikçe kontroller
genişletilir.

Pencereli (konsolsuz) EXE'de ekrana yazı basılamadığı için sonuçlar
``--report DOSYA`` ile bir dosyaya da yazılabilir.
"""

import sys

from agent import UtilityAgent
from game import GameState, Status
from ghosts import new_game
from levels import LEVELS, Direction, bfs_distances


def _check_levels():
    """Hazır seviyeler yükleniyor ve her yemeğe ulaşılabiliyor mu?"""
    for level in LEVELS:
        reachable = bfs_distances(level, level.pacman_start)
        assert level.pellets <= reachable.keys(), f"{level.name}: erişilemeyen yemek"
        assert len(level.ghost_starts) >= 2, f"{level.name}: hayalet sayısı"
    return f"{len(LEVELS)} seviye yüklendi; bütün yemekler erişilebilir"


def _check_game_rules():
    """Bir adımın puanı ve kopyanın bağımsızlığı (hayaletler hareketsiz)."""
    state = GameState(LEVELS[0])
    direction = state.legal_directions()[0]
    copy = state.clone()
    result = copy.step(direction)
    assert result.moved and copy.steps == 1
    assert copy.score in (state.rules.move_cost, state.rules.move_cost + state.rules.pellet,
                          state.rules.move_cost + state.rules.power)
    assert state.steps == 0 and state.pacman == LEVELS[0].pacman_start, "kopya asıl oyunu değiştirdi"
    assert state.status is Status.PLAYING
    return "oyun adımı, puanlama ve durum kopyalama"


def _check_seed_repeats():
    """Aynı seed ve aynı hamleler, standart hayaletlerle aynı oyunu üretir (iki oyuncu için eşit koşul)."""
    def run():
        state = new_game(LEVELS[1], seed=42)
        moves = (Direction.LEFT, Direction.UP, Direction.RIGHT, Direction.DOWN)
        for i in range(300):
            state.step(moves[i // 7 % 4])
        return state.pacman, state.score, state.steps, [g.position for g in state.ghosts], state.status
    assert run() == run(), "Aynı seed aynı oyunu vermedi"
    return "seed ile tekrarlanabilir oyun"


def _check_agent():
    """Fayda tabanlı ajan Seviye 1'i tamamlıyor mu? (Arayüzsüz, birkaç saniye.)"""
    state = new_game(LEVELS[0])
    agent = UtilityAgent()
    while not state.is_over and state.steps < 2000:
        state.step(agent.choose(state))
    assert state.status is Status.WON, f"ajan seviyeyi tamamlayamadı ({state.status.value})"
    return f"ajan Seviye 1'i {state.steps} adımda, {state.score} puanla tamamladı"


def _check_tkinter_available():
    """Tkinter ve Tcl/Tk kitaplıkları paketlenmiş mi? (Pencere açmaz.)"""
    import tkinter
    interpreter = tkinter.Tcl()
    version = interpreter.eval("info patchlevel")
    return f"Tkinter/Tcl {version} kullanılabilir"


def _check_fonts():
    """Programla gelen yazı tipi pakette mi? (Pencere açmaz.)"""
    import os

    import fonts
    for name in fonts.BUNDLED_FONTS:
        path = fonts.resource_path(fonts.FONT_DIR, name)
        assert os.path.getsize(path) > 10_000, f"{name} eksik ya da bozuk"
    return f"yazı tipleri pakette ({', '.join(fonts.BUNDLED_FONTS)})"


CHECKS = [
    _check_levels,
    _check_game_rules,
    _check_seed_repeats,
    _check_agent,
    _check_tkinter_available,
    _check_fonts,
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
