# Grafiki NF obowiązujące od miesiąca zmiany

Publiczna konfiguracja dyżurnych dla bota na Home Assistant.
Pliki zawierają wyłącznie publiczne nicki NF i dni dyżuru. Nie umieszczaj tu
tokenów, danych Discorda, mapowań Cerberusa ani powodów osobistych zmian.

## Format

Nowy plik `RRRR-MM.yaml` dodajesz tylko wtedy, gdy zmienia się skład lub dni.
Obowiązuje od podanego miesiąca aż do następnej zmiany:

```yaml
month: "2027-01"
dyzurni:
  - name: PrzykladowyNick
    days: [pn, czw]
```

- `month` musi odpowiadać nazwie pliku i oznacza miesiąc wejścia w życie grafiku.
  Nie musi być równy miesiącowi raportu, jeśli skład jest dziedziczony.
- `dyzurni` to niepusta lista: `name` i dni `pn, wt, sr, czw, pt, sob, nd`.
  Kilka dni tej samej osoby wpisuj w jednej pozycji, bez powtarzania nicku.
- Nicki zachowują pisownię z NF. Nie dodawaj danych osobowych ani powiązań kont.
- Grafik za miesiąc miniony nie jest zastępowany grafikiem aktualnym.
  Rzeczywistą korektę historyczną opisuj w commicie.
- Nie ma indeksu do ręcznej aktualizacji. Bot sam odczytuje listę plików
  w katalogu przez publiczne API GitHuba i wybiera najnowszą zmianę nie późniejszą
  niż miesiąc raportu. Grudniowy skład obowiązuje w styczniu i kolejnych
  miesiącach, dopóki nie dodasz nowego pliku. Przyszłe zmiany nie zmieniają
  wcześniejszych raportów.
- `2026-10` pochodzi z historycznego pliku lokalnego, `2026-11` z pliku bazowego.
  Grudzień to plan: dotychczasowy skład bez OldGuard; inne zmiany wymagają
  potwierdzenia. Konfiguracja nie zawiera ani nie pobiera składu Loży.

## Podłączenie bota

Po opublikowaniu grafików w gałęzi `main` ustaw w konfiguracji bota:

```dotenv
DUTY_ROSTER_URL_TEMPLATE=https://raw.githubusercontent.com/melendur88/nf-dyzury-app/main/grafiki/{month}.yaml
```

Bot pobiera listę plików i wybrany grafik przed każdym pełnym raportem. Błąd HTTP
(także limit publicznego API GitHuba), nieprawidłowa lista/YAML, brak grafiku
obowiązującego w danym okresie albo brak wybranego pliku zatrzymują raport. Nie ma zgadywania
składu ani ukrytego powrotu do starszego/lokalnego pliku po błędzie.
Puste ustawienie zachowuje dawny tryb lokalny.

Komenda Discord `/nf-grafik miesiac:2026-12` pokazuje dyżurnych, dni dyżuru
oraz miesiąc wejścia w życie i skrót wersji pobranego pliku.
Wymaga „Zarządzania serwerem”; nie pobiera tekstów NF i nie publikuje na NF.

Nowe pliki nie zmieniają samoczynnie działającego add-onu: pierwsze uruchomienie
wymaga wersji bota z obsługą źródła Git i ustawienia powyższej zmiennej.
Kolejne zmiany plików w Git nie wymagają ponownego wdrażania bota.
