"""Krok 5: rozliczenie po ceny wypełnienia. Uruchamiany po 16:05 ET."""
import csv
import sys

import config
from common import all_days, data_dir, load_day, log, now_et, save_day

CSV_FIELDS = ["data", "wersja", "zaliczona", "ticker", "kierunek", "pewnosc",
              "cena_wejscia", "cena_wyjscia", "zmiana", "wynik"]


def result(kierunek: str, entry: float, exit_: float) -> tuple:
    d = 1 if kierunek == "LONG" else -1
    change = (exit_ - entry) / entry
    return change, d * change - config.COST


def rebuild_csv() -> None:
    rows = []
    for rec in all_days():
        pew = {p["ticker"]: p["pewnosc"] for p in rec.get("prognozy", [])}
        for p in rec.get("pozycje", []):
            if "wynik" not in p:
                continue
            rows.append({"data": rec["data"], "wersja": rec["wersja"],
                         "zaliczona": rec["zaliczona"], "ticker": p["ticker"],
                         "kierunek": p["kierunek"], "pewnosc": pew.get(p["ticker"]),
                         "cena_wejscia": p["wejscie"]["cena"],
                         "cena_wyjscia": p["wyjscie"]["cena"],
                         "zmiana": round(p["zmiana"], 6), "wynik": round(p["wynik"], 6)})
    with open(data_dir() / "wyniki.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)


def main(broker=None) -> str:
    now = now_et()
    ds = now.date().isoformat()

    if now.time() < config.SETTLE_AFTER:
        log("Za wcześnie na rozliczenie, koniec.")
        return "za_wczesnie"
    rec = load_day(ds)
    if not rec or rec["etap"] not in ("otwarta", "zamykana"):
        log("Brak sesji do rozliczenia, koniec.")
        return "brak_sesji"

    if broker is None:
        from broker import AlpacaPaperBroker
        broker = AlpacaPaperBroker()

    if rec["etap"] == "otwarta":
        rec["powody"].append("zlecenia zamknięcia nie zostały złożone")

    for p in rec["pozycje"]:
        t = p["ticker"]
        try:
            if "zlecenie_wyjscia" in p:
                p["wyjscie"] = broker.fill(p["zlecenie_wyjscia"])
        except Exception as e:
            rec["powody"].append(f"{t}: błąd odczytu wyjścia: {e}")
        ent, ex = p.get("wejscie"), p.get("wyjscie")
        if ent and ex and ent["status"] == "filled" and ex["status"] == "filled" \
                and ent["cena"] and ex["cena"]:
            p["zmiana"], p["wynik"] = result(p["kierunek"], ent["cena"], ex["cena"])
        else:
            rec["powody"].append(f"{t}: brak pełnego wypełnienia wejścia lub wyjścia")

    try:
        leftover = broker.open_position_symbols()
    except Exception as e:
        leftover = [f"nieznane ({e})"]
    if leftover:
        rec["uwaga"] = f"OTWARTE POZYCJE: {', '.join(leftover)}. Zamknij ręcznie w panelu Alpaca paper."
        rec["powody"].append("otwarte pozycje po sesji")

    complete = len(rec["pozycje"]) == len(config.INSTRUMENTS) and all("wynik" in p for p in rec["pozycje"])
    rec["zaliczona"] = complete and not rec["powody"]
    rec["wynik_sesji"] = round(sum(p.get("wynik", 0) for p in rec["pozycje"]), 6)
    rec["etap"] = "rozliczona"
    save_day(rec)
    rebuild_csv()
    log(f"Rozliczono. Zaliczona: {rec['zaliczona']}. Wynik sesji: {rec['wynik_sesji']:+.4%}")
    return "rozliczona"


if __name__ == "__main__":
    print(main())
    sys.exit(0)
