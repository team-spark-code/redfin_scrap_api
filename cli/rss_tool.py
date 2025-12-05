# cli/rss_tool.py
import argparse, json, sys
from backend.services.crawler_service import CrawlerService
from backend.services.feed_service import FeedService
from backend.core.config import DISCOVER_TARGETS

def run():
    p = argparse.ArgumentParser("rss_tool")
    sp = p.add_subparsers(dest="cmd", required=True)

    sp.add_parser("init")
    sp.add_parser("update")
    sp.add_parser("init-indexes", help="MongoDB 인덱스 초기화")

    d = sp.add_parser("discover")
    d.add_argument("--url", default=None)
    d.add_argument("--top-k", type=int, default=3)

    s = sp.add_parser("stats")
    s.add_argument("--days", type=int, default=7)
    s.add_argument("--out", default=None)

    args = p.parse_args()

    crawler = CrawlerService()
    feed_service = FeedService()
    
    if args.cmd == "init":
        print(crawler.init_feeds())
    elif args.cmd == "update":
        print(crawler.update_all())
    elif args.cmd == "discover":
        if args.url:
            print(feed_service.discover_feeds(args.url, args.top_k))
        else:
            out = [feed_service.discover_feeds(u, args.top_k) for u in DISCOVER_TARGETS]
            print(out)
    elif args.cmd == "stats":
        res = crawler.get_stats(args.days)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f: json.dump(res, f, ensure_ascii=False, indent=2)
        print(res)
    elif args.cmd == "init-indexes":
        from cli.init_indexes import init_all_indexes
        success = init_all_indexes()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    run()
