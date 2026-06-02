# CHANGELOG


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
