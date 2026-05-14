"""
Automated test suite for the MCP server.
Tests tool functionality, validation, and edge cases.
"""

import json
import os
import sys
import unittest

# Add implementation directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from db import SQLiteAdapter, ValidationError
from init_db import create_database, DB_PATH


class TestDatabaseSetup(unittest.TestCase):
    """Test database initialization."""

    @classmethod
    def setUpClass(cls):
        """Create a fresh database before all tests."""
        create_database()
        cls.adapter = SQLiteAdapter(DB_PATH)

    def test_database_file_exists(self):
        """The database file should exist after initialization."""
        self.assertTrue(os.path.exists(DB_PATH))

    def test_tables_exist(self):
        """All three tables should be present."""
        tables = self.adapter.list_tables()
        self.assertIn("students", tables)
        self.assertIn("courses", tables)
        self.assertIn("enrollments", tables)
        self.assertEqual(len(tables), 3)

    def test_students_have_data(self):
        """Students table should have seed data."""
        result = self.adapter.search("students")
        self.assertEqual(result["total"], 10)

    def test_courses_have_data(self):
        """Courses table should have seed data."""
        result = self.adapter.search("courses")
        self.assertEqual(result["total"], 7)

    def test_enrollments_have_data(self):
        """Enrollments table should have seed data."""
        result = self.adapter.search("enrollments")
        self.assertEqual(result["total"], 24)


class TestSchemaIntrospection(unittest.TestCase):
    """Test schema-related operations."""

    @classmethod
    def setUpClass(cls):
        create_database()
        cls.adapter = SQLiteAdapter(DB_PATH)

    def test_table_schema_columns(self):
        """Each table schema should return valid column info."""
        schema = self.adapter.get_table_schema("students")
        col_names = [c["name"] for c in schema]
        self.assertIn("id", col_names)
        self.assertIn("name", col_names)
        self.assertIn("email", col_names)
        self.assertIn("cohort", col_names)
        self.assertIn("gpa", col_names)

    def test_full_schema(self):
        """Full schema should contain all tables."""
        full = self.adapter.get_full_schema()
        self.assertEqual(len(full), 3)
        self.assertIn("students", full)
        self.assertIn("courses", full)
        self.assertIn("enrollments", full)

    def test_invalid_table_schema(self):
        """Requesting schema for a non-existent table should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.get_table_schema("does_not_exist")


class TestSearchTool(unittest.TestCase):
    """Test the search functionality."""

    @classmethod
    def setUpClass(cls):
        create_database()
        cls.adapter = SQLiteAdapter(DB_PATH)

    def test_basic_search(self):
        """Search without filters should return all rows."""
        result = self.adapter.search("students")
        self.assertEqual(result["total"], 10)
        self.assertLessEqual(len(result["rows"]), 20)

    def test_search_with_filter(self):
        """Search with equality filter should return matching rows."""
        result = self.adapter.search(
            "students",
            filters=[{"column": "cohort", "operator": "=", "value": "A1"}],
        )
        self.assertEqual(result["total"], 3)
        for row in result["rows"]:
            self.assertEqual(row["cohort"], "A1")

    def test_search_with_like_filter(self):
        """Search with LIKE operator should work."""
        result = self.adapter.search(
            "students",
            filters=[{"column": "name", "operator": "LIKE", "value": "%Nguyen%"}],
        )
        self.assertGreaterEqual(result["total"], 1)

    def test_search_with_comparison_filter(self):
        """Search with > operator should return matching rows."""
        result = self.adapter.search(
            "students",
            filters=[{"column": "gpa", "operator": ">", "value": 3.5}],
        )
        for row in result["rows"]:
            self.assertGreater(row["gpa"], 3.5)

    def test_search_selected_columns(self):
        """Search with specific columns should only return those columns."""
        result = self.adapter.search("students", columns=["name", "gpa"])
        for row in result["rows"]:
            self.assertEqual(set(row.keys()), {"name", "gpa"})

    def test_search_order_by(self):
        """Search with order_by should return sorted results."""
        result = self.adapter.search("students", order_by="gpa", descending=True)
        gpas = [r["gpa"] for r in result["rows"]]
        self.assertEqual(gpas, sorted(gpas, reverse=True))

    def test_search_pagination(self):
        """Pagination should return correct subsets."""
        page1 = self.adapter.search("students", limit=3, offset=0)
        page2 = self.adapter.search("students", limit=3, offset=3)
        self.assertEqual(len(page1["rows"]), 3)
        self.assertEqual(len(page2["rows"]), 3)
        # Pages should not overlap
        ids1 = {r["id"] for r in page1["rows"]}
        ids2 = {r["id"] for r in page2["rows"]}
        self.assertEqual(len(ids1 & ids2), 0)

    def test_search_limit_clamped(self):
        """Limit above 100 should be clamped to 100."""
        result = self.adapter.search("students", limit=999)
        self.assertEqual(result["limit"], 100)

    def test_search_invalid_table(self):
        """Search on invalid table should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.search("fake_table")

    def test_search_invalid_column(self):
        """Search with invalid column should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.search("students", columns=["fake_column"])

    def test_search_invalid_operator(self):
        """Search with unsupported operator should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.search(
                "students",
                filters=[{"column": "gpa", "operator": "BETWEEN", "value": 3.0}],
            )


class TestInsertTool(unittest.TestCase):
    """Test the insert functionality."""

    @classmethod
    def setUpClass(cls):
        create_database()
        cls.adapter = SQLiteAdapter(DB_PATH)

    def test_insert_student(self):
        """Inserting a valid student should succeed."""
        result = self.adapter.insert("students", {
            "name": "Unit Test Student",
            "email": "unittest@university.edu",
            "cohort": "T1",
            "gpa": 4.0,
        })
        self.assertIn("inserted_id", result)
        self.assertIsNotNone(result["inserted_id"])
        self.assertEqual(result["row"]["name"], "Unit Test Student")

    def test_insert_course(self):
        """Inserting a valid course should succeed."""
        result = self.adapter.insert("courses", {
            "code": "TEST101",
            "title": "Test Course",
            "credits": 3,
            "department": "Testing",
        })
        self.assertIn("inserted_id", result)

    def test_insert_empty_values(self):
        """Inserting with empty values should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.insert("students", {})

    def test_insert_invalid_table(self):
        """Inserting into invalid table should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.insert("fake_table", {"col": "val"})

    def test_insert_invalid_column(self):
        """Inserting with invalid column should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.insert("students", {"fake_column": "value"})

    def test_insert_duplicate_email(self):
        """Inserting a duplicate unique value should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.insert("students", {
                "name": "Duplicate",
                "email": "an.nguyen@university.edu",  # already exists
                "cohort": "A1",
            })


class TestAggregateTool(unittest.TestCase):
    """Test the aggregate functionality."""

    @classmethod
    def setUpClass(cls):
        create_database()
        cls.adapter = SQLiteAdapter(DB_PATH)

    def test_count_all(self):
        """COUNT(*) should return total row count."""
        result = self.adapter.aggregate("students", "count")
        self.assertEqual(result["results"][0]["value"], 10)

    def test_avg(self):
        """AVG should return a numeric value."""
        result = self.adapter.aggregate("students", "avg", column="gpa")
        self.assertIsInstance(result["results"][0]["value"], float)

    def test_sum(self):
        """SUM should return total."""
        result = self.adapter.aggregate("enrollments", "sum", column="score")
        self.assertGreater(result["results"][0]["value"], 0)

    def test_min(self):
        """MIN should return the smallest value."""
        result = self.adapter.aggregate("enrollments", "min", column="score")
        self.assertIsNotNone(result["results"][0]["value"])

    def test_max(self):
        """MAX should return the largest value."""
        result = self.adapter.aggregate("enrollments", "max", column="score")
        self.assertIsNotNone(result["results"][0]["value"])

    def test_group_by(self):
        """GROUP BY should return multiple groups."""
        result = self.adapter.aggregate(
            "students", "avg", column="gpa", group_by="cohort"
        )
        self.assertGreater(len(result["results"]), 1)

    def test_aggregate_with_filter(self):
        """Aggregate with filter should only include matching rows."""
        result = self.adapter.aggregate(
            "enrollments", "avg", column="score",
            filters=[{"column": "semester", "operator": "=", "value": "2025-1"}],
        )
        self.assertIsNotNone(result["results"][0]["value"])

    def test_invalid_metric(self):
        """Unsupported metric should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.aggregate("students", "median", column="gpa")

    def test_aggregate_without_required_column(self):
        """AVG without column should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.aggregate("students", "avg")

    def test_aggregate_invalid_table(self):
        """Aggregate on invalid table should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.adapter.aggregate("fake_table", "count")


if __name__ == "__main__":
    unittest.main(verbosity=2)
