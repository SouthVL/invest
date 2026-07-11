import type {
  AccountsResponse,
  ConnectResponse,
  CurrentMacroResponse,
  DashboardData,
  IncomeFilterStatus,
  IncomeFilterType,
  IncomePeriod,
  IncomeResponse,
  PortfolioPositionsResponse,
  SessionStatusResponse
} from "@/lib/types";

const PUBLIC_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const SERVER_API_BASE_URL = process.env.INTERNAL_API_BASE_URL ?? PUBLIC_API_BASE_URL;

function apiBaseUrl(): string {
  return typeof window === "undefined" ? SERVER_API_BASE_URL : PUBLIC_API_BASE_URL;
}

export async function getDemoDashboard(): Promise<DashboardData> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/demo/dashboard`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Demo dashboard request failed with status ${response.status}`);
  }

  return (await response.json()) as DashboardData;
}

export async function connectSession(token: string): Promise<ConnectResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/session/connect`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ token })
  });

  if (!response.ok) {
    throw new Error(`T-Invest connection failed with status ${response.status}`);
  }

  return (await response.json()) as ConnectResponse;
}

export async function selectAccount(accountRef: string): Promise<AccountsResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/accounts/select`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ account_ref: accountRef })
  });

  if (!response.ok) {
    throw new Error(`Account selection failed with status ${response.status}`);
  }

  return (await response.json()) as AccountsResponse;
}

export async function getAccounts(): Promise<AccountsResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/accounts`, {
    credentials: "include",
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Accounts request failed with status ${response.status}`);
  }

  return (await response.json()) as AccountsResponse;
}

export async function getSessionStatus(): Promise<SessionStatusResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/session/status`, {
    credentials: "include",
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Session status request failed with status ${response.status}`);
  }

  return (await response.json()) as SessionStatusResponse;
}

export async function getRealDashboard(): Promise<DashboardData> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/portfolio/dashboard`, {
    credentials: "include",
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Real dashboard request failed with status ${response.status}`);
  }

  return (await response.json()) as DashboardData;
}

export async function getPortfolioPositions(): Promise<PortfolioPositionsResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/portfolio/positions`, {
    credentials: "include",
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Portfolio positions request failed with status ${response.status}`);
  }

  return (await response.json()) as PortfolioPositionsResponse;
}

export async function getIncome({
  period = "3m",
  type = "all",
  status = "all"
}: {
  period?: IncomePeriod;
  type?: IncomeFilterType;
  status?: IncomeFilterStatus;
} = {}): Promise<IncomeResponse> {
  const params = new URLSearchParams({ period, type, status });
  const response = await fetch(`${apiBaseUrl()}/api/v1/income?${params.toString()}`, {
    credentials: "include",
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Income request failed with status ${response.status}`);
  }

  return (await response.json()) as IncomeResponse;
}

export async function getCurrentMacro(): Promise<CurrentMacroResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/macro/current`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Current macro request failed with status ${response.status}`);
  }

  return (await response.json()) as CurrentMacroResponse;
}

export async function disconnectSession(): Promise<void> {
  const response = await fetch(`${apiBaseUrl()}/api/v1/session/disconnect`, {
    method: "POST",
    credentials: "include"
  });

  if (!response.ok) {
    throw new Error(`Disconnect failed with status ${response.status}`);
  }
}
