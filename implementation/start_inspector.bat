@echo off
REM Start MCP Inspector for the SQLite Lab server
REM This script launches the MCP Inspector connected to our FastMCP server.

echo ============================================
echo   MCP Inspector - SQLite Lab Server
echo ============================================
echo.

set SCRIPT_DIR=%~dp0
set SERVER_PATH=%SCRIPT_DIR%mcp_server.py

REM Find Python path
for /f "tokens=*" %%i in ('where python') do (
    set PYTHON_PATH=%%i
    goto :found
)

:found
echo Python: %PYTHON_PATH%
echo Server: %SERVER_PATH%
echo.

if not exist ".npm-cache" mkdir .npm-cache
set NPM_CONFIG_CACHE=%SCRIPT_DIR%.npm-cache
npx -y @modelcontextprotocol/inspector "%PYTHON_PATH%" "%SERVER_PATH%"
