import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import re
import os

# Configure tesseract path if it's not in your PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def is_text_meaningful(text):
    """
    Check if the extracted text is meaningful.
    This is a simple check based on text length and character variety.
    """
    if not text or len(text.strip()) < 100:  # Heuristic: require at least 100 characters
        return False
    
    # Check for a variety of characters (not just gibberish)
    unique_chars = set(text.strip())
    if len(unique_chars) < 10:
        return False
        
    return True

def ocr_page(page_image):
    """
    Perform OCR on a single page image.
    """
    return pytesseract.image_to_string(page_image)

def parse_text_for_transactions(text):
    """
    A more robust regex-based parser to find transactions in the text.
    This will need to be adapted to the specific format of your bank statements.
    """
    transactions = []
    
    # This is a generic regex and will likely need to be adjusted.
    # It looks for a date, a description, and an amount.
    # Format: DD/MM/YYYY Description Text Amount
    transaction_regex = re.compile(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})')
    
    for line in text.split('\n'):
        match = transaction_regex.search(line)
        if match:
            date = match.group(1)
            description = match.group(2).strip()
            amount = float(match.group(3).replace(',', ''))
            
            transactions.append({
                "date": date,
                "description": description,
                "amount": amount
            })
            
    return transactions

def parse_pdf_robust(file_path):
    """
    Parses a PDF file for transactions using a robust pipeline.
    1. Tries text extraction with PyMuPDF.
    2. If text is not meaningful, falls back to OCR.
    3. Parses the extracted text to find transactions.
    """
    transactions = []

    try:
        # Using a temporary file path
        temp_pdf_path = "temp_pdf_file.pdf"
        with open(temp_pdf_path, "wb") as f:
            f.write(file_path.getbuffer())

        # --- Step 1: Try text extraction with PyMuPDF ---
        doc = fitz.open(temp_pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        if is_text_meaningful(full_text):
            transactions = parse_text_for_transactions(full_text)

        # --- Step 2: If text is not meaningful, fall back to OCR ---
        if not transactions:
            images = convert_from_path(temp_pdf_path)
            ocr_text = ""
            for image in images:
                ocr_text += ocr_page(image)
            
            if is_text_meaningful(ocr_text):
                transactions = parse_text_for_transactions(ocr_text)

    finally:
        if os.path.exists("temp_pdf_file.pdf"):
            os.remove("temp_pdf_file.pdf")

    return pd.DataFrame(transactions)
