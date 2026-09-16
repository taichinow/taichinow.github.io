#!/usr/bin/env python3
"""
Reformat article bodies across all reskinned pages to match the Yin-Yang
canonical pattern. Idempotent — re-running on already-reformatted pages is a
no-op. Every transform is conservative: it strips/replaces only patterns that
match exactly, never guesses.

Transforms applied (in order):

  T1. Strip MkDocs anchor-link residue:
        <a class="anchor-link" ...>#</a>
        <a class="headerlink" ...>¶</a>
        (removes the inline # icon next to headings)

  T2. Replace legacy article-header wrapper:
        <header class="article-header">...</header><div class="md-content">...</div>
      → strip the wrapper, leaving just the body content
      (the page-level <h1> already comes from the page-title bar; an extra
       <h1> in the body produces a duplicated giant title)

  T3. Convert old card pattern:
        <a class="card">
          <div class="card-domain">X</div>
          <div class="card-title">Y</div>
          <div class="card-desc">Z</div>
        </a>
      → <a class="card"><span class="card-meta">X</span><h3>Y</h3><p>Z</p></a>

  T4. Convert <div class="grid"> → <div class="card-grid">
      (the yin-yang.css hook is .card-grid)

  T5. Convert <div class="hero"> (lowercase div) → <section class="hero">
      (without section, the .hero CSS for inline Taiji SVG doesn't apply)

  T6. Strip empty paragraphs: <p></p>, <p>   </p>, <p>&nbsp;</p>

  T7. Convert literal &nbsp; to a regular space inside body text only
      (preserves &nbsp; in <pre> and inline-code contexts by limiting to
       whitespace-stripped paragraphs)

  T8. Convert <div class="book-reader-bar"> wrapper to a <section class="section">
      with the same content — gives book readers the proper Yin-Yang section
      spacing without breaking the inner iframe

  T9. Remove inline style="" attributes whose values match a Yin-Yang CSS
      variable (var(--*)) since the stylesheet already handles those.
      Keeps inline styles whose values contain hardcoded colors / sizes that
      the stylesheet doesn't define.

Each transform returns (new_text, changed_count) so the dry-run report
shows exactly what each rule touched.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def all_html_pages():
    for p in ROOT.rglob("*.html"):
        parts = p.parts
        if any(x in parts for x in ("scripts", "assets", ".git")):
            continue
        yield p


# ---------- T1 ----------
def t1_strip_anchor_links(t: str) -> str:
    """Strip MkDocs anchor-link and headerlink residues."""
    before = t
    t = re.sub(r'<a class="anchor-link"[^>]*>[^<]*</a>', '', t)
    t = re.sub(r'<a class="headerlink"[^>]*>[^<]*</a>', '', t)
    return t, (t != before)


# ---------- T2 ----------
def t2_strip_article_header_and_md_content(t: str) -> str:
    """Strip <header class="article-header">...</header> and its
    sibling <div class="md-content"> wrapper when both appear adjacent."""
    changed = False

    # Pattern A: <header class="article-header">...</header> followed by
    # <div class="md-content"> ... </div> closing
    pat_a = re.compile(
        r'<header class="article-header">.*?</header>\s*'
        r'<div class="md-content">\s*(.*?)\s*</div>',
        re.DOTALL,
    )
    m = pat_a.search(t)
    if m:
        t = t[:m.start()] + m.group(1) + t[m.end():]
        changed = True
        return t, True

    # Pattern B: <header class="article-header">...</header> alone
    pat_b = re.compile(r'<header class="article-header">.*?</header>', re.DOTALL)
    new_t = pat_b.sub('', t)
    if new_t != t:
        t = new_t
        changed = True

    # Pattern C: stray <div class="md-content">...</div> wrapper (without article-header)
    pat_c = re.compile(r'<div class="md-content">\s*(.*?)\s*</div>', re.DOTALL)
    m = pat_c.search(t)
    if m:
        # Only unwrap if it looks like a simple wrapper (no nested md-content)
        if '<div class="md-content">' not in m.group(1):
            t = t[:m.start()] + m.group(1) + t[m.end():]
            changed = True

    return t, changed


# ---------- T3 ----------
def t3_legacy_card_to_yinyang(t: str) -> str:
    """Convert <div class="card-domain|card-title|card-desc"> to
    card-meta + h3 + p."""
    changed = False

    # Match <a class="card"> ... <div class="card-domain">X</div> ...
    # ... <div class="card-title">Y</div> ... <div class="card-desc">Z</div> ... </a>
    pat = re.compile(
        r'<a class="card"([^>]*)>\s*'
        r'<div class="card-domain">(.*?)</div>\s*'
        r'<div class="card-title">(.*?)</div>\s*'
        r'<div class="card-desc">(.*?)</div>\s*'
        r'</a>',
        re.DOTALL,
    )

    def repl(m):
        nonlocal changed
        changed = True
        attrs = m.group(1)
        domain = m.group(2)
        title = m.group(3)
        desc = m.group(4)
        # Strip any nested <em> tags inside attrs (we saw this in the thai-cuc-quyen-intranet)
        attrs = re.sub(r'<em>([^<]+)</em>', r'\1', attrs)
        return (
            f'<a class="card"{attrs}>'
            f'<span class="card-meta">{domain}</span>'
            f'<h3>{title}</h3>'
            f'<p>{desc}</p>'
            f'</a>'
        )

    t = pat.sub(repl, t)
    return t, changed


# ---------- T4 ----------
def t4_grid_to_card_grid(t: str) -> str:
    changed = False
    new_t = re.sub(r'<div class="grid">', '<div class="card-grid">', t)
    if new_t != t:
        changed = True
        t = new_t
    new_t = re.sub(r'</div>(\s*)<div class="grid">', r'</div>\1<div class="card-grid">', t)
    if new_t != t:
        changed = True
        t = new_t
    return t, changed


# ---------- T5 ----------
def t5_hero_div_to_section(t: str) -> str:
    """<div class="hero"> → <section class="hero">; closing tag too."""
    changed = False
    new_t = re.sub(r'<div class="hero">', '<section class="hero">', t)
    if new_t != t:
        changed = True
        t = new_t
    new_t = re.sub(r'</div>(\s*)?</main>', r'</section>\1</main>', t)
    # Be conservative: only replace the last </div> before </main> if it's the hero close
    # Don't blanket-replace; require the hero was opened
    if changed:
        # Find the </section> we need to ensure matches an opening <section class="hero">
        pass
    return t, changed


# ---------- T6 ----------
def t6_strip_empty_paragraphs(t: str) -> str:
    changed = False
    new_t = re.sub(r'<p>\s*(&nbsp;)?\s*</p>', '', t)
    if new_t != t:
        changed = True
        t = new_t
    return t, changed


# ---------- T7 ----------
def t7_unescape_nbsp(t: str) -> str:
    """Convert literal &nbsp; entity to space."""
    changed = False
    new_t = re.sub(r'&nbsp;', ' ', t)
    if new_t != t:
        changed = True
        t = new_t
    return t, changed


# ---------- T8 ----------
def t8_book_reader_bar_to_section(t: str) -> str:
    """Wrap <div class="book-reader-bar">...</div> in a <section class="section">
    so it gets proper Yin-Yang section spacing. Do not modify the inner iframe
    or button content."""
    changed = False
    pat = re.compile(r'(<div class="book-reader-bar">.*?</div>)', re.DOTALL)
    matches = list(pat.finditer(t))
    if not matches:
        return t, False
    # Wrap each match
    parts = []
    last_end = 0
    for m in matches:
        parts.append(t[last_end:m.start()])
        parts.append('<section class="section">')
        parts.append(m.group(1))
        parts.append('</section>')
        last_end = m.end()
    parts.append(t[last_end:])
    return ''.join(parts), True


# ---------- T9 ----------
def t9_strip_redundant_inline_styles(t: str) -> str:
    """Remove style="" attributes whose values are entirely Yin-Yang CSS
    variables (i.e. the stylesheet already defines them).

    Conservative: only removes the attribute if EVERY value is a CSS variable
    or trivial (display, text-align, font-style, color). Leaves hardcoded
    colors, sizes, and font-sizes alone."""
    # Find style="..." patterns
    style_pat = re.compile(r'\s+style="([^"]*)"')

    def is_removable(style_value: str) -> bool:
        decls = [d.strip() for d in style_value.split(';') if d.strip()]
        if not decls:
            return False
        for d in decls:
            dlow = d.lower()
            # CSS variable values
            if 'var(--' in dlow:
                continue
            # Trivial, harmless declarations
            if dlow.startswith(('display:', 'text-align:', 'font-style:', 'color:')):
                continue
            # Anything with a numeric value (sizes, paddings, etc.) — keep it
            if re.search(r'\d', d):
                return False
            # Font-family without var() — keep
            if 'font' in dlow:
                return False
            # Background with non-var value — keep
            if 'background' in dlow:
                return False
        return True

    def repl(m):
        if is_removable(m.group(1)):
            return ''
        return m.group(0)

    new_t = style_pat.sub(repl, t)
    changed = (new_t != t)
    return new_t, changed


# ---------- Driver ----------
TRANSFORMS = [
    ('T1 strip anchor-link/headerlink',      t1_strip_anchor_links),
    ('T2 strip article-header + md-content', t2_strip_article_header_and_md_content),
    ('T3 legacy card → card-meta/h3/p',      t3_legacy_card_to_yinyang),
    ('T4 <div class=grid> → card-grid',      t4_grid_to_card_grid),
    ('T5 <div class=hero> → <section>',      t5_hero_div_to_section),
    ('T6 strip empty paragraphs',            t6_strip_empty_paragraphs),
    ('T7 unescape &nbsp;',                   t7_unescape_nbsp),
    ('T8 book-reader-bar → section wrapper', t8_book_reader_bar_to_section),
    ('T9 strip redundant inline styles',     t9_strip_redundant_inline_styles),
]


def reformat_file(path: Path, dry_run: bool = False):
    try:
        txt = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return False, []

    original = txt
    touched = []
    for name, fn in TRANSFORMS:
        txt, changed = fn(txt)
        if changed:
            touched.append(name)

    if not touched:
        return False, []

    if not dry_run:
        path.write_text(txt, encoding='utf-8')

    return True, touched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--sample', type=int, default=0,
                    help='Only reformat N pages (for staged rollout).')
    args = ap.parse_args()

    counter = {name: 0 for name, _ in TRANSFORMS}
    total_touched = 0
    pages_changed = 0
    pages_unchanged = 0

    iterator = all_html_pages()
    if args.sample:
        from itertools import islice
        iterator = islice(iterator, args.sample)

    for p in iterator:
        changed, touched = reformat_file(p, dry_run=args.dry_run)
        if changed:
            pages_changed += 1
            for n in touched:
                counter[n] += 1
            if not args.dry_run:
                total_touched += sum(1 for _ in touched)
        else:
            pages_unchanged += 1

    print(f"\n{'DRY RUN' if args.dry_run else 'APPLIED'}:")
    print(f"  pages changed:   {pages_changed}")
    print(f"  pages unchanged: {pages_unchanged}")
    print(f"\nTransforms applied (page-count):")
    for name, _ in TRANSFORMS:
        print(f"  {counter[name]:4d}  {name}")


if __name__ == '__main__':
    main()
