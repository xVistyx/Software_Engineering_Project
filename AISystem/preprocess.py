def preprocess(page: dict) -> str:
    """Turn a page's fields into the text block the model sees. Empty fields are skipped."""
    parts = []
    if page.get("title"):
        parts.append(f"Title of the page: {page['title']}")
    if page.get("description"):
        parts.append(f"Description of the page: {page['description']}")
    return "\n".join(parts)

