import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import GitHubButton from "./GitHubButton";

export default function LoginForm() {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-white">🛡️ AegisOps AI</h1>

        <p className="mt-2 text-slate-400">
          AI Powered DevSecOps Platform
        </p>
      </div>

      <div className="space-y-5">

        <div>
          <label className="mb-2 block text-sm text-slate-300">
            Email
          </label>

          <Input
            type="email"
            placeholder="mohit@example.com"
          />
        </div>

        <div>

          <label className="mb-2 block text-sm text-slate-300">
            Password
          </label>

          <div className="relative">

            <Input
              type={showPassword ? "text" : "password"}
              placeholder="********"
            />

            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-3 text-slate-400"
            >
              {showPassword ? <EyeOff size={18}/> : <Eye size={18}/>}
            </button>

          </div>

        </div>

        <div className="flex items-center justify-between">

          <div className="flex items-center gap-2">

            <Checkbox />

            <span className="text-sm text-slate-400">
              Remember me
            </span>

          </div>

          <button
            className="text-sm text-blue-400 hover:text-blue-300"
          >
            Forgot password?
          </button>

        </div>

        <Button className="w-full h-11">
          Sign In
        </Button>

        <div className="relative py-2">

          <div className="border-t border-slate-700"></div>

          <span className="absolute left-1/2 top-0 -translate-x-1/2 bg-slate-900 px-3 text-sm text-slate-500">
            OR
          </span>

        </div>

        <GitHubButton />

      </div>

    </div>
  );
}