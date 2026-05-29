from backend.config import settings
from backend.services import openai_service, gemini_service

def format_cypher(query: str) -> str:
    """Standardizes spacing and formats Cypher clauses onto newlines for readability."""
    query = " ".join(query.split())
    clauses = ["MATCH", "WHERE", "WITH", "RETURN", "ORDER BY", "LIMIT"]
    for clause in clauses:
        for c in [clause, clause.lower()]:
            query = query.replace(f" {c} ", f"\n{c} ")
            # Handle if it is near the end or before braces
            query = query.replace(f" {c}(", f"\n{c}(")
            if query.endswith(f" {c}"):
                query = query[:-len(c)-1] + f"\n{c}"
    return query.strip()


async def generate_cypher(question: str) -> str:
    """Delegates Cypher query generation to the active LLM provider and formats it."""
    provider = settings.llm_provider.lower().strip()
    if provider == "openai":
        raw_query = await openai_service.generate_cypher(question)
    elif provider == "gemini":
        raw_query = await gemini_service.generate_cypher(question)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}. Must be 'openai' or 'gemini'.")
    
    return format_cypher(raw_query)


async def synthesize_answer(question: str, cypher: str, results: list[dict]) -> str:
    """Delegates answer synthesis to the active LLM provider."""
    provider = settings.llm_provider.lower().strip()
    if provider == "openai":
        return await openai_service.synthesize_answer(question, cypher, results)
    elif provider == "gemini":
        return await gemini_service.synthesize_answer(question, cypher, results)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}. Must be 'openai' or 'gemini'.")
