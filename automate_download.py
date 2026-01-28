import zotero
from dotenv import dotenv_values

TARGET_COLLECTION_ID = "INADL5PC"

if __name__ == "__main__":
    # Initialize Zotero client
    config = dotenv_values(".env")
    zot = zotero.create_zotero_client(config)
    for item in zotero.get_all_items(zot, TARGET_COLLECTION_ID):
        print(f"Item: {item.title} (ID: {item.id})")
        print(zotero.get_item(zot, item.id))
