# NF Dyżury dla Windows

Samodzielna aplikacja okienkowa generująca raport dyżuru na podstawie
publicznych tekstów i komentarzy z Fantastyka.pl. Nie wymaga konta NF, hasła,
bota Discord ani serwera.

## Pobranie

Gotowy plik Windows znajduje sie w zakladce
[Releases](https://github.com/melendur88/nf-dyzury-app/releases). Pobierz
`NF-Dyzury.exe` z najnowszej wersji i uruchom go. Python nie jest potrzebny.

Windows moze pokazac ostrzezenie SmartScreen, poniewaz aplikacja nie ma jeszcze
platnego podpisu kodu. Pobieraj plik wylacznie z Releases tego repozytorium.

## Użycie

1. Uruchom `NF-Dyzury.exe`.
2. Podaj dokładny nick użytkownika NF.
3. Podaj miesiąc w formacie `RRRR-MM`.
4. Zaznacz dni tygodnia, w których użytkownik miał dyżur.
5. Kliknij `Generuj raport`.
6. Kliknij `Kopiuj wynik`, aby wkleić raport na Discordzie lub forum.

Komentarz zalicza tekst, jeśli jego widoczna treść ma co najmniej 10 słów.
Nagłówek profilu i sygnatura nie są liczone. Własne jawne teksty użytkownika
są pomijane. Dyżur jest zaliczony, gdy użytkownik skomentował co najmniej 50%
tekstów zbiorczo w całym miesiącu, w swoich dniach dyżuru.
Do puli trafiają wyłącznie opowiadania i szorty. Drabble, wiersze, fragmenty
oraz pozycje oznaczone na NF jako konkursowe są wykluczane. Długość tekstu
musi być mniejsza niż 80 000 znaków; tekst mający dokładnie 80 000 znaków też
nie jest liczony.

Format i reguły pojedynczego raportu są zgodne z botem Discord. Aplikacja
Windows celowo nie generuje zbiorczego raportu wszystkich dyżurnych.

## Zbudowanie EXE

Na komputerze z Windows 10 lub 11:

1. Zainstaluj Python 3.12 z <https://www.python.org/downloads/windows/>.
2. W instalatorze zaznacz `Add python.exe to PATH`.
3. Kliknij dwukrotnie `build.bat`.
4. Gotowy plik znajdziesz jako `dist\NF-Dyzury.exe`.

Do korzystania z gotowego EXE Python nie jest potrzebny. Mozna przekazac sam
plik `NF-Dyzury.exe` dowolnej osobie.

## Wydania

GitHub Actions buduje testy na Windows przy kazdym pushu i pull requescie.
Tag w formacie `v*`, np. `v1.0.0`, buduje `NF-Dyzury.exe` i publikuje go jako
asset GitHub Release.

## Koszt i prywatność

Aplikacja działa lokalnie i odpytuje wyłącznie publiczne strony NF. Nie wysyła
danych do żadnego własnego serwera i nie przechowuje loginów ani haseł. Koszt
hostingu wynosi zero.
