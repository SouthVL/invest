from __future__ import annotations

import re
from datetime import date, datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser

import httpx

from app.domain.macro_indicators import AnnualInflationValue, KeyRateValue, RuoniaValue

KEY_RATE_URL = "https://www.cbr.ru/hd_base/keyrate/"
RUONIA_URL = "https://www.cbr.ru/hd_base/ruonia/dynamics/"
INFLATION_URL = "https://www.cbr.ru/hd_base/infl/"


class CbrIndicatorsError(Exception):
    pass


class CbrTransportError(CbrIndicatorsError):
    pass


class CbrParseError(CbrIndicatorsError):
    pass


class CbrDataNotFoundError(CbrIndicatorsError):
    pass


class CbrCurrentIndicatorsProvider:
    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def get_key_rate(self) -> KeyRateValue:
        fetched_at = datetime.now(timezone.utc)
        text = fetch_cbr_text(KEY_RATE_URL, timeout_seconds=self.timeout_seconds)
        return parse_key_rate(text, fetched_at=fetched_at)

    def get_latest_ruonia(self) -> RuoniaValue:
        fetched_at = datetime.now(timezone.utc)
        text = fetch_cbr_text(RUONIA_URL, timeout_seconds=self.timeout_seconds)
        return parse_ruonia(text, fetched_at=fetched_at)

    def get_latest_annual_inflation(self) -> AnnualInflationValue:
        fetched_at = datetime.now(timezone.utc)
        text = fetch_cbr_text(INFLATION_URL, timeout_seconds=self.timeout_seconds)
        return parse_annual_inflation(text, fetched_at=fetched_at)


def fetch_cbr_text(url: str, *, timeout_seconds: float) -> str:
    try:
        response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise CbrTransportError("Could not load Bank of Russia data.") from exc
    return html_to_text(response.text)


def parse_key_rate(text: str, *, fetched_at: datetime) -> KeyRateValue:
    match = re.search(r"(\d{2}\.\d{2}\.\d{4})\s+(\d{1,2},\d{1,2})", parseable_text(text))
    if match is None:
        raise CbrDataNotFoundError("Key rate value was not found.")
    return KeyRateValue(
        value_percent=parse_decimal(match.group(2)),
        effective_date=parse_russian_date(match.group(1)),
        effective_from=None,
        source="bank_of_russia",
        source_url=KEY_RATE_URL,
        fetched_at=fetched_at,
        quality_status="actual",
    )


def parse_ruonia(text: str, *, fetched_at: datetime) -> RuoniaValue:
    normalized = parseable_text(text)
    match = re.search(
        r"(\d{2}\.\d{2}\.\d{4})\s+(\d{1,2},\d{1,2})\s+([\d\s]+,\d{1,2})\s+(\d+)\s+(\d+).*?(\d{2}\.\d{2}\.\d{4})",
        normalized,
    )
    if match is None:
        raise CbrDataNotFoundError("RUONIA value was not found.")
    return RuoniaValue(
        value_percent=parse_decimal(match.group(2)),
        rate_date=parse_russian_date(match.group(1)),
        publication_date=parse_russian_date(match.group(6)),
        volume_rub_billion=parse_decimal(match.group(3).replace(" ", "")),
        trades_count=int(match.group(4)),
        participants_count=int(match.group(5)),
        calculation_status=None,
        source="bank_of_russia",
        source_url=RUONIA_URL,
        fetched_at=fetched_at,
        quality_status="actual",
    )


def parse_annual_inflation(text: str, *, fetched_at: datetime) -> AnnualInflationValue:
    normalized = parseable_text(text)
    match = re.search(r"(\d{2})\.(\d{4})\s+\d{1,2},\d{1,2}\s+(\d{1,2},\d{1,2})\s+(\d{1,2},\d{1,2})", normalized)
    if match is None:
        raise CbrDataNotFoundError("Annual inflation value was not found.")
    return AnnualInflationValue(
        value_percent_yoy=parse_decimal(match.group(3)),
        period_year=int(match.group(2)),
        period_month=int(match.group(1)),
        target_percent=parse_decimal(match.group(4)),
        source="rosstat_via_bank_of_russia",
        source_url=INFLATION_URL,
        fetched_at=fetched_at,
        quality_status="actual",
    )


def parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "."))
    except Exception as exc:
        raise CbrParseError("Decimal value could not be parsed.") from exc


def parse_russian_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError as exc:
        raise CbrParseError("Date value could not be parsed.") from exc


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parseable_text(text: str) -> str:
    if "<" in text and ">" in text:
        return normalize_text(html_to_text(text))
    return normalize_text(text)


def html_to_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return parser.text()


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(self.parts)
