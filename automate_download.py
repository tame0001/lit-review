import zotero
import shutil
import llm
import asyncio
import polars as pl
from dotenv import dotenv_values
from pathlib import Path
from tqdm.asyncio import tqdm
from dataclasses import dataclass


@dataclass
class Paper(zotero.ZoteroItem):
    is_agtech: str = ""


TARGET_COLLECTION_ID = "INADL5PC"
PDF_TARGET_DIR = Path("./pdfs")
PDF_DOWNLOAD_DIR = Path("/home/tam/Zotero/storage")


def move_pdf(meta) -> bool:
    """
    Move PDF from source to target location.
    Return True if PDF moved, False otherwise.
    """
    is_completed = False

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
                        / f"{item.author_short} - {item.date.year if item.date else 'Unknown'} - {item.id}.pdf"
                    )
                    if len(files) == 1:
                        shutil.copy(files[0], target_location)
                        is_completed = True
                    else:
                        print(f"Multiple or no PDF files found for item {item.id}")
                except Exception as e:
                    print(f"Error copying PDF for item {item.id}: {e}")

    return is_completed


async def process_papers(papers: list[Paper]):
    """
    Process all papers
    """

    tasks = [process_abstract(paper) for paper in papers]
    await tqdm.gather(*tasks)


async def process_abstract(paper: Paper):
    """
    Process a paper's abstract
    """
    if paper.abstract:
        paper.is_agtech = await llm.is_agtech_abstract(paper.abstract)
    else:
        paper.is_agtech = "No abstract provided."


if __name__ == "__main__":
    # Initialize Zotero client
    config = dotenv_values(".env")
    zot = zotero.create_zotero_client(config)
    # Retrieve all items including sub-collections
    items = zotero.get_all_items(zot, TARGET_COLLECTION_ID)

    print(f"Found {len(items)} items. Processing...")
    # Process each item
    papers: list[Paper] = []
    for item in tqdm(items):
        # Skip items that are not in the target collection (it is not a main item)
        if TARGET_COLLECTION_ID not in item.collections:
            continue
        meta = zotero.get_item(zot, item.id)
        # Convert to paper dataclass for further processing
        paper = Paper(**item.__dict__)
        # Move PDF if exists
        paper.pdf = move_pdf(meta)
        papers.append(paper)

    # Process abstracts
    print(f"Found {len(papers)} papers. Processing ...")
    asyncio.run(process_papers(papers))

    # Create DataFrame
    df = pl.DataFrame(papers)

    # Author column is list of list of strings, flatten it
    df = df.with_columns(
        pl.col("authors")
        .map_elements(
            lambda authors: [author["name"] for author in authors],
            return_dtype=pl.List(pl.String),
        )
        .alias("authors")
    )
    print(df)

    # Flatten authors column to string before export to CSV
    df = df.with_columns(
        pl.col("authors")
        .map_elements(lambda authors: ", ".join(authors), return_dtype=pl.String)
        .alias("authors"),
    )
    df.write_csv(Path(".") / "output" / "zotero_items.csv")
