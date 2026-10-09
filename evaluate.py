"""Bramka: agent vs zawsze LONG vs 1000 losowych agentów. Uruchamiany ręcznie."""
import random
import sys

import config
from common import all_days, data_dir


def sessions(version: str = config.VERSION) -> list:
    days = [d for d in all_days() if d.get("wersja") == version and d.get("zaliczona") is True]
    return sorted(days, key=lambda d: d["data"])


def agent_total(sess: list) -> float:
    return sum(p["wynik"] for s in sess for p in s["pozycje"])


def always_long_total(sess: list) -> float:
    return sum(p["zmiana"] - config.COST for s in sess for p in s["pozycje"])


def random_totals(sess: list, n: int = config.N_RANDOM, seed: int = config.SEED) -> list:
    rng = random.Random(seed)
    changes = [p["zmiana"] for s in sess for p in s["pozycje"]]
    return [sum(rng.choice((1, -1)) * c - config.COST for c in changes) for _ in range(n)]


def beaten(agent: float, totals: list) -> int:
    return sum(1 for t in totals if agent > t)


def hit_rate(sess: list) -> float:
    pos = [p for s in sess for p in s["pozycje"]]
    hits = sum(1 for p in pos if (p["zmiana"] > 0) == (p["kierunek"] == "LONG"))
    return hits / len(pos) if pos else 0.0


def block(name: str, sess: list) -> tuple:
    a = agent_total(sess)
    totals = random_totals(sess)
    b = beaten(a, totals)
    st = sorted(totals)
    lines = [
        f"### {name} ({len(sess)} sesji)",
        "",
        "| Miara | Wartość |",
        "|---|---|",
        f"| Agent, łączny wynik | {a:+.2%} |",
        f"| Zawsze LONG | {always_long_total(sess):+.2%} |",
        f"| Losowi: 5. / 50. / 95. percentyl | {st[49]:+.2%} / {st[499]:+.2%} / {st[949]:+.2%} |",
        f"| Agent bije losowych | {b} z {config.N_RANDOM} |",
        f"| Trafność kierunku | {hit_rate(sess):.1%} |",
        "",
    ]
    return b >= config.BEAT_THRESHOLD, lines


def main() -> str:
    sess = sessions()
    n = len(sess)
    out = [f"# Raport bramki, reguły v{config.VERSION}", "",
           f"Zaliczone sesje: {n}", ""]

    if n < config.KILL_SESSIONS:
        verdict = f"ZA MAŁO DANYCH: {n}/{config.KILL_SESSIONS} sesji. Bez decyzji."
        if n:
            out += block("Stan bieżący (tylko podgląd, nie decyzja)", sess)[1]
    else:
        ok1, l1 = block(f"Sesje 1–{config.KILL_SESSIONS}", sess[:config.KILL_SESSIONS])
        out += l1
        if not ok1:
            verdict = "KILL: agent nie bije 950 z 1000 losowych w sesjach 1–30. Zamknij pętlę."
        elif n < config.LIVE_SESSIONS:
            verdict = f"PRÓG 30 ZALICZONY. Kontynuuj do {config.LIVE_SESSIONS} sesji ({n}/{config.LIVE_SESSIONS})."
        else:
            ok2, l2 = block(f"Sesje 31–{config.LIVE_SESSIONS}",
                            sess[config.KILL_SESSIONS:config.LIVE_SESSIONS])
            out += l2
            verdict = ("GO LIVE: próg spełniony w obu połowach. Rozważ live ze stałą kwotą."
                       if ok2 else "STOP: druga połowa nie spełnia progu. Brak przejścia na live.")

    out += ["## Werdykt", "", verdict, ""]
    text = "\n".join(out)
    (data_dir() / "raport.md").write_text(text, encoding="utf-8")
    print(text)
    return verdict


if __name__ == "__main__":
    main()
    sys.exit(0)
