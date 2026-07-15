import {
  LayoutDashboard,
  GitBranch,
  ShieldCheck,
  Boxes,
  Cloud,
  Bot,
  Settings,
} from "lucide-react";

const menu = [
  { name: "Dashboard", icon: LayoutDashboard },
  { name: "Repositories", icon: GitBranch },
  { name: "Security", icon: ShieldCheck },
  { name: "Kubernetes", icon: Boxes },
  { name: "CloudWatch", icon: Cloud },
  { name: "AI Agents", icon: Bot },
  { name: "Settings", icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-72 bg-slate-900 border-r border-slate-800 h-screen">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-blue-500">
          AegisOps AI
        </h1>
      </div>

      <nav className="px-4">
        {menu.map((item) => (
          <div
            key={item.name}
            className="flex items-center gap-3 rounded-lg p-3 text-slate-300 hover:bg-slate-800 hover:text-white cursor-pointer transition"
          >
            <item.icon size={20} />
            <span>{item.name}</span>
          </div>
        ))}
      </nav>
    </aside>
  );
}