import pdfplumber
from pathlib import Path

path = Path(__file__).parent / "sample.pdf"
with pdfplumber.open(path) as pdf:
    # Extract and print metadata
    metadata = pdf.metadata
    print(metadata)

    # Print number of pages
    num_pages = len(pdf.pages)
    print("Number of pages:", num_pages)
