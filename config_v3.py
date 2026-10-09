"""Zamrożona konfiguracja v3: day trading long-only na surowcach w trendzie. Zmiana tutaj = nowa wersja."""
from datetime import time, timedelta

VERSION = "3.0"
DATA_DIRNAME = "data_v3"
DIRECTIONS = ("LONG", "SKIP")          # tylko long; SKIP = świadomy brak pozycji

# Kandydaci. Rozłączne z v1.1 (USO, SMH, DBA, GLD, TLT) i v2 (QQQ, URA, ITA, INDA, COPX, IBIT).
INSTRUMENTS = [
    {"sektor": "srebro", "ticker": "SLV", "sector_en": "silver", "query": "silver price OR silver market"},
    {"sektor": "platyna", "ticker": "PPLT", "sector_en": "platinum", "query": "platinum price OR platinum market"},
    {"sektor": "miedz", "ticker": "CPER", "sector_en": "copper", "query": "copper price OR copper market"},
    {"sektor": "metale_bazowe", "ticker": "DBB", "sector_en": "base metals (aluminum, zinc, copper)",
     "query": "aluminum price OR zinc price OR base metals"},
    {"sektor": "gaz", "ticker": "UNG", "sector_en": "US natural gas", "query": "natural gas price OR Henry Hub OR LNG"},
    {"sektor": "brent", "ticker": "BNO", "sector_en": "Brent crude oil", "query": "Brent crude OR OPEC OR oil market"},
    {"sektor": "pszenica", "ticker": "WEAT", "sector_en": "wheat", "query": "wheat price OR wheat futures OR grain market"},
    {"sektor": "kukurydza", "ticker": "CORN", "sector_en": "corn", "query": "corn price OR corn futures OR USDA crop"},
    {"sektor": "soja", "ticker": "SOYB", "sector_en": "soybeans", "query": "soybean price OR soybean futures"},
    {"sektor": "cukier", "ticker": "CANE", "sector_en": "sugar", "query": "sugar price OR sugar futures"},
]

MODEL = "claude-sonnet-5-5"
PROMPT_FILE = "prompts/forecast_v3.0.txt"

BUDGET_USD = 33_333                   # jedna trzecia konta paper
MAX_POSITIONS = 5
NOTIONAL_USD = BUDGET_USD // MAX_POSITIONS
COST = 0.0015                         # 0,15%: surowcowe ETF-y mają szersze spready niż w v1.1
SMA_DAYS = 200
HISTORY_DAYS = 420
MAX_HEADLINES = 20
NEWS_HOURS = 24

FORECAST_WINDOW = (time(8, 0), time(9, 20))
FORECAST_DEADLINE = time(9, 25)
CLOSE_WINDOW = (time(15, 0), time(15, 48))
SETTLE_AFTER = time(16, 5)
FULL_DAY_CLOSE = time(16, 0)

SEED = 20261009
N_RANDOM = 1000
BEAT_THRESHOLD = 950
KILL_SESSIONS = 30
LIVE_SESSIONS = 60


def select_universe(broker, day):
    """Surowce w trendzie: wczorajsze zamknięcie > SMA200. Max 5, najsilniejsze najpierw.
    Zwraca (lista instrumentów, szczegóły dla logu)."""
    tickers = [i["ticker"] for i in INSTRUMENTS]
    bars = broker.daily_bars(tickers, day - timedelta(days=HISTORY_DAYS), day)
    info, chosen = {}, []
    for inst in INSTRUMENTS:
        t = inst["ticker"]
        closes = [b["c"] for b in bars.get(t, [])]
        if len(closes) < SMA_DAYS:
            info[t] = {"trend": False, "uwaga": "za krótka historia"}
            continue
        sma = sum(closes[-SMA_DAYS:]) / SMA_DAYS
        sila = closes[-1] / sma
        info[t] = {"zamkniecie": closes[-1], "sma200": round(sma, 4), "sila": round(sila, 4), "trend": sila > 1}
        if sila > 1:
            chosen.append((sila, inst))
    chosen.sort(key=lambda x: -x[0])
    return [inst for _, inst in chosen[:MAX_POSITIONS]], info
