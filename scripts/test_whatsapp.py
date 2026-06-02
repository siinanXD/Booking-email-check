"""WhatsApp-Verbindungstest: Meta-Template hello_world an eine Nummer senden."""

from __future__ import annotations

import argparse
import sys

from _bootstrap import setup_path

setup_path()

from config.settings import get_settings  # noqa: E402
from services.whatsapp_client import send_whatsapp_hello_world_test  # noqa: E402


def main() -> int:
    """Sendet hello_world zur Verbindungsprüfung."""
    parser = argparse.ArgumentParser(
        description="WhatsApp-Verbindungstest (Meta hello_world)",
    )
    parser.add_argument(
        "--to",
        dest="recipient",
        help="Empfänger E.164, z. B. +491701234567 (sonst WHATSAPP_TEST_RECIPIENT)",
    )
    args = parser.parse_args()

    try:
        settings = get_settings()
    except Exception as exc:
        print(f"Settings-Fehler: {exc}", file=sys.stderr)
        return 1

    recipient = (args.recipient or settings.whatsapp_test_recipient).strip()
    if not recipient:
        print(
            "Empfänger fehlt: --to +49... oder WHATSAPP_TEST_RECIPIENT in .env setzen.",
            file=sys.stderr,
        )
        return 1

    if not settings.whatsapp_access_token.strip():
        print("WHATSAPP_ACCESS_TOKEN fehlt in .env", file=sys.stderr)
        return 1
    if not settings.whatsapp_phone_number_id.strip():
        print("WHATSAPP_PHONE_NUMBER_ID fehlt in .env", file=sys.stderr)
        return 1

    print(f"Sende hello_world an {recipient} …")
    result = send_whatsapp_hello_world_test(settings, recipient)
    if result.success:
        print(f"OK – Nachricht gesendet (message_id={result.provider_message_id})")
        print("Prüfe WhatsApp auf dem Empfänger-Handy.")
        return 0

    print(f"FEHLER: {result.error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
