"""Krok 4: zlecenia na aukcję zamknięcia. Uruchamiany ok. 15:20 ET."""
import sys

import config
from common import in_window, load_day, log, now_et, save_day


def main(broker=None) -> str:
    now = now_et()
    ds = now.date().isoformat()

    if not in_window(now.time(), config.CLOSE_WINDOW):
        log("Poza oknem zamknięcia, koniec.")
        return "poza_oknem"
    rec = load_day(ds)
    if not rec or rec["etap"] != "otwarta":
        log("Brak otwartej sesji na dziś, koniec.")
        return "brak_sesji"

    if broker is None:
        from broker import AlpacaPaperBroker
        broker = AlpacaPaperBroker()

    for p in rec["pozycje"]:
        t = p["ticker"]
        try:
            f = broker.fill(p["zlecenie_wejscia"])
        except Exception as e:
            rec["powody"].append(f"{t}: błąd odczytu wejścia: {e}")
            continue
        p["wejscie"] = f
        if f["status"] != "filled":
            rec["powody"].append(f"{t}: wejście niewypełnione ({f['status']})")
        if f["ilosc"] <= 0:
            continue
        side = "sell" if p["kierunek"] == "LONG" else "buy"
        try:
            p["zlecenie_wyjscia"] = broker.submit(t, f["ilosc"], side, "close")
        except Exception as e:
            rec["powody"].append(f"{t}: błąd zlecenia wyjścia: {e}")

    rec["etap"] = "zamykana"
    save_day(rec)
    log(f"Złożono zlecenia zamknięcia: {sum('zlecenie_wyjscia' in p for p in rec['pozycje'])}")
    return "zamykana"


if __name__ == "__main__":
    print(main())
    sys.exit(0)
