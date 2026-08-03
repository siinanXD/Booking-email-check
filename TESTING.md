# TESTING.md — Booking-email-check

## Tests ausfuehren

```bash
python -m pytest -q            # Backend
ruff check .
ruff format --check .
python -m mypy .
cd frontend && npm test        # Frontend (vitest)
cd frontend && npm run build
```

## Wo die Tests liegen

`tests/` bildet die Struktur von `backend/` nach (u.a.
`tests/whatsapp_bot/`). Das Frontend testet mit vitest neben dem Quellcode.
Konfiguration von pytest, ruff und mypy steht in `pyproject.toml`.

## Was ein guter Test hier leistet

Ein Test taugt nur, wenn er rot wird, sobald die Implementierung falsch ist.
Die Probe aufs Exempel: Waere dieser Test auch dann gruen, wenn die Funktion
Unsinn zurueckgibt? Dann sichert er nichts.

Abgedeckt gehoeren neben dem Normalfall:

- die Randfaelle — leer, null, eins, sehr gross, negativ
- der Fehlerfall — falscher Typ, fehlende Datei, ungueltige Eingabe
- bei wiederholbaren Ablaeufen: derselbe Aufruf zweimal

## Verbindlich

- **Testdaten sind erfunden.** Keine echten Kundennamen, Mailadressen,
  Buchungen oder Zugangsdaten — auch nicht "nur zum Ausprobieren".
- **Kein Test wird abgeschaltet, um eine Pruefung gruen zu bekommen.** Nicht
  mit `skip`, nicht mit `xit`, nicht mit `# noqa`, nicht mit `@ts-ignore`.
  Ein roter Test ist ein Befund, kein Hindernis.
- Ein Fehler bekommt erst einen Test, der ihn reproduziert, dann die Behebung.

## Besonderheit dieses Projekts

**Niemals echte Mails als Testdaten.** Das System verarbeitet personenbezogene
Daten; eine echte Buchungsmail in einer Fixture ist eine Datenpanne mit
Meldepflicht, kein Testdetail. Fixtures werden erfunden.

Wer eine echte Mail zum Nachstellen eines Fehlers braucht, anonymisiert sie
vollstaendig, bevor sie das Repository sieht — Adressen, Namen, Buchungsnummern,
Betraege.
