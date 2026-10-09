"""Zamrożona konfiguracja v2. Zmiana tutaj = nowa wersja reguł v2."""
from datetime import time

VERSION = "2.0"

# Aktywa z trendami światowymi. Rozłączne z tickerami v1.1.
ASSETS = [
    {"ticker": "QQQ", "temat": "AI i big tech", "theme_en": "US big tech and AI",
     "query": "Nasdaq OR big tech stocks OR AI spending"},
    {"ticker": "URA", "temat": "uran / energia jądrowa", "theme_en": "uranium and nuclear energy",
     "query": "uranium OR nuclear power OR Cameco"},
    {"ticker": "ITA", "temat": "zbrojenia", "theme_en": "aerospace and defense",
     "query": "defense spending OR defense stocks OR Lockheed OR RTX"},
    {"ticker": "INDA", "temat": "Indie", "theme_en": "Indian equities",
     "query": "India stocks OR Sensex OR Nifty OR Reserve Bank of India"},
    {"ticker": "COPX", "temat": "miedź / elektryfikacja", "theme_en": "copper miners",
     "query": "copper price OR copper miners OR Freeport"},
    {"ticker": "IBIT", "temat": "bitcoin", "theme_en": "bitcoin",
     "query": "bitcoin OR crypto market OR bitcoin ETF"},
]
TICKERS = [a["ticker"] for a in ASSETS]

BUDGET_USD = 50_000                  # połowa konta paper
PER_ASSET_USD = BUDGET_USD / len(ASSETS)
SMA_DAYS = 200
COST_SIDE = 0.0005                   # 0,05% na wejście i 0,05% na wyjście
HISTORY_DAYS = 420                   # kalendarzowo, ok. 290 sesji

MODEL = "claude-sonnet-5-5"
PROMPT_FILE = "prompts/risk_v2.0.txt"

RUN_WINDOW = (time(8, 0), time(9, 20))   # ET, zlecenia na aukcję otwarcia
EVAL_WEEKS = 26
FILTER_TOLERANCE = 0.01              # filtr może kosztować max 1 pp wyniku
