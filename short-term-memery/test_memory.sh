#!/usr/bin/env bash
set -euo pipefail

URL="http://localhost:8080/invocations"
SESS="sess-123456789012345678901234567890123"
ACTOR="wanderbot-user"

echo "=== Turn 1: 'I need a hotel in Paris' ==="
curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: $SESS" \
  -d "{\"message\": \"I need a hotel in Paris\", \"actor_id\": \"$ACTOR\"}"
echo
echo

echo "=== Turn 2: 'What city did I mention?' (should recall Paris) ==="
curl -s -X POST "$URL" \
  -H "Content-Type: application/json" \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: $SESS" \
  -d "{\"message\": \"What city did I mention?\", \"actor_id\": \"$ACTOR\"}"
echo
