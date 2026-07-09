import type { ReactNode } from "react";

import type { DashboardData, Money, PositionPreview } from "@/lib/types";
import { formatMoney, formatPercent } from "@/lib/format";

const ALLOCATION_COLORS = ["#d8ff3e", "#78a9ff", "#f4c95d", "#68d391", "#a7afb8"];

export function Dashboard({
  dashboard,
  isRefreshing = false,
  onRefresh,
  sessionPanel
}: {
  dashboard: DashboardData;
  isRefreshing?: boolean;
  onRefresh?: () => void;
  sessionPanel?: ReactNode;
}) {
  const allocation = normalizeAllocation(dashboard.allocation);
  const totalValue = moneyToNumber(dashboard.portfolio.total_value);
  const positions = dashboard.positions_preview.slice(0, 5);

  return (
    <main className="dashboard-page">
      <Sidebar
        accountLabel={dashboard.portfolio.account_label}
        mode={dashboard.mode}
        sessionPanel={sessionPanel}
        status={dashboard.portfolio.status}
      />

      <section className="dashboard-content" aria-label="Состояние портфеля">
        <header className="dashboard-header">
          <div>
            <h1>Состояние портфеля</h1>
            <p>Обновлено {formatDashboardTimestamp(dashboard.portfolio.updated_at)}</p>
          </div>

          <div className="dashboard-actions">
            <button className="account-button" type="button" aria-label="Выбрать брокерский счет">
              {dashboard.portfolio.account_label === "demo_account" ? "Demo" : dashboard.portfolio.account_label}
              <span aria-hidden="true">⌄</span>
            </button>
            <button
              className="icon-button"
              disabled={!onRefresh || isRefreshing}
              type="button"
              aria-busy={isRefreshing}
              aria-label="Обновить данные"
              onClick={onRefresh}
            >
              {isRefreshing ? "…" : "↻"}
            </button>
          </div>
        </header>

        <section className="summary-grid" aria-label="Краткая сводка">
          <PortfolioSummary totalValue={dashboard.portfolio.total_value} />
          <BenchmarkCard dashboard={dashboard} />
        </section>

        <section className="kpi-grid" aria-label="Ключевые показатели">
          <KpiCard label="Ключевая ставка" value={formatPercent(dashboard.macro.key_rate)} note={macroNote(dashboard)} tone="info" />
          <KpiCard label="Инфляция" value={formatPercent(dashboard.macro.inflation_yoy)} note={macroNote(dashboard)} tone="info" />
          <KpiCard label="Ожидаемая доходность" value="нет данных" note={`Период: ${dashboard.portfolio.period}`} tone="info" />
          <KpiCard label="Доходность за день" value="нет данных" note={`Период: ${dashboard.portfolio.period}`} tone="info" compact />
        </section>

        <section className="insight-grid" aria-label="Структура и риски">
          <AllocationCard allocation={allocation} totalValue={totalValue} />
          <RisksCard positions={positions} totalValue={totalValue} allocation={allocation} />
        </section>

        <PositionsTable positions={positions} totalValue={totalValue} />

        {dashboard.warnings.length > 0 ? (
          <section className="dashboard-card warning-card" aria-label="Предупреждения">
            <h2>Предупреждения</h2>
            <ul>
              {dashboard.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </section>
        ) : null}

        <p className="dashboard-disclaimer">
          Сервис показывает аналитику и не является индивидуальной инвестиционной рекомендацией.
        </p>
      </section>
    </main>
  );
}

function Sidebar({
  accountLabel,
  mode,
  sessionPanel,
  status
}: {
  accountLabel: string;
  mode: DashboardData["mode"];
  sessionPanel?: ReactNode;
  status: string;
}) {
  const items = ["Обзор", "Позиции", "Доходы · скоро", "Риски · скоро", "Настройки"];

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
        {items.map((item, index) => (
          <button className="sidebar-link" data-active={index === 0 ? "true" : undefined} type="button" key={item}>
            {item}
          </button>
        ))}
      </nav>

      {sessionPanel ?? (
        <div className="connection-card">
          <span className="connection-pill" data-mode={mode}>
            {mode === "real" ? "Real API" : "Demo"}
          </span>
          <p>Брокерский счёт</p>
          <div>
            <strong>{accountLabel === "demo_account" ? "Demo" : accountLabel}</strong>
          </div>
          <small>{status}</small>
        </div>
      )}
    </aside>
  );
}

function PortfolioSummary({ totalValue }: { totalValue: Money | null }) {
  return (
    <article className="dashboard-card portfolio-summary">
      <p className="eyebrow">СТОИМОСТЬ ПОРТФЕЛЯ</p>
      <strong>{formatWholeMoney(totalValue)}</strong>
      <span className="neutral-text">Доходность за день: нет данных</span>

      <div className="sparkline" aria-hidden="true">
        {[0, 1, 2, 0, 1, 2].map((height, index) => (
          <i data-muted={index > 3 ? "true" : undefined} style={{ transform: `translateY(${height * -8}px)` }} key={index} />
        ))}
      </div>

      <div className="range-tabs" aria-label="Период графика">
        <button type="button" data-active="true">
          День
        </button>
        <button type="button">Месяц</button>
        <button type="button">Год</button>
        <button type="button">Всё время</button>
      </div>
    </article>
  );
}

function BenchmarkCard({ dashboard }: { dashboard: DashboardData }) {
  return (
    <article className="dashboard-card benchmark-card">
      <p className="eyebrow">ОТНОСИТЕЛЬНО ОРИЕНТИРОВ</p>
      <strong>нет данных</strong>
      <span>Период: {dashboard.portfolio.period}</span>
      <dl>
        <div>
          <dt>Инфляция</dt>
          <dd>{formatPercent(dashboard.macro.inflation_yoy)}</dd>
        </div>
        <div>
          <dt>Ключевая ставка</dt>
          <dd>{formatPercent(dashboard.macro.key_rate)}</dd>
        </div>
      </dl>
      <p className="benchmark-insight">{macroNote(dashboard)}</p>
    </article>
  );
}

function KpiCard({
  label,
  value,
  note,
  tone,
  compact = false
}: {
  label: string;
  value: string;
  note: string;
  tone: "info" | "positive";
  compact?: boolean;
}) {
  return (
    <article className="dashboard-card kpi-card" data-compact={compact ? "true" : undefined}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span data-tone={tone}>{note}</span>
    </article>
  );
}

function AllocationCard({ allocation, totalValue }: { allocation: AllocationItem[]; totalValue: number | null }) {
  return (
    <article className="dashboard-card allocation-card">
      <header>
        <h2>Структура портфеля</h2>
        <p>По классам активов</p>
      </header>

      <div className="allocation-body">
        <div className="donut" style={{ background: allocationGradient(allocation) }} aria-label="Диаграмма структуры портфеля">
          <div>
            <strong>{formatMillionShort(totalValue)}</strong>
            {allocation[0]?.currency ? <span>{allocation[0].currency}</span> : null}
          </div>
        </div>

        <div className="allocation-legend">
          {allocation.length > 0 ? (
            allocation.map((item) => (
              <div className="allocation-row" key={item.type}>
                <span style={{ backgroundColor: item.color }} aria-hidden="true" />
                <strong>{item.label}</strong>
                <em>{formatCompactMoney(item.value, item.currency)}</em>
                <b>{formatDisplayPercent(item.sharePercent)}</b>
              </div>
            ))
          ) : (
            <p className="muted">Структура портфеля недоступна.</p>
          )}
        </div>
      </div>
    </article>
  );
}

function RisksCard({
  positions,
  totalValue,
  allocation
}: {
  positions: PositionPreview[];
  totalValue: number | null;
  allocation: AllocationItem[];
}) {
  const largestPositionShare = positions[0] ? shareOfTotal(moneyToNumber(positions[0].market_value), totalValue) : null;
  const largestTypeShare = allocation[0]?.sharePercent ?? null;
  const currencyShare = allocation.find((item) => item.type === "currency")?.sharePercent ?? null;

  return (
    <article className="dashboard-card risks-card">
      <header>
        <h2>Риски портфеля</h2>
        <p>Автоматические правила, не рекомендация</p>
      </header>

      <RiskLine
        label="Крупнейшая позиция"
        value={largestPositionShare ? formatDisplayPercent(largestPositionShare) : "нет данных"}
        note="Период: текущий snapshot"
        tone="warning"
      />
      <RiskLine
        label="Один эмитент"
        value={largestTypeShare ? formatDisplayPercent(largestTypeShare) : "нет данных"}
        note="Расчёт по доступной структуре"
        tone="warning"
      />
      <RiskLine label="Валютные активы" value={formatDisplayPercent(currencyShare)} note="Расчёт по доступной структуре" tone="positive" />
    </article>
  );
}

function RiskLine({ label, value, note, tone }: { label: string; value: string; note: string; tone: "warning" | "positive" }) {
  return (
    <div className="risk-line">
      <div>
        <p>{label}</p>
        <span data-tone={tone}>{note}</span>
      </div>
      <strong>{value}</strong>
    </div>
  );
}

function PositionsTable({ positions, totalValue }: { positions: PositionPreview[]; totalValue: number | null }) {
  return (
    <section className="dashboard-card positions-card">
      <header>
        <h2>Крупнейшие позиции</h2>
        <button type="button">Все позиции →</button>
      </header>

      <div className="positions-scroll">
        <table>
          <thead>
            <tr>
              <th>Актив</th>
              <th>Тип</th>
              <th>Количество</th>
              <th>Стоимость</th>
              <th>Доходность</th>
              <th>Доля</th>
            </tr>
          </thead>
          <tbody>
            {positions.length > 0 ? (
              positions.map((position) => {
                const marketValue = moneyToNumber(position.market_value);
                const positionShare = shareOfTotal(marketValue, totalValue);

                return (
                  <tr key={position.instrument_uid}>
                    <td>
                      <strong>{position.instrument_name}</strong>
                      <span>{position.ticker}</span>
                    </td>
                    <td>{instrumentTypeLabel(position.instrument_type, "singular")}</td>
                    <td>{formatQuantity(position.quantity)}</td>
                    <td>{position.market_value ? formatWholeMoney(position.market_value) : "нет данных"}</td>
                    <td>нет данных</td>
                    <td>{positionShare ? formatDisplayPercent(positionShare) : "нет данных"}</td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={6}>Позиции не найдены.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

type AllocationItem = {
  type: string;
  label: string;
  value: number;
  currency: string;
  sharePercent: string | null;
  color: string;
};

function normalizeAllocation(allocation: DashboardData["allocation"]): AllocationItem[] {
  return allocation
    .map((item, index) => ({
      type: item.type,
      label: instrumentTypeLabel(item.type, "plural"),
      value: moneyToNumber(item.value) ?? 0,
      currency: item.value.currency,
      sharePercent: item.share_percent,
      color: ALLOCATION_COLORS[index % ALLOCATION_COLORS.length]
    }))
    .sort((first, second) => second.value - first.value);
}

function allocationGradient(allocation: AllocationItem[]) {
  if (allocation.length === 0) {
    return "conic-gradient(#2a3038 0 100%)";
  }

  let start = 0;
  const stops = allocation.map((item) => {
    const share = Number((item.sharePercent ?? "0").replace(",", "."));
    const end = start + (Number.isFinite(share) ? share : 0);
    const segment = `${item.color} ${start}% ${end}%`;
    start = end;
    return segment;
  });

  if (start < 100) {
    stops.push(`#2a3038 ${start}% 100%`);
  }

  return `conic-gradient(${stops.join(", ")})`;
}

function instrumentTypeLabel(type: string, form: "plural" | "singular") {
  const pluralLabels: Record<string, string> = {
    bond: "Облигации",
    share: "Акции",
    etf: "Фонды",
    fund: "Фонды",
    currency: "Валюта",
    money: "Деньги",
    cash: "Деньги"
  };
  const singularLabels: Record<string, string> = {
    bond: "Облигация",
    share: "Акция",
    etf: "Фонд",
    fund: "Фонд",
    currency: "Валюта",
    money: "Деньги",
    cash: "Деньги"
  };

  return (form === "plural" ? pluralLabels[type] : singularLabels[type]) ?? type;
}

function moneyToNumber(value: Money | null): number | null {
  if (!value) {
    return null;
  }

  const amount = Number(value.amount);
  return Number.isFinite(amount) ? amount : null;
}

function shareOfTotal(part: number | null, total: number | null): string | null {
  if (part === null || total === null || total <= 0) {
    return null;
  }

  return (part / total * 100).toFixed(1).replace(".", ",");
}

function formatDisplayPercent(value: string | null): string {
  return formatPercent(value).replace(".", ",");
}

function formatWholeMoney(value: Money | null) {
  if (!value) {
    return "нет данных";
  }
  const amount = moneyToNumber(value);
  if (amount === null) {
    return formatMoney(value);
  }

  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: value.currency,
    maximumFractionDigits: 0
  }).format(amount);
}

function formatCompactMoney(value: number, currency: string) {
  const symbol = currency === "RUB" ? "₽" : currency;
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2).replace(".", ",")} млн ${symbol}`;
  }

  if (value >= 1_000) {
    return `${Math.round(value / 1_000)} тыс ${symbol}`;
  }

  return `${Math.round(value)} ${symbol}`;
}

function formatMillionShort(value: number | null) {
  if (value === null) {
    return "нет данных";
  }

  if (value <= 0) {
    return "0";
  }

  return `${(value / 1_000_000).toFixed(2).replace(".", ",")} млн`;
}

function formatQuantity(value: string) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return value;
  }

  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 4
  }).format(amount);
}

function formatDashboardTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit"
  })
    .format(date)
    .replace(" г. в", ",");
}

function macroNote(dashboard: DashboardData): string {
  if (dashboard.macro.updated_at) {
    return `Обновлено ${formatDashboardTimestamp(dashboard.macro.updated_at)}`;
  }
  return `Макроданные недоступны · период ${dashboard.portfolio.period}`;
}
