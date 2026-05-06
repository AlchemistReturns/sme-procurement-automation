import json
from agents import Agent, Runner, function_tool, ToolCallOutputItem
from core_agents.bom_input_agent import validate_bom_item, BOMValidationResult
from core_agents.supplier_discovery_agent import run_supplier_discovery, SupplierDiscoveryResult, SupplierCandidate
from core_agents.supplier_enrichment_agent import run_supplier_enrichment
from dotenv import load_dotenv

load_dotenv(override=True)

CONFIDENCE_THRESHOLD = 0.75

system_prompt = """You are the Master Procurement Agent. Your job is to orchestrate the procurement pipeline.
You receive Bill of Materials (BOM) items from the user.
Step 1: You MUST first validate any new BOM items using the `validate_bom` tool.
Step 2: Evaluate the result from the `validate_bom` tool.
- If the tool returns a confidence score < 0.75, you must STOP and return a message asking for human review, clearly stating the reasoning provided by the tool.
- If the confidence score is >= 0.75, you MUST call the `discover_suppliers` tool with the same item details.
Step 3: Take the suppliers JSON returned by `discover_suppliers` and pass it directly to `enrich_suppliers`.
Step 4: Present the enriched supplier results clearly, listing each supplier with their website, email, and phone.

Output your final response in clear, concise markdown format."""


@function_tool
async def validate_bom(item_category: str, item_description: str, item_quantity: int) -> str:
    """Validates a BOM item and returns a JSON string with confidence score and reasoning."""
    result = await validate_bom_item(item_category, item_description, item_quantity)
    return result.model_dump_json()


@function_tool
async def discover_suppliers(item_category: str, item_description: str, item_quantity: int) -> str:
    """Discovers suppliers for a validated BOM item. Returns a JSON string with supplier candidates."""
    result = await run_supplier_discovery(item_category, item_description, item_quantity)
    return result.model_dump_json()


@function_tool
async def enrich_suppliers(suppliers_json: str) -> str:
    """Enriches supplier list with email and phone scraped from their websites.
    Accepts the JSON string returned by discover_suppliers. Returns enriched JSON array."""
    discovery = SupplierDiscoveryResult.model_validate_json(suppliers_json)
    enriched = await run_supplier_enrichment(discovery.suppliers)
    return json.dumps([s.model_dump() for s in enriched])


_agent = Agent(
    name="Master Procurement Agent",
    instructions=system_prompt,
    tools=[validate_bom, discover_suppliers, enrich_suppliers],
)


async def run_master_agent(category: str, description: str, quantity: int):
    result = await Runner.run(
        _agent,
        f"Please process this new BOM item:\nCategory: {category}\nDescription: {description}\nQuantity: {quantity}",
    )

    val_result = None
    supplier_result = None
    enriched_suppliers = None
    for item in result.new_items:
        if isinstance(item, ToolCallOutputItem):
            if val_result is None:
                try:
                    val_result = BOMValidationResult.model_validate_json(item.output)
                    continue
                except Exception:
                    pass
            if val_result is not None and supplier_result is None:
                try:
                    supplier_result = SupplierDiscoveryResult.model_validate_json(item.output)
                    continue
                except Exception:
                    pass
            if supplier_result is not None and enriched_suppliers is None:
                try:
                    raw = json.loads(item.output)
                    enriched_suppliers = [SupplierCandidate.model_validate(s) for s in raw]
                except Exception:
                    pass

    status = "Error"
    if val_result:
        status = "Requires Human Review" if val_result.confidence_score < CONFIDENCE_THRESHOLD else "Ready for Discovery"

    suppliers_out = enriched_suppliers or (supplier_result.suppliers if supplier_result else None)

    return {
        "status": status,
        "message": result.final_output,
        "validation_details": val_result.model_dump() if val_result else None,
        "supplier_discovery": supplier_result.model_dump() if supplier_result else None,
        "enriched_suppliers": [s.model_dump() for s in suppliers_out] if suppliers_out else None,
    }
