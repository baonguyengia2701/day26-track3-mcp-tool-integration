#!/usr/bin/env bash
# Start MCP Inspector for the SQLite Lab server

echo "============================================"
echo "  MCP Inspector - SQLite Lab Server"
echo "============================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_PATH="$SCRIPT_DIR/mcp_server.py"
PYTHON_PATH="$(which python3 || which python)"

echo "Python: $PYTHON_PATH"
echo "Server: $SERVER_PATH"
echo ""

mkdir -p "$SCRIPT_DIR/.npm-cache"
NPM_CONFIG_CACHE="$SCRIPT_DIR/.npm-cache" npx -y @modelcontextprotocol/inspector "$PYTHON_PATH" "$SERVER_PATH"
