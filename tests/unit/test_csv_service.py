"""Unit tests for CSV service."""

import pytest
from io import BytesIO
from app.services.csv_service import CSVService
from app.utils.exceptions import ValidationError


class TestCSVService:
    """Test cases for CSVService."""
    
    def test_validate_file_success(self):
        """Test successful file validation."""
        from werkzeug.datastructures import FileStorage
        
        content = b"name,address\nHospital 1,Address 1\n"
        file = FileStorage(
            stream=BytesIO(content),
            filename="hospitals.csv",
            content_type="text/csv"
        )
        
        result = CSVService.validate_file(file)
        assert result is True
    
    def test_validate_file_no_file(self):
        """Test validation fails when no file provided."""
        with pytest.raises(ValidationError) as exc_info:
            CSVService.validate_file(None)
        
        assert "No file provided" in str(exc_info.value.message)
    
    def test_validate_file_empty_filename(self):
        """Test validation fails with empty filename."""
        from werkzeug.datastructures import FileStorage
        
        file = FileStorage(
            stream=BytesIO(b"content"),
            filename="",
            content_type="text/csv"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            CSVService.validate_file(file)
        
        assert "filename" in str(exc_info.value.message).lower()
    
    def test_validate_file_not_csv(self):
        """Test validation fails for non-CSV files."""
        from werkzeug.datastructures import FileStorage
        
        file = FileStorage(
            stream=BytesIO(b"content"),
            filename="data.txt",
            content_type="text/plain"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            CSVService.validate_file(file)
        
        assert "CSV" in str(exc_info.value.message)
    
    def test_validate_file_empty_content(self):
        """Test validation fails for empty file."""
        from werkzeug.datastructures import FileStorage
        
        file = FileStorage(
            stream=BytesIO(b""),
            filename="empty.csv",
            content_type="text/csv"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            CSVService.validate_file(file)
        
        assert "empty" in str(exc_info.value.message).lower()
    
    def test_parse_csv_valid(self, sample_csv_valid):
        """Test parsing valid CSV."""
        from werkzeug.datastructures import FileStorage
        
        content = sample_csv_valid.read()
        file = FileStorage(
            stream=BytesIO(content),
            filename="hospitals.csv",
            content_type="text/csv"
        )
        
        hospitals = CSVService.parse_csv(file)
        
        assert len(hospitals) == 3
        assert hospitals[0]['name'] == 'General Hospital'
        assert hospitals[0]['address'] == '123 Main St'
        assert hospitals[0]['phone'] == '555-0001'
    
    def test_parse_csv_no_phone(self, sample_csv_no_phone):
        """Test parsing CSV without phone column."""
        from werkzeug.datastructures import FileStorage
        
        content = sample_csv_no_phone.read()
        file = FileStorage(
            stream=BytesIO(content),
            filename="hospitals.csv",
            content_type="text/csv"
        )
        
        hospitals = CSVService.parse_csv(file)
        
        assert len(hospitals) == 2
        assert hospitals[0]['phone'] is None
    
    def test_parse_csv_missing_required_field(self, sample_csv_missing_required_field):
        """Test parsing CSV with missing required field."""
        from werkzeug.datastructures import FileStorage
        
        content = sample_csv_missing_required_field.read()
        file = FileStorage(
            stream=BytesIO(content),
            filename="hospitals.csv",
            content_type="text/csv"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            CSVService.parse_csv(file)
        
        assert "address" in str(exc_info.value.message).lower()
    
    def test_parse_csv_too_many_rows(self, sample_csv_too_large):
        """Test parsing CSV with too many rows."""
        from werkzeug.datastructures import FileStorage
        
        content = sample_csv_too_large.read()
        file = FileStorage(
            stream=BytesIO(content),
            filename="hospitals.csv",
            content_type="text/csv"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            CSVService.parse_csv(file)
        
        assert "maximum" in str(exc_info.value.message).lower()
    
    def test_parse_from_bytes_valid(self):
        """Test parsing CSV from bytes."""
        content = b"name,address,phone\nHospital 1,Address 1,555-0001\n"
        
        hospitals = CSVService.parse_from_bytes(content)
        
        assert len(hospitals) == 1
        assert hospitals[0]['name'] == 'Hospital 1'
    
    def test_parse_from_bytes_invalid_utf8(self):
        """Test parsing invalid UTF-8 content."""
        content = b"\xff\xfe invalid"
        
        with pytest.raises(ValidationError):
            CSVService.parse_from_bytes(content)
