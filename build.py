#!/usr/bin/env python3
"""Builds the RSS feed from articles/*.md.

Only articles whose `publish` time (Europe/Bratislava) is in the past are included.
Usage: python build.py <base_url>   e.g. https://user.github.io/english-reading/
"""
import html
import sys
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import markdown

TZ = ZoneInfo("Europe/Bratislava")
ROOT = Path(__file__).parent
OUT = ROOT / "_site"
FEED_TITLE = "Daily English Reading"
FEED_DESC = "Krátke články v americkej angličtine (A2–B1) so slovíčkami a gramatikou."


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path.name}: missing front matter")
    _, front, body = text.split("---", 2)
    meta = {}
    for line in front.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    meta["id"] = path.stem
    meta["publish_dt"] = datetime.strptime(meta["publish"], "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    meta["html"] = markdown.markdown(body.strip())
    return meta


def page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Georgia,serif;max-width:40rem;margin:2rem auto;padding:0 1rem;"
        "line-height:1.6;color:#222}h1{line-height:1.2}a{color:#1a5fb4}</style>"
        f"</head><body>{body}</body></html>"
    )


def cdata(s: str) -> str:
    return "<![CDATA[" + s.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def main() -> None:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost/").rstrip("/") + "/"
    now = datetime.now(TZ)
    articles = [parse(p) for p in sorted((ROOT / "articles").glob("*.md"))]
    published = sorted(
        (a for a in articles if a["publish_dt"] <= now),
        key=lambda a: a["publish_dt"],
        reverse=True,
    )

    (OUT / "articles").mkdir(parents=True, exist_ok=True)
    items = []
    for a in published:
        link = f"{base}articles/{a['id']}.html"
        (OUT / "articles" / f"{a['id']}.html").write_text(
            page(a["title"], f"<h1>{html.escape(a['title'])}</h1>{a['html']}"
                 f"<p><a href=\"../index.html\">← All articles</a></p>"),
            encoding="utf-8",
        )
        items.append(
            "<item>"
            f"<title>{html.escape(a['title'])}</title>"
            f"<link>{link}</link>"
            f"<guid isPermaLink=\"false\">{a['id']}</guid>"
            f"<pubDate>{format_datetime(a['publish_dt'])}</pubDate>"
            f"<description>{cdata(a['html'])}</description>"
            f"<content:encoded>{cdata(a['html'])}</content:encoded>"
            "</item>"
        )

    feed = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<rss version=\"2.0\" xmlns:content=\"http://purl.org/rss/1.0/modules/content/\" "
        "xmlns:atom=\"http://www.w3.org/2005/Atom\"><channel>"
        f"<title>{FEED_TITLE}</title><link>{base}</link>"
        f"<description>{html.escape(FEED_DESC)}</description><language>en-us</language>"
        f"<atom:link href=\"{base}feed.xml\" rel=\"self\" type=\"application/rss+xml\"/>"
        f"<lastBuildDate>{format_datetime(now)}</lastBuildDate>"
        + "".join(items)
        + "</channel></rss>\n"
    )
    (OUT / "feed.xml").write_text(feed, encoding="utf-8")

    links = "".join(
        f"<li><a href=\"articles/{a['id']}.html\">{html.escape(a['title'])}</a> "
        f"<small>{a['publish_dt']:%d.%m.%Y}</small></li>"
        for a in published
    )
    (OUT / "index.html").write_text(
        page(FEED_TITLE, f"<h1>{FEED_TITLE}</h1><p>RSS: <a href=\"feed.xml\">{base}feed.xml</a></p>"
                         f"<ul>{links}</ul>"),
        encoding="utf-8",
    )
    print(f"{len(published)} of {len(articles)} articles published")


if __name__ == "__main__":
    main()
