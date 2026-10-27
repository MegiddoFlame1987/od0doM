# Strategie: testy pomysłów z rolek i z literatury

Każdy pomysł dostaje ten sam test, zanim ktokolwiek pomyśli o pieniądzach: backtest albo śledzenie po kosztach, benchmark "kup i trzymaj" (SPY), reguła oceny spisana przed wynikiem. Nic z tej zakładki nie idzie live.

| # | Pomysł | Źródło | Test | Status |
|---|---|---|---|---|
| 1 | Typy akcji z rolek (Vertiv, EMCOR, Corning, Constellation, Vistra, Micron, Arista, Broadcom i inne) | martinelli_paul 5.10, derekanddakota 11.10 | `typy_rolek.py`: wynik od publikacji vs SPY, horyzonty 30/90/180/365 dni, co tydzień | **śledzenie od 27.10.2026** |
| 2 | Opening range breakout ("noise band") | rolka, Zarattini i Aziz 2023 | backtest 15-min ORB na SPY/QQQ 2018–2026 bez dźwigni vs kup i trzymaj | na liście |
| 3 | Pairs trading (Coke/Pepsi) | rolka, Gatev i in. 2006 | backtest pary ETF, wejście 2 sigma, vs kup i trzymaj obie | na liście |
| 4 | Trend SMA200 na "trendach światowych" | v2 | zrobiony 9.10: kup i trzymaj wygrało, `../data_v2/backtest.md` | **odrzucony** |

Jak dodać typ z rolki: dopisz wiersz do `typy.json` (źródło, data publikacji, ticker, etykieta, cena z rolki jeśli podana). Skrypt policzy resztę. Typ dopisany po fakcie z datą wsteczną psuje test, więc data = dzień, w którym rolka została zobaczona, albo data publikacji, jeśli jest widoczna.
