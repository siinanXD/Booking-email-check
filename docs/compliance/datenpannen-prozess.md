# Prozess bei Datenpannen (Art. 33/34 DSGVO)

**Betreiber:** Sinan Kahraman · **Stand:** Juli 2026
**Zuständige Aufsichtsbehörde:** Landesbeauftragte für Datenschutz und Informationsfreiheit Nordrhein-Westfalen (LDI NRW), Kavalleriestraße 2–4, 40213 Düsseldorf — Online-Meldung: https://www.ldi.nrw.de (Meldeformular Datenpanne)

## Was ist eine meldepflichtige Datenpanne?

Jede Verletzung des Schutzes personenbezogener Daten: unbefugter Zugriff (z. B. kompromittierte MongoDB oder Railway-Account), Datenabfluss, versehentliche Offenlegung (falscher E-Mail-/WhatsApp-Empfänger), Verlust des Verschlüsselungs-Keys mit Datenverlust, kompromittierte OAuth-Tokens.

## Ablauf — die Uhr läuft ab Kenntnisnahme (72 Stunden)

**1. Sofort eindämmen (Stunde 0–2)**
- Betroffene Zugänge sperren/rotieren: `CREDENTIALS_ENCRYPTION_KEY`, `FLASK_SECRET_KEY`, MongoDB-Passwort, Railway-Token, OpenAI-Key, Meta-Token
- Bei kompromittierten Mandanten-Postfächern: OAuth-Verbindungen trennen (Mandant informieren, Microsoft-Passwort ändern lassen)
- Betroffenen Zeitraum und Umfang aus Logs sichern (Railway-Logs, Sentry, Admin-Audit-Log, MongoDB Atlas Access History)

**2. Bewerten (Stunde 2–24)**
- Welche Datenkategorien? Wie viele Betroffene? Welche Mandanten?
- Risiko für Betroffene: gering / vorhanden / hoch (Kriterium für Schritte 3–5)

**3. Mandanten informieren — immer und unverzüglich**
- Als Auftragsverarbeiter besteht Meldepflicht an die Mandanten ohne unangemessene Verzögerung (Art. 33 Abs. 2) — unabhängig von der Risikobewertung. Die Mandanten entscheiden über ihre eigene Meldung an die Behörde.

**4. Behörde melden — binnen 72 h (für eigene Verantwortlichen-Daten)**
- Bei Risiko für Betroffene: Meldung an LDI NRW mit Art der Verletzung, Kategorien/ungefährer Zahl der Betroffenen, wahrscheinlichen Folgen, ergriffenen Maßnahmen
- Kein Risiko (z. B. verschlüsselte Daten, Key nicht betroffen): keine Meldepflicht, aber dokumentieren

**5. Betroffene benachrichtigen — nur bei hohem Risiko (Art. 34)**
- Klartext-Sprache: Was ist passiert, welche Daten, was wurde getan, was sollen Betroffene tun

**6. Dokumentieren — immer, auch ohne Meldepflicht**
- Vorfall, Zeitpunkte, Bewertung, Entscheidung (gemeldet ja/nein und warum), Maßnahmen → Ablage in diesem Ordner als `vorfall-JJJJ-MM-TT.md`

## Vorbeugend bereits umgesetzt

Verschlüsselte Credentials at rest, PII-Maskierung im Monitoring, Audit-Log, Mandantentrennung, Sentry-Alerts. **Empfehlung:** Zugangsdaten-Rotation einmal testen, damit sie im Ernstfall in Minuten statt Stunden klappt.
