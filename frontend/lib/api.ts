import type { DemoDashboard } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function getDemoDashboard(): Promise<DemoDashboard> {
  const response = await fetch(`${API_BASE_URL}/api/v1/demo/dashboard`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Demo dashboard request failed with status ${response.status}`);
  }

  return (await response.json()) as DemoDashboard;
}
