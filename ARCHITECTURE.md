# ARCHITECTURE.md — Booking-email-check

Die Architektur ist beschrieben in **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.
Ergaenzend: `docs/SPEC.md`, `docs/WHATSAPP_BOT_SPEC.md`, `docs/DEPLOYMENT.md`.

Diese Datei ist nur ein Wegweiser und wiederholt den Inhalt bewusst nicht.

## Grobaufbau in einem Absatz

`backend/` ist nach Schichten geordnet: `api/` (Endpunkte), `features/`
(Fachlichkeit, u.a. `whatsapp_bot/`), `ai/` (Modellanbindung),
`infrastructure/` (Anbindung nach aussen, u.a. `observability/`), `core/`
(Gemeinsames), `application/`. `frontend/` ist eine React-Anwendung mit Vite.
`tests/` liegt getrennt und bildet die Backend-Struktur nach.
