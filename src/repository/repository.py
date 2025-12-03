from configuration.database_config import get_cursor
from fastapi.responses import RedirectResponse, FileResponse , HTMLResponse
import logging 
logger = logging.getLogger("repository.blog")

async def create_exams_repo(title , subject , instructions):
    try:
        conn , cursor = get_cursor()
        cursor.execute(
        "INSERT INTO exams (title, subject, instructions) VALUES (%s, %s, %s)",
        (title, subject, instructions),
        )
        exam_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)
    except Exception as e:
        logger.error(f"Error is {e}")
        return None

async def get_exams(exam_id):
    conn , cursor = get_cursor()
    cursor.execute("SELECT * FROM exams WHERE id = %s", (exam_id,))
    exam = cursor.fetchone()
    return exam

async def get_questons(exam_id):
    conn , cursor = get_cursor()
    cursor.execute("SELECT * FROM questions WHERE exam_id = %s ORDER BY id", (exam_id,))
    questions = cursor.fetchall()
    return questions

async def get_students(exam_id):
    conn , cursor = get_cursor()
    cursor.execute("SELECT * FROM students WHERE exam_id = %s ORDER BY id", (exam_id,))
    students = cursor.fetchall()
    return students

async def get_data(student):
    conn , cursor = get_cursor()
    cursor.execute("SELECT COUNT(*) FROM answer_sheets WHERE student_id = %s", (student["id"],))
    return cursor.fetchone()[0]

async def get_students_results(exam_id):
    conn , cursor = get_cursor() 
    cursor.execute(
        """
        SELECT students.id AS student_id, students.name, answer_sheets.id AS sheet_id, answer_sheets.total_score
        FROM students
        LEFT JOIN answer_sheets ON students.id = answer_sheets.student_id
        WHERE students.exam_id = %s
        ORDER BY students.id
        """,
        (exam_id,),
    )
    return cursor.fetchall()

async def get_sheet(sheet_id):
    conn , cursor = get_cursor()
    cursor.execute(
        """
        SELECT answer_sheets.*, students.name AS student_name, exams.title AS exam_title, exams.id AS exam_id
        FROM answer_sheets
        JOIN students ON answer_sheets.student_id = students.id
        JOIN exams ON students.exam_id = exams.id
        WHERE answer_sheets.id = ?
        """,
        (sheet_id,),
    )
    return cursor.fetchone()

async def get_evaluations(sheet_id):
    conn , cursor = get_cursor()
    cursor.execute(
        """
        SELECT questions.text AS question_text, questions.ideal_answer, answers.student_answer, answers.score
        FROM answers
        JOIN questions ON answers.question_id = questions.id
        WHERE answers.answer_sheet_id = %s
        ORDER BY questions.id
        """,
        (sheet_id,),
    )
    return cursor.fetchall()

async def retrieve_scroes(exam_id):
    conn , cursor = get_cursor()
    cursor.execute(
        """
        SELECT students.name, answer_sheets.total_score
        FROM students
        LEFT JOIN answer_sheets ON students.id = answer_sheets.student_id
        WHERE students.exam_id = %s
        ORDER BY students.id
        """,
        (exam_id,),
    )
    return cursor.fetchall()