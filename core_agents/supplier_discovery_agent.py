import os
import sys
from pydantic import BaseModel, Field
from typing import Optional
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv

load_dotenv(override=True)

SUPPLIER_DISCOVERY_PROMPT = """You are a Supplier Discovery Agent for SME procurement.
Given a BOM item (category, description, quantity), find real suppliers.

Step 1: Use the Exa search tool to search for:
  "{description} {category} supplier manufacturer distributor"
  Use neural/semantic search mode for best results.

Step 2: For each promising result (up to 15), use Apollo.io to look up
  the company and retrieve contact email and phone if available.

Step 3: Return your findings as a SupplierDiscoveryResult with the
  search_query used and a list of SupplierCandidate objects.
  Include a short relevance_summary for each supplier explaining why
  they are a good match. If Apollo returns no contacts, leave those fields null."""


class SupplierCandidate(BaseModel):
    name: str = Field(..., description="Company name")
    website: Optional[str] = Field(None, description="Company website URL")
    contact_email: Optional[str] = Field(None, description="Primary contact email")
    phone: Optional[str] = Field(None, description="Primary contact phone number")
    relevance_summary: str = Field(..., description="Why this supplier is a good match for the BOM item")


class SupplierDiscoveryResult(BaseModel):
    suppliers: list[SupplierCandidate] = Field(..., description="Ranked list of supplier candidates")
    search_query: str = Field(..., description="The query used to find suppliers")


NPX = "npx.cmd" if sys.platform == "win32" else "npx"


async def run_supplier_discovery(category: str, description: str, quantity: int) -> SupplierDiscoveryResult:
    base_env = dict(os.environ)
    exa_key = os.getenv("EXA_API_KEY", "")
    apollo_key = os.getenv("APOLLO_API_KEY", "")

    print(f"[supplier_discovery] starting for: {description!r} | category={category} qty={quantity}")
    print(f"[supplier_discovery] EXA_API_KEY present: {bool(exa_key)} | APOLLO_API_KEY present: {bool(apollo_key)}")

    print("[supplier_discovery] spawning exa MCP server...")
    async with MCPServerStdio(
        name="exa",
        params={
            "command": NPX,
            "args": ["-y", "exa-mcp-server"],
            "env": {**base_env, "EXA_API_KEY": exa_key},
        },
        client_session_timeout_seconds=120,
    ) as exa_server:
        print("[supplier_discovery] exa MCP server ready")
        print("[supplier_discovery] spawning apollo MCP server...")
        async with MCPServerStdio(
            name="apollo",
            params={
                "command": NPX,
                "args": ["-y", "@thevgergroup/apollo-io-mcp"],
                "env": {**base_env, "APOLLO_API_KEY": apollo_key},
            },
            client_session_timeout_seconds=120,
        ) as apollo_server:
            print("[supplier_discovery] apollo MCP server ready")

            exa_tools = await exa_server.list_tools()
            apollo_tools = await apollo_server.list_tools()
            print(f"[supplier_discovery] exa tools: {[t.name for t in exa_tools]}")
            print(f"[supplier_discovery] apollo tools: {[t.name for t in apollo_tools]}")

            agent = Agent(
                name="Supplier Discovery Agent",
                instructions=SUPPLIER_DISCOVERY_PROMPT,
                mcp_servers=[exa_server, apollo_server],
                output_type=SupplierDiscoveryResult,
            )

            print("[supplier_discovery] running agent...")
            result = await Runner.run(
                agent,
                f"Find suppliers for this BOM item:\nCategory: {category}\nDescription: {description}\nQuantity: {quantity}",
            )
            print(f"[supplier_discovery] agent done. suppliers found: {len(result.final_output.suppliers)}")

            return result.final_output
