"""Führt `property_whatsapp_recipients` in `cleaning_partners` zusammen.

Hintergrund: Mitarbeiter lagen doppelt vor — der WhatsApp-Bot schrieb nach
`cleaning_partners`, die Weboberfläche las `property_whatsapp_recipients`. Seit
der Zusammenführung ist `cleaning_partners` die einzige Quelle; dieses Skript
holt die Altbestände dorthin.

Reihenfolge (bewusst so):
  1. Partner mit gleicher Telefonnummer zusammenlegen (Union der Objekte).
  2. Empfänger-Altbestand über die Telefonnummer an den Partner hängen.
  3. Objektnamen gegen den echten Katalog prüfen und Karteileichen melden.

Ohne Schritt 2 verlieren Objekte ihre Mitarbeiter, deren Partner-Datensatz unter
einem abweichenden Namen eingetragen ist (real: "RebenGlück" vs. die Unterkunft
"Ferienwohnung RebenGlück").

Standard ist der Trockenlauf. Erst `--apply` schreibt.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from typing import Any

from backend.core.config.settings import Settings
from backend.features.cleaning.models import CleaningPartner
from backend.infrastructure.repositories.mongo import get_database

_LEGACY = "property_whatsapp_recipients"


def _norm(name: str) -> str:
    return name.strip().lower()


def _plan(db: Any) -> tuple[list[str], dict[str, list[CleaningPartner]], list[str]]:
    """Baut den Migrationsplan: Meldungen + Partner je Account + Dubletten."""
    lines: list[str] = []
    by_account: dict[str, list[CleaningPartner]] = {}
    retired: list[str] = []

    partners = [CleaningPartner.from_mongo(d) for d in db["cleaning_partners"].find()]
    accounts = {p.account_id for p in partners if p.account_id}
    accounts |= {
        str(d["account_id"])
        for d in db[_LEGACY].find({}, {"account_id": 1})
        if d.get("account_id")
    }

    for account_id in sorted(accounts):
        merged = _merge_by_phone(
            [p for p in partners if p.account_id == account_id], lines, retired
        )
        _apply_legacy(db, account_id, merged, lines)
        _report_stale(db, account_id, merged, lines)
        by_account[account_id] = list(merged.values())
    return lines, by_account, retired


def _merge_by_phone(
    partners: list[CleaningPartner],
    lines: list[str],
    retired: list[str],
) -> dict[str, CleaningPartner]:
    """Gleiche Nummer = eine Person. Objekte werden vereinigt.

    Die abgelösten Dubletten landen in ``retired`` und werden deaktiviert —
    sonst bleiben zwei aktive Datensätze derselben Person stehen.
    """
    groups: dict[str, list[CleaningPartner]] = defaultdict(list)
    for p in partners:
        phone = (p.phone or "").strip()
        groups[phone or f"__ohne_nummer__{p.partner_id}"].append(p)

    merged: dict[str, CleaningPartner] = {}
    for phone, group in groups.items():
        keep = max(group, key=lambda p: (len(p.property_names), p.updated_at))
        for other in group:
            if other.partner_id == keep.partner_id:
                continue
            for name in other.property_names:
                if _norm(name) not in {_norm(n) for n in keep.property_names}:
                    keep.property_names.append(name.strip())
            retired.append(other.partner_id)
            lines.append(
                f"  ZUSAMMENLEGEN  {other.name!r} ({other.partner_id[:8]}) "
                f"-> {keep.name!r} ({keep.partner_id[:8]}); "
                f"Objekte jetzt: {keep.property_names}"
            )
        merged[phone] = keep
    return merged


def _apply_legacy(
    db: Any,
    account_id: str,
    merged: dict[str, CleaningPartner],
    lines: list[str],
) -> None:
    """Altbestand über die Telefonnummer an den passenden Partner hängen."""
    for doc in db[_LEGACY].find({"account_id": account_id}):
        prop = str(doc.get("property_name") or "").strip()
        if not prop:
            continue
        employees = doc.get("employees") or [
            {"phone_e164": p} for p in (doc.get("phones") or [])
        ]
        for emp in employees:
            phone = str(emp.get("phone_e164") or "").strip()
            if not phone:
                continue
            partner = merged.get(phone)
            if partner is None:
                partner = CleaningPartner(
                    partner_id=f"cp_legacy_{abs(hash((account_id, phone))):016x}",
                    account_id=account_id,
                    name=phone,
                    phone=phone,
                    locale="de",
                    property_names=[],
                )
                merged[phone] = partner
                lines.append(
                    f"  NEU  Partner {phone} (aus Altbestand, Name nachpflegen)"
                )
            if _norm(prop) not in {_norm(n) for n in partner.property_names}:
                partner.property_names.append(prop)
                lines.append(f"  ZUORDNEN  {partner.name!r} -> {prop!r}")


def _report_stale(
    db: Any,
    account_id: str,
    merged: dict[str, CleaningPartner],
    lines: list[str],
) -> None:
    """Objektnamen ohne passende Unterkunft melden (wirkungslose Zuordnungen)."""
    catalog = {
        _norm(str(d.get("name") or ""))
        for d in db["properties"].find({"account_id": account_id}, {"name": 1})
    }
    for partner in merged.values():
        for name in partner.property_names:
            if _norm(name) not in catalog:
                lines.append(
                    f"  KARTEILEICHE  {partner.name!r} -> {name!r} "
                    f"(keine Unterkunft dieses Namens; Zuordnung wirkungslos)"
                )
        if not partner.property_names:
            lines.append(
                f"  OHNE OBJEKT  {partner.name!r} ({partner.partner_id[:8]}) "
                f"— bekommt nie eine Benachrichtigung"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Änderungen schreiben")
    parser.add_argument(
        "--drop-empty", action="store_true", help="Partner ohne Objekt deaktivieren"
    )
    args = parser.parse_args()

    settings = Settings()
    db = get_database(settings)
    lines, by_account, retired = _plan(db)

    print("\n".join(lines) if lines else "Nichts zu tun.")
    if not args.apply:
        print("\nTROCKENLAUF — nichts geschrieben. Mit --apply ausführen.")
        return 0

    written = 0
    for account_id, partners in by_account.items():
        for partner in partners:
            if args.drop_empty and not partner.property_names:
                db["cleaning_partners"].update_one(
                    {"_id": partner.partner_id}, {"$set": {"active": False}}
                )
                continue
            doc = partner.to_mongo()
            doc["account_id"] = account_id
            db["cleaning_partners"].update_one(
                {"_id": partner.partner_id}, {"$set": doc}, upsert=True
            )
            written += 1
    for partner_id in retired:
        db["cleaning_partners"].update_one(
            {"_id": partner_id},
            {
                "$set": {
                    "active": False,
                    "property_names": [],
                    "property_names_lower": [],
                }
            },
        )
    print(f"\nGeschrieben: {written} Partner, {len(retired)} Dubletten deaktiviert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
