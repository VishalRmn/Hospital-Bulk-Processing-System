"""Batch processor for orchestrating hospital bulk processing workflow."""

import asyncio
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models.batch import Batch
from app.models.batch_item import BatchItem
from app.services.csv_service import CSVService
from app.services.hospital_client import HospitalAPIClient
from app.repositories.in_memory_repository import InMemoryBatchRepository
from app.utils.constants import (
    BATCH_UPLOADED,
    BATCH_VALIDATING,
    BATCH_PROCESSING,
    BATCH_COMPLETED,
    BATCH_PARTIAL_FAILURE,
    BATCH_FAILED,
    ITEM_CREATED_AND_ACTIVATED,
    ITEM_CREATION_FAILED,
    ACTIVATION_SUCCESS,
    ACTIVATION_FAILED,
    ACTIVATION_SKIPPED,
    ACTIVATION_PENDING
)
from app.utils.exceptions import ValidationError, APIError, NonRetryableError, RetryableError
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class BatchProcessor:
    """Orchestrates the hospital bulk processing workflow."""
    
    def __init__(self, repository: Optional[InMemoryBatchRepository] = None):
        """
        Initialize batch processor.
        
        Args:
            repository: Batch repository for persistence
        """
        self.repository = repository or InMemoryBatchRepository()
    
    async def process_batch(
        self,
        hospitals: List[Dict[str, Any]],
        batch_id: Optional[str] = None
    ) -> Batch:
        """
        Process a batch of hospitals.
        
        Workflow:
        1. Validate input
        2. Create batch object
        3. Create all hospitals concurrently
        4. If all succeed, activate batch
        5. Return results
        
        Args:
            hospitals: List of hospital dictionaries with name, address, phone
            batch_id: Optional batch ID (generated if not provided)
            
        Returns:
            Completed Batch object with results
            
        Raises:
            ValidationError: If input validation fails
        """
        start_time = time.time()
        batch_id = batch_id or str(uuid.uuid4())
        
        # Create batch object
        batch = Batch(
            batch_id=batch_id,
            status=BATCH_VALIDATING,
            total_hospitals=len(hospitals),
            started_at=datetime.utcnow()
        )
        
        logger.info(f"Starting batch processing: batch_id={batch_id}, hospitals={len(hospitals)}")
        
        try:
            # Save initial batch state
            await self.repository.save(batch)
            
            # Update status to PROCESSING
            batch.status = BATCH_PROCESSING
            await self.repository.save(batch)
            
            # Create hospitals concurrently
            batch_items = await self._create_hospitals_concurrently(batch, hospitals)
            batch.items = batch_items
            
            # Count results
            created_count = sum(1 for item in batch_items if item.hospital_id is not None)
            failed_count = sum(1 for item in batch_items if item.hospital_id is None)
            
            batch.processed_hospitals = created_count
            batch.failed_hospitals = failed_count
            
            logger.info(
                f"Hospital creation complete: batch_id={batch_id}, "
                f"created={created_count}, failed={failed_count}"
            )
            
            # Determine if batch can be activated
            if failed_count == 0:
                # All succeeded - activate batch
                logger.info(f"All hospitals created successfully. Activating batch: {batch_id}")
                await self._activate_batch(batch)
            else:
                # Some or all failed - mark as partial failure and skip activation
                logger.warning(
                    f"Batch has failures. Skipping activation: batch_id={batch_id}, "
                    f"failed={failed_count}"
                )
                batch.status = BATCH_PARTIAL_FAILURE
                batch.activation_status = ACTIVATION_SKIPPED
                batch.batch_activated = False
            
        except Exception as e:
            logger.error(f"Batch processing failed: batch_id={batch_id}, error={str(e)}")
            batch.status = BATCH_FAILED
            batch.error_message = str(e)
        
        finally:
            # Finalize batch
            batch.completed_at = datetime.utcnow()
            batch.processing_time_seconds = time.time() - start_time
            
            # Save final state
            await self.repository.save(batch)
            
            logger.info(
                f"Batch processing finished: batch_id={batch_id}, "
                f"status={batch.status}, time={batch.processing_time_seconds:.1f}s"
            )
        
        return batch
    
    async def _create_hospitals_concurrently(
        self,
        batch: Batch,
        hospitals: List[Dict[str, Any]]
    ) -> List[BatchItem]:
        """
        Create all hospitals concurrently.
        
        Args:
            batch: Batch object
            hospitals: List of hospital data
            
        Returns:
            List of BatchItem objects with results
        """
        async with HospitalAPIClient() as client:
            # Create tasks for all hospitals
            tasks = [
                self._create_single_hospital(client, batch.batch_id, hospital)
                for hospital in hospitals
            ]
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=False)
            
            return results
    
    async def _create_single_hospital(
        self,
        client: HospitalAPIClient,
        batch_id: str,
        hospital_data: Dict[str, Any]
    ) -> BatchItem:
        """
        Create a single hospital and track result.
        
        Args:
            client: Hospital API client
            batch_id: Batch ID
            hospital_data: Hospital data with row_number, name, address, phone
            
        Returns:
            BatchItem with result
        """
        row_number = hospital_data.get('row_number', 0)
        name = hospital_data.get('name', '')
        address = hospital_data.get('address', '')
        phone = hospital_data.get('phone')
        
        item = BatchItem(
            row_number=row_number,
            hospital_name=name,
            status=ITEM_CREATION_FAILED
        )
        
        try:
            
            logger.debug(f"Creating hospital: row={row_number}, name={name}")
            logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} START {name}")
            
            response = await client.create_hospital(
                name=name,
                address=address,
                phone=phone,
                batch_id=batch_id
            )

            logger.info(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} END {name}")
            item.hospital_id = response.get('id')
            item.status = ITEM_CREATED_AND_ACTIVATED  # Will be updated after activation
            item.attempts = 1
            
            logger.info(f"Hospital created: row={row_number}, id={item.hospital_id}")
        
        except NonRetryableError as e:
            logger.error(f"Non-retryable error creating hospital: row={row_number}, error={e.message}")
            item.failure_reason = e.message
            item.attempts = 1
        
        except RetryableError as e:
            logger.error(f"Retryable error exhausted for hospital: row={row_number}, error={e.message}")
            item.failure_reason = f"Network error after retries: {e.message}"
            item.attempts = 3  # Indicates max retries were attempted
        
        except Exception as e:
            logger.error(f"Unexpected error creating hospital: row={row_number}, error={str(e)}")
            item.failure_reason = f"Unexpected error: {str(e)}"
            item.attempts = 1
        
        return item
    
    async def _activate_batch(self, batch: Batch) -> None:
        """
        Activate all hospitals in batch.
        
        Args:
            batch: Batch object to activate
        """
        try:
            async with HospitalAPIClient() as client:
                logger.info(f"Activating batch: {batch.batch_id}")
                
                await client.activate_batch(batch.batch_id)
                
                batch.batch_activated = True
                batch.activation_status = ACTIVATION_SUCCESS
                batch.status = BATCH_COMPLETED
                
                # Update all items to activated status
                for item in batch.items:
                    if item.hospital_id is not None:
                        item.status = ITEM_CREATED_AND_ACTIVATED
                
                logger.info(f"Batch activated successfully: {batch.batch_id}")
        
        except NonRetryableError as e:
            logger.error(f"Activation failed (non-retryable): batch_id={batch.batch_id}, error={e.message}")
            batch.batch_activated = False
            batch.activation_status = ACTIVATION_FAILED
            batch.status = BATCH_PARTIAL_FAILURE
            batch.error_message = f"Activation failed: {e.message}"
        
        except RetryableError as e:
            logger.error(f"Activation failed (retries exhausted): batch_id={batch.batch_id}, error={e.message}")
            batch.batch_activated = False
            batch.activation_status = ACTIVATION_FAILED
            batch.status = BATCH_PARTIAL_FAILURE
            batch.error_message = f"Activation failed after retries: {e.message}"
        
        except Exception as e:
            logger.error(f"Unexpected error during activation: batch_id={batch.batch_id}, error={str(e)}")
            batch.batch_activated = False
            batch.activation_status = ACTIVATION_FAILED
            batch.status = BATCH_PARTIAL_FAILURE
            batch.error_message = f"Activation failed: {str(e)}"
    
    async def resume_batch(self, batch_id: str) -> Batch:
        """
        Resume processing of a failed or partially failed batch.
        
        Args:
            batch_id: Batch ID to resume
            
        Returns:
            Updated Batch object
            
        Raises:
            ValidationError: If batch not found or not in resumable state
        """
        logger.info(f"Resuming batch: {batch_id}")
        
        # Retrieve batch
        batch = await self.repository.get(batch_id)
        if not batch:
            raise ValidationError(f"Batch not found: {batch_id}")
        
        # Check if batch can be resumed
        if batch.status not in [BATCH_PARTIAL_FAILURE, BATCH_FAILED]:
            raise ValidationError(
                f"Batch cannot be resumed. Current status: {batch.status}. "
                f"Only PARTIAL_FAILURE or FAILED batches can be resumed."
            )
        
        # Find failed items
        failed_items = [item for item in batch.items if item.hospital_id is None]
        
        if not failed_items:
            logger.info(f"No failed items to retry in batch: {batch_id}")
            batch.status = BATCH_COMPLETED
            batch.batch_activated = True
            await self.repository.update(batch)
            return batch
        
        logger.info(f"Retrying {len(failed_items)} failed hospitals in batch: {batch_id}")
        
        start_time = time.time()
        batch.status = BATCH_PROCESSING
        
        try:
            # Prepare hospital data for failed items
            failed_hospitals = [
                {
                    'row_number': item.row_number,
                    'name': item.hospital_name,
                    'address': '',  # Note: we lost address on original creation failure
                    'phone': None
                }
                for item in failed_items
            ]
            
            # Retry creation
            async with HospitalAPIClient() as client:
                tasks = [
                    self._create_single_hospital(client, batch.batch_id, hospital)
                    for hospital in failed_hospitals
                ]
                
                new_results = await asyncio.gather(*tasks, return_exceptions=False)
            
            # Update failed items with new results
            for old_item, new_result in zip(failed_items, new_results):
                old_item.hospital_id = new_result.hospital_id
                old_item.status = new_result.status
                old_item.failure_reason = new_result.failure_reason
                old_item.attempts += new_result.attempts
            
            # Recount
            created_count = sum(1 for item in batch.items if item.hospital_id is not None)
            failed_count = sum(1 for item in batch.items if item.hospital_id is None)
            
            batch.processed_hospitals = created_count
            batch.failed_hospitals = failed_count
            
            # If all now succeed, activate
            if failed_count == 0:
                await self._activate_batch(batch)
            else:
                batch.status = BATCH_PARTIAL_FAILURE
                batch.activation_status = ACTIVATION_SKIPPED
        
        except Exception as e:
            logger.error(f"Error during batch resume: batch_id={batch_id}, error={str(e)}")
            batch.status = BATCH_FAILED
            batch.error_message = str(e)
        
        finally:
            batch.completed_at = datetime.utcnow()
            batch.processing_time_seconds = time.time() - start_time
            await self.repository.update(batch)
        
        return batch
