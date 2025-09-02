import os
import sys
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.feeds_io import load_blacklist_urls, load_feeds_yaml, import_opml, export_opml, sync_from_yaml
from app.config import PROJECT_ROOT

from argparse import ArgumentParser

def main():
    p = ArgumentParser()
    p.add_argument("--import-opml", type=str)
    p.add_argument("--export-opml", action="store_true")
    p.add_argument("--sync-yaml", action="store_true")
    p.add_argument("--delete-missing", action="store_true")
    args = p.parse_args()

    if args.import_opml:
        bl = load_blacklist_urls()
        res = import_opml(PROJECT_ROOT / args.import_opml, blacklist=bl)
        print(res)

    if args.sync_yaml:
        res = sync_from_yaml(delete_missing=args.delete_missing)
        print(res)

    if args.export_opml:
        xml = export_opml(PROJECT_ROOT / "data" / "my_feeds.opml")
        print({"exported": True, "path": "data/my_feeds.opml", "length": len(xml)})

if __name__ == "__main__":
    main()
