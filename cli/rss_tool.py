# cli/rss_tool.py
import argparse, json, sys
from app.rss_core import init_feeds, update_all, add_discovered_feeds, stats
from app.config import DISCOVER_TARGETS

def run():
    p = argparse.ArgumentParser("rss_tool")
    sp = p.add_subparsers(dest="cmd", required=True)

    sp.add_parser("init")
    sp.add_parser("update")

    d = sp.add_parser("discover")
    d.add_argument("--url", default=None)
    d.add_argument("--top-k", type=int, default=3)

    s = sp.add_parser("stats")
    s.add_argument("--days", type=int, default=7)
    s.add_argument("--out", default=None)

    args = p.parse_args()

    if args.cmd == "init":
        print(init_feeds())
    elif args.cmd == "update":
        print(update_all())
    elif args.cmd == "discover":
        if args.url:
            print(add_discovered_feeds(args.url, args.top_k))
        else:
            out = [add_discovered_feeds(u, args.top_k) for u in DISCOVER_TARGETS]
            print(out)
    elif args.cmd == "stats":
        res = stats(args.days)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f: json.dump(res, f, ensure_ascii=False, indent=2)
        print(res)

if __name__ == "__main__":
    run()
