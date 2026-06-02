# PR: MVP Schritt 2 – Klassifikation, Extraktion, Validierung, Offline-Evals

**Branch:** `feat/mvp-step-2-offline-evals` → `main`  
**Kein direkter Push auf `main`** – Merge über GitHub-PR.

## Zusammenfassung

Dieser PR liefert MVP-Schritt 2 aus `docs/SPEC.md`: Booking-Klassifikation und -Extraktion mit Few-Shots, domänen-Validierung, Offline-Eval-Harness (datengetrieben über `cases.json`), aggregierte Kosten pro Mail inkl. Langfuse-Metadatum, sowie Aufräumen aus Schritt 1 (Grounding-Alert-Negativtest, Python-3.11-Konsistenz).

**Wichtig zur Eval:** In CI und bei normalem `pytest -q` laufen die Offline-Evals nur im **Mock-Modus** (`EVAL_LLM_MODE=mock`, Default). Das misst **Pipeline-Verdrahtung**, nicht die Extraktionsqualität des echten Modells. Ein **Live-Lauf** gegen anonymisierte Produktionsmails (`EVAL_LLM_MODE=live` + `OPENAI_API_KEY`) steht noch aus und ist bewusst nicht Teil der Merge-Bedingung.

## Akzeptanzkriterien (Plan Schritt 2)

- [x] **Python 3.11 only:** `requires-python = ">=3.11,<3.12"`; `AGENTS.md` ohne 3.12/3.13-Drift
- [x] **Few-Shots Extraktion:** `prompts/booking/examples/extract_examples.json`, Wiring in `ExtractionService`
- [x] **Validierung:** `ValidationService` im Workflow; Unit-Tests; optional `expect_validation_valid` in Eval-Fällen
- [x] **Offline-Eval Feld-für-Feld:** `tests/eval/compare.py`, `expected_extraction` in `cases.json`, Trefferquote in stdout
- [x] **cases.json migriert:** 5 Fälle, kein `expected_booking_number`
- [x] **Eval Mock/Live-Schalter:** `EVAL_LLM_MODE=mock|live`, Doku in `tests/eval/README.md` und `.env.example`
- [x] **Mock ≠ Qualität:** explizit dokumentiert; Live-Lauf lokal, nicht CI-Default
- [x] **Kosten pro Mail:** `MailCostTracker.add` + ein `finalize` pro Workflow-Lauf (auch Spam/Abbruch vor Draft)
- [x] **Grounding-Alert Negativfall:** gut gegroundet → kein `grounding_suspect`
- [x] **Qualitäts-Gate:** `pytest -q`, ruff, black, mypy grün (41 passed, 1 skipped ohne `MONGODB_URI`)

## Marker-Filter (`addopts = -m "not live_eval"`)

- Schließt **nur** Tests mit Marker `live_eval` aus.
- **`integration`**, unmarkierte Unit-Tests und Offline-Evals (`test_offline_eval.py`) werden weiterhin gesammelt (42 Tests mit und ohne Filter – aktuell **kein** Test trägt `@pytest.mark.live_eval`; Live-Modus wird über `EVAL_LLM_MODE=live` in denselben Eval-Tests geschaltet).
- CI bleibt sicher, solange `EVAL_LLM_MODE` nicht auf `live` gesetzt wird (Default: `mock`).

## Testplan (Review)

```bash
pytest --collect-only -q          # 42 gesammelt
pytest -q                         # 41 passed, 1 skipped (Integration)
pytest tests/eval/test_offline_eval.py -v -s
ruff check . && black --check . && mypy .
```

Optional lokal (nicht für CI-Merge):

```bash
set EVAL_LLM_MODE=live
set OPENAI_API_KEY=...
pytest tests/eval/test_offline_eval.py -v -s
```

Optional Integration:

```bash
set MONGODB_URI=...
pytest tests/test_integration_mongo.py -v
```

## Commits (Branch)

1. `fix: pin Python to 3.11 only across project config`
2. `feat(eval): dual-mode offline eval with field-wise extraction scoring` (+ MVP-Plattform auf dem Branch)

## Nach dem Merge (Owner)

- [ ] Anonymisierte Beispielmails in `tests/eval/cases.json` ergänzen
- [ ] Live-Eval mit `EVAL_LLM_MODE=live` gegen echte Mails auswerten
- [ ] Optional: dedizierte `@pytest.mark.live_eval`-Tests, wenn Live und Mock strikt getrennt werden sollen
