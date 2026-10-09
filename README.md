# Od 0 do milionera

Dwa równoległe eksperymenty na jednym koncie **paper** Alpaca. Rozłączne tickery, rozłączne budżety.

| | v1.1 | v2.0 |
|---|---|---|
| Pomysł | newsy przewidują kierunek sesji | trend wybiera kierunek, newsy tylko wyłączają pozycję |
| Horyzont | 1 sesja | tygodnie (trend sprawdzany raz w tygodniu) |
| Kierunek | LONG / SHORT | LONG / SHORT |
| Aktywa | USO, SMH, DBA, GLD, TLT | QQQ, URA, ITA, INDA, COPX, IBIT |
| Budżet | 50 000 USD | 50 000 USD |
| Reguły | `REGULY.md` | `REGULY_v2.md` |
| Dane | `data/` | `data_v2/` |
| Bramka | 30 / 60 sesji | backtest, potem 26 tygodni |

## v1.1: jak to działa

| Skrypt | Kiedy (ET) | Co robi |
|---|---|---|
| `forecast.py` | ok. 08:30 | nagłówki z Google News → Claude → prognoza → zlecenia na aukcję otwarcia |
| `close.py` | ok. 15:20 | zlecenia na aukcję zamknięcia |
| `settle.py` | ok. 16:30 | ceny wypełnienia → wynik → `data/wyniki.csv` |
| `evaluate.py` | ręcznie | bramka: agent vs zawsze LONG vs 1000 losowych → `data/raport.md` |

Uruchamia GitHub Actions według crona. Każdy dzień to plik `data/dni/RRRR-MM-DD.json` i commit z godziną. Commit jest dowodem, że prognoza powstała przed otwarciem.

## v2.0

| Skrypt | Kiedy (ET) | Co robi |
|---|---|---|
| `run_v2.py` | ok. 08:00–09:20, raz dziennie | pierwszy przebieg w tygodniu: trend SMA200 → cele LONG/SHORT. Codziennie: Claude ocenia ryzyko z nagłówków, WYSOKIE = zamknięcie pozycji do końca tygodnia. Zlecenia na aukcję otwarcia |
| `backtest_v2.py` | ręcznie, workflow "v2 backtest" | sam trend od 2016 vs kup i trzymaj → `data_v2/backtest.md` |
| `evaluate_v2.py` | ręcznie | v2 vs cień bez filtra vs kup i trzymaj → `data_v2/raport.md` |

Backtest uruchom **przed** pierwszym tygodniem: Actions → v2 backtest (ręcznie) → Run workflow. Potrzebuje tylko kluczy Alpaca. Jeśli trend nie bije kup i trzymaj, v2 nie startuje.

## Start: 5 kroków

1. **Alpaca paper:** załóż konto na alpaca.markets, przełącz na *Paper Trading*, wygeneruj klucze API (Key ID + Secret).
2. **Anthropic API:** w console.anthropic.com utwórz klucz API i doładuj małą kwotę.
3. **Repo:** gotowe, `MegiddoFlame1987/od0doM`. Repo jest publiczne: logi i prognozy widzi każdy, klucze są tylko w Secrets.
4. **Sekrety:** w repo *Settings → Secrets and variables → Actions → New repository secret* dodaj trzy:
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET_KEY`
   - `ANTHROPIC_API_KEY`
5. **Test ręczny:** zakładka *Actions → Prognoza i wejście → Run workflow*. Poza oknem 08:00–09:20 ET skrypt tylko wypisze "Poza oknem" i to jest poprawne. Pierwszy prawdziwy przebieg: najbliższy dzień roboczy, sam z crona.

Kluczy nigdy nie wklejaj do kodu ani do czatu.

## Co sprawdzić w pierwszym tygodniu

| Dzień | Sprawdź |
|---|---|
| 1 | w `data/dni/` jest plik z 5 prognozami i 5 pozycjami |
| 1 | w panelu Alpaca paper po 09:30 ET widać 5 pozycji |
| 1 | po 16:30 ET `etap: rozliczona`, `zaliczona: true` |
| 1–5 | godziny startu w *Actions*: czy prognoza zdąża przed 09:20 ET |

Gdy w pliku dnia pojawi się `uwaga: OTWARTE POZYCJE`, zamknij je ręcznie w panelu Alpaca paper. Do tego czasu agent nie handluje.

## Testy offline

```
python -m unittest discover tests
```

Atrapy brokera, modelu i feedu. Pełna sesja, zabezpieczenia, bramka.

## Czego nie wolno w trakcie testu

Zmieniać `config.py`, `config_v2.py`, `prompts/`, `REGULY.md` ani `REGULY_v2.md`. Każda zmiana = nowa wersja i licznik od 0.
