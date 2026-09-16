#!/usr/bin/env python3
"""
Reskin the taichinow.github.io (Intranet/deploy/) site to the Yin-Yang theme
that lives in taichikb_repo. Re-shells every HTML page; preserves all body
content; rewrites relative asset paths; maps top-level links to canonical.

USAGE
  python scripts/reskin_to_yinyang.py            # reskin everything (default)
  python scripts/reskin_to_yinyang.py --dry-run  # print plan only, write nothing

DESIGN
  - Theme assets (yin-yang.css, taiji-logo.svg) must already exist in
    deploy/assets/stylesheets/ and deploy/assets/images/ (copied once at setup).
  - Three chrome patterns are stripped from every page:
        <header class="masthead">...</header>
        <nav class="topnav">...</nav>
        <aside class="toc-sidebar">...</aside>
  - The extracted body is wrapped in <main><article class="intranet-content">
    and re-shelled with the Yin-Yang header / footer / nav.
  - Inline Taiji SVG (NOT <img>) appears in header brand + footer signature,
    matching taichikb's pattern (yin-yang.css only styles inline SVGs).
"""
from __future__ import annotations

import argparse
import html as html_module
import re
import sys
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent  # Intranet/deploy/
ASSETS = "/assets"  # absolute; both github-pages and local serve.py handle it
CSS = f"{ASSETS}/stylesheets/yin-yang.css"
FAVICON = f"{ASSETS}/images/taiji-logo.svg"
FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400"
    "&family=Inter:wght@400;500;600"
    "&family=Noto+Serif+SC:wght@400;500&display=swap"
)

# Taiji SVG (inline; yin-yang.css needs inline <svg>, not <img>)
TAIJI_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" '
    'class="taiji-logo">'
    '<circle cx="100" cy="100" r="98" fill="#ffffff" stroke="#000000" stroke-width="4"/>'
    '<path d="M 100,2 A 98,98 0 0,1 100,198 A 49,49 0 0,1 100,100 '
    'A 49,49 0 0,0 100,2 Z" fill="#000000"/>'
    '<circle cx="100" cy="51" r="12" fill="#ffffff"/>'
    '<circle cx="100" cy="149" r="12" fill="#000000"/>'
    "</svg>"
)
TAIJI_SVG_INLINE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" '
    'width="20" height="20" style="vertical-align:-3px;display:inline-block;">'
    '<circle cx="100" cy="100" r="98" fill="#ffffff" stroke="#000000" stroke-width="4"/>'
    '<path d="M 100,2 A 98,98 0 0,1 100,198 A 49,49 0 0,1 100,100 '
    'A 49,49 0 0,0 100,2 Z" fill="#000000"/>'
    '<circle cx="100" cy="51" r="12" fill="#ffffff"/>'
    '<circle cx="100" cy="149" r="12" fill="#000000"/>'
    "</svg>"
)

NAV_ITEMS = [
    ("Home",                "/"),
    ("Techniques",          "/techniques/"),
    ("Philosophy",          "/philosophy/"),
    ("History",             "/history/"),
    ("Contact",             "/contact/"),
]

# ---------------------------------------------------------------------------
# Chrome stripping
# ---------------------------------------------------------------------------

CHROME_PATTERNS = [
    r'<header class="masthead">.*?</header>',
    r'<nav class="topnav">.*?</nav>',
    r'<aside class="toc-sidebar">.*?</aside>',
    r'<aside[^>]*class="[^"]*toc[^"]*".*?</aside>',
    r'<div class="article-meta-bar">.*?</div>',
    r'<div id="reading-progress"></div>',
    r'<a class="headerlink"[^>]*>.*?</a>',
    r'<button id="theme-toggle-btn"[^>]*>.*?</button>',
    r'<div class="scrim">\s*</div>',
]


def strip_chrome(html: str) -> str:
    """Remove intranet-style chrome (masthead, topnav, toc-sidebar, etc.)."""
    for pat in CHROME_PATTERNS:
        html = re.sub(pat, "", html, flags=re.DOTALL)
    return html


def extract_title(html: str, fallback: str = "Untitled") -> str:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.DOTALL | re.IGNORECASE)
    if not m:
        return fallback
    title = m.group(1)
    # Strip trailing " · Thái Cực Khố" or " — Taichi Health & Finance Intranet"
    title = re.split(r"[·—\-]+", title)[0].strip()
    title = re.sub(r"<[^>]+>", "", title).strip()
    return html_module.unescape(title) or fallback


def extract_body(html: str) -> str:
    """Extract the main content region from an intranet page.

    Tries three patterns in priority order:
      1. <article class="article-body">...</article>
      2. <main>...</main>
      3. <body>...</body> minus scripts/styles
    """
    # 1. article-body
    m = re.search(r'<article[^>]*class="[^"]*article-body[^"]*"[^>]*>(.*?)</article>',
                  html, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    # 2. main
    m = re.search(r"<main[^>]*>(.*?)</main>", html, flags=re.DOTALL)
    if m:
        return m.group(1).strip()
    # 3. body fallback
    m = re.search(r"<body[^>]*>(.*?)</body>", html, flags=re.DOTALL)
    if m:
        body = m.group(1)
        body = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.DOTALL)
        body = re.sub(r"<style[^>]*>.*?</style>", "", body, flags=re.DOTALL)
        return body.strip()
    return html


def normalize_internal_links(html: str) -> str:
    """Rewrite intranet-style links to canonical /<section>/ paths.

    taichinow currently uses /thai-cuc-quyen/, /tai-chi/, etc. directly —
    those are already canonical. The main rewrite we need is:
      - href="/foo/bar/" relative-from-root style is fine.
      - assets: rewrite ../../assets and ../assets to /assets (absolute).
    """
    # Strip a few legacy junk patterns first
    html = re.sub(r'<em>([^<]+)</em>', r"\1", html)
    # Asset path absolutization
    html = re.sub(r'(href|src)="\.\.\/\.\.\/assets', r'\1="/assets', html)
    html = re.sub(r'(href|src)="\.\.\/assets',     r'\1="/assets', html)
    html = re.sub(r'(href|src)="\.\.\/\.\.\/\.\.\/assets', r'\1="/assets', html)
    html = re.sub(r'(href|src)="assets',           r'\1="/assets', html)
    # /thai-cuc-quyen-intranet/ legacy → /thai-cuc-quyen/
    html = re.sub(r'href="/thai-cuc-quyen-intranet/', 'href="/thai-cuc-quyen/', html)
    return html


# ---------------------------------------------------------------------------
# Page shell (Yin-Yang style)
# ---------------------------------------------------------------------------

def page_shell(title: str, body: str, *,
               home="/", active_nav: str = "",
               back_label="← Back", back_href="",
               home_label="⌂ Home",
               description: str = "") -> str:
    """Wrap content in the Yin-Yang page shell."""
    nav_links = []
    for label, href in NAV_ITEMS:
        cls = "active" if href == active_nav else ""
        nav_links.append(f'<a href="{href}" class="{cls}">{label}</a>')
    nav_html = "\n".join(nav_links)

    desc_meta = (f'\n<meta name="description" content="{description}">' if description else "")

    back_html = ""
    if back_href:
        back_html = f'<a href="{back_href}">{back_label}</a>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html_module.escape(title)} — TaichiNOW</title>{desc_meta}
<link rel="icon" href="{FAVICON}" type="image/svg+xml">
<link href="{FONTS}" rel="stylesheet">
<link rel="stylesheet" href="{CSS}">
</head>
<body>

<header class="site-header">
    <a href="{home}" class="brand">{TAIJI_SVG}<span>TaichiNOW</span></a>
    <nav class="site-nav">
{nav_html}
    </nav>
</header>

<main>
<article class="intranet-content" style="max-width: 880px; margin: 0 auto; padding: 2rem 1rem;">
{body}
</article>

<nav class="page-nav">
    {back_html}
    <a href="{home}" class="home">{home_label}</a>
</nav>
</main>

<footer class="site-footer">
    <p>Built with ❤️ for the Vietnamese Tai Chi community {TAIJI_SVG_INLINE} by Phạm Đức Hải</p>
    <p>Trang web này được xây dựng với ❤️ cho cộng đồng Thái Cực Quyền Việt Nam {TAIJI_SVG_INLINE} by Phạm Đức Hải</p>
</footer>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Per-file driver
# ---------------------------------------------------------------------------

def is_already_yinyang(html: str) -> bool:
    """Skip pages already on the Yin-Yang theme (e.g. mirrored from taichikb)."""
    return 'href="/assets/stylesheets/yin-yang.css"' in html


def reskin_file(path: Path, *, active_nav: str = "", back_href: str = "",
                dry_run: bool = False) -> bool:
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"  ! cannot read {path}: {e}")
        return False

    if is_already_yinyang(html):
        return False  # already reskinned — idempotent

    if "<html" not in html:
        return False  # not a real page (e.g. binary saved as .html)

    title = extract_title(html)
    body = extract_body(html)
    body = normalize_internal_links(body)
    body = strip_chrome(body)

    new_html = page_shell(
        title=title, body=body,
        active_nav=active_nav,
        back_href=back_href,
    )
    if dry_run:
        print(f"  would-reskin: {path.relative_to(ROOT)}  ({len(html)} -> {len(new_html)} bytes)")
        return True
    path.write_text(new_html, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Site-wide plan
# ---------------------------------------------------------------------------

def all_html() -> Iterable[Path]:
    for p in ROOT.rglob("*.html"):
        # Skip scripts/, .git/, anything under assets/
        rel = p.relative_to(ROOT)
        parts = rel.parts
        if not parts:
            continue
        if parts[0] in {"scripts", ".git"}:
            continue
        if parts[0] == "assets":
            continue
        yield p


def section_active_nav(path: Path) -> tuple[str, str]:
    """Return (active_nav_href, back_href) for a given page."""
    rel = path.relative_to(ROOT).as_posix()
    parts = rel.split("/")
    # First non-empty path segment under deploy/
    section = parts[0] if parts else ""
    active = ""
    back = "/"
    if section == "thai-cuc-quyen":
        active = "/thai-cuc-quyen/"
        back = "/thai-cuc-quyen/"
    elif section == "tai-chi":
        active = "/tai-chi/"
        back = "/tai-chi/"
    elif section == "articles":
        active = "/articles/"
        back = "/articles/"
    elif section == "daoist":
        active = "/daoist/"
        back = "/daoist/"
    elif section == "deep-dives":
        active = "/deep-dives/"
        back = "/deep-dives/"
    elif section == "practice-vault":
        active = "/practice-vault/"
        back = "/practice-vault/"
    elif section == "life-skills":
        active = "/life-skills/"
        back = "/life-skills/"
    elif section == "research":
        active = "/research/"
        back = "/research/"
    elif section == "podcast":
        active = "/podcast/"
        back = "/podcast/"
    elif section == "videos":
        active = "/videos/"
        back = "/videos/"
    elif section == "books":
        active = "/books/"
        back = "/books/"
    elif section == "gemini-notebooks":
        active = "/gemini-notebooks/"
        back = "/gemini-notebooks/"
    elif section == "techniques":
        active = "/techniques/"
        back = "/techniques/"
    elif section == "philosophy":
        active = "/philosophy/"
        back = "/philosophy/"
    elif section == "history":
        active = "/history/"
        back = "/history/"
    elif section == "contact":
        active = "/contact/"
        back = "/contact/"
    elif section == "en":
        if len(parts) >= 3:
            sub = parts[1]
            active = f"/{sub}/"
            back = f"/{sub}/"
    elif section == "vi":
        if len(parts) >= 3:
            sub = parts[1]
            active = f"/{sub}/"
            back = f"/{sub}/"
    elif section == "cn":
        if len(parts) >= 3:
            sub = parts[1]
            active = f"/{sub}/"
            back = f"/{sub}/"
    return active, back


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    reskinned = 0
    skipped = 0
    failed = 0
    for path in all_html():
        active, back = section_active_nav(path)
        ok = reskin_file(path, active_nav=active, back_href=back, dry_run=args.dry_run)
        if ok:
            reskinned += 1
        else:
            skipped += 1
    print(f"\nreskinned: {reskinned}    skipped: {skipped}    failed: {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
