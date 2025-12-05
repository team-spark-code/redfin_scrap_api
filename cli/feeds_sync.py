import os
import sys
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.feed_service import FeedService
from backend.core.config import PROJECT_ROOT

from argparse import ArgumentParser

def main():
    p = ArgumentParser()
    p.add_argument("--import-opml", type=str)
    p.add_argument("--export-opml", action="store_true")
    p.add_argument("--sync-yaml", action="store_true")
    p.add_argument("--delete-missing", action="store_true")
    args = p.parse_args()

    service = FeedService()

    if args.import_opml:
        bl = service.load_blacklist_urls()
        res = service.import_opml(PROJECT_ROOT / args.import_opml, blacklist=bl)
        print(res)

    if args.sync_yaml:
        res = service.sync_from_yaml(delete_missing=args.delete_missing)
        print(res)

    if args.export_opml:
        xml = service.export_opml()
        output_path = PROJECT_ROOT / "data" / "my_feeds.opml"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(xml, encoding="utf-8")
        print({"exported": True, "path": "data/my_feeds.opml", "length": len(xml)})

if __name__ == "__main__":
    main()
