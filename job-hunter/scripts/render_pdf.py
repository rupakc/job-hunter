#!/usr/bin/env python3
"""Render a resume (HTML or Jinja template + data JSON) to PDF via Chromium.
Exit code 2 signals the PDF exceeds the target page count (length overflow)."""
import argparse, json, os, pathlib, sys

def is_overflow(pages: int, target_pages) -> bool:
    return target_pages is not None and pages > target_pages

def build_html(template_path: str, data_path: str) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    tdir = os.path.dirname(os.path.abspath(template_path)) or "."
    env = Environment(loader=FileSystemLoader(tdir),
                      autoescape=select_autoescape(["html", "j2"]))
    tmpl = env.get_template(os.path.basename(template_path))
    with open(data_path, encoding="utf-8") as fh:
        data = json.load(fh)
    return tmpl.render(**data)

def count_pages(pdf_path: str) -> int:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)

def render(input_path: str, pdf_path: str, target_pages, data_path=None) -> dict:
    if input_path.endswith(".j2"):
        if not data_path:
            raise ValueError("Jinja template requires --data")
        html = build_html(input_path, data_path)
        html_path = os.path.splitext(pdf_path)[0] + ".html"
        pathlib.Path(html_path).write_text(html, encoding="utf-8")
    else:
        html_path = input_path
    from playwright.sync_api import sync_playwright
    uri = pathlib.Path(html_path).resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(uri, wait_until="networkidle")
        page.pdf(path=pdf_path, format="A4", print_background=True,
                 margin={"top": "14mm", "bottom": "14mm", "left": "16mm", "right": "16mm"})
        browser.close()
    pages = count_pages(pdf_path)
    return {"pdf_path": pdf_path, "page_count": pages, "target_pages": target_pages,
            "overflow": is_overflow(pages, target_pages), "html_path": html_path}

def main(argv=None):
    ap = argparse.ArgumentParser(description="Render resume HTML/template to PDF")
    ap.add_argument("input", help="path to .html or .j2 template")
    ap.add_argument("pdf", help="output PDF path")
    ap.add_argument("--data", default=None, help="JSON data for a .j2 template")
    ap.add_argument("--target-pages", type=int, default=None)
    args = ap.parse_args(argv)
    result = render(args.input, args.pdf, args.target_pages, args.data)
    print(json.dumps(result))
    sys.exit(2 if result["overflow"] else 0)

if __name__ == "__main__":
    main()
