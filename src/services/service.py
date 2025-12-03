from fastapi import APIRouter , HTTPException , Request
from repository import repository

async def create_exams(request):
    form = await request.form()
    title = form.get("title", "").strip()
    subject = form.get("subject", "").strip()
    instructions = form.get("instructions", "").strip()
    if not title or not subject:
        raise HTTPException(status_code=400, detail="Title and subject are required")
    return repository.create_exams_repo(title , subject , instructions)
    