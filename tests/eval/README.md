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

Zwei Sets:
- **`cases.json`** — 10 Verdrahtungs-Fälle (`eval-001…010`). Der `MockLLM` reproduziert
  sie exakt → der Mock-Lauf bleibt das 100 %-Regressions-Gate (CI).
- **`cases_live.json`** — 20 realistische **harte** Fälle (`eval-live-001…020`):
  Beds24/Booking/Airbnb-Relay-Absender, mehrsprachig (IT/FR), generischer `property_name`
  („Zimmer Nummer 3"), informelle Anfragen, Marketing-/Kalender-/Bestell-Mails als `other`,
  fehlende Felder. **Nur im Live-Modus** evaluiert (Mock kann sie nicht erzeugen) — sie
  messen die echte Modellqualität, nicht die Verdrahtung.

Neue Produktionsmails: harten Fall zu `cases_live.json` hinzufügen (Live misst), Verdrahtungs-
Fall zu `cases.json` nur, wenn der `MockLLM` ihn reproduziert (sonst bricht das Mock-Gate).

## Live-Baseline (Owner, lokal)

Nach Änderungen an Prompts oder `cases.json`:

```bash
set EVAL_LLM_MODE=live
set OPENAI_API_KEY=sk-...
pytest tests/eval/test_offline_eval.py -v -s --no-cov
```

Ergebnis (z. B. `field_accuracy`, `case_hit_rate`) hier oder im PR-Kommentar festhalten.
**Mock=1.0** bedeutet nicht, dass Live=1.0 ist — Live misst Modellqualität.

### Live-Baseline (2026-06-23, `gpt-4o-mini`, 30 Fälle = 10 Basis + 20 hart)

| Metrik | Wert |
|--------|------|
| Klassifikation `hit_rate` | 0.93 (28/30) |
| Extraktion `field_accuracy` | 0.99 (80/81 Felder) |
| Extraktion `case_hit_rate` | 0.97 (28/29 Fälle mit `expected_extraction`) |

> Bekannte offene Schwächen (von den harten Fällen aufgedeckt):
> `eval-live-004` informelle Anfrage „Sind noch Zimmer frei?" → Modell `guest_inquiry` statt
> `new_booking`; `eval-live-016` italienische Bestätigung „Prenotazione confermata" → Modell
> `cancellation` statt `new_booking`. Kandidaten für Prompt-/Few-Shot-Verbesserung.
>
> Nur Basis-10 (Stand 2026-06-22): classify 1.00, extraction 1.00 — die alte 2026-06-04-Baseline
> (0.10 / 0.38 / 0.22) war ein veralteter Messstand aus defekter Pipeline-Phase.

> Die frühere Baseline (2026-06-04: 0.10 / 0.38 / 0.22) war ein veralteter Messstand
> aus einer frühen, defekten Pipeline-Phase und entsprach nicht der Modellqualität.
> Harness verifiziert korrekt (Slug→Enum-Mapping, Feld-für-Feld-Vergleich). Fall
> `eval-010` hatte zudem eine unbegründete `guest_count=2`-Erwartung (Text nennt keine
> Gästezahl) — entfernt.

Lokal ausführen (lädt `.env`):

```bash
.\.venv\Scripts\python.exe -c "from pathlib import Path; from dotenv import load_dotenv; load_dotenv(Path('.env')); import os, subprocess, sys; os.environ['EVAL_LLM_MODE']='live'; subprocess.run([sys.executable,'-m','pytest','tests/eval/test_offline_eval.py','-v'], env=os.environ)"
```
