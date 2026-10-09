"""v2, przebieg dzienny (okno 08:00-09:20 ET).
Raz w tygodniu trend (SMA200) wyznacza cele. Codziennie newsy mogą tylko wyłączyć pozycję."""
import json
import os
import sys
from datetime import timedelta, timezone
from pathlib import Path

import config_v2 as C
import llm_v2
import news
import strategy_v2 as S
from common import ROOT, in_window, log, now_et


def data_dir() -> Path:
    d = Path(os.environ.get("DATA_DIR_V2", ROOT / "data_v2"))
    (d / "dni").mkdir(parents=True, exist_ok=True)
    return d


def _read(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _write(p: Path, obj) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def all_records() -> list:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((data_dir() / "dni").glob("*.json"))]


def main(broker=None, risk_fn=None, fetch=None) -> str:
    now = now_et()
    day = now.date()
    ds = day.isoformat()
    day_file = data_dir() / "dni" / f"{ds}.json"
    state_file = data_dir() / "stan.json"

    if not in_window(now.time(), C.RUN_WINDOW):
        log("v2: poza oknem, koniec.")
        return "poza_oknem"
    if day_file.exists():
        log("v2: dzień już zapisany, koniec.")
        return "juz_wykonane"

    if broker is None:
        from broker import AlpacaPaperBroker
        broker = AlpacaPaperBroker()
    risk_fn = risk_fn or llm_v2.claude_risk
    fetch = fetch or news.fetch_headlines

    if broker.session_close(day) is None:
        _write(day_file, {"data": ds, "wersja": C.VERSION, "etap": "pominieta", "powod": "giełda nieczynna"})
        return "pominieta"

    pending = [s for s in broker.open_order_symbols() if s in C.TICKERS]
    if pending:
        log(f"v2: otwarte zlecenia ({', '.join(pending)}), nie składam drugi raz.")
        return "juz_wykonane"

    bars = broker.daily_bars(C.TICKERS, day - timedelta(days=C.HISTORY_DAYS), day)
    state = _read(state_file, {})
    iso = day.isocalendar()
    week = f"{iso[0]}-W{iso[1]:02d}"
    weekly = state.get("ostatni_tydzien") != week

    if weekly:
        trend, info = S.trend_targets(bars)
        state = {"ostatni_tydzien": week, "cele_trend": trend, "zablokowane": [], "info_trend": info}
    trend = state["cele_trend"]
    blocked = list(state.get("zablokowane", []))

    held = {s: q for s, q in broker.positions().items() if s in C.TICKERS}

    # Filtr ryzyka: tylko dla aktywów z celem albo z pozycją. Może tylko wyłączyć, nigdy włączyć.
    ryzyko, bledy = {}, []
    now_utc = now.astimezone(timezone.utc)
    for a in C.ASSETS:
        t = a["ticker"]
        d = trend.get(t, 0) or S.sign(held.get(t, 0))
        if t in blocked or d == 0:
            continue
        kierunek = "LONG" if d > 0 else "SHORT"
        try:
            r = risk_fn(a, ds, fetch(a["query"], now_utc), kierunek)
        except Exception as e:
            bledy.append(f"{t}: {e}")   # błąd = brak sygnału ryzyka, pozycja bez zmian
            continue
        ryzyko[t] = {**r, "kierunek": kierunek}
        if r["ryzyko"] == "WYSOKIE":
            blocked.append(t)
    state["zablokowane"] = blocked

    final = S.final_targets(trend, blocked)
    wykonane = S.no_flip(final, held)          # odwrócenie kierunku w dwóch sesjach
    last_close = {t: bars[t][-1]["c"] for t in C.TICKERS if bars.get(t)}
    plan = S.order_plan(wykonane, held, last_close)

    rec = {"data": ds, "wersja": C.VERSION, "model": C.MODEL,
           "prompt_sha256": llm_v2.prompt_sha256(), "etap": "zlecenia_w_toku",
           "czas_et": now_et().strftime("%H:%M"), "tydzien": week,
           "sprawdzenie_trendu": weekly, "cele_trend": trend, "cele_final": final,
           "cele_wykonane": wykonane,
           "zablokowane": blocked, "ryzyko": ryzyko, "pozycje_przed": held,
           "plan": plan, "zlecenia": [], "bledy": bledy, "info_trend": state.get("info_trend", {}),
           "bary": {t: s[-10:] for t, s in bars.items()}}
    _write(state_file, state)
    _write(day_file, rec)   # decyzja zapisana przed zleceniami

    orders = []
    for p in plan:
        try:
            oid = broker.submit(p["ticker"], p["ilosc"], p["strona"], "open")
            orders.append({**p, "zlecenie": oid})
        except Exception as e:
            bledy.append(f"{p['ticker']}: błąd zlecenia: {e}")

    rec["zlecenia"], rec["bledy"], rec["etap"] = orders, bledy, "wykonana"
    _write(day_file, rec)
    longs = sum(1 for v in trend.values() if v > 0)
    shorts = sum(1 for v in trend.values() if v < 0)
    log(f"v2: trend LONG={longs} SHORT={shorts}, zablokowane={blocked}, "
        f"zlecenia={len(orders)}, błędy={len(bledy)}")
    return "wykonana"


if __name__ == "__main__":
    print(main())
    sys.exit(0)
