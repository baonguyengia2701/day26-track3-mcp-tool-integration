"""
Database initialization script.
Creates the SQLite database with schema and seed data for the MCP lab.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    cohort TEXT NOT NULL,
    gpa REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL DEFAULT 3,
    department TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    semester TEXT NOT NULL,
    score REAL,
    grade TEXT,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE(student_id, course_id, semester)
);
"""

SEED_SQL = """
-- Students
INSERT OR IGNORE INTO students (name, email, cohort, gpa) VALUES
    ('Nguyen Van An', 'an.nguyen@university.edu', 'A1', 3.8),
    ('Tran Thi Binh', 'binh.tran@university.edu', 'A1', 3.5),
    ('Le Van Cuong', 'cuong.le@university.edu', 'A2', 3.2),
    ('Pham Thi Dung', 'dung.pham@university.edu', 'A2', 3.9),
    ('Hoang Van Em', 'em.hoang@university.edu', 'A1', 2.8),
    ('Vo Thi Phuong', 'phuong.vo@university.edu', 'B1', 3.6),
    ('Bui Van Giang', 'giang.bui@university.edu', 'B1', 3.1),
    ('Dang Thi Hoa', 'hoa.dang@university.edu', 'B2', 3.7),
    ('Ngo Van Ich', 'ich.ngo@university.edu', 'A2', 2.9),
    ('Do Thi Kim', 'kim.do@university.edu', 'B2', 3.4);

-- Courses
INSERT OR IGNORE INTO courses (code, title, credits, department) VALUES
    ('CS101', 'Introduction to Programming', 3, 'Computer Science'),
    ('CS201', 'Data Structures and Algorithms', 4, 'Computer Science'),
    ('CS301', 'Database Systems', 3, 'Computer Science'),
    ('AI401', 'Machine Learning', 4, 'AI & Data Science'),
    ('AI402', 'Deep Learning', 4, 'AI & Data Science'),
    ('MATH201', 'Linear Algebra', 3, 'Mathematics'),
    ('MATH301', 'Probability and Statistics', 3, 'Mathematics');

-- Enrollments
INSERT OR IGNORE INTO enrollments (student_id, course_id, semester, score, grade) VALUES
    (1, 1, '2025-1', 92.5, 'A'),
    (1, 2, '2025-1', 88.0, 'B+'),
    (1, 4, '2025-2', 95.0, 'A+'),
    (2, 1, '2025-1', 85.0, 'B+'),
    (2, 3, '2025-1', 78.5, 'B'),
    (2, 5, '2025-2', 90.0, 'A'),
    (3, 1, '2025-1', 72.0, 'B'),
    (3, 2, '2025-1', 68.5, 'C+'),
    (3, 6, '2025-2', 80.0, 'B+'),
    (4, 1, '2025-1', 96.0, 'A+'),
    (4, 4, '2025-2', 93.5, 'A'),
    (4, 5, '2025-2', 91.0, 'A'),
    (5, 1, '2025-1', 65.0, 'C+'),
    (5, 3, '2025-1', 70.0, 'B'),
    (6, 2, '2025-1', 87.0, 'B+'),
    (6, 4, '2025-2', 82.5, 'B+'),
    (7, 1, '2025-1', 75.0, 'B'),
    (7, 6, '2025-2', 73.0, 'B'),
    (8, 3, '2025-1', 89.0, 'A'),
    (8, 5, '2025-2', 94.0, 'A'),
    (9, 1, '2025-1', 60.5, 'C'),
    (9, 2, '2025-1', 62.0, 'C'),
    (10, 3, '2025-1', 83.0, 'B+'),
    (10, 4, '2025-2', 86.5, 'B+');
"""


def create_database(db_path: str = DB_PATH) -> str:
    """
    Create and initialize the SQLite database with schema and seed data.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        The path to the created database file.
    """
    # Remove existing database for a clean start
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()
        print(f"[OK] Database created at: {db_path}")

        # Verify data
        cursor = conn.cursor()
        for table in ["students", "courses", "enrollments"]:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"     {table}: {count} rows")
    finally:
        conn.close()

    return db_path


if __name__ == "__main__":
    create_database()
