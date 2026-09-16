#!/usr/bin/env python3
"""
Fix the malformed card markup on 2nd-level landing pages
(/gemini-notebooks/, /daoist/, /life-skills/, /deep-dives/, etc.).

The corruption comes from a prior single-line rewrite that produced patterns
like:

  P1: <a class="card" ...><span class="card-meta">X<div class="card-title">Y</div>
        <div class="card-meta"><span>...</span></div>
        <div class="card-desc">Z</div>
        <div class="card-footer"><span>...</span></div>
      </a>

      Bug: <span class="card-meta"> is never closed; <div class="card-title">
      should be <h3>.

  P2: <a class="card" ...><span class="card-meta">X</span><h3>Y</div>
        <div class="card-meta"><span>...</span></h3><p>Z</div>
        <div class="card-footer">...</p></a>

      Bug: h3 closed with </div>; p closed with </div>; nested tag mismatches.

Fix strategy — pattern-targeted regex rewrites, applied IN ORDER so each
fix is idempotent. Do NOT touch well-formed <a class="card"> blocks.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fix_pattern_p1(t: str) -> tuple[str, int]:
    """Pattern 1: <span class="card-meta">X<div class="card-title">Y</div>...
    Bug: <span> not closed; card-title should be h3.

    Fix: close </span> before <div>; convert card-title div to h3.
    """
    fixed = 0
    # <span class="card-meta">X<div class="card-title">Y</div>
    #   → <span class="card-meta">X</span><h3>Y</h3>
    # X may include whitespace/newlines (no <), so use [\s\S] with re.DOTALL.
    pat = re.compile(
        r'<span class="card-meta">([\s\S]*?)<div class="card-title">([\s\S]*?)</div>',
    )
    new_t, n = pat.subn(r'<span class="card-meta">\1</span><h3>\2</h3>', t)
    fixed += n
    return new_t, fixed


def fix_pattern_p2(t: str) -> tuple[str, int]:
    """Pattern 2: <div class="card-domain">X</span><h3>Y</div>
    Bug: opening div closed with </span>, h3 closed with </div>.

    Fix: close </div> properly, close </h3>, and convert the mashed div/span
    pair into a clean <span class="card-meta">X</span><h3>Y</h3>.
    """
    fixed = 0
    pat = re.compile(
        r'<div class="card-domain">([^<]+)</span><h3>(.*?)</div>',
        re.DOTALL
    )
    new_t, n = pat.subn(r'<span class="card-meta">\1</span><h3>\2</h3>', t)
    fixed += n
    return new_t, fixed


def fix_pattern_p3(t: str) -> tuple[str, int]:
    """Pattern 3: <div class="card-meta"><span>...</span></h3><p>Z</div>
    Bug: <span> closed with </h3>; <p> closed with </div>.

    Fix: normalize the inner tags.

    Note: this only fires when the surrounding <h3>Y</h3> from p2 isn't
    present. After p2 fires, the structure is cleaner; p3 then catches
    the leftover mash from the next card.
    """
    fixed = 0
    # <div class="card-meta"><span>X</span> · <span>Y</span></h3><p>Z</div>
    #   → <span class="card-meta"><span>X</span> · <span>Y</span></span><p>Z</p>
    pat = re.compile(
        r'<div class="card-meta"><span>([^<]*)</span>([^<]*)<span>([^<]*)</span></h3><p>(.*?)</div>',
        re.DOTALL
    )
    new_t, n = pat.subn(
        r'<p><span>\1</span>\2<span>\3</span></p><p>\4</p>',
        t
    )
    fixed += n
    return new_t, fixed


def fix_pattern_p4(t: str) -> tuple[str, int]:
    """Pattern 4: card-footer ends with </p></a> (p closed then card closed).
    Bug: <p> is a stray wrapping for the footer text.

    Fix: convert </p></a> at the end of a card-footer block to </div></a>.
    Also strip the orphan <p> wrapping the Read Article span.
    """
    fixed = 0
    # <div class="card-footer"><span>...</span></p></a>
    pat = re.compile(
        r'<div class="card-footer"><span>([^<]*)</span></p></a>',
        re.DOTALL
    )
    new_t, n = pat.subn(
        r'<div class="card-footer"><span>\1</span></div></a>',
        t
    )
    fixed += n
    return new_t, fixed


def fix_pattern_p5(t: str) -> tuple[str, int]:
    """Pattern 5: <div class="card-desc">Z</div> at the body of a card.
    Bug: should be <p>Z</p> for proper typography under Yin-Yang css.

    Fires on any <div class="card-desc"> that appears inside an <a class="card">.
    """
    fixed = 0
    # Idempotency: only fires when this div has not already been converted.
    # The pattern <p> ... <div class="card-desc">  → <p> ... <p>
    # The pattern <div class="card-desc"> directly follows </h3>, <p>, or
    # the span-meta block.
    pat = re.compile(
        r'<div class="card-desc">([\s\S]*?)</div>',
    )
    # Only fire if there's NO <p> immediately wrapping this div already.
    # Simple heuristic: convert, then dedup later if needed. For now we
    # unconditionally convert — the patterns don't nest.
    new_t, n = pat.subn(r'<p>\1</p>', t)
    fixed += n
    return new_t, fixed


def fix_pattern_p6(t: str) -> tuple[str, int]:
    """Pattern 6: <div class="card-meta"> with <span>X</span> · <span>Y</span></div>
    Bug: appears as a meta info block (read time + size) that should be a <p>.

    Convert: <div class="card-meta"><span>X</span> · <span>Y</span></div>
       → <p><span>X</span> · <span>Y</span></p>
    Idempotent: only fires when this exact structure (NOT the domain span card-meta).
    """
    fixed = 0
    pat = re.compile(
        r'<div class="card-meta"><span>([^<]*)</span>\s*(&middot;|·|&nbsp;|\s)\s*<span>([^<]*)</span></div>',
    )
    new_t, n = pat.subn(
        r'<p><span>\1</span> \2 <span>\3</span></p>',
        t
    )
    fixed += n
    return new_t, fixed


def fix_standard_card_pattern(t: str) -> tuple[str, int]:
    """Standard pattern (most common on /books/, /tai-chi/, /thai-cuc-quyen/,
    /daoist/): <a class="card" ...> followed by:
      <div> optional wrapper containing <div class="card-domain">X</div>
      <span class="badge">Y</span>  (optional)
      </div>
      <div class="card-title">Z</div>
      <div class="card-desc">W</div>
      <div class="card-footer"><span>...</span></div>
    </a>

    Convert to canonical:
      <a class="card" ...>
        <span class="card-meta">X</span>
        <h3>Z</h3>
        <p>W</p>
        <div class="card-footer">...</div>
      </a>
    """
    # Match full <a class="card..."> block first (allow extra classes)
    card_pat = re.compile(r'<a class="card[^"]*"([^>]*)>([\s\S]*?)</a>')

    def repl(m):
        attrs = m.group(1)
        inner = m.group(2)
        # Only fix if it contains card-domain + card-title (card-desc is optional)
        if 'card-domain' not in inner or 'card-title' not in inner:
            return m.group(0)

        # Extract domain
        d = re.search(r'<div class="card-domain"[^>]*>([\s\S]*?)</div>', inner)
        domain = d.group(1).strip() if d else ''

        # Extract title
        t2 = re.search(r'<div class="card-title"[^>]*>([\s\S]*?)</div>', inner)
        title = t2.group(1).strip() if t2 else ''

        # Extract meta line (optional) — read-time / size info
        mt = re.search(r'<div class="card-meta"[^>]*>(?:<span>([\s\S]*?)</span>[\s\S]*?)</div>', inner)
        meta = mt.group(1).strip() if mt else ''

        # Extract desc
        d2 = re.search(r'<div class="card-desc"[^>]*>([\s\S]*?)</div>', inner)
        desc = d2.group(1).strip() if d2 else ''

        # Extract footer if present
        f = re.search(r'<div class="card-footer"[^>]*>([\s\S]*?)</div>', inner)
        footer = f.group(1).strip() if f else ''

        # Rebuild
        parts = [
            f'<a class="card"{attrs}>',
            f'<span class="card-meta">{domain}</span>' if domain else '',
            f'<h3>{title}</h3>' if title else '',
            f'<p>{meta}</p>' if meta else '',
            f'<p>{desc}</p>' if desc else '',
            f'<div class="card-footer">{footer}</div>' if footer else '',
            '</a>',
        ]
        return ''.join(p for p in parts if p)

    new_t = card_pat.sub(repl, t)
    # Count actual replacements (count <a class="card..."> with card-domain in original)
    fixed = len(re.findall(r'<a class="card[^"]*"[^>]*>(?:(?!</a>).)*?card-domain', t, re.DOTALL))
    return new_t, fixed


def fix_pattern_p7(t: str) -> tuple[str, int]:
    """Pattern 7: remove leftover <div class="filter-bar">...</div> with
    <input id="search-input"> — this is leftover intranet chrome that's
    not part of the canonical Yin-Yang shell."""
    fixed = 0
    pat = re.compile(r'<div class="filter-bar">[\s\S]*?</div>')
    new_t, n = pat.subn('', t)
    fixed += n
    return new_t, fixed




def fix_pattern_p8(t: str) -> tuple[str, int]:
    """Pattern 8: <div class="card-domain">X</div><div class="card-title">Y</div>
    Used in PDF book-reader pages (no <a class="card"> wrapper, just a <div class="card">).

    Convert to a single labeled line: <span class="card-meta">X · Y</span>
    """
    fixed = 0
    pat = re.compile(
        r'<div class="card-domain">([^<]+)</div>\s*<div class="card-title">([^<]+)</div>',
    )
    new_t, n = pat.subn(r'<span class="card-meta">\1 · \2</span>', t)
    fixed += n
    return new_t, fixed


def fix_pattern_p9(t: str) -> tuple[str, int]:
    """Pattern 9: orphan <div class="card-title">X</div> inside a card
    (preceded by badge span + closing div, no card-domain sibling).

    Convert to <h3>X</h3>.
    """
    fixed = 0
    pat = re.compile(
        r'(<span class="badge"[^>]*>[^<]*</span>\s*</div>\s*)<div class="card-title">([^<]+)</div>',
    )
    new_t, n = pat.subn(r'\1<h3>\2</h3>', t)
    fixed += n
    return new_t, fixed


# Add to FIXES list (must be appended before the closing bracket).
# Order matters: p2 (domain) before p3 (mash).
FIXES = [
    fix_pattern_p7,
    fix_pattern_p2,
    fix_pattern_p1,
    fix_pattern_p8,
    fix_pattern_p9,
    fix_standard_card_pattern,
    fix_pattern_p5,
    fix_pattern_p6,
    fix_pattern_p3,
    fix_pattern_p4,
]


def fix_html(t: str) -> tuple[str, int]:
    total = 0
    for fn in FIXES:
        t, n = fn(t)
        total += n
    return t, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    fixed_files = 0
    total_fixed = 0

    for p in ROOT.rglob("*.html"):
        parts = p.parts
        if any(x in parts for x in ("scripts", "assets", ".git")):
            continue
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        new_txt, n = fix_html(txt)
        if n > 0:
            if not args.dry_run:
                p.write_text(new_txt, encoding='utf-8')
            fixed_files += 1
            total_fixed += n
            if args.dry_run:
                rel = p.relative_to(ROOT).as_posix()
                print(f"  would-fix {n}: {rel}")

    print(f"\n{'DRY RUN' if args.dry_run else 'APPLIED'}:")
    print(f"  files touched:  {fixed_files}")
    print(f"  total fixes:    {total_fixed}")


if __name__ == '__main__':
    main()
