"""Testy offline v2. Uruchom: python -m unittest discover tests"""
import json
import os
import sys
import tempfile
import unittest
from datetime import date, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backtest_v2  # noqa: E402
import config  # noqa: E402
import config_v2 as C  # noqa: E402
import evaluate_v2  # noqa: E402
import forecast  # noqa: E402
import llm_v2  # noqa: E402
import run_v2  # noqa: E402
import strategy_v2 as S  # noqa: E402

RISING = {"QQQ", "URA", "ITA"}
FALLING = {"INDA", "COPX", "IBIT"}


def make_series(start: date, n: int, p0: float, step: float) -> list:
    out, d, p = [], start, p0
    while len(out) < n:
        if d.weekday() < 5:
            out.append({"d": d.isoformat(), "o": p, "c": p * (1 + step)})
            p *= 1 + step
        d += timedelta(days=1)
    return out


class FakeBroker:
    def __init__(self, held=None, pending=None, rising=None, short_history=()):
        self.held, self.pending = held or {}, pending or []
        self.rising = RISING if rising is None else rising
        self.short_history = set(short_history)
        self.orders = []

    def session_close(self, day):
        return time(16, 0)

    def open_order_symbols(self):
        return self.pending

    def open_position_symbols(self):
        return list(self.held)

    def positions(self):
        return dict(self.held)

    def daily_bars(self, symbols, start, end):
        out = {}
        for t in symbols:
            step = 0.002 if t in self.rising else -0.002
            n = 50 if t in self.short_history else 400
            s = make_series(date(2025, 6, 1), n, 100.0, step)
            out[t] = [b for b in s if b["d"] < end.isoformat()]
        return out

    def submit(self, symbol, qty, side, when):
        self.orders.append((symbol, qty, side, when))
        return f"o{len(self.orders)}"


def no_news(q, now):
    return []


def low(a, d, h, k):
    return {"ryzyko": "NISKIE", "powod": "spokojnie"}


FULL = {"QQQ": 10, "URA": 10, "ITA": 10, "INDA": -10, "COPX": -10, "IBIT": -10}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DATA_DIR_V2"] = self.tmp.name
        os.environ["DATA_DIR"] = self.tmp.name + "/v1"

    def tearDown(self):
        for k in ("FAKE_NOW_ET", "DATA_DIR_V2", "DATA_DIR"):
            os.environ.pop(k, None)
        self.tmp.cleanup()

    def at(self, iso):
        os.environ["FAKE_NOW_ET"] = iso

    def rec(self, ds):
        return json.loads((Path(self.tmp.name) / "dni" / f"{ds}.json").read_text())


class RunV2(Base):
    def test_weekly_trend_long_and_short(self):
        b = FakeBroker()
        self.at("2026-10-12T08:10")  # poniedziałek
        self.assertEqual(run_v2.main(b, low, no_news), "wykonana")
        self.assertEqual({o[0] for o in b.orders if o[2] == "buy"}, RISING)
        self.assertEqual({o[0] for o in b.orders if o[2] == "sell"}, FALLING)
        self.assertTrue(all(o[3] == "open" for o in b.orders))
        rec = self.rec("2026-10-12")
        self.assertTrue(rec["sprawdzenie_trendu"])
        self.assertEqual(rec["cele_trend"]["QQQ"], 1)
        self.assertEqual(rec["cele_trend"]["IBIT"], -1)
        self.assertEqual(rec["etap"], "wykonana")
        self.assertEqual(run_v2.main(b, low, no_news), "juz_wykonane")

    def test_midweek_keeps_trend_and_news_exits(self):
        self.at("2026-10-12T08:10")
        run_v2.main(FakeBroker(), low, no_news)
        # wtorek: ceny odwrócone, ale cele z poniedziałku zostają; newsy wyłączają URA
        b = FakeBroker(held=dict(FULL), rising=set())
        self.at("2026-10-13T08:10")

        def risk(a, d, h, k):
            return {"ryzyko": "WYSOKIE" if a["ticker"] == "URA" else "NISKIE", "powod": "x"}
        run_v2.main(b, risk, no_news)
        self.assertEqual(b.orders, [("URA", 10, "sell", "open")])
        self.assertEqual(self.rec("2026-10-13")["ryzyko"]["IBIT"]["kierunek"], "SHORT")
        # środa: URA zablokowane do końca tygodnia, nie wraca
        held = {k: v for k, v in FULL.items() if k != "URA"}
        b2 = FakeBroker(held=dict(held))
        self.at("2026-10-14T08:10")
        run_v2.main(b2, low, no_news)
        self.assertEqual(b2.orders, [])
        # następny poniedziałek: nowe sprawdzenie, blokada zdjęta
        b3 = FakeBroker(held=dict(held))
        self.at("2026-10-19T08:10")
        run_v2.main(b3, low, no_news)
        self.assertEqual(b3.orders, [("URA", int(C.PER_ASSET_USD // b3.daily_bars(["URA"], None, date(2026, 10, 19))["URA"][-1]["c"]), "buy", "open")])

    def test_flip_takes_two_sessions(self):
        # trzymamy QQQ long, trend mówi SHORT: dziś tylko zamknięcie, jutro otwarcie shorta
        b = FakeBroker(held={"QQQ": 10}, rising=set())
        self.at("2026-10-12T08:10")
        run_v2.main(b, low, no_news)
        qqq = [o for o in b.orders if o[0] == "QQQ"]
        self.assertEqual(qqq, [("QQQ", 10, "sell", "open")])
        self.assertEqual(self.rec("2026-10-12")["cele_wykonane"]["QQQ"], 0)
        b2 = FakeBroker(held={}, rising=set())
        self.at("2026-10-13T08:10")
        run_v2.main(b2, low, no_news)
        qqq = [o for o in b2.orders if o[0] == "QQQ"]
        self.assertEqual(len(qqq), 1)
        self.assertEqual(qqq[0][2], "sell")
        self.assertGreater(qqq[0][1], 10)

    def test_risk_only_for_targeted_or_held(self):
        seen = []

        def risk(a, d, h, k):
            seen.append(a["ticker"])
            return {"ryzyko": "NISKIE", "powod": "x"}
        self.at("2026-10-12T08:10")
        run_v2.main(FakeBroker(short_history={"IBIT"}), risk, no_news)
        self.assertEqual(sorted(seen), ["COPX", "INDA", "ITA", "QQQ", "URA"])

    def test_model_error_keeps_trend_orders(self):
        def boom(a, d, h, k):
            raise ValueError("timeout")
        b = FakeBroker()
        self.at("2026-10-12T08:10")
        run_v2.main(b, boom, no_news)
        self.assertEqual({o[0] for o in b.orders}, RISING | FALLING)
        self.assertEqual(len(self.rec("2026-10-12")["bledy"]), 6)

    def test_pending_and_window(self):
        self.at("2026-10-12T09:40")
        self.assertEqual(run_v2.main(FakeBroker(), low, no_news), "poza_oknem")
        self.at("2026-10-12T08:10")
        self.assertEqual(run_v2.main(FakeBroker(pending=["QQQ"]), low, no_news), "juz_wykonane")

    def test_v1_ignores_v2_positions_and_orders(self):
        from tests.test_offline import FakeBroker as V1Broker, fake_fetch, fake_forecaster
        b = V1Broker(leftover=["QQQ", "IBIT"])
        b.pending = ["URA"]
        self.at("2026-10-12T08:31")
        self.assertEqual(forecast.main(b, fake_forecaster, fake_fetch), "otwarta")


class Strategy(unittest.TestCase):
    def test_long_entry_and_exit_costs(self):
        prices = {"A": {"d1": {"o": 100, "c": 110}, "d2": {"o": 110, "c": 121}}}
        r = S.simulate(prices, {"d1": {"A": 1}}, ["A"])
        self.assertAlmostEqual(r["wynik"], (1.10 - C.COST_SIDE) * 1.10 - 1, places=6)
        r2 = S.simulate(prices, {"d1": {"A": 1}, "d2": {"A": 0}}, ["A"])
        self.assertAlmostEqual(r2["wynik"], (1.10 - C.COST_SIDE) * (1 - C.COST_SIDE) - 1, places=6)

    def test_short_profits_on_drop(self):
        prices = {"A": {"d1": {"o": 100, "c": 90}, "d2": {"o": 90, "c": 81}}}
        r = S.simulate(prices, {"d1": {"A": -1}}, ["A"])
        self.assertAlmostEqual(r["wynik"], (1 + 0.10 - C.COST_SIDE) * 1.10 - 1, places=6)

    def test_flip_costs_two_sides(self):
        prices = {"A": {"d1": {"o": 100, "c": 100}, "d2": {"o": 100, "c": 100}}}
        r = S.simulate(prices, {"d1": {"A": 1}, "d2": {"A": -1}}, ["A"])
        self.assertAlmostEqual(r["wynik"], (1 - C.COST_SIDE) * (1 - 2 * C.COST_SIDE) - 1, places=6)

    def test_max_drawdown(self):
        prices = {"A": {"d1": {"o": 100, "c": 100}, "d2": {"o": 100, "c": 50}, "d3": {"o": 50, "c": 75}}}
        r = S.simulate(prices, {"d1": {"A": 1}}, ["A"])
        self.assertAlmostEqual(r["max_obsuniecie"], 0.5, places=3)

    def test_no_flip_and_order_plan(self):
        self.assertEqual(S.no_flip({"A": -1, "B": 1, "C": 1}, {"A": 5, "B": 5, "C": -5}), {"A": 0, "B": 1, "C": 0})
        plan = S.order_plan({"A": 0, "B": -1, "C": 0}, {"A": 5, "C": -5}, {"B": 50.0})
        self.assertEqual(plan, [{"ticker": "A", "strona": "sell", "ilosc": 5},
                                {"ticker": "B", "strona": "sell", "ilosc": int(C.PER_ASSET_USD // 50)},
                                {"ticker": "C", "strona": "buy", "ilosc": 5}])

    def test_parse_risk_and_prompt(self):
        self.assertEqual(llm_v2.parse_risk('{"ryzyko": "wysokie", "powod": "Sankcje."}')["ryzyko"], "WYSOKIE")
        with self.assertRaises(ValueError):
            llm_v2.parse_risk('{"ryzyko": "SREDNIE", "powod": "x"}')
        system, _ = llm_v2.build_messages(C.ASSETS[0], "2026-10-12", [], "SHORT")
        self.assertIn("QQQ", system)
        self.assertIn("SHORT position", system)
        self.assertNotIn("$", system)

    def test_tickers_disjoint_from_v1(self):
        self.assertFalse(set(C.TICKERS) & {i["ticker"] for i in config.INSTRUMENTS})


class EvalAndBacktest(Base):
    def test_evaluate_runs(self):
        self.at("2026-10-12T08:10")
        run_v2.main(FakeBroker(), low, no_news)
        self.assertIn("PODGLĄD", evaluate_v2.main())

    def test_backtest_report(self):
        bars = FakeBroker().daily_bars(C.TICKERS, date(2016, 1, 1), date(2027, 1, 1))
        prices = {t: {b["d"]: {"o": b["o"], "c": b["c"]} for b in s} for t, s in bars.items()}
        text = backtest_v2.report(prices)
        self.assertIn("Werdykt", text)
        self.assertIn("| trend long/short |", text)
        self.assertIn("| trend tylko long |", text)
        dec = backtest_v2.weekly_decisions(prices)
        self.assertTrue(all(isinstance(k, str) for k in dec))


if __name__ == "__main__":
    unittest.main()
