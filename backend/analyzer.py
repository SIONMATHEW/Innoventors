"""
File: analyzer.py
Purpose: AI-powered text & PDF analyzer for Innoventors backend (Azure OpenAI).
"""

import os
import re
import time
import json
from typing import List, Dict
from PyPDF2 import PdfReader
from openai import AzureOpenAI
from dotenv import load_dotenv

# ------------------------------------------------------
# Environment Setup
# ------------------------------------------------------
load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# Optional sanity check
for var in ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_VERSION"]:
    if not os.getenv(var):
        print(f"⚠️ Warning: Missing environment variable {var}")

# ------------------------------------------------------
# Utility: Extract text from PDF
# ------------------------------------------------------
def extract_text_from_pdf(file_path: str) -> str:
    """Safely extract text from a PDF file."""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
    except Exception as e:
        print(f"⚠️ PDF extraction failed: {e}")
    return text.strip()

# ------------------------------------------------------
# Text Cleaning Utilities
# ------------------------------------------------------
def clean_text(text: str) -> str:
    """Remove weird mid-word spacing and normalize spaces."""
    if not text:
        return ""
    text = re.sub(r"(?<=\w)\s(?=\w)", "", text)  # remove intra-word gaps
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_title(title: str) -> str:
    """
    Clean and properly format titles like 'test case 1 (email escalated from l1 support)'.
    """
    if not title:
        return ""
    title = clean_text(title)

    # Insert missing spaces like: Case1 → Case 1, (Email→ (Email
    title = re.sub(r"(?<=Case)(\d)", r" \1", title)
    title = re.sub(r"(?<=\d)(?=\()", " ", title)

    # Capitalize words but preserve acronyms (L1, PDF)
    words = title.split()
    result = []
    for w in words:
        if len(w) > 1 and w.isupper():  # preserve acronyms
            result.append(w)
        else:
            result.append(w.capitalize())
    return " ".join(result)


# ------------------------------------------------------
# Split multi-incident PDFs
# ------------------------------------------------------
def _split_sections(content: str) -> List[Dict[str, str]]:
    """
    Split text into sections like [{"title": "...", "body": "..."}].
    Recognizes headings like "Test Case 1" or "Scenario 2".
    """
    lines = content.splitlines()
    sections = []
    current = {"title": "", "body": ""}

    for line in lines:
        if re.match(r"(?i)(test\s*case\s*\d+|scenario\s*\d+)", line.strip()):
            if current["title"] or current["body"]:
                sections.append(current)
                current = {"title": "", "body": ""}
            current["title"] = line.strip()
        else:
            current["body"] += line.strip() + " "

    if current["title"] or current["body"]:
        sections.append(current)

    # Clean up each section
    for sec in sections:
        sec["title"] = normalize_title(sec["title"])
        sec["body"] = clean_text(sec["body"])

    return sections

# ------------------------------------------------------
# Optional Field Coercion (placeholder for backend use)
# ------------------------------------------------------
def _coerce_to_fields(ai_json: str) -> dict:
    """
    Ensure AI output has expected fields even if model response is partial.
    """
    try:
        data = json.loads(ai_json)
        return {
            "summary": data.get("summary", "N/A"),
            "root_cause": data.get("root_cause", "N/A"),
            "recommendation": data.get("recommendation", "N/A"),
            "category": data.get("category", "Uncategorized"),
            "severity": data.get("severity", "Unknown"),
        }
    except Exception:
        return {
            "summary": "Invalid AI output",
            "root_cause": "Parsing failed",
            "recommendation": "Manual review required",
            "category": "Error",
            "severity": "Unknown",
        }

# ------------------------------------------------------
# AI Analysis Core
# ------------------------------------------------------
def analyze_text(content: str, retries: int = 2, delay: int = 2) -> dict:
    """
    Analyze each section using Azure OpenAI and return structured JSON results.
    Retries automatically if model output is invalid.
    """
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    sections = _split_sections(content)
    results = []

    for idx, sec in enumerate(sections, start=1):
        title = sec["title"] or f"Incident {idx}"
        body = sec["body"]

        prompt = f"""
        You are a senior product operations and incident management analyst.
        Analyze the following incident and return a detailed root cause analysis
        STRICTLY in valid JSON with the following keys:
        - summary
        - root_cause
        - recommendation
        - category
        - severity (Low / Medium / High)

        Incident Title: {title}

        Incident Text:
        {body}
        """

        response_text = ""
        for attempt in range(1, retries + 1):
            try:
                resp = client.chat.completions.create(
                    model=deployment,
                    messages=[
                        {"role": "system", "content": "You are an expert RCA analyst. Always reply in valid JSON."},
                        {"role": "user", "content": prompt.strip()},
                    ],
                    temperature=0.2,
                )
                response_text = resp.choices[0].message.content.strip()
                json.loads(response_text)  # Validate JSON
                break
            except Exception as e:
                print(f"⚠️ Attempt {attempt} failed: {e}")
                if attempt < retries:
                    time.sleep(delay)
                    prompt += "\n\n⚠️ Please output valid JSON only."
                else:
                    response_text = json.dumps({
                        "summary": body[:150],
                        "root_cause": f"AI parsing failed after {retries} attempts.",
                        "recommendation": "Manual review required.",
                        "category": "Error",
                        "severity": "Unknown"
                    })

        results.append({"case": title, "analysis": response_text})

    return {
        "status": "success",
        "total_incidents": len(results),
        "analysis": results
    }
