"""Testy offline: atrapy brokera, modelu i feedu. Uruchom: python -m unittest discover tests"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, time, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import close  # noqa: E402
import config  # noqa: E402
import evaluate  # noqa: E402
import forecast  # noqa: E402
import llm  # noqa: E402
import news  # noqa: E402
import settle  # noqa: E402
from common import all_days, load_day  # noqa: E402

DAY = "2026-10-12"
OPEN = {"USO": 80.0, "SMH": 250.0, "DBA": 26.0, "GLD": 240.0, "TLT": 90.0}
CLOSE = {"USO": 81.0, "SMH": 245.0, "DBA": 26.0, "GLD": 242.4, "TLT": 89.1}


class FakeBroker:
    def __init__(self, close_time=time(16, 0), leftover=None, fill_status="filled"):
        self.close_time, self.leftover, self.fill_status = close_time, leftover or [], fill_status
        self.orders, self.n = {}, 0

    def session_close(self, day):
        return self.close_time

    def open_position_symbols(self):
        return self.leftover

    def open_order_symbols(self):
        return getattr(self, "pending", [])

    def latest_prices(self, symbols):
        return {s: OPEN[s] for s in symbols}

    def submit(self, symbol, qty, side, when):
        self.n += 1
        oid = f"o{self.n}"
        price = OPEN[symbol] if when == "open" else CLOSE[symbol]
        self.orders[oid] = {"symbol": symbol, "qty": qty, "side": side, "when": when, "price": price}
        return oid

    def fill(self, oid):
        o = self.orders[oid]
        return {"status": self.fill_status, "cena": o["price"], "ilosc": o["qty"]}


def fake_fetch(query, now_utc):
    return [{"czas_utc": "2026-10-12 11:00", "tytul": f"news for {query[:10]}"}]


def fake_forecaster(inst, day, heads):
    return {"kierunek": "LONG" if inst["ticker"] in ("USO", "GLD") else "SHORT",
            "pewnosc": 3, "powod": "test"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DATA_DIR"] = self.tmp.name

    def tearDown(self):
        os.environ.pop("FAKE_NOW_ET", None)
        os.environ.pop("DATA_DIR", None)
        self.tmp.cleanup()

    def at(self, hhmm, day=DAY):
        os.environ["FAKE_NOW_ET"] = f"{day}T{hhmm}"


class FullDay(Base):
    def test_full_session(self):
        b = FakeBroker()
        self.at("08:31")
        self.assertEqual(forecast.main(b, fake_forecaster, fake_fetch), "otwarta")
        rec = load_day(DAY)
        self.assertEqual(len(rec["prognozy"]), 5)
        self.assertEqual(len(rec["pozycje"]), 5)
        self.assertEqual(rec["prompt_sha256"], llm.prompt_sha256())
        entry = [o for o in b.orders.values() if o["when"] == "open"]
        self.assertEqual({o["symbol"]: o["side"] for o in entry},
                         {"USO": "buy", "SMH": "sell", "DBA": "sell", "GLD": "buy", "TLT": "sell"})
        self.assertEqual(next(o for o in entry if o["symbol"] == "SMH")["qty"], 40)

        # druga próba tego samego dnia nic nie robi
        self.assertEqual(forecast.main(b, fake_forecaster, fake_fetch), "juz_wykonane")

        self.at("15:21")
        self.assertEqual(close.main(b), "zamykana")
        exits = [o for o in b.orders.values() if o["when"] == "close"]
        self.assertEqual(len(exits), 5)
        self.assertEqual(next(o for o in exits if o["symbol"] == "USO")["side"], "sell")
        self.assertEqual(next(o for o in exits if o["symbol"] == "SMH")["side"], "buy")

        self.at("16:30")
        self.assertEqual(settle.main(b), "rozliczona")
        rec = load_day(DAY)
        self.assertTrue(rec["zaliczona"], rec["powody"])
        w = {p["ticker"]: p["wynik"] for p in rec["pozycje"]}
        self.assertAlmostEqual(w["USO"], 0.0125 - 0.001)     # LONG +1,25%
        self.assertAlmostEqual(w["SMH"], 0.02 - 0.001)       # SHORT, spadek 2%
        self.assertAlmostEqual(w["DBA"], -0.001)             # bez zmiany, sam koszt
        self.assertAlmostEqual(w["GLD"], 0.01 - 0.001)
        self.assertAlmostEqual(w["TLT"], 0.01 - 0.001)
        self.assertTrue((Path(self.tmp.name) / "wyniki.csv").exists())
        self.assertEqual(settle.main(b), "brak_sesji")


class Guards(Base):
    def test_outside_window(self):
        self.at("09:40")
        self.assertEqual(forecast.main(FakeBroker(), fake_forecaster, fake_fetch), "poza_oknem")
        self.assertIsNone(load_day(DAY))

    def test_holiday_and_half_day(self):
        self.at("08:31")
        b = FakeBroker(close_time=None)
        self.assertEqual(forecast.main(b, fake_forecaster, fake_fetch), "pominieta")
        self.at("08:31", "2026-11-27")
        b = FakeBroker(close_time=time(13, 0))
        self.assertEqual(forecast.main(b, fake_forecaster, fake_fetch), "pominieta")
        self.assertEqual(b.orders, {})

    def test_leftover_positions_block_trading(self):
        self.at("08:31")
        b = FakeBroker(leftover=["USO"])
        forecast.main(b, fake_forecaster, fake_fetch)
        rec = load_day(DAY)
        self.assertFalse(rec["zaliczona"])
        self.assertEqual(b.orders, {})

    def test_pending_orders_block_duplicate(self):
        self.at("08:31")
        b = FakeBroker()
        b.pending = ["USO"]
        self.assertEqual(forecast.main(b, fake_forecaster, fake_fetch), "juz_wykonane")
        self.assertEqual(b.orders, {})
        self.assertIsNone(load_day(DAY))

    def test_bad_model_output_no_orders(self):
        def bad(inst, day, heads):
            if inst["ticker"] == "DBA":
                raise ValueError("zły JSON")
            return fake_forecaster(inst, day, heads)
        self.at("08:31")
        b = FakeBroker()
        forecast.main(b, bad, fake_fetch)
        rec = load_day(DAY)
        self.assertFalse(rec["zaliczona"])
        self.assertEqual(b.orders, {})

    def test_feed_failure_no_orders(self):
        def broken(q, n):
            raise OSError("timeout")
        self.at("08:31")
        b = FakeBroker()
        forecast.main(b, fake_forecaster, broken)
        self.assertFalse(load_day(DAY)["zaliczona"])
        self.assertEqual(b.orders, {})

    def test_deadline(self):
        self.at("09:19")
        orig = forecast.now_et
        calls = {"n": 0}

        def slow_now():
            calls["n"] += 1
            t = orig()
            return t if calls["n"] == 1 else t.replace(hour=9, minute=26)
        forecast.now_et = slow_now
        try:
            b = FakeBroker()
            forecast.main(b, fake_forecaster, fake_fetch)
        finally:
            forecast.now_et = orig
        rec = load_day(DAY)
        self.assertFalse(rec["zaliczona"])
        self.assertIn("09:25", " ".join(rec["powody"]))
        self.assertEqual(b.orders, {})

    def test_unfilled_entry_not_counted(self):
        b = FakeBroker(fill_status="canceled")
        self.at("08:31")
        forecast.main(b, fake_forecaster, fake_fetch)
        self.at("15:21")
        close.main(b)
        self.at("16:30")
        settle.main(b)
        self.assertFalse(load_day(DAY)["zaliczona"])

    def test_close_missed_still_settles_as_failed(self):
        b = FakeBroker()
        self.at("08:31")
        forecast.main(b, fake_forecaster, fake_fetch)
        self.at("16:30")
        settle.main(b)
        rec = load_day(DAY)
        self.assertFalse(rec["zaliczona"])
        self.assertEqual(rec["etap"], "rozliczona")


class ParseAndNews(unittest.TestCase):
    def test_parse_forecast(self):
        ok = llm.parse_forecast('Odpowiedź: {"kierunek": "short", "pewnosc": 4, "powod": "Spadek."}')
        self.assertEqual(ok, {"kierunek": "SHORT", "pewnosc": 4, "powod": "Spadek."})
        for bad in ['{"kierunek": "FLAT", "pewnosc": 3, "powod": "x"}',
                    '{"kierunek": "LONG", "pewnosc": 7, "powod": "x"}',
                    '{"kierunek": "LONG", "pewnosc": true, "powod": "x"}',
                    '{"kierunek": "LONG", "pewnosc": 2, "powod": ""}',
                    'brak json']:
            with self.assertRaises(ValueError):
                llm.parse_forecast(bad)

    def test_prompt_has_no_prices_and_fills(self):
        inst = config.INSTRUMENTS[0]
        system, user = llm.build_messages(inst, DAY, [{"czas_utc": "x", "tytul": "OPEC cuts"}])
        self.assertIn("USO", system)
        self.assertIn(DAY, system)
        self.assertIn("OPEC cuts", user)
        self.assertNotIn("$", system)

    def test_parse_rss_filters_old(self):
        xml = b"""<rss><channel>
        <item><title>New one</title><pubDate>Mon, 12 Oct 2026 11:00:00 GMT</pubDate></item>
        <item><title>Old one</title><pubDate>Fri, 09 Oct 2026 11:00:00 GMT</pubDate></item>
        <item><title>No date</title></item>
        </channel></rss>"""
        since = datetime(2026, 10, 11, 12, 30, tzinfo=timezone.utc)
        items = news.parse_rss(xml, since, 20)
        self.assertEqual([i["tytul"] for i in items], ["New one"])


class Gate(Base):
    def _write(self, n, agent_good):
        import random
        rng = random.Random(1)
        d = Path(self.tmp.name) / "dni"
        d.mkdir(exist_ok=True)
        for i in range(n):
            pos = []
            for inst in config.INSTRUMENTS:
                ch = rng.gauss(0, 0.01)
                k = ("LONG" if ch > 0 else "SHORT") if agent_good else rng.choice(["LONG", "SHORT"])
                dd = 1 if k == "LONG" else -1
                pos.append({"ticker": inst["ticker"], "kierunek": k, "zmiana": ch,
                            "wynik": dd * ch - config.COST})
            rec = {"data": f"2027-01-{i + 1:02d}" if i < 31 else f"2027-02-{i - 30:02d}",
                   "wersja": config.VERSION, "zaliczona": True, "pozycje": pos, "prognozy": []}
            (d / f"{rec['data']}.json").write_text(json.dumps(rec))

    def test_too_few(self):
        self._write(10, True)
        self.assertIn("ZA MAŁO", evaluate.main())

    def test_kill_random_agent(self):
        self._write(30, False)
        self.assertIn("KILL", evaluate.main())

    def test_perfect_agent_goes_live(self):
        self._write(60, True)
        self.assertEqual(len(all_days()), 60)
        self.assertIn("GO LIVE", evaluate.main())


if __name__ == "__main__":
    unittest.main()
