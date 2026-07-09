import type { DemoDashboard } from "@/lib/types";
import { formatMoney, formatPercent, formatReadableDate } from "@/lib/format";

export function Dashboard({ dashboard }: { dashboard: DemoDashboard }) {
  const macroTone = dashboard.macro.status === "fresh" ? "ok" : "warning";

  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <h1 className="brand-title">Кооператив Юг — Портфель инвестора</h1>
            <span className="brand-caption">Demo dashboard на read-only данных</span>
          </div>
          <span className="status-pill" data-tone="ok">
            {dashboard.portfolio.status} · {formatReadableDate(dashboard.portfolio.period)}
          </span>
        </header>

        <section className="hero">
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2 className="section-title">Стоимость портфеля</h2>
                <p className="section-caption">Обновлено: {dashboard.portfolio.updated_at}</p>
              </div>
              <span className="status-pill" data-tone="ok">
                {dashboard.mode}
              </span>
            </div>
            <p className="total-value">{formatMoney(dashboard.portfolio.total_value)}</p>
            <p className="muted">Доходность не рассчитана: demo endpoint не подменяет отсутствующие данные нулём.</p>
          </div>

          <div className="panel">
            <div className="panel-header">
              <div>
                <h2 className="section-title">Макроданные</h2>
                <p className="section-caption">Банк России</p>
              </div>
              <span className="status-pill" data-tone={macroTone}>
                {dashboard.macro.status}
              </span>
            </div>
            <p className="muted">Ключевая ставка и инфляция недоступны в demo API.</p>
          </div>
        </section>

        <section className="metric-grid" aria-label="Краткие показатели">
          <Metric label="Cashflow, 12 месяцев" value={formatMoney(dashboard.cashflow_summary.total)} />
          <Metric label="Подтверждено" value={formatMoney(dashboard.cashflow_summary.actual_total)} />
          <Metric label="Оценка" value={formatMoney(dashboard.cashflow_summary.estimated_total)} />
        </section>

        <section className="content-grid" style={{ marginTop: 16 }}>
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2 className="section-title">Структура</h2>
                <p className="section-caption">По типам инструментов</p>
              </div>
            </div>
            <div className="allocation-list">
              {dashboard.allocation.length > 0 ? (
                dashboard.allocation.map((item) => (
                  <div className="allocation-row" key={item.type}>
                    <div className="allocation-head">
                      <strong>{instrumentTypeLabel(item.type)}</strong>
                      <span>
                        {formatMoney(item.value)} · {formatPercent(item.share_percent)}
                      </span>
                    </div>
                    <div className="bar" aria-hidden="true">
                      <div className="bar-fill" style={{ width: `${item.share_percent ?? "0"}%` }} />
                    </div>
                  </div>
                ))
              ) : (
                <p className="muted">Структура портфеля недоступна.</p>
              )}
            </div>
          </div>

          <PositionsTable positions={dashboard.positions_preview} />
        </section>

        {dashboard.warnings.length > 0 ? (
          <section className="panel" style={{ marginTop: 16 }}>
            <h2 className="section-title">Предупреждения</h2>
            <ul className="warning-list" style={{ marginTop: 14 }}>
              {dashboard.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
    </div>
  );
}

function PositionsTable({ positions }: { positions: DemoDashboard["positions_preview"] }) {
  return (
    <div className="table-panel">
      <div className="table-header">
        <div>
          <h2 className="section-title">Позиции</h2>
          <p className="section-caption">Top preview из demo portfolio</p>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Инструмент</th>
            <th>Количество</th>
            <th>Цена</th>
            <th>Стоимость</th>
          </tr>
        </thead>
        <tbody>
          {positions.length > 0 ? (
            positions.map((position) => (
              <tr key={position.instrument_uid}>
                <td>
                  <span className="instrument">
                    <strong>{position.instrument_name}</strong>
                    <span className="ticker">{position.ticker}</span>
                  </span>
                </td>
                <td>{position.quantity}</td>
                <td>{position.current_price ? formatMoney(position.current_price) : "нет данных"}</td>
                <td>{position.market_value ? formatMoney(position.market_value) : "нет данных"}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td className="muted" colSpan={4}>
                Позиции не найдены.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function instrumentTypeLabel(type: string) {
  const labels: Record<string, string> = {
    bond: "Облигации",
    share: "Акции"
  };
  return labels[type] ?? type;
}
