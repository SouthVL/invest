import { DashboardApp } from "@/components/dashboard-app";
import { getDemoDashboard } from "@/lib/api";

export default async function Home() {
  const dashboard = await getDemoDashboard();

  return <DashboardApp initialDashboard={dashboard} />;
}
