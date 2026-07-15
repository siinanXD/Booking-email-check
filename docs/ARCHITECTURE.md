# Architecture

## Repository layout

```
frontend/          React SPA (feature modules)
backend/           Python application
  api/             HTTP layer (Flask blueprints, auth, schemas)
  ai/              LLM pipeline (workflows, services, prompts, domain)
  features/        Product features (mail, notifications, platform)
  infrastructure/  Repositories, adapters, observability
  core/            Config, models, shared utils
  application/     Workflow ports (ingestion, review)
scripts/           CLI and maintenance scripts
tests/             Pytest suite
docs/              Documentation
```

## Import rules

| Layer | May import |
|-------|------------|
| `backend/api/` | `features/`, `application/`, `core/config` |
| `backend/features/` | `ai/`, `infrastructure/`, `core/` |
| `backend/ai/` | `infrastructure/repositories`, `core/models`, `ai/domain` |
| `backend/infrastructure/` | `core/` only |
| `backend/application/` | `ai/workflows`, `features/` (minimal) |

**Forbidden:** `infrastructure/` → `api/`; `ai/services` → `features/`; cross-feature imports in the frontend (use `shared/` and `lib/`).

All Python imports use the `backend.*` prefix.

## File size rule

No `.py`, `.ts`, or `.tsx` file may exceed **300 lines**. CI runs `python scripts/check_max_file_lines.py`.

## Where to put new code

- New REST endpoint → `backend/api/blueprints/` + schema in `backend/api/schemas/`
- New LLM step → `backend/ai/workflows/nodes/` or `backend/ai/services/`
- New mail/notification/platform logic → `backend/features/<area>/`
- New DB access → `backend/infrastructure/repositories/`
- New React screen → `frontend/src/features/<feature>/`
- Shared UI → `frontend/src/shared/`
- API client / types → `frontend/src/lib/`
- Colors → use the design tokens (`text-ink`, `bg-surface`, `border-border`,
  `text-brandink`, `bg-warnbg`/`text-warntext`, …), never hardcoded palette
  classes (`text-slate-*`, `bg-amber-*`) — see README "Frontend theming". Tokens
  honor the light/dark switch; palette classes wash out in dark mode. The
  fixed-dark sidebar uses `rail*` tokens.

## Entrypoints

- WSGI: `wsgi.py` → `backend.api.app:create_app`
- Flask dev: `flask --app backend.api.app:create_app run`
- Tests: `pytest` with `pythonpath = ["."]`
