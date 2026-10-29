import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  server: { host: "127.0.0.1", proxy: { "/api": "http://127.0.0.1:8080" } },
  plugins: [react(), tailwindcss(), tsconfigPaths()],
});
