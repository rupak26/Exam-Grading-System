import os
import uuid
from pathlib import Path
from fastapi import APIRouter , HTTPException , Request
from configuration.database_config import get_cursor
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse , HTMLResponse
from ..utility import utilities
from services import service
from repository import repository

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
uploads = BASE_DIR / "uploads"
uploads.mkdir(parents=True, exist_ok=True)

import logging 
logger = logging.getLogger("routers.blog")


router = APIRouter(
    prefix = "/api/v1" ,
    tags = ['Grading_Endpoints'],
)

@router.get("/")
async def index(request: Request):
    conn , cursor = get_cursor()
    cursor.execute("SELECT id, title, subject FROM exams ORDER BY id DESC")
    exams = cursor.fetchall()
    conn.close()
    logger.info(f"Checked")
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "exams": exams},
    )

@router.get("/exams/new")
async def new_exam_form(request: Request):
    logger.info(f"get exam list")
    return templates.TemplateResponse("create_exam.html", {"request": request})

@router.post("/exams/new",response_class=HTMLResponse)
async def create_exam(request: Request):
    logger.info(f"create exam")
    return await service.create_exams(request)
   


@router.get("/exams/{exam_id}")
async def exam_detail(request: Request, exam_id: int):
    exam = await repository.get_exams(exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    questions = await repository.get_questons(exam_id)
    students = await repository.get_students(exam_id)
    sheet_counts = {}
    for student in students:
        sheet_data = await repository.get_data(student)
        sheet_counts[student["id"]] = sheet_data
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
    conn , cursor = get_cursor()
    cursor.execute(
        "INSERT INTO questions (exam_id, text, ideal_answer, point_value) VALUES (%s, %s, %s, %s)",
        (exam_id, text, ideal_answer, point_value_float),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)

@router.post("/exams/{exam_id}/students")
async def add_student(request: Request, exam_id: int):
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Student name is required")
    conn , cursor = get_cursor()
    cursor.execute(
        "INSERT INTO students (exam_id, name) VALUES (%s, %s)",
        (exam_id, name),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)

@router.get("/answer_sheets/{sheet_id}/download")
async def download_answer_sheet(sheet_id: int):
    """Allow the user to download the original uploaded PDF file."""
    conn , cursor = get_cursor()
    cursor.execute("SELECT filename FROM answer_sheets WHERE id = %s", (sheet_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = uploads / row["filename"]
    return FileResponse(path=file_path, filename=file_path.name, media_type="routerlication/pdf")

@router.post("/exams/{exam_id}/upload")
async def upload_answer_sheet(request: Request, exam_id: int):
    body = await request.body()
    content_type = request.headers.get("content-type", "")
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
    file_field = fields.get("file")
    if not isinstance(file_field, dict) or "filename" not in file_field:
        raise HTTPException(status_code=400, detail="Missing file field")
    filename = file_field["filename"]
    content_bytes: bytes = file_field["content"]
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    unique_name = f"{uuid.uuid4().hex}_{os.path.basename(filename)}"
    dest_path = uploads / unique_name
    with open(dest_path, "wb") as f:
        f.write(content_bytes)
    conn , cursor = get_cursor()
    cursor.execute(
        "INSERT INTO answer_sheets (student_id, filename) VALUES (%s, %s)",
        (student_id, unique_name),
    )
    sheet_id = cursor.lastrowid
    conn.commit()
    conn.close()
    # ======================================= Evaluate the sheet =============================================
    try:
        utilities.evaluate_answer_sheet(dest_path , sheet_id)
    except Exception as e:
        print(f"Error evaluating sheet {sheet_id}: {e}")
    return RedirectResponse(url=f"/exams/{exam_id}", status_code=303)

@router.get("/exams/{exam_id}/results")
async def exam_results(request: Request, exam_id: int):
    exam = await repository.get_exams(exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")

    rows = await repository.get_students_results(exam_id)
    # Build a list grouped by students; each student may have multiple sheets
    students = {}
    for row in rows:
        sid = row["student_id"]
        if sid not in students:
            students[sid] = {"name": row["name"], "sheets": []}
        if row["sheet_id"] is not None:
            students[sid]["sheets"].append({"id": row["sheet_id"], "total_score": row["total_score"]})

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "exam": exam,
            "students": students,
        },
    )

@router.get("/answer_sheets/{sheet_id}")
async def sheet_detail(request: Request, sheet_id: int):
    """Show detailed evaluation for a single answer sheet."""
    sheet = await repository.get_sheet(sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Answer sheet not found")
    # Fetch question evaluations
    
    evaluations = repository.get_evaluations(sheet_id)
    return templates.TemplateResponse(
        "sheet_detail.html",
        {
            "request": request,
            "sheet": sheet,
            "evaluations": evaluations,
            "exam_id": sheet["exam_id"],
        },
    )

@router.get("/exams/{exam_id}/export")
async def export_results(exam_id: int):
    """Export all results for an exam as a CSV file."""
    import csv
    from io import StringIO
    conn , cursor = get_cursor()
    # Get exam and question count to compute maximum possible score
    exam = await repository.get_exams(exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    cursor.execute("SELECT SUM(point_value) FROM questions WHERE exam_id = ?", (exam_id,))
    total_possible = cursor.fetchone()[0] or 0.0
    # Retrieve scores
    rows = await repository.retrieve_scores(exam_id)
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
