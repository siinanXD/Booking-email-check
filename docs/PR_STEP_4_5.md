# PR: MVP Schritt 4–5 + Mandanten-Workflows

**Branch:** `feat/mvp-step-4-5-generation-vector` → `main`  
**Kein direkter Push auf `main`** – Merge über GitHub-PR.

## Zusammenfassung

Dieser PR liefert MVP-Schritte 4 und 5 aus `docs/SPEC.md` sowie die Mandanten-Workflow-Plattform (Sandbox, Live-Routing, Admin-Verwaltung):

| Block | Inhalt |
|-------|--------|
| **Schritt 4** | Grounding `check_with_detail` (Buchungsnr., Gastname, Datum), `ReviewFeedbackTracker` + Langfuse-Scores, Prompt-Templates |
| **Schritt 5** | `SimilaritySearchService` (In-Memory + optional Atlas), Indexing-Fehlerbehandlung, `similarity_top_k` in Admin-LLM-Config |
| **Workflows** | `tenant_workflows` CRUD, KI-Vorschläge, Preview, Test-Gate vor Live; Pipeline-Routing in [`pipeline.py`](../backend/ai/workflows/nodes/pipeline.py); Plattform-Admin unter `/admin/workflows` |
| **Admin** | LLM-Config mit Prompt-Overrides und Historie, Observability/Kosten, Triage-LLM-Gate |

**Custom-Workflows:** Nach erfolgreicher Validierung endet der Graph (`after_validate` → `end` wenn `workflow_id` gesetzt). `draft_prompt` und Review für Custom-Mails sind **bewusst nicht** in diesem PR.

## Akzeptanzkriterien

### Schritt 4 (Antwortgenerierung)

- [x] **Grounding:** `check_with_detail` + Tests in `tests/test_grounding.py`
- [x] **Edit-Distanz:** `ReviewFeedbackTracker` + `tests/test_review_feedback.py`
- [x] **Langfuse-Scores:** `LangfuseTracer.log_score` bei Freigabe

### Schritt 5 (Vektorsuche)

- [x] **SimilaritySearchService:** `use_atlas` / `SIMILARITY_USE_ATLAS` in Settings
- [x] **Retrieval:** `similar_cases` in `RetrievalService.retrieve`
- [x] **Tests:** `tests/test_similarity_search.py`, `tests/test_indexing.py`

### Mandanten-Workflows

- [x] Tenant-API `/api/workflows` + Admin `/api/admin/accounts/<id>/workflows`
- [x] Live-Routing: `WorkflowRouter` + `TenantWorkflowExecutor`
- [x] Enable-Gate: alle Test-Mails grün vor `enabled` + `sandbox_only=false`
- [x] Web-Tests: `tests/web/test_tenant_workflows.py`, `tests/web/test_admin_account_workflows.py`
- [x] Unit/Live-Pipeline: `tests/test_tenant_workflow_live.py`

### Qualitäts-Gate (CI)

- [x] `pytest -q` (Mock-LLM, mongomock)
- [x] `ruff check .`, `black --check .`, `mypy .`
- [x] Frontend: `npm test`, `npm run build`
- [x] `python scripts/check_max_file_lines.py`

## Was CI **nicht** prüft (nur lokal / Staging)

| Check | Befehl |
|-------|--------|
| Live-Eval (OpenAI-Kosten) | `set EVAL_LLM_MODE=live` → `pytest tests/eval/ -m live_eval -v -s --no-cov` |
| Mongo Integration | `set MONGODB_URI=...` → `pytest -m integration -v` |
| Atlas Vector Index | Index `embedding_vector_index` in Atlas UI; `SIMILARITY_USE_ATLAS=true` |
| Langfuse Live-Traces | Gültige Langfuse-Keys in `.env` |

## Testplan (Review)

```bash
.\.venv\Scripts\activate
pytest -q
pytest tests/eval/test_offline_eval.py -v -s
ruff check . && black --check . && mypy .
cd frontend && npm test && npm run build
```

Optional Integration:

```bash
set MONGODB_URI=mongodb+srv://...
pytest -m integration -v
```

## PR erstellen / mergen

```bash
git push -u origin feat/mvp-step-4-5-generation-vector
```

Auf GitHub: **Compare & pull request** → `main` ← `feat/mvp-step-4-5-generation-vector`.  
Titel-Vorschlag: `feat: MVP steps 4–5, tenant workflows, and admin platform`.  
Beschreibung: Abschnitte aus diesem Dokument übernehmen. Nach grüner CI mergen (Squash oder Merge-Commit).

Release: Conventional Commits auf `main` triggern [`.github/workflows/release.yml`](../.github/workflows/release.yml) (SemVer + `CHANGELOG.md`).

## Nach dem Merge (Owner)

- [ ] Live-Eval-Baseline lokal fahren und in `tests/eval/README.md` oder PR-Kommentar notieren
- [ ] Atlas-Index anlegen und `SIMILARITY_USE_ATLAS=true` in Staging testen
- [ ] `pytest -m integration -v` mit `MONGODB_URI`
- [ ] Einmaliger End-to-End-Smoke: Ingest → Review → Freigabe → Langfuse
