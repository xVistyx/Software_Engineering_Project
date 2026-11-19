"""
Label crawled pages by hand with single key presses (used to measure how well the AI labels agree with you).

    python review_pages.py --limit 150        # label 150 random pages, then it stops by itself
    python review_pages.py                    # no limit, press q to stop whenever you want

For every page you see the topic, the title, the description and a study goal. You do NOT see the AI verdict.
    y   fine: this page would NOT distract from that study goal (do not block)
    n   no:   this page WOULD distract from that study goal (block)
    d   delete: the page does not match its topic label at all (hijacked domain, junk, bot check, ...)
    u   undo the last answer
    q   quit (progress is saved after every key press; run again to continue)

Answers go to data/page_reviews_<reviewer>.jsonl. Compare them with the AI labels using review_labels.py.
Several people can share the work: python review_pages.py --reviewer 2 --of 6
"""
import argparse, json, random, sys, textwrap
from pathlib import Path

script_dir = Path(__file__).resolve().parent
cfg = json.load(open(script_dir / "dataset_config.json"))
data_dir = script_dir / cfg["output_dir"]

BOLD, DIM, END = "\033[1m", "\033[2m", "\033[0m"


def getkey():
    """One key press, no Enter needed (falls back to a typed line when input is piped)."""
    if not sys.stdin.isatty():
        line = sys.stdin.readline()
        return line.strip().lower()[:1] if line else "q"
    import termios, tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if ch == "\x03":
        raise KeyboardInterrupt
    return ch.lower()


def wrap(text, indent="    "):
    return textwrap.fill(text, width=100, initial_indent=indent, subsequent_indent=indent) if text else indent + "(empty)"


def show(page, query, position, total, counts):
    topic_path = "/".join(page["label"].split("/")[2:])      # drop the leading /en/
    print("\n" + "=" * 100)
    print(f"{DIM}[{position}/{total}]   y {counts['y']}   n {counts['n']}   d {counts['d']}{END}")
    print(f"{BOLD}Topic:{END}       {page['topic']}   {DIM}({topic_path}){END}")
    print(f"{BOLD}Site:{END}        {page['final_url']}")
    print(f"{BOLD}Title:{END}")
    print(wrap(page["title"]))
    print(f"{BOLD}Description:{END}")
    print(wrap(page["description"]))
    print(f"{BOLD}Study goal:{END}  {query}")
    print(f"\n  y = not a distraction    n = distraction (block)    d = delete (does not match topic)    u = undo    q = quit")
    print("  > ", end="", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviewer", type=int, default=1)
    ap.add_argument("--of", type=int, default=1, help="how many reviewers share the work")
    ap.add_argument("--limit", type=int, default=None, help="stop after this many labelled pages in total")
    args = ap.parse_args()

    queries = json.load(open(script_dir / cfg["queries_path"]))
    topics = list(queries)
    pages = [json.loads(l) for l in open(data_dir / "pages.jsonl", encoding="utf-8") if l.strip()]
    pages.sort(key=lambda p: p["page_id"])
    random.Random(cfg["seed"]).shuffle(pages)                   # same order for everybody
    mine = pages[args.reviewer - 1:: args.of]
    if args.limit:
        mine = mine[: args.limit]

    out_path = data_dir / f"page_reviews_{args.reviewer}.jsonl"
    done = {}
    if out_path.exists():
        for l in open(out_path, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                done[r["page_id"]] = r["verdict"]
    counts = {k: sum(v == k for v in done.values()) for k in "ynd"}
    todo = [p for p in mine if p["page_id"] not in done]
    print(f"reviewer {args.reviewer}/{args.of}: {len(mine)} pages, {len(done)} already done, {len(todo)} to go")

    def query_for(page):
        r = random.Random(page["page_id"])                      # same query every time this page is shown
        t = page["topic"] if page["topic"] in queries else r.choice(topics)
        return r.choice(queries[t])

    history, i = [], 0
    with open(out_path, "a", encoding="utf-8") as f:
        try:
            while i < len(todo):
                p = todo[i]
                show(p, query_for(p), len(done) + 1, len(mine), counts)
                k = getkey()
                print(k if k.isprintable() else "")
                if k in ("y", "n", "d"):
                    f.write(json.dumps({"page_id": p["page_id"], "verdict": k, "reviewer": args.reviewer}) + "\n")
                    f.flush()
                    done[p["page_id"]] = k
                    counts[k] += 1
                    history.append(i)
                    i += 1
                elif k == "u" and history:
                    i = history.pop()
                    last = done.pop(todo[i]["page_id"])
                    counts[last] -= 1
                    f.close()
                    lines = open(out_path, encoding="utf-8").read().splitlines()[:-1]
                    open(out_path, "w", encoding="utf-8").write("".join(l + "\n" for l in lines))
                    f = open(out_path, "a", encoding="utf-8")
                elif k == "q":
                    break
        except KeyboardInterrupt:
            print("\nstopped")
        finally:
            f.close()
    print(f"\nsaved to {out_path.name}: y {counts['y']}, n {counts['n']}, d {counts['d']}, "
          f"{len(mine) - len(done)} left. Next: python review_labels.py")


if __name__ == "__main__":
    main()