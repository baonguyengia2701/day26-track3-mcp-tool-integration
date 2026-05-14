"""
FastMCP Server for the SQLite Lab.
Exposes search, insert, and aggregate tools plus schema resources.
"""

import json
import sys
import os
from typing import Any, Optional

from fastmcp import FastMCP

# Ensure implementation directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import SQLiteAdapter, ValidationError
from init_db import create_database, DB_PATH

# ---------------------------------------------------------------------------
# Initialize database if it doesn't exist
# ---------------------------------------------------------------------------
if not os.path.exists(DB_PATH):
    create_database()

# ---------------------------------------------------------------------------
# Create MCP server and database adapter
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "SQLite Lab MCP Server",
    instructions=(
        "This MCP server provides access to a university SQLite database "
        "containing students, courses, and enrollments. "
        "Use the search tool to query data, insert to add new records, "
        "and aggregate for statistical queries. "
        "Read schema resources to understand the database structure."
    ),
)
adapter = SQLiteAdapter(DB_PATH)


# ===========================================================================
# TOOLS
# ===========================================================================


@mcp.tool(name="search")
def search(
    table: str,
    columns: Optional[list[str]] = None,
    filters: Optional[list[dict[str, Any]]] = None,
    limit: int = 20,
    offset: int = 0,
    order_by: Optional[str] = None,
    descending: bool = False,
) -> str:
    """
    Search rows in a database table with optional filtering, ordering, and pagination.

    Args:
        table: Name of the table to query (e.g. 'students', 'courses', 'enrollments').
        columns: List of column names to return. If not provided, all columns are returned.
        filters: List of filter conditions. Each filter is a dict with keys:
                 - column: the column name to filter on
                 - operator: comparison operator (=, !=, >, <, >=, <=, LIKE)
                 - value: the value to compare against
                 Example: [{"column": "cohort", "operator": "=", "value": "A1"}]
        limit: Maximum number of rows to return (default: 20, max: 100).
        offset: Number of rows to skip for pagination (default: 0).
        order_by: Column name to sort the results by.
        descending: If True, sort in descending order (default: False).

    Returns:
        JSON string with matched rows, total count, and pagination metadata.
    """
    try:
        result = adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValidationError as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> str:
    """
    Insert a new row into a database table.

    Args:
        table: Name of the table to insert into (e.g. 'students', 'courses', 'enrollments').
        values: A dictionary mapping column names to values.
                Example for students: {"name": "John Doe", "email": "john@uni.edu", "cohort": "A1", "gpa": 3.5}
                Example for courses: {"code": "CS401", "title": "Cloud Computing", "credits": 3, "department": "Computer Science"}

    Returns:
        JSON string with the inserted row data and its generated ID.
    """
    try:
        result = adapter.insert(table=table, values=values)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValidationError as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: Optional[str] = None,
    filters: Optional[list[dict[str, Any]]] = None,
    group_by: Optional[str] = None,
) -> str:
    """
    Run an aggregate query on a database table.

    Args:
        table: Name of the table (e.g. 'students', 'courses', 'enrollments').
        metric: The aggregate function to apply. One of: count, avg, sum, min, max.
        column: The column to aggregate on. Required for avg, sum, min, max.
                Optional for count (defaults to COUNT(*)).
        filters: Optional list of filter conditions (same format as search filters).
        group_by: Optional column name to group the results by.
                  Example: group_by="cohort" with metric="avg" and column="gpa"
                  will return the average GPA per cohort.

    Returns:
        JSON string with aggregate results.
    """
    try:
        result = adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by,
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValidationError as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


# ===========================================================================
# RESOURCES
# ===========================================================================


@mcp.resource("schema://database")
def database_schema() -> str:
    """
    Get the complete database schema.
    Returns JSON describing all tables and their column definitions.
    """
    schema = adapter.get_full_schema()
    return json.dumps(schema, indent=2, ensure_ascii=False)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """
    Get the schema for a specific table.

    Args:
        table_name: Name of the table (e.g. 'students', 'courses', 'enrollments').

    Returns:
        JSON describing the table's columns, types, and constraints.
    """
    try:
        columns = adapter.get_table_schema(table_name)
        result = {
            "table": table_name,
            "columns": columns,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValidationError as e:
        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)


# ===========================================================================
# ENTRY POINT
# ===========================================================================

if __name__ == "__main__":
    mcp.run()
