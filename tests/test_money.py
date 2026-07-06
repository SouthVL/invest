from decimal import Decimal
from types import SimpleNamespace

from invest_bonds.money import money_to_decimal, quotation_to_decimal, units_nano_to_decimal


def test_units_nano_to_decimal_whole() -> None:
    assert units_nano_to_decimal(10, 0) == Decimal("10")


def test_units_nano_to_decimal_fractional() -> None:
    assert units_nano_to_decimal(10, 250_000_000) == Decimal("10.25")


def test_units_nano_to_decimal_zero() -> None:
    assert units_nano_to_decimal(0, 0) == Decimal("0")


def test_units_nano_to_decimal_negative_nano() -> None:
    assert units_nano_to_decimal(0, -500_000_000) == Decimal("-0.5")


def test_money_to_decimal() -> None:
    assert money_to_decimal(SimpleNamespace(units=1, nano=100_000_000)) == Decimal("1.1")


def test_quotation_to_decimal() -> None:
    assert quotation_to_decimal(SimpleNamespace(units=2, nano=1)) == Decimal("2.000000001")
