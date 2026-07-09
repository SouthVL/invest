import type { Money } from "@/lib/types";

export function formatMoney(value: Money): string {
  const amount = Number(value.amount);
  if (!Number.isFinite(amount)) {
    return `${value.amount} ${value.currency}`;
  }

  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: value.currency,
    maximumFractionDigits: 2
  }).format(amount);
}

export function formatPercent(value: string | null): string {
  if (value === null) {
    return "нет данных";
  }
  return `${value}%`;
}

export function formatReadableDate(value: string): string {
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(date);
}
