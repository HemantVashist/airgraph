from neo4j import AsyncGraphDatabase
from backend.config import settings

# Single shared driver instance
_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
    return _driver


async def close_driver():
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


async def run_cypher(cypher: str) -> list:
    """Execute a Cypher query and return raw Neo4j Record objects asynchronously."""
    driver = get_driver()
    async with driver.session() as session:
        result = await session.run(cypher)
        records = [record async for record in result]
        return records


async def get_schema() -> dict:
    """Return node labels, relationship types, and property keys, filtered for the aviation schema."""
    driver = get_driver()
    async with driver.session() as session:
        labels_result = await session.run("CALL db.labels()")
        labels = [r["label"] async for r in labels_result]

        rel_result = await session.run("CALL db.relationshipTypes()")
        rel_types = [r["relationshipType"] async for r in rel_result]

        prop_result = await session.run("CALL db.propertyKeys()")
        prop_keys = [r["propertyKey"] async for r in prop_result]

    # Filter to ensure movie/tmdb or other project schemas are excluded if sharing a Neo4j DB
    valid_labels = {"Airport", "Country", "Airline", "Plane"}
    valid_rels = {"IN_COUNTRY", "FLIGHT_TO"}
    valid_props = {"code", "name", "city", "lat", "lon", "distance_km", "airline", "plane"}

    labels = [l for l in labels if l in valid_labels]
    rel_types = [r for r in rel_types if r in valid_rels]
    prop_keys = [p for p in prop_keys if p in valid_props]

    return {"labels": labels, "relationship_types": rel_types, "property_keys": prop_keys}


def build_graph_data(records: list) -> dict:
    """
    Walk raw Neo4j records and extract unique nodes + edges for visualization.
    Handles Node objects, Relationship objects, and Path objects.
    """
    nodes = {}
    edges = []

    def add_node(node):
        nid = str(node.element_id)
        if nid not in nodes:
            label = list(node.labels)[0] if node.labels else "Unknown"
            props = dict(node)
            # Use short 3-letter IATA code if available for display readability
            display = props.get("code") or props.get("title") or props.get("name") or nid
            nodes[nid] = {"id": nid, "label": label, "properties": {**props, "display": display}}

    def add_relationship(rel):
        edges.append({
            "source": str(rel.start_node.element_id),
            "target": str(rel.end_node.element_id),
            "type": rel.type,
        })

    for record in records:
        for value in record.values():
            _process_value(value, add_node, add_relationship)

    return {"nodes": list(nodes.values()), "edges": edges}


def _process_value(value, add_node, add_relationship):
    from neo4j.graph import Node, Relationship, Path

    if isinstance(value, Node):
        add_node(value)
    elif isinstance(value, Relationship):
        add_node(value.start_node)
        add_node(value.end_node)
        add_relationship(value)
    elif isinstance(value, Path):
        for node in value.nodes:
            add_node(node)
        for rel in value.relationships:
            add_node(rel.start_node)
            add_node(rel.end_node)
            add_relationship(rel)
    elif isinstance(value, list):
        for item in value:
            _process_value(item, add_node, add_relationship)
