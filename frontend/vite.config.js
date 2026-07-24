import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const here = fileURLToPath(new URL(".", import.meta.url));
const repo = fileURLToPath(new URL("../", import.meta.url));
const API_PORT = 3000;

// Runs the Flask API as a child of the dev server so `npm run dev` is the only
// command. Tied to vite's lifecycle: it dies when vite does.
function flaskApi() {
  return {
    name: "flask-api",
    apply: "serve", // never spawn during `vite build`
    configureServer() {
      const venv = `${repo}.venv/bin/python`;
      const python = existsSync(venv) ? venv : "python3";
      const flask = spawn(python, [`${repo}api_server.py`], {
        stdio: "inherit",
        // PORT is set explicitly: api_server.py reads it, and an inherited PORT
        // (from a parent dev runner) would otherwise send Flask to the wrong one.
        env: { ...process.env, PORT: String(API_PORT) },
      });

      flask.on("error", (e) =>
        console.error(`\n[flask] could not start: ${e.message}\n`),
      );
      flask.on("exit", (code) => {
        if (code) console.error(`\n[flask] exited with code ${code}\n`);
      });

      const stop = () => flask.kill();
      process.on("exit", stop);
      for (const signal of ["SIGINT", "SIGTERM"]) {
        process.on(signal, () => {
          stop();
          process.exit(0);
        });
      }
    },
  };
}

// root stays the default (this directory) — index.html lives here, not in src/.
export default defineConfig({
  root: here,
  plugins: [react(), flaskApi()],
  server: {
    proxy: {
      "/api": `http://localhost:${API_PORT}`,
    },
  },
});
