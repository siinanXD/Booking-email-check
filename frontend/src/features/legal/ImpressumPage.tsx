import { LegalLayout, LegalSection } from "./LegalLayout";

export function ImpressumPage() {
  return (
    <LegalLayout title="Impressum">
      <LegalSection title="Angaben gemäß § 5 DDG">
        <p>
          Sinan Kahraman
          <br />
          Mühlenstraße 44
          <br />
          53879 Euskirchen
          <br />
          Deutschland
        </p>
      </LegalSection>

      <LegalSection title="Kontakt">
        <p>
          E-Mail:{" "}
          <a href="mailto:sinanKahraman@hotmail.de" className="text-brandink underline">
            sinanKahraman@hotmail.de
          </a>
        </p>
      </LegalSection>

      <LegalSection title="Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV">
        <p>
          Sinan Kahraman
          <br />
          Mühlenstraße 44, 53879 Euskirchen
        </p>
      </LegalSection>

      <LegalSection title="Streitbeilegung">
        <p>
          Die Europäische Kommission stellt eine Plattform zur
          Online-Streitbeilegung (OS) bereit:{" "}
          <a
            href="https://ec.europa.eu/consumers/odr/"
            target="_blank"
            rel="noreferrer"
            className="text-brandink underline"
          >
            https://ec.europa.eu/consumers/odr/
          </a>
          . Wir sind nicht bereit oder verpflichtet, an
          Streitbeilegungsverfahren vor einer
          Verbraucherschlichtungsstelle teilzunehmen.
        </p>
      </LegalSection>
    </LegalLayout>
  );
}
