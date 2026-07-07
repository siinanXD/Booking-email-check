import { LegalLayout, LegalSection } from "./LegalLayout";

export function DatenschutzPage() {
  return (
    <LegalLayout title="Datenschutzerklärung" stand="Juli 2026">
      <LegalSection title="1. Verantwortlicher">
        <p>
          Verantwortlicher im Sinne der Datenschutz-Grundverordnung (DSGVO)
          ist: Sinan Kahraman, Mühlenstraße 44, 53879 Euskirchen,
          Deutschland. E-Mail:{" "}
          <a href="mailto:sinanKahraman@hotmail.de" className="text-brandink underline">
            sinanKahraman@hotmail.de
          </a>
          .
        </p>
      </LegalSection>

      <LegalSection title="2. Was dieser Dienst tut">
        <p>
          Mail Assistant AI ist eine Software für Gastgeber und Hotels
          (&bdquo;Mandanten&ldquo;). Der Dienst liest die vom Mandanten
          verbundenen Buchungs-Postfächer, ordnet eingehende E-Mails
          automatisch ein (z.&nbsp;B. Buchung, Stornierung, Gastanfrage),
          extrahiert Buchungsdaten und erstellt KI-gestützte
          Antwortentwürfe. Entwürfe werden erst nach Freigabe versendet.
          Für die Inhalte der Gäste-E-Mails handeln wir als
          Auftragsverarbeiter des jeweiligen Mandanten (Art. 28 DSGVO);
          Grundlage ist der mit dem Mandanten geschlossene Vertrag zur
          Auftragsverarbeitung.
        </p>
      </LegalSection>

      <LegalSection title="3. Registrierung und Nutzerkonto">
        <p>
          Bei der Registrierung verarbeiten wir Name, E-Mail-Adresse,
          Firmenangaben und ein Passwort (gespeichert ausschließlich als
          kryptografischer Hash). Rechtsgrundlage ist Art. 6 Abs. 1
          lit.&nbsp;b DSGVO (Vertragserfüllung). Die Anmeldung erfolgt über
          zeitlich begrenzte Zugriffstoken; sicherheitsrelevante Ereignisse
          werden protokolliert.
        </p>
      </LegalSection>

      <LegalSection title="4. Verarbeitung von E-Mail-Inhalten">
        <p>
          Verbindet ein Mandant sein Postfach (Microsoft Outlook über die
          Microsoft-Graph-Schnittstelle oder IMAP), ruft der Dienst
          eingehende E-Mails ab und verarbeitet deren Inhalte einschließlich
          der darin enthaltenen personenbezogenen Daten von Gästen (z.&nbsp;B.
          Name, Reisedaten, Kontaktdaten). Zugangsdaten der Postfächer
          (OAuth-Token, IMAP-Passwörter) werden verschlüsselt gespeichert.
          Rechtsgrundlage im Verhältnis zum Mandanten ist Art. 6 Abs. 1
          lit.&nbsp;b DSGVO; im Übrigen erfolgt die Verarbeitung im Auftrag
          des Mandanten.
        </p>
      </LegalSection>

      <LegalSection title="5. KI-gestützte Verarbeitung (OpenAI)">
        <p>
          Zur Klassifizierung, Datenextraktion und Entwurfserstellung setzen
          wir Sprachmodelle der OpenAI, L.L.C. (USA) über deren
          API ein. Nach den API-Bedingungen von OpenAI werden übermittelte
          Inhalte nicht zum Training der Modelle verwendet. Die Übermittlung
          in die USA erfolgt auf Grundlage von
          EU-Standardvertragsklauseln bzw. des EU-U.S. Data Privacy
          Framework. Es findet keine automatisierte Entscheidungsfindung im
          Sinne des Art. 22 DSGVO statt: Jeder Antwortentwurf wird vor dem
          Versand durch einen Menschen geprüft oder nach vom Mandanten
          ausdrücklich aktivierten Regeln freigegeben.
        </p>
      </LegalSection>

      <LegalSection title="6. WhatsApp-Benachrichtigungen (Meta)">
        <p>
          Auf Wunsch des Mandanten versendet der Dienst Benachrichtigungen
          (z.&nbsp;B. Reinigungsaufgaben, Buchungshinweise) über die WhatsApp
          Business API der Meta Platforms Ireland Ltd. an vom Mandanten
          hinterlegte Telefonnummern. Dabei werden Telefonnummer und
          Nachrichteninhalt an Meta übermittelt. Der Mandant stellt sicher,
          dass die Empfänger (z.&nbsp;B. Mitarbeitende) hierüber informiert
          sind. Rechtsgrundlage: Art. 6 Abs. 1 lit.&nbsp;b und f DSGVO.
        </p>
      </LegalSection>

      <LegalSection title="7. Hosting und Speicherung">
        <p>
          Die Anwendung wird bei Railway Corp. (USA) betrieben; Daten werden
          in einer MongoDB-Atlas-Datenbank der MongoDB, Inc. gespeichert.
          Mit den Anbietern bestehen Auftragsverarbeitungsverträge; für
          Übermittlungen in Drittländer werden EU-Standardvertragsklauseln
          eingesetzt. Alle Verbindungen sind transportverschlüsselt (TLS);
          Postfach-Zugangsdaten werden zusätzlich verschlüsselt gespeichert.
        </p>
      </LegalSection>

      <LegalSection title="8. Fehler- und Qualitätsüberwachung">
        <p>
          Zur Fehlerdiagnose nutzen wir Sentry (Functional Software, Inc.)
          und zur Qualitätsüberwachung der KI-Verarbeitung Langfuse.
          Personenbezogene Inhalte (E-Mail-Adressen, Telefonnummern) werden
          vor der Übermittlung an diese Dienste maskiert. Rechtsgrundlage:
          Art. 6 Abs. 1 lit.&nbsp;f DSGVO (berechtigtes Interesse an einem
          stabilen, sicheren Betrieb).
        </p>
      </LegalSection>

      <LegalSection title="9. Cookies und Tracking">
        <p>
          Diese Anwendung verwendet keine Tracking- oder Marketing-Cookies
          und keine Analysedienste. Im Browser wird lediglich technisch
          Notwendiges gespeichert (Anmeldestatus, Darstellungs-Einstellung).
          Ein Cookie-Banner ist daher nicht erforderlich.
        </p>
      </LegalSection>

      <LegalSection title="10. Speicherdauer">
        <p>
          Personenbezogene Daten werden gelöscht, sobald sie für die
          genannten Zwecke nicht mehr erforderlich sind, spätestens mit
          Beendigung des Mandanten-Vertrags, soweit keine gesetzlichen
          Aufbewahrungspflichten entgegenstehen. Mandanten können die
          Löschung von Gastdaten über die Anwendung anstoßen.
        </p>
      </LegalSection>

      <LegalSection title="11. Ihre Rechte">
        <p>
          Sie haben nach Maßgabe der DSGVO das Recht auf Auskunft (Art. 15),
          Berichtigung (Art. 16), Löschung (Art. 17), Einschränkung der
          Verarbeitung (Art. 18), Datenübertragbarkeit (Art. 20) sowie
          Widerspruch gegen Verarbeitungen auf Grundlage berechtigter
          Interessen (Art. 21). Wenden Sie sich dazu an die oben genannte
          Kontaktadresse. Betrifft Ihre Anfrage Gastdaten eines Mandanten,
          leiten wir sie an den verantwortlichen Mandanten weiter. Zudem
          besteht ein Beschwerderecht bei einer
          Datenschutz-Aufsichtsbehörde (Art. 77 DSGVO).
        </p>
      </LegalSection>

      <LegalSection title="12. Änderungen">
        <p>
          Wir passen diese Datenschutzerklärung an, wenn sich der Dienst
          oder die Rechtslage ändert. Es gilt die jeweils hier
          veröffentlichte Fassung.
        </p>
      </LegalSection>
    </LegalLayout>
  );
}
