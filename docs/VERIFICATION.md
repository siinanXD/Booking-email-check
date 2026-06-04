# Full MVP – Verifikations-Checkliste

## Qualitäts-Gate

```bash
.\.venv\Scripts\activate   # Windows
pytest -q
ruff check .
black --check .
mypy .
cd frontend && npm test && npm run build
python scripts/check_max_file_lines.py
```

## MVP-Schritt 2 (Klassifikation · Extraktion · Validierung · Offline-Eval)

| Check | Befehl / Artefakt |
|-------|-------------------|
| Python 3.11 only | `requires-python = ">=3.11,<3.12"` in `pyproject.toml` |
| Few-Shots Extract | `prompts/booking/examples/extract_examples.json` |
| Offline-Eval Mock (CI) | `pytest tests/eval/test_offline_eval.py -v -s` |
| Offline-Eval Live (lokal) | `EVAL_LLM_MODE=live pytest tests/eval/test_offline_eval.py -v -s --no-cov` |
| Eval-Doku + 10 Fälle | `tests/eval/README.md`, `tests/eval/cases.json` |
| Kosten pro Mail | `observability/mail_cost.py`, `finalize` in `EmailWorkflow.run` finally |
| Grounding-Alert Negativ | `tests/test_alerts.py::test_no_grounding_alert_when_grounded` |
| Spam + finalize | `tests/test_workflow.py::test_workflow_finalize_cost_after_spam_discard` |
| Triage-Gate / kein classify bei Verwurf | `tests/test_triage.py`, `tests/test_workflow.py::test_workflow_skips_classify_llm_on_unknown_discard` |
| Triage-Kosten-Doku | `docs/COST_TRIAGE.md` |

Neue Eval-Fälle: nur `tests/eval/cases.json` ergänzen (`expected_extraction`).

## MVP-Schritt 3 (Retrieval · Review)

| Check | Tests |
|-------|-------|
| Entity Resolution | `tests/test_entity_resolution.py` |
| Retrieval + leer-Alert | `tests/test_retrieval.py`, `tests/test_alerts.py::test_retrieval_empty_alert` |
| Review-Persistenz / Resume | `tests/test_review_repository.py`, `tests/test_workflow.py` |
| Tenant-Isolation | `tests/test_tenant_isolation.py` |

## MVP-Schritt 4 (Antwort · Grounding · Feedback)

| Check | Tests / Artefakt |
|-------|------------------|
| Grounding Detail (Nr., Name, Datum) | `tests/test_grounding.py` |
| Response Generation | `tests/test_response_generation.py` |
| Edit-Distanz + Langfuse Score | `tests/test_review_feedback.py` |
| Admin LLM-Config + Preview-Fehler | `tests/web/test_admin_llm_config.py` |
| Prompt-Historie | `tests/web/test_admin_llm_config.py` (prompt-history) |

## MVP-Schritt 5 (Index · Vektorsuche)

| Check | Tests / Config |
|-------|----------------|
| Indexing | `tests/test_indexing.py` |
| Similarity (Memory vs Atlas) | `tests/test_similarity_search.py` |
| Atlas optional | `SIMILARITY_USE_ATLAS` in `.env.example`; Index `embedding_vector_index` in `AGENTS.md` |
| Similarity in Retrieval | `tests/test_retrieval.py` (similar_cases) |

## Mandanten-Workflows

| Check | Tests |
|-------|-------|
| Tenant CRUD / Preview / Tests | `tests/web/test_tenant_workflows.py` |
| Admin pro Mandant | `tests/web/test_admin_account_workflows.py` |
| Live-Routing Pipeline | `tests/test_tenant_workflow_live.py` |

## Integration (live MongoDB, optional)

```bash
set MONGODB_URI=mongodb+srv://...
pytest -m integration -v
```

| Test | Datei |
|------|-------|
| Ping | `tests/test_integration_mongo.py` |
| Embedding upsert + search | `tests/test_integration_embeddings.py` |

## Staging-Checkliste (Owner)

1. Atlas: Vector-Index `embedding_vector_index` anlegen (1536 für `text-embedding-3-small`).
2. `SIMILARITY_USE_ATLAS=true` setzen und eine Mail durch die Pipeline laufen lassen.
3. Langfuse: Trace + `log_score` nach Review-Freigabe prüfen (`AdminObservabilityPage`).
4. Manueller Smoke: `flask run` + `npm run dev` → Mail ingestieren → Review-Queue → Freigabe.

## Weitere Schritte (Kurzreferenz)

| Schritt | Tests |
|---------|-------|
| 1 Ingestion/Triage | `test_ingestion.py`, `test_triage.py` |
| Outlook / Graph | `test_outlook_graph.py` (live_graph separat) |
