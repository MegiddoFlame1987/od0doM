"""Test 1 zakładki Strategie: typy akcji z rolek vs S&P 500 (SPY) od dnia publikacji.
Rejestr: strategie/typy.json. Wynik: strategie/typy_raport.md. Bez LLM, bez decyzji, tylko ceny."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BENCH = "SPY"
HORYZONTY = (30, 90, 180, 365)


def first_close_on_or_after(series: list, d: str):
    for b in series:
        if b["d"] >= d:
            return b["d"], b["c"]
    return None, None


def close_at_or_before(series: list, d: str):
    last = None
    for b in series:
        if b["d"] > d:
            break
        last = b
    return (last["d"], last["c"]) if last else (None, None)


def evaluate(picks: list, bars: dict, today: date) -> list:
    rows = []
    for p in picks:
        s = bars.get(p["ticker"], [])
        d0, p0 = first_close_on_or_after(s, p["data"])
        _, b0 = first_close_on_or_after(bars.get(BENCH, []), p["data"])
        if p0 is None or b0 is None:
            rows.append({**p, "brak_danych": True})
            continue
        row = {**p, "data_wejscia": d0, "cena_wejscia": p0, "horyzonty": {}}
        for h in HORYZONTY:
            dh = (date.fromisoformat(d0) + timedelta(days=h)).isoformat()
            if date.fromisoformat(dh) > today:
                continue
            _, ph = close_at_or_before(s, dh)
            _, bh = close_at_or_before(bars[BENCH], dh)
            row["horyzonty"][h] = {"akcja": ph / p0 - 1, "spy": bh / b0 - 1}
        _, pn = close_at_or_before(s, today.isoformat())
        _, bn = close_at_or_before(bars[BENCH], today.isoformat())
        row["teraz"] = {"akcja": pn / p0 - 1, "spy": bn / b0 - 1, "dni": (today - date.fromisoformat(d0)).days}
        rows.append(row)
    return rows


def report(rows: list, today: date) -> str:
    out = [f"# Typy z rolek vs S&P 500 (SPY), stan na {today}", "",
           "Wejście: zamknięcie pierwszej sesji od daty publikacji. Bez kosztów, bez dywidend. "
           "Przewaga = wynik akcji minus wynik SPY w tym samym okresie.", "",
           "| Źródło | Data | Ticker | Etykieta | Wejście | Dni | Akcja | SPY | Przewaga |", "|---|---|---|---|---|---|---|---|---|"]
    groups = {}
    for r in rows:
        if r.get("brak_danych"):
            out.append(f"| {r['zrodlo']} | {r['data']} | {r['ticker']} | {r['etykieta']} | brak danych | | | | |")
            continue
        t = r["teraz"]
        adv = t["akcja"] - t["spy"]
        out.append(f"| {r['zrodlo']} | {r['data']} | {r['ticker']} | {r['etykieta']} | {r['cena_wejscia']:.2f} | "
                   f"{t['dni']} | {t['akcja']:+.1%} | {t['spy']:+.1%} | {adv:+.1%} |")
        groups.setdefault((r["zrodlo"], r["etykieta"]), []).append(adv)
    out += ["", "## Średnia przewaga nad SPY wg źródła i etykiety", "", "| Źródło | Etykieta | Typów | Średnia przewaga | Trafionych (przewaga > 0) |", "|---|---|---|---|---|"]
    for (z, e), advs in sorted(groups.items()):
        hits = sum(1 for a in advs if a > 0)
        out.append(f"| {z} | {e} | {len(advs)} | {mean(advs):+.1%} | {hits}/{len(advs)} |")
    out += ["", "## Horyzonty (gdy minęły)", "", "| Ticker | Data | " + " | ".join(f"{h} d akcja / SPY" for h in HORYZONTY) + " |",
            "|---|---|" + "---|" * len(HORYZONTY)]
    for r in rows:
        if r.get("brak_danych"):
            continue
        cells = []
        for h in HORYZONTY:
            x = r["horyzonty"].get(h)
            cells.append(f"{x['akcja']:+.1%} / {x['spy']:+.1%}" if x else "")
        out.append(f"| {r['ticker']} | {r['data']} | " + " | ".join(cells) + " |")
    out += ["", "## Reguła oceny (zapisana z góry)", "",
            "Werdykt po 180 dniach od publikacji każdej grupy: grupa \"KUP\" / \"RIGHT NOW\" ma sens tylko, gdy średnia przewaga nad SPY > 0 "
            "i więcej niż połowa typów bije SPY. Grupa \"TOO LATE\" bijąca \"RIGHT NOW\" = timing autora odwrócony. "
            "Jeden typ nie dowodzi niczego; liczy się grupa.", ""]
    return "\n".join(out)


def main(broker=None, today=None) -> str:
    picks = json.loads((ROOT / "strategie" / "typy.json").read_text(encoding="utf-8"))
    today = today or date.today()
    if broker is None:
        from broker import AlpacaPaperBroker
        broker = AlpacaPaperBroker()
    tickers = sorted({p["ticker"] for p in picks} | {BENCH})
    start = min(date.fromisoformat(p["data"]) for p in picks) - timedelta(days=7)
    bars = broker.daily_bars(tickers, start, today + timedelta(days=1))
    text = report(evaluate(picks, bars, today), today)
    (ROOT / "strategie" / "typy_raport.md").write_text(text, encoding="utf-8")
    print(text)
    return text


if __name__ == "__main__":
    main()
