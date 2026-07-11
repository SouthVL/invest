"use client";

import { FormEvent, useEffect, useState } from "react";

import { Dashboard } from "@/components/dashboard";
import { connectSession, disconnectSession, getCurrentMacro, getRealDashboard, getSessionStatus, selectAccount } from "@/lib/api";
import { applyMacroSnapshot } from "@/lib/macro";
import type { ConnectedAccount, DashboardData, SessionStatusResponse } from "@/lib/types";

type SessionNotice = {
  tone: "info" | "warning";
  message: string;
} | null;

export function DashboardApp({ initialDashboard }: { initialDashboard: DashboardData }) {
  const [dashboard, setDashboard] = useState(initialDashboard);
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [token, setToken] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionNotice, setSessionNotice] = useState<SessionNotice>(null);

  useEffect(() => {
    let isActive = true;

    async function restoreSession() {
      try {
        const session = await getSessionStatus();
        if (session.session.status !== "connected") {
          const dashboardWithMacro = await withCurrentMacro(initialDashboard);
          if (isActive) {
            setDashboard(dashboardWithMacro);
            setAccounts([]);
            setSessionNotice(sessionNoticeForStatus(session.session.status));
          }
          return;
        }
        const restoredDashboard = await getRealDashboardWithMacro();
        if (!isActive) {
          return;
        }
        setAccounts(session.accounts);
        setDashboard(restoredDashboard);
        setSessionNotice(null);
      } catch {
        if (isActive) {
          setDashboard(await withCurrentMacro(initialDashboard));
          setAccounts([]);
        }
      }
    }

    void restoreSession();

    return () => {
      isActive = false;
    };
  }, [initialDashboard]);

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
    setSessionNotice(null);
    try {
      const connection = await connectSession(submittedToken);
      setAccounts(connection.accounts);
      setDashboard(await getRealDashboardWithMacro());
      setSessionNotice(null);
    } catch {
      setError("Не удалось подключить T-Invest.");
      setDashboard(await withCurrentMacro(initialDashboard));
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
      setDashboard(await getRealDashboardWithMacro());
    } catch {
      const handled = await handleSessionLoss();
      if (!handled) {
        setError("Не удалось выбрать счёт.");
      }
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRefresh() {
    if (dashboard.mode !== "real") {
      return;
    }
    setIsRefreshing(true);
    setError(null);
    try {
      setDashboard(await getRealDashboardWithMacro());
    } catch {
      const handled = await handleSessionLoss();
      if (!handled) {
        setError("Не удалось обновить данные.");
      }
    } finally {
      setIsRefreshing(false);
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
      setDashboard(await withCurrentMacro(initialDashboard));
      setAccounts([]);
      setSessionNotice(null);
      setIsBusy(false);
    }
  }

  async function handleSessionLoss(): Promise<boolean> {
    try {
      const session = await getSessionStatus();
      if (session.session.status === "connected") {
        return false;
      }
      setDashboard(await withCurrentMacro(initialDashboard));
      setAccounts([]);
      setSessionNotice(sessionNoticeForStatus(session.session.status));
      return true;
    } catch {
      return false;
    }
  }

  return (
    <Dashboard
      dashboard={dashboard}
      isRefreshing={isRefreshing}
      onRefresh={dashboard.mode === "real" ? handleRefresh : undefined}
      sessionPanel={
        <SessionPanel
          accounts={accounts}
          dashboardMode={dashboard.mode}
          error={error}
          isBusy={isBusy || isRefreshing}
          sessionNotice={sessionNotice}
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

async function getRealDashboardWithMacro(): Promise<DashboardData> {
  const [dashboardResult, macroResult] = await Promise.allSettled([getRealDashboard(), getCurrentMacro()]);
  if (dashboardResult.status === "rejected") {
    throw dashboardResult.reason;
  }
  if (macroResult.status === "fulfilled") {
    return applyMacroSnapshot(dashboardResult.value, macroResult.value);
  }
  return dashboardResult.value;
}

async function withCurrentMacro(dashboard: DashboardData): Promise<DashboardData> {
  try {
    return applyMacroSnapshot(dashboard, await getCurrentMacro());
  } catch {
    return dashboard;
  }
}

function SessionPanel({
  accounts,
  dashboardMode,
  error,
  isBusy,
  sessionNotice,
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
  sessionNotice: SessionNotice;
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

      {sessionNotice ? (
        <p className="session-notice" data-tone={sessionNotice.tone} role="status">
          {sessionNotice.message}
        </p>
      ) : null}

      {dashboardMode === "real" ? (
        <>
          <div className="account-select-field">
            <label htmlFor="account-selector">Счёт</label>
            <select
              disabled={isBusy || accounts.length === 0}
              id="account-selector"
              value={accounts.find((account) => account.selected)?.ref ?? ""}
              onChange={(event) => {
                if (event.target.value) {
                  onSelectAccount(event.target.value);
                }
              }}
            >
              {accounts.map((account) => (
                <option key={account.ref} value={account.ref}>
                  {account.name} · {account.masked_id}
                </option>
              ))}
            </select>
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

function sessionNoticeForStatus(status: SessionStatusResponse["session"]["status"]): SessionNotice {
  if (status === "expired") {
    return {
      tone: "warning",
      message: "Сессия истекла. Подключите read-only token заново."
    };
  }
  if (status === "missing") {
    return {
      tone: "info",
      message: "Нет активной сессии. Подключите read-only token, чтобы увидеть реальные данные."
    };
  }
  return null;
}
