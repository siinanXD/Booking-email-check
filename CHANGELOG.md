# CHANGELOG


## v0.27.0 (2026-06-23)

### Features

- **observability**: Polling-heartbeat im /health-Endpoint (Dead-man's-Switch)
  ([`e8e85dd`](https://github.com/siinanXD/Booking-email-check/commit/e8e85dd5fdb5ab5c3103a72c5fd39a8c7080c9d6))

Fällt der Polling-Thread aus, merkte es niemand. /health prüft jetzt zusätzlich einen Mongo-Ping und
  die Polling-Frische: newest_sync_at über alle Verbindungen (wird jeden erfolgreichen Zyklus
  gesetzt) vs. POLL_HEARTBEAT_STALE_SECONDS (900). Bei DB-Ausfall oder veraltetem Poll →
  status=degraded + HTTP 503, damit externes Monitoring/Railway alarmiert. Kein Fehlalarm ohne
  pollbare Accounts. Nutzt bestehendes last_sync_at — keine neue Collection.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>


## v0.26.0 (2026-06-23)

### Bug Fixes

- **scripts**: Reindex-dry-run zählt Purges nicht mehr als "indexiert"
  ([`ddb4c13`](https://github.com/siinanXD/Booking-email-check/commit/ddb4c1349c112a403e27b0144368e57ff24c7d2c))

Im --dry-run wurde processed für index- UND purge-Vorschauen erhöht, sodass der Bericht "N
  indexiert, 0 gepurged" zeigte, obwohl Mails gepurged würden. Jetzt getrennt gezählt. (Die
  vectorSearchScore-Projektion liefert korrekt Scores — verifiziert gegen Prod, kein Fix nötig.)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Continuous Integration

- **security**: Dependency-/secret-scanning (pip-audit, bandit, npm audit, Dependabot)
  ([`a420706`](https://github.com/siinanXD/Booking-email-check/commit/a420706463da285f82e7ae7bbcc4c4616c614d7f))

Supply-Chain-Lücke für eine Auth+PII-SaaS geschlossen: neuer security-Job mit pip-audit
  (Abhängigkeits-CVEs) und bandit (Code-Sicherheit), npm audit im Frontend-Job, plus
  .github/dependabot.yml (wöchentlich pip/npm/github-actions). Scans starten nicht-blockierend
  (continue-on-error), bis der Bestand sauber ist — dann scharf schalten.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Features

- **observability**: Sentry-error-tracking (opt-in, PII-maskiert)
  ([`ee1060c`](https://github.com/siinanXD/Booking-email-check/commit/ee1060cb0eae4a766255cd0907532c911abb5bff))

Pipeline- und Polling-Fehler verschwanden bisher in den Railway-Logs. sentry-sdk wird früh in
  create_app initialisiert — nur wenn SENTRY_DSN gesetzt ist (lokal/ Tests neutral). before_send
  maskiert E-Mail/Telefon (mask_pii), send_default_pii ist aus. Settings SENTRY_DSN +
  SENTRY_TRACES_SAMPLE_RATE.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Performance Improvements

- **workflow**: Extraktion für klar nicht-buchungsbezogene Mails überspringen
  ([`a8e2ed2`](https://github.com/siinanXD/Booking-email-check/commit/a8e2ed2814bac88d1e6f63694feb4a67cbbf886d))

graph.add_edge("classify","extract") war unbedingt — nach intent=OTHER lief die Extraktion
  (LLM-Call) trotzdem, verworfen wurde erst nach der Validierung. Neue Conditional-Edge
  after_classify (analog after_validate) verwirft intent=OTHER ohne Rettungssignale direkt nach der
  Klassifikation (DISCARDED, not_booking_pre_extract) und spart so den Extraktions-LLM-Call für
  Marketing/ Newsletter/Kalender. Informelle Buchungsanfragen bleiben sicher: extrahiert wird weiter
  bei has_reservation_request_signals / is_probable_booking_mail / infer_beds24_intent — exakt die
  Signale, die enrich_extraction später als Buchung wertet.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Testing

- **eval**: Golden-set um 20 harte Live-Fälle erweitern (echte Qualitätsmessung)
  ([`993a13c`](https://github.com/siinanXD/Booking-email-check/commit/993a13c0000aa85d86e46aca436629f4888734a9))

10 triviale Fälle bei 100% sagten nichts aus. Neue cases_live.json mit 20 realistischen Edge-Cases
  (Beds24/Relay-Absender, mehrsprachig IT/FR, generischer property_name, informelle Anfragen,
  Marketing/Kalender/Bestellung als other, fehlende Felder). Nur im Live-Modus evaluiert (MockLLM
  kann sie nicht reproduzieren) — der Mock-Lauf bleibt das 100%-Verdrahtungs-Gate auf den Basis-10.

Live-Baseline (gpt-4o-mini, 30 Fälle): classify 0.93, extraction 0.99. Aufgedeckt: informelle
  Anfrage→guest_inquiry, italienische Bestätigung→cancellation (Kandidaten für Prompt-Verbesserung).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>


## v0.25.0 (2026-06-23)

### Features

- **frontend**: Ux/quality pass across all routes
  ([`9b19f17`](https://github.com/siinanXD/Booking-email-check/commit/9b19f179c43e663ad857b93d54590c0790de3041))

- Global feedback: toast store + Toaster, MutationCache.onError surfaces all mutation errors;
  ErrorBoundary + inline ErrorState for queries - Destructive actions gated by ConfirmDialog
  (settings wipe, admin suspend/expiry/delete) with typed confirmation - Route-level code splitting
  (React.lazy + Suspense) and a real 404 page - 401 single-flight token refresh before logout -
  Dedupe: useSidebarNav (desktop+mobile), useReviewActions (review+ ground-zero), useAllAccounts
  (admin), shared format/cn/errors helpers - A11y: table scope/role/aria-selected, focus rings,
  drawer focus trap + restore, role=alert on auth errors, date-range min/max - UI primitives: Button
  loading/forwardRef/type=button, Input forwardRef/ label/error, Badge tone union - Search debounce,
  isError handling, KPI label fix, properties row removal

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>


## v0.24.0 (2026-06-22)


## v0.23.0 (2026-06-22)

### Bug Fixes

- **api**: Vor unsicheren CORS-Origins in Produktion warnen
  ([`5d0cbc6`](https://github.com/siinanXD/Booking-email-check/commit/5d0cbc61947c233dbe54a7c4e9607d8d4bac5f07))

localhost/127.0.0.1 oder leere CORS_ORIGINS in app_env=production loggen jetzt eine Warnung, damit
  Onboarding-Fehlkonfiguration auffällt.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Code Style

- 300-zeilen-limit nach Merge einhalten (pipeline, test_emails_api)
  ([`c466b78`](https://github.com/siinanXD/Booking-email-check/commit/c466b78c8af28b75cca46145bb32f25f9d1238ec))

Der Merge von main kombinierte die RAG- und perf-Änderungen, wodurch pipeline.py (301) und
  tests/web/test_emails_api.py (308) das 300-Zeilen-Limit rissen. pipeline.extract bindet
  self._email_repo._col.database einmal als lokale db
  (known_property_names/ensure_property_from_extraction je einzeilig). test_emails_api kompaktiert
  einen client.get-Aufruf und entfernt den redundanten is_booking=None-Fall (separat in eigenem Test
  abgedeckt).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Features

- **mail**: Erst-sync auf harte Tages-Rückschau begrenzen
  ([`8451565`](https://github.com/siinanXD/Booking-email-check/commit/845156580964816b8ccd75bac184b34bbcb647af))

Beim Onboarding wird das Postfach nur noch bis anchor - lookback_days zurück gelesen (Default 1 Tag)
  statt bis zu 60 Tage. Neue Funktion filter_messages_since_cutoff() ersetzt die zählbasierte
  Auswahl; resolve_poll_since_for_account() begrenzt die Untergrenze per max() statt min().
  Steuerbar über MAIL_INGEST_INITIAL_LOOKBACK_DAYS.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- **rag**: Vektor-index auf buchungsrelevante Mails begrenzen + Text säubern
  ([`4ecff35`](https://github.com/siinanXD/Booking-email-check/commit/4ecff3500a49468654d3eefadc221ae49d4e2ed1))

Beobachtung an Prod-Daten: der Index war zu ~80% intent=other (Marketing, Kalender, Tinder) mit
  CSS-/HTML-Müll (@font-face, &nbsp;) in den Chunks — die "ähnlichen Fälle" für echte Buchungen
  waren dadurch Rauschen.

- Validate-Node indexiert nur noch buchungsrelevante Mails (is_booking_relevant); intent=other wird
  nicht mehr indexiert. - IndexingService.purge() entfernt Chunks+Embeddings einer Mail; das
  Reindex-Skript purgt Nicht-Buchungs-Mails und säubert so den Bestand. - preprocess_mail_body
  entfernt <style>/<script>-Blöcke und dekodiert HTML-Entities (bessere Embeddings).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Performance Improvements

- **emails**: Buchungs-kategorie-listen DB-seitig filtern
  ([`c7b4cc8`](https://github.com/siinanXD/Booking-email-check/commit/c7b4cc8457cc48349e6a95c71337666d8dcb90bf))

Vorberechnete Felder is_booking/effective_intent auf StoredEmail ersetzen den alten Pfad (500 Mails
  laden + pro Request in Python klassifizieren). relevance_fields() ist die Single Source of Truth,
  wird beim Extrahieren geschrieben und vom neuen Backfill-Skript resynct. Neuer Index
  idx_email_account_booking_intent; Booking-Pfad nutzt plain find statt $lookup. Detail-Lookups
  laufen 4x parallel, Summary aus Cache statt Write.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Refactoring

- **mail**: Toten filter_messages_for_initial_sync entfernen
  ([`3bceb98`](https://github.com/siinanXD/Booking-email-check/commit/3bceb9894bc3662e35b185287b30b8e10174d31e))

Seit der Umstellung auf das zeitbasierte filter_messages_since_cutoff wird die zähl-/ankerbasierte
  Variante nirgends in backend/ mehr aufgerufen — nur noch von ihren eigenen Tests. Funktion plus
  die zwei test_initial_sync_*-Tests entfernt.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>


## v0.22.0 (2026-06-22)

### Bug Fixes

- **eval**: Veraltete Live-Baseline korrigieren + unbegründete Erwartung entfernen
  ([`3f80f30`](https://github.com/siinanXD/Booking-email-check/commit/3f80f30b36ecbd37670f78f32a33909c51a67fad))

Die dokumentierte Baseline (2026-06-04: classify 1/10, extraction 0.38) stammte aus einer frühen,
  defekten Pipeline-Phase und stellte ein gesundes System als kaputt dar. Harness verifiziert
  korrekt; tatsächlicher Live-Stand: classify 10/10, extraction 1.00/1.00. Fall eval-010 erwartete
  zudem guest_count=2, obwohl der Mailtext keine Gästezahl nennt (extract.md: nur bei Erkennbarkeit)
  - entfernt.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- **notifications**: Falscher WhatsApp-Unterkunftsname durch zu lockeres Matching
  ([`9a808d7`](https://github.com/siinanXD/Booking-email-check/commit/9a808d7d8982b779fdf7a1d587a82e2b2d25005a))

match_known_property_name() mappte jeden generischen extrahierten Namen (z. B. "Zimmer") via
  Teilstring auf den ersten Katalog-Eintrag ("Zimmer Nummer drei"), sodass jede Buchungsmail
  dieselbe falsche Unterkunft in der WhatsApp-Variable bekam. Matching jetzt wortgrenzen-genau,
  gefährliche Richtung (Kandidat als Teilstring des Katalog-Namens) entfernt, spezifischster
  (längster) Treffer gewinnt statt des ersten. Legitime Normalisierung (verbose Extraktion ->
  Katalog-Name) bleibt erhalten.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- **rag**: Account_id-filterfeld im Atlas-Vector-Index ergänzen
  ([`f9b9ba8`](https://github.com/siinanXD/Booking-email-check/commit/f9b9ba8fcbf63b2a643a6adb840753e1813f908c))

find_similar_cases schränkt jede Suche per {account_id: ...} ein, aber das Setup-Skript legte den
  Index nur mit dem embedding-Vektorfeld an. Atlas $vectorSearch verlangt deklarierte Filterfelder —
  ohne account_id scheiterte die mandantengefilterte Suche und RAG lieferte selbst bei aktivem Flag
  nichts. Index-Definition als build_vector_index_definition() neben VECTOR_INDEX_NAME im
  embedding_repository zentralisiert (Skript + Test nutzen dieselbe Quelle) und in der manuellen
  Anleitung ergänzt.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- **tests**: Poll-window-test zeitunabhängig machen
  ([`c996482`](https://github.com/siinanXD/Booking-email-check/commit/c9964826027adc17432ff4132eabfa7acef90627))

test_compute_poll_since_uses_max_received_overlap hardcodete newest auf 2026-06-06 und erwartete
  since == newest - 24h. compute_poll_since gibt aber max(candidates) inkl. now - default_window
  (7d) zurück. Sobald die reale Zeit >7d hinter newest liegt, gewinnt now - 7d und die Assertion
  bricht (main-CI rot seit 2026-06-13).

newest jetzt relativ zu now (now - 1h), damit newest - overlap stabil das Maximum bleibt.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Features

- **rag**: Semantisches Chunking im Live-Index statt naivem chunk_text
  ([`8c913a4`](https://github.com/siinanXD/Booking-email-check/commit/8c913a4f588be15013847dd31abb03350ce1f1c6))

_index_async nutzt jetzt semantic_chunk() (Token-Limit, Overlap, Kontext-Prefix aus
  Betreff|Intent|Unterkunft|Buchungsnr.) statt des naiven Absatz-Splits. Reiche Chunk-Metadaten
  (chunk_index, token_count, char_start/end, context_prefix) werden mitgespeichert. Re-Index ist
  jetzt idempotent: erst alle Embeddings berechnen, dann alte Chunks/Embeddings der correlation_id
  löschen und neu schreiben — kein Datenverlust bei Embedding-Fehler, keine Waisen bei weniger
  Chunks. Das Reindex-Skript profitiert automatisch (ruft denselben _index_async). subject und
  body_html werden durch schedule_index gereicht. Neue Settings CHUNK_MAX_TOKENS (512) /
  CHUNK_OVERLAP_TOKENS (64). chunk_text entfernt (war nur hier genutzt).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- **rag**: Similar_cases PII-maskiert und nur als Stilreferenz in den Draft
  ([`3bf6305`](https://github.com/siinanXD/Booking-email-check/commit/3bf630580f3a5a5badb2a01d2d5db4817bc7cc53))

similar_cases gingen als rohe Mongo-Dicts (fremde PII, account_id, fremde Buchungsnummern) in die
  "Fakten" des Draft-Prompts — Halluzinationsrisiko. Jetzt: _compact_similar_cases reduziert auf
  intent + PII-maskierten Auszug (mask_pii, max 5 Fälle, interne Metadaten entfernt). Im Prompt als
  "aehnliche_faelle_nur_stil" gekennzeichnet; draft.md weist den LLM an, daraus NIE Fakten zu
  übernehmen. Grounding prüft Referenzen weiterhin gegen reservations und flaggt aus Stil-Auszügen
  kopierte Fakten.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- **rag**: Such-query symmetrisch zum Index aufbauen
  ([`1c674d1`](https://github.com/siinanXD/Booking-email-check/commit/1c674d1cd1cdbdcdb9eb1e9d4f56a841bb3a378f))

retrieve() embeddet nicht mehr den rohen email.body_text, sondern eine Query mit demselben Aufbau
  wie die indexierten Chunks: Kontext-Prefix (Betreff | Intent | Unterkunft | Buchungsnr.) +
  zitatbereinigter Body (build_context_prefix + preprocess_mail_body). Damit passen Query- und
  Dokument-Vektorraum zusammen und Zitat-Historie/Signaturen verschlechtern das Query-Embedding
  nicht mehr. Leere Query überspringt die Suche.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

- **rag**: Zweistufiges Retrieval mit LLM-Reranking
  ([`4061db0`](https://github.com/siinanXD/Booking-email-check/commit/4061db057e19440e52010ecfedf6a1431590e19e))

Neuer RerankService ordnet die Vektor-Kandidaten per LLM nach Relevanz zur Anfrage und schneidet auf
  top_k. RetrievalService holt bei aktivem Reranking top_k*Multiplier Kandidaten und reranked sie;
  bei Fehler/Timeout Fallback auf die Vektor-Reihenfolge (nicht-blockierend). Kandidaten-Text wird
  als untrusted behandelt. search_by_vector_atlas projiziert jetzt den vectorSearchScore und lässt
  den großen embedding-Vektor weg. Settings RERANK_ENABLED/PROVIDER/ CANDIDATE_MULTIPLIER/MODEL (nur
  Provider "llm" implementiert), default aus.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>


## v0.21.1 (2026-06-15)

### Bug Fixes

- Kürze überlange Embedding-Inputs auf Token-Limit
  ([`af84553`](https://github.com/siinanXD/Booking-email-check/commit/af845534ec557b6ea4a68b6b7518b3024b8b1d75))

text-embedding-3-small lehnt Inputs >8192 Tokens mit HTTP 400 ab, was beim Indexieren langer Mails
  als "Postfach-Hinweis" auftauchte. embed() kürzt den Text jetzt via tiktoken (cl100k_base) auf
  8000 Tokens, mit zeichenbasiertem Fallback falls tiktoken nicht verfügbar ist.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

### Chores

- **scripts**: Atlas-speicher-cleanup-tool + Tenant-Skript härten
  ([`06c1eab`](https://github.com/siinanXD/Booking-email-check/commit/06c1eab4ed575d426422b452d1f78ad36c93542e))

mongo_storage_cleanup.py analysiert Collection-Größen und räumt auf Wunsch LangGraph-Checkpoints
  bzw. alte Mails weg (Dry-Run by default), um die M0-512-MB-Quota freizuräumen, die sonst alle
  Writes blockiert.

clear_tenant_whatsapp_credentials.py: str()-Cast vor .strip(), damit Nicht-String-DB-Werte das
  Skript nicht crashen.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>


## v0.21.0 (2026-06-07)

### Features

- Erkläre Meta-WhatsApp-Fehlercodes im UI
  ([`c062b71`](https://github.com/siinanXD/Booking-email-check/commit/c062b716e552570f18160906cb775c16af5cb8ad))

Bekannte Meta Cloud API Fehlercodes (131030 allowed-list/Testmodus, 131026, 190, 133010) werden nun
  mit deutscher Handlungsanweisung versehen - im Backend an die Fehlermeldung angehängt und im
  Frontend als hervorgehobene Callout-Box in Admin-Diagnose und Settings.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>


## v0.20.0 (2026-06-06)

### Features

- Admin tenant management — suspend, expiry, delete, lock, password-reset
  ([`ac4dcf7`](https://github.com/siinanXD/Booking-email-check/commit/ac4dcf71410a45476b08aca4c697c198805271cd))

Backend: - AccountRecord: add expires_at field; AccountRepository: set_expiry, delete - UserRecord:
  add is_locked field; UserRepository: set_locked, reset_password_hash, delete -
  admin_user_actions.py (new): suspend/unsuspend/expiry/delete account routes,
  lock/reset-password/delete user routes - auth_guard: check is_locked and expires_at on every
  request - mail_poll_service: skip expired accounts during polling

Frontend: - admin.ts: add all new API functions - AdminAccountDetailPage: add Mandanten-Verwaltung
  panel and per-user actions

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.19.0 (2026-06-06)

### Features

- Add AOL Mail IMAP preset and dynamic app-password warnings
  ([`d858374`](https://github.com/siinanXD/Booking-email-check/commit/d858374c54e6ee275ce0eaf06ba92789a49c8018))

- presets.py: add 'aol' preset (imap.aol.com:993) with domains aol.com, aol.de, aol.co.uk, aol.at,
  aol.com.au, aim.com - ImapConfigFields.tsx: replace static GMX-only hint with APP_PASSWORD_HINTS
  map covering Gmail, Yahoo, AOL, iCloud, GMX, Web.de — shows amber warning with direct link when
  preset requires an app password

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.18.0 (2026-06-06)

### Chores

- Clean up repo and rewrite README
  ([`7e24fda`](https://github.com/siinanXD/Booking-email-check/commit/7e24fdae3a4bf4e2933f01332d5d85763d1ddd24))

- Remove internal docs (PR steps, kickoff, verification checklist) - Remove one-time migration
  scripts (restructure_backend/frontend) - Remove masterprompt, nginx example, code quality report -
  Add .claude/ to .gitignore - Rewrite README: concise, up-to-date, includes WhatsApp webhook setup

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Merge main and resolve README conflict
  ([`278ed40`](https://github.com/siinanXD/Booking-email-check/commit/278ed40948f205ffd23e34e4dd2b6f7cbc3811ff))

Keep the streamlined main README and integrate the Dashboard UI screenshots section.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Documentation

- Add API and prompt engineering comparison table
  ([`516acdd`](https://github.com/siinanXD/Booking-email-check/commit/516acdd6f3ea599a693fe94c8b50d5ab51d45841))

Documents model experiments (GPT-4o vs GPT-4o-mini vs Gemini), prompt iterations (V1→V3),
  temperature tuning, and cost analysis.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Features

- Fix mobile layout — wire MobileNavDrawer and hamburger button
  ([`14caa4c`](https://github.com/siinanXD/Booking-email-check/commit/14caa4c630b5d5c79115f9f251f5291058f88924))

- Sidebar: add `hidden lg:flex` so it collapses below lg breakpoint - Layout: import MobileNavDrawer
  and pass open/close state; reduce main padding to p-4 on mobile (p-6 on md+) - TopBar: accept
  onMenuOpen prop; add hamburger Menu button (lg:hidden); hide email text on xs screens (sm:block)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.17.0 (2026-06-06)

### Features

- Forward WhatsApp replies from cleaning staff to host
  ([`24a099b`](https://github.com/siinanXD/Booking-email-check/commit/24a099bf26e0ba7b521e672fb71f8ed8b6b818e0))

- New GET /api/whatsapp/webhook — Meta verification endpoint - New POST /api/whatsapp/webhook —
  receives incoming messages, forwards to host - WhatsAppIncomingService: parses Meta payload, finds
  host number, sends free-text forward -
  PlatformSettingsRepository.find_account_by_phone_number_id() for multi-tenant routing - Settings:
  WHATSAPP_WEBHOOK_VERIFY_TOKEN + WHATSAPP_APP_SECRET

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.16.1 (2026-06-06)

### Bug Fixes

- Resolve TypeScript build errors causing Railway deploy failure
  ([`45a5bdf`](https://github.com/siinanXD/Booking-email-check/commit/45a5bdf413fe3be2183812d59441429420c6f4ee))

- Add showFullBody prop to EmailDetailPanel (controls body max-height) - Add selectedCorrelationId
  prop to EmailTable + isSelected to EmailRow - Fix EmailDetailSideCard: remove EmailListItem
  fallback for EmailDetail prop

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Split 300-line violations to make CI pass
  ([`bf58b60`](https://github.com/siinanXD/Booking-email-check/commit/bf58b60f9588d5600fd7c333e24bb98769b5d4cd))

- Extract ImapConfigFields + OutlookConfigFields from ConfigStep.tsx (383→130 lines) - Extract
  SettingsMailCard from SettingsPage.tsx (309→237 lines) - Remove dev-only oauth-config endpoint to
  bring mail.py to ≤300 lines - Fix autodiscover.py mypy: dict | None → dict[str, object] | None

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.16.0 (2026-06-06)

### Chores

- Resolve merge conflicts with main — keep UI/UX redesign
  ([`64e534a`](https://github.com/siinanXD/Booking-email-check/commit/64e534a9709759af4ce48284deffd09c84359f5c))

All 12 conflicting files were frontend UI components. Accepted our version (new design system) over
  main's older styling.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.15.0 (2026-06-06)

### Bug Fixes

- **ci**: Black formatting für presets.py
  ([`679003b`](https://github.com/siinanXD/Booking-email-check/commit/679003b59508ccb478df701da8dd0eeaa4bdde7a))

Lange Domain-Listen auf mehrere Zeilen aufgeteilt (black-konform).

https://claude.ai/code/session_01VXKroNAoXGLoFjYfC89wCq

### Chores

- Update package-lock.json after npm install
  ([`c2636fd`](https://github.com/siinanXD/Booking-email-check/commit/c2636fd2ea47cfeff66e7d188de81926f51e5c98))

https://claude.ai/code/session_01VXKroNAoXGLoFjYfC89wCq

### Documentation

- Add UI screenshots to README with capture tooling
  ([`6095508`](https://github.com/siinanXD/Booking-email-check/commit/6095508d283f343c19e98930a2b4d525adddc493))

Embed production dashboard screenshots and add Playwright scripts to regenerate them from Railway or
  a local demo server.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- Merge UI/UX redesign + fix MongoDBSaver dependency
  ([`e06d83a`](https://github.com/siinanXD/Booking-email-check/commit/e06d83a4b6afa85ed8c1f810757b279c39dea1ab))

- Merge claude/ui-ux-skill-refactor-E9n71: full visual overhaul, IMAP autodiscovery, WhatsApp
  locale/template improvements - Add langgraph-checkpoint-mongodb==0.1.4 so LangGraph state persists
  in MongoDB across restarts (instead of MemorySaver) - Resolve 4 frontend merge conflicts in favour
  of new design

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

- Whatsapp host alerts, admin templates, and mobile UI
  ([`f3712ee`](https://github.com/siinanXD/Booking-email-check/commit/f3712ee01d5dba3c59b32b601dafc7825175884c))

Notify hosts with the status template on new bookings while employees keep cleaning tasks. Let
  platform admins configure and test all Meta templates. Add an accessible mobile nav drawer, card
  email lists, and touch-friendly forms.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **mail**: Imap autodiscovery — 15 Anbieter + Mozilla ISPDB Fallback
  ([`350fb2b`](https://github.com/siinanXD/Booking-email-check/commit/350fb2bea3086802e8991621e5ac8fac3cb91fcd))

Backend: - presets.py: erweitert auf 15 Anbieter (GMX, Web.de, Gmail, T-Online, 1&1/IONOS, Strato,
  Posteo, mailbox.org, Freenet, Yahoo, iCloud, Zoho, Outlook/Hotmail, Office365, Custom) mit
  Domain-Index für O(1)-Lookup - autodiscover.py: neues Modul — lokale Presets zuerst, dann Mozilla
  ISPDB (https://autoconfig.thunderbird.net/v1.1/{domain}), ablehnen von unverschlüsselten
  Verbindungen (port 143 / kein TLS) - mail.py: GET /api/mail/autodiscover?domain=gmx.de Endpoint
  (auth required)

Frontend: - mail.ts: autodiscoverImap(domain) Funktion - ConfigStep.tsx: Live-Erkennung beim
  Eintippen der E-Mail (600ms debounce), Spinner → Checkmark → Fehlermeldung als Feedback,
  auto-setzt Preset + Username, dunkles Styling passend zum Onboarding-Theme

Sicherheit: Nur die Domain (nie Passwort/Benutzername) wird an ISPDB übermittelt. Unverschlüsselte
  IMAP-Vorschläge werden verworfen.

https://claude.ai/code/session_01VXKroNAoXGLoFjYfC89wCq

- **ui**: Complete UI/UX redesign with modern SaaS design system
  ([`3c614c3`](https://github.com/siinanXD/Booking-email-check/commit/3c614c3fcb5fe16b41b5be24bc89e99b31941675))

Applied professional UI/UX skill across all shared components: - Tailwind: extended token system
  (shadows, animations, gradients, palette) - index.css: CSS custom properties, custom scrollbar,
  smooth rendering - Sidebar: dark gradient, refined nav states, icon backgrounds, footer - TopBar:
  frosted glass, user avatar initials, icon action buttons - Button: 5 variants, 3 sizes, focus
  rings, disabled states - Card: shadow levels, hover lift, variant system - Input: better focus
  ring, hover, disabled states - Badge: ring border style, optional dot indicator per tone -
  StatCard: colored icon bg, label uppercase tracking, highlight glow - EmailTable/Row: refined
  table header, empty state with icon, hover indigo tint - EmailListPage: search with icon, spinner,
  Button-based pagination - LoginPage: dark branded login with glassmorphism card and bg glow
  effects

https://claude.ai/code/session_01VXKroNAoXGLoFjYfC89wCq

- **ui**: Dramatic visual overhaul — colors, depth, stat card tones
  ([`692fd36`](https://github.com/siinanXD/Booking-email-check/commit/692fd364294f42290011cb4b632265895c8498b3))

Sidebar: - Darker bg (#0c1222), indigo gradient logo icon - Active item: indigo-600 bg + white
  left-bar accent strip - "System aktiv" green dot in footer

TopBar: - Dynamic page title from route - Gradient avatar initials (indigo) - Bell icon for
  notifications

StatCard: - 4px colored left-border per tone (indigo/success/warning/danger/info) - text-3xl
  font-extrabold value numbers - Colored icon container that matches tone - Hover scale on icon,
  hover lift on card - TrendingUp CTA link for navigable cards

Layout: - Dot-grid radial background pattern on main content area - bg-[#f1f5f9] base color

DashboardPage: - Sectioned with "Heute" / "Weitere Metriken" labels - All 8 stat cards use matching
  tones - Cancellations turn red when > 0

https://claude.ai/code/session_01VXKroNAoXGLoFjYfC89wCq

- **ui**: Redesign remaining pages and components
  ([`c871597`](https://github.com/siinanXD/Booking-email-check/commit/c87159772ee94265c49257373f3c7971e7031bfc))

Auth: - RegisterPage: dark glassmorphism card matching LoginPage, icon inputs, radio cards for
  account type, success state with checkmark

Onboarding: - OnboardingPage: animated step indicator (done/active/upcoming), dark theme -
  ProviderStep: selection cards with icon, custom radio indicator - TestStep: success/error feedback
  with icons, conditional finish button

Admin: - AdminLayout: underline tab navigation, Shield icon header

Review: - ReviewQueuePage: skeleton loading, inbox empty state, ChevronRight indicator, separate
  reject zone card, icon buttons

Settings: - SettingsPage: SectionHeader helper, mail status badge with icon, Save icon on button,
  loading spinner, improved layout - SettingsDangerZone: TriangleAlert icon, confirm code styling

Dashboard: - DashboardPage: Info/AlertTriangle banners, meta row with separators, consistent icon
  sizes in StatCards - CostsPage: page subtitle, icons on StatCards, chart header with badge

Shared: - EmailDetailPanel: skeleton loader, section headers, draft amber block, meta pill badges
  with icons - DateRangeFilter: quick preset buttons (7T/30T/90T), Calendar icon, styled single-row
  layout

https://claude.ai/code/session_01VXKroNAoXGLoFjYfC89wCq


## v0.14.4 (2026-06-06)

### Bug Fixes

- Booking list date filter and endclothing spam block
  ([`46c605e`](https://github.com/siinanXD/Booking-email-check/commit/46c605ec4c4745c3433c47ad34cc92177dbf73bf))

to_date now includes the full calendar day so same-day mails appear in Buchungen. Exclude
  endclothing newsletters even when the LLM mislabels them as new_booking.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.14.3 (2026-06-06)

### Bug Fixes

- Align IMAP and CLI Outlook ingest with poll time window
  ([`0075979`](https://github.com/siinanXD/Booking-email-check/commit/0075979b2a093c0777377876a2980836cb33ed43))

Apply SINCE search for IMAP and resolve_poll_since_for_account in OutlookIngestionRunner so all mail
  paths use the same recent-mail window logic.

Co-authored-by: Cursor <cursoragent@cursor.com>

- Fetch recent inbox mails via Graph receivedDateTime filter
  ([`b67ab8b`](https://github.com/siinanXD/Booking-email-check/commit/b67ab8b260f6f8256a828499ca55b6555de28d1d))

Microsoft Graph ignores orderby without a matching receivedDateTime filter, so polls returned
  arbitrary old messages (duplicates=100) and missed new test mails.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.14.2 (2026-06-06)

### Bug Fixes

- Restore MongoDBSaver and optimize poll dedup queries
  ([`9200f00`](https://github.com/siinanXD/Booking-email-check/commit/9200f003e7ccf2117dd92e13382d112f980194e9))

Pin langgraph-checkpoint-mongodb with compatible pymongo, batch duplicate checks during mail
  polling, and add indexes for poll hot paths.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.14.1 (2026-06-06)

### Bug Fixes

- Enable mail polling in production (remove dev-only guard)
  ([`d0f530a`](https://github.com/siinanXD/Booking-email-check/commit/d0f530a75196eb764e5a4b0d10a3604b91c4de85))

### Chores

- Add script to clear stale WhatsApp token from MongoDB
  ([`b8b54f2`](https://github.com/siinanXD/Booking-email-check/commit/b8b54f2c8fb538249a6ed8dde9b43903a405c4e4))


## v0.14.0 (2026-06-06)

### Features

- Fix WhatsApp tenant credentials, add property suggestions to list
  ([`6cc8a5c`](https://github.com/siinanXD/Booking-email-check/commit/6cc8a5c15844dc0a53d2ad011e44c87ecba38968))

- WhatsApp test endpoints now always return HTTP 200 with success/error in body — prevents axios
  from swallowing the actual error message - platform_from_env no longer copies
  access_token/phone_number_id to tenant DB records; credentials always fall back to current env
  values - display_platform_settings uses env directly as fallback for credentials so the UI
  correctly shows platform-configured values - Frontend: remove access token and phone number ID
  fields from tenant settings UI (credentials are managed centrally via env) - Properties page:
  KI-Vorschläge now have '+ Zur Liste' button to add suggestion directly to Mitarbeiter-Empfänger
  form without navigating - Extract PropertySuggestionsCard component to stay under 300-line limit -
  Add migration script to clear stale tenant credential copies from DB - docs: add Railway
  deployment section to README - chore: expand .env.example with structured sections and required
  markers

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Refactoring

- Split 8 files exceeding 300-line CI limit
  ([`f5c8513`](https://github.com/siinanXD/Booking-email-check/commit/f5c8513ba7d89862f6e2544e15d9e60d89d1b6fb))

Extract constants, models, and helpers into private sub-modules so every source file stays under the
  300-line hard limit enforced by CI. Also add pymongo to pre-commit mypy deps so CommandListener
  stubs resolve correctly in the hook's isolated environment. All 320 unit tests pass; ruff, black,
  and mypy remain clean.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.13.4 (2026-06-06)

### Bug Fixes

- Correct frontend static dir path resolution (3 parent levels)
  ([`df55e3f`](https://github.com/siinanXD/Booking-email-check/commit/df55e3feb4cb348857b745aa5f0fe9d99a231f8f))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.13.3 (2026-06-06)

### Bug Fixes

- Remove startCommand from railway.toml, use Procfile instead
  ([`f303448`](https://github.com/siinanXD/Booking-email-check/commit/f3034483746dc845c9d6eff8976fbc757cc7b9b2))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- Add railway.toml to build frontend and serve via Flask
  ([`ad5137c`](https://github.com/siinanXD/Booking-email-check/commit/ad5137c090285414c340e5671a2c2532145833ba))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.13.2 (2026-06-06)

### Bug Fixes

- Correct langgraph-checkpoint-mongodb version constraint
  ([`f1f86e6`](https://github.com/siinanXD/Booking-email-check/commit/f1f86e64dfbce90dd92802fc41b57e8db9e508d0))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.13.1 (2026-06-06)

### Bug Fixes

- Add langgraph-checkpoint-mongodb dependency for production checkpointer
  ([`1f0b202`](https://github.com/siinanXD/Booking-email-check/commit/1f0b20204ea3fe545d7f55898001fdbbe3389d51))

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- Add Procfile for Railway deployment
  ([`d875567`](https://github.com/siinanXD/Booking-email-check/commit/d875567c556815984c8b584d2c7eba6a4d49cf42))

Gunicorn listens on Railway-injected $PORT (0.0.0.0).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.13.0 (2026-06-05)

### Features

- **ocr**: Paddleocr als Gemini-Fallback für Workflow-Vorschläge aus Bildern
  ([`a0ab755`](https://github.com/siinanXD/Booking-email-check/commit/a0ab755c28e790e4aff7a02154ffc2329adabd30))

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
  ([`534ff47`](https://github.com/siinanXD/Booking-email-check/commit/534ff474ce36a77eae72a36e7648ebfbd2b1e17e))

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
  ([`154453f`](https://github.com/siinanXD/Booking-email-check/commit/154453fe270c501a7f9ebbb18467066413b201d5))

Settings() requires env vars that exist locally via .env but not in GitHub Actions.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- **whatsapp**: Per-employee cleaning alerts in five languages
  ([`031a956`](https://github.com/siinanXD/Booking-email-check/commit/031a956712bc386e042dcb76f2a6c924f48ca93c))

Add per-employee locale for cleaning task WhatsApp templates (de/en/pl/it/es), localized review
  previews, and flag-based locale picker in the property UI.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Refactoring

- Remove dead code and move test mocks to ai/testing
  ([`c1fd93d`](https://github.com/siinanXD/Booking-email-check/commit/c1fd93d73847cb23fe96a1053418223c77f0eb32))

Drop unused repositories, models, and top-level stubs; relocate LLM and WhatsApp mocks for clearer
  production boundaries.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.11.0 (2026-06-05)

### Bug Fixes

- **vector**: Eliminate >20GB RAM blow-up in chunking and vector search
  ([`a6e6b8d`](https://github.com/siinanXD/Booking-email-check/commit/a6e6b8d32203abf80d78db0006f90f1ab20ae722))

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
  ([`993fcf1`](https://github.com/siinanXD/Booking-email-check/commit/993fcf1d7699929314eae1be8b967f98c76d69e4))

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
  ([`7f35528`](https://github.com/siinanXD/Booking-email-check/commit/7f3552802fb586edd50f59c9660ebf3ad582e0e9))

Die Checkbox-Stati standen noch auf [ ], obwohl die Features (Support-Tickets, Erst-Import,
  Admin-Kosten, Review-Nav, Abgeschlossen-Detail, Unterkuenfte, semantisches Chunking) laengst
  implementiert sind. Stati an den realen Code-Stand angeglichen.

Echt offen bleiben: Re-Ranking (bewusst zurueckgestellt, AGENTS.md), optionale UI-Politur (Phase
  8.6/10), manueller Meta-Template-Ops-Schritt, Onboarding-Hinweis.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

### Features

- **platform**: Gdpr Langfuse trace wipe, Phase-8 cost tests, deploy docs
  ([`d198e71`](https://github.com/siinanXD/Booking-email-check/commit/d198e71feaa98b31479e13281439c2dd1e7062e1))

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
  ([`db91489`](https://github.com/siinanXD/Booking-email-check/commit/db914892ed8a2b42412b5972dc738a3d52047bac))

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
  ([`88d221d`](https://github.com/siinanXD/Booking-email-check/commit/88d221d8b3be9ccbd34586cbdd303fff9253854a))

ButtonProps has no size field; use className for compact admin ticket actions.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **types**: Resolve mypy errors in entity_sync and reindex script
  ([`06c7065`](https://github.com/siinanXD/Booking-email-check/commit/06c7065d85bbaeda490368cb8231fd1e9d78e870))

Use Db/BookingExtraction types in ensure_property_from_extraction and narrow Mongo document fields
  to str before reindexing.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- **tenant**: Properties, review workflow, and dashboard performance
  ([`5853767`](https://github.com/siinanXD/Booking-email-check/commit/58537675b0a304f5ea211ff2d8aeba937400bced))

Batch Mongo aggregation replaces N+1 queries that made dashboard stats take minutes. Add properties
  API, review queue services, WhatsApp notifications, mail summaries, completed queue, date filters,
  and related tenant UI and test coverage.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **tenant**: Wave-1 planned features — support tickets, properties, ingest
  ([`8aaa627`](https://github.com/siinanXD/Booking-email-check/commit/8aaa62713fdc21ebe7e3fbfcee879225a74df6f8))

Add support ticket flow with admin WhatsApp alerts, property profiles with year stats, initial mail
  ingest window, semantic chunking groundwork, and dashboard/email UX improvements including Ground
  Zero review mode.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.9.0 (2026-06-04)

### Chores

- **mvp**: Verification docs, integration smoke, and quality fixes
  ([`f2a26ed`](https://github.com/siinanXD/Booking-email-check/commit/f2a26ed869c6f9a282646a600837e5ca35b8a45d))

Add PR_STEP_4_5 checklist, expand VERIFICATION for steps 4-5 and workflows, document eval baseline,
  fix live workflow triage test, mypy on admin aggregates, and optional Mongo embedding integration
  test.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Documentation

- Add GitHub PR merge instructions to PR_STEP_4_5
  ([`1a6200c`](https://github.com/siinanXD/Booking-email-check/commit/1a6200c99f80474190be40489d3be1e97144ebf6))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- **workflows**: Gemini multimodal suggest, preview, and workflow rubrics
  ([`7e5fd55`](https://github.com/siinanXD/Booking-email-check/commit/7e5fd55b139d3f3ae2c669d17f5e1bc840beb8ba))

Add Gemini client integration for screenshot-based workflow suggestions and multimodal extract
  preview, extend tenant workflow APIs and admin routes, and wire the dashboard with workflow rubric
  navigation. Includes CI fixes (ruff, mypy, pytest, frontend build) and temporary line-limit skips
  for oversized MVP branch files pending split before merge to main.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Refactoring

- Split oversized files for 300-line CI limit
  ([`7de840a`](https://github.com/siinanXD/Booking-email-check/commit/7de840a195b67ffdc5e849d5e60fcf2007f5d9d0))

Extract modules for workflows UI, API types, pipeline review, admin overview metrics, and tests.
  Remove temporary SKIP_FILES entries so check_max_file_lines enforces the limit on all production
  code.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.8.0 (2026-06-04)

### Features

- **admin**: Cross-tenant monitoring and cost observability
  ([`b3a15af`](https://github.com/siinanXD/Booking-email-check/commit/b3a15af2e5daf899f0b8e1c736c8155321c2f3cd))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **admin**: Llm config UI with prompt overrides and similarity top-k
  ([`853b62d`](https://github.com/siinanXD/Booking-email-check/commit/853b62db033b1c0de87a289e4fbb0388a7aa7466))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **admin**: Per-tenant mail and whatsapp connection tests
  ([`9bf92fc`](https://github.com/siinanXD/Booking-email-check/commit/9bf92fcc5d6bfafe3087f78c1c32d35e019df85a))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **admin**: Separate platform admin from tenant mail onboarding
  ([`428c144`](https://github.com/siinanXD/Booking-email-check/commit/428c144147233df8db7e7546eac8dcf8f5d92429))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **triage**: Llm gate for unknown senders, tenant workflows, admin charts
  ([`2324d0f`](https://github.com/siinanXD/Booking-email-check/commit/2324d0f1206a3dcdc4a6ec8fbac7151029a46dab))

Add optional cheap triage model before classify/extract, tenant workflow API/runtime, prompt history
  in admin LLM config, and observability charts plus cost-triage docs.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.7.0 (2026-06-03)

### Bug Fixes

- **grounding**: Filter false-positive guest name matches in draft
  ([`5aeafc4`](https://github.com/siinanXD/Booking-email-check/commit/5aeafc49d7bb5c9596a6a9da78f600d37b41fedf))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **pre-push**: Log atlas fallback, tighten name grounding, add edit-distance alert
  ([`2023b5e`](https://github.com/siinanXD/Booking-email-check/commit/2023b5e722ed1e20e16a55e1e1bc212b0d7c4cc2))

Log silent Atlas vector search fallback, require two token overlaps for guest names, and alert when
  draft edit distance exceeds 0.4.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **tests**: Use patch.object for atlas aggregate mocks
  ([`5885ad0`](https://github.com/siinanXD/Booking-email-check/commit/5885ad0d9a227573cdf03aab3108dd8ac1151a94))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- **dashboard**: Add timestamps and reviewed_today KPI
  ([`2e185a9`](https://github.com/siinanXD/Booking-email-check/commit/2e185a9eadf96da81e1eef953d9328e34e14d588))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **draft**: Platform tone and grounding instructions in prompt template
  ([`1c3ba8c`](https://github.com/siinanXD/Booking-email-check/commit/1c3ba8ce84559abc2039fa2451ea09d429c6eed0))

Extend draft.md with platform_tone, grounding rules, and response structure; add _platform_tone and
  _build_prompt helpers.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **feedback-loop**: Track draft edit distance via Langfuse scores
  ([`d729823`](https://github.com/siinanXD/Booking-email-check/commit/d72982336be775e042b43f2404d1bea3a85357d7))

Add LangfuseTracer.log_score, ReviewFeedbackTracker with difflib distance, and wire record() into
  WorkflowNodes.finalize on approval.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **grounding**: Add check_with_detail with guest and date validation
  ([`54e8ee9`](https://github.com/siinanXD/Booking-email-check/commit/54e8ee9367b34f2dc87bc79c029e4b07086febd8))

Extend grounding beyond booking refs to guest names and dates, returning GroundingResult with
  failed_fields and confidence while keeping check() as wrapper.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **indexing**: Alert on async indexing failures
  ([`b21738f`](https://github.com/siinanXD/Booking-email-check/commit/b21738f943dc793e99d6c065c5a5d32b2181fb25))

Wrap _index_async in try/except and report errors via AlertService with indexing: prefix.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **mail-sync**: Fast manual sync, expose errors, background reprocess
  ([`5732f72`](https://github.com/siinanXD/Booking-email-check/commit/5732f72ebe1bbfab50b959b2ad18712a9261be99))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **mongo**: Auto-create domain collections and tenant-scoped entities
  ([`186ea90`](https://github.com/siinanXD/Booking-email-check/commit/186ea90e90d981e97106c3eca1cc538196b8680c))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **vector-search**: Atlas vector search with in-memory fallback
  ([`156aa9d`](https://github.com/siinanXD/Booking-email-check/commit/156aa9da2d7b00d459e754a6586d125bdde4d8cd))

Add search_by_vector_atlas with OperationFailure fallback, SIMILARITY_USE_ATLAS setting, and
  AGENTS.md index setup note.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Testing

- **eval**: Add complaint and direct-booking eval cases
  ([`3aeaade`](https://github.com/siinanXD/Booking-email-check/commit/3aeaadefb070b4f1b00efd021cf39a7fd5042ace))

Add eval-009 for complaint with guest name and eval-010 for direct booking without platform; extend
  MockLLM responses.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.6.0 (2026-06-03)

### Bug Fixes

- **review-queue**: Add compound index on review_status + account_id + updated_at
  ([`4d4b8a3`](https://github.com/siinanXD/Booking-email-check/commit/4d4b8a3314daf31a4ed7efb57c587a998178148c))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Documentation

- Add Cursor Cloud dev environment notes to AGENTS.md
  ([`4a2f82d`](https://github.com/siinanXD/Booking-email-check/commit/4a2f82df802c3b81167349e4d44ce3521f21c536))

Co-authored-by: siinanXD <siinanXD@users.noreply.github.com>

### Features

- **alerts**: Retrieval empty alert test
  ([`be6cd2d`](https://github.com/siinanXD/Booking-email-check/commit/be6cd2d185bfafee693529ddc64b8a1a737008e5))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **entity-resolution**: Guest matching with confidence thresholds
  ([`3bf22f0`](https://github.com/siinanXD/Booking-email-check/commit/3bf22f002f98815887ed9a1fa82151bc062d07b7))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **retrieval**: Entity resolution, caps, and empty-booking alerts
  ([`0df908c`](https://github.com/siinanXD/Booking-email-check/commit/0df908cfed5bb743fa34c594b449e4eeebad71fc))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **review**: Reject alias and rejection flow tests
  ([`8c2e7eb`](https://github.com/siinanXD/Booking-email-check/commit/8c2e7ebb027c4a2b68f3a4c30ca0a1851e182538))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **review-queue**: Review repository aliases and persistence tests
  ([`1f0c453`](https://github.com/siinanXD/Booking-email-check/commit/1f0c45362d7ee671d3ceb6d6d63b555d57578947))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Testing

- **eval**: Add retrieval and entity resolution cases
  ([`e8fef07`](https://github.com/siinanXD/Booking-email-check/commit/e8fef0767a1e88dd5a9cc8a60c8bd59f52bc175a))

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.5.1 (2026-06-02)

### Bug Fixes

- **config**: Validate mongodb_uri format
  ([`250984c`](https://github.com/siinanXD/Booking-email-check/commit/250984c0db40ab69e57a284cee7d22424548384b))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **indexing**: Thread-backed asyncio.run fallback
  ([`31dd81c`](https://github.com/siinanXD/Booking-email-check/commit/31dd81c78e50c6e178ae421a589fda4dfda713b3))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **langfuse**: Log mail cost on active trace
  ([`c79f679`](https://github.com/siinanXD/Booking-email-check/commit/c79f679ad2633f42ce1ed1b0b52422b11b4b974e))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **mongo**: Singleton client with timeout
  ([`38f852e`](https://github.com/siinanXD/Booking-email-check/commit/38f852e06ea8ee591078219fb69f32426c639877))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **triage**: Ignore platform hint on unknown domain
  ([`7e3de9c`](https://github.com/siinanXD/Booking-email-check/commit/7e3de9c2da8df37eb2aff8bb61644b76b0f178e5))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Chores

- **deps**: Align ruff to 0.9.6
  ([`c03c004`](https://github.com/siinanXD/Booking-email-check/commit/c03c0043e051b500927c6e3bd97ef3f70be2bdc8))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **models**: Remove duplicate RetrievalResult model
  ([`0df9679`](https://github.com/siinanXD/Booking-email-check/commit/0df9679cdf4fdeb30b3bfce0def16c72ccd7f5d7))

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.5.0 (2026-06-02)

### Features

- Outlook OAuth onboarding, README refresh, and CI hygiene
  ([`bfffeae`](https://github.com/siinanXD/Booking-email-check/commit/bfffeaeb79c6877dced8884491932891b371b4a7))

Add delegated Outlook OAuth flow with mail sync/reprocess APIs, update README with architecture
  SVGs, split booking mail counters for the 300-line rule, and fix lint/import ordering for green
  CI.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.4.1 (2026-06-02)

### Bug Fixes

- Use app context database for settings wipe-all in tests
  ([`57916fb`](https://github.com/siinanXD/Booking-email-check/commit/57916fb141dcbb51ef08f931adadd048cddc0b35))

Route wipe-all through g.ctx.db so web tests use mongomock instead of connecting to localhost
  MongoDB.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Refactoring

- Reorganize backend and frontend for layered architecture
  ([`09707dc`](https://github.com/siinanXD/Booking-email-check/commit/09707dcb01f3beb75825a894efe14abe985d8934))

Move Python code under backend/ with api, ai, features, and infrastructure layers, restructure the
  dashboard into features/lib/shared, and align CI fixes including authStore tests and lint
  formatting.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.4.0 (2026-06-02)

### Features

- Multi-tenant SaaS with mail onboarding and automatic polling
  ([`2dadfd6`](https://github.com/siinanXD/Booking-email-check/commit/2dadfd6986a8f9364a411e0341658f06cfc56942))

Enable open registration with admin approval, strict account_id isolation across APIs and data,
  per-tenant IMAP/Outlook mailbox setup with onboarding wizard, and a dedicated poll worker for all
  active tenants.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.3.0 (2026-06-02)


## v0.2.1 (2026-06-02)

### Bug Fixes

- **auth**: Persist JWT blocklist in Mongo for multi-worker logout
  ([`a2dccb5`](https://github.com/siinanXD/Booking-email-check/commit/a2dccb507286c3aaadc69990a02dafd8642c2a19))

Logout tokens are stored in MongoDB with TTL so revocation works across Gunicorn workers. Fixes MyPy
  CI errors, Docker admin seed failures, demo credentials in .env.example, and missing docstrings.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- Whatsapp-benachrichtigungen und Einstellungs-Dashboard
  ([`9c69290`](https://github.com/siinanXD/Booking-email-check/commit/9c692901251d7719a3f475bca50b54cbdb6cacd8))

Nach Review-Freigabe werden WhatsApp-Templates an Host und Putzfrau versendet. Einstellungen und
  Unterkuenfte werden persistent in MongoDB gespeichert (mit .env-Vorausfuellung), inkl. Test-Button
  und Daten-Loeschen. Docker-Build und SPA-Auslieferung wurden repariert.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.2.0 (2026-06-02)

### Bug Fixes

- Align project with agent requirements
  ([`9c816b0`](https://github.com/siinanXD/Booking-email-check/commit/9c816b08b5e4ce5c8dd396114222b940016e5f9e))

- Stable env loading, gpt-5 drafts, and ingest helper scripts
  ([`382eeb1`](https://github.com/siinanXD/Booking-email-check/commit/382eeb1140d7ef7537ece1e6a0451ed2dd111db0))

Load .env from project root regardless of cwd. Omit temperature for gpt-5 draft models. Add venv
  path bootstrap and PowerShell wrapper for Outlook ingest, plus diagnose, live OpenAI smoke test,
  and Mongo booking mail listing scripts.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Documentation

- Document venv ingest, LLM_MODE, and helper scripts
  ([`6717b56`](https://github.com/siinanXD/Booking-email-check/commit/6717b56b446350a1544d703b2accd90ade46d5ce))

Expand README quickstart with project-root .env, PowerShell ingest wrapper, live vs mock mode, and
  diagnose/live-test/check scripts.

Co-authored-by: Cursor <cursoragent@cursor.com>

### Features

- Outlook Graph ingestion, LLM mock mode, and Langfuse tracing
  ([`830a7f2`](https://github.com/siinanXD/Booking-email-check/commit/830a7f254c8d06455848af5e656182f49f35cd9b))

Add Microsoft Graph adapters with MSAL device-code and application auth, CLI ingest, and OUTLOOK_*
  settings. Enable LLM_MODE=mock for dev without OpenAI quota. Use Langfuse @observe and
  langfuse.openai for automatic generations, sessions per mail, and embed traces.

- **web**: Add Flask JWT auth and dashboard API blueprints
  ([`c4d2504`](https://github.com/siinanXD/Booking-email-check/commit/c4d2504ab7308b40f27d9e934b90b6a91b9926f8))

Application factory with CORS, login/logout/me/refresh, dashboard stats, email list/detail, review
  approve/reject, costs API, QueryService, and tests/web suite.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **web**: Add React dashboard, Docker production, and frontend tests
  ([`05fb8c0`](https://github.com/siinanXD/Booking-email-check/commit/05fb8c03728c135ee141165c1dd7c9dbd2ceaf93))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **web**: Strict booking-mail detection and review queue fixes
  ([`1d79176`](https://github.com/siinanXD/Booking-email-check/commit/1d791768b9ce6877753f894d974324d765f7d6c2))

Filter lists and review to real Beds24/PMS mail, add dashboard booking KPIs, fix bookings API and
  workflow interrupt, and add maintenance/backfill scripts.

Co-authored-by: Cursor <cursoragent@cursor.com>

- **workflow**: Persist drafts, metrics, and Mongo checkpointer support
  ([`8c9d995`](https://github.com/siinanXD/Booking-email-check/commit/8c9d99512b1f55521cd1cc253d14416ddceaf909))

Add review and mail_metrics collections, resume_after_rejection, email list filters, and optional
  MongoDBSaver via build_checkpointer. MailCostTracker snapshots costs to Mongo.

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.1.0 (2026-06-02)

### Bug Fixes

- Pin Python to 3.11 only across project config
  ([`618f062`](https://github.com/siinanXD/Booking-email-check/commit/618f062cd2ba327acafefd03893b510898b9c1ca))

Co-authored-by: Cursor <cursoragent@cursor.com>

- **build**: Declare setuptools packages for flat-layout editable install
  ([`0a39f13`](https://github.com/siinanXD/Booking-email-check/commit/0a39f13fe92018547003e6ee2b043aedf42f572e))

Co-authored-by: Cursor <cursoragent@cursor.com>

### Documentation

- Pr description for MVP step 2
  ([`98935ec`](https://github.com/siinanXD/Booking-email-check/commit/98935ec677764bcc6a289dff2af49b1c9771d89b))

### Features

- **eval**: Dual-mode offline eval with field-wise extraction scoring
  ([`f837398`](https://github.com/siinanXD/Booking-email-check/commit/f83739850cf8b3a4f866021d4ad60271912215e5))

Co-authored-by: Cursor <cursoragent@cursor.com>
