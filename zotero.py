from pyzotero import zotero
from dotenv import dotenv_values
from pydantic.dataclasses import dataclass


@dataclass
class ZoteroCollection:
    """
    Represents a Zotero collection with its ID, name, and parent collection ID.
    """

    id: str
    name: str
    parent: str | bool | None


@dataclass
class ZoteroItem:
    """
    Represents a Zotero item with its ID, title, and type.
    """

    id: str
    title: str


def create_zotero_client(config, library_type="group"):
    """
    Create a Zotero client using the API key and library ID from configuration.
    By default, it connects to a group library.
    """

    if "ZOTERO_API_KEY" not in config or "ZOTERO_LIBRARY_ID" not in config:
        raise ValueError("ZOTERO_API_KEY or ZOTERO_LIBRARY_ID not set.")
    return zotero.Zotero(
        config["ZOTERO_LIBRARY_ID"], library_type, config["ZOTERO_API_KEY"]
    )


def get_all_collections(zot, collection_id):
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


def get_all_items(zot, collection_id):
    """
    Retrieve items from a specific Zotero collections including sub-collections.
    This function will return a list of items.
    """
    items = []
    for collection in get_all_collections(zot, collection_id):
        items += zot.collection_items(collection.id)
    return items


if __name__ == "__main__":
    # Initialize Zotero client
    config = dotenv_values(".env")
    zot = create_zotero_client(config)
    collections = get_all_collections(zot, config["COLLECTION_ID"])
    for collection in collections:
        print(
            f"Collection: {collection.name} (ID: {collection.id}) parent: {collection.parent})"
        )
    print("------------------------------------------")

    print(zot.item("ARDGYCFD"))
