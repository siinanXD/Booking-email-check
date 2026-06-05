# Code Quality Analyse – Booking-email-checl
*Erstellt: 2026-06-05*

---

## 1. Toter Code

> Analyse mit `vulture --min-confidence 60` + manuelle Nachprüfung.  
> False Positives (in Tests/Scripts referenzierte Symbole) wurden herausgefiltert.

### Wirklich ungenutzte Symbole

| Datei | Zeile | Symbol | Typ | Empfehlung |
|---|---|---|---|---|
| `backend/infrastructure/repositories/conversation_repository.py` | 25 | `ConversationRepository` | Klasse | Löschen – nirgendwo importiert oder instanziiert |
| `backend/ai/workflows/email_workflow.py` | 206 | `reject_after_review()` | Methode | Löschen – wird nie aufgerufen |
| `backend/ai/services/entity_resolution.py` | 70 | `EntityMatch.is_match()` | Statische Methode | Löschen – nur definiert, nie genutzt |
| `backend/ai/services/triage.py` | 68 | `_triage_llm_enabled` | Instanzattribut | Löschen – wird gesetzt, aber nie gelesen |
| `backend/features/booking/entity_sync.py` | 19 | `sync_properties_from_extractions()` | Funktion | Löschen – kein Import in anderen Modulen |
| `backend/features/notifications/whatsapp_client.py` | 37 | `MockWhatsAppClient` | Klasse | Löschen oder in `tests/` verschieben |
| `backend/core/models/chunk.py` | 8, 17 | `Chunk`, `Embedding` | Klassen | Datei löschen – wird nie importiert (Repos definieren eigene Strukturen) |
| `adapters/__init__.py` | — | `OutlookGraphClient`, `map_graph_message`, `OutlookIngestionAdapter`, `OutlookIngestionRunner` | Re-Exports via `__all__` | Ordner löschen (siehe Dateibaum) |

---

## 2. PEP8-Verstöße

> Analyse mit `flake8 --exclude=.venv,.cursor,scripts,tests --max-line-length=88`.

**Befund: Nur 3 Verstöße im gesamten Backend – der Code ist sehr sauber.**

| Datei | Zeile | Code | Beschreibung |
|---|---|---|---|
| `backend/api/services/email_queries.py` | 147:31 | E203 | Whitespace vor `:` in Slice |
| `backend/api/services/email_queries.py` | 200:33 | E203 | Whitespace vor `:` in Slice |
| `backend/ai/workflows/email_workflow.py` | 150:89 | E501 | Zeile zu lang (100 > 88 Zeichen) |

**Hinweis zu E203:** Das ist ein bekannter Konflikt zwischen `flake8` und `black`. Black formatiert Slices mit Leerzeichen (`strict[offset : offset + limit]`), flake8 bemängelt es. Ruff (im Projekt konfiguriert) ignoriert E203 korrekt. Kein Handlungsbedarf, solange Ruff das primäre Linting-Tool bleibt.

**Handlungsbedarf:** Nur das E501 in `email_workflow.py` Zeile 150 sollte umgebrochen werden.

---

## 3. Docstrings & Type Hints

### Docstring-Abdeckung (interrogate)

**Gesamtabdeckung: 79,7 %** (803 von 1007 Elementen dokumentiert)

Top 10 Dateien mit den meisten fehlenden Docstrings:

| Datei | Gesamt | Fehlend | Abdeckung |
|---|---|---|---|
| `backend/api/schemas/tenant_workflows.py` | 22 | **17** | 23 % |
| `backend/api/schemas/properties.py` | 15 | **14** | 7 % |
| `backend/api/services/query_service.py` | 11 | **9** | 18 % |
| `backend/api/blueprints/workflows.py` | 11 | **9** | 18 % |
| `backend/api/blueprints/properties.py` | 10 | **9** | 10 % |
| `backend/infrastructure/repositories/support_ticket_repository.py` | 10 | **8** | 20 % |
| `backend/api/services/tenant_workflow_service.py` | 11 | **8** | 27 % |
| `backend/api/services/support_ticket_service.py` | 11 | **8** | 27 % |
| `backend/api/blueprints/support_tickets.py` | 9 | **8** | 11 % |
| `backend/infrastructure/repositories/tenant_workflow_repository.py` | 15 | **7** | 53 % |

Weitere auffällige Dateien (geringe prozentuale Abdeckung):
- `backend/ai/workflows/nodes/pipeline.py` – 7 fehlend (22 %)
- `backend/ai/services/tenant_workflow_runtime.py` – 7 fehlend (36 %)
- `backend/infrastructure/adapters/outlook/graph.py` – 6 fehlend (33 %)

### Type Hints (mypy)

Nur **3 Fehler in 2 Dateien** – alle dieselbe Ursache:

| Datei | Zeile | Fehler |
|---|---|---|
| `backend/core/config/settings.py` | 16 | `Class cannot subclass "BaseSettings" (has type "Any")` |
| `backend/core/config/settings.py` | 217 | `Returning Any from function declared to return "Settings"` |
| `backend/features/platform/effective_settings.py` | 58 | `Returning Any from function declared to return "Settings"` |

**Ursache:** `pydantic-settings` hat zur Analysezeit kein Typ-Stub – `BaseSettings` erscheint als `Any`. Kein Logik-Fehler. Fix: `pip install pydantic-settings[mypy]` oder `# type: ignore[misc]`-Kommentar an Zeile 16.

---

## 4. Dateibaum-Probleme

### Ghost-Ordner (Code migriert, Verzeichnis nicht aufgeräumt)

| Pfad | Problem |
|---|---|
| `web/` | Enthält **keine `.py`-Quelldateien** mehr – nur `__pycache__/` mit alten `.pyc`-Dateien. Code wurde nach `backend/api/` migriert. → Ordner löschen |
| `config/` | Gleiche Situation: nur `__pycache__/` übrig. Code lebt in `backend/core/config/`. → Ordner löschen |

### Top-Level-Stub-Ordner (leere Relikte)

| Pfad | Inhalt | Problem |
|---|---|---|
| `adapters/` | `__init__.py` mit 4 Re-Exports via `__all__` | Niemand importiert aus diesem Top-Level-Paket. Totes Re-Export-Modul. → Löschen |
| `schemas/` | `__init__.py` mit nur einem Modul-Docstring | Vollständig leer, kein Inhalt. → Löschen |
| `services/` | `__init__.py` mit nur einem Modul-Docstring | Vollständig leer, kein Inhalt. → Löschen |

Diese drei Ordner sind Relikte einer früheren Architektur (vor der Konsolidierung in `backend/`). Sie können potenzielle Namenskonflikte mit `backend/infrastructure/adapters/`, `backend/api/schemas/` und `backend/ai/services/` verursachen.

### Fehlende `__init__.py`

| Pfad | Problem |
|---|---|
| `backend/features/support/` | Hat kein `__init__.py` – alle anderen `features/`-Unterverzeichnisse (`booking/`, `mail/`, `notifications/`, `platform/`, `review/`) haben eines. Das Verzeichnis ist kein registriertes Python-Paket. → `__init__.py` hinzufügen |

### Mock-Klassen im Produktionspfad

`backend/ai/services/mock_llm.py` und `backend/ai/services/mock_gemini.py` sind Test-Doubles, die im Produktionscode-Verzeichnis liegen. Besser wäre ein eigener Ordner:
- `backend/ai/testing/mock_llm.py`
- `backend/ai/testing/mock_gemini.py`

(oder direkt in `tests/`)

### Drei konkurrierende `services/`-Ebenen

```
services/                     ← Top-Level-Stub (leer, löschen)
backend/ai/services/          ← 29 Dateien (LLM-Clients, Prompts, KI-Logik)
backend/api/services/         ← 25 Dateien (HTTP-Schicht: Queries, CRUD)
```

Die Trennlinie zwischen `ai/services/` und `api/services/` ist nicht immer klar. Beispiel: `backend/ai/services/triage.py` (KI-Logik) vs. `backend/api/services/query_service.py` (enthält ebenfalls Klassifizierungslogik). Eine klare Konvention wäre hilfreich:
- `ai/services/` = alles was LLM-Aufrufe macht
- `api/services/` = alles was DB-Queries macht und HTTP-Antworten aufbaut

---

## Zusammenfassung & Prioritäten

| Priorität | Maßnahme | Aufwand |
|---|---|---|
| 🔴 Hoch | Ghost-Ordner `web/` und `config/` löschen | 2 min |
| 🔴 Hoch | Leere Top-Level-Ordner `adapters/`, `schemas/`, `services/` löschen | 2 min |
| 🔴 Hoch | `backend/features/support/__init__.py` hinzufügen | 1 min |
| 🟡 Mittel | 8 tote Symbole (Funktionen/Klassen) löschen | 30 min |
| 🟡 Mittel | `backend/core/models/chunk.py` löschen (nie importiert) | 5 min |
| 🟡 Mittel | `mock_llm.py` / `mock_gemini.py` nach `backend/ai/testing/` verschieben | 15 min |
| 🟡 Mittel | Docstrings in Top-10-Dateien ergänzen (Fokus auf `schemas/` und `blueprints/`) | 2–3 h |
| 🟢 Niedrig | E501 in `email_workflow.py` Zeile 150 umbrechen | 1 min |
| 🟢 Niedrig | mypy-Stub für `pydantic-settings` installieren oder `# type: ignore` setzen | 5 min |
