"""Jednorazowy backtest samego trendu v2 (bez newsów, bez LLM) na historii od 2016.
Uruchamiany ręcznie przez workflow. Wynik: data_v2/backtest.md."""
import sys
from datetime import date

import config_v2 as C
import strategy_v2 as S
from run_v2 import data_dir

START = date(2016, 1, 1)


def weekly_decisions(prices: dict, long_only: bool = False) -> dict:
    """Pierwsza sesja każdego tygodnia: +1 gdy wczorajsze zamknięcie > SMA200, -1 gdy poniżej."""
    dates = sorted({d for t in C.TICKERS for d in prices.get(t, {})})
    decisions, seen = {}, set()
    for d in dates:
        iso = date.fromisoformat(d).isocalendar()
        wk = (iso[0], iso[1])
        if wk in seen:
            continue
        seen.add(wk)
        dec = {}
        for t in C.TICKERS:
            closes = [prices[t][x]["c"] for x in sorted(prices.get(t, {})) if x < d]
            avg = S.sma(closes, C.SMA_DAYS)
            sg = S.sign(closes[-1] - avg) if avg is not None else 0
            dec[t] = max(sg, 0) if long_only else sg
        decisions[d] = dec
    return decisions


def yearly(curve: list) -> dict:
    out, prev_end = {}, 1.0
    for y in sorted({d[:4] for d, _ in curve}):
        end = [e for d, e in curve if d[:4] == y][-1]
        out[y] = end / prev_end - 1
        prev_end = end
    return out


def report(prices: dict) -> str:
    dec = weekly_decisions(prices)
    first = min(dec)
    tr = S.simulate(prices, dec, C.TICKERS)
    lo = S.simulate(prices, weekly_decisions(prices, long_only=True), C.TICKERS)
    bh = S.simulate(prices, {first: {t: 1 for t in C.TICKERS}}, C.TICKERS)
    yrs = max(tr["dni"] / 252, 1e-9)
    lines = [f"# Backtest v{C.VERSION}: trend SMA{C.SMA_DAYS} (sprawdzany raz w tygodniu) vs kup i trzymaj", "",
             f"Okres: {first} → {tr['krzywa'][-1][0]} ({yrs:.1f} lat). Koszt {C.COST_SIDE:.2%} na stronę.",
             "Aktywa bez historii (np. IBIT przed 2024) liczone jako gotówka w obu wariantach.", "",
             "| Wariant | Wynik | Rocznie | Maks. obsunięcie | Wynik / obsunięcie |", "|---|---|---|---|---|"]
    for name, r in (("trend long/short", tr), ("trend tylko long", lo), ("kup i trzymaj", bh)):
        cagr = (1 + r["wynik"]) ** (1 / yrs) - 1
        lines.append(f"| {name} | {r['wynik']:+.1%} | {cagr:+.1%} | {r['max_obsuniecie']:.1%} | {S.ratio(r):.2f} |")
    lines += ["", "| Rok | Trend L/S | Trend long | Kup i trzymaj |", "|---|---|---|---|"]
    yt, yl, yb = yearly(tr["krzywa"]), yearly(lo["krzywa"]), yearly(bh["krzywa"])
    lines += [f"| {y} | {yt[y]:+.1%} | {yl.get(y, 0):+.1%} | {yb.get(y, 0):+.1%} |" for y in yt]
    best = max((("trend long/short", tr), ("trend tylko long", lo), ("kup i trzymaj", bh)),
               key=lambda x: S.ratio(x[1]))[0]
    verdict = (f"Najlepszy stosunek wynik/obsunięcie: {best}. "
               + ("Trend daje przewagę nad kup i trzymaj." if best != "kup i trzymaj"
                  else "TREND NIE DAJE PRZEWAGI na historii. Teza o trendzie na tych aktywach słaba."))
    lines += ["", "## Werdykt", "", verdict,
              "", "Uwaga: aktywa wybrano w 2026 jako 'trendy światowe', czyli z wiedzą o przeszłości. "
              "Backtest jest przez to zawyżony na korzyść obu wariantów."]
    return "\n".join(lines)


def main(broker=None) -> str:
    if broker is None:
        from broker import AlpacaPaperBroker
        broker = AlpacaPaperBroker()
    bars = broker.daily_bars(C.TICKERS, START, date.today())
    prices = {t: {b["d"]: {"o": b["o"], "c": b["c"]} for b in s} for t, s in bars.items()}
    text = report(prices)
    (data_dir() / "backtest.md").write_text(text, encoding="utf-8")
    print(text)
    return text


if __name__ == "__main__":
    main()
    sys.exit(0)
