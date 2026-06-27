"""Response models for API endpoints."""

from pydantic import BaseModel, Field
from typing import List, Optional, Any


class HospitalResponse(BaseModel):
    """Response model for individual hospital in batch result."""
    
    row: int = Field(..., description="CSV row number")
    hospital_id: Optional[int] = Field(None, description="Hospital ID from API")
    name: str = Field(..., description="Hospital name")
    status: str = Field(..., description="Status: created_and_activated, creation_failed, etc.")
    attempts: int = Field(default=0, description="Number of creation attempts")
    failure_reason: Optional[str] = Field(None, description="Failure reason if applicable")


class BulkUploadResponse(BaseModel):
    """Response model for bulk upload endpoint."""
    
    batch_id: str = Field(..., description="Unique batch ID")
    status: str = Field(..., description="Overall batch status")
    total_hospitals: int = Field(..., description="Total hospitals in batch")
    processed_hospitals: int = Field(..., description="Successfully processed")
    failed_hospitals: int = Field(..., description="Failed hospitals")
    processing_time_seconds: float = Field(..., description="Time taken to process")
    batch_activated: bool = Field(..., description="Whether batch was activated")
    activation_status: str = Field(..., description="Activation status")
    hospitals: List[HospitalResponse] = Field(default_factory=list, description="Individual hospital results")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class BatchStatusResponse(BaseModel):
    """Response model for batch status endpoint."""
    
    batch_id: str = Field(..., description="Batch ID")
    status: str = Field(..., description="Current batch status")
    total_hospitals: int = Field(..., description="Total hospitals")
    processed_hospitals: int = Field(..., description="Processed count")
    failed_hospitals: int = Field(..., description="Failed count")
    batch_activated: bool = Field(..., description="Activation status")
    activation_status: str = Field(..., description="Activation status detail")
    started_at: str = Field(..., description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    processing_time_seconds: Optional[float] = Field(None, description="Processing duration")
    hospitals: List[HospitalResponse] = Field(default_factory=list, description="Hospital details")


class ErrorResponse(BaseModel):
    """Response model for error responses."""
    
    status: str = Field(default="error", description="Status indicator")
    message: str = Field(..., description="Error message")
    details: Optional[Any] = Field(None, description="Additional error details")
    batch_id: Optional[str] = Field(None, description="Batch ID if applicable")


class ValidationErrorResponse(BaseModel):
    """Response model for validation errors."""
    
    status: str = Field(default="validation_error", description="Status indicator")
    message: str = Field(..., description="Error message")
    details: List[str] = Field(default_factory=list, description="List of validation errors")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
