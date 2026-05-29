from fastapi import APIRouter
from backend.services.neo4j_service import get_schema

router = APIRouter()

EXAMPLE_QUESTIONS = [
    "Show flights from Delhi (DEL) to London (LHR) operated by Air India (AI)",
    "Which long-haul flights from Delhi (DEL) use the Boeing 777-300ER (77W)?",
    "Find direct flight paths from India to Germany operated by Air India (AI)",
    "Which airlines based in the United Arab Emirates fly to India?",
    "What plane models and airlines are used on flights between Delhi (DEL) and Singapore (SIN)?",
    "Find flight routes from Delhi (DEL) to London (LHR) with 1 layover, bypassing the Middle East",
    "Find flight routes from Mumbai (BOM) to New York (JFK) with exactly 1 layover",
]


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/schema")
async def schema():
    return await get_schema()


@router.get("/examples")
async def examples():
    return {"examples": EXAMPLE_QUESTIONS}
