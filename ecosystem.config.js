const os = require("node:os");
const path = require("node:path");

const projectRoot = __dirname;
const backendRoot = path.join(projectRoot, "backend");
const frontendRoot = path.join(projectRoot, "frontend");
const backendPort = process.env.NEXUS_PORT || "8000";
const frontendPort = process.env.FRONTEND_PORT || "5008";
const omniroutePort = process.env.OMNIROUTE_PORT || "20128";
const omnirouteHome =
  process.env.OMNIROUTE_HOME ||
  path.join(os.homedir(), ".local", "share", "nexus-ai", "omniroute");
const omnirouteEntry =
  process.env.OMNIROUTE_ENTRY ||
  path.join(omnirouteHome, "node_modules", "omniroute", "bin", "omniroute.mjs");

module.exports = {
  apps: [
    {
      name: "nexus-omniroute",
      script: "node",
      args: [
        omnirouteEntry,
        "serve",
        "--no-open",
        "--no-tray",
        "--port",
        omniroutePort,
      ],
      cwd: projectRoot,
      interpreter: "none",
      env: {
        OMNIROUTE_SERVER_HOST: "127.0.0.1",
      },
    },
    {
      name: "nexus-backend",
      script: "python3",
      args: `-m uvicorn main:app --host 0.0.0.0 --port ${backendPort}`,
      cwd: backendRoot,
      interpreter: "none",
      env: {
        PYTHONPATH: ".",
        NEXUS_ENV: "production",
        DEFAULT_AI_PROVIDER: process.env.DEFAULT_AI_PROVIDER || "omniroute",
        OMNIROUTE_URL:
          process.env.OMNIROUTE_URL || `http://127.0.0.1:${omniroutePort}/v1`,
        OMNIROUTE_MODEL: process.env.OMNIROUTE_MODEL || "auto",
      },
    },
    {
      name: "nexus-frontend",
      script: "npm",
      args: `run start -- --hostname 0.0.0.0 --port ${frontendPort}`,
      cwd: frontendRoot,
      interpreter: "none",
      env: {
        NODE_ENV: "production",
        BACKEND_URL: `http://127.0.0.1:${backendPort}`,
      },
    },
  ],
};
