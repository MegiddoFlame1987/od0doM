"""Krok 1-3: newsy → prognozy → zlecenia na aukcję otwarcia. Uruchamiany ok. 08:30 ET."""
import sys
from datetime import timezone

import confload
import llm
import news
from common import in_window, load_day, log, now_et, save_day

config = confload.load()


def main(broker=None, forecaster=None, fetch=None) -> str:
    now = now_et()
    day = now.date()
    ds = day.isoformat()

    if not in_window(now.time(), config.FORECAST_WINDOW):
        log("Poza oknem prognozy, koniec.")
        return "poza_oknem"
    if load_day(ds):
        log("Dzień już zapisany, koniec.")
        return "juz_wykonane"

    if broker is None:
        from broker import AlpacaPaperBroker
        broker = AlpacaPaperBroker()
    forecaster = forecaster or llm.claude_forecast
    fetch = fetch or news.fetch_headlines

    rec = {"data": ds, "wersja": config.VERSION, "model": config.MODEL,
           "prompt_sha256": llm.prompt_sha256(), "etap": "prognoza",
           "zaliczona": None, "powody": [], "prognozy": [], "pozycje": []}
    all_tickers = {i["ticker"] for i in config.INSTRUMENTS}

    def finish(etap, zaliczona, powod):
        rec["etap"], rec["zaliczona"] = etap, zaliczona
        if powod:
            rec["powody"].append(powod)
        save_day(rec)
        log(f"{etap}: {'; '.join(rec['powody']) or 'ok'}")
        return etap

    close = broker.session_close(day)
    if close is None:
        return finish("pominieta", None, "giełda nieczynna")
    if close < config.FULL_DAY_CLOSE:
        return finish("pominieta", None, f"sesja skrócona do {close:%H:%M} ET")

    pending = [s for s in broker.open_order_symbols() if s in all_tickers]
    if pending:
        log(f"Są już otwarte zlecenia ({', '.join(pending)}), nie składam drugi raz. Koniec.")
        return "juz_wykonane"

    leftover = [s for s in broker.open_position_symbols() if s in all_tickers]
    if leftover:
        return finish("rozliczona", False, f"otwarte pozycje z poprzedniego dnia: {', '.join(leftover)}")

    # Uniwersum dnia: stałe (v1.1) albo wybrane przez config.select_universe (v3: trendujące surowce).
    select = getattr(config, "select_universe", None)
    if select is None:
        instruments = list(config.INSTRUMENTS)
    else:
        try:
            instruments, rec["uniwersum"] = select(broker, day)
        except Exception as e:
            return finish("rozliczona", False, f"błąd wyboru uniwersum: {e}")
        if not instruments:
            return finish("pominieta", None, "brak instrumentów w trendzie")
    rec["liczba_oczekiwana"] = len(instruments)

    # Prognozy. Agent widzi tylko nagłówki, nigdy cen.
    now_utc = now.astimezone(timezone.utc)
    for inst in instruments:
        try:
            heads = fetch(inst["query"], now_utc)
        except Exception as e:
            rec["powody"].append(f"{inst['ticker']}: błąd feedu: {e}")
            continue
        try:
            f = forecaster(inst, ds, heads)
        except Exception as e:
            rec["powody"].append(f"{inst['ticker']}: błąd prognozy: {e}")
            continue
        rec["prognozy"].append({
            "data": ds, "czas_zapisu_et": now_et().strftime("%H:%M"),
            "sektor": inst["sektor"], "ticker": inst["ticker"], **f,
            "naglowki": heads})

    late = [p["ticker"] for p in rec["prognozy"]
            if p["czas_zapisu_et"] > config.FORECAST_DEADLINE.strftime("%H:%M")]
    if late:
        rec["powody"].append(f"zapis po {config.FORECAST_DEADLINE:%H:%M} ET: {', '.join(late)}")
    if rec["powody"] or len(rec["prognozy"]) != len(instruments):
        return finish("rozliczona", False, None)

    save_day(rec)  # prognozy zapisane przed jakimkolwiek zleceniem

    # Zlecenia na aukcję otwarcia. SKIP (v3) = brak pozycji, bez zlecenia.
    active = [p for p in rec["prognozy"] if p["kierunek"] != "SKIP"]
    rec["pominiete"] = [{"ticker": p["ticker"]} for p in rec["prognozy"] if p["kierunek"] == "SKIP"]
    if not active:
        return finish("otwarta", None, None)   # świadome wstrzymanie się: sesja liczy się, wynik 0
    tickers = [p["ticker"] for p in active]
    try:
        prices = broker.latest_prices(tickers)
    except Exception as e:
        return finish("rozliczona", False, f"brak cen do wyliczenia wielkości: {e}")

    for p in active:
        t = p["ticker"]
        qty = int(config.NOTIONAL_USD // prices[t])
        side = "buy" if p["kierunek"] == "LONG" else "sell"
        try:
            oid = broker.submit(t, qty, side, "open")
        except Exception as e:
            rec["powody"].append(f"{t}: błąd zlecenia wejścia: {e}")
            continue
        rec["pozycje"].append({"ticker": t, "kierunek": p["kierunek"], "ilosc": qty,
                               "zlecenie_wejscia": oid})

    if not rec["pozycje"]:
        return finish("rozliczona", False, "żadne zlecenie nie zostało przyjęte")
    if rec["powody"]:
        rec["zaliczona"] = False
    return finish("otwarta", rec["zaliczona"], None)


if __name__ == "__main__":
    print(main())
    sys.exit(0)
