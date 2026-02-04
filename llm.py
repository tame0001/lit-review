import httpx
from dotenv import dotenv_values


def read_api_key() -> str:
    config = dotenv_values(".env")
    api_key = config.get("GENAI_API_KEY")
    if not api_key:
        raise ValueError("GENAI_API_KEY is not set in .env file")
    return api_key


async def send_request(prompt: str) -> httpx.Response:
    api_key = read_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": "llama4:latest",
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url="https://genai.rcac.purdue.edu/api/chat/completions",
                headers=headers,
                json=body,
                timeout=300,
            )
        return response

    except httpx.TimeoutException as e:
        raise RuntimeError(f"Request timed out: {e}") from e

    except httpx.RequestError as e:
        raise RuntimeError(f"An error occurred while requesting: {e}") from e


async def is_agtech_abstract(abstract_text: str) -> str:
    prompt = f"""
    From the abstract I am going to give to you, can you tell me if the abstract is talking about agricultural technology or not? 
    If yes, state which sentences that has to do with agricultural technology.
    Do not provide any explanations, just answer "Yes" or "No" followed by the sentences if applicable.
    Abstract: {abstract_text}
    """

    response = await send_request(prompt)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        raise RuntimeError(f"Error: {response.status_code}, {response.text}")
