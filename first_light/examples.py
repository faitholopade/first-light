"""Original deterministic synthetic arrays; no competition or research data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Example:
    name: str
    description: str
    values: tuple[int, ...]


def examples():
    broad = tuple(max(0, 180_000 - 14 * (i - 92) ** 2) for i in range(400))
    double = tuple(
        max(0, 130_000 - 12 * (i - 145) ** 2)
        + max(0, 180_000 - 13 * (i - 515) ** 2)
        + (i * 37 % 17)
        for i in range(700)
    )
    flat = (100,) * 401
    hidden = tuple(
        max(0, 160_000 - 16 * (i - 90) ** 2) + (300_000 if i == 999 else 0)
        for i in range(1000)
    )
    return (
        Example("broad_hill", "one broad early peak", broad),
        Example("two_hills", "early decoy and larger late peak", double),
        Example("flat", "all positions tie", flat),
        Example("hidden_spike", "unread distant maximum stress case", hidden),
    )
