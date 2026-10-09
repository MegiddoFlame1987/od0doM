# Reguły v2.0: trend światowy, long i short, newsy tylko do wyjścia

Data zamrożenia: 2026-10-09
Tryb: wyłącznie paper trading (to samo konto Alpaca paper co v1.1, osobne tickery, osobny budżet).
Chodzi równolegle z v1.1. Jeden eksperyment nie dotyka pozycji drugiego.

## 1. Cel

Sprawdzić dwie rzeczy osobno:
1. Czy podążanie za trendem (long i short) na aktywach z silnymi trendami światowymi daje lepszy stosunek wyniku do obsunięcia niż kup i trzymaj.
2. Czy filtr newsów, który może tylko wyłączać pozycję, zmniejsza obsunięcie bez utraty wyniku.

## 2. Aktywa

| Ticker | Temat |
|---|---|
| QQQ | AI i big tech |
| URA | uran, energia jądrowa |
| ITA | zbrojenia |
| INDA | Indie |
| COPX | miedź, elektryfikacja |
| IBIT | bitcoin |

Rozłączne z v1.1 (USO, SMH, DBA, GLD, TLT).

## 3. Budżet

50 000 USD z konta paper, ok. 8 333 USD na aktywo, pełne sztuki w dół. Reszta konta należy do v1.1.

## 4. Mechanizm

| Krok | Kiedy (ET) | Co |
|---|---|---|
| Trend | pierwszy przebieg w tygodniu, okno 08:00–09:20 | dla każdego aktywa: wczorajsze zamknięcie > SMA200 → cel LONG, < SMA200 → cel SHORT, brak 200 sesji historii → brak pozycji |
| Filtr ryzyka | codziennie w tym samym oknie | Claude dostaje nagłówki z 24 h i kierunek pozycji. Odpowiada tylko NISKIE / WYSOKIE. WYSOKIE = pozycja zamknięta i zablokowana do następnego sprawdzenia trendu |
| Zlecenia | aukcja otwarcia 09:30 | tylko różnica między celem a stanem. Odwrócenie kierunku w dwóch sesjach: dziś zamknięcie, jutro nowa pozycja |

Filtr może tylko wyłączyć pozycję. Nigdy jej nie włącza i nie zmienia kierunku. Błąd modelu lub feedu = brak sygnału, pozycja bez zmian.

Decyzja dnia (cele, ryzyko, plan) jest zapisana w `data_v2/dni/` zanim poleci jakiekolwiek zlecenie.

## 5. Koszty

0,05% na wejście i 0,05% na wyjście (w symulacji). Na koncie paper wynik liczony z cen wypełnienia.

## 6. Benchmarki

| Wariant | Definicja |
|---|---|
| v2 | trend L/S + filtr newsów (to, co faktycznie wykonano) |
| Cień | sam trend L/S bez filtra, liczony na tych samych cenach |
| Kup i trzymaj | wszystkie 6 aktyw LONG od pierwszego dnia |

Metryka: wynik łączny, maksymalne obsunięcie, stosunek wynik / obsunięcie.

## 7. Backtest

Przed startem na żywo: sam trend (bez newsów, bez LLM) na cenach od 2016. Trzy wiersze: trend L/S, trend tylko long, kup i trzymaj. Jeśli trend nie bije kup i trzymaj w stosunku wynik / obsunięcie, filtr newsów nie ma czego poprawiać.

Uwaga zapisana z góry: aktywa wybrano w 2026 jako "trendy światowe", czyli z wiedzą o przeszłości. Backtest jest przez to zawyżony. To test odrzucenia, nie dowód.

## 8. Bramka

| Etap | Warunek | Decyzja |
|---|---|---|
| Backtest | trend L/S lub trend long ma lepszy stosunek wynik / obsunięcie niż kup i trzymaj | inaczej: teza o trendzie odrzucona, v2 zatrzymane przed startem |
| Po 26 tygodniach na żywo | filtr: obsunięcie v2 < obsunięcie cienia **i** wynik v2 ≥ wynik cienia − 1 pp | inaczej filtr do usunięcia |
| Po 26 tygodniach na żywo | trend: stosunek wynik / obsunięcie lepszy niż kup i trzymaj | inaczej teza o trendzie odrzucona |

## 9. Zamrożenie

- Żadnych zmian w `config_v2.py`, `prompts/risk_v2.0.txt` ani w tym pliku w trakcie testu.
- Każda zmiana = nowa wersja (v2.1, v3.0) i licznik od 0.
- Pomysły na zmiany trafiają na listę do następnej wersji, nie do kodu.

## 10. Prawdziwe pieniądze

Tylko po spełnieniu bramki 26 tygodni i jako osobna decyzja. Kwota stała, ustalona z góry, z twardym stop-lossem na całości. Strata nie zmienia nic w życiu.
