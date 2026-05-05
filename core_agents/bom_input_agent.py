import os
from openai import AsyncOpenAI
import json
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(override=True)

# We'll use the environment variable OPENAI_API_KEY
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class BOMValidationResult(BaseModel):
    confidence_score: float = Field(..., description="A score between 0.0 and 1.0 representing confidence in the part description and category match.")
    requires_human_review: bool = Field(..., description="True if the confidence score is below 0.75 or if the part is highly ambiguous.")
    reasoning: str = Field(..., description="Explanation for the confidence score and any potential issues found.")
    suggested_category: str = Field(None, description="If the category provided seems incorrect, suggest the correct one.")

async def validate_bom_item(category: str, sku_or_description: str, quantity: int) -> BOMValidationResult:
    """
    Validates a BOM line item using OpenAI.
    """
    system_prompt = (
        "You are an expert procurement agent. Your job is to validate Bill of Materials (BOM) line items.\n"
        "Analyze the provided item category, SKU/description, and quantity.\n"
        "1. Does the description make sense for the given category?\n"
        "2. Is the SKU/description specific enough to source from suppliers?\n"
        "Provide a confidence_score between 0.0 and 1.0.\n"
        "If the score is < 0.75, set requires_human_review to true.\n"
        "Provide your reasoning."
    )
    
    user_prompt = f"Category: {category}\nSKU/Description: {sku_or_description}\nQuantity: {quantity}"

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_schema", "json_schema": {"name": "BOMValidationResult", "schema": BOMValidationResult.model_json_schema()}},
            temperature=0.2
        )
        
        result_json = response.choices[0].message.content
        result_dict = json.loads(result_json)
        return BOMValidationResult(**result_dict)
    except Exception as e:
        # Fallback in case of failure
        print(f"Error calling OpenAI: {e}")
        return BOMValidationResult(
            confidence_score=0.0,
            requires_human_review=True,
            reasoning=f"Failed to validate with AI: {str(e)}"
        )
