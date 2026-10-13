import os
from pypdf import PdfReader, PdfWriter

TARGET_FOLDER = "/home/nirmata/Documents/medbook 2"
CHUNK_PAGES = 400

# Look for the original unsplit book
# If the original file has a specific name, enter it here directly:
INPUT_PDF = os.path.join(TARGET_FOLDER, "/home/nirmata/Documents/medbook 2/Harrison&_039_s Principles of Internal Medicine (19th Ed) (Vols 1 &amp_ 2){Dennis Kasper, Anthony Fauci, Stephen Hauser, Dan Longo, J. Jameson, Joseph Loscalzo}(2015){106178487} libgen.li.pdf")

# If you don't know the exact name, auto-detect the largest PDF in the folder
if not os.path.exists(INPUT_PDF):
    candidates = [
        os.path.join(TARGET_FOLDER, f)
        for f in os.listdir(TARGET_FOLDER)
        if f.endswith(".pdf") and not f.startswith("harrisonpart")
    ]
    if not candidates:
        raise FileNotFoundError(f"Original source PDF not found in {TARGET_FOLDER}")
    # Pick the largest file (the original ~121 MB book)
    INPUT_PDF = max(candidates, key=os.path.getsize)

print(f"Reading: {INPUT_PDF}")
reader = PdfReader(INPUT_PDF)
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

part_number = 1
for start_idx in range(0, total_pages, CHUNK_PAGES):
    end_idx = min(start_idx + CHUNK_PAGES, total_pages)
    writer = PdfWriter()
    
    for page_num in range(start_idx, end_idx):
        writer.add_page(reader.pages[page_num])
        
    out_filename = os.path.join(TARGET_FOLDER, f"harrisonpart{part_number}.pdf")
    with open(out_filename, "wb") as f:
        writer.write(f)
        
    print(f"Created: {out_filename} (pages {start_idx + 1} to {end_idx})")
    part_number += 1

print("\nSplitting complete!")