import llm
import asyncio
import json
import polars as pl
from pathlib import Path
from tqdm.asyncio import tqdm


# Set path

PATH = Path(".")


def process_response(response: str) -> dict:
    """
    Process the response from the LLM and extract the relevant information.
    Return a dictionary with the following structure:
        is_agtech: "Yes" or "No" or "Error" if there is processing is failed
        sentence: The sentence in the abstract that indicates whether it's AgTech or not.
        reason: A brief explanation of why LLM think it's AgTech or not based on the abstract.

    In case of error, the raw response will be stored in the reason field for debugging purposes.
    """
    try:
        # Extract JSON from response
        response = response[response.find("{") : response.rfind("}") + 1]
        response = json.loads(response)
        return {
            "is_agtech": response.get("is_agtech", "Error"),
            "sentence": response.get("sentence", ""),
            "reason": response.get("reason", ""),
        }

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Error decoding JSON: {e}") from e
    except KeyError as e:
        raise RuntimeError(f"Missing expected key in response: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error processing response: {e}") from e

    finally:
        # In case of any error, return the raw response for debugging
        return {
            "is_agtech": "Error",
            "sentence": "",
            "reason": json.dumps(response, indent=2),
        }


async def process_web_of_science_export(file_path):
    """
    Process a Web of Science export file.
    Columns of interest:
    - Publication Type: Indicating the type of publication
    - Document Type: Type of document
    - Authors: List of authors
    - Article Title: Title of the article
    - Source Title: Journal or conference name
    - Conference Title: Name of the conference (if applicable)
    - DOI: Digital Object Identifier
    - Publication Year: Year of publication
    - Publication Date: Full date of publication
    - Abstract: Summary of the article
    """
    wos = pl.read_excel(file_path)
    # Print number of total papers
    print(f"Total papers: {len(wos)}")
    # Remove papers that does not have title, DOI or abstract
    wos = wos.filter(
        (pl.col("Article Title").is_not_null())
        & (pl.col("DOI").is_not_null())
        & (pl.col("Abstract").is_not_null())
    )
    print(f"Papers with title, DOI and abstract: {len(wos)}")
    # Only keep columns of interest
    wos = wos.select(
        [
            "Publication Type",
            "Document Type",
            "Authors",
            "Article Title",
            "Source Title",
            "Conference Title",
            "DOI",
            "Publication Year",
            "Publication Date",
            "Abstract",
        ]
    )
    # Process abstracts
    tasks = [llm.is_agtech_abstract(abstract) for abstract in wos["Abstract"]]
    print("Processed abstracts ...")
    is_agtech = await tqdm.gather(*tasks)
    # Process the responses and extract relevant information
    responses = [process_response(response) for response in is_agtech]
    # Add the extracted information to the DataFrame
    wos = wos.with_columns(
        pl.Series("is_agtech", [response["is_agtech"] for response in responses]),
        pl.Series("agtech_sentence", [response["sentence"] for response in responses]),
        pl.Series("agtech_reason", [response["reason"] for response in responses]),
    )

    # Save to CSV
    wos.write_csv(PATH / "output" / "processed_wos.csv")


if __name__ == "__main__":
    # Load export file from Web of Science
    asyncio.run(process_web_of_science_export(PATH / "export_wos.xls"))
