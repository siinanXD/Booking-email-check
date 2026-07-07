import { Link } from "react-router-dom";

const LINK_CLASS =
  "font-medium text-indigo-400 transition-colors hover:text-indigo-300";

/** Datenschutz-Hinweis (Art. 13 DSGVO) und Login-Link unter dem Registrierungsformular. */
export function RegisterFormFooter() {
  return (
    <>
      <p className="text-center text-xs text-slate-500">
        Mit der Registrierung nimmst du unsere{" "}
        <Link to="/datenschutz" className={LINK_CLASS}>
          Datenschutzerklärung
        </Link>{" "}
        zur Kenntnis.
      </p>
      <p className="text-center text-xs text-slate-500">
        Bereits ein Konto?{" "}
        <Link to="/login" className={LINK_CLASS}>
          Anmelden
        </Link>
      </p>
    </>
  );
}
