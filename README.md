# ProcureAI — SME Procurement Automation Backend

AI-powered procurement pipeline that validates Bill of Materials (BOM) items, discovers real suppliers, and enriches contact data — fully automated via multi-agent orchestration.

## Architecture

```
User Input (BOM item)
        │
        ▼
Master Agent (OpenAI Agents SDK)
   ├── validate_bom     → BOM Input Agent   (GPT-4o, structured output)
   ├── discover_suppliers → Supplier Discovery Agent  (Exa MCP + Apollo MCP)
   └── enrich_suppliers  → Supplier Enrichment Agent  (Exa MCP get_contents)
```

**Confidence threshold:** items scoring < 0.75 are flagged for human review and pipeline halts.

## Interfaces

| Interface | Entry point | Default port |
|-----------|-------------|--------------|
| Gradio web UI | `gradio_app.py` | 7860 |
| FastAPI REST API | `main.py` | 8000 |

### REST endpoints
- `POST /api/v1/procurement/items` — submit a BOM item, runs full pipeline
- `GET  /api/v1/procurement/items/{id}` — fetch result by ID
- `GET  /health` — health check

## MCP Servers

| Server | npm package | API key env var | Used by |
|--------|-------------|-----------------|---------|
| **Exa** | `exa-mcp-server` | `EXA_API_KEY` | Supplier discovery (web search) + enrichment (page scraping) |
| **Apollo.io** | `@thevgergroup/apollo-io-mcp` | `APOLLO_API_KEY` | Supplier discovery (company/contact lookup) |

MCP servers are spawned as child processes via `npx` — Node.js must be installed.

## Setup

### Prerequisites
- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ with `npx`

### 1. Clone and install

```bash
git clone <repo-url>
cd backend
uv sync
```

### 2. Configure environment

Copy and fill in API keys:

```bash
cp .env.example .env   # or create .env manually
```

`.env` contents:

```env
OPENAI_API_KEY=sk-...
EXA_API_KEY=...
APOLLO_API_KEY=...
```

| Key | Where to get |
|-----|-------------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/api-keys) |
| `EXA_API_KEY` | [exa.ai](https://exa.ai) |
| `APOLLO_API_KEY` | [apollo.io](https://apollo.io) Settings → API Keys |

### 3. Run

**Gradio UI (recommended for demo):**
```bash
uv run python gradio_app.py
# open http://localhost:7860
```

**FastAPI server:**
```bash
uv run uvicorn main:app --reload
# open http://localhost:8000/docs
```

## Project Structure

```
backend/
├── main.py                          # FastAPI app entry point
├── gradio_app.py                    # Gradio web UI
├── pyproject.toml
├── core_agents/
│   ├── master_agent.py              # Orchestrator — runs the full pipeline
│   ├── bom_input_agent.py           # Validates BOM items via GPT-4o
│   ├── supplier_discovery_agent.py  # Finds suppliers (Exa + Apollo MCP)
│   └── supplier_enrichment_agent.py # Scrapes contact info (Exa MCP)
├── api/
│   └── routes.py                    # FastAPI route handlers
└── schemas/
    └── procurement.py               # Pydantic request/response models
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `openai-agents` | ≥0.15.1 | Agent SDK + MCP client |
| `openai` | ≥2.34.0 | GPT-4o for BOM validation |
| `fastapi` | ≥0.136.1 | REST API |
| `gradio` | ≥6.14.0 | Web UI |
| `uvicorn` | ≥0.46.0 | ASGI server |
| `pydantic` | ≥2.13.3 | Data validation |
