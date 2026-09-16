import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "./",
  server: {
    // Mirrors the vercel.json rewrites so `vite dev` serves live registry data.
    proxy: {
      "^/hooklist(-vanilla-swap)?\\.json$": {
        target: "https://raw.githubusercontent.com/Uniswap/hooklist/main",
        changeOrigin: true,
      },
    },
  },
});
