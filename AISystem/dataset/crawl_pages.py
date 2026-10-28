"""
Stage 2: fetch every link in data/links.csv, keep the pages that really load.

Output:  data/pages.jsonl          one JSON record per kept page (page_id == link_id)
         data/crawl_failures.csv   every dropped link and the reason

Resumable: links already in either file are skipped, so you can stop (Ctrl+C) and rerun.
Test first:   python 2_crawl_pages.py --limit 50
Full run:     python 2_crawl_pages.py

pip install requests beautifulsoup4 py3langid
"""
import argparse, csv, json, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

from page_fields import extract_fields, is_bad_title, is_parked, detect_language

script_dir = Path(__file__).resolve().parent
cfg = json.load(open(script_dir / "dataset_config.json"))
data_dir = script_dir / cfg["output_dir"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = (5, 10)          # connect and read 
MAX_BYTES = 300_000        # title/meta are at the top


def candidate_urls(url):
    """Try the url as given; if https fails (many old sites), retry once over http."""
    yield url
    if url.startswith("https://"):
        yield "http://" + url[len("https://"):]


def fetch_html(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True, allow_redirects=True)
    try:
        ctype = r.headers.get("Content-Type", "").lower()
        if r.status_code != 200 or (ctype and "html" not in ctype):
            return r.status_code, r.url, ctype, b""
        raw, size = [], 0
        for chunk in r.iter_content(16384):
            raw.append(chunk)
            size += len(chunk)
            if size >= MAX_BYTES:
                break
        return r.status_code, r.url, ctype, b"".join(raw)
    finally:
        r.close()


def process(link):
    """Returns (record, None) if the page is kept, else (None, (link_id, url, reason))."""
    fail = lambda reason: (None, (link["link_id"], link["url"], reason))
    last_err = None
    for u in candidate_urls(link["url"]):
        try:
            status, final_url, ctype, raw = fetch_html(u)
            break
        except requests.RequestException as e:
            last_err = type(e).__name__
    else:
        return fail(f"fetch_error:{last_err}")

    if status != 200:
        return fail(f"http_{status}")
    if not raw:
        return fail("not_html")

    f = extract_fields(raw)
    if not f["title"]:
        return fail("no_title")
    if is_bad_title(f["title"]):
        return fail("bad_title")
    if is_parked(f):
        return fail("parked")
    lang = detect_language(f)
    if lang != "en":
        return fail(f"not_english:{lang}")

    return {
        "page_id": link["link_id"],
        "uid": link["uid"],
        "url": link["url"],
        "final_url": final_url,
        "domain": link["domain"],
        "final_domain": urlparse(final_url).netloc.lower().removeprefix("www."),
        "label": link["label"],
        "topic": link["topic"],
        "role": link["role"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "http_status": status,
        "lang": lang,
        **f,
    }, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only process the first N unprocessed links")
    ap.add_argument("--workers", type=int, default=32)
    args = ap.parse_args()

    pages_path = data_dir / "pages.jsonl"
    fail_path = data_dir / "crawl_failures.csv"

    links = pd.read_csv(data_dir / "links.csv", dtype=str).fillna("")
    done = set()
    if pages_path.exists():
        done |= {json.loads(l)["page_id"] for l in open(pages_path, encoding="utf-8") if l.strip()}
    if fail_path.exists():
        done |= set(pd.read_csv(fail_path, dtype=str)["link_id"])
    todo = [r for r in links.to_dict("records") if r["link_id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(links)} links, {len(done)} already processed, {len(todo)} to do")

    new_file = not fail_path.exists()
    reasons, kept, start = Counter(), 0, time.time()
    with open(pages_path, "a", encoding="utf-8") as pf, \
         open(fail_path, "a", newline="", encoding="utf-8") as ff, \
         ThreadPoolExecutor(args.workers) as pool:
        fw = csv.writer(ff)
        if new_file:
            fw.writerow(["link_id", "url", "reason"])
        futures = [pool.submit(process, r) for r in todo]
        try:
            for i, fut in enumerate(as_completed(futures), 1):
                rec, fail = fut.result()
                if rec:
                    pf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    pf.flush()
                    kept += 1
                else:
                    fw.writerow(fail)
                    ff.flush()
                    reasons[fail[2].split(":")[0]] += 1
                if i % 100 == 0:
                    print(f"  {i}/{len(todo)} done, {kept} kept, {time.time() - start:.0f}s")
        except KeyboardInterrupt:
            print("stopped; rerun to resume")
            pool.shutdown(wait=False, cancel_futures=True)

    print(f"\nkept {kept}; dropped {sum(reasons.values())}")
    for reason, n in reasons.most_common():
        print(f"  {reason:15s} {n}")
    if pages_path.exists():
        pages = pd.read_json(pages_path, lines=True)
        print("\npages kept so far, per topic:")
        print(pages.groupby(["role", "topic"]).size().to_string())


if __name__ == "__main__":
    main()