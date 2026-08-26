"""
extractor.py
Pulls raw text/tables out of an uploaded PDF or Excel file.
This is the "input" half of the pipeline — dumb on purpose.
The LLM in agent.py is what turns this into structured line items.
"""

import pdfplumber
import openpyxl


def extract_text_from_pdf(filepath: str) -> str:
    """Concatenate text from every page. For scanned/image PDFs you will
    get little or nothing back — that's a TODO (see README: OCR fallback)."""
    chunks = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            chunks.append(text)

            # Tables are where the real financial numbers usually live.
            # extract_table() is naive — it will mis-align merged cells
            # and multi-line headers often found in annual reports.
            # TODO: improve table detection (see README).
            for table in page.extract_tables():
                for row in table:
                    row_text = " | ".join(cell or "" for cell in row)
                    chunks.append(row_text)
    return "\n".join(chunks)


def extract_text_from_excel(filepath: str) -> str:
    """Flatten every sheet into a plain text block of pipe-separated rows."""
    wb = openpyxl.load_workbook(filepath, data_only=True)
    chunks = []
    for sheet in wb.worksheets:
        chunks.append(f"--- Sheet: {sheet.title} ---")
        for row in sheet.iter_rows(values_only=True):
            row_text = " | ".join(str(c) if c is not None else "" for c in row)
            chunks.append(row_text)
    return "\n".join(chunks)


def extract_raw_content(filepath: str) -> str:
    if filepath.lower().endswith(".pdf"):
        return extract_text_from_pdf(filepath)
    elif filepath.lower().endswith((".xlsx", ".xlsm")):
        return extract_text_from_excel(filepath)
    else:
        raise ValueError(f"Unsupported file type: {filepath}")
