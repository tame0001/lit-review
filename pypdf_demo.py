# Experiment script for pypdf version 6.4.0
from pypdf import PdfReader
from pathlib import Path

path = Path(__file__).parent / "sample.pdf"

reader = PdfReader(path)
meta = reader.metadata
print(meta)

xmp = reader.xmp_metadata
print(xmp.dc_title)
print(xmp.dc_creator)

page = reader.pages[1]
text = page.extract_text()
print(text)
