"""Batch item model for tracking individual hospital processing."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class BatchItem(BaseModel):
    """Represents a single hospital entry in a batch."""
    
    row_number: int = Field(..., description="CSV row number (1-indexed)")
    hospital_name: str = Field(..., description="Hospital name from CSV")
    hospital_id: Optional[int] = Field(None, description="ID assigned by Hospital API")
    status: str = Field(..., description="Status of this item (created, creation_failed, etc.)")
    attempts: int = Field(default=0, description="Number of creation attempts")
    failure_reason: Optional[str] = Field(None, description="Reason for failure if creation failed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of creation")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
