"""
File: analyzer.py
Purpose: Robust AI-powered text & PDF analyzer for Innoventors backend (v3).
Now guarantees detailed, structured JSON output for each Test Case or Scenario.
"""

import os
import re
import json
import time
from typing import List, Dict
from PyPDF2 import PdfReader
from openai import AzureOpenAI
from dotenv import load_dotenv

# Debug flag to print PDF splits
DEBUG_MODE = True


load_dotenv()

# ------------------------------------------------------------
# Azure OpenAI client
# ------------------------------------------------------------
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# ------------------------------------------------------------
# PDF Utilities
# ------------------------------------------------------------
def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF, page by page."""
    text = ""
    reader = PdfReader(file_path)
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    return text.strip()

# ------------------------------------------------------------
# Section Splitter
# ------------------------------------------------------------
_SECTION_PATTERN = re.compile(
    r"(?P<title>(?:Test\s*Case|Scenario)\s*\d+[^\n]*)\s*(?P<body>[\s\S]*?)(?=(?:Test\s*Case|Scenario)\s*\d+|\Z)",
    flags=re.IGNORECASE
)

def _split_sections(content: str) -> List[Dict[str, str]]:
    """
    Split content into sections based on 'Test Case' or 'Scenario' markers.
    Always returns at least one section.
    """
    sections = [
        {"title": m.group("title").strip(), "body": (m.group("body") or "").strip()}
        for m in _SECTION_PATTERN.finditer(content)
    ]
    if not sections:
        sections = [{"title": "Incident 1", "body": content.strip()}]

    for s in sections:
        if not s["body"] or len(s["body"]) < 10:
            s["body"] = (s["body"] or "") + "\n(Note: Minimal text detected. Parsed from PDF.)"

    if DEBUG_MODE:
        print("\n🧩 === PDF SPLIT DEBUG ===")
        for idx, s in enumerate(sections, 1):
            print(f"\nCase {idx}: {s['title']}\n{'-'*60}")
            print(s["body"][:1000])  # Print up to 1000 chars for clarity
            print("\n")

    return sections

# ------------------------------------------------------------
# Structured JSON Parser Helper
# ------------------------------------------------------------
def _extract_between(text: str, start_pat: str, end_pat: str) -> str:
    s = re.search(start_pat, text, flags=re.IGNORECASE)
    if not s:
        return None
    start = s.end()
    e = re.search(end_pat, text[start:], flags=re.IGNORECASE)
    if not e:
        return text[start:]
    return text[start:start + e.start()]

def _coerce_to_fields(free_text: str) -> dict:
    """Extract structured fields from AI free-text (fallback if JSON fails)."""
    try:
        maybe = json.loads(free_text)
        if isinstance(maybe, dict):
            return {
                "root_cause": maybe.get("root_cause"),
                "summary": maybe.get("summary"),
                "recommendation": maybe.get("recommendation"),
                "category": maybe.get("category"),
                "severity": maybe.get("severity"),
            }
    except Exception:
        pass

    rc = _extract_between(free_text, r"(Root\s*Cause[:\-])", r"(Summary|Recommendation|Severity|Category|$)")
    sm = _extract_between(free_text, r"(Summary[:\-])", r"(Recommendation|Severity|Category|$)")
    rec = _extract_between(free_text, r"(Recommendation[:\-])", r"(Severity|Category|$)")
    sev = _extract_between(free_text, r"(Severity[:\-])", r"(Category|$)")
    cat = _extract_between(free_text, r"(Category[:\-])", r"$")

    def clean(x): return x.strip(" \n-:") if x else None

    if not any([rc, sm, rec, sev, cat]):
        return {"root_cause": None, "summary": free_text.strip(), "recommendation": None, "category": None, "severity": None}

    return {
        "root_cause": clean(rc),
        "summary": clean(sm),
        "recommendation": clean(rec),
        "category": clean(cat),
        "severity": clean(sev)
    }

# ------------------------------------------------------------
# AI Analysis Logic (robust)
# ------------------------------------------------------------
def analyze_text(content: str, retries: int = 2, delay: int = 2) -> dict:
    """
    Analyze each section using Azure OpenAI and return detailed JSON results.
    Retries automatically if the model returns invalid or empty output.
    """
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    sections = _split_sections(content)
    results = []

    for idx, sec in enumerate(sections, start=1):
        title = sec["title"]
        body = sec["body"]

        base_prompt = f"""
        You are a senior product operations and incident management analyst.
        Analyze the following incident and return a detailed root cause analysis
        STRICTLY in valid JSON with the following keys:
        - root_cause
        - summary
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
                        {"role": "system", "content": "You are an expert RCA analyst. Always reply in JSON."},
                        {"role": "user", "content": base_prompt.strip()},
                    ],
                    temperature=0.2,
                )
                response_text = resp.choices[0].message.content.strip()
                # Try parsing JSON to verify validity
                json.loads(response_text)
                break  # valid JSON → break retry loop
            except Exception:
                if attempt < retries:
                    time.sleep(delay)
                    base_prompt += "\n\n⚠️ Please output valid JSON only."
                else:
                    response_text = f'{{"root_cause": "AI parsing failed after {retries} attempts.", "summary": "{body[:150]}", "recommendation": "Manual review required.", "category": "Error", "severity": "Unknown"}}'

        results.append({"case": title, "analysis": response_text})

    return {"status": "success", "total_incidents": len(results), "analysis": results}
