from ollama import chat, ChatResponse


def is_agtech_abstract(abstract_text: str) -> str:
    prompt = f"""
    From the abstract I am going to give to you, can you tell me if the abstract is talking about agricultural technology or not? 
    If yes, state which sentences that has to do with agricultural technology.
    Do not provide any explanations, just answer "Yes" or "No" followed by the sentences if applicable.
    Abstract: {abstract_text}
    """
    response: ChatResponse = chat(
        model="llama3.1:8b",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.message.content or "No response from LLM"
