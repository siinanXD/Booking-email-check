# AI Email Processing Platform

Automatisierte Verarbeitung eingehender E-Mails: Klassifikation, Extraktion,
Wissensspeicherung und Antwortentwurf mit menschlicher Freigabe. Erste Domäne
ist die Buchungswelt (Airbnb, Booking.com, Expedia, VRBO, Direktbuchung); das
System ist über austauschbare **Domänen-Packs** auch für andere Branchen wie
E-Commerce-Bestellungen oder Support ausgelegt.

Die Plattform läuft als **Multi-Tenant-SaaS**: Mandanten registrieren sich,
richten das Postfach im Onboarding ein, und ein Hintergrund-Worker holt Mails
periodisch ab.

> Diese README ist für Menschen. Operative Regeln für KI-Agenten: `AGENTS.md`.
> Architektur im Detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) ·
> fachliche Spezifikation: [`docs/SPEC.md`](docs/SPEC.md) ·
> Kickoff: [`docs/KICKOFF.md`](docs/KICKOFF.md).

## Überblick

![Multi-Tenant-Plattform](docs/images/saas-platform.svg)

| Komponente | Rolle |
|------------|--------|
| **React-Dashboard** | Login, Mail-Onboarding, Review-Queue, KPIs, Kosten |
| **Flask-API** | JWT, Mandanten-Scope, REST — kein Auto-Versand |
| **LangGraph / LLM** | Triage, Klassifikation, Extraktion, Antwortentwurf |
| **Mail-Poll-Worker** | Periodischer Abruf für alle aktiven Mandanten |
| **MongoDB Atlas** | Dokumente, Vektoren, Review-Status |

## Was das System tut

Eingehende Mails durchlaufen zwei getrennte Flüsse. Im **Antwort-Fluss** wird
eine Mail klassifiziert, ihre Daten extrahiert und validiert, relevante
Historie abgerufen und ein Antwortentwurf erzeugt – der Entwurf geht immer in
eine **menschliche Freigabe**, nie direkt an den Gast. Parallel läuft im
Hintergrund der **Indexierungs-Fluss**, der Chunks, Embeddings und Entitäten
speichert, ohne den Antwortpfad zu verlangsamen. Ein vorgeschaltetes
**Triage-Gate** sortiert Spam und irrelevante Mails günstig aus (Regeln + optional
kleines Modell für unbekannte Absender), bevor classify/extract laufen. Details:
[`docs/COST_TRIAGE.md`](docs/COST_TRIAGE.md). Postfach-Sync liest nur die **INBOX**.

![E-Mail-Pipeline](docs/images/email-pipeline.svg)

## Architektur im Repository

Geschichtetes Backend und feature-basiertes Frontend — Import-Regeln und
Dateigrößen-Limit (max. 300 Zeilen) sind in der Architektur-Doku festgehalten.

![Backend-Schichten](docs/images/architecture-layers.svg)

```
booking-email-checl/
├── backend/                 # Python-Anwendung
│   ├── api/                 # HTTP (Flask, Auth, Blueprints, Schemas)
│   ├── ai/                  # LangGraph, LLM-Services, Prompts, Domäne
│   ├── features/            # Mail, Benachrichtigungen, Plattform
│   ├── infrastructure/      # Repositories, Adapter, Observability
│   ├── core/                # Config, Modelle, Utils
│   └── application/         # Ingestion- & Review-Ports
├── frontend/                # React + Vite + TypeScript
│   └── src/
│       ├── app/             # Router-Einstieg
│       ├── features/        # Screens pro Fachbereich
│       ├── lib/             # API-Clients, Typen
│       ├── shared/          # Layout, UI-Komponenten
│       └── routes/          # Guards (Auth, Platform-Admin)
├── scripts/                 # CLI, Backfills, Wartung
├── tests/                   # Pytest (Unit, Web-API, Integration)
└── docs/                    # SPEC, ARCHITECTURE, Outlook, Langfuse, …
```

**Neuen Code ablegen:** siehe Tabelle in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#where-to-put-new-code).

## Technologie

| Bereich | Stack |
|---------|--------|
| Backend | Python 3.11, Flask, LangGraph, Pydantic, PyTest |
| KI | OpenAI (Klassifikation, Extraktion, Embeddings, Draft) |
| Daten | MongoDB Atlas (Dokument + Vektor/Hybrid) |
| Observability | Langfuse |
| Frontend | React, TypeScript, Vite, Zustand, Tailwind |
| Betrieb | Railway, Docker Compose, Gunicorn, GitHub Actions CI |

## Schnellstart

Voraussetzungen: Python 3.11, Node.js 20 (für das Dashboard), Docker optional,
MongoDB Atlas sowie API-Keys für OpenAI und Langfuse.

1. Repository klonen und ins Verzeichnis wechseln.
2. Virtuelle Umgebung anlegen und Abhängigkeiten installieren:

   ```bash
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```

   Windows (PowerShell): `.venv\Scripts\Activate.ps1` statt `source`.

3. `.env` aus `.env.example` erzeugen und Keys eintragen. **Keine Secrets
   committen** — `.env` steht in `.gitignore`. Die App lädt `.env` immer aus dem
   **Projektroot**.
4. Git-Hooks (einmalig):

   ```bash
   pre-commit install && pre-commit install --hook-type commit-msg
   ```

5. Tests: `pytest -q` · Zeilenlimit: `python scripts/check_max_file_lines.py`

### Web-API (Dev)

```powershell
python scripts/seed_admin.py
flask --app backend.api.app:create_app run --debug --port 5000
```

Optional: `pip install langgraph-checkpoint-mongodb==0.1.4` für durable
LangGraph-Checkpoints in Mongo. Sonst `WEB_USE_MEMORY_CHECKPOINTER=true` nur
für Tests.

API: `GET /health`, `POST /api/auth/login`, geschützte Routes unter
`/api/dashboard`, `/api/emails`, `/api/review`, `/api/costs`, `/api/mail`, …

### React-Dashboard (Dev)

Zwei Terminals: Flask (Port 5000) und Vite (Port 5173). Vite proxied `/api`
und `/health` zum Backend.

```powershell
# Terminal 1 – Backend (Projektroot, .venv aktiv)
python scripts/seed_admin.py
flask --app backend.api.app:create_app run --debug --port 5000

# Terminal 2 – Frontend
cd frontend
npm ci
npm run dev
```

Browser: `http://localhost:5173` — Login mit `ADMIN_EMAIL` / `ADMIN_PASSWORD`
aus `.env` (nach `seed_admin.py`).

Frontend-Tests: `cd frontend && npm test`.

### Outlook-Ingestion (optional)

Siehe [`docs/OUTLOOK.md`](docs/OUTLOOK.md). Unter Windows die **Projekt-venv**
nutzen:

```powershell
.\scripts\run_outlook_ingest.ps1
```

Einzelmandant-Debug: `INGEST_ACCOUNT_ID` in `.env` setzen.

### Automatisches Mail-Polling

Der Poll-Worker holt periodisch Mails für **alle freigegebenen Mandanten**
(`active`) mit abgeschlossenem Onboarding.

**Docker (Produktion)** — Web, Mongo und Poll-Worker:

```powershell
docker compose up -d
```

Intervall: `MAIL_POLL_INTERVAL_SECONDS=300` (Standard: 5 Minuten).

**Lokal (Windows, Dev)**:

```powershell
.\scripts\run_mail_poll_loop.ps1
```

Einmaliger Lauf: `.\scripts\run_mail_poll.ps1`

### LLM-Modus und Hilfsskripte

| Variable | Wirkung |
|----------|---------|
| `LLM_MODE=live` | Echte OpenAI-API |
| `LLM_MODE=mock` | Platzhalter ohne API-Kosten (nur Dev) |

- `python scripts/diagnose_env.py` — geladene `.env`-Pfade und Modellnamen
- `python scripts/test_live_openai.py` — Smoke-Test Embedding + Workflow
- `python scripts/check_booking_mails.py` — letzte Buchungs-Mails in MongoDB

Langfuse: [`docs/LANGFUSE.md`](docs/LANGFUSE.md).

### Railway (Cloud-Deployment)

Die App läuft produktiv auf [Railway](https://railway.app). `railway.toml` und
`Procfile` liegen bereits im Repo — ein Push auf `main` löst den Deploy aus.

**Voraussetzungen:**
- Railway-Account + neues Projekt → "Deploy from GitHub Repo"
- MongoDB Atlas Cluster (Railway hat kein eigenes Mongo)

**Environment Variables im Railway-Dashboard setzen:**

| Variable | Wert |
|----------|------|
| `OPENAI_API_KEY` | OpenAI API Key |
| `MONGODB_URI` | Atlas-Connection-String |
| `FLASK_SECRET_KEY` | `openssl rand -hex 32` |
| `ADMIN_EMAIL` | Admin-Login-Mail |
| `ADMIN_PASSWORD` | Starkes Passwort |
| `LANGFUSE_PUBLIC_KEY` | Langfuse Key |
| `LANGFUSE_SECRET_KEY` | Langfuse Secret |
| `APP_ENV` | `production` |
| `FLASK_ENV` | `production` |
| `CORS_ORIGINS` | Railway-URL, z. B. `https://myapp.up.railway.app` |
| `OUTLOOK_OAUTH_REDIRECT_URI` | `https://myapp.up.railway.app/api/mail/outlook/callback` |
| `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` | Azure App-Registrierung |
| `WEB_USE_MEMORY_CHECKPOINTER` | leer lassen (auto: `false` in production) |

**Admin-Account anlegen (einmalig nach erstem Deploy):**

```bash
# Railway CLI installieren: npm install -g @railway/cli
railway login
railway run python scripts/seed_admin.py
```

**Deployed URL** → Railway Dashboard → Settings → Domains.

---

### Production (Docker + Gunicorn)

Multi-Stage-Image: React-Build + Gunicorn auf Port **8000**.

```powershell
docker compose up --build
```

- UI + API: `http://localhost:8000`
- Atlas: `MONGODB_URI` in `.env`; optionalen `mongo`-Service in Compose weglassen
- Start: `scripts/seed_admin.py`, wenn `ADMIN_EMAIL` / `ADMIN_PASSWORD` gesetzt
- Lokal ohne Docker: `pip install -e ".[prod]"` und
  `gunicorn -c gunicorn.conf.py wsgi:app` (nach `npm run build` in `frontend/`)

Dashboard-KPI „Eingegangen“ zählt nach `received_at`. Review zeigt
LLM-Entwürfe (Testmodus, **kein Versand**). Optional Backfill:

```powershell
python scripts/fix_noise_intents.py
python scripts/backfill_mail_metrics.py
python scripts/backfill_review_drafts.py
```

## Konfiguration

Secrets nur über Umgebungsvariablen. Vollständige Liste: `.env.example`
(u. a. `OPENAI_API_KEY`, `MONGODB_URI`, `LANGFUSE_*`, `LLM_MODE`,
`FLASK_SECRET_KEY`, `MAIL_POLL_INTERVAL_SECONDS`).

Modelle (Beispiel): `OPENAI_MODEL_CLASSIFY` / `EXTRACT` = `gpt-4o-mini`,
`OPENAI_MODEL_DRAFT` = `gpt-5-mini` oder `gpt-4o-mini`. Bei `gpt-5-*` entfällt
`temperature` automatisch (API-Vorgabe).

## Qualitätssicherung

| Ebene | Was passiert |
|-------|----------------|
| **Cursor-Hooks** | Format nach Edit; Push auf `main` blockiert |
| **pre-commit** | Ruff, Black, MyPy, Conventional Commits |
| **CI** | Dieselben Checks in GitHub Actions (`.github/workflows/ci.yml`) |
| **Release** | semantic-release auf `main` → Version, Tag, Changelog |

Frontend in CI: `npm ci`, `npm test`, `npm run build`.

## Git-Workflow

Feature-Branches, kleine Commits (`feat:`, `fix:`, `chore:`). `main` ist
geschützt; Merge über Pull Request mit grüner CI. Kein Force-Push auf `main`.

## Domänen-Pack hinzufügen

Die Engine bleibt unverändert. Ein neues Pack bringt Taxonomie, Extraktionsschema,
Entitätstypen und Prompts unter `backend/ai/domain/` und `backend/ai/prompts/` —
ohne `AGENTS.md` oder die Schichten-Regeln zu brechen.

## Tests

`pytest -q` — Unit, Pipeline, Edge Cases, Sicherheit/Kosten, Web-API unter
`tests/web/`. Marker: `integration`, `live_eval`, `live_graph` (siehe
`pyproject.toml`).

## Sicherheit und Datenschutz

Keine Secrets im Repo; PII vor Langfuse maskieren; **kein automatischer
Mailversand**. DSGVO-Löschung über MongoDB, Vektorindex und Langfuse-Traces.

## Dokumentation

| Datei | Inhalt |
|-------|--------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layern, Imports, Entrypoints |
| [`docs/SPEC.md`](docs/SPEC.md) | Fachliche Spezifikation |
| [`docs/OUTLOOK.md`](docs/OUTLOOK.md) | Microsoft Graph / Ingestion |
| [`docs/LANGFUSE.md`](docs/LANGFUSE.md) | Tracing und Observability |
| [`docs/GEMINI.md`](docs/GEMINI.md) | Gemini Multimodal (Workflow-Sandbox) |
| [`docs/images/`](docs/images/) | Architektur-Diagramme für diese README |
