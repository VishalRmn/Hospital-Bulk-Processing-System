"""Batch model for tracking batch processing state and history."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from app.models.batch_item import BatchItem


class Batch(BaseModel):
    """Represents a batch of hospitals being processed."""
    
    batch_id: str = Field(..., description="Unique batch identifier (UUID)")
    status: str = Field(..., description="Current batch status (UPLOADED, VALIDATING, PROCESSING, COMPLETED, etc.)")
    total_hospitals: int = Field(default=0, description="Total number of hospitals in batch")
    processed_hospitals: int = Field(default=0, description="Number of successfully processed hospitals")
    failed_hospitals: int = Field(default=0, description="Number of failed hospitals")
    processing_time_seconds: Optional[float] = Field(None, description="Time taken to process batch")
    batch_activated: bool = Field(default=False, description="Whether batch was activated")
    activation_status: str = Field(default="pending", description="Status of batch activation (pending, success, failed, skipped)")
    items: List[BatchItem] = Field(default_factory=list, description="List of individual hospital items")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="When batch processing started")
    completed_at: Optional[datetime] = Field(None, description="When batch processing completed")
    error_message: Optional[str] = Field(None, description="Overall error message if batch failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self):
        """Convert batch to dictionary for JSON serialization."""
        return {
            'batch_id': self.batch_id,
            'status': self.status,
            'total_hospitals': self.total_hospitals,
            'processed_hospitals': self.processed_hospitals,
            'failed_hospitals': self.failed_hospitals,
            'processing_time_seconds': self.processing_time_seconds,
            'batch_activated': self.batch_activated,
            'activation_status': self.activation_status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'items': [
                {
                    'row': item.row_number,
                    'hospital_id': item.hospital_id,
                    'name': item.hospital_name,
                    'status': item.status,
                    'attempts': item.attempts,
                    'failure_reason': item.failure_reason,
                    'created_at': item.created_at.isoformat()
                }
                for item in self.items
            ]
        }
