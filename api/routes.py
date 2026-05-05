from fastapi import APIRouter, HTTPException, status
from uuid import UUID, uuid4
from schemas.procurement import BOMLineItemCreate, BOMLineItemResponse
from agents.bom_input_agent import validate_bom_item

router = APIRouter(
    prefix="/procurement",
    tags=["procurement"]
)

# In-memory storage for early Phase 1 stubbing before DB is hooked up
mock_db = {}

@router.post("/items", response_model=BOMLineItemResponse, status_code=status.HTTP_201_CREATED)
async def validate_procurement_item(item: BOMLineItemCreate):
    """
    Validate a single BOM line item for procurement.
    """
    validation_result = await validate_bom_item(
        category=item.category, 
        sku_or_description=item.sku_or_description, 
        quantity=item.quantity
    )
    
    response = BOMLineItemResponse(
        id=uuid4(),
        **item.model_dump(),
        confidence_score=validation_result.confidence_score,
        requires_human_review=validation_result.requires_human_review,
        reasoning=validation_result.reasoning,
        suggested_category=validation_result.suggested_category
    )
    
    mock_db[response.id] = response
    return response

@router.get("/items/{item_id}", response_model=BOMLineItemResponse)
async def get_procurement_item(item_id: UUID):
    """
    Fetch the validation result of a single procurement item.
    """
    if item_id not in mock_db:
        raise HTTPException(status_code=404, detail="Item not found")
        
    return mock_db[item_id]
