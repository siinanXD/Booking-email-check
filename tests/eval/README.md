# Offline-Evals (MVP Schritt 2)

Fälle liegen nur in `cases.json`. Neue anonymisierte Mails = neuer JSON-Eintrag,
kein Code-Change nötig.

## Modi (`EVAL_LLM_MODE`)

| Modus | Default | Bedeutung |
|-------|---------|-----------|
| `mock` | ja (CI) | Misst **Pipeline-Verdrahtung** (MockLLM → Parser → Feldvergleich). **Nicht** die Extraktionsqualität des echten Modells. |
| `live` | nein | Misst **Extraktions-/Klassifikationsqualität** mit OpenAI (`OPENAI_API_KEY` Pflicht). |

```bash
# CI / Regression Verdrahtung
pytest tests/eval/test_offline_eval.py -v -s

# Live (lokal, nicht in CI)
set EVAL_LLM_MODE=live
pytest tests/eval/ -m live_eval -v -s --no-cov
```

`pyproject.toml` schließt `live_eval` per Default aus (`addopts = -m "not live_eval"`).

## Schema `cases.json`

- `expected_intent`: Slug aus Booking-Taxonomie
- `expected_extraction`: nur zu prüfende Felder (exakter Feld-für-Feld-Vergleich)
- optional: `expect_validation_valid`: true/false

## Ausgabe

Trefferquote in der Konsole, z. B.:

`OFFLINE_EVAL mode=mock note=wiring_regression field_accuracy=1.00 ... case_hit_rate=1.00 ...`

## Schwellwert (nur Mock)

`EVAL_MIN_CASE_RATE=1.0` (Default) – unterhalb schlägt pytest fehl.
