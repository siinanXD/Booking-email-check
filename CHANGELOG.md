# CHANGELOG


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
