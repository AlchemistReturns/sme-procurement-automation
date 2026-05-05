from agents import Agent, Runner, function_tool
from core_agents.bom_input_agent import validate_bom_item
from dotenv import load_dotenv

load_dotenv(override=True)

system_prompt = """You are the Master Procurement Agent. Your job is to orchestrate the procurement pipeline.
You receive Bill of Materials (BOM) items from the user.
Step 1: You MUST first validate any new BOM items using the `validate_bom` tool.
Step 2: Evaluate the result from the `validate_bom` tool.
- If the tool returns a confidence score < 0.8, you must STOP and return a message asking for human review, clearly stating the reasoning provided by the tool.
- If the confidence score is >= 0.8, you should state that the item is approved for sourcing and is ready for the Supplier Discovery phase.

Output your final response in clear, concise markdown format."""


async def run_master_agent(category: str, description: str, quantity: int):
    val_result = None

    @function_tool
    async def validate_bom(item_category: str, item_description: str, item_quantity: int) -> str:
        """Validates a BOM item and returns a JSON string with confidence score and reasoning."""
        nonlocal val_result
        val_result = await validate_bom_item(item_category, item_description, item_quantity)
        return val_result.model_dump_json()

    agent = Agent(
        name="Master Procurement Agent",
        instructions=system_prompt,
        tools=[validate_bom],
    )

    result = await Runner.run(
        agent,
        f"Please process this new BOM item:\nCategory: {category}\nDescription: {description}\nQuantity: {quantity}",
    )

    status = "Error"
    if val_result:
        status = "Requires Human Review" if val_result.confidence_score < 0.8 else "Ready for Discovery"

    return {
        "status": status,
        "message": result.final_output,
        "validation_details": val_result.model_dump() if val_result else None,
    }
