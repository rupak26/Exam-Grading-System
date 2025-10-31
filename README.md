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
    python grade_buddy_ai/main.py
    ```

    This will start a server on `http://127.0.0.1:8000/`.  Navigate
    there in your browser to begin creating exams.

3.  To stop the server press `Ctrl+C` in the terminal.

## Integrating a real AI model

The current scoring logic lives in `grade_buddy_ai/main.py` in the
function `evaluate_answer`.  It uses the RapidFuzz library to compute
a simple similarity metric between the student's answer and the ideal
answer.  To use a large language model instead (for example the
Florence 2 Large model on Replicate), replace the body of
`evaluate_answer` with a call to your model.  You might construct a
prompt like this:

```python
import replicate

def evaluate_answer(student_answer: str, ideal_answer: str, point_value: float) -> float:
    # Compose a prompt that asks the model to grade the student's
    # response.  Include instructions about the grading rubric and
    # format.  Adjust according to your model's API.
    prompt = f"""
    You are grading a short answer question.  The ideal answer is:
    "{ideal_answer}"

    The student's answer is:
    "{student_answer}"

    Respond with a single number between 0 and {point_value} representing
    the score.  Do not provide explanations, only the number.
    """
    output = replicate.run(
        "meta/florence-2-large",  # specify the correct model slug
        input={"prompt": prompt}
    )
    # The API will return a string; convert to float
    try:
        return float(output.strip())
    except Exception:
        return 0.0
```

You will need to set your Replicate API token in the environment
variable `REPLICATE_API_TOKEN` before running the server.  See the
[Replicate documentation](https://replicate.com) for details.

## Limitations

* **No external dependencies can be installed.**  This environment
  does not allow `pip install` from the internet.  That is why this
  project uses FastAPI instead of Django and parses multipart form data
  manually.  When deploying on your own machine you can switch back
  to Django and install `python-multipart` to simplify form handling.
* **OCR quality.**  Text extraction uses PyMuPDF, which works well on
  typed PDFs.  For handwritten answers you may need to integrate an
  OCR engine (such as Tesseract or an AI model) to convert images to
  text before evaluation.
* **PDF segmentation.**  The function `split_answers` naively divides
  the extracted text into equal chunks.  Exams with varying answer
  lengths may require a more sophisticated segmentation strategy.

Despite these limitations, Grade Buddy AI demonstrates how to put
exam grading on autopilot.  Feel free to extend it to suit your
needs.
