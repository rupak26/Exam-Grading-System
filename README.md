# Exam-Grading-System

Exam-Grading-System is a lightweight, self‑contained exam grading tool.  It
allows educators to create exams, add questions and students, upload
PDF answer sheets and receive automated scoring.  The backend is
implemented with FastAPI and SQLite using only packages available in
this environment; the frontend is rendered with Jinja2 templates and
styled with a minimalist stylesheet inspired by shadcn/ui's white
palette.

## Features

* **Exam management** – create exams with titles, subjects and
  instructions, add questions with ideal answers and point values and
  register students.
* **Answer sheet upload** – upload a PDF answer sheet for each
  student.  The server extracts text from the PDF, splits it into
  responses and compares each response to the ideal answer using
  RapidFuzz's token set ratio.  The total score and per‑question
  breakdown are stored.
* **Results dashboard** – view all students, their uploaded sheets
  and scores; drill down to see a side‑by‑side comparison of the
  student's answer and the canonical answer.
* **CSV export** – download a CSV file summarising scores for the
  entire class.

## Running the application

1.  Make sure you have Python 3.11 available.  All required
    dependencies are included in this environment (FastAPI, uvicorn,
    PyMuPDF, RapidFuzz).  You do **not** need to install Django; this
    project uses FastAPI because external package installation is
    restricted in this environment.
2.  Create the database and start the web server:

    ```bash
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    This will start a server on `http://127.0.0.1:8000/`.  Navigate
    there in your browser to begin creating exams.

3.  To stop the server press `Ctrl+C` in the terminal.

## Integrating a real AI model

core login in src/utility/utility.py:

You have to use Useing two AI models 

   * Florence-2: For OCR and text extraction from scanned answer sheets

   * LLaMA 3 8B Instruct: For evaluating and grading student answers against ideal answers


# Core Functions
  1. Text Extraction with Florence-2

    * extract_with_paddleocr(image_path: str) -> str

    * Converts PDF pages to images using pdf2image

    * Processes each image with Florence-2 model

    * Uses <OCR_WITH_REGION> task prompt for optimized text extraction

    * Returns structured OCR data with bounding boxes and text labels

  2. Key Features:

    * Handles multi-page PDF documents

    * Automatic cleanup of temporary image files

    * Robust error handling for corrupted pages

    * Returns both text content and spatial information

  3. Answer Evaluation with LLaMA
    
    * evaluate_answer(student_answer: str, ideal_answer: str, point_value: float) -> float

    * Uses LLaMA 3 8B Instruct model via Replicate API

    * Compares student answers against ideal answers

    * Returns numerical score based on point value

    * Includes strict prompt engineering for consistent grading

## Grading Prompt Structure:
```
  prompt = f"""
    You are grading a short answer question. The ideal answer is:
    "{ideal_answer}"

    The student's answer is:
    "{student_answer}"

    Respond with a single number between 0 and {point_value} representing
    the score. Do not provide explanations, only the number.
  """
```

## Workflow:

  *  PDF Processing: Converts PDF to individual page images

  *  Text Extraction: Uses Florence-2 to extract answers from each page

  *  Answer Matching: Aligns extracted answers with database questions

  *  AI Grading: Evaluates each answer using LLaMA model

  *  Results Storage: Saves scores to database with timestamps

## Database Operations:

  *  Updates answers table with individual question scores

  *  Updates answer_sheets table with total score and evaluation timestamp

  *  Maintains referential integrity with student and exam data

## Model Configuration
   
   Florence-2 Setup
   Located in configuration/florence2_configuration.py
   ```
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True)
    
    model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True, torch_dtype=torch.bfloat16)
   ```
  # LLaMA Configuration

    Model: meta/meta-llama-3-8b-instruct

    Access: Via Replicate API with secure token authentication

    Output: Strict numerical scoring only


You will need to set your Replicate API token in the environment
variable `REPLICATE_API_TOKEN` before running the server.  See the
[Replicate documentation](https://replicate.com) for details.


## API Endpoints List
   Dashboard & Navigation
   ```
    GET / - Home page listing all exams

    GET /exams/new - Create exam form
   ``` 

   Exam Management
   ```
    POST /exams/new - Create new exam

    GET /exams/{exam_id} - Get exam details

    POST /exams/{exam_id}/questions - Add question to exam

    POST /exams/{exam_id}/students - Add student to exam
   ```

   Answer Sheet Management
   ```
    POST /exams/{exam_id}/upload - Upload answer sheet PDF

    GET /answer_sheets/{sheet_id}/download - Download answer sheet PDF

    GET /answer_sheets/{sheet_id} - Get answer sheet details
   ```

   Results & Reporting
  ```
    GET /exams/{exam_id}/results - View exam results

    GET /exams/{exam_id}/export - Export results as CSV
  ```

