"""
Shared helpers for turning a fetched page into the fields the model uses.
Only reports what it finds; 2_crawl_pages.py decides what to keep.

pip install beautifulsoup4 py3langid        (lxml is optional, makes parsing faster)
"""
import re
from bs4 import BeautifulSoup
import py3langid

try:
    import py3langid
except ImportError:          # language detection is optional; we then rely on <html lang>
    py3langid = None

BAD_TITLE = re.compile(
    r"^(untitled( document| page)?|home( page)?|welcome|loading\.*|index( of.*)?|"
    r"404.*|403.*|error.*|.*not found.*|just a moment.*|access denied.*|"
    r"attention required.*|forbidden.*|redirecting.*|default web site page|"
    r"welcome to nginx.*|apache.*test page.*|site under construction.*|coming soon)$",
    re.I,
)
PARKED_HINTS = (
    "domain is for sale", "domain for sale", "buy this domain", "this domain may be for sale",
    "this domain has expired", "domain parking", "parked domain", "hugedomains",
    "this web page is parked", "account suspended", "website expired", "sedo",
)


def clean(s, n):
    return re.sub(r"\s+", " ", s or "").strip()[:n]


def extract_fields(html):
    """html: bytes or str. Returns a dict of short text fields."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    def meta(**attrs):
        tag = soup.find("meta", attrs=attrs)
        return clean(tag.get("content") if tag else "", 300)

    title = clean(soup.title.get_text() if soup.title else "", 200)
    description = meta(name="description") or meta(property="og:description")
    h1 = [clean(h.get_text(), 120) for h in soup.find_all("h1")[:3] if h.get_text().strip()]

    snippet = ""
    for p in soup.find_all("p"):
        if p.find_parent(["nav", "header", "footer", "aside", "form"]):
            continue
        t = clean(p.get_text(), 400)
        if len(t) < 40:
            continue
        snippet += t + " "
        if len(snippet) >= 800:
            break

    html_tag = soup.find("html")
    return {
        "title": title,
        "description": description,
        "h1": h1,
        "snippet": clean(snippet, 800),
        "html_lang": clean(html_tag.get("lang") if html_tag else "", 10).lower(),
    }


def is_bad_title(title):
    return bool(BAD_TITLE.match(title.strip()))


def is_parked(fields):
    text = f"{fields['title']} {fields['description']} {fields['snippet'][:300]}".lower()
    return any(h in text for h in PARKED_HINTS)


def detect_language(fields):
    """Language code of the page text. <html lang> alone is unreliable, so use the detector when there is enough text."""
    text = f"{fields['title']}. {fields['description']}. {fields['snippet'][:300]}"
    if py3langid is not None and len(text) >= 25:
        return py3langid.classify(text)[0]
    return (fields["html_lang"] or "unknown")[:2]