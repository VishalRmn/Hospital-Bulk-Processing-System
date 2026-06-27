"""Unit tests for batch repository."""

import pytest
import os
from datetime import datetime
from app.models.batch import Batch
from app.models.batch_item import BatchItem
from app.repositories.in_memory_repository import InMemoryBatchRepository


class TestInMemoryBatchRepository:
    """Test cases for InMemoryBatchRepository."""
    
    @pytest.mark.asyncio
    async def test_save_batch(self, repository):
        """Test saving a batch."""
        batch = Batch(
            batch_id="test-123",
            status="PROCESSING",
            total_hospitals=2,
            processed_hospitals=1,
            failed_hospitals=0
        )
        
        await repository.save(batch)
        
        # Verify batch is in memory
        retrieved = await repository.get("test-123")
        assert retrieved is not None
        assert retrieved.batch_id == "test-123"
        assert retrieved.status == "PROCESSING"
    
    @pytest.mark.asyncio
    async def test_save_batch_persists_to_disk(self, repository):
        """Test that saving batch persists to disk."""
        batch = Batch(
            batch_id="test-456",
            status="COMPLETED",
            total_hospitals=1,
            processed_hospitals=1,
            failed_hospitals=0
        )
        
        await repository.save(batch)
        
        # Check that file was created
        file_path = os.path.join(repository.data_dir, "test-456.json")
        assert os.path.exists(file_path)
    
    @pytest.mark.asyncio
    async def test_get_batch_found(self, repository):
        """Test retrieving an existing batch."""
        batch = Batch(
            batch_id="test-789",
            status="COMPLETED",
            total_hospitals=1,
            processed_hospitals=1,
            failed_hospitals=0
        )
        
        await repository.save(batch)
        retrieved = await repository.get("test-789")
        
        assert retrieved is not None
        assert retrieved.batch_id == "test-789"
    
    @pytest.mark.asyncio
    async def test_get_batch_not_found(self, repository):
        """Test retrieving a non-existent batch."""
        retrieved = await repository.get("nonexistent")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_update_batch(self, repository):
        """Test updating a batch."""
        batch = Batch(
            batch_id="test-update",
            status="PROCESSING",
            total_hospitals=2,
            processed_hospitals=1,
            failed_hospitals=0
        )
        
        await repository.save(batch)
        
        # Update the batch
        batch.status = "COMPLETED"
        batch.processed_hospitals = 2
        await repository.update(batch)
        
        # Retrieve and verify
        retrieved = await repository.get("test-update")
        assert retrieved.status == "COMPLETED"
        assert retrieved.processed_hospitals == 2
    
    @pytest.mark.asyncio
    async def test_update_batch_not_found(self, repository):
        """Test updating a non-existent batch fails."""
        batch = Batch(
            batch_id="nonexistent",
            status="PROCESSING",
            total_hospitals=1,
            processed_hospitals=0,
            failed_hospitals=0
        )
        
        from app.utils.exceptions import RepositoryError
        with pytest.raises(RepositoryError):
            await repository.update(batch)
    
    @pytest.mark.asyncio
    async def test_delete_batch(self, repository):
        """Test deleting a batch."""
        batch = Batch(
            batch_id="test-delete",
            status="COMPLETED",
            total_hospitals=1,
            processed_hospitals=1,
            failed_hospitals=0
        )
        
        await repository.save(batch)
        await repository.delete("test-delete")
        
        # Verify batch is deleted
        retrieved = await repository.get("test-delete")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_delete_batch_removes_disk_file(self, repository):
        """Test that deleting batch removes disk file."""
        batch = Batch(
            batch_id="test-delete-disk",
            status="COMPLETED",
            total_hospitals=1,
            processed_hospitals=1,
            failed_hospitals=0
        )
        
        await repository.save(batch)
        file_path = os.path.join(repository.data_dir, "test-delete-disk.json")
        assert os.path.exists(file_path)
        
        await repository.delete("test-delete-disk")
        assert not os.path.exists(file_path)
    
    @pytest.mark.asyncio
    async def test_list_all_batches(self, repository):
        """Test listing all batches."""
        batch1 = Batch(batch_id="test-1", status="COMPLETED", total_hospitals=1)
        batch2 = Batch(batch_id="test-2", status="COMPLETED", total_hospitals=1)
        
        await repository.save(batch1)
        await repository.save(batch2)
        
        all_batches = await repository.list_all()
        assert len(all_batches) == 2
    
    @pytest.mark.asyncio
    async def test_load_from_disk_on_init(self, temp_data_dir):
        """Test that repository loads batches from disk on initialization."""
        # Create first repository and save a batch
        repo1 = InMemoryBatchRepository(data_dir=temp_data_dir)
        batch = Batch(batch_id="test-persist", status="COMPLETED", total_hospitals=1)
        await repo1.save(batch)
        
        # Create new repository and verify batch is loaded
        repo2 = InMemoryBatchRepository(data_dir=temp_data_dir)
        retrieved = await repo2.get("test-persist")
        assert retrieved is not None
        assert retrieved.batch_id == "test-persist"
    
    @pytest.mark.asyncio
    async def test_save_batch_with_items(self, repository):
        """Test saving and retrieving batch with items."""
        item = BatchItem(
            row_number=1,
            hospital_name="Test Hospital",
            hospital_id=123,
            status="created_and_activated"
        )
        
        batch = Batch(
            batch_id="test-items",
            status="COMPLETED",
            total_hospitals=1,
            processed_hospitals=1,
            failed_hospitals=0,
            items=[item]
        )
        
        await repository.save(batch)
        retrieved = await repository.get("test-items")
        
        assert len(retrieved.items) == 1
        assert retrieved.items[0].hospital_name == "Test Hospital"
        assert retrieved.items[0].hospital_id == 123
