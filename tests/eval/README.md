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

## Eval-Fälle (Stand)

`cases.json` enthält **10** anonymisierte Fälle (`eval-001` … `eval-010`), u. a.:

| ID | Intent | Schwerpunkt |
|----|--------|-------------|
| eval-001 | new_booking | Daten + Gästezahl |
| eval-002 | cancellation | Buchungsnummer |
| eval-006 | change | Check-in-Verschiebung |
| eval-008 | guest_inquiry | Relay-Absender |
| eval-009 | complaint | Gastname + Buchungsnr. |
| eval-010 | new_booking | Direktbuchung |

Neue Produktionsmails: JSON-Eintrag ergänzen, Mock-Lauf grün halten, dann optional Live-Baseline.

## Live-Baseline (Owner, lokal)

Nach Änderungen an Prompts oder `cases.json`:

```bash
set EVAL_LLM_MODE=live
set OPENAI_API_KEY=sk-...
pytest tests/eval/test_offline_eval.py -v -s --no-cov
```

Ergebnis (z. B. `field_accuracy`, `case_hit_rate`) hier oder im PR-Kommentar festhalten.
**Mock=1.0** bedeutet nicht, dass Live=1.0 ist — Live misst Modellqualität.

### Live-Baseline (2026-06-22, `gpt-4o-mini`, 10 Fälle)

| Metrik | Wert |
|--------|------|
| Klassifikation `hit_rate` | 1.00 (10/10) |
| Extraktion `field_accuracy` | 1.00 (23/23 Felder) |
| Extraktion `case_hit_rate` | 1.00 (9/9 Fälle mit `expected_extraction`) |

> Die frühere Baseline (2026-06-04: 0.10 / 0.38 / 0.22) war ein veralteter Messstand
> aus einer frühen, defekten Pipeline-Phase und entsprach nicht der Modellqualität.
> Harness verifiziert korrekt (Slug→Enum-Mapping, Feld-für-Feld-Vergleich). Fall
> `eval-010` hatte zudem eine unbegründete `guest_count=2`-Erwartung (Text nennt keine
> Gästezahl) — entfernt.

Lokal ausführen (lädt `.env`):

```bash
.\.venv\Scripts\python.exe -c "from pathlib import Path; from dotenv import load_dotenv; load_dotenv(Path('.env')); import os, subprocess, sys; os.environ['EVAL_LLM_MODE']='live'; subprocess.run([sys.executable,'-m','pytest','tests/eval/test_offline_eval.py','-v'], env=os.environ)"
```
