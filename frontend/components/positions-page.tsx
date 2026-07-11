"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { getPortfolioPositions } from "@/lib/api";
import { formatMoney, formatReadableDate } from "@/lib/format";
import type { Money, PortfolioPositionsResponse, PositionPreview } from "@/lib/types";

type PositionFilter = "all" | "bond" | "share";
type PositionSort = "value_desc" | "ticker_asc" | "type_asc";

const FILTERS: Array<{ label: string; value: PositionFilter }> = [
  { label: "Все", value: "all" },
  { label: "Облигации", value: "bond" },
  { label: "Акции", value: "share" }
];

export function PositionsPageApp() {
  const [data, setData] = useState<PortfolioPositionsResponse | null>(null);
  const [filter, setFilter] = useState<PositionFilter>("all");
  const [sort, setSort] = useState<PositionSort>("value_desc");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadPositions() {
      setIsLoading(true);
      setError(null);
      try {
        const response = await getPortfolioPositions();
        if (isMounted) {
          setData(response);
        }
      } catch {
        if (isMounted) {
          setError("Не удалось загрузить позиции. Проверьте активную сессию и попробуйте обновить страницу.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadPositions();

    return () => {
      isMounted = false;
    };
  }, []);

  const positions = useMemo(() => {
    return sortPositions(filterPositions(data?.positions ?? [], filter), sort);
  }, [data?.positions, filter, sort]);

  return (
    <main className="dashboard-page">
      <PositionsSidebar accountLabel={data?.account_label ?? "нет данных"} status={isLoading ? "loading" : data ? "fresh" : "unavailable"} />

      <section className="dashboard-content" aria-label="Все позиции портфеля">
        <header className="dashboard-header positions-page-header">
          <div>
            <h1>Позиции</h1>
            <p>
              {data
                ? `${data.account_label} · период ${formatReadableDate(data.as_of)} · обновлено ${formatDateTime(data.generated_at)}`
                : "Полный список бумаг выбранного счета или всего портфеля"}
            </p>
          </div>
        </header>

        <section className="dashboard-card positions-card full-positions-card">
          <header>
            <div>
              <h2>Все бумаги</h2>
              <p>{isLoading ? "Загрузка позиций" : `${positions.length} из ${data?.positions.length ?? 0}`}</p>
            </div>

            <div className="positions-toolbar">
              <div className="segmented-control" aria-label="Фильтр по типу бумаги">
                {FILTERS.map((item) => (
                  <button
                    data-active={filter === item.value ? "true" : undefined}
                    key={item.value}
                    type="button"
                    onClick={() => setFilter(item.value)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              <label className="sort-select">
                <span>Сортировка</span>
                <select value={sort} onChange={(event) => setSort(event.target.value as PositionSort)}>
                  <option value="value_desc">Стоимость</option>
                  <option value="ticker_asc">Тикер</option>
                  <option value="type_asc">Тип</option>
                </select>
              </label>
            </div>
          </header>

          {isLoading ? <PositionsState text="Загружаем позиции портфеля." /> : null}
          {error ? <PositionsState text={error} tone="error" /> : null}
          {!isLoading && !error && positions.length === 0 ? <PositionsState text="Позиции не найдены." /> : null}
          {!isLoading && !error && positions.length > 0 ? <PositionsTable positions={positions} /> : null}
        </section>

        {data && data.warnings.length > 0 ? (
          <section className="dashboard-card warning-card" aria-label="Предупреждения по позициям">
            <h2>Предупреждения</h2>
            <ul>
              {data.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </section>
        ) : null}
      </section>
    </main>
  );
}

function PositionsSidebar({ accountLabel, status }: { accountLabel: string; status: string }) {
  return (
    <aside className="dashboard-sidebar" aria-label="Навигация">
      <div className="sidebar-brand">
        <div className="sidebar-logo">Ю</div>
        <div>
          <strong>Кооператив Юг</strong>
          <span>Портфель</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <p>НАВИГАЦИЯ</p>
        <Link className="sidebar-link" href="/">
          Обзор
        </Link>
        <Link className="sidebar-link" data-active="true" href="/positions">
          Позиции
        </Link>
        <button className="sidebar-link" disabled type="button">
          Доходы · скоро
        </button>
        <button className="sidebar-link" disabled type="button">
          Риски · скоро
        </button>
        <button className="sidebar-link" disabled type="button">
          Настройки
        </button>
      </nav>

      <div className="connection-card">
        <span className="connection-pill" data-mode="real">
          Real API
        </span>
        <p>Брокерский счёт</p>
        <div>
          <strong>{accountLabel}</strong>
        </div>
        <small>{status}</small>
      </div>
    </aside>
  );
}

function PositionsTable({ positions }: { positions: PositionPreview[] }) {
  return (
    <div className="positions-scroll">
      <table>
        <thead>
          <tr>
            <th>Бумага</th>
            <th>Тип</th>
            <th>Количество</th>
            <th>Средняя цена</th>
            <th>Текущая цена</th>
            <th>Стоимость</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => (
            <tr key={position.instrument_uid}>
              <td>
                <strong>{position.instrument_name || "Без названия"}</strong>
                <span>{[position.ticker, position.isin].filter(Boolean).join(" · ") || "нет данных"}</span>
              </td>
              <td>{instrumentTypeLabel(position.instrument_type)}</td>
              <td>{formatQuantity(position.quantity)}</td>
              <td>{formatOptionalMoney(position.average_position_price ?? null)}</td>
              <td>{formatOptionalMoney(position.current_price)}</td>
              <td>{formatOptionalMoney(position.market_value)}</td>
              <td>{sourceStatusLabel(position.source_status)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PositionsState({ text, tone = "muted" }: { text: string; tone?: "muted" | "error" }) {
  return (
    <div className="positions-state" data-tone={tone}>
      {text}
    </div>
  );
}

function filterPositions(positions: PositionPreview[], filter: PositionFilter): PositionPreview[] {
  if (filter === "all") {
    return positions;
  }
  return positions.filter((position) => normalizeInstrumentType(position.instrument_type) === filter);
}

function sortPositions(positions: PositionPreview[], sort: PositionSort): PositionPreview[] {
  return [...positions].sort((first, second) => {
    if (sort === "ticker_asc") {
      return first.ticker.localeCompare(second.ticker, "ru");
    }
    if (sort === "type_asc") {
      return (
        normalizeInstrumentType(first.instrument_type).localeCompare(normalizeInstrumentType(second.instrument_type), "ru")
        || first.ticker.localeCompare(second.ticker, "ru")
      );
    }
    return moneyToNumber(second.market_value) - moneyToNumber(first.market_value);
  });
}

function moneyToNumber(value: Money | null): number {
  if (!value) {
    return -1;
  }
  const amount = Number(value.amount);
  return Number.isFinite(amount) ? amount : -1;
}

function formatOptionalMoney(value: Money | null): string {
  return value ? formatMoney(value) : "нет данных";
}

function formatQuantity(value: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return value;
  }
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 4
  }).format(amount);
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function instrumentTypeLabel(type: string): string {
  const normalizedType = normalizeInstrumentType(type);
  const labels: Record<string, string> = {
    bond: "Облигация",
    share: "Акция",
    etf: "Фонд",
    fund: "Фонд",
    currency: "Валюта",
    money: "Деньги",
    cash: "Деньги"
  };
  return labels[normalizedType] ?? type;
}

function normalizeInstrumentType(type: string): string {
  const normalized = type.trim().toLowerCase().replace(/[- ]/g, "_").split(".").pop() ?? "";
  const withoutPrefix = normalized.startsWith("instrument_type_") ? normalized.replace("instrument_type_", "") : normalized;
  const aliases: Record<string, string> = {
    "1": "bond",
    bond: "bond",
    bonds: "bond",
    "2": "share",
    share: "share",
    shares: "share",
    stock: "share",
    stocks: "share",
    equity: "share",
    "3": "currency",
    currency: "currency",
    "4": "etf",
    etf: "etf",
    fund: "etf",
    funds: "etf"
  };
  return aliases[withoutPrefix] ?? withoutPrefix;
}

function sourceStatusLabel(value: string | undefined): string {
  if (value === "actual") {
    return "актуально";
  }
  return value || "нет данных";
}
