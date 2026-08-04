# .ai — Booking-email-check

Projektspezifische Konfiguration fuer das Agent-System.
Erzeugt am 2026-08-04 von `bootstrap_project.py`.

## Was hier liegt

| Pfad | Inhalt |
|---|---|
| `project.yaml` | erkannter Stack und Gates — **nicht geraten**, aus dem Bestand. Ohne Branch: der ist dynamisch. |
| `agent-overrides.yaml` | Anpassungen globaler Agenten. Leer ist der Normalfall. |
| `model-routing.yaml` | Abweichungen von der globalen Modellwahl |
| `quality-gates.yaml` | Gates dieses Projekts |
| `development-policy.yaml` | aktivierte Policies und Abweichungen |
| `agents/` | projektspezifische Agenten |
| `context/` | Projektkontext fuer Agenten |
| `prompts/` | erprobte Prompts fuer dieses Projekt |
| `workflows/` | projektspezifische Ablaeufe |
| `memory/` | dauerhafter Zustand zwischen Laeufen |
| `decisions/` | Entscheidungen, die kein voller ADR sind |
| `evaluations/` | Auswertungen |
| `research/` | Rechercheergebnisse, nach Quelle geordnet |

## Verhaeltnis zu den anderen Dokumenten

`AGENTS.md` im Wurzelverzeichnis ist die **Projektbeschreibung** und bleibt
die einzige Quelle dafuer. Dieses Verzeichnis enthaelt die **Konfiguration**
des Agent-Systems — was der Orchestrator liest, nicht was ein Mensch liest.

Wer wissen will, was das Projekt ist: `AGENTS.md`.
Wer wissen will, wie Agenten hier arbeiten: dieses Verzeichnis.

## Erkannter Stand

- Remote: https://github.com/siinanXD/Booking-email-check.git
- Paketmanager: npm
- Testlaeufer: pytest, vitest
- Lint: black, ruff
- Typpruefung: mypy, tsc

## Neu erzeugen

```powershell
python C:\Dev\Shared\Scripts\bootstrap_project.py --path C:\Dev\Repositories\Booking-email-check
```

Bestehende Dateien werden dabei **nicht** ueberschrieben.
