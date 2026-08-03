# TASKS.md — Booking-email-check

Offene Punkte dieses Projekts. Der Stand ist vom **2026-08-03** und stammt aus
der Migration nach `C:\Dev\Repositories`.

## Offen

- [ ] venv neu aufbauen und `pip install -e .[dev]`, danach Funktionstest
- [ ] 3 geaenderte Dateien im Arbeitsbaum sichten und einordnen
      (mit `git diff --ignore-cr-at-eol` gemessen, nicht 748)
- [ ] `.gitattributes` mit `* text=auto eol=lf` ergaenzen, damit die
      CRLF-Verwirrung nicht wiederkehrt
- [ ] Entscheiden, was mit `docs/ROADMAP.md` an Naechstem ansteht

## Erledigt

- [x] 2026-08-03 — nach `C:\Dev\Repositories` migriert
- [x] 2026-08-03 — rsync-Reste in `.git/objects` entfernt, die `bad sha1 file`
      verursachten; `git fsck` danach sauber
- [x] 2026-08-03 — verwaiste `index.lock` entfernt, die jedes `git add`
      blockierte

---

## Wie hier gearbeitet wird

Erledigtes wird abgehakt und mit Datum versehen, nicht geloescht — sonst
verschwindet die Spur, warum etwas so ist, wie es ist.

Aufgaben, die ein Agent uebernehmen soll, gehoeren ins Agent-System:

```bash
python C:\Dev\AI-Workspace\AGENT-SYSTEM\orchestration\run.py new \
  --id TASK-XXX --project Booking-email-check --title "..."
```
