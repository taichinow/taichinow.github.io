# Taichi Book Sites — Full Session Report

**Date:** September 17, 2026
**Scope:** Book uploads, reader redesign, image fixes, and slop cleanup across both sites

---

## 1. Repository Locations

| Site | Local Repo | Remote | Branch | HEAD |
|------|-----------|--------|--------|------|
| **taichinow.github.io** | `D:\Taichi-Health-Finance\Intranet\deploy` | `github.com/taichinow/taichinow.github.io` | `main` | `b851113` (verified: local == remote) |
| **taichikb.github.io** | `D:\Taichi-Health-Finance\Intranet\taichikb_repo` | `github.com/taichikb/taichikb.github.io` | `main` | `0618063` (verified: local == remote) |

**Source of truth for PDFs:** `D:\Taichi-Health-Finance\Intranet\docs\books\` (76 PDFs, 1,173 MB total)

---

## 2. taichinow.github.io — Book Upload & Reader Redesign

### 2.1 What Was Done

**PDF Upload (73 files, 722 MB)**
- All books from `docs/books/` matched to their existing reader pages by slug (mapping saved at `deploy/scripts/pdf_upload_map.json`)
- Copied to `deploy/books/pdfs/<slug>.pdf` with URL-safe ASCII filenames (Vietnamese diacritics stripped, spaces → hyphens)
- Pushed in 7 size-batched commits (~115 MB each) to keep pushes under timeout

**Reader Redesign (116 pages total)**
- `/books/read/<slug>/` (73 EN books): replaced "online reader pending PDF hosting" placeholder with inline 100%-wide PDF reader (iframe, 88vh) + "Mở Toàn Tab PDF ↗" button
- `/thai-cuc-quyen/<slug>/` (30 VI books): fixed broken iframe srcs — previously pointed at non-existent `/books/<Vietnamese filename>.pdf`, now `/books/pdfs/<slug>.pdf`
- `/daoist/<slug>/` (13 books): fixed relative iframe srcs pointing at old filenames (all 404'd), now absolute `/books/pdfs/<slug>.pdf`

**Reader Defaults (all pages)**
- iframe URL params: `#toolbar=1&navpanes=0&view=FitH&zoom=page-width`
  - `navpanes=0` — PDF sidebar hidden by default (Chrome + Firefox)
  - `zoom=page-width` (Chrome) / `view=FitH` (Firefox) — opens fit to full reader width

**AI-Slop Cleanup (76 `/books/read/` pages)**
Removed entirely:
- "Tài liệu gốc có sẵn trong thư viện intranet…" paragraphs
- "📂 Tên tệp PDF: `<filename>`" lines
- "📚 Về Tài Liệu Này" sections — local disk paths (`D:/Taichi-Health-Finance/…`), `serve.py` commands, `localhost:8765` links, "Online reader status" paragraphs
- Stale meta descriptions ("online reader pending PDF hosting")

Clean page structure now:
```
Hero (title + tagline)
📖 <Book title> — one short VI description sentence
📖 Đọc Sách Trực Tuyến — inline reader + "Mở Toàn Tab PDF ↗"
🔗 Điều Hướng — back to Books / Home
```

**Bug Fixed Along the Way**
- Double-extension bug: my first iframe-fix regex produced `/books/pdfs/<slug>.pdf.pdf#…` on all 30 thai-cuc-quyen pages (user reported the 404 on `tra-va-tinh-lang-cau-truyen-ve-tap-thai-cuc-quyen`). Fixed globally, then re-audited all 103 reader pages: every iframe src and PDF href resolves to an existing file, zero cross-wired references.

### 2.2 Skipped Books (3, exceed GitHub 100 MB hard limit)

| Book | Size | Status |
|------|------|--------|
| Dan Miller & Tim Cartmell — Xing Yi Nei Gong | 99.5 MB | Reader page keeps short notice |
| Daoist Plant, Animal and Mineral Magic | 121 MB | Reader page keeps short notice |
| Mantak Chia — 35 Books compilation | 230 MB | Reader page keeps short notice |

These pages show one italic line: *"File PDF gốc vượt giới hạn lưu trữ của GitHub Pages nên chưa có trình đọc trực tuyến."* Full-text access requires the local intranet, or Git LFS / volume-splitting if online hosting is wanted later.

### 2.3 Commits (this session, newest first)

```
b851113  Remove AI-slop intranet text from all 76 book reader pages — keep only short description + inline reader + nav
44921d7  Fix daoist section readers: point iframes to /books/pdfs/ URLs (100% width, navpanes=0); placeholder notices for 2 oversized books
3e8495e  PDF readers: default to page-width (100%) zoom and hide nav sidebar (navpanes=0) on all 116 reader pages
af1970e  Fix inline PDF reader iframes: remove double .pdf.pdf extension on all 30 thai-cuc-quyen reader pages
c7392aa  Add book PDFs batch 7/7 (1 file, 86 MB)
55bbc3c  Add book PDFs batch 6/7 (2 files, 120 MB)
cb33af6  Add book PDFs batch 5/7 (2 files, 80 MB)
c01984b  Add book PDFs batch 4/7 (3 files, 91 MB)
8408905  Add book PDFs batch 3/7 (7 files, 117 MB)
8745f67  Add book PDFs batch 2/7 (11 files, 115 MB)
31f2737  Add book PDFs batch 1/7 (47 files, 114 MB)
3b3f39a  Upload books: embed 73 PDFs into reader pages (books/read + thai-cuc-quyen) with 100% wide inline readers
2ff47a3  (prior) Replace broken <img src=filename.png> with SVG placeholder on tai-chi pages
6079670  (prior) Replace broken PDF iframes with placeholder notification on 76 book reader pages
```

### 2.4 Site Statistics

- **Total HTML pages:** 393
- **PDFs hosted:** 73 (722 MB) at `/books/pdfs/`
- **Reader pages:** 76 EN (`/books/read/`) + 30 VI (`/thai-cuc-quyen/`) + 13 Daoist (`/daoist/`)
- **Readers with working inline PDF:** 112 of 115 (3 skipped for size)

---

## 3. taichikb.github.io — Image Fixes & Book Translations

### 3.1 Upside-Down Image Fixes

- Detected via brightness heuristic (top-vs-bottom mean differential; threshold −25 to −40; book-cover dimensions excluded)
- **39 images rotated 180°** (20 heavily upside-down, diff < −40; 19 moderate, diff −25 to −40)
- Post-rotation verified: all 39 now show positive differential (top brighter than bottom)
- Commit: `0618063` — "Rotate 39 upside-down legacy book images 180°"

### 3.2 Misplaced Book Images — Per-Book Image Folders

**Root cause:** all books shared `/assets/images/` with `p###_img##.png` naming — every book referenced `p001_img00.png` expecting its own page 1, but it was one shared file (extracted from a single source PDF).

**Fix:** images re-extracted from each book's own PDF into `/assets/book_images/<slug>/`:

| Book | Images | Size | Live |
|------|--------|------|------|
| Baguazhang Vol.1 (Erle Montaigue) | 94 | 4.1 MB | ✓ |
| Bát Quái Quyền Chưởng | 182 | 24.1 MB | ✓ |
| Chen-Style Handout (Jerry Cheng) | 16 | 3.1 MB | ✓ |
| How Stuff Works | 18 | 4.3 MB | ✓ |
| Xing Yi Nei Gong | 218 | 99.6 MB | ✗ dropped — too large to push; HTML reverted to legacy `/assets/images/` |

- Baguazhang Vol.2: no source PDF exists locally — 97 img tags replaced with placeholder notices
- All book HTMLs updated to reference their own subfolder (verified live: 0 legacy refs in migrated books)

### 3.3 Book Translations (16 of 70 target)

Translated this session (+5): Tianren Heyi (Thiên Nhân Hợp Nhất), How Stuff Works, TaiChiLexicon (từ điển thuật ngữ), Acu Summer 2021 (Thần, Nguyên Thần & Não), General Principles of Tai Chi (Erle Montaigue), Thái Cực Quyền Trong Quần Vợt (tennis × tai chi).

Each translation is a bilingual reader page (EN original | VI translation, two-column) in Yin-Yang theme.

**Known limitation:** source PDF classification found ~20 of the 76 PDFs are already Vietnamese; 12 are image-only scans (no extractable text — would need OCR). Remaining translation pool ≈ 44 books.

### 3.4 Commits (this session)

```
0618063  Rotate 39 upside-down legacy book images 180°
78d4762  Add per-book images: bat-quai-quyen-chuong
d9915dc  Add per-book images: how-stuff-works
e1375bc  Add per-book images: chen-style-handout
6a2c9bb  Add per-book images: baguazhang-vol1
9f8ff64  Fix upside-down book images (39 rotated) + update HTML refs to per-book subfolders + add Tai Chi Tennis translation
62fb160  Clean vi/books/index.html — remove duplicate entries, use clean dir names
3143d6c  Rename book dirs to remove %20 (CDN compatibility)
03c3e0d  Translate 5 more books (18/70 total)
720c9fb  Fix 28 PDF-iframe pages in /vi/daoist/ and /vi/thai-cuc-quyen/
490284a  Add 68 redirect pages for legacy slugs
5c10766  Fix 84+ legacy section links across all pages
```

### 3.5 Site Statistics

- **Total HTML pages:** 877
- **Per-book images:** 528 PNGs in `/assets/book_images/` (5 books)
- **Legacy images:** 780 PNGs in `/assets/images/` (39 rotated)
- **Books translated (VI bilingual readers):** 16 / 70 target
- **Known gap:** Xing Yi Nei Gong per-book images (99.6 MB) not pushed — exceeds practical push size

---

## 4. Verification Performed (all cache-busted, `?v=<timestamp>` + no-cache headers)

### taichinow.github.io
- `git ls-remote origin main` == local HEAD (`b851113`) ✓
- 73/73 hosted PDFs return 200 (swept in parallel) ✓
- 30/30 VI readers: iframe → correct `/books/pdfs/<slug>.pdf`, `navpanes=0` ✓
- 72/72 EN readers with hosted PDFs: inline reader present ✓
- 13/13 daoist readers fixed (11 → PDF, 2 oversized → notice) ✓
- Slop sweep on sampled pages: 0 hits for `localhost:8765`, `serve.py`, `Tên tệp PDF`, `Online reader status` ✓
- Landing pages 200: `/tai-chi/`, `/thai-cuc-quyen/`, `/daoist/`, `/books/` ✓

### taichikb.github.io
- `git ls-remote origin main` == local HEAD (`0618063`) ✓
- Per-book image URLs live (baguazhang-vol1, chen-style-handout, how-stuff-works, bat-quai-quyen-chuong) ✓
- Book pages reference only their own subfolder images (0 legacy refs in migrated books) ✓
- 39 rotated images verified by brightness differential ✓

---

## 5. Outstanding Items

1. **3 oversized PDFs** not hosted on taichinow (Xing Yi 99.5 MB, Daoist Plant 121 MB, Mantak Chia 230 MB) — options: Git LFS, split volumes, or external hosting
2. **Xing Yi Nei Gong per-book images** (99.6 MB) not on taichikb — HTML still uses legacy shared images for this book
3. **Baguazhang Vol.2** — no source PDF exists anywhere on disk; reader shows placeholders
4. **Book translations** — 16/70 complete on taichikb; ~44 translatable remain (12 PDFs are image-only scans needing OCR)
5. **CDN propagation** — GitHub Pages / Fastly lag runs 10–15+ min behind push; all verification above was done after propagation confirmed
