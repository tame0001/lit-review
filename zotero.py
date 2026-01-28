import polars as pl
from dotenv import dotenv_values
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
    type: str


@dataclass
class ZoteroItem:
    """
    Represents a Zotero item
    """

    id: str
    title: str
    authors: list[ZoteroAuthor]
    publication: str | None
    date: str | None
    DOI: str | None
    url: str | None
    collections: list[str] | None


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
                type=author_data.get("creatorType", "unknown"),
            )

        else:
            return ZoteroAuthor(
                name=f"{author_data.get('firstName', '')} {author_data.get('lastName', '')}",
                type=author_data.get("creatorType", "unknown"),
            )

    except Exception as e:
        print(author_data)
        print(f"Error extracting author details: {e}")


def get_all_items(zot, collection_id) -> list[ZoteroItem]:
    """
    Retrieve items from a specific Zotero collections including sub-collections.
    This function will return a list of items.
    """
    items = []
    # TODO: Should implement this task with asynchronous calls for better performance
    for collection in get_all_collections(zot, collection_id):
        for item in zot.collection_items(collection.id):
            items.append(
                ZoteroItem(
                    id=item["data"]["key"],
                    title=item["data"].get("title", ""),
                    authors=[
                        extract_author_details(author)
                        for author in item["data"].get("creators", [])
                    ],
                    publication=item["data"].get("publicationTitle"),
                    date=item["data"].get("date"),
                    DOI=item["data"].get("DOI"),
                    url=item["data"].get("url"),
                    collections=item["data"].get("collections", []),
                )
            )
    return items


def get_item(zot, id):
    """
    Retrieve a specific item by its ID.
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
