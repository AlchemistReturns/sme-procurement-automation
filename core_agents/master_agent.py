from agents import Agent, Runner, function_tool, ToolCallOutputItem
from core_agents.bom_input_agent import validate_bom_item, BOMValidationResult
from core_agents.supplier_discovery_agent import run_supplier_discovery, SupplierDiscoveryResult
from dotenv import load_dotenv

load_dotenv(override=True)

CONFIDENCE_THRESHOLD = 0.75

system_prompt = """You are the Master Procurement Agent. Your job is to orchestrate the procurement pipeline.
You receive Bill of Materials (BOM) items from the user.
Step 1: You MUST first validate any new BOM items using the `validate_bom` tool.
Step 2: Evaluate the result from the `validate_bom` tool.
- If the tool returns a confidence score < 0.75, you must STOP and return a message asking for human review, clearly stating the reasoning provided by the tool.
- If the confidence score is >= 0.75, you MUST call the `discover_suppliers` tool with the same item details.
Step 3: Present the supplier discovery results clearly, listing each supplier with their website and contact info.

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


_agent = Agent(
    name="Master Procurement Agent",
    instructions=system_prompt,
    tools=[validate_bom, discover_suppliers],
)


async def run_master_agent(category: str, description: str, quantity: int):
    result = await Runner.run(
        _agent,
        f"Please process this new BOM item:\nCategory: {category}\nDescription: {description}\nQuantity: {quantity}",
    )

    val_result = None
    supplier_result = None
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
                except Exception:
                    pass

    status = "Error"
    if val_result:
        status = "Requires Human Review" if val_result.confidence_score < CONFIDENCE_THRESHOLD else "Ready for Discovery"

    return {
        "status": status,
        "message": result.final_output,
        "validation_details": val_result.model_dump() if val_result else None,
        "supplier_discovery": supplier_result.model_dump() if supplier_result else None,
    }
