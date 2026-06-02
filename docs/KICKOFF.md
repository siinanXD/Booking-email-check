# Kickoff-Nachricht für den Cursor-Agenten

Dies ist NICHT der Spec-Text selbst – den liest der Agent aus der Datei.
Kopiere nur die folgende kurze Nachricht in den Agent-Modus (idealerweise Plan
Mode). Sie verweist auf die Dateien, statt sie hineinzukopieren.

---

Lies zuerst `AGENTS.md` und `docs/SPEC.md` vollständig.

Halte dich strikt an die Constraints und an die Lieferreihenfolge am Ende von
SPEC.md. Arbeite nicht alles auf einmal ab.

Starte mit Plan Mode: Erstelle einen überprüfbaren Plan für **MVP-Schritt 1**
(Ingestion + Triage-Gate + Pydantic-Datenmodelle des Booking-Packs + Storage),
inklusive der dafür nötigen Tests. Liste auf, welche bestehenden Templates oder
Skills du aus `awesome-claude-code`, den LangGraph-Templates oder den
Atlas-Beispielen wiederverwenden würdest (Phase 0: Reuse before Build), mit
kurzer Begründung pro Komponente.

Beginne erst mit der Umsetzung, nachdem ich den Plan freigegeben habe. Committe
in kleinen, atomaren Schritten mit Conventional Commits auf einem Feature-Branch.