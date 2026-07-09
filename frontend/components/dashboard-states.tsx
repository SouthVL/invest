export function DashboardSkeleton() {
  return (
    <main className="page">
      <div className="shell">
        <div className="topbar">
          <div className="brand">
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-line" style={{ width: 220, marginTop: 8 }} />
          </div>
        </div>
        <section className="hero">
          <div className="panel">
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-line" style={{ width: "65%", height: 44, marginTop: 24 }} />
          </div>
          <div className="panel">
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-line" style={{ width: "85%", marginTop: 24 }} />
          </div>
        </section>
      </div>
    </main>
  );
}

export function DashboardError({ onRetry }: { onRetry: () => void }) {
  return (
    <main className="state-page">
      <section className="state-panel">
        <h1 className="section-title">Dashboard недоступен</h1>
        <p className="muted">Не удалось получить demo данные из backend API.</p>
        <button className="retry-button" type="button" onClick={onRetry}>
          Повторить
        </button>
      </section>
    </main>
  );
}
