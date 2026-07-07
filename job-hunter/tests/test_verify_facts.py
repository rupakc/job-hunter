import importlib.util, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_facts.py"

def _load():
    spec = importlib.util.spec_from_file_location("verify_facts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_extract_numbers():
    m = _load()
    nums = m.extract_numbers("Grew revenue 40% in 2021 across 3 teams")
    assert "40" in nums and "2021" in nums and "3" in nums

def test_verify_passes_when_subset():
    m = _load()
    profile = {"raw_text": "Led 5 engineers, grew usage 40% in 2021. jane@x.com"}
    out = m.verify("Grew usage 40% in 2021 leading 5 engineers", profile)
    assert out["ok"] is True

def test_verify_flags_invented_metric():
    m = _load()
    profile = {"raw_text": "Grew usage 40% in 2021"}
    out = m.verify("Grew usage 250% in 2021", profile)
    assert out["ok"] is False
    assert "250" in out["new_numbers"]

def test_verify_flags_invented_email():
    m = _load()
    profile = {"raw_text": "Contact jane@x.com", "contact": {"email": "jane@x.com"}}
    out = m.verify("Contact fake@evil.com", profile)
    assert out["ok"] is False
    assert "fake@evil.com" in out["new_contacts"]
