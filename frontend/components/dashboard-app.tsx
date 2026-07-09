"use client";

import { FormEvent, useState } from "react";

import { Dashboard } from "@/components/dashboard";
import { connectSession, disconnectSession, getRealDashboard, selectAccount } from "@/lib/api";
import type { ConnectedAccount, DashboardData } from "@/lib/types";

export function DashboardApp({ initialDashboard }: { initialDashboard: DashboardData }) {
  const [dashboard, setDashboard] = useState(initialDashboard);
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [token, setToken] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConnect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submittedToken = token.trim();
    setToken("");
    if (!submittedToken) {
      setError("Введите read-only token.");
      return;
    }

    setIsBusy(true);
    setError(null);
    try {
      const connection = await connectSession(submittedToken);
      setAccounts(connection.accounts);
      setDashboard(await getRealDashboard());
    } catch {
      setError("Не удалось подключить T-Invest.");
      setDashboard(initialDashboard);
      setAccounts([]);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleSelectAccount(accountRef: string) {
    setIsBusy(true);
    setError(null);
    try {
      const result = await selectAccount(accountRef);
      setAccounts(result.accounts);
      setDashboard(await getRealDashboard());
    } catch {
      setError("Не удалось выбрать счёт.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRefresh() {
    if (dashboard.mode !== "real") {
      return;
    }
    setIsBusy(true);
    setError(null);
    try {
      setDashboard(await getRealDashboard());
    } catch {
      setError("Не удалось обновить данные.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleDisconnect() {
    setIsBusy(true);
    setError(null);
    try {
      await disconnectSession();
    } catch {
      setError("Сессия сброшена локально.");
    } finally {
      setDashboard(initialDashboard);
      setAccounts([]);
      setIsBusy(false);
    }
  }

  return (
    <Dashboard
      dashboard={dashboard}
      onRefresh={dashboard.mode === "real" ? handleRefresh : undefined}
      sessionPanel={
        <SessionPanel
          accounts={accounts}
          dashboardMode={dashboard.mode}
          error={error}
          isBusy={isBusy}
          token={token}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onSelectAccount={handleSelectAccount}
          onTokenChange={setToken}
        />
      }
    />
  );
}

function SessionPanel({
  accounts,
  dashboardMode,
  error,
  isBusy,
  token,
  onConnect,
  onDisconnect,
  onSelectAccount,
  onTokenChange
}: {
  accounts: ConnectedAccount[];
  dashboardMode: DashboardData["mode"];
  error: string | null;
  isBusy: boolean;
  token: string;
  onConnect: (event: FormEvent<HTMLFormElement>) => void;
  onDisconnect: () => void;
  onSelectAccount: (accountRef: string) => void;
  onTokenChange: (value: string) => void;
}) {
  return (
    <div className="session-panel">
      <span className="connection-pill" data-mode={dashboardMode}>
        {dashboardMode === "real" ? "Real API" : "Demo"}
      </span>

      {dashboardMode === "real" ? (
        <>
          <div className="account-list">
            {accounts.map((account) => (
              <button
                className="account-option"
                data-active={account.selected ? "true" : undefined}
                disabled={isBusy || account.selected}
                key={account.ref}
                type="button"
                onClick={() => onSelectAccount(account.ref)}
              >
                <strong>{account.name}</strong>
                <span>{account.masked_id}</span>
              </button>
            ))}
          </div>
          <button className="disconnect-button" disabled={isBusy} type="button" onClick={onDisconnect}>
            Отключить
          </button>
        </>
      ) : (
        <form className="token-form" onSubmit={onConnect}>
          <label htmlFor="tinvest-token">T-Invest token</label>
          <input
            autoComplete="off"
            disabled={isBusy}
            id="tinvest-token"
            name="token"
            type="password"
            value={token}
            onChange={(event) => onTokenChange(event.target.value)}
          />
          <button disabled={isBusy} type="submit">
            Подключить
          </button>
        </form>
      )}

      {error ? <p className="session-error">{error}</p> : null}
    </div>
  );
}
