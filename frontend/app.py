import httpx
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

BACKEND = "http://localhost:8000"

# Node colors and sizes by label for premium Light Theme visualization
NODE_COLORS = {
    "Airport": "#007AFF",   # Deep Active Blue
    "Country": "#34C759",   # Vibrant Emerald Green
    "Airline": "#FF9500",   # Premium Soft Orange
    "Plane": "#AF52DE",     # Sleek Violet/Purple
}
NODE_SIZES = {
    "Airport": 25,
    "Country": 22,
    "Airline": 18,
    "Plane": 18,
}

st.set_page_config(page_title="AirGraph", layout="wide")

# ── Health check on startup ──────────────────────────────────────────────────
try:
    httpx.get(f"{BACKEND}/api/health", timeout=2).raise_for_status()
except Exception:
    st.error("⚠️ Backend not reachable. Start it with: python3 -m uvicorn backend.main:app --reload")
    st.stop()


# ── Schema (cached 5 min) ────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_schema():
    return httpx.get(f"{BACKEND}/api/schema", timeout=5).json()


@st.cache_data(ttl=300)
def fetch_examples():
    return httpx.get(f"{BACKEND}/api/examples", timeout=5).json()["examples"]


# ── Session state defaults ───────────────────────────────────────────────────
if "question" not in st.session_state:
    st.session_state.question = ""
if "result" not in st.session_state:
    st.session_state.result = None
if "run_query" not in st.session_state:
    st.session_state.run_query = False


# ── Layout: three columns (wider central column for massive graph canvas) ──────
col1, col2, col3 = st.columns([1, 2.8, 1])

# ── Column 1: Controls ───────────────────────────────────────────────────────
with col1:
    st.title("✈️ AirGraph")
    st.caption("GraphRAG flight routing visualizer")

    question_input = st.text_area(
        "Ask a question about flight paths",
        value=st.session_state.question,
        height=100,
        key="question_input",
    )

    if st.button("Ask", type="primary"):
        st.session_state.question = question_input
        st.session_state.run_query = True

    st.divider()
    st.subheader("Try an example")

    for example in fetch_examples():
        if st.button(example, key=example):
            st.session_state.question = example
            st.session_state.run_query = True
            st.rerun()

    st.divider()
    with st.expander("Graph Schema"):
        schema_data = fetch_schema()
        st.markdown("**Node labels:** " + ", ".join(f"`{l}`" for l in schema_data.get("labels", [])))
        st.markdown("**Relationships:** " + ", ".join(f"`{r}`" for r in schema_data.get("relationship_types", [])))

    st.info(
        "**Why Graph RAG for Aviation?**\n\n"
        "Flight networks are pure graph structures. Standard Vector RAG completely breaks down "
        "when answering routing queries because layover connections span across multiple independent records. "
        "Graph traversal walks the `:FLIGHT_TO` edges directly, calculating exact distances and layover stops in real time."
    )

# ── Run query if flagged ─────────────────────────────────────────────────────
if st.session_state.run_query and st.session_state.question:
    st.session_state.run_query = False
    with col2:
        with st.spinner("Finding optimal routes…"):
            try:
                response = httpx.post(
                    f"{BACKEND}/api/query",
                    json={"question": st.session_state.question},
                    timeout=60,
                )
                st.session_state.result = response.json()
            except Exception as e:
                st.session_state.result = {"error": True, "detail": str(e)}

# ── Column 2: Graph canvas ───────────────────────────────────────────────────
with col2:
    result = st.session_state.result

    if result is None:
        st.info("Ask a routing question or pick an example to visualize the flight map")
    elif result.get("error"):
        st.error(result.get("detail", "Unknown error"))
    else:
        graph_data = result.get("graph_data", {})
        raw_nodes = graph_data.get("nodes", [])
        raw_edges = graph_data.get("edges", [])

        if not raw_nodes:
            st.warning("No routes found matching your query criteria.")
        else:
            agraph_nodes = [
                Node(
                    id=n["id"],
                    label=n["properties"].get("display", n["id"]),
                    size=NODE_SIZES.get(n["label"], 15),
                    color=NODE_COLORS.get(n["label"], "#888888"),
                )
                for n in raw_nodes
            ]
            agraph_edges = [
                Edge(source=e["source"], target=e["target"], label=e.get("type", "FLIGHT_TO"), color="#64748B")
                for e in raw_edges
            ]
            config = Config(
                height=750,
                width="100%",
                directed=True,
                physics=True,
                hierarchical=False,
            )
            agraph(nodes=agraph_nodes, edges=agraph_edges, config=config)

# ── Column 3: Answer + Cypher ────────────────────────────────────────────────
with col3:
    result = st.session_state.result
    if result and not result.get("error"):
        st.subheader("Flight Plan")
        st.markdown(result["answer"])

        st.divider()
        st.subheader("Generated Cypher")
        st.code(result["cypher"], language="cypher")

        st.divider()
        meta = result.get("meta", {})
        m1, m2, m3 = st.columns(3)
        m1.metric("Airports", meta.get("node_count", 0))
        m2.metric("Connections", meta.get("edge_count", 0))
        m3.metric("Time", f"{meta.get('query_ms', 0)} ms")

        st.caption(f"This query traversed {result.get('hop_count', 1)} hop(s) across the global flight network.")
