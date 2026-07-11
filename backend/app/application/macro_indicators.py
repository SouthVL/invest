from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import Protocol

from app.domain.macro_indicators import AnnualInflationValue, CurrentMacroSnapshot, KeyRateValue, RuoniaValue
from app.storage.macro_indicators import MacroIndicatorsRepository


class CurrentMacroIndicatorsProvider(Protocol):
    def get_key_rate(self) -> KeyRateValue:
        ...

    def get_latest_ruonia(self) -> RuoniaValue:
        ...

    def get_latest_annual_inflation(self) -> AnnualInflationValue:
        ...


class MacroIndicatorsStrictError(Exception):
    pass


class CachedCurrentMacroIndicatorsProvider:
    def __init__(
        self,
        *,
        upstream: CurrentMacroIndicatorsProvider,
        repository: MacroIndicatorsRepository,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.upstream = upstream
        self.repository = repository
        self.now = now or (lambda: datetime.now(timezone.utc))

    def get_key_rate(self) -> KeyRateValue:
        latest = self.repository.latest_key_rate()
        return self._load(
            latest=latest,
            is_due=monthly_fifth_refresh_due(latest.fetched_at if latest else None, self.now().date()),
            fetch=self.upstream.get_key_rate,
            save=self.repository.save_key_rate,
        )

    def get_latest_ruonia(self) -> RuoniaValue:
        latest = self.repository.latest_ruonia()
        return self._load(
            latest=latest,
            is_due=daily_refresh_due(latest.fetched_at if latest else None, self.now().date()),
            fetch=self.upstream.get_latest_ruonia,
            save=self.repository.save_ruonia,
        )

    def get_latest_annual_inflation(self) -> AnnualInflationValue:
        latest = self.repository.latest_annual_inflation()
        return self._load(
            latest=latest,
            is_due=monthly_fifth_refresh_due(latest.fetched_at if latest else None, self.now().date()),
            fetch=self.upstream.get_latest_annual_inflation,
            save=self.repository.save_annual_inflation,
        )

    def _load(self, *, latest, is_due: bool, fetch, save):
        if latest is not None and not is_due:
            return latest.model_copy(update={"quality_status": "cached"})

        try:
            fresh = fetch()
        except Exception:
            if latest is not None:
                return latest.model_copy(update={"quality_status": "stale"})
            raise

        save(fresh)
        return fresh


def daily_refresh_due(latest_fetched_at: datetime | None, current_date: date) -> bool:
    if latest_fetched_at is None:
        return True
    return latest_fetched_at.astimezone(timezone.utc).date() < current_date


def monthly_fifth_refresh_due(latest_fetched_at: datetime | None, current_date: date) -> bool:
    if latest_fetched_at is None:
        return True
    return latest_fetched_at.astimezone(timezone.utc).date() < latest_monthly_fifth(current_date)


def latest_monthly_fifth(current_date: date) -> date:
    if current_date.day >= 5:
        return date(current_date.year, current_date.month, 5)
    if current_date.month == 1:
        return date(current_date.year - 1, 12, 5)
    return date(current_date.year, current_date.month - 1, 5)


def build_current_macro_snapshot(
    provider: CurrentMacroIndicatorsProvider,
    *,
    generated_at: datetime | None = None,
    strict: bool = False,
) -> CurrentMacroSnapshot:
    warnings = []
    key_rate = None
    ruonia = None
    annual_inflation = None

    try:
        key_rate = provider.get_key_rate()
    except Exception:
        warnings.append("Key rate could not be loaded from Bank of Russia.")

    try:
        ruonia = provider.get_latest_ruonia()
    except Exception:
        warnings.append("RUONIA could not be loaded from Bank of Russia.")

    try:
        annual_inflation = provider.get_latest_annual_inflation()
    except Exception:
        warnings.append("Annual inflation could not be loaded from Bank of Russia.")

    if strict and (key_rate is None or ruonia is None or annual_inflation is None):
        raise MacroIndicatorsStrictError("Current macro indicators are incomplete.")

    if ruonia is not None:
        warnings.append("RUONIA is published with a lag relative to the current date.")
    if annual_inflation is not None:
        warnings.append("Annual inflation is the latest published monthly year-on-year value, not a daily indicator.")

    return CurrentMacroSnapshot(
        generated_at=generated_at or datetime.now(timezone.utc),
        key_rate=key_rate,
        ruonia=ruonia,
        annual_inflation=annual_inflation,
        warnings=warnings,
    )
