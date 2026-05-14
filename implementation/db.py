"""
Database adapter module.
Provides a safe, validated interface to the SQLite database for the MCP server.
"""

import sqlite3
import os
from typing import Any, Optional


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


# Operators supported in search filters
SUPPORTED_OPERATORS = {
    "=": "=",
    "!=": "!=",
    ">": ">",
    "<": "<",
    ">=": ">=",
    "<=": "<=",
    "like": "LIKE",
    "LIKE": "LIKE",
}

# Aggregate functions supported
SUPPORTED_METRICS = {"count", "avg", "sum", "min", "max"}

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab.db")


class SQLiteAdapter:
    """
    Safe database adapter for SQLite.
    All identifiers are validated against the actual schema before use.
    All user values are bound via parameterized queries.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> sqlite3.Connection:
        """Return a SQLite connection with Row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ------------------------------------------------------------------
    # Schema introspection
    # ------------------------------------------------------------------

    def list_tables(self) -> list[str]:
        """Return a list of user-created table names (excluding internal tables)."""
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
            return [row["name"] for row in rows]
        finally:
            conn.close()

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        """
        Return column definitions for the given table.

        Each column is a dict with keys: cid, name, type, notnull, default_value, pk.
        Raises ValidationError if the table does not exist.
        """
        self._validate_table(table)
        conn = self.connect()
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return [
                {
                    "cid": row["cid"],
                    "name": row["name"],
                    "type": row["type"],
                    "notnull": bool(row["notnull"]),
                    "default_value": row["dflt_value"],
                    "pk": bool(row["pk"]),
                }
                for row in rows
            ]
        finally:
            conn.close()

    def get_full_schema(self) -> dict[str, list[dict[str, Any]]]:
        """Return schema information for every table in the database."""
        schema = {}
        for table in self.list_tables():
            schema[table] = self.get_table_schema(table)
        return schema

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_table(self, table: str) -> None:
        """Raise ValidationError if the table does not exist."""
        valid_tables = self.list_tables()
        if table not in valid_tables:
            raise ValidationError(
                f"Unknown table '{table}'. Valid tables: {valid_tables}"
            )

    def _validate_columns(self, table: str, columns: list[str]) -> None:
        """Raise ValidationError if any column does not exist in the table."""
        schema = self.get_table_schema(table)
        valid_columns = {col["name"] for col in schema}
        for col in columns:
            if col not in valid_columns:
                raise ValidationError(
                    f"Unknown column '{col}' in table '{table}'. "
                    f"Valid columns: {sorted(valid_columns)}"
                )

    def _validate_operator(self, op: str) -> str:
        """Return the SQL operator or raise ValidationError."""
        sql_op = SUPPORTED_OPERATORS.get(op)
        if sql_op is None:
            raise ValidationError(
                f"Unsupported filter operator '{op}'. "
                f"Supported: {list(SUPPORTED_OPERATORS.keys())}"
            )
        return sql_op

    def _validate_metric(self, metric: str) -> str:
        """Return the upper-cased metric or raise ValidationError."""
        m = metric.lower()
        if m not in SUPPORTED_METRICS:
            raise ValidationError(
                f"Unsupported metric '{metric}'. Supported: {sorted(SUPPORTED_METRICS)}"
            )
        return m.upper()

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def search(
        self,
        table: str,
        columns: Optional[list[str]] = None,
        filters: Optional[list[dict[str, Any]]] = None,
        limit: int = 20,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        """
        Search rows in a table with optional filtering, ordering, and pagination.

        Args:
            table: Name of the table to search.
            columns: Columns to return (default: all).
            filters: List of filter dicts, each with keys: column, operator, value.
            limit: Max rows to return (default 20, max 100).
            offset: Number of rows to skip.
            order_by: Column name to sort by.
            descending: Sort descending if True.

        Returns:
            Dict with keys: table, columns, rows, total, limit, offset.
        """
        self._validate_table(table)

        # Validate and build SELECT columns
        if columns:
            self._validate_columns(table, columns)
            select_cols = ", ".join(columns)
        else:
            select_cols = "*"

        # Build WHERE clause
        where_parts: list[str] = []
        params: list[Any] = []
        if filters:
            for f in filters:
                col = f.get("column")
                op = f.get("operator", "=")
                val = f.get("value")
                if col is None or val is None:
                    raise ValidationError(
                        "Each filter must have 'column' and 'value' keys."
                    )
                self._validate_columns(table, [col])
                sql_op = self._validate_operator(op)
                where_parts.append(f"{col} {sql_op} ?")
                params.append(val)

        sql = f"SELECT {select_cols} FROM {table}"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)

        # ORDER BY
        if order_by:
            self._validate_columns(table, [order_by])
            direction = "DESC" if descending else "ASC"
            sql += f" ORDER BY {order_by} {direction}"

        # Count total matching rows before pagination
        count_sql = f"SELECT COUNT(*) as cnt FROM {table}"
        if where_parts:
            count_sql += " WHERE " + " AND ".join(where_parts)

        # Clamp limit
        limit = min(max(1, limit), 100)
        sql += " LIMIT ? OFFSET ?"
        params_with_pagination = params + [limit, offset]

        conn = self.connect()
        try:
            total = conn.execute(count_sql, params).fetchone()["cnt"]
            rows = conn.execute(sql, params_with_pagination).fetchall()
            result_rows = [dict(row) for row in rows]
            return {
                "table": table,
                "columns": columns or [k for k in result_rows[0].keys()] if result_rows else columns or [],
                "rows": result_rows,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        finally:
            conn.close()

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a single row into a table.

        Args:
            table: Name of the table.
            values: Dict mapping column names to values.

        Returns:
            Dict with keys: table, inserted_id, row.
        """
        self._validate_table(table)

        if not values:
            raise ValidationError("Cannot insert an empty row. Provide at least one column-value pair.")

        columns = list(values.keys())
        self._validate_columns(table, columns)

        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        params = list(values.values())

        conn = self.connect()
        try:
            cursor = conn.execute(sql, params)
            conn.commit()
            inserted_id = cursor.lastrowid

            # Fetch the inserted row
            row = conn.execute(
                f"SELECT * FROM {table} WHERE rowid = ?", [inserted_id]
            ).fetchone()

            return {
                "table": table,
                "inserted_id": inserted_id,
                "row": dict(row) if row else values,
            }
        except sqlite3.IntegrityError as e:
            raise ValidationError(f"Integrity error: {e}")
        finally:
            conn.close()

    def aggregate(
        self,
        table: str,
        metric: str,
        column: Optional[str] = None,
        filters: Optional[list[dict[str, Any]]] = None,
        group_by: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Run an aggregate query on a table.

        Args:
            table: Table name.
            metric: One of count, avg, sum, min, max.
            column: Column to aggregate (required for avg, sum, min, max).
            filters: Optional filters (same format as search).
            group_by: Optional column to group results by.

        Returns:
            Dict with keys: table, metric, column, results.
        """
        self._validate_table(table)
        sql_metric = self._validate_metric(metric)

        # COUNT can work without a column (COUNT(*))
        if sql_metric == "COUNT" and column is None:
            agg_expr = "COUNT(*)"
        elif column is None:
            raise ValidationError(
                f"Metric '{metric}' requires a 'column' argument."
            )
        else:
            self._validate_columns(table, [column])
            agg_expr = f"{sql_metric}({column})"

        # Build SELECT
        select_parts = [f"{agg_expr} AS value"]
        if group_by:
            self._validate_columns(table, [group_by])
            select_parts.insert(0, group_by)

        sql = f"SELECT {', '.join(select_parts)} FROM {table}"

        # WHERE
        params: list[Any] = []
        if filters:
            where_parts: list[str] = []
            for f in filters:
                col = f.get("column")
                op = f.get("operator", "=")
                val = f.get("value")
                if col is None or val is None:
                    raise ValidationError(
                        "Each filter must have 'column' and 'value' keys."
                    )
                self._validate_columns(table, [col])
                sql_op = self._validate_operator(op)
                where_parts.append(f"{col} {sql_op} ?")
                params.append(val)
            sql += " WHERE " + " AND ".join(where_parts)

        # GROUP BY
        if group_by:
            sql += f" GROUP BY {group_by}"

        conn = self.connect()
        try:
            rows = conn.execute(sql, params).fetchall()
            results = [dict(row) for row in rows]
            return {
                "table": table,
                "metric": metric,
                "column": column,
                "results": results,
            }
        finally:
            conn.close()
