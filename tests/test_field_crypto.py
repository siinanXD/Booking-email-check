"""Tests: Feld-Verschlüsselung für Credentials at rest."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from backend.core.utils.field_crypto import ENCRYPTED_PREFIX, FieldCipher
from backend.infrastructure.repositories.mail_connection_repository import (
    MailConnectionRecord,
    MailConnectionRepository,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRecord,
    PlatformSettingsRepository,
)


@pytest.fixture
def cipher() -> FieldCipher:
    return FieldCipher(Fernet.generate_key().decode())


class TestFieldCipher:
    def test_roundtrip(self, cipher: FieldCipher) -> None:
        assert cipher.decrypt(cipher.encrypt("geheim")) == "geheim"

    def test_encrypted_value_is_marked_and_not_plaintext(
        self, cipher: FieldCipher
    ) -> None:
        encrypted = cipher.encrypt("geheim")
        assert encrypted.startswith(ENCRYPTED_PREFIX)
        assert "geheim" not in encrypted

    def test_empty_value_passthrough(self, cipher: FieldCipher) -> None:
        assert cipher.encrypt("") == ""
        assert cipher.decrypt("") == ""

    def test_double_encrypt_is_idempotent(self, cipher: FieldCipher) -> None:
        once = cipher.encrypt("geheim")
        assert cipher.encrypt(once) == once

    def test_legacy_plaintext_passthrough_on_decrypt(self, cipher: FieldCipher) -> None:
        assert cipher.decrypt("altes-klartext-passwort") == "altes-klartext-passwort"

    def test_without_key_is_passthrough(self) -> None:
        plain = FieldCipher()
        assert not plain.enabled
        assert plain.encrypt("geheim") == "geheim"

    def test_encrypted_value_without_key_raises(self, cipher: FieldCipher) -> None:
        encrypted = cipher.encrypt("geheim")
        with pytest.raises(ValueError, match="CREDENTIALS_ENCRYPTION_KEY"):
            FieldCipher().decrypt(encrypted)

    def test_wrong_key_raises(self, cipher: FieldCipher) -> None:
        encrypted = cipher.encrypt("geheim")
        other = FieldCipher(Fernet.generate_key().decode())
        with pytest.raises(ValueError, match="passt nicht"):
            other.decrypt(encrypted)

    def test_invalid_key_raises(self) -> None:
        with pytest.raises(ValueError, match="Fernet-Key"):
            FieldCipher("kein-gueltiger-key")


class TestMailConnectionEncryption:
    def test_credentials_encrypted_at_rest(
        self, mock_db: object, cipher: FieldCipher
    ) -> None:
        repo = MailConnectionRepository(mock_db, cipher)  # type: ignore[arg-type]
        repo.save(
            MailConnectionRecord(
                account_id="acc-1",
                imap_password="super-geheim",
                outlook_token_cache='{"token": "graph-secret"}',
            )
        )
        raw = mock_db[MailConnectionRepository.COLLECTION].find_one(  # type: ignore[index]
            {"_id": "acc-1"}
        )
        assert raw["imap_password"].startswith(ENCRYPTED_PREFIX)
        assert raw["outlook_token_cache"].startswith(ENCRYPTED_PREFIX)
        assert "super-geheim" not in raw["imap_password"]

        loaded = repo.get("acc-1")
        assert loaded is not None
        assert loaded.imap_password == "super-geheim"
        assert loaded.outlook_token_cache == '{"token": "graph-secret"}'

    def test_legacy_plaintext_record_still_readable(
        self, mock_db: object, cipher: FieldCipher
    ) -> None:
        plain_repo = MailConnectionRepository(mock_db)  # type: ignore[arg-type]
        plain_repo.save(
            MailConnectionRecord(account_id="acc-legacy", imap_password="klartext")
        )
        repo = MailConnectionRepository(mock_db, cipher)  # type: ignore[arg-type]
        loaded = repo.get("acc-legacy")
        assert loaded is not None
        assert loaded.imap_password == "klartext"

    def test_list_pollable_decrypts(self, mock_db: object, cipher: FieldCipher) -> None:
        repo = MailConnectionRepository(mock_db, cipher)  # type: ignore[arg-type]
        repo.save(
            MailConnectionRecord(
                account_id="acc-2",
                provider="imap",
                imap_host="imap.example.com",
                imap_username="user",
                imap_password="pw",
                onboarding_completed=True,
            )
        )
        pollable = repo.list_pollable()
        assert len(pollable) == 1
        assert pollable[0].imap_password == "pw"


class TestPlatformSettingsEncryption:
    def test_whatsapp_token_encrypted_at_rest(
        self, mock_db: object, cipher: FieldCipher
    ) -> None:
        repo = PlatformSettingsRepository(mock_db, cipher)  # type: ignore[arg-type]
        repo.save(
            PlatformSettingsRecord(id="acc-1", whatsapp_access_token="EAAB-secret")
        )
        raw = mock_db[PlatformSettingsRepository.COLLECTION].find_one(  # type: ignore[index]
            {"_id": "acc-1"}
        )
        assert raw["whatsapp_access_token"].startswith(ENCRYPTED_PREFIX)

        loaded = repo.get("acc-1")
        assert loaded is not None
        assert loaded.whatsapp_access_token == "EAAB-secret"
