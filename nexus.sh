#!/usr/bin/env bash
set -euo pipefail

# Nexus AI service manager. The script is location-independent.
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$PROJECT_ROOT/ecosystem.config.js"
OMNIROUTE_HOME="${OMNIROUTE_HOME:-$HOME/.local/share/nexus-ai/omniroute}"
OMNIROUTE_ENTRY="${OMNIROUTE_ENTRY:-$OMNIROUTE_HOME/node_modules/omniroute/bin/omniroute.mjs}"
OMNIROUTE_VERSION="${OMNIROUTE_VERSION:-3.8.51}"

usage() {
  echo "Usage: $0 {setup-omniroute|start|stop|restart|status|logs|build}"
}

require_omniroute() {
  if [[ ! -f "$OMNIROUTE_ENTRY" ]]; then
    echo "OmniRoute is not installed at $OMNIROUTE_ENTRY" >&2
    echo "Run: $0 setup-omniroute" >&2
    exit 1
  fi
  export OMNIROUTE_HOME OMNIROUTE_ENTRY
}

case "${1:-}" in
  setup-omniroute)
    mkdir -p "$OMNIROUTE_HOME"
    npm install --prefix "$OMNIROUTE_HOME" --no-fund --no-audit "omniroute@$OMNIROUTE_VERSION"
    echo "OmniRoute $OMNIROUTE_VERSION installed at $OMNIROUTE_HOME"
    ;;
  start)
    require_omniroute
    pm2 start "$CONFIG" --update-env
    ;;
  stop)
    pm2 stop "$CONFIG"
    ;;
  restart)
    require_omniroute
    pm2 restart "$CONFIG" --update-env
    ;;
  status)
    pm2 status
    ;;
  logs)
    pm2 logs --lines 100
    ;;
  build)
    (cd "$PROJECT_ROOT/frontend" && npm run build)
    ;;
  *)
    usage
    exit 1
    ;;
esac
