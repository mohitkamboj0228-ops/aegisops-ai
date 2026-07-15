import {
  FolderGit2,
  Rocket,
  ShieldCheck,
  Bot,
} from "lucide-react";

import StatCard from "./StatCard";

export default function DashboardGrid() {
  return (
    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
      <StatCard
        title="Repositories"
        value="12"
        icon={FolderGit2}
      />

      <StatCard
        title="Deployments"
        value="18"
        icon={Rocket}
        color="text-green-500"
      />

      <StatCard
        title="Security Score"
        value="96%"
        icon={ShieldCheck}
        color="text-yellow-500"
      />

      <StatCard
        title="AI Agents"
        value="4"
        icon={Bot}
        color="text-purple-500"
      />
    </div>
  );
}