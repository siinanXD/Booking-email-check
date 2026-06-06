# CHANGELOG


## v0.13.4 (2026-06-06)

### Bug Fixes

- Correct frontend static dir path resolution (3 parent levels)
  ([`df55e3f`](https://github.com/siinanXD/Booking-email-checl/commit/df55e3feb4cb348857b745aa5f0fe9d99a231f8f))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.13.3 (2026-06-06)

### Bug Fixes

- Remove startCommand from railway.toml, use Procfile instead
  ([`f303448`](https://github.com/siinanXD/Booking-email-checl/commit/f3034483746dc845c9d6eff8976fbc757cc7b9b2))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- Add railway.toml to build frontend and serve via Flask
  ([`ad5137c`](https://github.com/siinanXD/Booking-email-checl/commit/ad5137c090285414c340e5671a2c2532145833ba))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.13.2 (2026-06-06)

### Bug Fixes

- Correct langgraph-checkpoint-mongodb version constraint
  ([`f1f86e6`](https://github.com/siinanXD/Booking-email-checl/commit/f1f86e64dfbce90dd92802fc41b57e8db9e508d0))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.13.1 (2026-06-06)

### Bug Fixes

- Add langgraph-checkpoint-mongodb dependency for production checkpointer
  ([`1f0b202`](https://github.com/siinanXD/Booking-email-checl/commit/1f0b20204ea3fe545d7f55898001fdbbe3389d51))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- Add Procfile for Railway deployment
  ([`d875567`](https://github.com/siinanXD/Booking-email-checl/commit/d875567c556815984c8b584d2c7eba6a4d49cf42))

Gunicorn listens on Railway-injected $PORT (0.0.0.0).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.13.0 (2026-06-05)

### Features

- **ocr**: Paddleocr als Gemini-Fallback für Workflow-Vorschläge aus Bildern
  ([`a0ab755`](https://github.com/siinanXD/Booking-email-checl/commit/a0ab755c28e790e4aff7a02154ffc2329adabd30))

- ocr_service.py: optionaler PaddleOCR-Wrapper (graceful import, kein Crash ohne Dep) -
  tenant_workflow_suggest_ocr.py: Bild → OCR-Text → OpenAI-Suggest-Pfad - suggest_workflow:
  bevorzugt Gemini, fällt auf PaddleOCR zurück wenn verfügbar - GeminiStatusResponse: neues Feld
  ocr_available für Frontend-Feedback - WorkflowEditorAssistCard: zeigt OCR-Info statt Fehler wenn
  PaddleOCR installiert - pyproject.toml: optionale [ocr]-Gruppe + scripts-mypy-Override erweitert -
  fix(mypy): type-ignore-Codes in scripts/setup_atlas_vector_index.py korrigiert - Weitere offene
  Items: CLAUDE.md, rate_limit, EmailDetailSideCard, Security-Tests, Load-Tests, E2E-Tests, diverse
  Frontend- und Backend-Verbesserungen

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.12.0 (2026-06-05)

### Bug Fixes

- **booking**: Mongomock-safe count query + PMS subject overrides LLM other
  ([`534ff47`](https://github.com/siinanXD/Booking-email-checl/commit/534ff474ce36a77eae72a36e7648ebfbd2b1e17e))

Behebt die zwei zuvor fehlschlagenden Tests:

1. $substrCP-Projektion ist in mongomock nicht implementiert -> Zaehl-Queries brachen unter Tests
  ab. _load_emails_for_count faengt NotImplementedError (nur mongomock; echtes Atlas wirft
  OperationFailure) und laedt ohne Server-Truncation, kuerzt body_text-Prefix in Python.
  Atlas-Optimierung bleibt fuer Produktion erhalten.

2. classify_booking_mail verwarf Beds24-Mails mit LLM intent=other sofort, obwohl ein eindeutiger
  PMS-Betreff (Buchung:, Stornierung:, ...) ein staerkeres Signal ist. Jetzt ueberstimmt
  infer_beds24_intent die Fehlklassifikation -> Mail erscheint korrekt als new_booking.

Volle Suite jetzt gruen: 276 passed, 0 failed (3 deselected = integration).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- **test**: Use explicit Settings in review learning test for CI
  ([`154453f`](https://github.com/siinanXD/Booking-email-checl/commit/154453fe270c501a7f9ebbb18467066413b201d5))

Settings() requires env vars that exist locally via .env but not in GitHub Actions.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- **whatsapp**: Per-employee cleaning alerts in five languages
  ([`031a956`](https://github.com/siinanXD/Booking-email-checl/commit/031a956712bc386e042dcb76f2a6c924f48ca93c))

Add per-employee locale for cleaning task WhatsApp templates (de/en/pl/it/es), localized review
  previews, and flag-based locale picker in the property UI.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Refactoring

- Remove dead code and move test mocks to ai/testing
  ([`c1fd93d`](https://github.com/siinanXD/Booking-email-checl/commit/c1fd93d73847cb23fe96a1053418223c77f0eb32))

Drop unused repositories, models, and top-level stubs; relocate LLM and WhatsApp mocks for clearer
  production boundaries.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.11.0 (2026-06-05)

### Bug Fixes

- **vector**: Eliminate >20GB RAM blow-up in chunking and vector search
  ([`a6e6b8d`](https://github.com/siinanXD/Booking-email-checl/commit/a6e6b8d32203abf80d78db0006f90f1ab20ae722))

## Problem Beim Start von `pytest` / der Pipeline schoss der RAM-Verbrauch auf über 20 GB
  (Task-Manager: ~21 GB). Ursache war **nicht** ein lokales ML-Modell (es gibt keins — Embeddings
  laufen rein über die OpenAI-API).

## Root Causes (zwei) 1. **Endlosschleife im semantischen Chunking** (Hauptursache): Ein Segment
  größer als `max_body_tokens` (langer Satz ohne Satzzeichen, URL, Base64, zitierte Tabelle) ließ
  die Overlap-Logik den Index immer wieder auf denselben Start zurücksetzen → die `packed`-Liste
  wuchs unendlich. Wird bei jedem `pytest`-Lauf getriggert. 2. **In-Memory-Vektorsuche**:
  `search_by_vector` lud die gesamte `embeddings`-Collection in den RAM (Filter `{}` bei leerem
  `account_id`).

## Changes - **`semantic_chunking.py`**: garantierte Vorwärts-Progress-Sperre (`idx` nie vor
  `chunk_start_idx+1`) + übergroße Sätze werden hart an Wortgrenzen in overlap-große Fenster
  gesplittet (kein Segment überschreitet das Limit). - **`embedding_repository.py`**:
  In-Memory-`search_by_vector` + `_dot` entfernt; bei Atlas-`OperationFailure` keine
  Fallback-Berechnung mehr, sondern Warnung `vektordatenbank_offline` + leere Liste. -
  **`similarity_search.py`**: bei `SIMILARITY_USE_ATLAS=false` → übersprungen + Warnung, ohne
  `embed()`-Aufruf. Nur Atlas, sonst leer. - **`pyproject.toml`**: Integrationstests standardmäßig
  ausgeschlossen (kein versehentlicher Lauf gegen echtes Atlas).

## Verification - Volle Suite läuft jetzt in **~93 s ohne RAM-Spike** (vorher: Hang bei 21 GB). -
  266 Tests grün; mypy (308 Dateien) + ruff sauber. - 2 verbleibende Fehler (`$substrCP`) sind
  **vorbestehend** und unabhängig (mongomock- Limitierung in `booking_mail_counts.py`) — per
  Stash-Test bestätigt.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

- **vector**: Eliminate RAM blow-up in chunking and vector search
  ([`993fcf1`](https://github.com/siinanXD/Booking-email-checl/commit/993fcf1d7699929314eae1be8b967f98c76d69e4))

Zwei Speicher-Probleme behoben, die zu >20GB RAM beim Test-/Pipeline-Lauf fuehrten:

1. Endlosschleife im semantischen Chunking (Hauptursache des 25GB-Spikes): Ein Segment groesser als
  max_body_tokens (langer Satz ohne Satzzeichen, URL, Base64, zitierte Tabelle) liess die
  Overlap-Logik den Index immer wieder auf denselben Start zuruecksetzen -> packed-Liste wuchs
  unendlich. - _pack_body_chunks: garantierte Vorwaerts-Progress-Sperre (idx nie vor
  chunk_start_idx+1). - _split_segments: uebergrosse Saetze werden hart an Wortgrenzen in
  overlap-grosse Fenster geteilt; kein Segment ueberschreitet das Limit.

2. In-Memory-Vektorsuche entfernt (RAM-Risiko + 25GB-Mitursache): search_by_vector lud die gesamte
  embeddings-Collection in den RAM. - search_by_vector + _dot entfernt. - search_by_vector_atlas:
  bei OperationFailure kein Fallback mehr, sondern Warnung 'vektordatenbank_offline' + leere Liste.
  - SimilaritySearchService: use_atlas=False -> uebersprungen + Warnung, ohne embed()-Aufruf. Nur
  Atlas, sonst leer.

3. pyproject.toml: Integrationstests standardmaessig ausgeschlossen, damit pytest nie unbeabsichtigt
  gegen echtes Atlas laeuft.

Volle Suite laeuft jetzt in ~93s ohne RAM-Spike (266 passed; 2 vorbestehende
  mongomock-$substrCP-Fehler unberuehrt).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Documentation

- **roadmap**: Sync checkboxes with implemented phases 6-12
  ([`7f35528`](https://github.com/siinanXD/Booking-email-checl/commit/7f3552802fb586edd50f59c9660ebf3ad582e0e9))

Die Checkbox-Stati standen noch auf [ ], obwohl die Features (Support-Tickets, Erst-Import,
  Admin-Kosten, Review-Nav, Abgeschlossen-Detail, Unterkuenfte, semantisches Chunking) laengst
  implementiert sind. Stati an den realen Code-Stand angeglichen.

Echt offen bleiben: Re-Ranking (bewusst zurueckgestellt, AGENTS.md), optionale UI-Politur (Phase
  8.6/10), manueller Meta-Template-Ops-Schritt, Onboarding-Hinweis.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Features

- **platform**: Gdpr Langfuse trace wipe, Phase-8 cost tests, deploy docs
  ([`d198e71`](https://github.com/siinanXD/Booking-email-checl/commit/d198e71feaa98b31479e13281439c2dd1e7062e1))

## Summary Setzt die offenen Roadmap-Punkte um. **Baut auf `fix/vector-search-no-memory-fallback`
  auf** — daher bitte diesen RAM-Fix-PR zuerst mergen (oder diesen hier, er enthält den Fix
  bereits).

## Changes - **DSGVO – Langfuse-Trace-Löschung**: neuer `LangfuseWipeService` löscht Traces pro
  `correlation_id` (= session_id) nach dem Mongo-Wipe; Fehler werden geloggt, kein Rollback.
  `DataWipeService` sammelt die IDs vor dem Löschen und meldet einen `langfuse_traces`-Zähler.
  Verdrahtet in `settings/wipe-all` wenn Langfuse-Keys gesetzt. - **Phase 8 – Kosten-Konsistenz**:
  zwei fehlende Tests (`overview` ↔ `metrics/costs`, `account-detail` ↔ `by_account`). - **Phase 8 –
  Frontend**: `AdminOverviewPage` warnt, wenn Gesamtkosten ≠ Summe aktiver Mandanten
  (pending/rejected oder nicht zugeordnete Metriken). - **DEPLOYMENT.md**: Erst-Import (Phase 7) +
  semantisches Re-Index (Phase 12) mit Migrations-Befehlen. - **ROADMAP.md**: Checkboxen der Phasen
  6–12 an den realen Code-Stand angeglichen.

## Test plan - [x] `pytest tests/test_langfuse_wipe.py tests/web/test_admin_overview.py
  tests/web/test_settings_api.py` → 19 grün - [x] mypy (310 Dateien) + ruff sauber - [x]
  Frontend-Build grün - [ ] CI grün abwarten

## Notes Re-Ranking (`reranking.py`) bleibt bewusst zurückgestellt (siehe AGENTS.md). Die 2
  vorbestehenden `$substrCP`-Testfehler (mongomock) sind nicht Teil dieses PRs.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

- **platform**: Gdpr Langfuse trace wipe, Phase-8 cost tests, deploy docs
  ([`db91489`](https://github.com/siinanXD/Booking-email-checl/commit/db914892ed8a2b42412b5972dc738a3d52047bac))

Setzt die offenen Punkte aus der Roadmap um:

- DSGVO: LangfuseWipeService loescht Traces pro session_id (correlation_id) nach dem Mongo-Wipe;
  Fehler werden geloggt, kein Rollback. DataWipeService sammelt correlation_ids vor dem Loeschen und
  meldet langfuse_traces-Zaehler. settings/wipe-all verdrahtet den Service wenn Langfuse-Keys
  gesetzt sind. - Phase 8: zwei fehlende Kosten-Konsistenz-Tests (overview vs metrics/costs,
  account-detail vs by_account). - Phase 8: AdminOverviewPage warnt, wenn Gesamtkosten != Summe
  aktiver Mandanten (pending/rejected oder nicht zugeordnete Metriken). - DEPLOYMENT.md: Erst-Import
  (Phase 7) + semantisches Re-Index (Phase 12) mit Migrations-Befehlen. - ROADMAP: erledigte
  Phase-8-Punkte abgehakt.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>


## v0.10.0 (2026-06-05)

### Bug Fixes

- **frontend**: Remove invalid Button size prop in AdminTicketsPage
  ([`88d221d`](https://github.com/siinanXD/Booking-email-checl/commit/88d221d8b3be9ccbd34586cbdd303fff9253854a))

ButtonProps has no size field; use className for compact admin ticket actions.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **types**: Resolve mypy errors in entity_sync and reindex script
  ([`06c7065`](https://github.com/siinanXD/Booking-email-checl/commit/06c7065d85bbaeda490368cb8231fd1e9d78e870))

Use Db/BookingExtraction types in ensure_property_from_extraction and narrow Mongo document fields
  to str before reindexing.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- **tenant**: Properties, review workflow, and dashboard performance
  ([`5853767`](https://github.com/siinanXD/Booking-email-checl/commit/58537675b0a304f5ea211ff2d8aeba937400bced))

Batch Mongo aggregation replaces N+1 queries that made dashboard stats take minutes. Add properties
  API, review queue services, WhatsApp notifications, mail summaries, completed queue, date filters,
  and related tenant UI and test coverage.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **tenant**: Wave-1 planned features — support tickets, properties, ingest
  ([`8aaa627`](https://github.com/siinanXD/Booking-email-checl/commit/8aaa62713fdc21ebe7e3fbfcee879225a74df6f8))

Add support ticket flow with admin WhatsApp alerts, property profiles with year stats, initial mail
  ingest window, semantic chunking groundwork, and dashboard/email UX improvements including Ground
  Zero review mode.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.9.0 (2026-06-04)

### Chores

- **mvp**: Verification docs, integration smoke, and quality fixes
  ([`f2a26ed`](https://github.com/siinanXD/Booking-email-checl/commit/f2a26ed869c6f9a282646a600837e5ca35b8a45d))

Add PR_STEP_4_5 checklist, expand VERIFICATION for steps 4-5 and workflows, document eval baseline,
  fix live workflow triage test, mypy on admin aggregates, and optional Mongo embedding integration
  test.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Documentation

- Add GitHub PR merge instructions to PR_STEP_4_5
  ([`1a6200c`](https://github.com/siinanXD/Booking-email-checl/commit/1a6200c99f80474190be40489d3be1e97144ebf6))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- **workflows**: Gemini multimodal suggest, preview, and workflow rubrics
  ([`7e5fd55`](https://github.com/siinanXD/Booking-email-checl/commit/7e5fd55b139d3f3ae2c669d17f5e1bc840beb8ba))

Add Gemini client integration for screenshot-based workflow suggestions and multimodal extract
  preview, extend tenant workflow APIs and admin routes, and wire the dashboard with workflow rubric
  navigation. Includes CI fixes (ruff, mypy, pytest, frontend build) and temporary line-limit skips
  for oversized MVP branch files pending split before merge to main.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Refactoring

- Split oversized files for 300-line CI limit
  ([`7de840a`](https://github.com/siinanXD/Booking-email-checl/commit/7de840a195b67ffdc5e849d5e60fcf2007f5d9d0))

Extract modules for workflows UI, API types, pipeline review, admin overview metrics, and tests.
  Remove temporary SKIP_FILES entries so check_max_file_lines enforces the limit on all production
  code.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.8.0 (2026-06-04)

### Features

- **admin**: Cross-tenant monitoring and cost observability
  ([`b3a15af`](https://github.com/siinanXD/Booking-email-checl/commit/b3a15af2e5daf899f0b8e1c736c8155321c2f3cd))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **admin**: Llm config UI with prompt overrides and similarity top-k
  ([`853b62d`](https://github.com/siinanXD/Booking-email-checl/commit/853b62db033b1c0de87a289e4fbb0388a7aa7466))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **admin**: Per-tenant mail and whatsapp connection tests
  ([`9bf92fc`](https://github.com/siinanXD/Booking-email-checl/commit/9bf92fcc5d6bfafe3087f78c1c32d35e019df85a))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **admin**: Separate platform admin from tenant mail onboarding
  ([`428c144`](https://github.com/siinanXD/Booking-email-checl/commit/428c144147233df8db7e7546eac8dcf8f5d92429))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **triage**: Llm gate for unknown senders, tenant workflows, admin charts
  ([`2324d0f`](https://github.com/siinanXD/Booking-email-checl/commit/2324d0f1206a3dcdc4a6ec8fbac7151029a46dab))

Add optional cheap triage model before classify/extract, tenant workflow API/runtime, prompt history
  in admin LLM config, and observability charts plus cost-triage docs.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.7.0 (2026-06-03)

### Bug Fixes

- **grounding**: Filter false-positive guest name matches in draft
  ([`5aeafc4`](https://github.com/siinanXD/Booking-email-checl/commit/5aeafc49d7bb5c9596a6a9da78f600d37b41fedf))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **pre-push**: Log atlas fallback, tighten name grounding, add edit-distance alert
  ([`2023b5e`](https://github.com/siinanXD/Booking-email-checl/commit/2023b5e722ed1e20e16a55e1e1bc212b0d7c4cc2))

Log silent Atlas vector search fallback, require two token overlaps for guest names, and alert when
  draft edit distance exceeds 0.4.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **tests**: Use patch.object for atlas aggregate mocks
  ([`5885ad0`](https://github.com/siinanXD/Booking-email-checl/commit/5885ad0d9a227573cdf03aab3108dd8ac1151a94))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- **dashboard**: Add timestamps and reviewed_today KPI
  ([`2e185a9`](https://github.com/siinanXD/Booking-email-checl/commit/2e185a9eadf96da81e1eef953d9328e34e14d588))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **draft**: Platform tone and grounding instructions in prompt template
  ([`1c3ba8c`](https://github.com/siinanXD/Booking-email-checl/commit/1c3ba8ce84559abc2039fa2451ea09d429c6eed0))

Extend draft.md with platform_tone, grounding rules, and response structure; add _platform_tone and
  _build_prompt helpers.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **feedback-loop**: Track draft edit distance via Langfuse scores
  ([`d729823`](https://github.com/siinanXD/Booking-email-checl/commit/d72982336be775e042b43f2404d1bea3a85357d7))

Add LangfuseTracer.log_score, ReviewFeedbackTracker with difflib distance, and wire record() into
  WorkflowNodes.finalize on approval.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **grounding**: Add check_with_detail with guest and date validation
  ([`54e8ee9`](https://github.com/siinanXD/Booking-email-checl/commit/54e8ee9367b34f2dc87bc79c029e4b07086febd8))

Extend grounding beyond booking refs to guest names and dates, returning GroundingResult with
  failed_fields and confidence while keeping check() as wrapper.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **indexing**: Alert on async indexing failures
  ([`b21738f`](https://github.com/siinanXD/Booking-email-checl/commit/b21738f943dc793e99d6c065c5a5d32b2181fb25))

Wrap _index_async in try/except and report errors via AlertService with indexing: prefix.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **mail-sync**: Fast manual sync, expose errors, background reprocess
  ([`5732f72`](https://github.com/siinanXD/Booking-email-checl/commit/5732f72ebe1bbfab50b959b2ad18712a9261be99))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **mongo**: Auto-create domain collections and tenant-scoped entities
  ([`186ea90`](https://github.com/siinanXD/Booking-email-checl/commit/186ea90e90d981e97106c3eca1cc538196b8680c))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **vector-search**: Atlas vector search with in-memory fallback
  ([`156aa9d`](https://github.com/siinanXD/Booking-email-checl/commit/156aa9da2d7b00d459e754a6586d125bdde4d8cd))

Add search_by_vector_atlas with OperationFailure fallback, SIMILARITY_USE_ATLAS setting, and
  AGENTS.md index setup note.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Testing

- **eval**: Add complaint and direct-booking eval cases
  ([`3aeaade`](https://github.com/siinanXD/Booking-email-checl/commit/3aeaadefb070b4f1b00efd021cf39a7fd5042ace))

Add eval-009 for complaint with guest name and eval-010 for direct booking without platform; extend
  MockLLM responses.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.6.0 (2026-06-03)

### Bug Fixes

- **review-queue**: Add compound index on review_status + account_id + updated_at
  ([`4d4b8a3`](https://github.com/siinanXD/Booking-email-checl/commit/4d4b8a3314daf31a4ed7efb57c587a998178148c))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Documentation

- Add Cursor Cloud dev environment notes to AGENTS.md
  ([`4a2f82d`](https://github.com/siinanXD/Booking-email-checl/commit/4a2f82df802c3b81167349e4d44ce3521f21c536))

Co-authored-by: siinanXD <siinanXD@users.noreply.github.com>

### Features

- **alerts**: Retrieval empty alert test
  ([`be6cd2d`](https://github.com/siinanXD/Booking-email-checl/commit/be6cd2d185bfafee693529ddc64b8a1a737008e5))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **entity-resolution**: Guest matching with confidence thresholds
  ([`3bf22f0`](https://github.com/siinanXD/Booking-email-checl/commit/3bf22f002f98815887ed9a1fa82151bc062d07b7))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **retrieval**: Entity resolution, caps, and empty-booking alerts
  ([`0df908c`](https://github.com/siinanXD/Booking-email-checl/commit/0df908cfed5bb743fa34c594b449e4eeebad71fc))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **review**: Reject alias and rejection flow tests
  ([`8c2e7eb`](https://github.com/siinanXD/Booking-email-checl/commit/8c2e7ebb027c4a2b68f3a4c30ca0a1851e182538))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **review-queue**: Review repository aliases and persistence tests
  ([`1f0c453`](https://github.com/siinanXD/Booking-email-checl/commit/1f0c45362d7ee671d3ceb6d6d63b555d57578947))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Testing

- **eval**: Add retrieval and entity resolution cases
  ([`e8fef07`](https://github.com/siinanXD/Booking-email-checl/commit/e8fef0767a1e88dd5a9cc8a60c8bd59f52bc175a))

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.5.1 (2026-06-02)

### Bug Fixes

- **config**: Validate mongodb_uri format
  ([`250984c`](https://github.com/siinanXD/Booking-email-checl/commit/250984c0db40ab69e57a284cee7d22424548384b))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **indexing**: Thread-backed asyncio.run fallback
  ([`31dd81c`](https://github.com/siinanXD/Booking-email-checl/commit/31dd81c78e50c6e178ae421a589fda4dfda713b3))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **langfuse**: Log mail cost on active trace
  ([`c79f679`](https://github.com/siinanXD/Booking-email-checl/commit/c79f679ad2633f42ce1ed1b0b52422b11b4b974e))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **mongo**: Singleton client with timeout
  ([`38f852e`](https://github.com/siinanXD/Booking-email-checl/commit/38f852e06ea8ee591078219fb69f32426c639877))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **triage**: Ignore platform hint on unknown domain
  ([`7e3de9c`](https://github.com/siinanXD/Booking-email-checl/commit/7e3de9c2da8df37eb2aff8bb61644b76b0f178e5))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Chores

- **deps**: Align ruff to 0.9.6
  ([`c03c004`](https://github.com/siinanXD/Booking-email-checl/commit/c03c0043e051b500927c6e3bd97ef3f70be2bdc8))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **models**: Remove duplicate RetrievalResult model
  ([`0df9679`](https://github.com/siinanXD/Booking-email-checl/commit/0df9679cdf4fdeb30b3bfce0def16c72ccd7f5d7))

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.5.0 (2026-06-02)

### Features

- Outlook OAuth onboarding, README refresh, and CI hygiene
  ([`bfffeae`](https://github.com/siinanXD/Booking-email-checl/commit/bfffeaeb79c6877dced8884491932891b371b4a7))

Add delegated Outlook OAuth flow with mail sync/reprocess APIs, update README with architecture
  SVGs, split booking mail counters for the 300-line rule, and fix lint/import ordering for green
  CI.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.4.1 (2026-06-02)

### Bug Fixes

- Use app context database for settings wipe-all in tests
  ([`57916fb`](https://github.com/siinanXD/Booking-email-checl/commit/57916fb141dcbb51ef08f931adadd048cddc0b35))

Route wipe-all through g.ctx.db so web tests use mongomock instead of connecting to localhost
  MongoDB.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Refactoring

- Reorganize backend and frontend for layered architecture
  ([`09707dc`](https://github.com/siinanXD/Booking-email-checl/commit/09707dcb01f3beb75825a894efe14abe985d8934))

Move Python code under backend/ with api, ai, features, and infrastructure layers, restructure the
  dashboard into features/lib/shared, and align CI fixes including authStore tests and lint
  formatting.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.4.0 (2026-06-02)

### Features

- Multi-tenant SaaS with mail onboarding and automatic polling
  ([`2dadfd6`](https://github.com/siinanXD/Booking-email-checl/commit/2dadfd6986a8f9364a411e0341658f06cfc56942))

Enable open registration with admin approval, strict account_id isolation across APIs and data,
  per-tenant IMAP/Outlook mailbox setup with onboarding wizard, and a dedicated poll worker for all
  active tenants.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.3.0 (2026-06-02)


## v0.2.1 (2026-06-02)

### Bug Fixes

- **auth**: Persist JWT blocklist in Mongo for multi-worker logout
  ([`a2dccb5`](https://github.com/siinanXD/Booking-email-checl/commit/a2dccb507286c3aaadc69990a02dafd8642c2a19))

Logout tokens are stored in MongoDB with TTL so revocation works across Gunicorn workers. Fixes MyPy
  CI errors, Docker admin seed failures, demo credentials in .env.example, and missing docstrings.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- Whatsapp-benachrichtigungen und Einstellungs-Dashboard
  ([`9c69290`](https://github.com/siinanXD/Booking-email-checl/commit/9c692901251d7719a3f475bca50b54cbdb6cacd8))

Nach Review-Freigabe werden WhatsApp-Templates an Host und Putzfrau versendet. Einstellungen und
  Unterkuenfte werden persistent in MongoDB gespeichert (mit .env-Vorausfuellung), inkl. Test-Button
  und Daten-Loeschen. Docker-Build und SPA-Auslieferung wurden repariert.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.2.0 (2026-06-02)

### Bug Fixes

- Align project with agent requirements
  ([`9c816b0`](https://github.com/siinanXD/Booking-email-checl/commit/9c816b08b5e4ce5c8dd396114222b940016e5f9e))

- Stable env loading, gpt-5 drafts, and ingest helper scripts
  ([`382eeb1`](https://github.com/siinanXD/Booking-email-checl/commit/382eeb1140d7ef7537ece1e6a0451ed2dd111db0))

Load .env from project root regardless of cwd. Omit temperature for gpt-5 draft models. Add venv
  path bootstrap and PowerShell wrapper for Outlook ingest, plus diagnose, live OpenAI smoke test,
  and Mongo booking mail listing scripts.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Documentation

- Document venv ingest, LLM_MODE, and helper scripts
  ([`6717b56`](https://github.com/siinanXD/Booking-email-checl/commit/6717b56b446350a1544d703b2accd90ade46d5ce))

Expand README quickstart with project-root .env, PowerShell ingest wrapper, live vs mock mode, and
  diagnose/live-test/check scripts.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- Outlook Graph ingestion, LLM mock mode, and Langfuse tracing
  ([`830a7f2`](https://github.com/siinanXD/Booking-email-checl/commit/830a7f254c8d06455848af5e656182f49f35cd9b))

Add Microsoft Graph adapters with MSAL device-code and application auth, CLI ingest, and OUTLOOK_*
  settings. Enable LLM_MODE=mock for dev without OpenAI quota. Use Langfuse @observe and
  langfuse.openai for automatic generations, sessions per mail, and embed traces.

- **web**: Add Flask JWT auth and dashboard API blueprints
  ([`c4d2504`](https://github.com/siinanXD/Booking-email-checl/commit/c4d2504ab7308b40f27d9e934b90b6a91b9926f8))

Application factory with CORS, login/logout/me/refresh, dashboard stats, email list/detail, review
  approve/reject, costs API, QueryService, and tests/web suite.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **web**: Add React dashboard, Docker production, and frontend tests
  ([`05fb8c0`](https://github.com/siinanXD/Booking-email-checl/commit/05fb8c03728c135ee141165c1dd7c9dbd2ceaf93))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **web**: Strict booking-mail detection and review queue fixes
  ([`1d79176`](https://github.com/siinanXD/Booking-email-checl/commit/1d791768b9ce6877753f894d974324d765f7d6c2))

Filter lists and review to real Beds24/PMS mail, add dashboard booking KPIs, fix bookings API and
  workflow interrupt, and add maintenance/backfill scripts.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **workflow**: Persist drafts, metrics, and Mongo checkpointer support
  ([`8c9d995`](https://github.com/siinanXD/Booking-email-checl/commit/8c9d99512b1f55521cd1cc253d14416ddceaf909))

Add review and mail_metrics collections, resume_after_rejection, email list filters, and optional
  MongoDBSaver via build_checkpointer. MailCostTracker snapshots costs to Mongo.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.1.0 (2026-06-02)

### Bug Fixes

- Pin Python to 3.11 only across project config
  ([`618f062`](https://github.com/siinanXD/Booking-email-checl/commit/618f062cd2ba327acafefd03893b510898b9c1ca))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **build**: Declare setuptools packages for flat-layout editable install
  ([`0a39f13`](https://github.com/siinanXD/Booking-email-checl/commit/0a39f13fe92018547003e6ee2b043aedf42f572e))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Documentation

- Pr description for MVP step 2
  ([`98935ec`](https://github.com/siinanXD/Booking-email-checl/commit/98935ec677764bcc6a289dff2af49b1c9771d89b))

### Features

- **eval**: Dual-mode offline eval with field-wise extraction scoring
  ([`f837398`](https://github.com/siinanXD/Booking-email-checl/commit/f83739850cf8b3a4f866021d4ad60271912215e5))

Co-authored-by: Cursor <cursoragent@cursor.com>
