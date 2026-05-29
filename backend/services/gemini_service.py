from google import genai
from google.genai import types
from backend.config import settings
from backend.prompts.cypher_prompt import CYPHER_SYSTEM_PROMPT, ANSWER_SYSTEM_PROMPT

client = None

def get_client():
    global client
    if client is None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
        client = genai.Client(api_key=settings.gemini_api_key)
    return client


async def generate_cypher(question: str) -> str:
    """Ask Gemini 3.1 Flash Lite to produce a Cypher query for the given question."""
    gemini_client = get_client()
    response = await gemini_client.aio.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=CYPHER_SYSTEM_PROMPT,
            temperature=0.0,
        )
    )
    
    query = response.text.strip()
    # Strip markdown code fences if present
    if query.startswith("```"):
        lines = query.splitlines()
        if len(lines) >= 2:
            if lines[-1].startswith("```"):
                query = "\n".join(lines[1:-1])
            else:
                query = "\n".join(lines[1:])
                
    return query.strip()


async def synthesize_answer(question: str, cypher: str, results: list[dict]) -> str:
    """Ask Gemini 3.1 Flash Lite to turn raw query results into a conversational answer."""
    gemini_client = get_client()
    user_content = f"""Question: {question}

Cypher query used:
{cypher}

Query results (raw):
{results}"""

    response = await gemini_client.aio.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=ANSWER_SYSTEM_PROMPT,
            temperature=0.3,
        )
    )
    return response.text.strip()
