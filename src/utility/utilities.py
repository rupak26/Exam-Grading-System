from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image 
from configuration.database_config import get_cursor
from configuration.florenc2_config import processor , model 
from langchain_community.llms import Replicate

from pdf2image import convert_from_path

import replicate , os
import json
import time


load_dotenv() 

# PyMuPDF (imported as fitz) allows us to extract text from PDF files.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
images_from_pdf = BASE_DIR / "images_from_pdf" 
images_from_pdf.mkdir(parents=True,exist_ok=True)

client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

def run_example(image , task_prompt, text_input=None):
    
    prompt = task_prompt if text_input is None else task_prompt + text_input

    inputs = processor(text=task_prompt, images=image, return_tensors="pt").to(model.device)

    generated_ids = model.generate(
        input_ids=inputs["input_ids"],          # no .cuda()
        pixel_values=inputs["pixel_values"],    # no .cuda()
        max_new_tokens=1024,
        early_stopping=False,
        do_sample=False,
        num_beams=3,
        use_cache=False
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed_answer = processor.post_process_generation(
        generated_text,
        task=task_prompt,
        image_size=image.size   # (width, height)
    )
    return parsed_answer

def extract_with_paddleocr(image_path: str) -> str:
    image = Image.open(image_path).convert("RGB")
    task_prompt = "<OCR_WITH_REGION>"
    ocr_ans = run_example(image, task_prompt)
    return ocr_ans

def extract_text_from_pdf(pdf_path: Path) -> list:
    pdf_path = Path(pdf_path).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if not os.access(pdf_path, os.R_OK):
        raise PermissionError(f"No read access to: {pdf_path}")

    images = convert_from_path(pdf_path)
    all_answers = []  

    for i, img in enumerate(images):
        timestamp = int(time.time() * 1000) + i  # Use milliseconds + page index for unique names
        image_path = os.path.join(images_from_pdf, f"page_{timestamp}.png")
        img.save(image_path, "PNG")
        
        try:
            value = extract_with_paddleocr(image_path)
            print(f"Raw OCR result for page {i+1}: {value}")
            if "<OCR_WITH_REGION>" not in value:
                print(f"Warning: Page {i+1} missing OCR_WITH_REGION key")
                continue
                
            ocr_data = value["<OCR_WITH_REGION>"]
            print("=========================================================")
            print(f"Page {i+1} OCR data:")
            print(ocr_data)
            print("=========================================================")
   
            # Extract answers from this page
            if "labels" not in ocr_data:
                print(f"Warning: Page {i+1} missing labels key in OCR data")
                continue
                
            page_answers = ocr_data["labels"]
            if isinstance(page_answers, list):
                all_answers.extend(page_answers)
                print(f"Page {i+1}: Added {len(page_answers)} answers")
            else:
                all_answers.append(page_answers)
                print(f"Page {i+1}: Added 1 answer")
                
        except Exception as e:
            print(f"Error processing page {i+1}: {e}")
            continue
        finally:
            # Clean up the temporary image file
            try:
                os.remove(image_path)
            except:
                pass

    print(f"Total answers extracted from {len(images)} pages: {len(all_answers)}")
    return all_answers

def evaluate_answer(student_answer: str, ideal_answer: str, point_value: float) -> float:
    prompt = f"""
    You are grading a short answer question.  The ideal answer is:
    "{ideal_answer}"

    The student's answer is:
    "{student_answer}"

    Respond with a single number between 0 and {point_value} representing
    the score.  Do not provide explanations, only the number.
    """
    output = client.run(
        "meta/meta-llama-3-8b-instruct",
        input={"prompt": prompt}
    )
  
    # The API will return a string; convert to float
    try:
        return float(output[1])
    except Exception:
        return 0.0
    

def evaluate_answer_sheet(pdf_path: Path , answer_sheet_id: int) -> None:
    conn , cursor = get_cursor()
    # Retrieve answer sheet and associated student
    cursor.execute(
        "SELECT answer_sheets.*, students.exam_id FROM answer_sheets JOIN students ON answer_sheets.student_id = students.id WHERE answer_sheets.id = ?",
        (answer_sheet_id,)
    )
    sheet = cursor.fetchone()
    if sheet is None:
        conn.close()
        raise ValueError(f"Answer sheet {answer_sheet_id} not found")
    
    # pdf_path = Path(__file__).parent / "uploads" / sheet["filename"]
    extracted_text = extract_text_from_pdf(pdf_path)
    # extracted_text is now a list of all answers from all pages
    all_answers = extracted_text
    
    cursor.execute(
        "SELECT id, text, ideal_answer, point_value FROM questions WHERE exam_id = %s ORDER BY id",
        (sheet["exam_id"],)
    )
    questions = cursor.fetchall()
    questions = [dict(row) for row in questions]
    
    # Ensure we have enough answers for all questions
    if len(all_answers) < len(questions):
        print(f"Warning: Only {len(all_answers)} answers found for {len(questions)} questions")
        # Pad with empty answers if needed
        all_answers.extend([""] * (len(questions) - len(all_answers)))
    elif len(all_answers) > len(questions):
        print(f"Warning: {len(all_answers)} answers found for {len(questions)} questions, truncating")
        all_answers = all_answers[:len(questions)]
    
    total_score = 0.0
    # Delete previous evaluations for this answer sheet if any
    cursor.execute("DELETE FROM answers WHERE answer_sheet_id = ?", (answer_sheet_id,))
    
    # Evaluate each answer
    for i, (question, student_answer) in enumerate(zip(questions, all_answers)):
        print("==========================================================")
        print(f"Question {i+1}: {question['text']}")
        print(f"Student Answer: {student_answer}")
        print(f"Ideal Answer: {question['ideal_answer']}")
        print("==========================================================")
        
        # Clean the student answer
        if isinstance(student_answer, str):
            student_answer = student_answer.replace("</s>", "").replace("<s>", "").strip()
        else:
            student_answer = str(student_answer)
        
        score = evaluate_answer(student_answer, question["ideal_answer"], question["point_value"])
        total_score += score
        
        cursor.execute(
            """INSERT INTO answers (answer_sheet_id, question_id, student_answer, score)
            VALUES (?, ?, ?, ?)""",
            (answer_sheet_id, question["id"], student_answer, score),
        )
    cursor.execute(
        """UPDATE answer_sheets SET extracted_text = ?, evaluated_at = ?, total_score = ? WHERE id = ?""",
        (", ".join(str(answer) for answer in extracted_text), datetime.now(timezone.utc).isoformat(), total_score, answer_sheet_id),
    )
    conn.commit()
    conn.close()
    