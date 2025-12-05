import os
import sys 
import xml.etree.ElementTree as ET

from backend.services.reader_service import ReaderService

def import_opml(path: str):
    r = ReaderService.get_reader()
    added = skipped = 0
    for o in ET.parse(path).iter("outline"):
        url = o.attrib.get("xmlUrl")
        if not url:
            continue
        try:
            r.add_feed(url)
            added += 1
        except Exception:
            skipped += 1
    # 최초 업데이트
    r.update_feeds()
    print({"added": added, "skipped": skipped})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cli/opml_import.py <file.opml>")
        sys.exit(1)
    import_opml(sys.argv[1])
