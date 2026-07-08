# WhatsApp-Bot als Frontend – Spezifikation & Meta-Setup

Masterspezifikation für das WhatsApp-Interface des Booking-SaaS. Umsetzung in
8 PRs (siehe „Umsetzungsreihenfolge“). Referenz für alle WhatsApp-Bot-PRs.

## Anpassungen an dieses Repo (verbindlich, überschreiben Teil 1)

Die Spezifikation unten wurde extern formuliert. Folgende Punkte weichen von
den harten Repo-Constraints ab und gelten in der angepassten Form:

| Spezifikation (Original) | Gilt in diesem Repo |
| --- | --- |
| Python 3.12, FastAPI | **Python 3.11, Flask-Blueprint** (`backend/api/blueprints/whatsapp_webhook.py`) – bestehende App-Factory, kein zweiter Service |
| Motor (async Mongo) | **PyMongo** über bestehende Repositories (`backend/infrastructure/repositories/`) |
| Eigene Collections `tenants`/`users` | Bestehende Multi-Tenancy: `account_id` + `with_account_filter()`; WhatsApp-Nummern hängen an bestehenden `users` (`whatsapp_phone_e164`) bzw. neuen Employee-Records |
| Env-Namen `WHATSAPP_TOKEN`, `WHATSAPP_VERIFY_TOKEN` | Bestehende Namen: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_PHONE_NUMBER_ID` (siehe `.env.example`) |
| Webhook-Pfad `/webhook/whatsapp` | Bestehender Pfad: **`/api/whatsapp/webhook`** |
| Sofort 200 + Background-Task | Flask synchron; Verarbeitung leichtgewichtig halten, langlaufende Schritte über bestehende Background-Jobs (`backend/api/background_jobs.py`) |
| Sentry/Whisper/WeasyPrint neu einführen | Nur bei Bedarf im jeweiligen PR ergänzen und pinnen (`pyproject.toml`) |

Unverändert gültig (deckt sich mit Repo-Regeln): Nachrichteninhalt = Daten,
keine Schreiboperation ohne Bestätigungs-Button, Tenant-Isolation je Query,
LLM nur für Intent/Extraktion, 300-Zeilen-Limit, Conventional Commits.

Bereits vorhandene Bausteine (wiederverwenden, nicht neu bauen):

- `backend/api/blueprints/whatsapp_webhook.py` – GET-Verifizierung
  (`hub.challenge`), POST mit HMAC-Prüfung (`X-Hub-Signature-256`,
  fail-closed in Produktion), Account-Auflösung über `phone_number_id`.
- `backend/features/notifications/whatsapp_client.py` – Outbound-Client
  (Protocol `WhatsAppClient`, `MetaCloudWhatsAppClient`,
  `DisabledWhatsAppClient`), Meta-Fehlercode-Hinweise.
- `backend/features/notifications/whatsapp_incoming_service.py` – Parsing
  eingehender Text-Nachrichten, Credential-Auflösung (DB überschreibt `.env`),
  Weiterleitung an den Host; **Echo-Modus** (`WHATSAPP_ECHO_MODE=true`) für
  den isolierten Test des Meta-Webhook-Kreislaufs (Schritt 1).
- `backend/ai/testing/mock_whatsapp.py` – Mock für Tests.
- `docs/whatsapp_templates_cleaning.md` – bestehende Meta-Templates.

## Umsetzungsstand: Konversations-Bot (`backend/features/whatsapp_bot/`)

Der Bot ist implementiert und wird über `WHATSAPP_BOT_ENABLED=true`
aktiviert (Vorrangkette im Webhook: Echo > Bot > Host-Weiterleitung).
Sitzungsfreie Nachrichten (Service-Konversationen) — **keine Meta-Templates
nötig**, da der Bot nur auf eingehende Nachrichten antwortet
(24h-Kundenservice-Fenster). Templates braucht weiterhin nur der
proaktive Versand (`notification_service`, `docs/whatsapp_templates_cleaning.md`).

| Baustein | Modul |
| --- | --- |
| Sender-Auflösung `wa_id` → Account + Rolle | `sender_resolver.py` (Dashboard-User → owner/manager, Putzpartner → cleaner) |
| Rollen-Matrix | `permissions.py` |
| Intent-Erkennung (LLM, structured output, Injection-Schutz) | `intent_service.py` |
| Deterministische Zeitangaben (heute/morgen/KW/Datum) | `dates.py` |
| Nachrichten-Templates (Emoji, *fett*, Limits) | `messages.py` |
| Putzplan + Excel-Anhang, eigene Termine, Buchungen | `handlers_read.py` |
| Mitarbeiter-/Objekt-CRUD mit Bestätigungs-Buttons | `handlers_admin.py` |
| Versand: Text, Buttons, Dokument (Media-Upload) | `messenger.py` |
| Sprachnachrichten (Whisper, mockbar) | `transcription.py` |
| Routing, Dedupe, Pending-Actions, Audit | `service.py` |
| Konversations-State (TTL 24h) | `infrastructure/repositories/whatsapp_conversation_repository.py` |
| Audit-Log | `infrastructure/repositories/whatsapp_audit_repository.py` |
| Wochen-Berichte (Putzplan Mo, Review Fr) | `weekly_reports.py` + `api/background_jobs.py` |

### Geplante Wochen-Berichte

Hintergrund-Thread (Fälligkeitsprüfung alle 5 Minuten, Zeitzone
Europe/Berlin, Dedupe über `whatsapp_report_markers` — genau ein Versand
pro Account und Kalenderwoche, auch bei Restarts/mehreren Workern):

- **Montags 07:00** (`WHATSAPP_WEEKLY_PUTZPLAN_ENABLED`): aktueller
  Wochen-Putzplan als Text + Excel an alle WhatsApp-Empfänger des Accounts.
- **Freitags 16:00** (`WHATSAPP_WEEKLY_REVIEW_ENABLED`): Wochen-Review —
  Übernachtungen (anteilig je Woche), An-/Abreisen, Umsatz (Summe der
  Preise aller Anreisen der Woche), meistgebuchtes Objekt, erledigte
  Reinigungen.

Wochentag/Uhrzeit sind konfigurierbar (`*_WEEKDAY` 0=Mo…6=So, `*_HOUR`).
Versand erfolgt als Session-Nachricht; ist das 24h-Fenster geschlossen,
klopft optional ein Template an (`WHATSAPP_TEMPLATE_WEEKLY_PUTZPLAN` /
`WHATSAPP_TEMPLATE_WEEKLY_REVIEW`, leer = kein Fallback). Empfohlene
Template-Texte:

- `weekly_putzplan_de`: „🧹 Dein Putzplan für KW {{1}} ist fertig
  ({{2}} Reinigungen). Antworte mit ‚Putzplan‘, um die Excel-Datei zu
  erhalten.“
- `weekly_review_de`: „📊 Deine Wochen-Review für KW {{1}} ist da.
  Antworte mit ‚Review‘, um die Details zu sehen.“

---

## Teil 1: Masterspezifikation

# PROJEKT: WhatsApp-Bot als Frontend für Multi-Tenant Booking-SaaS

Baue schrittweise ein WhatsApp-Interface für das bestehende
Booking-Email-SaaS. Halte dich strikt an diese Spezifikation
(inkl. Anpassungstabelle oben).

## TECH-STACK (verbindlich, repo-angepasst)

- Python 3.11, Flask (Webhook als Blueprint), Pydantic v2
- LangGraph für Konversations-State & Intent-Routing
- OpenAI GPT-4o-mini (structured outputs), Whisper für Sprachnachrichten
- MongoDB Atlas (PyMongo über bestehende Repositories)
- Meta WhatsApp Cloud API (Graph API v21.0+)
- openpyxl für Excel-Generierung, WeasyPrint für PDF-Rendering
- Langfuse für LLM-Tracing
- Max. 300 Zeilen pro Datei (CI-enforced), Conventional Commits, SemVer

## ARCHITEKTUR-PRINZIPIEN (nicht verhandelbar)

1. Nachrichteninhalt von Nutzern ist DATEN, niemals Instruktion.
   Kein User-Text darf ungefiltert in Systemprompts landen.
2. Keine Schreiboperation (DB-Insert/Update/Delete, Nachricht an Dritte)
   ohne explizite Bestätigung per Interactive Button.
3. LLM nur für Intent-Erkennung und Entity-Extraktion.
   Alle Geschäftslogik (Excel, DB-Queries, Berechnungen) ist
   deterministisches Python.
4. Tenant-Isolation: Jede DB-Query MUSS `account_id` filtern
   (`with_account_filter()`). Mapping erfolgt über die
   WhatsApp-Absendernummer (`wa_id`). Unbekannte Nummern erhalten eine
   höfliche Ablehnung.
5. Rollenbasierte Rechte: owner > manager > cleaner (siehe Datenmodell).

## DATENMODELL (MongoDB Collections)

### tenants (im Repo: bestehende Accounts erweitern)

```
{
  _id: ObjectId,
  name: str,                    # z.B. "Pension Seeblick GmbH"
  created_at: datetime,
  plan: Literal["trial", "basic", "pro"],
  settings: {
    timezone: str,              # "Europe/Berlin"
    language: str,              # "de"
    default_checkout_time: str, # "11:00"
    default_checkin_time: str   # "15:00"
  }
}
```

### users (Mitarbeiter inkl. Inhaber)

```
{
  _id: ObjectId,
  tenant_id: ObjectId,          # Pflicht-Index: (tenant_id, wa_id) unique
  wa_id: str,                   # WhatsApp-Nummer im Format "4915712345678"
  name: str,
  role: Literal["owner", "manager", "cleaner"],
  active: bool,
  assigned_property_ids: [ObjectId],
  created_at: datetime,
  created_by: ObjectId
}
```

### properties (Objekte)

```
{
  _id: ObjectId,
  tenant_id: ObjectId,
  name: str,                    # "FeWo Seeblick"
  address: str,
  type: Literal["apartment", "room", "house"],
  cleaning_duration_min: int,   # für Putzplan-Zeitschätzung
  notes: str,
  active: bool
}
```

### bookings (bereits vorhanden aus Email-Pipeline – erweitern, nicht ersetzen)

```
{
  _id: ObjectId,
  tenant_id: ObjectId,
  property_id: ObjectId,
  guest_name: str,
  checkin: datetime,
  checkout: datetime,
  source_email_id: ObjectId,    # Referenz auf geparste Original-Mail
  status: Literal["confirmed", "cancelled", "pending"],
  price: Decimal128,
  raw_summary: str              # LLM-Zusammenfassung der Mail
}
```

### conversations (LangGraph-State pro WhatsApp-Chat)

```
{
  _id: ObjectId,
  tenant_id: ObjectId,
  wa_id: str,
  state: dict,                  # serialisierter Graph-State
  pending_action: dict | null,  # wartende Bestätigung {action, payload, expires_at}
  updated_at: datetime          # TTL-Index: 24h
}
```

### audit_log

```
{
  _id, tenant_id, wa_id, action, payload, timestamp, confirmed: bool
}
```

## INTENTS (Pydantic, structured output)

```python
class UserIntent(BaseModel):
    action: Literal[
        "putzplan_erstellen",
        "buchungen_anzeigen",
        "buchung_details",
        "mitarbeiter_anlegen", "mitarbeiter_bearbeiten", "mitarbeiter_liste",
        "objekt_anlegen", "objekt_bearbeiten", "objekt_liste",
        "objekt_zuweisen",
        "hilfe", "unklar"
    ]
    zeitraum_start: date | None
    zeitraum_ende: date | None
    person_name: str | None
    person_phone: str | None
    person_role: str | None
    property_name: str | None
    booking_ref: str | None
    freitext: str | None          # Rest-Kontext für Rückfragen
```

Regeln:

- Relative Zeitangaben („nächste Woche“, „morgen“) deterministisch in
  Python auflösen (Timezone des Tenants), NICHT vom LLM raten lassen.
- Bei `action="unklar"` oder fehlenden Pflichtfeldern: Rückfrage senden,
  State in `conversations` speichern, auf Antwort warten (LangGraph interrupt).

## ROLLEN-MATRIX

| Aktion | owner | manager | cleaner |
| --- | --- | --- | --- |
| putzplan_erstellen | ✓ | ✓ | ✗ |
| putzplan_eigener_abruf | ✓ | ✓ | ✓ |
| buchungen_anzeigen | ✓ | ✓ | ✗ |
| mitarbeiter_anlegen | ✓ | ✗ | ✗ |
| mitarbeiter_bearbeiten | ✓ | ✓ (nur cleaner) | ✗ |
| objekt_anlegen/bearbeiten | ✓ | ✓ | ✗ |
| objekt_zuweisen | ✓ | ✓ | ✗ |

Verstöße: freundliche Meldung „Dafür fehlt dir die Berechtigung.
Wende dich an [Owner-Name].“ – niemals Fehlermeldung mit Stacktrace.

## WHATSAPP-NACHRICHTEN-DESIGN

Formatierungsregeln (WhatsApp unterstützt `*fett*`, `_kursiv_`,
`~durchgestrichen~`, Monospace, Zeilenumbrüche, Emojis):

- Jede Bot-Antwort beginnt mit einem thematischen Emoji als visuellem Anker
- Max. ~10 Zeilen pro Nachricht, lieber aufteilen
- Wichtige Werte (Namen, Daten, Zahlen) immer `*fett*`
- Listen mit Emoji-Bullets statt Bindestrichen
- Interactive Buttons für Bestätigungen (max. 3 Buttons, Label max. 20 Zeichen)
- List Messages für Auswahl aus >3 Optionen (max. 10 Einträge)

### Template-Bibliothek (Jinja2-Templates in `backend/ai/prompts/whatsapp/` bzw. `templates/whatsapp/`)

`willkommen.txt`

```
👋 Hallo *{{ name }}*!

Ich bin dein Assistent für *{{ tenant_name }}*.

Das kann ich für dich tun:
🧹 Putzpläne erstellen
📅 Buchungen anzeigen
👥 Mitarbeiter verwalten
🏠 Objekte verwalten

Schreib mir einfach, z. B.:
_"Putzplan für nächste Woche"_
```

`putzplan_fertig.txt`

```
🧹 *Putzplan {{ kw }}. KW*
📆 {{ start }} – {{ ende }}

✅ *{{ anzahl }} Reinigungen* geplant
🏠 {{ objekte_anzahl }} Objekte
⏱️ Gesamt ca. *{{ stunden }} Std.*

📎 Die Excel-Datei kommt gleich als Anhang.
[Buttons: "📤 An Team senden" | "✏️ Ändern" | "❌ Verwerfen"]
```

`buchung_details.txt`

```
📅 *Buchung {{ ref }}*

👤 Gast: *{{ guest_name }}*
🏠 Objekt: *{{ property_name }}*
🛬 Check-in: *{{ checkin }}*
🛫 Check-out: *{{ checkout }}*
💶 Preis: *{{ price }} €*
📧 Quelle: {{ source }}

[Buttons: "📄 Original-Mail" | "🧹 Zum Putzplan" | "🔙 Zurück"]
```

`mitarbeiter_bestaetigen.txt`

```
👥 *Neuen Mitarbeiter anlegen?*

📛 Name: *{{ name }}*
📱 Nummer: *{{ phone }}*
🎖️ Rolle: *{{ role_label }}*
🏠 Objekte: {{ properties | join(", ") }}

[Buttons: "✅ Anlegen" | "✏️ Ändern" | "❌ Abbrechen"]
```

`fehler_berechtigung.txt`

```
🔒 Dafür fehlt dir leider die Berechtigung.
Bitte wende dich an *{{ owner_name }}*.
```

`unbekannte_nummer.txt`

```
👋 Hallo! Deine Nummer ist noch keinem Konto zugeordnet.
Wenn du {{ product_name }} nutzen möchtest:
🌐 {{ website }}
```

### Interactive Buttons – API-Payload-Beispiel

```json
{
  "messaging_product": "whatsapp",
  "to": "{{ wa_id }}",
  "type": "interactive",
  "interactive": {
    "type": "button",
    "body": { "text": "..." },
    "action": { "buttons": [
      { "type": "reply", "reply": { "id": "confirm_putzplan_{{ id }}", "title": "✅ Anlegen" }},
      { "type": "reply", "reply": { "id": "edit_{{ id }}", "title": "✏️ Ändern" }},
      { "type": "reply", "reply": { "id": "cancel_{{ id }}", "title": "❌ Abbrechen" }}
    ]}
  }
}
```

Button-IDs sind strukturiert: `{aktion}_{entity}_{uuid}` → deterministisches
Routing im Webhook ohne LLM-Aufruf.

## EXCEL-PUTZPLAN (openpyxl)

- Sheet `Putzplan KW{{ kw }}`
- Spalten: Datum | Wochentag | Objekt | Check-out | nächster Check-in |
  Zeitfenster | Zugewiesen an | Dauer (Min) | Notizen | Erledigt ☐
- Header: fett, Hintergrund `#1F4E79`, weiße Schrift, AutoFilter, Freeze Pane A2
- Zeilen abwechselnd weiß/`#F2F2F2`, Spaltenbreiten auto-fit
- Warnzeile rot markieren, wenn Zeitfenster < `cleaning_duration_min`
- Fußzeile: „Erstellt am {{ now }} via {{ product_name }}“

## WEBHOOK-FLOW (Flask, `/api/whatsapp/webhook`)

- `GET /api/whatsapp/webhook` → `hub.challenge`-Verifizierung
  (`WHATSAPP_WEBHOOK_VERIFY_TOKEN` aus env)
- `POST /api/whatsapp/webhook` →
  1. `X-Hub-Signature-256` gegen `WHATSAPP_APP_SECRET` prüfen (sonst 403;
     fail-closed in Produktion, Dev-Bypass ohne Secret)
  2. Schnell 200 zurückgeben; langlaufende Verarbeitung über
     Background-Jobs
  3. `wa_id` → User-Lookup → `account_id` + Rolle
  4. `message.type` unterscheiden:
     - `text` → Intent-Pipeline
     - `audio` → Media-Download → Whisper → Intent-Pipeline
     - `interactive.button_reply` → deterministisches Button-Routing
     - `interactive.list_reply` → deterministisches Listen-Routing
  5. `pending_action` in `conversations` prüfen (Bestätigungs-Kontext)
  6. Antwort über Graph API senden, alles in `audit_log` schreiben

## MEDIA-VERSAND (Excel/PDF)

1. `POST https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/media`
   (multipart, `type=document`) → `media_id`
2. `POST /messages` mit `type=document`, `document.id=media_id`,
   `document.filename="Putzplan_KW{{ kw }}.xlsx"`
3. Temp-Dateien nach Versand löschen

## ENV-VARIABLEN (bereits in `.env.example`, Repo-Namen)

```
WHATSAPP_ACCESS_TOKEN=            # System User Access Token (permanent!)
WHATSAPP_PHONE_NUMBER_ID=         # numerische ID, NICHT die Rufnummer
WHATSAPP_WEBHOOK_VERIFY_TOKEN=    # selbst gewählter String
WHATSAPP_APP_SECRET=              # für Signatur-Prüfung (Pflicht in Prod)
WHATSAPP_ECHO_MODE=false          # true = Echo-Bot (nur Meta-Kreislauf-Test)
OPENAI_API_KEY= / MONGODB_URI= / LANGFUSE_*  # wie gehabt
```

## TESTS (pytest, jede Schicht isoliert)

- Webhook-Signaturprüfung (gültig/ungültig/fehlend) ✓ vorhanden
- Intent-Parsing mit gemockten LLM-Responses (keine echten API-Calls in CI)
- Tenant-Isolation: User A darf niemals Daten von Tenant B sehen (Pflichttest!)
- Rollen-Matrix vollständig abtesten
- Putzplan-Generator: Zeitfenster-Kollisionen, leere Wochen, Timezone-Kanten
- Button-ID-Routing

## UMSETZUNGSREIHENFOLGE (jeweils als eigener PR)

1. Webhook-Skeleton + Verifizierung + Signaturprüfung + **Echo-Bot** ← dieser PR
2. Datenmodell + Repositories + Tenant-Resolution über `wa_id`
3. Intent-Pipeline (LangGraph) + Rückfrage-Loop
4. Putzplan-Tool (Excel) + Media-Upload + Templates
5. Mitarbeiter-/Objekt-CRUD mit Bestätigungs-Buttons + Rollen
6. Buchungsanzeige (List Messages) + Original-Mail als PDF
7. Whisper-Integration für Sprachnachrichten
8. Audit-Log, Rate-Limiting, Hardening

---

## Teil 2: Meta-Einrichtung Schritt für Schritt

### A. Voraussetzungen

1. **Meta Business Portfolio** anlegen: business.facebook.com →
   „Unternehmensportfolio erstellen“ (Firmenname, E-Mail)
2. **Meta Developer Account**: developers.facebook.com → mit demselben
   Konto registrieren

### B. App erstellen

1. developers.facebook.com → *My Apps* → *Create App*
2. Use Case: **„Other“** → App-Typ: **„Business“**
3. Name z. B. `sjcode-whatsapp-bot`, Business-Portfolio auswählen
4. Im App-Dashboard: Produkt **WhatsApp** → *Set up*

### C. Test-Setup (kostenlos)

1. Unter *WhatsApp → API Setup* bekommst du automatisch:
   - eine **Test-Telefonnummer** (von Meta gestellt)
   - eine **Phone Number ID** und **WABA ID** → notieren
   - einen **temporären Access Token** (24h gültig – nur zum Ausprobieren)
2. Unter *„To“* bis zu **5 Empfänger-Nummern** hinzufügen (private
   Handynummer) – jede bekommt einen Bestätigungscode per WhatsApp
3. Test: den vorgefertigten cURL-Befehl im Dashboard ausführen →
   „Hello World“-Nachricht aufs Handy (alternativ
   `python scripts/test_whatsapp.py` mit `WHATSAPP_TEST_RECIPIENT`)

### D. Permanenter Token (wichtig, sonst bricht alles nach 24h)

1. business.facebook.com → *Einstellungen* → *Benutzer* →
   **Systembenutzer** → neu anlegen (Rolle: Admin)
2. Systembenutzer → *Assets zuweisen* → App auswählen → volle Kontrolle
3. *Token generieren* → App wählen → Berechtigungen:
   `whatsapp_business_messaging` + `whatsapp_business_management` →
   Ablauf: **„Nie“**
4. Token als `WHATSAPP_ACCESS_TOKEN` in `.env` ablegen (niemals committen!)

### E. Webhook verbinden

1. Backend deployen (Railway) oder lokal starten + `ngrok http 5000`
2. App-Dashboard → *WhatsApp → Configuration* → *Webhook*:
   - **Callback URL**: `https://<deine-domain>/api/whatsapp/webhook`
   - **Verify Token**: Wert von `WHATSAPP_WEBHOOK_VERIFY_TOKEN` aus `.env`
   - *Verify and Save* → Meta schickt GET mit `hub.challenge`, der Endpoint
     gibt ihn zurück
3. **Webhook Fields** abonnieren: mindestens `messages` ✅
4. **App Secret** (App-Dashboard → *Settings → Basic*) als
   `WHATSAPP_APP_SECRET` in `.env` → für Signaturprüfung
5. Echo-Test: `WHATSAPP_ECHO_MODE=true` setzen, WhatsApp-Nachricht an die
   Test-Nummer schicken → Bot antwortet mit Echo. Danach wieder auf `false`.

### F. Später: Produktion

1. Eigene Nummer hinzufügen (*WhatsApp → API Setup → Add phone number*) –
   Nummer darf **nicht** in der normalen WhatsApp-App aktiv sein
2. **Business-Verifizierung** durchlaufen (business.facebook.com →
   Sicherheitscenter): Handelsregisterauszug/Gewerbeanmeldung hochladen –
   dauert 1–5 Werktage
3. Display-Name für die Nummer beantragen (z. B. „sjcode Booking Assistent“)
4. Ohne Verifizierung: Limit 250 Konversationen/Tag – für erste
   Pilotkunden ausreichend
5. **DSGVO**: AVV mit Meta abschließen (in den WhatsApp Business Terms
   enthalten, EU-Data-Processing-Addendum), Datenschutzerklärung um
   WhatsApp-Kanal erweitern, Kunden-AVV anpassen (siehe `docs/compliance/`)

### G. Kosten-Merkzettel

| Posten | Kosten |
| --- | --- |
| Cloud API Grundgebühr | 0 € |
| Service-Konversationen (Kunde schreibt zuerst) | 0 € |
| Utility/Marketing-Templates (du schreibst zuerst) | ~0,05–0,08 €/Stück (DE) |
| Test-Nummer + 5 Empfänger | 0 € |
| GPT-4o-mini + Whisper | Cent-Beträge |
| ngrok (Entwicklung) | 0 € |

---

## Teil 3: Schnellstart-Checkliste

- [ ] Meta Business Portfolio + Developer App angelegt
- [ ] Test-Nummer aktiv, eigene Handynummer als Empfänger verifiziert
- [ ] „Hello World“ per cURL bzw. `scripts/test_whatsapp.py` erhalten
- [ ] Systembenutzer + permanenter Token erstellt
- [ ] Schritt 1 (Webhook + Echo-Bot) deployed
- [ ] ngrok-Tunnel + Webhook verifiziert
- [ ] Echo-Bot antwortet auf WhatsApp-Nachricht (`WHATSAPP_ECHO_MODE=true`)
- [ ] Ab dann: Schritte 2–8 aus der Umsetzungsreihenfolge
