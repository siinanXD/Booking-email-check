# DPA-Checkliste: Auftragsverarbeitungsverträge mit den eigenen Anbietern

Jeden Punkt einmal erledigen, Datum eintragen, PDF/Bestätigung ablegen. Links können sich ändern — im Zweifel im Anbieter-Account nach „DPA" oder „Data Processing" suchen.

| ✔ | Anbieter | Wo abschließen | Datum |
|---|---|---|---|
| ☐ | **OpenAI** | https://privacy.openai.com → „Data Processing Addendum" ausfüllen (E-Mail der API-Org angeben); Bestätigung kommt per Mail | |
| ☐ | **MongoDB Atlas** | Atlas-Konsole → Organization → Settings → Legal/„Data Processing Agreement"; DPA ist Teil der Cloud Terms, ggf. Gegenzeichnung anfordern | |
| ☐ | **Railway** | https://railway.com/legal — DPA ist in den Terms enthalten; Kopie herunterladen und ablegen. Region: EU West ✔ (bereits geprüft) | |
| ☐ | **Sentry** | https://sentry.io/legal/dpa/ — im Account akzeptieren bzw. Self-Serve-DPA herunterladen. Zusätzlich prüfen: EU-Data-Residency-Option | |
| ☐ | **Langfuse** | https://langfuse.com/security → DPA anfordern/abschließen; prüfen, ob das Projekt in der EU-Region liegt | |
| ☐ | **Meta (WhatsApp Business)** | WhatsApp Business Terms + „Meta Data Processing Terms" gelten mit Nutzung; Kopie ablegen: https://www.whatsapp.com/legal/business-terms | |
| ☐ | **Microsoft** | Sonderfall: Die Postfächer gehören den Mandanten — deren M365-Vertrag mit Microsoft deckt das ab. Für deine Azure-App-Registrierung gilt das Microsoft Products and Services DPA (automatisch Vertragsbestandteil); Kopie ablegen | |

## Danach

- Die unterschriebenen/abgelegten DPAs sind Anlage der eigenen **Subunternehmer-Liste im AVV** gegenüber den Mandanten (→ `avv.md`, Anhang III).
- Bei Aufnahme eines neuen Anbieters: DPA abschließen **und** Mandanten über den neuen Subunternehmer informieren (Frist laut AVV, üblich 30 Tage Widerspruchsrecht).
