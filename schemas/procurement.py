from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID, uuid4

class BOMLineItemBase(BaseModel):
    category: str = Field(..., description="The category of the item (e.g., Electronics, Metals)")
    sku_or_description: str = Field(..., description="SKU or detailed description of the part")
    quantity: int = Field(..., gt=0, description="Quantity required")

class BOMLineItemCreate(BOMLineItemBase):
    pass

class BOMLineItemResponse(BOMLineItemBase):
    id: UUID
    confidence_score: Optional[float] = Field(None, description="AI confidence score for validation")
    requires_human_review: bool = False
    reasoning: Optional[str] = Field(None, description="Agent reasoning for the validation score")
    suggested_category: Optional[str] = Field(None, description="Suggested category if the original was wrong")
