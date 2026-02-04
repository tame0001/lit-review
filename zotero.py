import polars as pl
from dotenv import dotenv_values
from datetime import date
from pydantic.dataclasses import dataclass
from pyzotero import zotero


@dataclass
class ZoteroCollection:
    """
    Represents a Zotero collection with its ID, name, and parent collection ID.
    """

    id: str
    name: str
    parent: str | bool | None


@dataclass
class ZoteroAuthor:
    """
    Represents a Zotero author with their name and type.
    """

    name: str

    def __repr__(self):
        return self.name


@dataclass
class ZoteroItem:
    """
    Represents a Zotero item
    """

    id: str
    author_short: str | None
    authors: list[ZoteroAuthor]
    title: str
    type: str | None
    publication: str | None
    date: date | None
    DOI: str | None
    url: str | None
    collections: str = ""
    pdf: bool = False
    abstract: str | None = None


def create_zotero_client(config, library_type="group") -> zotero.Zotero:
    """
    Create a Zotero client using the API key and library ID from configuration.
    By default, it connects to a group library.
    """

    if "ZOTERO_API_KEY" not in config or "ZOTERO_LIBRARY_ID" not in config:
        raise ValueError("ZOTERO_API_KEY or ZOTERO_LIBRARY_ID not set.")
    return zotero.Zotero(
        config["ZOTERO_LIBRARY_ID"], library_type, config["ZOTERO_API_KEY"]
    )


def get_all_collections(zot, collection_id) -> list[ZoteroCollection]:
    """
    Retrieve all nested collections under a specific Zotero collection.
    There is a built-in method `zot.all_collections(collection_id)` that retrieves sub-collections.
    This function will return a list of dictionaries with collection ID, name, and parent ID.
    """
    collections: list[ZoteroCollection] = []
    for collection in zot.all_collections(collection_id):
        collections.append(
            ZoteroCollection(
                id=collection["data"]["key"],
                name=collection["data"]["name"],
                parent=collection["data"]["parentCollection"],
            )
        )
    return collections


def extract_author_details(author_data) -> ZoteroAuthor:
    """
    Extract author details from the Zotero author data.
    Returns a list of ZoteroAuthor objects.
    """
    try:
        if "name" in author_data.keys():
            return ZoteroAuthor(
                name=author_data["name"],
            )

        else:
            return ZoteroAuthor(
                name=f"{author_data.get('firstName', '')} {author_data.get('lastName', '')}",
            )

    except Exception as e:
        print(author_data)
        print(f"Error extracting author details: {e}")
        return ZoteroAuthor(name="Unknown Author")


def get_all_items(zot, collection_id) -> list[ZoteroItem]:
    """
    Retrieve items from a specific Zotero collections including sub-collections.
    This function will return a list of items.
    """
    items = []
    # TODO: Should implement this task with asynchronous calls for better performance
    for collection in get_all_collections(zot, collection_id):
        # TODO: Write raw data in the database for caching
        for item in zot.collection_items(collection.id):
            items.append(
                ZoteroItem(
                    id=item["data"]["key"],
                    title=item["data"].get("title", ""),
                    author_short=item["meta"].get("creatorSummary"),
                    authors=[
                        extract_author_details(author)
                        for author in item["data"].get("creators", [])
                    ],
                    type=item["data"].get("itemType"),
                    publication=item["data"].get("publicationTitle"),
                    date=item["data"].get("date"),
                    DOI=item["data"].get("DOI"),
                    url=item["data"].get("url"),
                    collections=",".join(item["data"].get("collections", [])),
                    abstract=item["data"].get("abstractNote"),
                )
            )

    return items


def get_item(zot, id) -> dict:
    """
    Retrieve a raw data specific item by its ID.
    """
    return zot.item(id)


if __name__ == "__main__":
    # Initialize Zotero client
    config = dotenv_values(".env")
    zot = create_zotero_client(config)

    # Retrieve all items including sub-collections
    items = get_all_items(zot, config["COLLECTION_ID"])
    df = pl.DataFrame(items)
    print(df)

    # Example: Retrieve item by DOI
    doi = "10.1007/s10460-025-10793-2"
    item = df.filter(pl.col("DOI") == doi)
    print(item)
