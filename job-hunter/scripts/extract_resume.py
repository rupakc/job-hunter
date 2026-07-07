#!/usr/bin/env python3
"""Extract raw text and page count from a resume (PDF/DOCX/TXT) into profile.json."""
import argparse, json, os, sys

LINES_PER_PAGE = 45

def estimate_pages_from_text(text: str) -> int:
    lines = text.count("\n") + 1
    return max(1, (lines + LINES_PER_PAGE - 1) // LINES_PER_PAGE)

def extract_pdf(path: str):
    import pdfplumber
    parts = []
    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts), page_count

def extract_docx(path: str):
    import docx
    doc = docx.Document(path)
    text = "\n".join(p.text for p in doc.paragraphs)
    return text, estimate_pages_from_text(text)

def extract_txt(path: str):
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return text, estimate_pages_from_text(text)

def extract(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text, pages = extract_pdf(path)
    elif ext == ".docx":
        text, pages = extract_docx(path)
    elif ext in (".txt", ".text"):
        text, pages = extract_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return {"source_path": os.path.abspath(path), "raw_text": text,
            "original_page_count": pages}

def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract resume text + page count")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default="profile.json")
    args = ap.parse_args(argv)
    result = extract(args.input)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(json.dumps({"page_count": result["original_page_count"],
                      "chars": len(result["raw_text"]), "output": args.output}))

if __name__ == "__main__":
    main()
