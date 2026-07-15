import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function GitHubButton() {
  return (
    <Button
      variant="outline"
      className="w-full h-11 bg-slate-900 border-slate-700 hover:bg-slate-800"
    >
      <LogIn className="mr-2 h-5 w-5" />
      Continue with GitHub
    </Button>
  );
}