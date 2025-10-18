"""
File: analyzer.py
Purpose: AI-powered text & PDF analyzer for Innoventors backend (Azure OpenAI).
"""

import os
import re
from typing import List, Dict
from PyPDF2 import PdfReader
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts text from a PDF safely."""
    text = ""
    reader = PdfReader(file_path)
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    return text.strip()

_SECTION_PATTERN = re.compile(
    r"(?P<title>(?:Test\s*Case|Scenario)\s*\d+[^\n]*)\s*(?P<body>[\s\S]*?)(?=(?:Test\s*Case|Scenario)\s*\d+|\Z)",
    flags=re.IGNORECASE
)

def _split_sections(content: str) -> List[Dict[str, str]]:
    """
    Returns a list of sections like:
    [{"title": "Test Case 1 ...", "body": "..."}, ...]
    Falls back to one section if no headers found.
    """
    sections = [
        {"title": m.group("title").strip(), "body": (m.group("body") or "").strip()}
        for m in _SECTION_PATTERN.finditer(content)
    ]
    if not sections:
        sections = [{"title": "Incident 1", "body": content.strip()}]
    # Filter out tiny scraps
    sections = [s for s in sections if len(s["body"]) > 80]
    return sections

def analyze_text(content: str) -> dict:
    """
    For each section, call Azure OpenAI and return a list of {case, analysis}.
    """
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    sections = _split_sections(content)

    results = []
    for idx, sec in enumerate(sections, start=1):
        title = sec["title"] or f"Incident {idx}"
        prompt = f"""
        You are an expert in Product Operations and Root Cause Analysis.

        Analyze the following incident and provide:
        - Root Cause
        - Summary (1–2 lines)
        - Recommended Corrective Action
        - Severity (Low / Medium / High)

        Text:
        {sec["body"]}
        """
        try:
            resp = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": "You are a senior product incident analyst."},
                    {"role": "user", "content": prompt.strip()}
                ]
            )
            analysis = resp.choices[0].message.content.strip()
        except Exception as e:
            analysis = f"⚠️ AI analysis failed: {e}"

        results.append({"case": title, "analysis": analysis})

    return {"status": "success", "total_incidents": len(results), "analysis": results}
