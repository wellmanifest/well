# Centrum Zasad i Onboardingu (Governance & Onboarding Hub)

[![Purpose: Governance](https://img.shields.io/badge/Purpose-Governance_%26_Policy-blue.svg)](#)
[![AI Agent Ready](https://img.shields.io/badge/AI_Agents-Ready-success.svg)](#)

Repozytorium `wellmanifest/new-project` stanowi wyłączne, oficjalne źródło polityk bezpieczeństwa, procedur pracy oraz uniwersalnych narzędzi automatyzujących dla ludzi oraz autonomicznych agentów AI.

> **UTRZYMANIE HUBA (`P-CORE-007`):** Niniejsze repozytorium jest edytowalnym
> źródłem standardu. Każda wieloetapowa zmiana standardu musi odbywać się w
> `wellmanifest/new-project` i być przypisana do dokładnie jednego ticketu
> `project/ticket-{NNN}` z zatwierdzonym `intent.json`. Tickety i logi dotyczące
> nowego systemu (System X) powstają wyłącznie w jego osobnym repozytorium.

---

## 1. Struktura Drzewa Plików Repozytorium Docelowego

```text
DOCELOWE REPOZYTORIUM SYSTEMU X (Root)
├── .env.example                 <-- (Szablon konfiguracji: DEFAULT_AGENT)
├── .env                         <-- (Lokalna konfiguracja uaktualniona z .env.example)
├── README.md                    <-- (Główne Menu Całego Projektu)
├── VERSION                      <-- (Wersja główna projektu, np. 0.1.0)
├── CHANGELOG.md                 <-- (Główny rejestr zmian projektu)
├── TODO.md                      <-- (Główna checklista kroków i zadań)
├── Dockerfile & compose.yml     <-- (Odizolowane środowisko kontenerowe)
├── project.sh / project.bat     <-- (Fail-closed governance gate; opcjonalna analiza w przypiętym obrazie)
│
└── project/                     <-- (Katalog zarządzania ticketami)
    ├── README.md                <-- (Opcjonalny plik generatora analizy; scaffolder go nie nadpisuje)
    ├── TICKETS.md               <-- (Indeks ticketów zarządczych)
    ├── readme.sh                <-- (Skrypt aktualizujący project/TICKETS.md)
    ├── new-ticket.sh            <-- (Skrypt generujący strukturę nowego ticketu)
    │
    └── ticket-001/              <-- (Podkatalog Konkretnego Ticketu)
        ├── README.md            <-- (Cel, zakres, status i kryteria odbioru ticketu)
        ├── user-{NAME}.md       <-- (Opcjonalne notatki utworzone przez człowieka/trusted intake)
        ├── preprompt.md         <-- (Wyciągnięte wytyczne z notatek & ustrukturyzowany workflow)
        ├── intent.json          <-- (Maszynowy, zatwierdzany zakres dozwolonych zmian)
        ├── ai-{PROVIDER}.md     <-- (MÓZG AGENTA: rozumienie intencji, plan, Kryteria Odbioru)
        ├── ai-{PROVIDER}-logs.txt <-- (Dedykowany plik surowych logów tego agenta)
        └── changelog.md         <-- (Lokalny rejestr zmian dotyczący tylko tego ticketu)
```

---

## 2. Chronologia i Wynikanie ("Co z Czego Wynika")

Realizacja każdego zadania w docelowym repozytorium odbywa się według ściśle określonej kolejności:

1. **Wyszczególnienie Wymagań (`USER_REQUEST`)**
   * 1.1. Człowiek przekazuje inicjujące notatki, wytyczne i polecenie biznesowe.

2. **Inicjalizacja Korzenia Projektu (Root Level Bootstrap)**
   * 2.1. Tworzony jest plik konfiguracji `.env` (na bazie `.env.example`).
   * 2.2. Tworzone są pliki bazowe: `README.md` (Master Menu), `VERSION`, `CHANGELOG.md`, `TODO.md` oraz kontener `Dockerfile`/`compose.yml`.

3. **Inicjalizacja Katalogu `project/`**
   * 3.1. Tworzony jest `project/TICKETS.md` (indeks ticketów), `project/readme.sh` oraz `project/new-ticket.sh`. Istniejący `project/README.md` pozostaje własnością jego generatora.

4. **Wywołanie Skryptu `new-ticket.sh` (`project/ticket-{NNN}/`)**
   * 4.1. Skrypt tworzy `README.md`, `preprompt.md`, jawnie typowany `ai-{AGENT}.md`, pusty log agenta i `changelog.md`.
   * 4.2. Skrypt nie tworzy `user-*` ani tożsamości człowieka. Taki plik może utworzyć wyłącznie jego ludzki właściciel lub zaufana granica intake.
   * 4.3. Generator odmawia drugiego aktywnego ticketu w tym samym workstreamie albo przy nierozstrzygniętym workstreamie. Równoległy ticket wymaga jawnie innego workstreamu; ostateczny overlap sprawdza walidator.

5. **Ekstrakcja Wytycznych (`preprompt.md`)**
   * 5.1. Agent AI analizuje tylko istniejące, human-owned notatki `user-{NAME}.md` i zapisuje własne rozumienie w `ai-{AGENT}.md`. Brak człowieka pozostaje `unresolved:human`.

6. **Generowanie Mózgu AI (`ai-{AGENT}.md`) oraz Harmonogramu (`TODO.md`)**
   * 6.1. Z pliku `preprompt.md` Agent generuje plik `ai-{AGENT}.md` (MÓZG AI), zawierający rozumienie intencji, koncepcję architektury, zakres i **Kryteria Odbioru (Acceptance Criteria)**.
   * 6.2. Agent wpisuje listę zadań wykonawczych do głównego pliku `TODO.md`.

7. **Wstrzymanie Pracy i Akceptacja Planu (`P-CORE-008`)**
   * 7.1. Agent zatrzymuje przerwane kodowanie i przedstawia plik `ai-{AGENT}.md` oraz checklistę w `TODO.md` Użytkownikowi do weryfikacji.
   * 7.2. Pisanie kodu rozpoczyna się wyłącznie po wyraźnej zgodzie Użytkownika.

8. **Kodowanie, Logowanie i Rejestr Zmian**
   * 8.1. Podczas wykonania Agent zapisuje surowe wyjścia z terminala i testów do pliku `ai-{AGENT}-logs.txt`.
   * 8.2. Po zakończeniu etapu Agent uzupełnia `project/ticket-{NNN}/changelog.md`, odznacza pozycje w `TODO.md`, a po wyznaczeniu wydania aktualizuje zbiorczy `CHANGELOG.md` i podbija `VERSION`.

---

## 3. Specyfikacja Plików i Kontrakty (DSL)

| Plik | Rola i Specyfikacja Kontraktu |
| :--- | :--- |
| **`.env.example`** | **Szablon Konfiguracji**: definiuje domyślnego agenta (`DEFAULT_AGENT="antigravity"`); nie materializuje ludzi z konfiguracji. |
| **`user-{NAME}.md`** | **Kontekst Człowieka**: ręczne, human-owned instrukcje i decyzje z jawnym `participant-id`, rolą, ticketem i typowanymi sekcjami. Agent nie tworzy ani nie edytuje tego pliku. |
| **`preprompt.md`** | **Ustrukturyzowany Workflow**: przetworzone wytyczne z plików `user-*.md` ze zdefiniowanymi krokami wykonawczymi. |
| **`ai-{AGENT}.md`** | **Mózg Agenta AI**: rozumienie intencji, zakres prac, specyfikacja techniczna i Kryteria Odbioru (AC). |
| **`ai-{AGENT}-logs.txt`** | **Dedykowane Logi**: wyłączne surowe wyjścia komend CLI i testów uruchamianych przez danego agenta. |
| **`changelog.md`** | **Lokalny Changelog**: wykaz zmian i edycji wykonanych wyłącznie w ramach danego ticketu. |
| **`project/TICKETS.md`** | **Indeks Ticketów**: centralny plik nawigacyjny indeksujący tickety bez nadpisywania analitycznego `project/README.md`. |

---

## 4. Interfejs CLI Skryptów Automatyzujących

### Skrypt `new-ticket.sh`
Automatyzuje tworzenie struktury nowego ticketu bez przejmowania ludzkiej
tożsamości i bez zapisywania kodu wykonywalnego w katalogu ticketu.

```bash
# Użycie podstawowe z jawnym workstreamem z manifestu
./project/new-ticket.sh --title "Implementacja Walidacji" --workstream "application"

# Użycie z jawnym agentem; --users jest tylko wejściem kompatybilności i nie
# tworzy plików człowieka
./project/new-ticket.sh --title "Naprawa Błędu" --agent "codex" --workstream "application"

# Niezależny ticket równoległy
./project/new-ticket.sh --title "SDK klienta" --agent "codex-2" --workstream "interfaces"
```

### Skrypt `readme.sh`
Skanuje katalog `project/` i atomowo aktualizuje spis ticketów w
`project/TICKETS.md`. Brak markerów lub próba wyjścia poza `project/` kończy się
błędem.

```bash
# Aktualizacja indeksu w project/TICKETS.md
./project/readme.sh
```

### Deterministyczny governance gate

Wersja 0.9.0 dodaje zwalnianie rezerwacji przez `BACKLOG`, `PLAN` i `BLOCKED`,
jawnie zaufanych reviewerów oraz fixture'y regresyjne dla kolejek workstreamów.
Wersja 0.8.0 dodała workstreamy, intent v2, graf zależności, konflikty,
integrację i bezkolizyjną pracę równoległą do manifestu policy-as-code, locka
SHA-256, stabilnych diagnostyk `GOV-*` i reusable CI. Walidator blokuje
implementację bez jednoznacznego ticketu, stanu `EDIT`, dozwolonego zakresu i —
w trybie PR — zewnętrznej zgody. Szczegóły opisuje
[`docs/GOVERNANCE_ENFORCEMENT.md`](docs/GOVERNANCE_ENFORCEMENT.md).
Kontrakty adopcji są publikowane jako `governance/manifest.schema.json`,
`governance/intent.schema.json` i `governance/lock.schema.json`.

Opublikowaną rewizję adoptuje się bez ręcznego kopiowania i liczenia hashy:

```bash
python3 /path/to/new-project/scripts/create_adoption_lock.py \
   --target-root /path/to/target-repository \
   --source-revision <FULL_PUBLISHED_SHA>
```

Generator czyta artefakty bezpośrednio z obiektu Git, odmawia nadpisania
różniących się plików i wymaga świadomego `--upgrade` przy aktualizacji.
Istniejące projekty korzystające z `goal` mogą wykonać tę samą adopcję przez
`goal governance adopt`; preflight, retrofit i upgrade opisuje
[`docs/GOAL_ADOPTION.md`](docs/GOAL_ADOPTION.md).

Bieżący stan prac, bramy publikacji, pilotażu i szerszej adopcji opisuje
[`docs/ROADMAP_AFTER_0.9.0.md`](docs/ROADMAP_AFTER_0.9.0.md).

---

## 5. Zasada Odbioru Planu przed Kodowaniem (`P-CORE-008`)

Przed rozpoczęciem edycji plików źródłowych w nowym systemie Agent AI **musi**:
1. Wygenerować plik `ai-{PROVIDER}.md` oraz uzupełnić `TODO.md`.
2. Przedstawić Użytkownikowi oba te dokumenty do wglądu.
3. Uzyskać wyraźną akceptację (`"Zgoda"`, `"Plan zatwierdzony"`) przed przejściem do fazy wykonawczej.

### 5.1. Zasada Kontynuacji Aktywnego Ticketu (`P-CORE-009` / `C-TICKET-008`)
Dla kolejnych promptów i poprawek w ramach tego samego workstreamu i zakresu Agent AI **nie tworzy nowego ticketu**.
* Agent wykorzystuje ponownie pasujący aktywny katalog `project/ticket-{NNN}/` i aktualizuje swój plik planu `ai-{PROVIDER}.md` oraz `TODO.md`.
* Odrębny aktywny ticket jest dozwolony tylko w innym workstreamie, bez nakładania zakresu zapisu; każdy branch/PR musi należeć do dokładnie jednego ticketu.
* Tylko status `IN_PROGRESS` jest aktywny. `BACKLOG`, `PLAN` i `BLOCKED`
   zachowują kontekst, ale zwalniają rezerwację workstreamu i ścieżek.
* **Agentowi zabrania się modyfikowania plików notatek człowieka (`user-{github_username}.md`)**.

---

## 6. Przewodnik i Zasady Pracy (Opis w Języku Naturalnym)

*Poniższy opis stanowi przystępną wykładnię zasad zawartych w ścisłych plikach polityk [POLICY.md](POLICY.md) oraz [CONTRIBUTING.md](CONTRIBUTING.md). Jeśli formuła DSL w plikach jest dla kogoś trudna do zinterpretowania, ten przewodnik służy jako oficjalne wyjaśnienie.*

### 6.1. Hierarchia Ważności Źródeł Prawdy
W przypadku wystąpienia konfliktu informacji obowiązuje następująca kolejność ważności:
1. **Bezpośrednie polecenie użytkownika (`USER_REQUEST`)** – najwyższy autorytet.
2. **Aktualny stan plików w docelowym repozytorium (`FILESYSTEM`)**.
3. **[POLICY.md](POLICY.md)** – bezwzględne zasady i zakazy bezpieczeństwa.
4. **[CONTRIBUTING.md](CONTRIBUTING.md)** – procedura pracy i maszyna stanów.
5. **README.md / Historia Git** – informacje pomocnicze i kontekstowe.

---

### 6.2. System Ticketów (`project/ticket-{NNN}` w Docelowym Repozytorium)
* **Wymóg zakładania**: Każde zadanie składające się z więcej niż 1 kroku lub wymagające użycia Agenta AI **musi** posiadać swój folder pod `project/ticket-{NNN}` w repozytorium, którego dotyczy zmiana: w `wellmanifest/new-project` dla utrzymania standardu albo w repozytorium docelowym dla Systemu X.
* **Indeks projektu (`project/TICKETS.md`)**: Służy jako menu nawigacyjne do ticketów z linkami do dokumentacji i uczestników; nie koliduje z artefaktami analizy w `project/README.md`.
* **Mózg Agenta (`ai-{AGENT}.md`)**: Definiuje rozumienie intencji, plan, ryzyka i kryteria odbioru widziane przez danego agenta. Nie zastępuje polecenia ani decyzji człowieka; rozbieżności muszą pozostać widoczne.
* **Pliki uczestników (`user-mateusz.md`, `user-tom.md`)**: Ręczne notatki człowieka wklejane przy każdym zleceniu jako stały kontekst.
* **Logi (`ai-{AGENT}-logs.txt`)**: Wyłączne surowe wyjścia z konsoli i testów wykonywanych przez danego agenta.
* **Granica implementacji**: Katalog ticketu przechowuje governance, decyzje, logi i dowody. Kod, testy oraz skrypty badawcze trafiają do zwykłych katalogów repozytorium.
* **Brak odbiorcy**: Wymagana odpowiedź bez zaufanego uczestnika używa `unresolved:human` lub `unresolved:agent`; pusta lista i zgadywanie tożsamości są zabronione.
* **Retencja (Nie wolno usuwać ticketów!)**: Foldery ticketów są trwale zachowywane w docelowym repozytorium. Agentom **nie wolno ich usuwać**, chyba że po zakończonym projekcie użytkownik wyraźnie wyda takie polecenie.

---

### 6.3. Bezpieczeństwo i Dobre Praktyki (`POLICY.md`)
* **Weryfikacja faktów**: Twierdzenia bez dowodów (np. "test przeszedł" bez uruchomienia komendy) są zabronione.
* **Ochrona sekretów**: Klucze API, tokeny i hasła nie mogą trafić do repozytorium ani logów.
* **Czyszczenie ścieżek**: W komitach i logach używamy ścieżek względnych. Zabronione jest wyciekanie lokalnych ścieżek bezwzględnych użytkownika (`C:/Users/...`).
* **Higiena kontekstu**: Wczytywanie dużych plików i logów odbywa się fragmentami (`head`, `tail`, paginacja), aby nie zapychać okna kontekstowego Agenta AI.
* **Zakaz niszczących komend**: Operacje takie jak `force push`, czyszczenie historii czy niezweryfikowane skasowanie plików wymagają zgody człowieka.

---

### 6.4. Wymagania Środowiskowe (Docker i Narzędzia)
* Każdy tworzony system **musi** być budowany i uruchamiany w odizolowanym środowisku **Docker** (`Dockerfile`, `compose.yml`).
* `project.sh` / `project.bat` najpierw uruchamia deterministyczny governance gate. Analiza jest opcjonalna i może ruszyć dopiero w obrazie Docker przypiętym pełnym digestem SHA-256 przez `NEW_PROJECT_ANALYSIS_IMAGE`.

| Narzędzie | Krótki Opis i Przeznaczenie |
| :--- | :--- |
| **`todo2code`** | Narzędzie konwertujące checklisty i pliki TODO na wykonywalne prompty oraz kod dla agentów (`https://github.com/semcod/todo2code`). |
| **`code2llm`** | Pakuje kod źródłowy i strukturę projektu w zoptymalizowany format dla modeli AI/LLM. |
| **`redup`** | Skaner wykrywający powtórzenia i redundancje w kodzie źródłowym. |
| **`prefact`** | Automatyczne przygotowanie refaktoryzacji oraz analiza zależności w kodzie. |
| **`doql`** | Generowanie podsumowań strukturalnych i relacyjnych projektu (`app.doql.less`). |
| **`sumd` / `sumr`** | Generowanie automatycznych raportów ze struktur repozytorium. |
| **`goal`** | Weryfikacja celów projektowych i zgodności ze specyfikacją wymagań. |
| **`vallm`** | Moduł semantycznej walidacji i wsadowego przetwarzania kontekstu dla agentów LLM. |

---

### 6.5. Maszyna Stanów (Przepływ Pracy)
Praca nad każdym zadaniem w docelowym repozytorium przechodzi przez cykl stanów:
`START` ➔ `ANALYSIS` ➔ `PLAN` ➔ `WAIT_FOR_APPROVAL` ➔ `TOOLS` ➔ `DELEGATION` ➔ `EDIT` ➔ `VALIDATION` ➔ `PUBLICATION` ➔ `DONE` (lub `BLOCKED` w przypadku braku dowodów/blokady).

---

## 7. Indeks Dokumentów Zarządczych i Skryptów

| Dokument / Skrypt | Rola i Opis |
| :--- | :--- |
| **[POLICY.md](POLICY.md)** | Ścisłe zasady bezpieczeństwa, zakazy i limity (MODE STRICT). |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | Procedura pracy, tickety, Docker i maszyna stanów (MODE PROCEDURAL). |
| **[AGENTS.md](AGENTS.md)** | Standardowy punkt wejścia dla agentów AI (Cursor, Claude Code, Antigravity itp.). |
| **[llms.txt](llms.txt)** | Mapa dokumentacji dla modeli LLM. |
| **[project.sh](project.sh)** / **[project.bat](project.bat)** | Fail-closed wejście: najpierw governance gate, potem opcjonalna analiza w obrazie przypiętym digestem. |
| **[template/](template/)** | Czyste szablony dla ticketów i wpisów uczestników. |
