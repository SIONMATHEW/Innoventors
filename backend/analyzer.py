"""
File: analyzer.py
Purpose: Handles AI-based text and PDF analysis using OpenAI API (standard, non-Azure).
"""

import os
import PyPDF2
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------------------------------------------
# Helper: Extract text from a PDF
# ------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text.strip()

# ------------------------------------------------------
# Main: Analyze text using OpenAI
# ------------------------------------------------------
def analyze_text(content: str) -> dict:
    """
    Uses OpenAI GPT to analyze input text and return structured insights.
    """
    prompt = f"""
    Analyze the following incident report text and extract these fields:

    - Root Cause
    - Summary (1–2 lines)
    - Recommended Corrective Action
    - Severity (Low/Medium/High)

    Text:
    {content}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",   # simple, cheap model for testing
        messages=[
            {"role": "system", "content": "You are an expert incident analyst."},
            {"role": "user", "content": prompt}
        ]
    )

    analysis = response.choices[0].message.content.strip()
    return {"analysis": analysis}
