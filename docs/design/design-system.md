# Design-System — Booking-email-check (Frontend)

## Woher die Werte kommen

Die Wahrheit steht im Code, nicht in Figma und nicht in dieser Datei:

- CSS-Custom-Properties: `frontend/src/index.css`
- Tailwind: `frontend/tailwind.config.ts`

Stand 2026-08-03: 63 Custom-Properties in `frontend/src/index.css`.

`design-tokens.json` daneben ist eine **Extraktion**, kein Original. Bei
Abweichung gewinnt das CSS. Wer die Datei von Hand pflegt, erzeugt genau die
zweite Wahrheit, die dieses Verzeichnis vermeiden soll.

## Regeln

- **Keine hartkodierten Farbwerte in Bauteilen.** Ein `#3b82f6` neben einem
  vorhandenen Token ist ein Befund, kein Geschmacksthema.
- Abstaende, Radien und Schriftgroessen kommen aus der Skala, nicht aus dem
  Gefuehl.
- Ein neuer Token wird angelegt, wenn ein Wert zum zweiten Mal gebraucht wird
  — nicht beim ersten Mal und nicht beim fuenften.

## Besonderheit

Das Frontend ist der Admin-Bereich, nicht die Aussendarstellung. Es zeigt echte Buchungsdaten.

**Screenshots duerfen keine echten Daten enthalten.** Unter `docs/images/screenshots/` liegen bereits sieben Aufnahmen — wer neue erzeugt, tut das gegen Testdaten, nicht gegen die Produktionsinstanz.

## Barrierefreiheit

Kontrast mindestens 4.5:1 fuer Fliesstext, 3:1 fuer grosse Schrift und
Bedienelemente. Das ist keine Empfehlung, sondern die Schwelle, ab der Text
fuer einen Teil der Nutzer lesbar wird.

Fokus muss sichtbar sein. Wer `outline: none` setzt, ersetzt es durch etwas
Gleichwertiges — oder laesst es.
