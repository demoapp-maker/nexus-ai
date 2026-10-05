const path = require("node:path");

const projectRoot = __dirname;
const backendRoot = path.join(projectRoot, "backend");
const frontendRoot = path.join(projectRoot, "frontend");
const backendPort = process.env.NEXUS_PORT || "8000";
const frontendPort = process.env.FRONTEND_PORT || "5008";

module.exports = {
  apps: [
    {
      name: "nexus-backend",
      script: "python3",
      args: `-m uvicorn main:app --host 0.0.0.0 --port ${backendPort}`,
      cwd: backendRoot,
      interpreter: "none",
      env: {
        PYTHONPATH: ".",
        NEXUS_ENV: "production",
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
