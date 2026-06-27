"""In-memory batch repository with disk persistence."""

import os
import json
import threading
from datetime import datetime
from typing import Optional, Dict
from app.repositories.batch_repository import BatchRepository
from app.models.batch import Batch
from app.models.batch_item import BatchItem
from app.utils.exceptions import RepositoryError
from app.utils.logger import setup_logger
from app.config import get_config

logger = setup_logger(__name__)


class InMemoryBatchRepository(BatchRepository):
    """In-memory batch repository with JSON file persistence."""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize in-memory repository.
        
        Args:
            data_dir: Directory for persisting batch data to disk
        """
        self.data_dir = data_dir or get_config().DATA_DIR
        self.batches: Dict[str, Batch] = {}
        self._lock = threading.RLock()
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load persisted batches from disk
        self._load_from_disk()
        
        logger.info(f"InMemoryBatchRepository initialized with data_dir={self.data_dir}")
    
    def _load_from_disk(self) -> None:
        """Load all persisted batches from disk into memory."""
        try:
            if not os.path.exists(self.data_dir):
                return
            
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.data_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            batch = self._dict_to_batch(data)
                            self.batches[batch.batch_id] = batch
                            logger.debug(f"Loaded batch from disk: {batch.batch_id}")
                    except Exception as e:
                        logger.error(f"Error loading batch from {filepath}: {str(e)}")
            
            logger.info(f"Loaded {len(self.batches)} batches from disk")
        
        except Exception as e:
            logger.error(f"Error loading batches from disk: {str(e)}")
    
    def _save_to_disk(self, batch: Batch) -> None:
        """
        Persist a batch to disk.
        
        Args:
            batch: Batch to persist
        """
        try:
            filepath = os.path.join(self.data_dir, f"{batch.batch_id}.json")
            with open(filepath, 'w') as f:
                json.dump(batch.to_dict(), f, indent=2)
            logger.debug(f"Batch persisted to disk: {batch.batch_id}")
        except Exception as e:
            logger.error(f"Error saving batch to disk: {str(e)}")
            raise RepositoryError(f"Failed to persist batch: {str(e)}")
    
    def _delete_from_disk(self, batch_id: str) -> None:
        """
        Delete a batch file from disk.
        
        Args:
            batch_id: Batch ID to delete
        """
        try:
            filepath = os.path.join(self.data_dir, f"{batch_id}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug(f"Batch deleted from disk: {batch_id}")
        except Exception as e:
            logger.error(f"Error deleting batch from disk: {str(e)}")
    
    @staticmethod
    def _dict_to_batch(data: Dict) -> Batch:
        """
        Convert dictionary to Batch object.
        
        Args:
            data: Dictionary with batch data
            
        Returns:
            Batch object
        """
        # Convert items
        items = []
        for item_data in data.get('items', []):
            item = BatchItem(
                row_number=item_data['row'],
                hospital_name=item_data['name'],
                hospital_id=item_data.get('hospital_id'),
                status=item_data['status'],
                attempts=item_data.get('attempts', 0),
                failure_reason=item_data.get('failure_reason'),
                created_at=datetime.fromisoformat(item_data['created_at']) if isinstance(item_data.get('created_at'), str) else item_data.get('created_at', datetime.utcnow())
            )
            items.append(item)
        
        # Create batch
        batch = Batch(
            batch_id=data['batch_id'],
            status=data['status'],
            total_hospitals=data.get('total_hospitals', 0),
            processed_hospitals=data.get('processed_hospitals', 0),
            failed_hospitals=data.get('failed_hospitals', 0),
            processing_time_seconds=data.get('processing_time_seconds'),
            batch_activated=data.get('batch_activated', False),
            activation_status=data.get('activation_status', 'pending'),
            items=items,
            started_at=datetime.fromisoformat(data['started_at']) if isinstance(data.get('started_at'), str) else data.get('started_at', datetime.utcnow()),
            completed_at=datetime.fromisoformat(data['completed_at']) if isinstance(data.get('completed_at'), str) and data.get('completed_at') else None,
            error_message=data.get('error_message')
        )
        
        return batch
    
    async def save(self, batch: Batch) -> None:
        """
        Save a batch to memory and disk.
        
        Args:
            batch: Batch to save
        """
        with self._lock:
            try:
                self.batches[batch.batch_id] = batch
                self._save_to_disk(batch)
                logger.info(f"Batch saved: {batch.batch_id}")
            except Exception as e:
                logger.error(f"Error saving batch: {str(e)}")
                raise RepositoryError(f"Failed to save batch: {str(e)}")
    
    async def get(self, batch_id: str) -> Optional[Batch]:
        """
        Retrieve a batch from memory.
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Batch object or None if not found
        """
        with self._lock:
            batch = self.batches.get(batch_id)
            if batch:
                logger.debug(f"Batch retrieved: {batch_id}")
            else:
                logger.debug(f"Batch not found: {batch_id}")
            return batch
    
    async def update(self, batch: Batch) -> None:
        """
        Update a batch.
        
        Args:
            batch: Batch with updated data
        """
        with self._lock:
            if batch.batch_id not in self.batches:
                logger.error(f"Batch not found for update: {batch.batch_id}")
                raise RepositoryError(f"Batch not found: {batch.batch_id}")
            
            self.batches[batch.batch_id] = batch
            self._save_to_disk(batch)
            logger.info(f"Batch updated: {batch.batch_id}")
    
    async def delete(self, batch_id: str) -> None:
        """
        Delete a batch.
        
        Args:
            batch_id: Batch ID to delete
        """
        with self._lock:
            if batch_id in self.batches:
                del self.batches[batch_id]
                self._delete_from_disk(batch_id)
                logger.info(f"Batch deleted: {batch_id}")
            else:
                logger.warning(f"Batch not found for deletion: {batch_id}")
    
    async def list_all(self) -> list:
        """
        List all batches.
        
        Returns:
            List of all Batch objects
        """
        with self._lock:
            batches = list(self.batches.values())
            logger.debug(f"Listed {len(batches)} batches")
            return batches
