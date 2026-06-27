"""Integration tests for bulk processing endpoints."""

import pytest
import json
from io import BytesIO


class TestBulkEndpoint:
    """Integration tests for bulk processing endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'Hospital Bulk Processing System' in data['service']
    
    def test_bulk_upload_no_file(self, client):
        """Test bulk upload without file."""
        response = client.post('/hospitals/bulk')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'validation_error'
        assert 'file' in data['message'].lower()
    
    def test_bulk_upload_empty_filename(self, client):
        """Test bulk upload with empty filename."""
        response = client.post(
            '/hospitals/bulk',
            data={'file': (BytesIO(b''), '')}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'validation_error'
    
    def test_bulk_upload_invalid_csv_headers(self, client):
        """Test bulk upload with invalid CSV headers."""
        csv_content = b"hospital,location\nTest Hospital,Test Location\n"
        
        response = client.post(
            '/hospitals/bulk',
            data={'file': (BytesIO(csv_content), 'hospitals.csv')}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'validation_error'
        assert 'header' in data['message'].lower()
    
    def test_bulk_upload_missing_required_field(self, client):
        """Test bulk upload with missing required field."""
        csv_content = b"name,phone\nHospital 1,555-0001\n"
        
        response = client.post(
            '/hospitals/bulk',
            data={'file': (BytesIO(csv_content), 'hospitals.csv')}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'validation_error'
    
    def test_bulk_upload_too_many_hospitals(self, client):
        """Test bulk upload with too many hospitals."""
        # Create CSV with 21 hospitals (exceeds max of 20)
        csv_lines = ["name,address,phone"]
        for i in range(21):
            csv_lines.append(f"Hospital {i},Address {i},555-{i:04d}")
        
        csv_content = "\n".join(csv_lines).encode()
        
        response = client.post(
            '/hospitals/bulk',
            data={'file': (BytesIO(csv_content), 'hospitals.csv')}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'validation_error'
        assert 'maximum' in data['message'].lower()
    
    def test_bulk_upload_valid_csv_structure(self, client):
        """Test bulk upload response structure with valid CSV."""
        csv_content = b"""name,address,phone
Hospital 1,Address 1,555-0001
Hospital 2,Address 2,555-0002
"""
        
        response = client.post(
            '/hospitals/bulk',
            data={'file': (BytesIO(csv_content), 'hospitals.csv')}
        )
        
        # Response should be 200 even if API calls fail
        assert response.status_code in [200, 500]
        data = json.loads(response.data)
        
        # Verify response structure
        assert 'batch_id' in data
        assert 'status' in data
        assert 'total_hospitals' in data
        assert 'processed_hospitals' in data
        assert 'failed_hospitals' in data
        assert 'batch_activated' in data
        assert 'hospitals' in data
    
    def test_get_batch_status_not_found(self, client):
        """Test getting status of non-existent batch."""
        response = client.get('/batches/nonexistent-batch-id')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'not found' in data['message'].lower()
    
    def test_resume_batch_invalid_batch_id(self, client):
        """Test resuming non-existent batch."""
        response = client.post('/batches/nonexistent-batch-id/resume')
        
        assert response.status_code == 404
    
    def test_404_endpoint(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent-endpoint')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'not found' in data['message'].lower()


class TestBulkUploadValidation:
    """Test CSV validation during bulk upload."""
    
    def test_csv_with_no_phone_column(self, client):
        """Test CSV upload without phone column (optional)."""
        csv_content = b"""name,address
Hospital 1,Address 1
Hospital 2,Address 2
"""
        
        response = client.post(
            '/hospitals/bulk',
            data={'file': (BytesIO(csv_content), 'hospitals.csv')}
        )
        
        # Should succeed - phone is optional
        assert response.status_code in [200, 500]
        data = json.loads(response.data)
        assert 'batch_id' in data
    
    def test_csv_with_empty_required_field(self, client):
        """Test CSV with empty required field."""
        csv_content = b"""name,address,phone
Hospital 1,,555-0001
"""
        
        response = client.post(
            '/hospitals/bulk',
            data={'file': (BytesIO(csv_content), 'hospitals.csv')}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'validation_error' in data['status'].lower()
    
    def test_csv_single_hospital(self, client):
        """Test CSV with single hospital."""
        csv_content = b"""name,address,phone
Test Hospital,Test Address,555-0000
"""
        
        response = client.post(
            '/hospitals/bulk',
            data={'file': (BytesIO(csv_content), 'hospitals.csv')}
        )
        
        assert response.status_code in [200, 500]
        data = json.loads(response.data)
        assert data['total_hospitals'] == 1
    
    def test_csv_max_hospitals(self, client):
        """Test CSV with maximum allowed hospitals (20)."""
        csv_lines = ["name,address,phone"]
        for i in range(20):
            csv_lines.append(f"Hospital {i},Address {i},555-{i:04d}")
        
        csv_content = "\n".join(csv_lines).encode()
        
        response = client.post(
            '/hospitals/bulk',
            data={'file': (BytesIO(csv_content), 'hospitals.csv')}
        )
        
        assert response.status_code in [200, 500]
        data = json.loads(response.data)
        assert data['total_hospitals'] == 20
