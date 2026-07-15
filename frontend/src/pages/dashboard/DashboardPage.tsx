import MainLayout from "../../components/layout/MainLayout";
import DashboardGrid from "../../components/dashboard/DashboardGrid";

export default function DashboardPage() {
  return (
    <MainLayout>
      <div className="space-y-8">
        <div>
          <h1 className="text-4xl font-bold text-white">
            Dashboard
          </h1>

          <p className="mt-2 text-slate-400">
            Welcome to AegisOps AI DevSecOps Platform
          </p>
        </div>

        <DashboardGrid />
      </div>
    </MainLayout>
  );
}