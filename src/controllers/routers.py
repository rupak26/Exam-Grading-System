from fastapi import APIRouter , HTTPException
from ..configuration.database_config import get_db_connection
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, FileResponse , HTMLResponse
from fastapi.templating import Jinja2Templates
from ..utility import utilities

import os 
import uuid

import os
from pathlib import Path

###########################
# Route handlers          #
###########################


BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
uploads = BASE_DIR / "uploads"
uploads.mkdir(parents=True, exist_ok=True)

router = APIRouter()

#Checked
@router.get("/")
async def index(request: Request):
    """Render the home page listing all exams."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, subject FROM exams ORDER BY id DESC")
    exams = cur.fetchall()
    conn.close()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "exams": exams},
    )

#checked
@router.get("/exams/new")
async def new_exam_form(request: Request):
    """Display a form to create a new exam."""
    return templates.TemplateResponse("create_exam.html", {"request": request})

#checked
@router.post("/exams/new",response_class=HTMLResponse)
async def create_exam(request: Request):
    """Persist a new exam to the database and redirect to its page."""
    # Parse a standard URL-encoded form.  Using request.form() here does
    # not require python-multipart when the content-type is
    # routerlication/x-www-form-urlencoded (the default for HTML forms).
    form = await request.form()
    title = form.get("title", "").strip()
    subject = form.get("subject", "").strip()
    instructions = form.get("instructions", "").strip()
    if not title or not subject:
        raise HTTPException(status_code=400, detail="Title and subject are required")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO exams (title, subject, instructions) VALUES (?, ?, ?)",
        (title, subject, instructions),
    )
    exam_id = cur.lastrowid
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)

#checked
@router.get("/exams/{exam_id}")
async def exam_detail(request: Request, exam_id: int):
    """Show details for a specific exam including questions and students."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
    exam = cur.fetchone()
    if exam is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Exam not found")
    # Fetch questions and students
    cur.execute("SELECT * FROM questions WHERE exam_id = ? ORDER BY id", (exam_id,))
    questions = cur.fetchall()
    cur.execute("SELECT * FROM students WHERE exam_id = ? ORDER BY id", (exam_id,))
    students = cur.fetchall()
    # Count uploaded sheets for each student
    sheet_counts = {}
    for student in students:
        cur.execute("SELECT COUNT(*) FROM answer_sheets WHERE student_id = ?", (student["id"],))
        sheet_counts[student["id"]] = cur.fetchone()[0]
    conn.close()
    return templates.TemplateResponse(
        "exam_detail.html",
        {
            "request": request,
            "exam": exam,
            "questions": questions,
            "students": students,
            "sheet_counts": sheet_counts,
        },
    )

#checked
@router.post("/exams/{exam_id}/questions")
async def add_question(request: Request, exam_id: int):
    """Add a new question to an existing exam."""
    form = await request.form()
    text = form.get("text", "").strip()
    ideal_answer = form.get("ideal_answer", "").strip()
    point_value = form.get("point_value", "1").strip()
    try:
        point_value_float = float(point_value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Point value must be a number")
    if not text or not ideal_answer:
        raise HTTPException(status_code=400, detail="Question text and ideal answer are required")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO questions (exam_id, text, ideal_answer, point_value) VALUES (?, ?, ?, ?)",
        (exam_id, text, ideal_answer, point_value_float),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)

#checked
@router.post("/exams/{exam_id}/students")
async def add_student(request: Request, exam_id: int):
    """Add a new student to the exam roster."""
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Student name is required")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (exam_id, name) VALUES (?, ?)",
        (exam_id, name),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)


@router.get("/answer_sheets/{sheet_id}/download")
async def download_answer_sheet(sheet_id: int):
    """Allow the user to download the original uploaded PDF file."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT filename FROM answer_sheets WHERE id = ?", (sheet_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = uploads / row["filename"]
    return FileResponse(path=file_path, filename=file_path.name, media_type="routerlication/pdf")


#checked
@router.post("/exams/{exam_id}/upload")
async def upload_answer_sheet(request: Request, exam_id: int):
    """Handle PDF upload for a student's answer sheet.

    This implementation manually parses the multipart/form-data body
    because python-multipart is not available in this environment.  It
    expects two fields: ``student_id`` (the integer ID of the student)
    and ``file`` (the PDF upload).  The file is stored on disk and
    evaluation is performed immediately.
    """
    # Read the raw request body
    body = await request.body()
    content_type = request.headers.get("content-type", "")
    # Extract boundary
    boundary_marker = "boundary="
    if boundary_marker not in content_type:
        raise HTTPException(status_code=400, detail="Invalid multipart request")
    boundary = content_type.split(boundary_marker)[1]
    if boundary.startswith("\"") and boundary.endswith("\""):
        boundary = boundary[1:-1]
    delimiter = ("--" + boundary).encode()
    parts = body.split(delimiter)
    fields: dict[str, bytes] = {}
    for part in parts:
        if not part or part == b"--\r\n" or part == b"--":
            continue
        # Trim CRLF at the start and end
        part = part.strip(b"\r\n")
        # Split headers and content
        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue
        header_blob = part[:header_end].decode(errors="ignore")
        content = part[header_end + 4:]
        # Parse headers
        headers = {}
        for line in header_blob.split("\r\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        disposition = headers.get("content-disposition", "")
        # content-disposition: form-data; name="student_id"
        # or: content-disposition: form-data; name="file"; filename="..."
        if "form-data" in disposition:
            # Extract name and filename if present
            attrs = {}
            for item in disposition.split(";"):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    attrs[key.strip()] = value.strip().strip('"')
            name = attrs.get("name")
            filename = attrs.get("filename")
            if filename:
                # It's the uploaded file
                fields[name] = {"filename": filename, "content": content}
            else:
                fields[name] = content
    # Validate student_id
    if "student_id" not in fields:
        raise HTTPException(status_code=400, detail="Missing student_id field")
    student_id_bytes = fields["student_id"]
    try:
        student_id = int(student_id_bytes.decode().strip())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid student_id")
    # Validate file
    file_field = fields.get("file")
    if not isinstance(file_field, dict) or "filename" not in file_field:
        raise HTTPException(status_code=400, detail="Missing file field")
    filename = file_field["filename"]
    content_bytes: bytes = file_field["content"]
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    # Generate unique filename and save
    unique_name = f"{uuid.uuid4().hex}_{os.path.basename(filename)}"
    dest_path = uploads / unique_name
    with open(dest_path, "wb") as f:
        f.write(content_bytes)
    # Record in database
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO answer_sheets (student_id, filename) VALUES (?, ?)",
        (student_id, unique_name),
    )
    sheet_id = cur.lastrowid
    conn.commit()
    conn.close()
    # ======================================= Evaluate the sheet =============================================
    try:
        utilities.evaluate_answer_sheet(dest_path , sheet_id)
    except Exception as e:
        print(f"Error evaluating sheet {sheet_id}: {e}")
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)

#not checked
@router.get("/exams/{exam_id}/results")
async def exam_results(request: Request, exam_id: int):
    """Display detailed results for all students in an exam."""
    conn = get_db_connection()
    cur = conn.cursor()
    # Get exam information
    cur.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
    exam = cur.fetchone()
    if exam is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Exam not found")
    # Get students and their results
    cur.execute(
        """
        SELECT students.id AS student_id, students.name, answer_sheets.id AS sheet_id, answer_sheets.total_score
        FROM students
        LEFT JOIN answer_sheets ON students.id = answer_sheets.student_id
        WHERE students.exam_id = ?
        ORDER BY students.id
        """,
        (exam_id,),
    )
    rows = cur.fetchall()
    # Build a list grouped by students; each student may have multiple sheets
    students = {}
    for row in rows:
        sid = row["student_id"]
        if sid not in students:
            students[sid] = {"name": row["name"], "sheets": []}
        if row["sheet_id"] is not None:
            students[sid]["sheets"].append({"id": row["sheet_id"], "total_score": row["total_score"]})
    conn.close()
    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "exam": exam,
            "students": students,
        },
    )

#checked
@router.get("/answer_sheets/{sheet_id}")
async def sheet_detail(request: Request, sheet_id: int):
    """Show detailed evaluation for a single answer sheet."""
    conn = get_db_connection()
    cur = conn.cursor()
    # Retrieve sheet
    cur.execute(
        """
        SELECT answer_sheets.*, students.name AS student_name, exams.title AS exam_title, exams.id AS exam_id
        FROM answer_sheets
        JOIN students ON answer_sheets.student_id = students.id
        JOIN exams ON students.exam_id = exams.id
        WHERE answer_sheets.id = ?
        """,
        (sheet_id,),
    )
    sheet = cur.fetchone()
    if sheet is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Answer sheet not found")
    # Fetch question evaluations
    cur.execute(
        """
        SELECT questions.text AS question_text, questions.ideal_answer, answers.student_answer, answers.score
        FROM answers
        JOIN questions ON answers.question_id = questions.id
        WHERE answers.answer_sheet_id = ?
        ORDER BY questions.id
        """,
        (sheet_id,),
    )
    evaluations = cur.fetchall()
    conn.close()
    return templates.TemplateResponse(
        "sheet_detail.html",
        {
            "request": request,
            "sheet": sheet,
            "evaluations": evaluations,
            "exam_id": sheet["exam_id"],
        },
    )

#Problem is here
@router.get("/exams/{exam_id}/export")
async def export_results(exam_id: int):
    """Export all results for an exam as a CSV file."""
    import csv
    from io import StringIO
    conn = get_db_connection()
    cur = conn.cursor()
    # Get exam and question count to compute maximum possible score
    cur.execute("SELECT title FROM exams WHERE id = ?", (exam_id,))
    exam = cur.fetchone()
    if exam is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Exam not found")
    cur.execute("SELECT SUM(point_value) FROM questions WHERE exam_id = ?", (exam_id,))
    total_possible = cur.fetchone()[0] or 0.0
    # Retrieve scores
    cur.execute(
        """
        SELECT students.name, answer_sheets.total_score
        FROM students
        LEFT JOIN answer_sheets ON students.id = answer_sheets.student_id
        WHERE students.exam_id = ?
        ORDER BY students.id
        """,
        (exam_id,),
    )
    rows = cur.fetchall()
    conn.close()
    csv_io = StringIO()
    writer = csv.writer(csv_io)
    writer.writerow(["Student", "Score", "Out of"])
    for row in rows:
        score = row["total_score"] if row["total_score"] is not None else ""
        writer.writerow([row["name"], score, total_possible])
    csv_content = csv_io.getvalue()
    csv_io.close()
    filename = f"exam_{exam_id}_results.csv"
    return FileResponse(
        path_or_file=bytes(csv_content, "utf-8"),
        media_type="text/csv",
        filename=filename,
    )
