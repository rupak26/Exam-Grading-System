from pathlib import Path
import sqlite3



###########################
# Database configuration  #
###########################
import os
from pathlib import Path

BASE_DIR = Path(os.getenv("BASE_DIR", ".")).resolve()
UPLOAD_DIR = BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")
DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "grade_buddy.db")
# DATABASE_PATH = Path(__file__).parent / "grade_buddy.db"

def get_db_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database.

    The connection uses row_factory to return dictionaries for easier
    access to columns by name.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialise_database() -> None:
    """Create the necessary tables if they do not already exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    # Exams table stores metadata about each exam.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            instructions TEXT
        )
        """
    )
    # Questions table stores questions belonging to an exam.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            ideal_answer TEXT NOT NULL,
            point_value REAL NOT NULL DEFAULT 1.0,
            FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
        )
        """
    )
    # Students table stores the roster for each exam.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
        )
        """
    )
    # Answer sheets represent a student's uploaded PDF and evaluation
    # summary.  The extracted_text column stores raw text extracted
    # from the PDF for later analysis.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS answer_sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            extracted_text TEXT,
            evaluated_at TIMESTAMP,
            total_score REAL,
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        )
        """
    )
    # Answers table stores per-question evaluations for each answer
    # sheet.  Each row contains the student's answer, the assigned
    # score and any evaluation notes.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            answer_sheet_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            student_answer TEXT,
            score REAL,
            FOREIGN KEY(answer_sheet_id) REFERENCES answer_sheets(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    conn.close()
