#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

printf 'Checking Nexus AI at %s\n' "$BASE_URL"
curl --fail --silent --show-error "$BASE_URL/health" | python3 -m json.tool

regular_response=$(curl --fail --silent --show-error -X POST "$BASE_URL/chat" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Hello, how are you?","session_id":"smoke-direct"}')
python3 -c 'import json,sys; data=json.loads(sys.stdin.read()); assert data["response"]' <<<"$regular_response"
printf 'Regular chat: OK\n'

stream_response=$(curl --fail --silent --show-error -N -X POST "$BASE_URL/chat/tools" \
  -H 'Content-Type: application/json' \
  -d '{"message":"What is the latest news about AI?","session_id":"smoke-tools","model":"openrouter/free"}')
grep -q 'data: \[DONE\]' <<<"$stream_response"
grep -q '"type": "info"' <<<"$stream_response"
printf 'Streaming chat: OK\n'

research_response=$(curl --fail --silent --show-error -X POST "$BASE_URL/research/autonomous" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Research the benefits of renewable energy","session_id":"smoke-research"}')
python3 -c 'import json,sys; data=json.loads(sys.stdin.read()); assert data["query"]; assert "final_report" in data' <<<"$research_response"
printf 'Autonomous research: OK\n'

planning_response=$(curl --fail --silent --show-error -X POST "$BASE_URL/planning/task" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Create a plan to build a web scraping application","session_id":"smoke-planning"}')
python3 -c 'import json,sys; data=json.loads(sys.stdin.read()); assert isinstance(data,dict)' <<<"$planning_response"
printf 'Task planning: OK\n'
