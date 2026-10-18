from dataclasses import dataclass
from decimal import Decimal

MODELS: tuple[str, ...] = ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5")
EFFORTS = ("low", "medium", "high", "xhigh", "max")


@dataclass(frozen=True)
class Price:
    """USD per 1M tokens."""

    input: Decimal
    output: Decimal
    cache_read: Decimal


# shortcut: цены зашиты в код, обновлять при изменении прайса Anthropic
# Haiku 5.5: тариф для промптов до 100K токенов (лимиты на входе держат кейс ниже порога).
PRICES: dict[str, Price] = {
    "claude-opus-5-5": Price(Decimal("4.00"), Decimal("20.00"), Decimal("0.20")),
    "claude-sonnet-5-5": Price(Decimal("2.00"), Decimal("10.00"), Decimal("0.10")),
    "claude-haiku-5-5": Price(Decimal("0.10"), Decimal("0.50"), Decimal("0.01")),
}

CACHE_WRITE_FACTOR = Decimal("1.25")  # of the input price
_MTOK = Decimal(1_000_000)


def cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> Decimal:
    p = PRICES[model]
    return (
        input_tokens * p.input
        + output_tokens * p.output
        + cache_read_tokens * p.cache_read
        + cache_write_tokens * p.input * CACHE_WRITE_FACTOR
    ) / _MTOK
