import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl

from app.core.errors import Unauthorized


@dataclass(frozen=True)
class TelegramUser:
    id: int
    first_name: str
    username: str | None


def verify_init_data(
    init_data: str, bot_token: str, now: datetime, max_age: timedelta = timedelta(hours=1)
) -> TelegramUser:
    """Check the Telegram WebApp initData signature and freshness, return the signed user."""
    invalid = Unauthorized("Invalid Telegram data")
    if not bot_token:  # an empty token makes the HMAC key public, anyone could forge initData
        raise invalid
    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received = fields.pop("hash", None)
    if received is None:
        raise invalid
    # every received field except hash is signed, including `signature`
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    # bytes, so a non-ASCII hash cannot raise TypeError
    if not secrets.compare_digest(expected.encode(), received.encode()):
        raise invalid
    try:
        auth_date = datetime.fromtimestamp(int(fields["auth_date"]), UTC)
        user = json.loads(fields["user"])
        result = TelegramUser(
            id=int(user["id"]), first_name=str(user["first_name"]), username=user.get("username")
        )
    except (KeyError, ValueError, TypeError, AttributeError, OverflowError, OSError) as exc:
        raise invalid from exc
    if now - auth_date > max_age:
        raise invalid
    return result
