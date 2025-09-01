#!/usr/bin/env python3
"""
Test script to verify multi-page PDF processing
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utility.utilities import extract_text_from_pdf

def test_pdf_processing(pdf_path):
    """Test the PDF processing function with a multi-page PDF"""
    print(f"Testing PDF processing for: {pdf_path}")
    print("=" * 60)
    
    try:
        # Extract text from all pages
        results = extract_text_from_pdf(pdf_path)
        
        print(f"\nProcessing completed successfully!")
        print(f"Total answers extracted: {len(results)}")
        print(f"Answer types: {[type(ans) for ans in results]}")
        print("\nExtracted answers:")
        for i, answer in enumerate(results):
            print(f"  {i+1}: {answer}")
            
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_pdf_processing.py <path_to_pdf>")
        print("Example: python test_pdf_processing.py uploads/your_pdf.pdf")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    test_pdf_processing(pdf_path)
