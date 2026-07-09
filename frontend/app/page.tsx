import { Dashboard } from "@/components/dashboard";
import { getDemoDashboard } from "@/lib/api";

export default async function Home() {
  const dashboard = await getDemoDashboard();

  return <Dashboard dashboard={dashboard} />;
}
