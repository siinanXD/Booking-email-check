# AI Email Processing Platform

Automatisierte Verarbeitung eingehender E-Mails: Klassifikation, Extraktion,
Wissensspeicherung und Antwortentwurf mit menschlicher Freigabe. Erste Domäne
ist die Buchungswelt (Airbnb, Booking.com, Expedia, VRBO, Direktbuchung); das
System ist über austauschbare **Domänen-Packs** auch für andere Branchen wie
E-Commerce-Bestellungen oder Support ausgelegt.

> Diese README ist für Menschen. Die operativen Regeln für KI-Coding-Agenten
> stehen in `AGENTS.md` (Repo-Kontext) und in `.cursor/` (Cursor-spezifisch).
> Architektur: `docs/SPEC.md` · Kickoff-Checkliste: `docs/KICKOFF.md`.
> Sie wird hier bewusst nicht wiederholt, um Doppelpflege zu vermeiden.

## Was das System tut

Eingehende Mails durchlaufen zwei getrennte Flüsse. Im **Antwort-Fluss** wird
eine Mail klassifiziert, ihre Daten extrahiert und validiert, relevante
Historie abgerufen und ein Antwortentwurf erzeugt – der Entwurf geht immer in
eine **menschliche Freigabe**, nie direkt an den Gast. Parallel läuft im
Hintergrund der **Indexierungs-Fluss**, der Chunks, Embeddings und Entitäten
speichert, ohne den Antwortpfad zu verlangsamen. Ein vorgeschaltetes
**Triage-Gate** sortiert Spam und irrelevante Mails günstig aus, bevor ein
teures Modell überhaupt anläuft.

## Technologie

Python 3.11, LangGraph (zustandsbehafteter Workflow mit Human-in-the-Loop),
OpenAI Embeddings, MongoDB Atlas (Dokumente, Vektor- und Hybrid-Suche),
Langfuse (Observability), Pydantic (Datenmodelle), PyTest, Docker.

## Schnellstart

Voraussetzungen: Python 3.11, Docker, ein MongoDB-Atlas-Cluster sowie API-Keys
für OpenAI und Langfuse.

1. Repository klonen und ins Verzeichnis wechseln.
2. Virtuelle Umgebung anlegen und Abhängigkeiten installieren:
   `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
3. `.env` aus `.env.example` erzeugen und die Keys eintragen. **Keine Secrets
   committen** – `.env` steht in `.gitignore`.
4. Git-Hooks aktivieren (einmalig):
   `pre-commit install && pre-commit install --hook-type commit-msg`
5. Tests laufen lassen: `pytest -q`.

## Konfiguration (Environment-Variablen)

Alle Secrets ausschließlich über Umgebungsvariablen, nie im Code. Erwartet
werden u. a. `OPENAI_API_KEY`, `MONGODB_URI`, `LANGFUSE_PUBLIC_KEY`,
`LANGFUSE_SECRET_KEY`. Die vollständige Liste steht in `.env.example`.

## Qualitäts- und Sicherheitsschichten

Das Projekt sichert Codequalität und Git-Disziplin auf mehreren Ebenen ab, die
absichtlich ineinandergreifen. Es hilft, sie als Kette von der schnellsten und
billigsten bis zur unumgehbaren Schranke zu verstehen.

Wenn das Projekt in **Cursor** bearbeitet wird, formatiert der
`afterFileEdit`-Hook jede vom Agenten geänderte Python-Datei sofort mit Ruff
und Black, und der `beforeShellExecution`-Hook blockiert einen versehentlichen
Direkt-Push auf `main`. Das ist die erste, sofort wirksame Ebene.

Beim eigentlichen Commit greift das **pre-commit-Framework**: Ruff, Black und
MyPy müssen durchlaufen, und Commitizen erzwingt das Conventional-Commit-Format
der Nachricht. Schlägt etwas fehl, entsteht gar kein Commit. Das ist günstiger,
als die CI rot werden zu lassen.

Die **CI** (GitHub Actions, `.github/workflows/ci.yml`) fährt dieselben Checks
serverseitig erneut – als Backstop für den Fall, dass lokal jemand die Hooks
mit `--no-verify` umgangen hat. Über die Branch-Protection von `main` ist der
Merge an eine grüne CI gebunden; das ist die unumgehbare Schranke.

Nach dem Merge auf `main` erzeugt der **Release-Workflow**
(`.github/workflows/release.yml`) mit python-semantic-release automatisch die
nächste Version, den Git-Tag und das Changelog – abgeleitet aus den
Conventional Commits. Deshalb sind diese Commit-Typen Pflicht und nicht bloß
Stilfrage: `fix:` ergibt einen Patch, `feat:` eine Minor, `BREAKING CHANGE`
eine Major.

## Git-Workflow

Arbeite auf Feature-Branches und committe in kleinen, atomaren Schritten.
`main` ist geschützt; der Weg dorthin führt ausschließlich über einen Pull
Request mit grüner CI. Force-Push auf `main` ist gesperrt.

## Projektstruktur

```
routers/        Eingänge (z. B. Outlook-Ingestion)
services/       Geschäftslogik (Klassifikation, Extraktion, Retrieval, ...)
repositories/   Datenzugriff (MongoDB Atlas)
models/         Pydantic-Datenmodelle
schemas/        Domänen-Pack-Schemata (Booking, später Orders, ...)
workflows/      LangGraph-Workflow und Nodes
prompts/        Prompt-Templates und Few-Shot-Beispiele
observability/  Langfuse-Anbindung, Alerts
config/         Einstellungen, Environment-Handling
tests/          Unit-, Integrations-, Edge-Case-, Sicherheits-Tests
utils/          Hilfsfunktionen
```

## Eine neue Branche (Domänen-Pack) hinzufügen

Die Engine bleibt unverändert. Ein neues Pack besteht aus einer
Klassifikations-Taxonomie, einem Pydantic-Extraktionsschema mit Few-Shot-
Beispielen, den Entitätstypen samt Auflösungsregeln und den Prompt-Templates.
Es wird ergänzt, ohne Engine oder `AGENTS.md` anzufassen.

## Tests

`pytest -q` für den vollen Lauf. Die Suite deckt Unit-Tests (Klassifikation,
Extraktion, Retrieval, Prompting, Antwortgenerierung, Datenmodelle),
Integrationstests entlang der Pipeline, Edge Cases (leere Mail, kaputtes HTML,
fehlende Felder, Doppelbuchung, unbekannte Plattform/Sprache) sowie
Sicherheits- und Kostentests ab.

## Sicherheit und Datenschutz

API-Keys nur über Environment-Variablen; keine Secrets im Repository; keine
personenbezogenen Daten im Logging. Vor dem Tracing in Langfuse werden
PII maskiert. Für die DSGVO-konforme Löschung gilt: Daten werden über MongoDB,
den Vektorindex **und** die Traces hinweg entfernt.
