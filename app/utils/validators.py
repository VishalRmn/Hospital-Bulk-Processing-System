"""Validation utilities for CSV and request data."""

import csv
import io
from typing import List, Tuple, Optional
from app.utils.constants import CSV_REQUIRED_HEADERS, CSV_OPTIONAL_HEADERS, MAX_CSV_SIZE
from app.utils.exceptions import ValidationError


def validate_csv_file(file_content: bytes) -> Tuple[str, bytes]:
    """
    Validate CSV file format and content.
    
    Args:
        file_content: Raw file bytes
        
    Returns:
        Tuple of (filename, validated content)
        
    Raises:
        ValidationError: If file validation fails
    """
    if not file_content:
        raise ValidationError("File is empty")
    
    # Try to decode as CSV
    try:
        content_str = file_content.decode('utf-8')
    except UnicodeDecodeError:
        raise ValidationError("File must be UTF-8 encoded")
    
    if not content_str.strip():
        raise ValidationError("File is empty")
    
    return "upload.csv", file_content


def validate_csv_headers(headers: List[str]) -> bool:
    """
    Validate CSV headers.
    
    Args:
        headers: List of column headers
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If headers are invalid
    """
    headers_lower = [h.strip().lower() for h in headers]
    
    # Check required headers
    for required_header in CSV_REQUIRED_HEADERS:
        if required_header not in headers_lower:
            raise ValidationError(f"Missing required header: {required_header}")
    
    # Check for invalid headers
    valid_headers = set(CSV_REQUIRED_HEADERS + CSV_OPTIONAL_HEADERS)
    for header in headers_lower:
        if header not in valid_headers:
            raise ValidationError(f"Invalid header: {header}. Allowed headers: {', '.join(valid_headers)}")
    
    return True


def validate_csv_row(row: dict, row_number: int) -> Tuple[str, str, Optional[str]]:
    """
    Validate a single CSV row and extract hospital data.
    
    Args:
        row: Dictionary with hospital data
        row_number: Row number in CSV (for error reporting)
        
    Returns:
        Tuple of (name, address, phone)
        
    Raises:
        ValidationError: If row validation fails
    """
    errors = []
    
    # Check required fields
    name = row.get('name', '').strip()
    address = row.get('address', '').strip()
    phone = row.get('phone', '').strip() if 'phone' in row else None
    
    if not name:
        errors.append(f"Row {row_number}: name is required")
    if not address:
        errors.append(f"Row {row_number}: address is required")
    
    if errors:
        raise ValidationError(f"Row {row_number} validation failed", errors)
    
    # Validate phone format if provided (optional)
    if phone:
        if not isinstance(phone, str):
            errors.append(f"Row {row_number}: phone must be a string")
        # Could add more phone validation here if needed
    
    if errors:
        raise ValidationError(f"Row {row_number} validation failed", errors)
    
    return name, address, phone


def validate_hospital_data(hospitals: List[dict]) -> List[dict]:
    """
    Validate list of hospital records.
    
    Args:
        hospitals: List of hospital dictionaries
        
    Returns:
        Validated list of hospital dictionaries
        
    Raises:
        ValidationError: If validation fails
    """
    if not hospitals:
        raise ValidationError("CSV contains no hospital records")
    
    if len(hospitals) > MAX_CSV_SIZE:
        raise ValidationError(
            f"CSV contains {len(hospitals)} hospitals but maximum allowed is {MAX_CSV_SIZE}"
        )
    
    validated_hospitals = []
    
    for idx, hospital in enumerate(hospitals, start=1):
        try:
            name, address, phone = validate_csv_row(hospital, idx)
            validated_hospitals.append({
                'row_number': idx,
                'name': name,
                'address': address,
                'phone': phone
            })
        except ValidationError as e:
            raise ValidationError(
                f"CSV validation failed at row {idx}",
                [str(e.message)] + (e.details if e.details else [])
            )
    
    return validated_hospitals


def parse_csv_content(content: bytes) -> List[dict]:
    """
    Parse CSV file content.
    
    Args:
        content: Raw CSV file bytes
        
    Returns:
        List of dictionaries representing CSV rows
        
    Raises:
        ValidationError: If parsing fails
    """
    try:
        content_str = content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content_str))
        
        if reader.fieldnames is None:
            raise ValidationError("CSV file has no headers")
        
        # Validate headers
        headers = [h.strip() for h in reader.fieldnames]
        validate_csv_headers(headers)
        
        # Parse rows
        hospitals = []
        for row in reader:
            # Convert None values to empty strings
            row = {k: (v or '') for k, v in row.items()}
            hospitals.append(row)
        
        # Validate records
        return validate_hospital_data(hospitals)
    
    except csv.Error as e:
        raise ValidationError(f"CSV parsing error: {str(e)}")
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Unexpected error parsing CSV: {str(e)}")
