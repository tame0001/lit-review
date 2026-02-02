import zotero
import shutil
import polars as pl
from dotenv import dotenv_values
from pathlib import Path
from tqdm import tqdm


TARGET_COLLECTION_ID = "INADL5PC"
PDF_TARGET_DIR = Path("./pdfs")
PDF_DOWNLOAD_DIR = Path("/home/tam/Zotero/storage")

if __name__ == "__main__":
    # Initialize Zotero client
    config = dotenv_values(".env")
    zot = zotero.create_zotero_client(config)
    # Retrieve all items including sub-collections
    items = zotero.get_all_items(zot, TARGET_COLLECTION_ID)

    # Check for PDF attachments for each item
    print(f"Found {len(items)} items. processing...")
    for item in tqdm(items):
        # Skip items that are not in the target collection (it is not a main item)
        if TARGET_COLLECTION_ID not in item.collections:
            continue
        # TODO: Check data in cache before making API call
        meta = zotero.get_item(zot, item.id)
        if attachment := meta["links"].get("attachment", None):
            if attachment.get("attachmentType", None) == "application/pdf":
                # Extract PDF to target directory
                pdf_location = PDF_DOWNLOAD_DIR / attachment["href"].split("/")[-1]
                if pdf_location.exists():
                    # List files in the directory and find the PDF
                    files = [
                        file
                        for file in pdf_location.iterdir()
                        if file.is_file() and file.suffix == ".pdf"
                    ]
                    try:
                        # Copy the PDF to target location with DOI as filename
                        target_location = (
                            PDF_TARGET_DIR
                            / f"{item.short_author} - {item.date.year} - {item.id}.pdf"
                        )
                        if len(files) == 1:
                            shutil.copy(files[0], target_location)
                            item.pdf = True
                        else:
                            print(f"Multiple or no PDF files found for item {item.id}")
                    except Exception as e:
                        print(f"Error copying PDF for item {item.id}: {e}")

    df = pl.DataFrame(items)
    # Filter item that collection matches TARGET_COLLECTION_ID
    # It means that item is the direct member of the collection (not attachments)
    df_title = df.filter(pl.col("collections").str.contains(TARGET_COLLECTION_ID))
    # Remove duplicates based on doi column
    df_title = df_title.unique(subset=["DOI"], keep="any")

    # Author column is list of list of strings, flatten it
    df_title = df_title.with_columns(
        pl.col("authors")
        .map_elements(
            lambda authors: [author[0] for author in authors],
            return_dtype=pl.List(pl.String),
        )
        .alias("authors")
    )
    print(df_title)

    # Flatten authors column to string before export to CSV
    df_title = df_title.with_columns(
        pl.col("authors")
        .map_elements(lambda authors: ", ".join(authors), return_dtype=pl.String)
        .alias("authors"),
    )
    df_title.write_csv("zotero_items.csv")
