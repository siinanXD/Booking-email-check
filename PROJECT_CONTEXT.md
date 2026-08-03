# PROJECT_CONTEXT.md — Booking-email-check

## Wofuer das gebaut wird

Automatische Verarbeitung von Buchungsmails: Mails werden gelesen,
klassifiziert, Buchungen und Stornos erkannt und aufbereitet. Dazu ein
WhatsApp-Bot und ein Admin-Frontend.

## Was daraus folgt und im Code nicht steht

**Das System verarbeitet echte personenbezogene Daten.** Mailadressen, Namen,
Buchungsdaten. Das ist der wichtigste Kontext ueberhaupt fuer dieses Projekt:

- Keine echten Mails in Testfixtures.
- Keine Mailinhalte und keine Adressen in Logs.
- `docs/compliance/` ist kein Beiwerk — dort liegen AVV, Datenpannenprozess
  und das Verzeichnis der Verarbeitungstaetigkeiten.

**Modellaufrufe kosten Geld.** Es gibt `docs/COST_TRIAGE.md` und
`backend/infrastructure/observability/mail_cost.py`. Eine Aenderung, die pro
Mail einen zusaetzlichen Modellaufruf ausloest, ist eine Kostenentscheidung
und keine technische Kleinigkeit.

## Stand

Branch `feat/stornos-sichtbar`, 395 Commits. Das groesste und reifste Projekt
im Workspace: eigenes `AGENTS.md`, `.claude/`, `.cursor/`, 29 Dokumente unter
`docs/`, 164 Testdateien.

Weitere Notizen: `C:\Dev\Knowledge\01 Projects\Booking-email-check.md`

TODO: Welche Instanz laeuft produktiv, und wer hat Zugriff auf die
Produktionsdatenbank? Aus dem Repository geht das nicht hervor.
