# Database MCP Server - FastMCP + SQLite Lab

A **Model Context Protocol (MCP)** server built with [FastMCP](https://gofastmcp.com) that exposes a university SQLite database through standardized AI tool interfaces.

## Features

| Tool | Description |
|------|-------------|
| `search` | Query rows with filters, column selection, ordering, and pagination |
| `insert` | Add new records with full validation |
| `aggregate` | Run `COUNT`, `AVG`, `SUM`, `MIN`, `MAX` with optional `GROUP BY` |

| Resource | URI | Description |
|----------|-----|-------------|
| Full Schema | `schema://database` | Complete database structure (all tables) |
| Table Schema | `schema://table/{table_name}` | Schema for a specific table |

### Safety & Validation
- ✅ Whitelist-based table and column name validation
- ✅ Parameterized SQL queries (no string concatenation)
- ✅ Operator validation against supported set
- ✅ Metric validation for aggregate functions
- ✅ Clear error messages for all invalid inputs

## Project Structure

```
implementation/
├── db.py                 # SQLiteAdapter - database logic with validation
├── init_db.py            # Schema definition and seed data
├── mcp_server.py         # FastMCP server with tools and resources
├── verify_server.py      # Interactive verification script
├── start_inspector.bat   # Launch MCP Inspector (Windows)
├── start_inspector.sh    # Launch MCP Inspector (Linux/macOS)
├── lab.db                # SQLite database (auto-generated)
└── tests/
    └── test_server.py    # Automated test suite (35 tests)
```

## Data Model

```
students                  courses                   enrollments
├── id (PK)               ├── id (PK)               ├── id (PK)
├── name                  ├── code (UNIQUE)         ├── student_id (FK)
├── email (UNIQUE)        ├── title                 ├── course_id (FK)
├── cohort                ├── credits               ├── semester
└── gpa                   └── department            ├── score
                                                    └── grade
```

## Quick Start

### 1. Install Dependencies

```bash
pip install fastmcp
```

### 2. Initialize the Database

```bash
cd implementation
python init_db.py
```

### 3. Run Verification

```bash
python verify_server.py
```

### 4. Run Tests

```bash
python -m pytest tests/test_server.py -v
```

### 5. Start the MCP Server

```bash
python mcp_server.py
```

## MCP Inspector

Test the server interactively with MCP Inspector:

**Windows:**
```bash
cd implementation
start_inspector.bat
```

**Linux/macOS:**
```bash
cd implementation
chmod +x start_inspector.sh
./start_inspector.sh
```

**Manual:**
```bash
npx -y @modelcontextprotocol/inspector python /ABSOLUTE/PATH/TO/implementation/mcp_server.py
```

Then open `http://localhost:5173` in your browser.

### Inspector Checklist
- [ ] 3 tools appear with schemas (search, insert, aggregate)
- [ ] 2 resources appear (schema://database, schema://table/{table_name})
- [ ] Valid tool calls succeed and return data
- [ ] Invalid tool calls return clear error messages

## Client Configuration

### Gemini CLI

```bash
gemini mcp add sqlite-lab /ABSOLUTE/PATH/TO/python /ABSOLUTE/PATH/TO/implementation/mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
gemini mcp list
```

Verify:
```bash
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Use the sqlite-lab MCP server and show me the top 3 students by GPA."
```

### Claude Code

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "python",
      "args": ["/ABSOLUTE/PATH/TO/implementation/mcp_server.py"],
      "env": {}
    }
  }
}
```

### Codex

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.sqlite_lab]
command = "python"
args = ["/ABSOLUTE/PATH/TO/implementation/mcp_server.py"]
```

### Antigravity

Create `mcp_config.json`:

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "command": "python",
      "args": ["/ABSOLUTE/PATH/TO/implementation/mcp_server.py"],
      "cwd": "/ABSOLUTE/PATH/TO/implementation"
    }
  }
}
```

## Example Demonstrations

### Search - All students in cohort A1
```json
{
  "table": "students",
  "filters": [{"column": "cohort", "operator": "=", "value": "A1"}]
}
```

### Search - Top 5 students by GPA
```json
{
  "table": "students",
  "order_by": "gpa",
  "descending": true,
  "limit": 5
}
```

### Insert - New student
```json
{
  "table": "students",
  "values": {
    "name": "Tran Van Linh",
    "email": "linh.tran@university.edu",
    "cohort": "A1",
    "gpa": 3.7
  }
}
```

### Aggregate - Average GPA by cohort
```json
{
  "table": "students",
  "metric": "avg",
  "column": "gpa",
  "group_by": "cohort"
}
```

### Aggregate - Count enrollments per semester
```json
{
  "table": "enrollments",
  "metric": "count",
  "group_by": "semester"
}
```

### Error case - Unknown table
```json
{
  "table": "nonexistent_table"
}
```
→ Returns: `{"error": "Unknown table 'nonexistent_table'. Valid tables: ['courses', 'enrollments', 'students']"}`

### Read schema resource
- `schema://database` → Full database structure
- `schema://table/students` → Students table columns and types

## Test Results

```
35 passed in 0.32s

TestDatabaseSetup       - 5/5 passed
TestSchemaIntrospection - 3/3 passed
TestSearchTool          - 11/11 passed
TestInsertTool          - 6/6 passed
TestAggregateTool       - 10/10 passed
```
