import { DashboardApp } from "@/components/dashboard-app";
import { getCurrentMacro, getDemoDashboard } from "@/lib/api";
import { applyMacroSnapshot } from "@/lib/macro";

export default async function Home() {
  const [dashboardResult, macroResult] = await Promise.allSettled([getDemoDashboard(), getCurrentMacro()]);
  if (dashboardResult.status === "rejected") {
    throw dashboardResult.reason;
  }
  const dashboard = macroResult.status === "fulfilled" ? applyMacroSnapshot(dashboardResult.value, macroResult.value) : dashboardResult.value;

  return <DashboardApp initialDashboard={dashboard} />;
}
