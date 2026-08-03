# CONTRIBUTING.md — Booking-email-check

## Einrichten

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -e .[dev]
cp .env.example .env          # Werte eintragen
cd frontend && npm install
```

## Vor jedem Commit

```bash
ruff check .
ruff format --check .
python -m mypy .
python -m pytest -q
cd frontend && npm test
```

## Branches und Commits

Konventionen: `C:\Dev\AI-Workspace\shared-rules\GIT_CONVENTIONS.md`.

- Nicht direkt auf `main` committen. Fuer jede Aenderung ein eigener Branch.
- Commit-Nachrichten im Conventional-Commits-Format: `feat:`, `fix:`,
  `docs:`, `refactor:`, `test:`, `chore:`.
- Kein Force-Push auf geteilte Branches.

## Was einen Beitrag brauchbar macht

- Eine Aenderung pro Commit. Ein Diff, der drei Dinge gleichzeitig tut, laesst
  sich weder pruefen noch zurueckrollen.
- Kein Formatierungslauf ueber fremden Code im selben Commit wie eine
  inhaltliche Aenderung.
- Neue Abhaengigkeiten nur mit einem Satz Begruendung in der Commit-Nachricht.
- Was du nicht sicher weisst, schreibst du als `TODO:` mit konkreter Frage —
  nicht als plausibel klingende Vermutung.

## Fuer KI-Werkzeuge

`AGENTS.md` lesen, dann `C:\Dev\AI-Workspace\shared-rules\AI_TOOL_RULES.md`. Agentenlaeufe gehoeren in einen eigenen
Branch oder Worktree, nie in den Hauptarbeitsbaum.
