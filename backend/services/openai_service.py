from openai import AsyncOpenAI
from backend.config import settings
from backend.prompts.cypher_prompt import CYPHER_SYSTEM_PROMPT, ANSWER_SYSTEM_PROMPT

client = None

def get_client():
    global client
    if client is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment or .env file.")
        client = AsyncOpenAI(api_key=settings.openai_api_key)
    return client


async def generate_cypher(question: str) -> str:
    """Ask GPT-4o to produce a Cypher query for the given question."""
    openai_client = get_client()
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": CYPHER_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


async def synthesize_answer(question: str, cypher: str, results: list[dict]) -> str:
    """Ask GPT-4o to turn raw query results into a conversational answer."""
    openai_client = get_client()
    user_content = f"""Question: {question}

Cypher query used:
{cypher}

Query results (raw):
{results}"""

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()
