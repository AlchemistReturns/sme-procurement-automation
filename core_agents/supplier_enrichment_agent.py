import os
import sys
import json
from pydantic import BaseModel, Field
from typing import Optional
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from core_agents.supplier_discovery_agent import SupplierCandidate
from dotenv import load_dotenv

load_dotenv(override=True)

ENRICHMENT_PROMPT = """You are a Supplier Contact Enrichment Agent.
You receive a list of suppliers (JSON array), each with a name and website URL.
Your job: for each supplier that has a website, fetch its content using Exa's get_contents tool
and extract a contact email and phone number.

Steps:
1. For each supplier with a website, call get_contents with these URLs (as a list):
   - The homepage URL (as given)
   - The homepage URL + "/contact" (e.g. "https://example.com/contact")
   - The homepage URL + "/contact-us"
   Fetch all three in a single get_contents call per supplier.
2. Scan the returned text for email addresses (pattern: x@y.z) and phone numbers.
   Take the first plausible business email and phone found.
3. If a supplier already has contact_email or phone filled in, keep the existing value
   unless you find a clearly better one.
4. Return the full supplier list as a JSON array with the same fields as input,
   with contact_email and phone populated where found. Do not drop any suppliers."""


class EnrichmentResult(BaseModel):
    suppliers: list[SupplierCandidate] = Field(..., description="Enriched supplier list")


NPX = "npx.cmd" if sys.platform == "win32" else "npx"


async def run_supplier_enrichment(suppliers: list[SupplierCandidate]) -> list[SupplierCandidate]:
    suppliers_with_sites = [s for s in suppliers if s.website]
    if not suppliers_with_sites:
        print("[enrichment] no suppliers have websites, skipping enrichment")
        return suppliers

    base_env = dict(os.environ)
    exa_key = os.getenv("EXA_API_KEY", "")

    print(f"[enrichment] enriching {len(suppliers_with_sites)} suppliers via Exa get_contents")

    suppliers_json = json.dumps([s.model_dump() for s in suppliers])

    async with MCPServerStdio(
        name="exa",
        params={
            "command": NPX,
            "args": ["-y", "exa-mcp-server"],
            "env": {**base_env, "EXA_API_KEY": exa_key},
        },
        client_session_timeout_seconds=120,
    ) as exa_server:
        agent = Agent(
            name="Supplier Enrichment Agent",
            instructions=ENRICHMENT_PROMPT,
            mcp_servers=[exa_server],
            output_type=EnrichmentResult,
        )

        result = await Runner.run(
            agent,
            f"Enrich contact details for these suppliers:\n{suppliers_json}",
        )

    enriched = result.final_output.suppliers
    print(f"[enrichment] done. emails found: {sum(1 for s in enriched if s.contact_email)}, phones found: {sum(1 for s in enriched if s.phone)}")
    return enriched
