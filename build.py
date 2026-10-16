#!/usr/bin/env python3
"""Builds the NANO Updater site in place: one page per product, from template.html.

    python3 build.py

Every product in products.json gets <slug>/index.html, a copy of template.html stamped with
the template's id; products.json gets the same id as "page", so a page the browser or the CDN
kept from before reloads itself. The firmware in each folder (firmware.json + firmware/*.bin)
is not touched here: each product's own project publishes it (FX-DR2:
NANO-FX-DR/tools/web_updater/publish.sh). Commit and push the result; GitHub Pages serves it.
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main():
    template = (HERE / "template.html").read_text()
    page_id = hashlib.sha256(template.encode()).hexdigest()[:12]
    cat = json.loads((HERE / "products.json").read_text())
    for slug in cat["products"]:
        (HERE / slug).mkdir(exist_ok=True)
        (HERE / slug / "index.html").write_text(template.replace("__PAGE_ID__", page_id))
    cat["page"] = page_id
    (HERE / "products.json").write_text(json.dumps(cat, indent=2, ensure_ascii=False) + "\n")
    print(f"{len(cat['products'])} product pages, page id {page_id}")

if __name__ == "__main__":
    main()
