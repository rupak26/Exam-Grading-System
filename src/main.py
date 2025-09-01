"""
grade_buddy_ai
================

This module defines a simple web application for managing and grading
written exams.  The app is built with FastAPI and uses the Python
standard library (sqlite3) to persist data.  It exposes a small set
of pages that allow teachers to create exams, add questions and
students, upload PDF answer sheets and automatically evaluate the
responses.  Evaluation is performed using a basic text similarity
heuristic based on the RapidFuzz library.  While this logic does not
match the power of large language models, it demonstrates how you
might integrate OCR (Optical Character Recongition) and AI into a grading pipeline.  In a real
deployment you could swap out the ``evaluate_answer`` function with
calls to the Replicate Florence 2 model or another service.

To run the application, install the dependencies bundled with this
environment (FastAPI is already installed) and execute ``python
main.py``.  Visit ``http://localhost:8000`` in your browser to use
the interface.
"""

import os
import shutil
import sqlite3
import uvicorn

from fastapi import FastAPI 
from datetime import datetime
from pathlib import Path

from .configuration.database_config import get_db_connection , initialise_database
from .controllers import routers
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates


import psutil
# RapidFuzz provides efficient string similarity functions.  It's
# installed in the environment by default.
# from rapidfuzz import fuzz

# PyMuPDF (imported as fitz) allows us to extract text from PDF files.
# import fitz


###########################
# Application setup       #
###########################

# Initialise the database when the module is first imported.
initialise_database()

app = FastAPI()

# Directories for uploads and static files
BASE_DIR = Path(os.getenv("BASE_DIR", ".")).resolve()
UPLOAD_DIR = BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")
DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "grade_buddy.db")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(routers.router)

@app.get("/server-stats")
def server_stats():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    return {
        "cpu_percent": cpu,
        "memory_used_mb": memory.used / (1024 * 1024),
        "memory_available_mb": memory.available / (1024 * 1024),
        "total_memory_mb": memory.total / (1024 * 1024)
    }

@app.get("/cpu-info")
def cpu_info():
    return {
        "logical_cpus": psutil.cpu_count(),
        "physical_cores": psutil.cpu_count(logical=False),
        "cpu_usage_per_core": psutil.cpu_percent(percpu=True, interval=1),
        "total_cpu_usage": psutil.cpu_percent(interval=1)
    }

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
