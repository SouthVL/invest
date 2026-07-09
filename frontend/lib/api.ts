import type { AccountsResponse, ConnectResponse, DashboardData } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function getDemoDashboard(): Promise<DashboardData> {
  const response = await fetch(`${API_BASE_URL}/api/v1/demo/dashboard`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Demo dashboard request failed with status ${response.status}`);
  }

  return (await response.json()) as DashboardData;
}

export async function connectSession(token: string): Promise<ConnectResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/session/connect`, {
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
  const response = await fetch(`${API_BASE_URL}/api/v1/accounts/select`, {
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

export async function getRealDashboard(): Promise<DashboardData> {
  const response = await fetch(`${API_BASE_URL}/api/v1/portfolio/dashboard`, {
    credentials: "include",
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Real dashboard request failed with status ${response.status}`);
  }

  return (await response.json()) as DashboardData;
}

export async function disconnectSession(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/session/disconnect`, {
    method: "POST",
    credentials: "include"
  });

  if (!response.ok) {
    throw new Error(`Disconnect failed with status ${response.status}`);
  }
}
