"""
Verification script for the MCP server.
Runs a series of checks to validate tool and resource functionality.
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import SQLiteAdapter, ValidationError
from init_db import create_database, DB_PATH


def separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_pass(name: str) -> None:
    print(f"  [PASS] {name}")


def test_fail(name: str, detail: str = "") -> None:
    print(f"  [FAIL] {name}")
    if detail:
        print(f"          {detail}")


def run_verification():
    """Run all verification checks."""

    # ------------------------------------------------------------------
    # Step 0: Initialize database
    # ------------------------------------------------------------------
    separator("Step 0: Database Initialization")
    try:
        create_database()
        test_pass("Database created successfully")
    except Exception as e:
        test_fail("Database creation", str(e))
        return

    adapter = SQLiteAdapter(DB_PATH)

    # ------------------------------------------------------------------
    # Step 1: Schema introspection
    # ------------------------------------------------------------------
    separator("Step 1: Schema Introspection")

    tables = adapter.list_tables()
    if set(tables) == {"students", "courses", "enrollments"}:
        test_pass(f"Tables found: {tables}")
    else:
        test_fail("Table listing", f"Got: {tables}")

    for table in tables:
        schema = adapter.get_table_schema(table)
        col_names = [c["name"] for c in schema]
        test_pass(f"Schema for '{table}': {col_names}")

    full_schema = adapter.get_full_schema()
    if len(full_schema) == 3:
        test_pass("Full schema returns all 3 tables")
    else:
        test_fail("Full schema", f"Expected 3 tables, got {len(full_schema)}")

    # ------------------------------------------------------------------
    # Step 2: Search tool
    # ------------------------------------------------------------------
    separator("Step 2: Search Tool")

    # Basic search
    result = adapter.search("students")
    if result["total"] == 10:
        test_pass(f"Search all students: {result['total']} rows")
    else:
        test_fail("Search all students", f"Expected 10, got {result['total']}")

    # Search with filter
    result = adapter.search(
        "students",
        filters=[{"column": "cohort", "operator": "=", "value": "A1"}]
    )
    if result["total"] == 3:
        test_pass(f"Search students in cohort A1: {result['total']} rows")
    else:
        test_fail("Search filtered", f"Expected 3, got {result['total']}")

    # Search with columns
    result = adapter.search("students", columns=["name", "gpa"])
    if all(set(r.keys()) == {"name", "gpa"} for r in result["rows"]):
        test_pass("Search with specific columns works")
    else:
        test_fail("Search specific columns")

    # Search with ordering
    result = adapter.search("students", order_by="gpa", descending=True, limit=3)
    if len(result["rows"]) == 3 and result["rows"][0]["gpa"] >= result["rows"][1]["gpa"]:
        test_pass(f"Search with ORDER BY gpa DESC: top student = {result['rows'][0]['name']}")
    else:
        test_fail("Search with ordering")

    # Search with pagination
    page1 = adapter.search("students", limit=5, offset=0)
    page2 = adapter.search("students", limit=5, offset=5)
    if len(page1["rows"]) == 5 and len(page2["rows"]) == 5:
        test_pass("Pagination works (2 pages of 5)")
    else:
        test_fail("Pagination")

    # ------------------------------------------------------------------
    # Step 3: Insert tool
    # ------------------------------------------------------------------
    separator("Step 3: Insert Tool")

    result = adapter.insert("students", {
        "name": "Test Student",
        "email": "test@university.edu",
        "cohort": "C1",
        "gpa": 3.0,
    })
    if result["inserted_id"] is not None:
        test_pass(f"Insert student: id={result['inserted_id']}")
    else:
        test_fail("Insert student")

    # Verify the insert
    verify = adapter.search(
        "students",
        filters=[{"column": "email", "operator": "=", "value": "test@university.edu"}]
    )
    if verify["total"] == 1:
        test_pass("Inserted student is searchable")
    else:
        test_fail("Verify insert")

    # ------------------------------------------------------------------
    # Step 4: Aggregate tool
    # ------------------------------------------------------------------
    separator("Step 4: Aggregate Tool")

    # COUNT
    result = adapter.aggregate("students", "count")
    count_val = result["results"][0]["value"]
    test_pass(f"COUNT students: {count_val}")

    # AVG
    result = adapter.aggregate("students", "avg", column="gpa")
    avg_val = result["results"][0]["value"]
    test_pass(f"AVG gpa: {avg_val:.2f}")

    # AVG with GROUP BY
    result = adapter.aggregate("students", "avg", column="gpa", group_by="cohort")
    if len(result["results"]) > 1:
        test_pass(f"AVG gpa by cohort: {len(result['results'])} groups")
        for r in result["results"]:
            print(f"          cohort={r['cohort']}, avg_gpa={r['value']:.2f}")
    else:
        test_fail("Aggregate GROUP BY")

    # SUM
    result = adapter.aggregate("enrollments", "sum", column="score")
    test_pass(f"SUM scores: {result['results'][0]['value']}")

    # MIN / MAX
    result = adapter.aggregate("enrollments", "min", column="score")
    test_pass(f"MIN score: {result['results'][0]['value']}")

    result = adapter.aggregate("enrollments", "max", column="score")
    test_pass(f"MAX score: {result['results'][0]['value']}")

    # Aggregate with filter
    result = adapter.aggregate(
        "enrollments", "avg", column="score",
        filters=[{"column": "semester", "operator": "=", "value": "2025-1"}]
    )
    test_pass(f"AVG score in semester 2025-1: {result['results'][0]['value']:.2f}")

    # ------------------------------------------------------------------
    # Step 5: Error handling / Validation
    # ------------------------------------------------------------------
    separator("Step 5: Error Handling & Validation")

    # Unknown table
    try:
        adapter.search("nonexistent_table")
        test_fail("Reject unknown table (no error raised)")
    except ValidationError as e:
        test_pass(f"Reject unknown table: {e}")

    # Unknown column
    try:
        adapter.search("students", columns=["nonexistent_col"])
        test_fail("Reject unknown column (no error raised)")
    except ValidationError as e:
        test_pass(f"Reject unknown column: {e}")

    # Unsupported operator
    try:
        adapter.search("students", filters=[{"column": "gpa", "operator": "DROP", "value": "1"}])
        test_fail("Reject unsupported operator (no error raised)")
    except ValidationError as e:
        test_pass(f"Reject unsupported operator: {e}")

    # Invalid metric
    try:
        adapter.aggregate("students", "median", column="gpa")
        test_fail("Reject invalid metric (no error raised)")
    except ValidationError as e:
        test_pass(f"Reject invalid metric: {e}")

    # Empty insert
    try:
        adapter.insert("students", {})
        test_fail("Reject empty insert (no error raised)")
    except ValidationError as e:
        test_pass(f"Reject empty insert: {e}")

    # Aggregate without required column
    try:
        adapter.aggregate("students", "avg")
        test_fail("Reject aggregate without column (no error raised)")
    except ValidationError as e:
        test_pass(f"Reject aggregate without column: {e}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    separator("Verification Complete")
    print("  All checks above should show [PASS].")
    print("  If any show [FAIL], review the corresponding code.\n")


if __name__ == "__main__":
    run_verification()
