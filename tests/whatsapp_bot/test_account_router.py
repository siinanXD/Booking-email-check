"""Tests: AccountRouter – geteilte Plattform-Nummer vs. dedizierte Nummer."""

from __future__ import annotations

from typing import Any

from backend.features.whatsapp_bot.account_router import AccountRouter


def _payload(
    *,
    pnid: str,
    sender: str | None = "491705550001",
    status_only: bool = False,
) -> dict[str, Any]:
    value: dict[str, Any] = {"metadata": {"phone_number_id": pnid}}
    if status_only:
        value["statuses"] = [{"status": "read", "recipient_id": sender}]
    elif sender is not None:
        value["messages"] = [
            {"id": "wamid.x", "from": sender, "type": "text", "text": {"body": "Hallo"}}
        ]
    return {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": value}]}],
    }


class _Platform:
    def __init__(self, mapping: dict[str, str]) -> None:
        self._m = mapping

    def find_account_by_phone_number_id(self, pnid: str) -> str | None:
        return self._m.get(pnid)


class _Users:
    def __init__(self, m: dict[str, list[str]]) -> None:
        self._m = m

    def find_account_ids_by_whatsapp(self, digits: str) -> list[str]:
        return list(self._m.get(digits, []))


class _Partners:
    def __init__(self, m: dict[str, list[str]]) -> None:
        self._m = m

    def find_account_ids_by_phone(self, digits: str) -> list[str]:
        return list(self._m.get(digits, []))


def _router(
    *,
    platform_pnid: str,
    pnmap: dict[str, str] | None = None,
    users: dict[str, list[str]] | None = None,
    partners: dict[str, list[str]] | None = None,
) -> AccountRouter:
    return AccountRouter(
        platform_settings_repo=_Platform(pnmap or {}),
        user_repo=_Users(users or {}),
        cleaning_partner_repo=_Partners(partners or {}),
        platform_phone_number_id=platform_pnid,
    )


def test_dedicated_number_resolves_by_pnid() -> None:
    router = _router(platform_pnid="", pnmap={"DED1": "acc-ded"})
    res = router.route(_payload(pnid="DED1"))
    assert (res.account_id, res.status) == ("acc-ded", "resolved")


def test_dedicated_number_unknown_pnid_no_account() -> None:
    router = _router(platform_pnid="")
    res = router.route(_payload(pnid="NOPE"))
    assert res.account_id is None
    assert res.status == "no_account"


def test_shared_number_routes_by_sender_user() -> None:
    router = _router(platform_pnid="PLAT", users={"491705550001": ["acc-a"]})
    res = router.route(_payload(pnid="PLAT", sender="491705550001"))
    assert (res.account_id, res.status) == ("acc-a", "resolved")


def test_shared_number_routes_by_sender_partner_ignores_formatting() -> None:
    router = _router(platform_pnid="PLAT", partners={"491705550001": ["acc-b"]})
    res = router.route(_payload(pnid="PLAT", sender="+49 170 555-0001"))
    assert (res.account_id, res.status) == ("acc-b", "resolved")


def test_shared_number_unknown_sender() -> None:
    router = _router(platform_pnid="PLAT")
    res = router.route(_payload(pnid="PLAT", sender="490000000000"))
    assert res.account_id is None
    assert res.status == "unknown_sender"


def test_shared_number_ambiguous_sender_two_accounts() -> None:
    router = _router(
        platform_pnid="PLAT",
        users={"491705550001": ["acc-a"]},
        partners={"491705550001": ["acc-b"]},
    )
    res = router.route(_payload(pnid="PLAT", sender="491705550001"))
    assert res.account_id is None
    assert res.status == "ambiguous"


def test_shared_number_status_webhook_ignored() -> None:
    router = _router(platform_pnid="PLAT", users={"491705550001": ["acc-a"]})
    res = router.route(_payload(pnid="PLAT", status_only=True))
    assert res.status == "ignored"
