def preprocess(page: dict) -> str:
    """Turn a page's fields into the text block the model sees. Empty fields are skipped."""
    parts = []
    if page.get("title"):
        parts.append(f"Title of the page: {page['title']}")
    if page.get("description"):
        parts.append(f"Description of the page: {page['description']}")
    return "\n".join(parts)


if __name__ == "__main__":
    # quick manual check:  python preprocess.py
    print(preprocess({"title": "Contract law - Wikipedia", "description": "", "block": None}))