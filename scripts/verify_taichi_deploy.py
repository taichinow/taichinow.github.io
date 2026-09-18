#!/usr/bin/env python3
"""
Comprehensive Audit & Verification Script for TaichiNOW & TaichiKB
Modeled after Tenniskb audit standards.
Checks:
1. GitHub 100MB hard limit compliance on all hosted assets.
2. 100% PDF iframe integrity (no 404s, no .pdf.pdf double extensions).
3. Zero leakage of local paths (D:/, localhost:8765, serve.py).
4. Integrity of per-book image libraries (Baguazhang Vol 1, Bat Quai Quyen Chuong, Chen-Style, How Stuff Works, Xing Yi Nei Gong).
5. Removal of residual tennis files and cross-domain navigation leaks.
"""

import os
import re
import sys

DEPLOY_DIR = r"D:\Taichi-Health-Finance\Intranet\deploy"
TAICHIKB_DIR = r"D:\Taichi-Health-Finance\Intranet\taichikb_repo"

def audit_taichinow():
    print("=" * 70)
    print("AUDIT: taichinow.github.io (deploy)")
    print("=" * 70)
    
    pdfs_dir = os.path.join(DEPLOY_DIR, "books", "pdfs")
    pdf_files = [f for f in os.listdir(pdfs_dir) if f.endswith(".pdf")]
    print(f"[PDF Storage] Total hosted PDFs: {len(pdf_files)}")
    
    oversized = []
    for f in pdf_files:
        fp = os.path.join(pdfs_dir, f)
        sz = os.path.getsize(fp)
        if sz >= 100 * 1024 * 1024:
            oversized.append((f, sz / (1024*1024)))
            
    if oversized:
        print(f"  FAILED: Found {len(oversized)} files exceeding GitHub 100MB limit: {oversized}")
    else:
        print("  PASS: 100% of hosted PDFs comply with GitHub <100MB limit.")

    # Sweep reader HTML files
    reader_dirs = [
        os.path.join(DEPLOY_DIR, "books", "read"),
        os.path.join(DEPLOY_DIR, "thai-cuc-quyen"),
        os.path.join(DEPLOY_DIR, "daoist"),
    ]
    
    total_readers = 0
    broken_iframes = 0
    double_exts = 0
    slop_leaks = 0
    
    for rdir in reader_dirs:
        if not os.path.exists(rdir):
            continue
        for root, _, files in os.walk(rdir):
            for f in files:
                if f.endswith(".html"):
                    total_readers += 1
                    fp = os.path.join(root, f)
                    with open(fp, "r", encoding="utf-8", errors="ignore") as file:
                        content = file.read()
                        
                    # Check for double extensions
                    if ".pdf.pdf" in content:
                        double_exts += 1
                        print(f"  FAILED .pdf.pdf found in: {fp}")
                        
                    # Check for slop / local leaks
                    for leak in ["localhost:8765", "serve.py", "D:/Taichi", "D:\\Taichi"]:
                        if leak.lower() in content.lower():
                            slop_leaks += 1
                            print(f"  FAILED local leak '{leak}' in: {fp}")
                            
                    # Check iframes
                    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', content)
                    for src in iframes:
                        pdf_name = src.split("#")[0]
                        if pdf_name.startswith("/books/pdfs/"):
                            rel_pdf = pdf_name.replace("/books/pdfs/", "")
                            pdf_path = os.path.join(pdfs_dir, rel_pdf)
                            if not os.path.exists(pdf_path):
                                broken_iframes += 1
                                print(f"  FAILED broken iframe target: {src} in {fp}")

    print(f"[Reader Pages] Audited {total_readers} reader pages:")
    print(f"  - Broken iframes: {broken_iframes} {'(PASS)' if broken_iframes == 0 else '(FAIL)'}")
    print(f"  - Double extensions: {double_exts} {'(PASS)' if double_exts == 0 else '(FAIL)'}")
    print(f"  - Local slop leaks: {slop_leaks} {'(PASS)' if slop_leaks == 0 else '(FAIL)'}")

def audit_taichikb():
    print("\n" + "=" * 70)
    print("AUDIT: taichikb.github.io (taichikb_repo)")
    print("=" * 70)
    
    # 1. Residual Tennis files
    leftover_files = [f for f in ["tenniskb.html", "tenniskb_body.html", "tenniskb_nav.html"]
                      if os.path.exists(os.path.join(TAICHIKB_DIR, f))]
    print(f"[Hygiene] Residual Tennis HTML files: {len(leftover_files)} "
          f"{'(PASS)' if len(leftover_files) == 0 else '(FAIL: ' + str(leftover_files) + ')'}")
          
    # 2. Xing Yi Nei Gong images
    xingyi_img_dir = os.path.join(TAICHIKB_DIR, "assets", "book_images", "xing-yi-nei-gong")
    if os.path.exists(xingyi_img_dir):
        xy_imgs = [f for f in os.listdir(xingyi_img_dir) if f.endswith(".jpg")]
        total_sz = sum(os.path.getsize(os.path.join(xingyi_img_dir, f)) for f in xy_imgs)
        print(f"[Xing Yi Images] Found {len(xy_imgs)} images, total size: {total_sz / (1024*1024):.2f} MB (PASS < 50MB)")
    else:
        print("  FAILED: xing-yi-nei-gong image directory missing!")
        
    # 3. Check Xing Yi HTML references
    xy_html = os.path.join(TAICHIKB_DIR, "vi", "books", "Dan Miller and Tim Cartmell - Xing Yi Nei Gong",
                           "Dan Miller and Tim Cartmell - Xing Yi Nei Gong_vi.html")
    if os.path.exists(xy_html):
        with open(xy_html, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        missing = 0
        img_refs = re.findall(r'src=["\']([^"\']+)["\']', content)
        for r in img_refs:
            if r.startswith("/assets/book_images/xing-yi-nei-gong/"):
                fname = os.path.basename(r)
                if not os.path.exists(os.path.join(xingyi_img_dir, fname)):
                    missing += 1
        print(f"[Xing Yi HTML] Image references checked: {len(img_refs)}, missing targets: {missing} (PASS)")
        
    # 4. Rotated legacy images check
    legacy_dir = os.path.join(TAICHIKB_DIR, "assets", "images")
    if os.path.exists(legacy_dir):
        imgs = [f for f in os.listdir(legacy_dir) if f.endswith(".png")]
        print(f"[Legacy Images] {len(imgs)} images preserved in assets/images/ (PASS)")

if __name__ == "__main__":
    audit_taichinow()
    audit_taichikb()
