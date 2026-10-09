"""Ocena v2: z filtrem newsów vs sam trend vs kup i trzymaj. Uruchamiany ręcznie."""
import sys
from datetime import date

import config_v2 as C
import strategy_v2 as S
from run_v2 import all_records, data_dir


def results(records: list) -> dict:
    recs = [r for r in records if r.get("wersja") == C.VERSION and "cele_final" in r]
    if not recs:
        return {}
    prices = S.merge_bars(recs)
    first = recs[0]["data"]
    return {
        "v2 (trend L/S + filtr newsów)": S.simulate(
            prices, {r["data"]: r.get("cele_wykonane", r["cele_final"]) for r in recs}, C.TICKERS),
        "sam trend L/S (cień, bez filtra)": S.simulate(
            prices, {r["data"]: r["cele_trend"] for r in recs}, C.TICKERS),
        "kup i trzymaj": S.simulate(prices, {first: {t: 1 for t in C.TICKERS}}, C.TICKERS),
    }, recs


def table(res: dict) -> list:
    lines = ["| Wariant | Wynik | Maks. obsunięcie | Wynik / obsunięcie |", "|---|---|---|---|"]
    for name, r in res.items():
        rat = S.ratio(r)
        lines.append(f"| {name} | {r['wynik']:+.2%} | {r['max_obsuniecie']:.2%} | "
                     f"{'∞' if rat == float('inf') else f'{rat:.2f}'} |")
    return lines


def main() -> str:
    out = results(all_records())
    if not out:
        print("Brak danych v2.")
        return "BRAK DANYCH"
    res, recs = out
    weeks = (date.fromisoformat(recs[-1]["data"]) - date.fromisoformat(recs[0]["data"])).days // 7
    v2, tr, bh = res.values()
    blocks = sum(1 for r in recs for x in r.get("ryzyko", {}).values() if x["ryzyko"] == "WYSOKIE")

    lines = [f"# Raport v{C.VERSION}", "", f"Okres: {recs[0]['data']} → {recs[-1]['data']} ({weeks} tyg.)",
             f"Sygnały WYSOKIE z newsów: {blocks}", ""] + table(res) + [""]

    if weeks < C.EVAL_WEEKS:
        verdict = f"PODGLĄD, bez decyzji: {weeks}/{C.EVAL_WEEKS} tygodni."
    else:
        keep_filter = (v2["max_obsuniecie"] < tr["max_obsuniecie"]
                       and v2["wynik"] >= tr["wynik"] - C.FILTER_TOLERANCE)
        keep_trend = S.ratio(tr) > S.ratio(bh)
        verdict = (f"Filtr newsów: {'ZOSTAJE' if keep_filter else 'DO USUNIĘCIA'}. "
                   f"Trend vs kup i trzymaj: {'TREND LEPSZY' if keep_trend else 'TREND NIE DAJE PRZEWAGI'}.")
    lines += ["## Werdykt", "", verdict, ""]
    text = "\n".join(lines)
    (data_dir() / "raport.md").write_text(text, encoding="utf-8")
    print(text)
    return verdict


if __name__ == "__main__":
    main()
    sys.exit(0)
