"""Pytest configuration and shared fixtures."""

import pytest
import os
import tempfile
import shutil
from io import BytesIO
from app import create_app
from app.config import TestingConfig
from app.repositories.in_memory_repository import InMemoryBatchRepository


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app(TestingConfig)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def temp_data_dir():
    """Create temporary directory for test data."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def repository(temp_data_dir):
    """In-memory repository for testing."""
    return InMemoryBatchRepository(data_dir=temp_data_dir)


@pytest.fixture
def sample_csv_valid():
    """Sample valid CSV file."""
    content = b"""name,address,phone
General Hospital,123 Main St,555-0001
City Medical Center,456 Oak Ave,555-0002
Regional Health,789 Pine Rd,555-0003
"""
    return BytesIO(content)


@pytest.fixture
def sample_csv_no_phone():
    """Sample CSV without phone numbers."""
    content = b"""name,address
Hospital A,Address A
Hospital B,Address B
"""
    return BytesIO(content)


@pytest.fixture
def sample_csv_missing_required_field():
    """Sample CSV with missing required field."""
    content = b"""name,phone
Hospital 1,555-0001
Hospital 2,555-0002
"""
    return BytesIO(content)


@pytest.fixture
def sample_csv_empty():
    """Empty CSV file."""
    content = b""
    return BytesIO(content)


@pytest.fixture
def sample_csv_too_large():
    """CSV with too many hospitals."""
    header = b"name,address,phone\n"
    rows = b""
    for i in range(25):
        rows += f"Hospital {i},Address {i},555-{i:04d}\n".encode()
    
    return BytesIO(header + rows)


@pytest.fixture
def sample_hospital_data():
    """Sample hospital data for processing."""
    return [
        {
            'row_number': 1,
            'name': 'General Hospital',
            'address': '123 Main St',
            'phone': '555-0001'
        },
        {
            'row_number': 2,
            'name': 'City Medical Center',
            'address': '456 Oak Ave',
            'phone': '555-0002'
        }
    ]
