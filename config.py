"""Zamrożona konfiguracja eksperymentu. Zmiana tutaj = nowa wersja reguł."""
from datetime import time

VERSION = "1.1"

INSTRUMENTS = [
    {"sektor": "ropa", "ticker": "USO", "sector_en": "crude oil",
     "query": "crude oil OR OPEC OR Brent OR WTI"},
    {"sektor": "chipy", "ticker": "SMH", "sector_en": "semiconductors",
     "query": "semiconductor OR chipmaker OR Nvidia OR TSMC"},
    {"sektor": "zywnosc", "ticker": "DBA", "sector_en": "agricultural commodities",
     "query": "wheat OR corn OR soybeans OR grain prices OR USDA"},
    {"sektor": "zloto", "ticker": "GLD", "sector_en": "gold",
     "query": "gold price OR bullion"},
    {"sektor": "obligacje", "ticker": "TLT", "sector_en": "long-term US Treasury bonds",
     "query": "Treasury yields OR Federal Reserve OR bond market"},
]

MODEL = "claude-sonnet-5-5"
PROMPT_FILE = "prompts/forecast_v1.1.txt"

NOTIONAL_USD = 10_000      # wielkość pozycji na ticker
COST = 0.001               # 0,10% na pozycję (wejście + wyjście)
MAX_HEADLINES = 20         # na sektor
NEWS_HOURS = 24

# Okna czasowe (ET). Skrypt poza oknem kończy się bez działania.
FORECAST_WINDOW = (time(8, 0), time(9, 20))
FORECAST_DEADLINE = time(9, 25)
CLOSE_WINDOW = (time(15, 0), time(15, 48))
SETTLE_AFTER = time(16, 5)
FULL_DAY_CLOSE = time(16, 0)

SEED = 20261008
N_RANDOM = 1000
BEAT_THRESHOLD = 950
KILL_SESSIONS = 30
LIVE_SESSIONS = 60
