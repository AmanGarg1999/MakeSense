#!/usr/bin/env python3
"""
BEST PRACTICE: Clean extraction pipeline for architectural PDFs
Run each step and compare results.
"""
import fitz
import os

PDF_PATH = '/home/huntingvision/MR. ARUN GARG JI_TYPICAL FLOOR _WITH GRID.pdf'
OUT_DIR = '/home/huntingvision/pdf_analysis'
os.makedirs(OUT_DIR, exist_ok=True)

doc = fitz.open(PDF_PATH)
page = doc[0]

print("=" * 60)
print("STEP 1: HIGH-RES RENDER (600 DPI) for Vision Model")
print("=" * 60)
# 600 DPI = 8.33x zoom from 72 DPI base
mat = fitz.Matrix(8.33, 8.33)
pix = page.get_pixmap(matrix=mat)
high_res_path = f'{OUT_DIR}/page_600dpi.png'
pix.save(high_res_path)
print(f"Saved: {high_res_path} ({pix.width}x{pix.height})")

print("\n" + "=" * 60)
print("STEP 2: EXTRACT VECTOR TEXT WITH POSITION (all layers)")
print("=" * 60)
# Try different text extraction modes
for mode in ["text", "dict", "rawdict", "blocks"]:
    print(f"\n--- Mode: {mode} ---")
    if mode == "text":
        print(page.get_text(mode)[:2000])
    elif mode == "dict":
        blocks = page.get_text(mode)["blocks"]
        for b in blocks:
            if "lines" in b:
                for line in b["lines"]:
                    txt = " ".join([s["text"] for s in line["spans"]])
                    if any(kw in txt.upper() for kw in ["BED", "TOILET", "KITCHEN", "DINING", "LIVING", "DRAWING", "BALCONY", "TERRACE", "TEMPLE", "STORE", "UTILITY", "DRESS", "CLOSET", "STAIR", "FRIDGE", "CONSOLE", "POWDER"]):
                        print(f"  [{line['bbox'][0]:.0f},{line['bbox'][1]:.0f}] {txt}")

print("\n" + "=" * 60)
print("STEP 3: SEARCH FOR ANNOTATIONS / FORM FIELDS")
print("=" * 60)
annots = list(page.annots()) if page.annots() else []
print(f"Annotations: {len(annots)}")
for a in annots:
    print(f"  Type: {a.type}, Content: {a.info.get('content', '')}")

print("\n" + "=" * 60)
print("STEP 4: EXTRACT IMAGES (embedded rasters)")
print("=" * 60)
images = page.get_images(full=True)
print(f"Embedded images: {len(images)}")
for i, img in enumerate(images):
    xref = img[0]
    pix = fitz.Pixmap(doc, xref)
    if pix.n < 5:
        pix.save(f'{OUT_DIR}/embedded_img_{i}.png')
    else:
        pix1 = fitz.Pixmap(fitz.csRGB, pix)
        pix1.save(f'{OUT_DIR}/embedded_img_{i}.png')
    print(f"  Image {i}: {pix.width}x{pix.height}, saved")

print("\n" + "=" * 60)
print("STEP 5: LAYER/OCG ANALYSIS")
print("=" * 60)
# Check for Optional Content Groups (layers)
ocgs = doc.get_ocgs()
if ocgs:
    print(f"OCG Layers: {len(ocgs)}")
    for ocg in ocgs:
        print(f"  {ocg}")
else:
    print("No OCG layers found")

print("\n" + "=" * 60)
print("STEP 6: CROP TO DRAWING AREA (remove title block)")
print("=" * 60)
# Drawing area is roughly y=200 to y=2000 (below title block at y>2200)
clip = fitz.Rect(0, 0, page.rect.width, 2100)
mat = fitz.Matrix(4, 4)  # 288 DPI
pix = page.get_pixmap(matrix=mat, clip=clip)
cropped_path = f'{OUT_DIR}/drawing_only_288dpi.png'
pix.save(cropped_path)
print(f"Saved cropped drawing: {cropped_path} ({pix.width}x{pix.height})")

print("\n" + "=" * 60)
print("STEP 7: VECTOR PATH EXTRACTION (walls/doors)")
print("=" * 60)
# Get drawing paths - this shows wall lines as vectors
paths = page.get_drawings()
print(f"Vector paths: {len(paths)}")
# Filter for likely walls (long straight lines)
wall_paths = []
for p in paths:
    if p["rect"].width > 100 or p["rect"].height > 100:
        wall_paths.append(p)
print(f"  Likely wall paths: {len(wall_paths)}")

print("\n" + "=" * 60)
print("RECOMMENDED NEXT STEPS")
print("=" * 60)
print(f"""
1. VISION MODEL (Best for room labels):
   Upload '{high_res_path}' to GPT-4V / Claude / Gemini with prompt:
   "Read all room names, dimensions, and grid positions from this 
   architectural floor plan. Return JSON with grid coordinate, 
   room name, dimensions in ft-in, area."

2. CAD CONVERSION (If source available):
   Ask architect for DWG/DXF - text layers are preserved.

3. MANUAL VERIFICATION (Fastest):
   You confirm: "Bedroom 1 at grid D4 = 13'-0 x 17'-0"
   I build the complete dataset from your corrections.

4. pdfplumber TABLE EXTRACTION:
   Sometimes room schedules are embedded as tables.
""")