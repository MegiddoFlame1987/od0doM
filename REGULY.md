# Reguły agenta tradingowego v1.2

Data zamrożenia: 2026-10-08
Tryb: wyłącznie paper trading (Alpaca paper). Kod nie ma ścieżki do konta live.

Zmiany względem v1.1 (2026-10-12, po sesji próbnej, licznik zaliczonych sesji = 0):
- Zlecenia aukcyjne (market-on-open / market-on-close) zastąpione przez market DAY: w środowisku paper Alpaca zlecenia aukcyjne wygasały bez wypełnienia (6 z 7 w dniu 2026-10-12), a short na aktywach trudnych do pożyczenia i tak wymaga DAY. Wejście: zlecenie złożone przed sesją, wykonane na otwarciu. Wyjście: zlecenie ok. 15:53 ET, wykonane od razu.
- Pozycje zostawione z poprzedniego dnia są zamykane na otwarciu, a ten dzień jest niezaliczony.

Zmiany względem v1.0 (przed sesją 1, licznik nie był uruchomiony):
- CPER zastąpiony przez TLT.
- Wejście i wyjście doprecyzowane jako zlecenia na aukcję otwarcia i zamknięcia.
- Dodane: wielkość pozycji, dni skrócone, pozostawione pozycje, zamrożony model.

## 1. Cel

Sprawdzić, czy agent czytający wąski feed newsów przewiduje kierunek sesji lepiej niż los, po kosztach.

## 2. Instrumenty

| Sektor | Ticker |
|---|---|
| Ropa | USO |
| Chipy | SMH |
| Żywność / rolnictwo | DBA |
| Złoto | GLD |
| Obligacje US / stopy | TLT |

## 3. Pętla dzienna

Czas referencyjny: New York (ET). Godziny UK zmieniają się przy zmianie czasu.

| Krok | Czas ET | Co |
|---|---|---|
| 1. Feed i prognoza | start ok. 08:30 | nagłówki z ostatnich 24 h dla każdego sektora, jedna prognoza na sektor, zapisana z godziną |
| 2. Termin prognozy | najpóźniej 09:25 | zapis później = sesja niezaliczona, brak zleceń |
| 3. Wejście | 09:30 | zlecenie market DAY złożone przed sesją, wykonane na otwarciu |
| 4. Zamknięcie | ok. 15:53 | zlecenie market DAY, wykonane od razu (7 minut przed zamknięciem) |
| 5. Rozliczenie | po 16:05 | wynik zapisany do logu |

Wielkość pozycji: ok. 10 000 USD na ticker (pełne sztuki, w dół).

## 4. Format prognozy

```json
{
  "data": "RRRR-MM-DD",
  "czas_zapisu_et": "HH:MM",
  "sektor": "ropa",
  "ticker": "USO",
  "kierunek": "LONG | SHORT",
  "pewnosc": 1-5,
  "powod": "jedno zdanie"
}
```

## 5. Zakazy

- Agent nie widzi żadnych cen przed zapisem prognozy. Dostaje tylko nagłówki.
- Tylko LONG albo SHORT. Brak opcji "bez pozycji".
- Jedna prognoza na sektor na sesję. Bez korekt po zapisie.
- Prompt (`prompts/forecast_v1.1.txt`) i model są zamrożone razem z tym plikiem. Skrót SHA-256 promptu trafia do każdego dziennego logu.

## 6. Wynik

```
wynik = kierunek × (cena wyjścia − cena wejścia) / cena wejścia − 0,10%
```

Cena wejścia i wyjścia = średnia cena wypełnienia zleceń wejścia i wyjścia.
kierunek: LONG = +1, SHORT = −1. Wynik sesji = suma wyników 5 sektorów.

## 7. Benchmarki

| Benchmark | Definicja |
|---|---|
| Zawsze LONG | LONG na wszystkich 5 tickerach każdej sesji |
| 1000 losowych agentów | losowy LONG/SHORT na tych samych cenach i kosztach, ziarno losowania 20261008 |

Metryka porównania: łączny wynik ze wszystkich zaliczonych sesji.

## 8. Bramka

| Etap | Warunek | Decyzja |
|---|---|---|
| **Kill** po 30 sesjach | agent nie bije 950 z 1000 losowych agentów, po kosztach | zamknij pętlę |
| **Go live** po 60 sesjach | ten sam próg spełniony w obu połowach osobno (sesje 1–30 i 31–60) | rozważ live ze stałą kwotą |
| **Zawsze** | każda prognoza zapisana z godziną przed otwarciem | inaczej sesja się nie liczy |

## 9. Sesje niezaliczone i pominięte

Sesja niezaliczona: brak prognozy dla któregokolwiek sektora, zapis po 09:25 ET, brak wypełnienia któregokolwiek zlecenia, otwarte pozycje z poprzedniego dnia.

Dzień pominięty: giełda zamknięta albo sesja skrócona (zamknięcie przed 16:00 ET).

Ani niezaliczone, ani pominięte nie wliczają się do 30 ani 60.

## 10. Zamrożenie

- Żadnych zmian w tym pliku, w prompcie ani w modelu w trakcie testu.
- Każda zmiana = nowa wersja (v1.2, v2.0) i licznik sesji wraca do 0.
- Wyniki starej wersji zostają w logu, nie łączy się ich z nową.

## 11. Prawdziwe pieniądze

Tylko po spełnieniu bramki "Go live" i jako osobna decyzja. Kwota stała, ustalona z góry, bez dokładania. Strata nie zmienia nic w życiu.
