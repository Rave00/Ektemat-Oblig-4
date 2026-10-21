"""No personal e-mail addresses in the repository (CLAUDE.md, team rules).

Every e-mail address in a text file must use a reserved example domain (RFC 2606: example.com, example.org,
example.net, or a name ending in .example), so real addresses of group members or customers never get committed.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", ".venv", "venv", "instance", "__pycache__", ".pytest_cache", "node_modules"}
TEXT = {".py", ".md", ".html", ".css", ".js", ".sql", ".txt", ".toml", ".json", ".puml", ".bpmn", ".example", ""}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
ALLOWED = re.compile(r"(^|\.)example\.(com|org|net)$|\.example$|^example$", re.I)
# Commit attribution lines and documentation of tools may name these service addresses.
SERVICE = {"noreply@anthropic.com", "noreply@github.com"}


def text_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not SKIP & set(path.relative_to(ROOT).parts) and path.suffix in TEXT:
            yield path


def test_only_example_e_mail_addresses_are_committed():
    found = []
    for path in text_files():
        for match in EMAIL.finditer(path.read_text(encoding="utf-8", errors="ignore")):
            if match.group(0).lower() not in SERVICE and not ALLOWED.search(match.group(1)):
                found.append(f"{path.relative_to(ROOT)}: {match.group(0)}")
    assert found == [], found


def test_the_check_recognises_a_personal_address():
    assert not ALLOWED.search("gmail.com") and not ALLOWED.search("uib.no")
    assert ALLOWED.search("example.com") and ALLOWED.search("ektemat.example") and ALLOWED.search("test.example")
