"""CSV processing service for hospital data extraction and validation."""

import io
import csv
from typing import List, Dict, Tuple
from werkzeug.datastructures import FileStorage
from app.utils.validators import (
    validate_csv_file,
    parse_csv_content,
    validate_csv_headers,
    validate_hospital_data
)
from app.utils.exceptions import ValidationError
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CSVService:
    """Service for processing and validating CSV files containing hospital data."""
    
    @staticmethod
    def validate_file(file: FileStorage) -> bool:
        """
        Validate uploaded file.
        
        Args:
            file: Flask FileStorage object
            
        Returns:
            True if file is valid
            
        Raises:
            ValidationError: If file validation fails
        """
        if file is None:
            raise ValidationError("No file provided")
        
        if not file.filename:
            raise ValidationError("File has no filename")
        
        if not file.filename.endswith('.csv'):
            raise ValidationError("File must be a CSV file (.csv)")
        
        # Check file size (reasonable limit)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size == 0:
            raise ValidationError("File is empty")
        
        if file_size > 5 * 1024 * 1024:  # 5MB limit
            raise ValidationError("File is too large (maximum 5MB)")
        
        logger.info(f"File validation passed: {file.filename} ({file_size} bytes)")
        return True
    
    @staticmethod
    def parse_csv(file: FileStorage) -> List[Dict[str, str]]:
        """
        Parse CSV file and extract hospital records.
        
        Args:
            file: Flask FileStorage object
            
        Returns:
            List of hospital dictionaries
            
        Raises:
            ValidationError: If parsing or validation fails
        """
        try:
            # Read file content
            file.seek(0)
            content = file.read()
            
            # Validate file
            CSVService.validate_file(file)
            
            # Parse CSV content
            hospitals = parse_csv_content(content)
            
            logger.info(f"CSV parsed successfully: {len(hospitals)} hospitals found")
            return hospitals
        
        except ValidationError as e:
            logger.error(f"CSV validation error: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            raise ValidationError(f"Error parsing CSV: {str(e)}")
    
    @staticmethod
    def parse_from_bytes(content: bytes) -> List[Dict[str, str]]:
        """
        Parse CSV from raw bytes.
        
        Args:
            content: Raw CSV file bytes
            
        Returns:
            List of hospital dictionaries
            
        Raises:
            ValidationError: If parsing or validation fails
        """
        try:
            hospitals = parse_csv_content(content)
            logger.info(f"CSV parsed from bytes: {len(hospitals)} hospitals")
            return hospitals
        except ValidationError as e:
            logger.error(f"CSV validation error: {e.message}")
            raise
        except Exception as e:
            logger.error(f"Error parsing CSV from bytes: {str(e)}")
            raise ValidationError(f"Error parsing CSV: {str(e)}")
