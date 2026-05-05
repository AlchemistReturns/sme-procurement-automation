from fastapi import APIRouter, HTTPException, status
from uuid import UUID, uuid4
from schemas.procurement import BOMLineItemCreate, BOMLineItemResponse
from core_agents.master_agent import run_master_agent

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
    # Call the Master Agent
    master_result = await run_master_agent(
        category=item.category, 
        description=item.sku_or_description, 
        quantity=item.quantity
    )
    
    vd = master_result["validation_details"] or {}
    
    response = BOMLineItemResponse(
        id=uuid4(),
        **item.model_dump(),
        master_status=master_result["status"],
        master_message=master_result["message"],
        confidence_score=vd.get("confidence_score"),
        requires_human_review=vd.get("confidence_score", 1.0) < 0.75,
        reasoning=vd.get("reasoning"),
        suggested_category=vd.get("suggested_category")
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
