import time
from fastapi import APIRouter
from backend.models import QueryRequest, QueryResponse, GraphData, Meta
from backend.services import llm_service, neo4j_service

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    question = request.question

    # Step 1: Generate Cypher from the question
    cypher = await llm_service.generate_cypher(question)

    # Step 2: Run the Cypher against Neo4j
    start = time.time()
    records = await neo4j_service.run_cypher(cypher)
    elapsed_ms = int((time.time() - start) * 1000)

    # Step 3: Build graph visualization data (using rich records)
    raw_graph = neo4j_service.build_graph_data(records)
    graph_data = GraphData(**raw_graph)

    # Step 4: Synthesize a natural-language answer (convert to dict format for LLM)
    records_dict = [record.data() for record in records]
    answer = await llm_service.synthesize_answer(question, cypher, records_dict)

    # Estimate hop count from Cypher (count relationship hops [:FLIGHT_TO] or variable paths)
    hop_count = max(cypher.count("->"), cypher.count("<-"), 1)

    return QueryResponse(
        answer=answer,
        cypher=cypher,
        hop_count=hop_count,
        graph_data=graph_data,
        meta=Meta(
            node_count=len(graph_data.nodes),
            edge_count=len(graph_data.edges),
            query_ms=elapsed_ms,
        ),
    )
