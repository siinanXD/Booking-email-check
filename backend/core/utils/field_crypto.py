"""Feld-Verschlüsselung für sensible Credentials (Fernet, at rest in MongoDB)."""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Marker vor verschlüsselten Werten — erlaubt Legacy-Klartext beim Lesen
# zu erkennen und beim nächsten Speichern transparent nachzuverschlüsseln.
ENCRYPTED_PREFIX = "enc::"


def build_credentials_cipher(key: str, app_env: str) -> FieldCipher:
    """Erzeugt den Credentials-Cipher; warnt, wenn Produktion ohne Key läuft."""
    cipher = FieldCipher(key)
    if not cipher.enabled and app_env == "production":
        logger.warning(
            "CREDENTIALS_ENCRYPTION_KEY nicht gesetzt — IMAP-Passwörter, "
            "Outlook-Tokens und WhatsApp-Tokens werden im Klartext gespeichert."
        )
    return cipher


class FieldCipher:
    """Ver-/entschlüsselt einzelne String-Felder symmetrisch (Fernet/AES-128-CBC+HMAC).

    Ohne Schlüssel (leerer String) arbeitet der Cipher im Passthrough-Modus:
    Werte werden unverändert gespeichert und gelesen (Abwärtskompatibilität).
    """

    def __init__(self, key: str = "") -> None:
        """Erzeugt den Cipher; ``key`` ist ein Fernet-Key (base64, 44 Zeichen)."""
        stripped = key.strip()
        try:
            self._fernet = Fernet(stripped.encode()) if stripped else None
        except ValueError as exc:
            msg = (
                "CREDENTIALS_ENCRYPTION_KEY ist kein gültiger Fernet-Key. "
                'Generieren mit: python -c "from cryptography.fernet import '
                'Fernet; print(Fernet.generate_key().decode())"'
            )
            raise ValueError(msg) from exc

    @property
    def enabled(self) -> bool:
        """True, wenn ein Schlüssel konfiguriert ist."""
        return self._fernet is not None

    def encrypt(self, value: str) -> str:
        """Verschlüsselt ``value``; leere Werte und Passthrough bleiben unverändert."""
        if not value or self._fernet is None:
            return value
        if value.startswith(ENCRYPTED_PREFIX):
            return value  # bereits verschlüsselt (doppeltes save)
        token: str = self._fernet.encrypt(value.encode()).decode()
        return ENCRYPTED_PREFIX + token

    def decrypt(self, value: str) -> str:
        """Entschlüsselt ``value``; Legacy-Klartext wird unverändert zurückgegeben."""
        if not value or not value.startswith(ENCRYPTED_PREFIX):
            return value
        if self._fernet is None:
            msg = (
                "Verschlüsselter Wert gefunden, aber CREDENTIALS_ENCRYPTION_KEY "
                "ist nicht gesetzt."
            )
            raise ValueError(msg)
        try:
            plaintext: str = self._fernet.decrypt(
                value[len(ENCRYPTED_PREFIX) :].encode()
            ).decode()
        except InvalidToken as exc:
            msg = (
                "Entschlüsselung fehlgeschlagen — CREDENTIALS_ENCRYPTION_KEY "
                "passt nicht zum gespeicherten Wert."
            )
            raise ValueError(msg) from exc
        return plaintext
