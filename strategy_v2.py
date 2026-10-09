"""Czysta logika v2: trend, filtr ryzyka, plan zleceń, krzywe kapitału. Bez sieci."""
import config_v2 as C


def sma(values: list, n: int):
    return sum(values[-n:]) / n if len(values) >= n else None


def sign(x) -> int:
    return (x > 0) - (x < 0)


def trend_targets(bars: dict) -> tuple:
    """bars: {ticker: [{d,o,c}, ...]} do wczoraj włącznie.
    Cel: +1 LONG (zamknięcie > SMA200), -1 SHORT (zamknięcie < SMA200), 0 brak historii."""
    cele, info = {}, {}
    for t, series in bars.items():
        closes = [b["c"] for b in series]
        avg = sma(closes, C.SMA_DAYS)
        last = closes[-1] if closes else None
        if avg is None:
            cele[t] = 0
            info[t] = {"zamkniecie": last, "sma200": None, "uwaga": "za krótka historia"}
        else:
            cele[t] = sign(last - avg)
            info[t] = {"zamkniecie": last, "sma200": round(avg, 4)}
    return cele, info


def final_targets(trend: dict, blocked: list) -> dict:
    return {t: (0 if t in blocked else d) for t, d in trend.items()}


def no_flip(targets: dict, current: dict) -> dict:
    """Zmiana kierunku w dwóch krokach: dziś zamknięcie do zera, jutro nowa pozycja."""
    return {t: (0 if sign(current.get(t, 0)) * d == -1 else d) for t, d in targets.items()}


def order_plan(targets: dict, held: dict, last_close: dict) -> list:
    """held: ilość ze znakiem (short ujemny). targets: +1/-1/0 po no_flip."""
    plan = []
    for t, d in targets.items():
        q = held.get(t, 0)
        if d == 0 and q != 0:
            plan.append({"ticker": t, "strona": "sell" if q > 0 else "buy", "ilosc": abs(q)})
        elif d != 0 and q == 0:
            qty = int(C.PER_ASSET_USD // last_close[t])
            if qty > 0:
                plan.append({"ticker": t, "strona": "buy" if d > 0 else "sell", "ilosc": qty})
    return plan


def merge_bars(records: list) -> dict:
    """Łączy bary z wielu dziennych zapisów: {ticker: {data: {o,c}}}."""
    out = {}
    for r in records:
        for t, series in r.get("bary", {}).items():
            for b in series:
                out.setdefault(t, {})[b["d"]] = {"o": b["o"], "c": b["c"]}
    return out


def simulate(prices: dict, decisions: dict, tickers: list) -> dict:
    """prices: {ticker: {data: {o,c}}}; decisions: {data: {ticker: +1/-1/0}} (pozycja od otwarcia tej sesji).
    Dni bez decyzji: pozycje bez zmian. Zwraca wynik łączny, maks. obsunięcie, krzywą."""
    dates = sorted({d for t in tickers for d in prices.get(t, {})})
    if decisions:
        dates = [d for d in dates if d >= min(decisions)]
    held = {t: 0 for t in tickers}
    prev_close = {t: None for t in tickers}
    equity, peak, max_dd, curve = 1.0, 1.0, 0.0, []
    for d in dates:
        new = dict(held)
        if d in decisions:
            new.update({k: int(v) for k, v in decisions[d].items()})
        rets = []
        for t in tickers:
            bar = prices.get(t, {}).get(d)
            if bar is None:
                rets.append(0.0)
                continue
            was, now, pc = held[t], new[t], prev_close[t]
            if pc is None and was:
                # pozycja "trzymana" zanim pojawiła się pierwsza cena: start po otwarciu, bez kosztu
                r = now * (bar["c"] / bar["o"] - 1) if now else 0.0
            elif was == now:
                r = now * (bar["c"] / pc - 1) if now else 0.0
            else:
                r = 0.0
                if was:
                    r += was * (bar["o"] / pc - 1) - C.COST_SIDE
                if now:
                    r += now * (bar["c"] / bar["o"] - 1) - C.COST_SIDE
            rets.append(r)
            prev_close[t] = bar["c"]
        held = new
        equity *= 1 + sum(rets) / len(tickers)
        peak = max(peak, equity)
        max_dd = max(max_dd, 1 - equity / peak)
        curve.append((d, equity))
    return {"wynik": equity - 1, "max_obsuniecie": max_dd, "krzywa": curve, "dni": len(dates)}


def ratio(res: dict) -> float:
    return res["wynik"] / res["max_obsuniecie"] if res["max_obsuniecie"] > 0 else float("inf")
