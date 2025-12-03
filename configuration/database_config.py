import psycopg
from .main_config import DB_URL 

def get_cursor():
    try:
        conn = psycopg.connect(DB_URL)
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print("Database connection failed:", e)
        return None, None
    
def initialise_database() -> None:
    try:
        conn, cursor = get_cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                instructions TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                exam_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                ideal_answer TEXT NOT NULL,
                point_value REAL NOT NULL DEFAULT 1.0,
                FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                exam_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS answer_sheets (
                id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                extracted_text TEXT,
                evaluated_at TIMESTAMP,
                total_score REAL,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS answers (
                id SERIAL PRIMARY KEY,
                answer_sheet_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                student_answer TEXT,
                score REAL,
                FOREIGN KEY(answer_sheet_id) REFERENCES answer_sheets(id) ON DELETE CASCADE,
                FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
        """)

       
        conn.commit()
        conn.close()
    except Exception as e:
        print("initialise_database Failed")
        