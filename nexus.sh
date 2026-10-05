#!/usr/bin/env bash
set -euo pipefail

# Nexus AI service manager. The script is location-independent.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$PROJECT_ROOT/ecosystem.config.js"

usage() {
  echo "Usage: $0 {start|stop|restart|status|logs|build}"
}

case "${1:-}" in
  start)
    pm2 start "$CONFIG" --update-env
    ;;
  stop)
    pm2 stop "$CONFIG"
    ;;
  restart)
    pm2 restart "$CONFIG" --update-env
    ;;
  status)
    pm2 status
    ;;
  logs)
    pm2 logs nexus-backend --lines 100
    ;;
  build)
    (cd "$PROJECT_ROOT/frontend" && npm run build)
    ;;
  *)
    usage
    exit 1
    ;;
esac
