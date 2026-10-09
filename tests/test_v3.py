"""Testy offline v3 (CONFIG_MODULE=config_v3). Uruchom: python -m unittest discover tests"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from datetime import date, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import close  # noqa: E402
import evaluate  # noqa: E402
import forecast  # noqa: E402
import llm  # noqa: E402
import news  # noqa: E402
import settle  # noqa: E402
import config_v3 as C3  # noqa: E402
from common import load_day  # noqa: E402

MODULES = (news, llm, forecast, close, settle, evaluate)
DAY = "2026-10-12"
# trend: siła = step; dodatni = powyżej SMA200
STEP = {"SLV": 0.004, "CPER": 0.003, "UNG": 0.002, "WEAT": 0.0015, "CORN": 0.001, "SOYB": 0.0005,
        "PPLT": -0.001, "DBB": -0.002, "BNO": -0.003, "CANE": -0.004}
OPEN = {t: 50.0 for t in STEP}
CLOSE = {"SLV": 51.0, "CPER": 49.5, "UNG": 50.0, "WEAT": 50.5, "CORN": 49.0, "SOYB": 50.25,
         "PPLT": 50.0, "DBB": 50.0, "BNO": 50.0, "CANE": 50.0}


def reload_all():
    for m in MODULES:
        importlib.reload(m)


def series(step, n=400):
    out, d, p = [], date(2025, 6, 1), 50.0
    while len(out) < n:
        if d.weekday() < 5:
            out.append({"d": d.isoformat(), "o": p, "c": p * (1 + step)})
            p *= 1 + step
        d += timedelta(days=1)
    return out


class FakeBroker:
    def __init__(self, steps=None, leftover=None, fill_status="filled"):
        self.steps = steps or STEP
        self.leftover, self.fill_status = leftover or [], fill_status
        self.orders, self.n, self.pending = {}, 0, []

    def session_close(self, day):
        return time(16, 0)

    def open_order_symbols(self):
        return self.pending

    def open_position_symbols(self):
        return self.leftover

    def daily_bars(self, symbols, start, end):
        out = {}
        for t in symbols:
            if start == date.fromisoformat(DAY):          # settle: cena dnia dla SKIP
                out[t] = [{"d": DAY, "o": OPEN[t], "c": CLOSE[t]}]
            else:
                out[t] = [b for b in series(self.steps.get(t, 0.0)) if b["d"] < end.isoformat()]
        return out

    def latest_prices(self, symbols):
        return {s: OPEN[s] for s in symbols}

    def submit(self, symbol, qty, side, when):
        self.n += 1
        oid = f"o{self.n}"
        self.orders[oid] = {"symbol": symbol, "qty": qty, "side": side, "when": when,
                            "price": OPEN[symbol] if when == "open" else CLOSE[symbol]}
        return oid

    def fill(self, oid):
        o = self.orders[oid]
        return {"status": self.fill_status, "cena": o["price"], "ilosc": o["qty"]}


def fake_fetch(q, now):
    return [{"czas_utc": "2026-10-12 11:00", "tytul": "news"}]


def long_for(tickers):
    def f(inst, day, heads):
        k = "LONG" if inst["ticker"] in tickers else "SKIP"
        return {"kierunek": k, "pewnosc": 3, "powod": "test"}
    return f


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["CONFIG_MODULE"] = "config_v3"
        os.environ["DATA_DIR"] = self.tmp.name
        reload_all()

    def tearDown(self):
        for k in ("CONFIG_MODULE", "DATA_DIR", "FAKE_NOW_ET"):
            os.environ.pop(k, None)
        reload_all()
        self.tmp.cleanup()

    def at(self, hhmm):
        os.environ["FAKE_NOW_ET"] = f"{DAY}T{hhmm}"


class Universe(Base):
    def test_top5_trending_by_strength(self):
        inst, info = C3.select_universe(FakeBroker(), date.fromisoformat(DAY))
        self.assertEqual([i["ticker"] for i in inst], ["SLV", "CPER", "UNG", "WEAT", "CORN"])
        self.assertTrue(info["SLV"]["trend"] and not info["CANE"]["trend"])
        self.assertFalse(info["SOYB"]["sila"] < 1)   # w trendzie, ale poza top 5

    def test_no_trend_means_skipped_day(self):
        self.at("08:31")
        b = FakeBroker(steps={t: -0.002 for t in STEP})
        self.assertEqual(forecast.main(b, long_for(set()), fake_fetch), "pominieta")
        self.assertEqual(b.orders, {})


class FullSession(Base):
    def test_long_and_skip_session(self):
        b = FakeBroker()
        self.at("08:31")
        self.assertEqual(forecast.main(b, long_for({"SLV", "CPER"}), fake_fetch), "otwarta")
        rec = load_day(DAY)
        self.assertEqual(rec["liczba_oczekiwana"], 5)
        self.assertEqual(len(rec["prognozy"]), 5)
        self.assertEqual({p["ticker"] for p in rec["pozycje"]}, {"SLV", "CPER"})
        self.assertEqual({p["ticker"] for p in rec["pominiete"]}, {"UNG", "WEAT", "CORN"})
        entry = [o for o in b.orders.values() if o["when"] == "open"]
        self.assertTrue(all(o["side"] == "buy" for o in entry))
        self.assertEqual(entry[0]["qty"], int(C3.NOTIONAL_USD // 50))

        self.at("15:21")
        self.assertEqual(close.main(b), "zamykana")
        self.assertEqual(len([o for o in b.orders.values() if o["when"] == "close"]), 2)

        self.at("16:30")
        self.assertEqual(settle.main(b), "rozliczona")
        rec = load_day(DAY)
        self.assertTrue(rec["zaliczona"], rec["powody"])
        w = {p["ticker"]: p["wynik"] for p in rec["pozycje"]}
        self.assertAlmostEqual(w["SLV"], 0.02 - C3.COST)
        self.assertAlmostEqual(w["CPER"], -0.01 - C3.COST)
        sk = {p["ticker"]: p["zmiana"] for p in rec["pominiete"]}
        self.assertAlmostEqual(sk["WEAT"], 0.01)
        self.assertAlmostEqual(sk["CORN"], -0.02)
        self.assertAlmostEqual(rec["wynik_sesji"], 0.01 - 2 * C3.COST)
        csv = (Path(self.tmp.name) / "wyniki.csv").read_text()
        self.assertIn("SKIP", csv)
        self.assertEqual(csv.count("\n"), 6)   # nagłówek + 5 decyzji

    def test_all_skip_counts_as_session(self):
        b = FakeBroker()
        self.at("08:31")
        self.assertEqual(forecast.main(b, long_for(set()), fake_fetch), "otwarta")
        self.assertEqual(b.orders, {})
        self.at("15:21")
        close.main(b)
        self.at("16:30")
        settle.main(b)
        rec = load_day(DAY)
        self.assertTrue(rec["zaliczona"], rec["powody"])
        self.assertEqual(rec["wynik_sesji"], 0.0)
        self.assertEqual(len(rec["pominiete"]), 5)

    def test_short_answer_rejected(self):
        with self.assertRaises(ValueError):
            llm.parse_forecast('{"kierunek": "SHORT", "pewnosc": 3, "powod": "x"}')
        self.assertEqual(llm.parse_forecast('{"kierunek": "skip", "pewnosc": 2, "powod": "x"}')["kierunek"], "SKIP")
        system, _ = llm.build_messages(C3.INSTRUMENTS[0], DAY, [])
        self.assertIn("SLV", system)
        self.assertIn("SKIP", system)
        self.assertNotIn("$", system)

    def test_leftover_from_v1_ticker_is_ignored(self):
        b = FakeBroker(leftover=["USO", "QQQ"])
        self.at("08:31")
        self.assertEqual(forecast.main(b, long_for({"SLV"}), fake_fetch), "otwarta")

    def test_data_dir_defaults_to_v3(self):
        os.environ.pop("DATA_DIR")
        from common import data_dir
        self.assertTrue(str(data_dir()).endswith("data_v3"))


class Gate(Base):
    def _write(self, n, perfect):
        import random
        rng = random.Random(3)
        d = Path(self.tmp.name) / "dni"
        d.mkdir(exist_ok=True)
        for i in range(n):
            pos, skip = [], []
            for t in ["SLV", "CPER", "UNG", "WEAT", "CORN"]:
                ch = rng.gauss(0, 0.01)
                go = (ch > 0) if perfect else (rng.random() < 0.5)
                if go:
                    pos.append({"ticker": t, "kierunek": "LONG", "zmiana": ch, "wynik": ch - C3.COST})
                else:
                    skip.append({"ticker": t, "zmiana": ch, "wynik": 0.0})
            rec = {"data": f"2027-01-{i + 1:02d}" if i < 31 else f"2027-02-{i - 30:02d}",
                   "wersja": C3.VERSION, "zaliczona": True, "pozycje": pos, "pominiete": skip, "prognozy": []}
            (d / f"{rec['data']}.json").write_text(json.dumps(rec))

    def test_random_agent_killed(self):
        self._write(30, False)
        self.assertIn("KILL", evaluate.main())

    def test_perfect_agent_goes_live(self):
        self._write(60, True)
        self.assertIn("GO LIVE", evaluate.main())
        self.assertTrue(evaluate.LONG_ONLY)


if __name__ == "__main__":
    unittest.main()
