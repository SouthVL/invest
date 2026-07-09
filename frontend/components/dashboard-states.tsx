export function DashboardSkeleton() {
  return (
    <main className="dashboard-page">
      <aside className="dashboard-sidebar">
        <div className="sidebar-brand">
          <div className="skeleton" style={{ width: 40, height: 40, borderRadius: 10 }} />
          <div>
            <div className="skeleton skeleton-line" style={{ width: 108 }} />
            <div className="skeleton skeleton-line" style={{ width: 58, marginTop: 8 }} />
          </div>
        </div>
      </aside>
      <section className="dashboard-content">
        <div className="dashboard-header">
          <div style={{ width: "100%" }}>
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-line" style={{ width: 180, marginTop: 10 }} />
          </div>
        </div>
        <section className="summary-grid">
          <div className="dashboard-card portfolio-summary">
            <div className="skeleton skeleton-line" style={{ width: 150 }} />
            <div className="skeleton skeleton-line" style={{ width: "46%", height: 52, marginTop: 24 }} />
            <div className="skeleton skeleton-line" style={{ width: 220, marginTop: 12 }} />
          </div>
          <div className="dashboard-card benchmark-card">
            <div className="skeleton skeleton-line" style={{ width: 190 }} />
            <div className="skeleton skeleton-line" style={{ width: 82, height: 36, marginTop: 24 }} />
          </div>
        </section>
      </section>
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
