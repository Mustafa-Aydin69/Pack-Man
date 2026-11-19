"""Ajanı arayüz açmadan birçok seed'de oynatıp sonuçları özetler.

Fayda fonksiyonunun ağırlıkları bu araçla ayarlanmıştır. Kullanım (proje
klasöründe):

    python tools/benchmark_agent.py            # her seviye için 100 seed
    python tools/benchmark_agent.py --seeds 30

Her seviye ayrı ayrı, sıfırdan oynatılır. Çıktı: tamamlama oranı, ortalama
puan, adım, yenen hayalet ve yakalanan oyunlarda kalan yemek.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import UtilityAgent  # noqa: E402
from game import Status  # noqa: E402
from ghosts import new_game  # noqa: E402
from levels import LEVELS  # noqa: E402

# Ajan takılırsa (ör. sonsuz döngü) oyun bu adımda kesilir ve "bitmedi" sayılır.
MAX_STEPS = 3000


def play(level, seed, agent=None):
    agent = agent or UtilityAgent()
    state = new_game(level, seed=seed)
    while not state.is_over and state.steps < MAX_STEPS:
        state.step(agent.choose(state))
    return state


def summarize(level, seeds, agent=None):
    states = [play(level, seed, agent) for seed in seeds]
    won = [s for s in states if s.status is Status.WON]
    lost = [s for s in states if s.status is Status.LOST]
    count = len(states)
    return {
        "level": level.name,
        "won": len(won),
        "lost": len(lost),
        "stuck": count - len(won) - len(lost),
        "win_rate": len(won) / count,
        "avg_score": sum(s.score for s in states) / count,
        "avg_steps_won": sum(s.steps for s in won) / len(won) if won else 0,
        "avg_ghosts": sum(s.ghosts_eaten for s in states) / count,
        "avg_left_lost": sum(s.pellets_left for s in lost) / len(lost) if lost else 0,
        "lost_seeds": [seed for seed, s in zip(seeds, states) if s.status is not Status.WON],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=100, help="seviye başına oyun sayısı")
    args = parser.parse_args(argv)
    seeds = range(args.seeds)
    for level in LEVELS:
        started = time.perf_counter()
        r = summarize(level, seeds)
        elapsed = time.perf_counter() - started
        print(f"{r['level']}: tamamlandı {r['won']}/{args.seeds} (%{100 * r['win_rate']:.0f}), "
              f"yakalandı {r['lost']}, takıldı {r['stuck']} | ort. puan {r['avg_score']:.0f}, "
              f"tamamlananlarda ort. adım {r['avg_steps_won']:.0f}, ort. hayalet {r['avg_ghosts']:.2f}, "
              f"yakalananlarda kalan yemek {r['avg_left_lost']:.0f} | {elapsed:.1f} sn")
        if r["lost_seeds"]:
            print(f"  bitmeyen seed'ler: {r['lost_seeds'][:20]}")


if __name__ == "__main__":
    main()
