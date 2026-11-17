from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode

import pytest
from conftest import sign_fields, sign_init_data

from app.core.errors import Unauthorized
from app.modules.auth.telegram import TelegramUser, verify_init_data

BOT = "123:abc"
NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
USER = {"id": 42, "first_name": "Ann", "username": "ann"}


def signed(user: dict[str, Any] = USER, age: timedelta = timedelta(minutes=1), **extra: str) -> str:
    return sign_init_data(BOT, user, int((NOW - age).timestamp()), **extra)


def test_valid_init_data_returns_user() -> None:
    assert verify_init_data(signed(), BOT, NOW) == TelegramUser(
        id=42, first_name="Ann", username="ann"
    )


def test_user_with_signature_and_cyrillic_name() -> None:
    user = {"id": 7, "first_name": "Иван"}
    result = verify_init_data(signed(user, signature="abc"), BOT, NOW)
    assert result == TelegramUser(id=7, first_name="Иван", username=None)


def test_tampered_hash_rejected() -> None:
    data = signed()
    flipped = "0" if data[-1] != "0" else "1"
    with pytest.raises(Unauthorized, match="Invalid Telegram data"):
        verify_init_data(data[:-1] + flipped, BOT, NOW)


def test_tampered_field_rejected() -> None:
    fields = dict(parse_qsl(signed()))
    fields["user"] = '{"id": 1, "first_name": "Eve"}'
    with pytest.raises(Unauthorized):
        verify_init_data(urlencode(fields), BOT, NOW)


def test_missing_hash_rejected() -> None:
    fields = dict(parse_qsl(signed()))
    del fields["hash"]
    with pytest.raises(Unauthorized):
        verify_init_data(urlencode(fields), BOT, NOW)


def test_stale_auth_date_rejected() -> None:
    with pytest.raises(Unauthorized):
        verify_init_data(signed(age=timedelta(hours=1, minutes=1)), BOT, NOW)


def test_fresh_auth_date_accepted() -> None:
    assert verify_init_data(signed(age=timedelta(minutes=59)), BOT, NOW).id == 42


def test_non_ascii_hash_does_not_crash() -> None:
    fields = dict(parse_qsl(signed()))
    fields["hash"] = "é"
    with pytest.raises(Unauthorized):
        verify_init_data(urlencode(fields), BOT, NOW)


def test_malformed_user_json_rejected() -> None:
    fields = dict(parse_qsl(signed()))
    del fields["hash"]
    fields["user"] = "{not json"
    # validly signed, so only the broken JSON is at fault
    with pytest.raises(Unauthorized):
        verify_init_data(sign_fields(BOT, fields), BOT, NOW)


def test_wrong_bot_token_rejected() -> None:
    with pytest.raises(Unauthorized):
        verify_init_data(signed(), "999:other", NOW)


def test_empty_bot_token_rejected() -> None:
    # an empty token makes the HMAC key public: data signed with it must never pass
    with pytest.raises(Unauthorized):
        verify_init_data(sign_init_data("", USER, int(NOW.timestamp())), "", NOW)
