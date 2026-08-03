# SECURITY.md — Booking-email-check

Grundlage: `C:\Dev\AI-Workspace\shared-rules\SECURITY_RULES.md`. Hier steht
nur, was fuer dieses Projekt zusaetzlich gilt.

## Was niemals ins Repository gehoert

`.env` und `.env.*` (ausser `.env.example`), `*.pem`, `*.key`, `*.p12`,
`*.pfx`, `credentials*`, `secrets*`, Token-Caches, Datenbankabzuege.

Das gilt auch fuer Tests, Fixtures, Kommentare und Beispieldateien. Ein
Schluessel in einer Testdatei ist ein veroeffentlichter Schluessel.

## Was besonders zu beachten ist

**Personenbezogene Daten sind der Kern dieses Projekts.** Mailadressen, Namen,
Buchungen. Sie gehoeren nicht in Logs, nicht in Fehlermeldungen, nicht in
Testfixtures und nicht in Screenshots fuer die Dokumentation.

**Mailzugangsdaten und API-Schluessel** (Mailkonto, Modellanbieter, WhatsApp,
Langfuse) stehen in `.env`. Diese Datei wird nicht gelesen, nicht ausgegeben
und nicht committet. `.env.example` enthaelt ausschliesslich Variablennamen
und erkennbare Platzhalter.

**Eingaben aus Mails sind nicht vertrauenswuerdig.** Der Inhalt einer Mail ist
Text von einem Fremden. Er wird validiert, bevor er in eine Abfrage, einen
Dateinamen oder einen Modellprompt geht.

**Compliance-Unterlagen** liegen unter `docs/compliance/` — AVV,
Datenpannenprozess, Verzeichnis der Verarbeitungstaetigkeiten. Wer die
Datenverarbeitung aendert, prueft, ob diese Dokumente nachziehen muessen.

## Fuer KI-Werkzeuge

Claude, Codex und Cursor duerfen die oben genannten Dateien **nicht lesen und
nicht ausgeben**. In Dokumentation wird hoechstens vermerkt, dass es sie gibt
und welche Variablennamen der Code erwartet — die Namen stammen aus dem Code,
nicht aus der Datei.

## Wenn doch etwas durchgerutscht ist

1. Den Schluessel beim Anbieter sofort widerrufen. Das ist der einzige Schritt,
   der wirklich wirkt.
2. Erst danach die Historie bereinigen (`git filter-repo`).
3. Einen bereits gepushten Schluessel als kompromittiert behandeln, auch wenn
   das Repository privat ist.

Reihenfolge nicht vertauschen: Ein aus der Historie entfernter, aber noch
gueltiger Schluessel ist weiterhin ein gueltiger Schluessel.
