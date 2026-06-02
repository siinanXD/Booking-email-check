# Full MVP – Verifikations-Checkliste

## Qualitäts-Gate

```bash
pytest -q
ruff check .
black --check .
mypy .
```

## MVP-Schritt 2 (Klassifikation · Extraktion · Validierung · Offline-Eval)

| Check | Befehl / Artefakt |
|-------|-------------------|
| Python 3.11 only | `requires-python = ">=3.11,<3.12"` in `pyproject.toml` |
| Few-Shots Extract | `prompts/booking/examples/extract_examples.json` |
| Offline-Eval Mock (CI) | `pytest tests/eval/test_offline_eval.py -v -s` |
| Offline-Eval Live (lokal) | `EVAL_LLM_MODE=live pytest tests/eval/ -m live_eval -v -s` |
| Eval-Doku | `tests/eval/README.md` – Mock = Verdrahtung, Live = Qualität |
| Kosten pro Mail | `observability/mail_cost.py`, `finalize` in `EmailWorkflow.run` finally |
| Grounding-Alert Negativ | `tests/test_alerts.py::test_no_grounding_alert_when_grounded` |
| Spam + finalize | `tests/test_workflow.py::test_workflow_finalize_cost_after_spam_discard` |

Neue Eval-Fälle: nur `tests/eval/cases.json` ergänzen (`expected_extraction`).

## Weitere Schritte

| Schritt | Tests |
|---------|-------|
| 1 Ingestion/Triage | `test_ingestion.py`, `test_triage.py` |
| 3 Workflow/Retrieval | `test_workflow.py`, `test_retrieval.py` |
| 4 Draft/Grounding | `test_grounding.py`, `test_response_generation.py` |
| 5 Index/Vector | `test_indexing.py`, `test_similarity_search.py` |

Integration (Mongo live): `pytest -m integration` (skip ohne `MONGODB_URI`).
