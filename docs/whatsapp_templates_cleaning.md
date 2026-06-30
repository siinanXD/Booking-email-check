# WhatsApp-Templates – Putzplan (zur Meta-Verifizierung)

Diese Vorlagen müssen im **Meta WhatsApp Business Manager → Message Templates**
angelegt und genehmigt werden, bevor der Putzplan WhatsApp versendet. Ohne
genehmigtes Template wird der Versand übersprungen (Status `skipped`,
Dry-Run-Schutz); der Putzplan selbst funktioniert unabhängig davon.

## Wichtig (damit Code ↔ Template zusammenpassen)

- **Pro Sprache ein eigenes Template** mit Sprach-Suffix im Namen:
  `_de`, `_en`, `_pl`, `_it`, `_es`. Die Sprache (Language) im Meta-Template
  muss zum Suffix passen.
- **Kategorie: Utility** (kein Marketing).
- **Nur Body**, kein Header, keine Buttons (Footer optional).
- **Genau 5 Variablen** `{{1}}`–`{{5}}` in dieser Reihenfolge:

  | Variable | Inhalt | Beispiel |
  |----------|--------|----------|
  | `{{1}}` | Unterkunft (+ Zimmer/Kanal) | `Loft A (Booking.com)` |
  | `{{2}}` | Check-in | `05.07.2026` |
  | `{{3}}` | Check-out | `10.07.2026` |
  | `{{4}}` | Gast | `Max Muster` |
  | `{{5}}` | Buchungsnummer | `BN-100` |

- Die Template-Namen sind pro Tenant in den Einstellungen überschreibbar
  (Defaults unten). Werden andere Namen verwendet, müssen sie ebenfalls bei
  Meta existieren.

---

## 1) Putz-Erinnerung (Vortag)

Default-Name: `booking_cleaning_reminder_de` (Basis) bzw. `_en/_pl/_it/_es`.

**DE**
```
Erinnerung: morgen steht eine Reinigung an.

Unterkunft: {{1}}
Check-in: {{2}}
Check-out: {{3}}
Gast: {{4}}
Buchungsnummer: {{5}}

Bitte die Reinigung rechtzeitig einplanen. Danke!
```

**EN**
```
Reminder: a cleaning is due tomorrow.

Property: {{1}}
Check-in: {{2}}
Check-out: {{3}}
Guest: {{4}}
Booking reference: {{5}}

Please schedule the cleaning in time. Thank you!
```

**PL**
```
Przypomnienie: jutro zaplanowane sprzatanie.

Obiekt: {{1}}
Zameldowanie: {{2}}
Wymeldowanie: {{3}}
Gosc: {{4}}
Numer rezerwacji: {{5}}

Prosimy zaplanowac sprzatanie na czas. Dziekujemy!
```

**IT**
```
Promemoria: domani e prevista una pulizia.

Struttura: {{1}}
Check-in: {{2}}
Check-out: {{3}}
Ospite: {{4}}
Riferimento prenotazione: {{5}}

Pianifica la pulizia per tempo. Grazie!
```

**ES**
```
Recordatorio: manana hay una limpieza prevista.

Alojamiento: {{1}}
Entrada: {{2}}
Salida: {{3}}
Huesped: {{4}}
Referencia de reserva: {{5}}

Programa la limpieza a tiempo. Gracias!
```

---

## 2) Putz-Storno (Auftrag entfällt)

Default-Name: `booking_cleaning_cancelled_de` (Basis) bzw. `_en/_pl/_it/_es`.

**DE**
```
Stornierung – dieser Reinigungsauftrag entfällt.

Unterkunft: {{1}}
Check-in: {{2}}
Check-out: {{3}}
Gast: {{4}}
Buchungsnummer: {{5}}

Bitte für diese Wohnung keine Reinigung mehr einplanen. Danke!
```

**EN**
```
Cancellation – this cleaning assignment is no longer needed.

Property: {{1}}
Check-in: {{2}}
Check-out: {{3}}
Guest: {{4}}
Booking reference: {{5}}

Please do not schedule a cleaning for this unit. Thank you!
```

**PL**
```
Anulowanie – to zlecenie sprzatania jest nieaktualne.

Obiekt: {{1}}
Zameldowanie: {{2}}
Wymeldowanie: {{3}}
Gosc: {{4}}
Numer rezerwacji: {{5}}

Prosimy nie planowac sprzatania tego lokalu. Dziekujemy!
```

**IT**
```
Cancellazione – questo incarico di pulizia non e piu necessario.

Struttura: {{1}}
Check-in: {{2}}
Check-out: {{3}}
Ospite: {{4}}
Riferimento prenotazione: {{5}}

Non programmare pulizie per questa unita. Grazie!
```

**ES**
```
Cancelacion – esta tarea de limpieza ya no es necesaria.

Alojamiento: {{1}}
Entrada: {{2}}
Salida: {{3}}
Huesped: {{4}}
Referencia de reserva: {{5}}

Por favor, no programe limpieza para esta unidad. Gracias!
```

---

## Beispielwerte für die Meta-Freigabe

Beim Anlegen verlangt Meta Beispiel-Variablen. Verwende z. B.:
`{{1}}=Loft A (Booking.com)`, `{{2}}=05.07.2026`, `{{3}}=10.07.2026`,
`{{4}}=Max Muster`, `{{5}}=BN-100`.

> Hinweis: Der bestehende Putzauftrag bei Neubuchung nutzt das schon vorhandene
> Template `booking_cleaning_task_*` (separat, bereits im System). Neu für die
> Verifizierung sind nur die beiden oben: **Erinnerung** und **Storno**.
