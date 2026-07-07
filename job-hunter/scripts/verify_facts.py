#!/usr/bin/env python3
"""Fail (exit 1) if a tailored resume introduces numeric facts or contacts
absent from the original profile. Anti-hallucination gate."""
import argparse, json, re, sys

_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")

def _norm_num(tok: str) -> str:
    return tok.replace(",", "").rstrip(".").lstrip("0") or "0"

def extract_numbers(text: str) -> set:
    return {_norm_num(m.group()) for m in _NUM_RE.finditer(text)}

def _norm_phone(tok: str) -> str:
    return re.sub(r"\D", "", tok)

def extract_contacts(text: str) -> dict:
    return {"emails": {e.lower() for e in _EMAIL_RE.findall(text)},
            "phones": {_norm_phone(p) for p in _PHONE_RE.findall(text)}}

def verify(tailored_text: str, profile: dict) -> dict:
    original = profile.get("raw_text", "")
    orig_nums = extract_numbers(original)
    new_numbers = sorted(extract_numbers(tailored_text) - orig_nums)

    orig_c = extract_contacts(original)
    tail_c = extract_contacts(tailored_text)
    new_emails = tail_c["emails"] - orig_c["emails"]
    new_phones = tail_c["phones"] - orig_c["phones"]
    new_contacts = sorted(new_emails) + sorted(new_phones)

    return {"ok": not new_numbers and not new_contacts,
            "new_numbers": new_numbers, "new_contacts": new_contacts}

def main(argv=None):
    ap = argparse.ArgumentParser(description="Anti-hallucination fact verifier")
    ap.add_argument("--tailored", required=True, help="tailored resume text file")
    ap.add_argument("--profile", required=True, help="profile.json path")
    args = ap.parse_args(argv)
    with open(args.tailored, encoding="utf-8") as fh:
        tailored = fh.read()
    with open(args.profile, encoding="utf-8") as fh:
        profile = json.load(fh)
    result = verify(tailored, profile)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)

if __name__ == "__main__":
    main()
