import { Card, CardContent } from "../ui/card";
import type { LucideIcon } from "lucide-react";
interface StatCardProps {
  title: string;
  value: string;
  icon: LucideIcon;
  color?: string;
}

export default function StatCard({
  title,
  value,
  icon: Icon,
  color = "text-blue-500",
}: StatCardProps) {
  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardContent className="flex items-center justify-between p-6">
        <div>
          <p className="text-sm text-slate-400">{title}</p>
          <h2 className="mt-2 text-3xl font-bold text-white">{value}</h2>
        </div>

        <div className={`rounded-xl bg-slate-800 p-4 ${color}`}>
          <Icon size={28} />
        </div>
      </CardContent>
    </Card>
  );
}