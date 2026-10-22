"""Download the official web pages listed in data/sources.json into data/raw.

Each page is saved as Markdown-like text with a small header containing the
title, URL, authority and download date, so answers can cite their source.

Usage:  python scripts/fetch_sources.py
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_settings  # noqa: E402

HEADERS = {"User-Agent": "Mozilla/5.0 (student project: Finland Bureaucracy Helper)"}
REMOVE_TAGS = ["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg", "button"]
MIN_TEXT_CHARS = 400


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(REMOVE_TAGS):
        tag.decompose()
    for selector in ['[class*="cookie"]', '[id*="cookie"]', '[class*="breadcrumb"]', '[class*="share"]']:
        for tag in soup.select(selector):
            tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup

    blocks: list[str] = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "td"]):
        if el.find(["p", "li"]):  # skip containers; their children are visited separately
            continue
        text = " ".join(el.get_text(" ", strip=True).split())
        if len(text) < 3:
            continue
        if el.name in ("h1", "h2", "h3", "h4"):
            blocks.append(f"## {text}")
        elif el.name == "li":
            blocks.append(f"- {text}")
        else:
            blocks.append(text)

    # Drop repeated lines (menus, "Read more" links, etc.)
    seen, unique = set(), []
    for b in blocks:
        if b not in seen:
            seen.add(b)
            unique.append(b)
    return "\n\n".join(unique)


def main() -> int:
    settings = load_settings()
    sources = json.loads(settings.sources_path.read_text(encoding="utf-8"))
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    ok = 0

    for src in sources:
        url, title, authority = src["url"], src["title"], src["authority"]
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  FAILED  {url}: {exc}")
            continue
        text = extract_text(resp.text)
        if len(text) < MIN_TEXT_CHARS:
            print(f"  SKIPPED {url}: only {len(text)} characters of text extracted")
            continue
        path = settings.raw_dir / f"{slugify(authority + '-' + title)}.md"
        header = f"---\ntitle: {title}\nurl: {url}\nauthority: {authority}\nretrieved: {today}\n---\n\n"
        path.write_text(header + text + "\n", encoding="utf-8")
        ok += 1
        print(f"  OK      {path.name} ({len(text)} chars)")

    print(f"\nSaved {ok}/{len(sources)} sources to {settings.raw_dir}")
    print("Tip: open the files and delete leftover menu text before running ingest.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
