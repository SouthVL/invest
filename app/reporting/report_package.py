from __future__ import annotations

import csv
import html
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
from pathlib import Path
from typing import Any

from app.domain.bond_offer import BondOfferEvent
from app.domain.cashflow import CashflowEvent, CashflowType, MonthlyCashflow
from app.reporting.cashflow import (
    SCHEMA_VERSION,
    CashflowAccountReport,
    CashflowReport,
    combine_monthly_rows,
    event_source_label,
    source_status,
)
from app.reporting.offers import OffersAccountReport, OffersReport
from app.reporting.serializers.cashflow_csv import cashflow_events_to_csv, cashflow_monthly_to_csv
from app.reporting.serializers.cashflow_json import cashflow_report_to_dict, decimal_text, iso_datetime, money
from app.reporting.serializers.offers_csv import offers_to_csv
from app.reporting.serializers.offers_json import offers_report_to_dict

DISCLAIMER = "Forecasts are estimates and are not investment advice."
REPORT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ReportPackage:
    output_dir: Path
    manifest: dict[str, Any]
    files: list[Path]


def write_report_package(
    *,
    output_dir: Path,
    cashflow_report: CashflowReport,
    offers_report: OffersReport,
    mode: str,
    scenario: str = "base",
    anonymize: bool = False,
) -> ReportPackage:
    output_dir.mkdir(parents=True, exist_ok=True)
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    if anonymize:
        cashflow_report = anonymize_cashflow_report(cashflow_report)
        offers_report = anonymize_offers_report(offers_report)

    files: list[Path] = []
    monthly_rows = combine_monthly_rows(cashflow_report.accounts, currency=cashflow_report.report_currency)
    summary = build_summary(cashflow_report, offers_report, monthly_rows)
    data_quality = build_data_quality(cashflow_report, offers_report, anonymize=anonymize)

    def write_text(relative_path: str, content: str) -> None:
        path = output_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        files.append(path)

    def write_json(relative_path: str, payload: Any) -> None:
        write_text(relative_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    offers_payload = offers_report_to_dict(offers_report)
    charts = build_charts(monthly_rows=monthly_rows, cashflow_report=cashflow_report, offers_report=offers_report)

    write_json("summary.json", summary)
    write_json("portfolio.json", build_portfolio_placeholder(cashflow_report, mode=mode))
    write_text("portfolio.csv", portfolio_csv(cashflow_report, mode=mode))
    write_json("cashflow_monthly.json", cashflow_monthly_payload(cashflow_report))
    write_text("cashflow_monthly.csv", cashflow_monthly_to_csv(cashflow_report))
    write_json("cashflow_events.json", cashflow_events_payload(cashflow_report))
    write_text("cashflow_events.csv", cashflow_events_to_csv(cashflow_report))
    write_text("maturities.csv", maturities_csv(cashflow_report))
    write_json("offers.json", offers_payload)
    write_text("offers.csv", offers_to_csv(offers_report))
    write_json("floating_scenarios.json", floating_scenarios_placeholder(cashflow_report, scenario=scenario))
    write_text("floating_scenarios.csv", floating_scenarios_csv(cashflow_report, scenario=scenario))
    write_json("data_quality.json", data_quality)

    for name, svg in charts.items():
        write_text(f"charts/{name}.svg", svg)

    write_text(
        "report.html",
        build_html_report(
            cashflow_report=cashflow_report,
            offers_report=offers_report,
            summary=summary,
            data_quality=data_quality,
            charts=charts,
            mode=mode,
            scenario=scenario,
        ),
    )

    manifest = build_manifest(
        cashflow_report=cashflow_report,
        mode=mode,
        scenario=scenario,
        files=files,
        output_dir=output_dir,
        warnings=sorted({*cashflow_report.warnings, *offers_report.warnings}),
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files.insert(0, manifest_path)
    return ReportPackage(output_dir=output_dir, manifest=manifest, files=files)


def build_manifest(
    *,
    cashflow_report: CashflowReport,
    mode: str,
    scenario: str,
    files: list[Path],
    output_dir: Path,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": report_id(cashflow_report.as_of, mode=mode),
        "generated_at": iso_datetime(cashflow_report.generated_at),
        "as_of": cashflow_report.as_of.isoformat(),
        "months": cashflow_report.months,
        "currency": cashflow_report.report_currency,
        "mode": mode,
        "scenario": scenario,
        "files": [file_entry(path.relative_to(output_dir)) for path in files],
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }


def report_id(as_of: date, *, mode: str) -> str:
    return f"{as_of.isoformat()}-{mode}-001"


def file_entry(path: Path) -> dict[str, str]:
    suffix = path.suffix.removeprefix(".")
    return {
        "path": path.as_posix(),
        "type": path.stem,
        "format": suffix,
    }


def build_summary(
    cashflow_report: CashflowReport,
    offers_report: OffersReport,
    monthly_rows: list[MonthlyCashflow],
) -> dict[str, Any]:
    total = cashflow_report.summary.total
    nearest_offer = nearest_offer_payload(offers_report)
    min_month = min(monthly_rows, key=lambda row: row.total, default=None)
    max_month = max(monthly_rows, key=lambda row: row.total, default=None)
    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": cashflow_report.as_of.isoformat(),
        "months": cashflow_report.months,
        "currency": cashflow_report.report_currency,
        "expected_cashflow": money(total, cashflow_report.report_currency),
        "confirmed_payments": money(cashflow_report.summary.actual_total, cashflow_report.report_currency),
        "forecast_payments": money(cashflow_report.summary.estimated_total, cashflow_report.report_currency),
        "unknown_payments_count": cashflow_report.summary.unknown_count,
        "coupons": money(cashflow_report.summary.fixed_coupons + cashflow_report.summary.floating_coupons, cashflow_report.report_currency),
        "fixed_coupons": money(cashflow_report.summary.fixed_coupons, cashflow_report.report_currency),
        "floating_coupons": money(cashflow_report.summary.floating_coupons, cashflow_report.report_currency),
        "dividends": money(cashflow_report.summary.dividends, cashflow_report.report_currency),
        "amortizations": money(cashflow_report.summary.amortizations, cashflow_report.report_currency),
        "maturities": money(cashflow_report.summary.maturities, cashflow_report.report_currency),
        "average_monthly_cashflow": money(round_decimal(total / Decimal(cashflow_report.months)), cashflow_report.report_currency),
        "minimum_month": month_payload(min_month),
        "maximum_month": month_payload(max_month),
        "nearest_offer": nearest_offer,
        "attention_events_count": offers_report.summary.get("warnings_count", 0),
        "forecast_share": decimal_text(round_ratio((cashflow_report.summary.estimated_total / total) if total else Decimal("0"))),
        "currency_structure": currency_structure(cashflow_report),
        "warnings": sorted({*cashflow_report.warnings, *offers_report.warnings}),
    }


def month_payload(row: MonthlyCashflow | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "month": row.month,
        "total": money(row.total, row.currency),
    }


def nearest_offer_payload(report: OffersReport) -> dict[str, Any] | None:
    offers = [offer for account in report.accounts for offer in account.offers]
    if not offers:
        return None
    offer = min(offers, key=lambda item: item.offer_date)
    return {
        "instrument_name": offer.name,
        "offer_date": offer.offer_date.isoformat(),
        "event_type": offer.event_type.value,
        "days_until_offer": offer.days_until_offer,
        "status": offer.status.value,
    }


def currency_structure(report: CashflowReport) -> list[dict[str, str]]:
    totals: dict[str, Decimal] = {}
    for account in report.accounts:
        for event in account.events:
            currency = (event.payment_currency or event.currency).upper()
            amount = event.payment_total_amount if event.payment_total_amount is not None else event.total_amount
            totals[currency] = totals.get(currency, Decimal("0")) + amount
    return [{"currency": currency, "amount": decimal_text(amount)} for currency, amount in sorted(totals.items())]


def round_decimal(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def round_ratio(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def build_data_quality(cashflow_report: CashflowReport, offers_report: OffersReport, *, anonymize: bool) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    for account in cashflow_report.accounts:
        for event in account.events:
            status = source_status(event.source)
            statuses[status] = statuses.get(status, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "anonymized": anonymize,
        "cashflow": cashflow_report.data_quality,
        "offers": offers_report.data_quality,
        "source_status_counts": statuses,
        "warnings": sorted({*cashflow_report.warnings, *offers_report.warnings}),
        "limitations": [
            "Future payments can change before the payment date.",
            "Amortizations and maturities are capital return, not investment income.",
            "Foreign-currency payments are reported in the selected report currency when conversion data is available.",
        ],
    }


def cashflow_monthly_payload(report: CashflowReport) -> dict[str, Any]:
    return {
        "schema_version": report.schema_version,
        "report_type": "cashflow_monthly",
        "as_of": report.as_of.isoformat(),
        "months": report.months,
        "report_currency": report.report_currency,
        "accounts": [
            {
                "account_label": account.account_label,
                "monthly": [
                    {
                        "month": row.month,
                        "fixed_coupons": money(row.fixed_coupons, row.currency),
                        "floating_coupons": money(row.floating_coupons, row.currency),
                        "dividends": money(row.dividends, row.currency),
                        "amortizations": money(row.amortizations, row.currency),
                        "maturities": money(row.maturities, row.currency),
                        "total": money(row.total, row.currency),
                    }
                    for row in account.monthly
                ],
            }
            for account in report.accounts
        ],
    }


def cashflow_events_payload(report: CashflowReport) -> dict[str, Any]:
    payload = cashflow_report_to_dict(report)
    return {
        "schema_version": report.schema_version,
        "report_type": "cashflow_events",
        "as_of": report.as_of.isoformat(),
        "months": report.months,
        "report_currency": report.report_currency,
        "accounts": [
            {
                "account_label": account["account_label"],
                "events": account["events"],
            }
            for account in payload["accounts"]
        ],
    }


def build_portfolio_placeholder(report: CashflowReport, *, mode: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "report_type": "portfolio",
        "mode": mode,
        "as_of": report.as_of.isoformat(),
        "accounts": [{"account_label": account.account_label} for account in report.accounts],
        "data_status": "unknown",
        "warning": "Portfolio holdings snapshot is not included in the report MVP yet.",
    }


def portfolio_csv(report: CashflowReport, *, mode: str) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["account_label", "mode", "data_status", "note"])
    for account in report.accounts:
        writer.writerow([account.account_label, mode, "unknown", "Portfolio holdings snapshot is not included in the report MVP yet."])
    return output.getvalue()


def maturities_csv(report: CashflowReport) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["account_label", "payment_date", "instrument_name", "isin", "quantity", "total_amount", "currency", "source_status"])
    for account in report.accounts:
        for event in account.events:
            if event.event_type == CashflowType.MATURITY:
                writer.writerow(
                    [
                        account.account_label,
                        event.event_date.isoformat(),
                        event.name,
                        event.isin or "",
                        decimal_text(event.quantity),
                        decimal_text(event.total_amount),
                        event.currency.upper(),
                        source_status(event.source),
                    ]
                )
    return output.getvalue()


def floating_scenarios_placeholder(report: CashflowReport, *, scenario: str) -> dict[str, Any]:
    floating_events = [
        {
            "instrument_name": event.name,
            "payment_date": event.event_date.isoformat(),
            "scenario": scenario,
            "amount": money(event.total_amount, event.currency),
            "source": event_source_label(event),
            "source_status": source_status(event.source),
        }
        for account in report.accounts
        for event in account.events
        if "floating" in event_source_label(event)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "report_type": "floating_scenarios",
        "scenario": scenario,
        "events": floating_events,
        "warning": "Full multi-scenario rate matrix export is not included in the report MVP yet.",
    }


def floating_scenarios_csv(report: CashflowReport, *, scenario: str) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["instrument_name", "payment_date", "scenario", "total_amount", "currency", "source", "source_status"])
    for account in report.accounts:
        for event in account.events:
            source = event_source_label(event)
            if "floating" in source:
                writer.writerow(
                    [
                        event.name,
                        event.event_date.isoformat(),
                        scenario,
                        decimal_text(event.total_amount),
                        event.currency.upper(),
                        source,
                        source_status(event.source),
                    ]
                )
    return output.getvalue()


def build_charts(
    *,
    monthly_rows: list[MonthlyCashflow],
    cashflow_report: CashflowReport,
    offers_report: OffersReport,
) -> dict[str, str]:
    return {
        "cashflow_monthly": monthly_cashflow_svg(monthly_rows),
        "cashflow_cumulative": cumulative_cashflow_svg(monthly_rows),
        "payment_structure": payment_structure_svg(cashflow_report),
        "offers_timeline": offers_timeline_svg(offers_report),
        "floating_scenarios": floating_scenarios_svg(cashflow_report),
    }


def monthly_cashflow_svg(rows: list[MonthlyCashflow]) -> str:
    width, height = 920, 360
    chart_top, chart_bottom = 40, 300
    max_total = max((row.total for row in rows), default=Decimal("1")) or Decimal("1")
    bar_width = max(18, min(52, 700 // max(1, len(rows))))
    gap = 12
    x = 70
    colors = [
        ("fixed_coupons", "#2f6fbb"),
        ("floating_coupons", "#2b9b78"),
        ("dividends", "#8b5fbf"),
        ("amortizations", "#d18f25"),
        ("maturities", "#6b7280"),
    ]
    parts = [svg_header(width, height), '<text x="24" y="24" class="title">Monthly cashflow by payment type</text>']
    parts.append(f'<line x1="60" y1="{chart_bottom}" x2="890" y2="{chart_bottom}" class="axis"/>')
    for row in rows:
        y = chart_bottom
        for field, color in colors:
            value = getattr(row, field)
            segment_height = int((value / max_total) * Decimal(chart_bottom - chart_top)) if value else 0
            if segment_height:
                y -= segment_height
                parts.append(f'<rect x="{x}" y="{y}" width="{bar_width}" height="{segment_height}" fill="{color}"/>')
        parts.append(f'<text x="{x + bar_width / 2:.0f}" y="326" class="label" text-anchor="middle">{html.escape(row.month[5:])}</text>')
        x += bar_width + gap
    parts.append(legend(colors, x=620, y=52))
    parts.append("</svg>")
    return "".join(parts)


def cumulative_cashflow_svg(rows: list[MonthlyCashflow]) -> str:
    width, height = 920, 320
    chart_left, chart_top, chart_right, chart_bottom = 70, 44, 880, 270
    cumulative: list[Decimal] = []
    total = Decimal("0")
    for row in rows:
        total += row.total
        cumulative.append(total)
    max_total = max(cumulative, default=Decimal("1")) or Decimal("1")
    points = []
    for index, value in enumerate(cumulative):
        x = chart_left + int((chart_right - chart_left) * index / max(1, len(cumulative) - 1))
        y = chart_bottom - int((value / max_total) * Decimal(chart_bottom - chart_top))
        points.append(f"{x},{y}")
    parts = [svg_header(width, height), '<text x="24" y="24" class="title">Cumulative cashflow</text>']
    parts.append(f'<line x1="{chart_left}" y1="{chart_bottom}" x2="{chart_right}" y2="{chart_bottom}" class="axis"/>')
    if points:
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#2f6fbb" stroke-width="3"/>')
    parts.append('<text x="24" y="302" class="note">Includes capital return where amortizations or maturities are present.</text>')
    parts.append("</svg>")
    return "".join(parts)


def payment_structure_svg(report: CashflowReport) -> str:
    rows = [
        ("Fixed coupons", report.summary.fixed_coupons, "#2f6fbb"),
        ("Floating coupons", report.summary.floating_coupons, "#2b9b78"),
        ("Dividends", report.summary.dividends, "#8b5fbf"),
        ("Amortizations", report.summary.amortizations, "#d18f25"),
        ("Maturities", report.summary.maturities, "#6b7280"),
    ]
    max_value = max((value for _, value, _ in rows), default=Decimal("1")) or Decimal("1")
    parts = [svg_header(760, 300), '<text x="24" y="24" class="title">Payment structure</text>']
    y = 56
    for label, value, color in rows:
        width = int((value / max_value) * Decimal("420")) if value else 0
        parts.append(f'<text x="24" y="{y + 15}" class="label">{html.escape(label)}</text>')
        parts.append(f'<rect x="170" y="{y}" width="{width}" height="22" fill="{color}"/>')
        parts.append(f'<text x="{180 + width}" y="{y + 15}" class="label">{html.escape(decimal_text(value))}</text>')
        y += 38
    parts.append("</svg>")
    return "".join(parts)


def offers_timeline_svg(report: OffersReport) -> str:
    offers = sorted([offer for account in report.accounts for offer in account.offers], key=lambda item: item.offer_date)
    width, height = 920, 260
    left, right, y = 70, 870, 126
    max_days = max((offer.days_until_offer for offer in offers), default=1) or 1
    parts = [svg_header(width, height), '<text x="24" y="24" class="title">Offers timeline</text>']
    parts.append(f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" class="axis"/>')
    for offer in offers:
        x = left + int((right - left) * offer.days_until_offer / max_days)
        color = "#d18f25" if offer.status.value == "warning" else "#2f6fbb"
        parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}"/>')
        parts.append(f'<text x="{x}" y="{y + 28}" class="label" text-anchor="middle">{html.escape(offer.offer_date.isoformat())}</text>')
        parts.append(f'<text x="{x}" y="{y - 16}" class="label" text-anchor="middle">{html.escape(offer.event_type.value)}</text>')
    if not offers:
        parts.append('<text x="70" y="130" class="note">No offers inside the selected window.</text>')
    parts.append("</svg>")
    return "".join(parts)


def floating_scenarios_svg(report: CashflowReport) -> str:
    events = [event for account in report.accounts for event in account.events if "floating" in event_source_label(event)]
    parts = [svg_header(760, 260), '<text x="24" y="24" class="title">Floating coupon scenario markers</text>']
    if not events:
        parts.append('<text x="24" y="90" class="note">No floating coupon events in the selected window.</text>')
    y = 70
    max_value = max((event.total_amount for event in events), default=Decimal("1")) or Decimal("1")
    for event in events:
        width = int((event.total_amount / max_value) * Decimal("420"))
        status = source_status(event.source)
        opacity = "0.55" if status != "actual" else "1"
        parts.append(f'<text x="24" y="{y + 15}" class="label">{html.escape(event.event_date.isoformat())}</text>')
        parts.append(f'<rect x="150" y="{y}" width="{width}" height="22" fill="#2b9b78" opacity="{opacity}"/>')
        parts.append(f'<text x="{160 + width}" y="{y + 15}" class="label">{html.escape(status)}</text>')
        y += 38
    parts.append("</svg>")
    return "".join(parts)


def svg_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        "<style>"
        ".title{font:700 18px Arial,sans-serif;fill:#111827}"
        ".label{font:12px Arial,sans-serif;fill:#374151}"
        ".note{font:12px Arial,sans-serif;fill:#6b7280}"
        ".axis{stroke:#9ca3af;stroke-width:1}"
        "</style>"
    )


def legend(items: list[tuple[str, str]], *, x: int, y: int) -> str:
    labels = {
        "fixed_coupons": "fixed coupons",
        "floating_coupons": "floating coupons",
        "dividends": "dividends",
        "amortizations": "amortizations",
        "maturities": "maturities",
    }
    parts = []
    for index, (field, color) in enumerate(items):
        item_y = y + index * 20
        parts.append(f'<rect x="{x}" y="{item_y - 10}" width="12" height="12" fill="{color}"/>')
        parts.append(f'<text x="{x + 18}" y="{item_y}" class="label">{html.escape(labels[field])}</text>')
    return "".join(parts)


def build_html_report(
    *,
    cashflow_report: CashflowReport,
    offers_report: OffersReport,
    summary: dict[str, Any],
    data_quality: dict[str, Any],
    charts: dict[str, str],
    mode: str,
    scenario: str,
) -> str:
    metrics = [
        ("Expected cashflow", summary["expected_cashflow"]),
        ("Confirmed payments", summary["confirmed_payments"]),
        ("Forecast payments", summary["forecast_payments"]),
        ("Coupons", summary["coupons"]),
        ("Dividends", summary["dividends"]),
        (
            "Capital return",
            money(cashflow_report.summary.amortizations + cashflow_report.summary.maturities, cashflow_report.report_currency),
        ),
    ]
    offer = summary["nearest_offer"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cooperative South Finance Lab Report</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #111827; background: #f9fafb; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 28px; }}
    section {{ margin: 24px 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }}
    .card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; }}
    .metric {{ font-size: 24px; font-weight: 700; margin-top: 6px; }}
    .label {{ color: #6b7280; font-size: 13px; }}
    .warning {{ color: #92400e; }}
    svg {{ max-width: 100%; height: auto; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; font-size: 14px; }}
  </style>
</head>
<body>
<main>
  <h1>Cooperative South Finance Lab Report</h1>
  <p>Data date: {html.escape(cashflow_report.as_of.isoformat())}. Mode: {html.escape(mode)}. Scenario: {html.escape(scenario)}.</p>
  <p class="warning">{html.escape(DISCLAIMER)}</p>
  <section>
    <h2>Summary</h2>
    <div class="grid">{metric_cards(metrics)}</div>
  </section>
  <section>
    <h2>Monthly cashflow</h2>
    {charts["cashflow_monthly"]}
  </section>
  <section>
    <h2>Cumulative cashflow</h2>
    {charts["cashflow_cumulative"]}
  </section>
  <section>
    <h2>Payment structure</h2>
    {charts["payment_structure"]}
  </section>
  <section>
    <h2>Large future payments</h2>
    {events_table(cashflow_report)}
  </section>
  <section>
    <h2>Offers and important dates</h2>
    {charts["offers_timeline"]}
    <p>{html.escape(nearest_offer_text(offer))}</p>
  </section>
  <section>
    <h2>Floating scenarios</h2>
    {charts["floating_scenarios"]}
  </section>
  <section>
    <h2>Data quality</h2>
    <pre>{html.escape(json.dumps(data_quality, ensure_ascii=False, indent=2))}</pre>
  </section>
  <section>
    <h2>Methodology</h2>
    <p>Cashflow includes coupons, dividends, amortizations, and maturities. Amortizations and maturities are capital return, not income. Forecast and estimated rows are marked in the JSON/CSV files.</p>
  </section>
  <section>
    <h2>Files</h2>
    <p>See manifest.json for the full list of generated files.</p>
  </section>
</main>
</body>
</html>
"""


def metric_cards(metrics: list[tuple[str, dict[str, str]]]) -> str:
    return "".join(
        f'<div class="card"><div class="label">{html.escape(label)}</div>'
        f'<div class="metric">{html.escape(value["amount"])} {html.escape(value["currency"])}</div></div>'
        for label, value in metrics
    )


def events_table(report: CashflowReport) -> str:
    events = sorted([event for account in report.accounts for event in account.events], key=lambda item: item.total_amount, reverse=True)[
        :8
    ]
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(event.event_date.isoformat())}</td>"
        f"<td>{html.escape(event.name)}</td>"
        f"<td>{html.escape(event.event_type.value)}</td>"
        f"<td>{html.escape(decimal_text(event.total_amount))} {html.escape(event.currency)}</td>"
        f"<td>{html.escape(source_status(event.source))}</td>"
        "</tr>"
        for event in events
    )
    return (
        "<table><thead><tr><th>Date</th><th>Instrument</th><th>Type</th><th>Total</th><th>Status</th></tr></thead><tbody>"
        + rows
        + "</tbody></table>"
    )


def nearest_offer_text(offer: dict[str, Any] | None) -> str:
    if not offer:
        return "No offers inside the selected window."
    return f"Nearest offer: {offer['instrument_name']} on {offer['offer_date']} ({offer['event_type']}, {offer['status']})."


def anonymize_cashflow_report(report: CashflowReport) -> CashflowReport:
    aliases: dict[str, str] = {}
    accounts: list[CashflowAccountReport] = []
    for account_index, account in enumerate(report.accounts, start=1):
        events = [anonymize_cashflow_event(event, aliases) for event in account.events]
        accounts.append(
            account.model_copy(
                update={
                    "account_label": f"account_{account_index}",
                    "account_id": None,
                    "events": events,
                }
            )
        )
    return report.model_copy(update={"accounts": accounts})


def anonymize_cashflow_event(event: CashflowEvent, aliases: dict[str, str]) -> CashflowEvent:
    key = event.instrument_uid or event.figi or event.isin or event.name
    aliases.setdefault(key, f"Instrument {len(aliases) + 1}")
    return event.model_copy(
        update={
            "instrument_uid": f"instrument_{len(aliases)}",
            "figi": None,
            "isin": None,
            "name": aliases[key],
        }
    )


def anonymize_offers_report(report: OffersReport) -> OffersReport:
    aliases: dict[str, str] = {}
    accounts: list[OffersAccountReport] = []
    for account_index, account in enumerate(report.accounts, start=1):
        offers = [anonymize_offer(offer, aliases) for offer in account.offers]
        accounts.append(
            account.model_copy(
                update={
                    "account_label": f"account_{account_index}",
                    "account_id": None,
                    "offers": offers,
                }
            )
        )
    return report.model_copy(update={"accounts": accounts})


def anonymize_offer(offer: BondOfferEvent, aliases: dict[str, str]) -> BondOfferEvent:
    key = offer.instrument_uid or offer.figi or offer.isin or offer.name
    aliases.setdefault(key, f"Instrument {len(aliases) + 1}")
    return offer.model_copy(
        update={
            "instrument_uid": f"instrument_{len(aliases)}",
            "figi": None,
            "isin": "",
            "name": aliases[key],
        }
    )
