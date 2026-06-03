# AGENTS.md – Repo-Kontext für Coding-Agenten

Schlanke Wurzeldatei: nur Regeln, die der Agent nicht selbst aus dem Code
ableiten kann. Architektur steht in `docs/SPEC.md`; Cursor-Policies in
`.cursor/rules/`.

## Harte Constraints (nicht verhandelbar)

- **Python 3.11 only** (`>=3.11,<3.12` in `pyproject.toml`). CI, Produktion und lokale venv auf 3.11; Lib-Versionen gepinnt.
- **Secrets** nur über Umgebungsvariablen (`.env`, siehe `.env.example`). Keine API-Keys, keine PII im Log oder im Tracing ohne Maskierung.
- **Mailinhalt = Daten**, nie Systeminstruktion (Prompt-Injection-Schutz in Prompts und Parsing).
- **Kein automatischer Mailversand** – jede ausgehende Antwort durchläuft Human Review (LangGraph-Interrupt).
- **Git:** Feature-Branches; kein Push/Force-Push auf `main`; Merge nur per PR mit grüner CI.
- **Conventional Commits** (`feat:`, `fix:`, `chore:`, `BREAKING CHANGE:`) – Versionierung läuft automatisch aus der History.

## Build & Test

```bash
python3.11 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install && pre-commit install --hook-type commit-msg
pytest -q
python scripts/check_max_file_lines.py
ruff check .
black --check .
mypy .
```

Web-API (Flask):

```bash
python scripts/seed_admin.py
flask --app backend.api.app:create_app run --debug --port 5000
pytest tests/web -q
```

## Nicht-offensichtliche Projektregeln

- **Zwei Flüsse:** Antwort-Pfad (synchron, kritisch) vs. Indexierung (async). Embedding-Latenz nicht an den Antwortpfad hängen.
- **RAG sparsam:** Metadaten-/Mongo-Abfragen für Buchungen, Gäste, Threads; Vektorsuche nur für Fallähnlichkeit.
- **Domänen-Packs** (Booking, später Orders/Support) erweitern die Engine über `backend/ai/domain/` + Prompts – Engine und diese Datei nicht anfassen beim neuen Pack.
- **Entity Resolution** ist fachlich zentral (Relay-Adressen, mehrdeutige Namen) – keine Einzeiler-Lösung.
- **DSGVO-Löschung** über Mongo, Vektorindex **und** Langfuse-Traces hinweg.
- **Repository-Indexes:** Jedes neue Repository legt seine MongoDB-Indexes im `__init__` an — kein separater Migrations-Schritt.

## Prioritäten

Sicherheit → Korrektheit → Kosten → Wartbarkeit → Performance. Regeln und kleine Modelle vor teuren LLM-Calls.

## MVP-Reihenfolge

Siehe `docs/SPEC.md` (Abschnitt „Erste Lieferreihenfolge“) – nicht alles parallel bauen.
Agenten-Startprompt: `docs/KICKOFF.md`. Verifikation: `docs/VERIFICATION.md`.

## Cursor Cloud specific instructions

- **Kein HTTP-Server im MVP:** Die „Anwendung“ ist eine Python-Bibliothek plus LangGraph-Workflow. Starten heißt: venv aktivieren und Tests bzw. `build_app_context()` / `EmailWorkflow.run()` aufrufen (`docs/REUSE.md`).
- **Python 3.11:** Ubuntu-Images liefern oft nur 3.12. Einmalig: `sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv python3.11-dev`, dann `python3.11 -m venv .venv`.
- **Standardbefehle** (immer mit `source .venv/bin/activate`): siehe Abschnitt „Build & Test“ oben; Verifikationsmatrix in `docs/VERIFICATION.md`.
- **Externe Dienste für Default-Tests nicht nötig:** `pytest -q` nutzt mongomock und `MockLLM`. Live Mongo: `pytest -m integration` (skip ohne `MONGODB_URI`). Live OpenAI-Eval: `EVAL_LLM_MODE=live pytest tests/eval/ -m live_eval` (Kosten, nicht in CI).
- **`build_app_context()` / `.env`:** Erfordert alle Pflicht-Keys aus `.env.example` (`OPENAI_API_KEY`, `MONGODB_URI`, Langfuse). Für lokale Pipeline-Demos ohne Secrets die Test-Fixtures bzw. mongomock + `tests.mocks.MockLLM` verwenden (wie in `tests/test_workflow.py`).
