# Strategie: testy pomysłów z rolek i z literatury

Każdy pomysł dostaje ten sam test, zanim ktokolwiek pomyśli o pieniądzach: backtest albo śledzenie po kosztach, benchmark "kup i trzymaj" (SPY), reguła oceny spisana przed wynikiem. Nic z tej zakładki nie idzie live.

| # | Pomysł | Źródło | Test | Status |
|---|---|---|---|---|
| 1 | Typy akcji z rolek (Vertiv, EMCOR, Corning, Constellation, Vistra, Micron, Arista, Broadcom i inne) | martinelli_paul 5.10, derekanddakota 11.10 | `typy_rolek.py`: wynik od publikacji vs SPY, horyzonty 30/90/180/365 dni, co tydzień | **śledzenie od 27.10.2026** |
| 2 | Opening range breakout ("noise band") | rolka, Zarattini i Aziz 2023 | backtest 15-min ORB na SPY/QQQ 2018–2026 bez dźwigni vs kup i trzymaj | na liście |
| 3 | Pairs trading (Coke/Pepsi) | rolka, Gatev i in. 2006 | backtest pary ETF, wejście 2 sigma, vs kup i trzymaj obie | na liście |
| 4 | Trend SMA200 na "trendach światowych" | v2 | zrobiony 9.10: kup i trzymaj wygrało, `../data_v2/backtest.md` | **odrzucony** |
| 5 | Trend SMA200 na 30 niepowiązanych ETF-ach | naprawa błędu v2 (uniwersum bez wiedzy o przyszłości) | backtest 2016–2026 vs kup i trzymaj | **następny** |
| 6 | Momentum 12-1 | Jegadeesh i Titman 1993 | ten sam koszyk 30 ETF, rebalans miesięczny | na liście |
| 7 | Dual momentum | Antonacci | SPY / VEU / BND, decyzja miesięczna | na liście |
| 8 | "Krach akcji, krypto w górę" | rolka | korelacja BTC z Nasdaq w dniach spadków od 2018; teza przewiduje ujemną | na liście |
| 9 | Tabela 10 surowców | rozmowa 27.10 | cena, odległość od SMA200, zmiana 1 i 6 mies., co tydzień | **następny** |

Jak dodać typ z rolki: dopisz wiersz do `typy.json` (źródło, data publikacji, ticker, etykieta, cena z rolki jeśli podana). Skrypt policzy resztę. Typ dopisany po fakcie z datą wsteczną psuje test, więc data = dzień, w którym rolka została zobaczona, albo data publikacji, jeśli jest widoczna.

## Zapasowe źródło danych

| Źródło | Rola | Co daje | Status |
|---|---|---|---|
| Alpaca | główne | świece i ceny dla wszystkich testów | używane |
| London Strategic Edge (londonstrategicedge.com) | **backup** | świece od ticka do miesiąca, opcje z greckimi, makro od 1900, Parquet/CSV, darmowy klucz, 10 pobrań/h po max 1 mln wierszy | **niesprawdzone** |

Warunek użycia backupu: test zgodności z Alpaca. Dzienne świece SPY za 5 lat, porównanie zamknięć. Odchylenie powyżej 0,1% albo brakujące sesje = odpada. Do czasu testu nie podpinać do agenta ani do backtestu.

Ryzyka: brak niezależnych opinii, źródło danych nieujawnione, niespójne liczby na stronie (227 tys. vs 118 tys. zbiorów), skrót "LSE" myli się z London Stock Exchange. Pobrane pliki trzymamy u siebie, nie odpytujemy API na żywo.
