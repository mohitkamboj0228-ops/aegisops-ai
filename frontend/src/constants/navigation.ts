import {
  LayoutDashboard,
  FolderGit2,
  GitBranch,
  Shield,
  Boxes,
  Cloud,
  Bot,
  Settings,
} from "lucide-react";

export const navigation = [
  {
    title: "Dashboard",
    path: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "Repositories",
    path: "/repositories",
    icon: FolderGit2,
  },
  {
    title: "Pipelines",
    path: "/pipelines",
    icon: GitBranch,
  },
  {
    title: "Security",
    path: "/security",
    icon: Shield,
  },
  {
    title: "Kubernetes",
    path: "/kubernetes",
    icon: Boxes,
  },
  {
    title: "CloudWatch",
    path: "/monitoring",
    icon: Cloud,
  },
  {
    title: "AI Agents",
    path: "/ai",
    icon: Bot,
  },
  {
    title: "Settings",
    path: "/settings",
    icon: Settings,
  },
];