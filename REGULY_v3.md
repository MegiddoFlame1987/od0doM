# Reguły v3.0: day trading long-only na surowcach w trendzie

Data zamrożenia: 2026-10-09
Tryb: wyłącznie paper trading. To samo konto co v1.1, rozłączne tickery, osobny budżet. Chodzi równolegle z v1.1.

## 1. Cel

Sprawdzić, czy agent czytający nagłówki poprawia wynik dziennego "long na surowcu w trendzie" przez wybieranie sesji, w które wchodzi (LONG) albo nie (SKIP).

## 2. Kandydaci

| Ticker | Surowiec |
|---|---|
| SLV | srebro |
| PPLT | platyna |
| CPER | miedź |
| DBB | metale bazowe |
| UNG | gaz ziemny US |
| BNO | ropa Brent |
| WEAT | pszenica |
| CORN | kukurydza |
| SOYB | soja |
| CANE | cukier |

Rozłączne z v1.1 (USO, SMH, DBA, GLD, TLT) i v2 (QQQ, URA, ITA, INDA, COPX, IBIT).

## 3. Uniwersum dnia

Codziennie przed prognozą: surowiec jest "w trendzie", gdy wczorajsze zamknięcie > SMA200. Do gry wchodzi maksymalnie 5 najsilniejszych (zamknięcie / SMA200). Brak surowców w trendzie = dzień pominięty, nie liczy się.

Wybór uniwersum jest mechaniczny i zapisany w logu dnia. Agent nie ma na niego wpływu.

## 4. Budżet

33 333 USD, czyli jedna trzecia konta paper. Ok. 6 666 USD na pozycję, pełne sztuki w dół. v1.1 zostaje przy swoich 50 000 USD; zmiana wielkości nie zmienia wyniku w procentach, a zmiana kodu v1.1 przed sesją 1 to ryzyko bez korzyści.

## 5. Pętla dzienna

| Krok | Czas ET | Co |
|---|---|---|
| Uniwersum i prognoza | 08:00–09:20 | dla każdego surowca w trendzie: nagłówki z 24 h → LONG albo SKIP, pewność 1–5, zapis z godziną |
| Termin | 09:25 | zapis później = sesja niezaliczona |
| Wejście | 09:30 | zlecenie market-on-open tylko dla LONG |
| Zamknięcie | 16:00 | zlecenie market-on-close, składane ok. 15:20 |
| Rozliczenie | po 16:05 | wynik pozycji z cen wypełnienia; dla SKIP zapisana zmiana dnia (otwarcie → zamknięcie) do benchmarków |

Agent nie widzi cen. Dostaje tylko nagłówki i informację, że surowiec jest w trendzie.

## 6. Wynik

```
LONG: wynik = (wyjście − wejście) / wejście − 0,15%
SKIP: wynik = 0
```

Koszt 0,15% zamiast 0,10% z v1.1, bo surowcowe ETF-y mają szersze spready. Sesja z samymi SKIP liczy się jako sesja z wynikiem 0.

## 7. Benchmarki

| Benchmark | Definicja |
|---|---|
| Zawsze LONG | long na każdym surowcu z uniwersum dnia, każdej sesji, po kosztach. To mierzy, ile daje sam trend bez agenta |
| 1000 losowych agentów | moneta LONG / SKIP dla każdej decyzji, te same ceny, ziarno 20261009 |

Agent ma sens tylko wtedy, gdy bije oba.

## 8. Bramka

| Etap | Warunek | Decyzja |
|---|---|---|
| **Kill** po 30 sesjach | agent nie bije 950 z 1000 losowych | zamknij pętlę |
| **Go live** po 60 sesjach | ten sam próg w obu połowach osobno | rozważ live ze stałą kwotą |
| Zawsze | prognoza z godziną przed 09:25 ET, pełne wypełnienia, zmiana dnia dla każdego SKIP | inaczej sesja niezaliczona |

## 9. Zamrożenie

- Żadnych zmian w `config_v3.py`, `prompts/forecast_v3.0.txt` ani w tym pliku w trakcie testu.
- Każda zmiana = nowa wersja (v3.1) i licznik od 0.

## 10. Prawdziwe pieniądze

Tylko po bramce Go live, jako osobna decyzja. Kwota stała, ustalona z góry, bez dokładania, z twardym stop-lossem. Przy małej kwocie strategia wymaga przepisania na ułamki akcji i zlecenia market, czyli innego mechanizmu niż testowany.
