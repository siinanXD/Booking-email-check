# Verzeichnis von Verarbeitungstätigkeiten (Art. 30 DSGVO)

**Verantwortlicher:** Sinan Kahraman, Mühlenstraße 44, 53879 Euskirchen, Deutschland — sinanKahraman@hotmail.de
**Stand:** Juli 2026 · Bei Änderungen am Dienst aktualisieren.

Der Dienst „Mail Assistant AI" tritt in zwei Rollen auf:
- **Verantwortlicher** für Daten der eigenen Kunden (Mandanten-Konten, Support, Abrechnung).
- **Auftragsverarbeiter (Art. 28)** für Gästedaten, die in den Postfächern der Mandanten enthalten sind (→ Verzeichnis nach Art. 30 Abs. 2).

## Übersicht Subunternehmer / Empfänger

| Anbieter | Zweck | Sitz/Region | Drittlandtransfer |
|---|---|---|---|
| Railway Corp. | Applikations-Hosting | EU West (Amsterdam) | SCCs / DPF (Support-Zugriff) |
| MongoDB, Inc. (Atlas) | Datenbank | Cluster: AWS eu-central-1 (Frankfurt) | Support-Zugriff ggf. USA, SCCs |
| OpenAI, L.L.C. | LLM-Klassifikation, -Extraktion, -Entwürfe | USA | SCCs / DPF; kein Training mit API-Daten |
| Meta Platforms Ireland Ltd. | WhatsApp Business API | Irland/USA | SCCs / DPF |
| Microsoft Ireland Operations Ltd. | Graph-API (Postfach-Zugriff der Mandanten) | Irland/EU | Mandanten-eigene M365-Verträge |
| Functional Software, Inc. (Sentry) | Fehler-Monitoring (PII maskiert) | USA | SCCs / DPF |
| Langfuse GmbH | LLM-Observability (PII maskiert) | Deutschland (Cloud-Region prüfen) | — |

## Verarbeitungstätigkeiten

### 1. Mandanten-Kontoverwaltung (Rolle: Verantwortlicher)
- **Zweck:** Registrierung, Login, Vertragsdurchführung, Admin-Freigabe
- **Betroffene:** Mandanten (Gastgeber/Hotels), deren Mitarbeitende
- **Daten:** Name, E-Mail, Telefon, Firmenangaben, Passwort-Hash, Rollen, Login-Metadaten
- **Empfänger:** Railway, MongoDB
- **Löschung:** Bei Konto-Löschung; Admin-Löschfunktion vorhanden
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b

### 2. E-Mail-Ingestion und KI-Verarbeitung (Rolle: Auftragsverarbeiter)
- **Im Auftrag von:** jeweiliger Mandant
- **Zweck:** Abruf der Buchungs-E-Mails, Klassifikation, Extraktion von Buchungsdaten, KI-Antwortentwürfe (Versand erst nach Freigabe)
- **Betroffene:** Gäste der Mandanten, sonstige E-Mail-Absender
- **Daten:** E-Mail-Inhalte und -Metadaten, Namen, Kontaktdaten, Reisedaten, Buchungsnummern
- **Empfänger:** Railway, MongoDB, OpenAI; Postfach-Zugriff via Microsoft Graph/IMAP
- **Sicherheit:** Postfach-Zugangsdaten verschlüsselt (Fernet), TLS, Mandantentrennung per account_id, PII-Maskierung im Monitoring
- **Löschung:** Nach Weisung des Mandanten; Gast-Export/-Löschung über die App

### 3. WhatsApp-Benachrichtigungen (Rolle: Auftragsverarbeiter)
- **Zweck:** Benachrichtigung von Mandanten-Personal (Buchungen, Reinigung, Status)
- **Betroffene:** Mitarbeitende/Beauftragte der Mandanten
- **Daten:** Telefonnummer (E.164), Nachrichteninhalt (Template-Parameter)
- **Empfänger:** Meta (WhatsApp Business API)
- **Löschung:** Outbox-Einträge rotierend; Empfängerlisten durch Mandant pflegbar

### 4. Putzplan / Reinigungsaufgaben (Rolle: Auftragsverarbeiter)
- **Zweck:** Planung von Reinigungen aus Buchungsdaten, Aufgaben an Reinigungspartner
- **Betroffene:** Reinigungspartner der Mandanten, mittelbar Gäste (An-/Abreisedaten)
- **Daten:** Name, Telefon der Partner; Termine, Unterkunftsbezeichnungen
- **Empfänger:** Railway, MongoDB, Meta (Benachrichtigung)

### 5. Support-Tickets (Rolle: Verantwortlicher)
- **Zweck:** Kundensupport
- **Daten:** Ticketinhalt, Kontaktdaten des Mandanten
- **Empfänger:** Railway, MongoDB, ggf. Meta (Admin-Alert per WhatsApp)

### 6. Fehler- und Qualitäts-Monitoring (Rolle: beide)
- **Zweck:** Betriebsstabilität, Fehlerdiagnose, LLM-Qualität/-Kosten
- **Daten:** Fehlermeldungen, Traces, Token-/Kostenmetriken — **PII vor Übermittlung maskiert** (`backend/core/utils/pii_mask.py`)
- **Empfänger:** Sentry, Langfuse
- **Löschung:** Retention gemäß Anbieter-Einstellung

### 7. Audit-Logging (Rolle: Verantwortlicher)
- **Zweck:** Nachvollziehbarkeit von Admin-Aktionen, Auto-Freigaben (Rechenschaftspflicht Art. 5 Abs. 2)
- **Daten:** Nutzer-ID, Aktion, Zeitstempel
- **Empfänger:** MongoDB

## Technische und organisatorische Maßnahmen (Kurzfassung, Art. 32)

TLS für alle Verbindungen · Verschlüsselung der Postfach-/API-Zugangsdaten at rest (Fernet) · Passwort-Hashing (PBKDF2) · JWT mit Token-Widerruf · Mandantentrennung auf Datenbankebene · Rollenmodell (Tenant/Platform-Admin) · Rate-Limiting · Security-Header/HSTS · PII-Maskierung im Monitoring · Audit-Log · menschliche Freigabe vor E-Mail-Versand (Auto-Freigabe nur opt-in mit Konfidenzschwelle und Undo-Fenster).
