# ✈️ AirGraph — Multi-Node GraphRAG Aviation Demo

> **Prove that graph traversal beats vector RAG for complex routing and relationship-heavy aviation queries — visually, interactively, in real time.**

AirGraph is a demo application built on **OpenFlights aviation data** and **Neo4j AuraDB**. Ask a natural-language question, watch a force-directed graph animate on screen, read the generated Cypher query, and get an AI answer — all powered by graph traversal, zero embeddings.

![AirGraph Interactive Demo](./assets/video_demo.gif)

---

## 🧠 What is GraphRAG?

Standard RAG splits documents into chunks, embeds them, and retrieves the most similar ones. It works well for *"What is the altitude of Delhi Airport?"* — but completely breaks down for relational and pathing questions like:

- *"Which airlines based in the United Arab Emirates operate flights to India?"* → requires set intersection connecting countries, airlines, and airports
- *"Find flight routes from Delhi to London with 1 layover, bypassing the Middle East"* → requires exclusion reasoning over transit countries
- *"What plane models and airlines are used on flights between Delhi and Singapore?"* → requires multi-node clustering and property joins

**No chunk size, no re-ranking strategy, no retrieval k can fix this.** The operations are structurally absent from the vector RAG paradigm. Graph traversal is the only answer.

---

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph User["👤 User"]
        Browser["🌐 Browser\nlocalhost:8501"]
    end

    subgraph Frontend["🖥️ Frontend — Streamlit (port 8501)"]
        UI["app.py\n─────────────\n• Health check on load\n• 3-column layout\n• Example question buttons\n• agraph canvas\n• Session state\n• Slate Light Theme"]
    end

    subgraph Backend["🔙 Backend — FastAPI (port 8000)"]
        direction TB
        Main["main.py\nFastAPI + CORS"]
        RouteQ["routes/query.py\nPOST /api/query"]
        RouteS["routes/schema.py\nGET /api/schema\nGET /api/examples\nGET /health"]
        LLM["services/llm_service.py\n─────────────\ngenerate_cypher()\nsynthesize_answer()\n• Dual Provider Router"]
        Neo4jSvc["services/neo4j_service.py\n─────────────\nrun_cypher()\nbuild_graph_data()\nget_schema()"]
        Prompt["prompts/cypher_prompt.py\n─────────────\nSystem prompt\nFew-shot examples"]

        Main --> RouteQ
        Main --> RouteS
        RouteQ --> LLM
        RouteQ --> Neo4jSvc
        LLM --> Prompt
    end

    subgraph External["☁️ External Services"]
        LLMProvider["🤖 OpenAI GPT-4o / Gemini 3.1 Flash Lite"]
        Neo4j["🗄️ Neo4j AuraDB"]
        OpenFlights["✈️ OpenFlights raw database"]
    end

    subgraph Seed["🌱 Seed Script"]
        SeedScript["seed/load_airports.py\nFetch → Parse → Load"]
    end

    Browser -->|"HTTP"| UI
    UI -->|"httpx POST /api/query"| Main
    UI -->|"httpx GET /api/health\n/schema · /examples"| Main
    LLM -->|"Chat Completions / GenAI API"| LLMProvider
    Neo4jSvc -->|"Async Cypher"| Neo4j
    SeedScript -->|"Fetch airports, routes, airlines, planes"| OpenFlights
    SeedScript -->|"MERGE multi-node graph"| Neo4j

    style Frontend fill:#e3f2fd,stroke:#1565c0
    style Backend fill:#fff3e0,stroke:#e65100
    style External fill:#fce4ec,stroke:#c62828
    style Seed fill:#e8eaf6,stroke:#3949ab
```

---

## 🔄 Request Flow

```mermaid
sequenceDiagram
    actor User
    participant ST as 🖥️ Streamlit
    participant FA as 🔙 FastAPI
    participant LLM as 🤖 LLM Router (Gemini/OpenAI)
    participant N4J as 🗄️ Neo4j AuraDB

    User->>ST: Types question & clicks Ask
    ST->>FA: POST /api/query {"question": "..."}
    FA->>LLM: System prompt + schema + question
    Note over LLM: Generates Cypher query
    LLM-->>FA: "MATCH (a:Airport)..."
    FA->>N4J: Execute Cypher (async)
    Note over N4J: Graph traversal — walks edges
    N4J-->>FA: Raw records (nodes + relationships)
    FA->>FA: build_graph_data(records)
    FA->>LLM: Question + Cypher + raw results
    Note over LLM: Synthesizes conversational answer
    LLM-->>FA: Natural language answer
    FA-->>ST: {answer, cypher, graph_data, meta}
    ST-->>User: Live graph + Answer + Cypher
```

---

## 🗄️ Graph Schema

```mermaid
graph LR
    Airport["✈️ Airport\n──────\ncode · name\ncity · lat · lon"]
    Country["🌍 Country\n──────\nname"]
    Airline["🛩️ Airline\n──────\ncode · name"]
    Plane["🛫 Plane\n──────\ncode · name"]

    Airport -->|"IN_COUNTRY"| Country
    Airline -->|"IN_COUNTRY"| Country
    Airport -->|"FLIGHT_TO {distance_km, airline, plane}"| Airport

    style Airport fill:#007AFF,color:#fff,stroke:#0051a8
    style Country fill:#34C759,color:#fff,stroke:#1e8236
    style Airline fill:#FF9500,color:#fff,stroke:#b86c00
    style Plane fill:#AF52DE,color:#fff,stroke:#713496
```

---

## ✨ Features

- 🔍 **Natural language → Cypher** — Generates high-performance Cypher queries automatically
- 🕸️ **Live graph visualization** — Colorful, animated force-directed subgraphs rendered for every query
- 💬 **Conversational answers** — Synthesizes complex transit details into comprehensive, reader-friendly flight summaries
- ⚡ **7 live example questions** — Ready-to-go templates spanning carriers, direct routes, countries, and planes
- 🎨 **Color-coded light theme UI** — Sleek Apple-style design system tailored for daytime visual clarity
- 🚀 **Dual Provider Dynamic Router** — Switch between Gemini 3.1 Flash Lite and OpenAI GPT-4o seamlessly inside `.env`

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| 🔙 **Backend** | Python 3.11+, FastAPI |
| 🤖 **LLM** | OpenAI GPT-4o / Gemini 3.1 Flash Lite |
| 🗄️ **Graph DB** | Neo4j AuraDB (free tier) |
| 🖥️ **Frontend** | Streamlit |
| 📊 **Graph Viz** | streamlit-agraph |
| 🌐 **HTTP Client** | httpx |

> **100% Python.** No Node.js, no Docker, no npm. A single `pip install -r requirements.txt` installs everything.

---

## 📋 Prerequisites

Before you start, make sure you have:

| Requirement | Notes |
|---|---|
| 🐍 **Python 3.11+** | Check with `python3 --version` |
| ☁️ **Neo4j AuraDB account** | Free tier at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/) — no local install needed |
| 🔑 **LLM Provider API key** | Gemini API key at [ai.google.dev](https://ai.google.dev/) or OpenAI key at [platform.openai.com](https://platform.openai.com/) |

---

## 🚀 Getting Started

### Step 1 — Clone & Install

```bash
cd airgraph
pip install -r requirements.txt
```

### Step 2 — Configure Credentials

Configure `.env` in `airgraph/` directory:

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

*(Alternatively, set `LLM_PROVIDER=openai` and specify `OPENAI_API_KEY`)*

### Step 3 — Seed the Database

```bash
python3 seed/load_airports.py
```

This fetches raw databases from OpenFlights, filters the aviation network around India + selective international hubs (safely keeping element counts well under free-tier limits), computes physical flight distances using the **Haversine formula**, and seeds the multi-node property graph in less than 30 seconds!

### Step 4 — Start the Backend

```bash
# Terminal 1
python3 -m uvicorn backend.main:app --reload
```

Backend runs at **http://localhost:8000**

### Step 5 — Start the Frontend

```bash
# Terminal 2
python3 -m streamlit run frontend/app.py
```

Open **http://localhost:8501** in your browser. 🎉

---

## 🗂️ Project Structure

```
airgraph/
│
├── 🔙 backend/
│   ├── main.py                  # FastAPI app · CORS · route registration
│   ├── config.py                # Pydantic Settings · Loads credentials
│   ├── models.py                # Pydantic request & response models
│   │
│   ├── routes/
│   │   ├── query.py             # POST /api/query — LLM router + Neo4j orchestration
│   │   └── schema.py            # GET /api/schema · /api/examples · /health
│   │
│   ├── services/
│   │   ├── neo4j_service.py     # Async Neo4j driver · Cypher execution · graph visualizer builder
│   │   ├── llm_service.py       # Dual provider router dispatch
│   │   ├── openai_service.py    # OpenAI chat synthesis interface
│   │   └── gemini_service.py    # Gemini GenAI chat synthesis interface
│   │
│   └── prompts/
│       └── cypher_prompt.py     # Schema prompts · few-shot aviation Cypher examples
│
├── 🖥️ frontend/
│   ├── app.py                   # Entire Streamlit UI in one file
│   └── .streamlit/
│       └── config.toml          # Light theme aesthetic override configuration
│
├── 🌱 seed/
│   └── load_airports.py         # Downloads OpenFlights data → builds & seeds multi-node Neo4j graph
│
├── requirements.txt             # All Python dependencies
└── README.md                    # This document
```

---

## 🎯 Demo Walkthrough

Click the sidebar example questions to see GraphRAG in action:

| # | Question | Why it needs graph traversal |
|---|---|---|
| 1️⃣ | *Show flights from Delhi (DEL) to London (LHR) operated by Air India (AI)* | Warmup — matches direct routes filtering for specific carrier codes. |
| 2️⃣ | *Which long-haul flights from Delhi (DEL) use the Boeing 777-300ER (77W)?* | 🌟 **Visually stunning** — branches out DEL to multiple airports along with the 77W Plane node! |
| 3️⃣ | *Find direct flight paths from India to Germany operated by Air India (AI)* | Multi-hop country matching: traces airport nodes, country nodes, and carrier node in one flow. |
| 4️⃣ | *Which airlines based in the United Arab Emirates fly to India?* | Traces Middle East airline headquarters and maps them to all destination airports inside India. |
| 5️⃣ | *What plane models and airlines are used on flights between Delhi (DEL) and Singapore (SIN)?* | Property joins and multi-node mapping showing airlines and plane clusters. |
| 6️⃣ | *Find flight routes from Delhi (DEL) to London (LHR) with 1 layover, bypassing the Middle East* | Exclusion reasoning — filters out countries inside the path (impossible for vector RAG). |
| 7️⃣ | *Find flight routes from Mumbai (BOM) to New York (JFK) with exactly 1 layover* | High-performance multi-path traversal mapping out optimal layovers (London, Frankfurt, Paris, Dubai). |

---

## ❓ Why Not Vector RAG?

Vector RAG retrieves text chunks by embedding similarity. It fails on relational queries because:

**🔗 Complex layovers (Q7):** A flight route with layovers represents a *directed path* across multiple independent flight legs. No text chunk contains this path. Retrieval by similarity gives you a list of independent flight tables, not a structured traversal route. Only a graph database can walk relationships to map paths dynamically.

**🚫 Logical exclusions (Q6):** Finding flights that bypass the Middle East requires computing paths and applying negative logical constraints on the country property of layover airports. It is a structural graph operation. It cannot be approximated by embeddings or vector similarities.

---

## 📡 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness check |
| `GET` | `/api/schema` | Neo4j node labels, relationship types, property keys |
| `GET` | `/api/examples` | The 7 demo questions |
| `POST` | `/api/query` | Main endpoint: question → Cypher → answer + graph data |

---

*Built with ❤️ to show that for aviation routing and complex multi-node constraints, the graph wins.*
