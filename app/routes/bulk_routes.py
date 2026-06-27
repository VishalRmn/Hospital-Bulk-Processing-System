"""Routes for bulk hospital processing endpoints."""

import asyncio
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from app.services.batch_processor import BatchProcessor
from app.services.csv_service import CSVService
from app.repositories.in_memory_repository import InMemoryBatchRepository
from app.models.response_models import BulkUploadResponse, BatchStatusResponse, ErrorResponse
from app.utils.exceptions import ValidationError, APIError
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Create blueprint
bulk_routes = Blueprint('bulk', __name__, url_prefix='')

# Initialize services
repository = InMemoryBatchRepository()
batch_processor = BatchProcessor(repository)
csv_service = CSVService()


def _get_event_loop():
    """Get or create event loop for async operations."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


@bulk_routes.route('/hospitals/bulk', methods=['POST'])
def bulk_upload():
    """
    Bulk upload hospitals from CSV file.
    
    Request:
        - file: CSV file with columns: name, address, phone (phone optional)
        - Max 20 hospitals
    
    Response:
        - batch_id: Unique batch identifier
        - status: Processing status
        - processed_hospitals: Count of successfully created hospitals
        - failed_hospitals: Count of failed hospitals
        - batch_activated: Whether batch was activated
        - hospitals: Array of individual results with status
    """
    try:
        # Validate file upload
        if 'file' not in request.files:
            logger.warning("No file in request")
            return jsonify({
                'status': 'validation_error',
                'message': 'No file provided',
                'details': ['file field is required']
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            logger.warning("Empty filename")
            return jsonify({
                'status': 'validation_error',
                'message': 'No file selected',
                'details': ['Please select a file']
            }), 400
        
        logger.info(f"Processing upload: filename={file.filename}")
        
        # Parse and validate CSV
        try:
            hospitals = csv_service.parse_csv(file)
            logger.info(f"CSV parsed: {len(hospitals)} hospitals")
        except ValidationError as e:
            logger.warning(f"CSV validation error: {e.message}")
            return jsonify({
                'status': 'validation_error',
                'message': e.message,
                'details': e.details if e.details else []
            }), 400
        
        # Process batch (async operation)
        try:
            loop = _get_event_loop()
            batch = loop.run_until_complete(batch_processor.process_batch(hospitals))
            logger.info(f"Batch processed: batch_id={batch.batch_id}")
            
            # Build response
            hospital_responses = []
            for item in batch.items:
                hospital_responses.append({
                    'row': item.row_number,
                    'hospital_id': item.hospital_id,
                    'name': item.hospital_name,
                    'status': item.status,
                    'attempts': item.attempts,
                    'failure_reason': item.failure_reason
                })
            
            response_data = {
                'batch_id': batch.batch_id,
                'status': batch.status,
                'total_hospitals': batch.total_hospitals,
                'processed_hospitals': batch.processed_hospitals,
                'failed_hospitals': batch.failed_hospitals,
                'processing_time_seconds': batch.processing_time_seconds,
                'batch_activated': batch.batch_activated,
                'activation_status': batch.activation_status,
                'hospitals': hospital_responses
            }
            
            if batch.error_message:
                response_data['error_message'] = batch.error_message
            
            return jsonify(response_data), 200
        
        except Exception as e:
            logger.error(f"Batch processing error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Batch processing failed',
                'details': [str(e)]
            }), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in bulk_upload: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'details': [str(e)]
        }), 500


@bulk_routes.route('/batches/<batch_id>', methods=['GET'])
def get_batch_status(batch_id):
    """
    Get the status of a batch.
    
    Parameters:
        batch_id: Batch ID (UUID)
    
    Response:
        - batch_id: Batch identifier
        - status: Current status
        - total_hospitals: Total count
        - processed_hospitals: Successfully created count
        - failed_hospitals: Failed count
        - batch_activated: Activation status
        - hospitals: Individual hospital results
    """
    try:
        logger.debug(f"Getting batch status: batch_id={batch_id}")
        
        loop = _get_event_loop()
        batch = loop.run_until_complete(repository.get(batch_id))
        
        if not batch:
            logger.warning(f"Batch not found: batch_id={batch_id}")
            return jsonify({
                'status': 'error',
                'message': f'Batch not found: {batch_id}'
            }), 404
        
        # Build response
        hospital_responses = []
        for item in batch.items:
            hospital_responses.append({
                'row': item.row_number,
                'hospital_id': item.hospital_id,
                'name': item.hospital_name,
                'status': item.status,
                'attempts': item.attempts,
                'failure_reason': item.failure_reason
            })
        
        response_data = {
            'batch_id': batch.batch_id,
            'status': batch.status,
            'total_hospitals': batch.total_hospitals,
            'processed_hospitals': batch.processed_hospitals,
            'failed_hospitals': batch.failed_hospitals,
            'batch_activated': batch.batch_activated,
            'activation_status': batch.activation_status,
            'started_at': batch.started_at.isoformat() if batch.started_at else None,
            'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
            'processing_time_seconds': batch.processing_time_seconds,
            'hospitals': hospital_responses
        }
        
        if batch.error_message:
            response_data['error_message'] = batch.error_message
        
        return jsonify(response_data), 200
    
    except Exception as e:
        logger.error(f"Error getting batch status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error retrieving batch status',
            'details': [str(e)]
        }), 500


@bulk_routes.route('/batches/<batch_id>/resume', methods=['POST'])
def resume_batch(batch_id):
    """
    Resume processing of a failed or partially failed batch.
    
    Parameters:
        batch_id: Batch ID (UUID)
    
    Response:
        - Same as bulk upload response with updated status
    """
    try:
        logger.info(f"Resuming batch: batch_id={batch_id}")
        
        loop = _get_event_loop()
        batch = loop.run_until_complete(batch_processor.resume_batch(batch_id))
        
        # Build response
        hospital_responses = []
        for item in batch.items:
            hospital_responses.append({
                'row': item.row_number,
                'hospital_id': item.hospital_id,
                'name': item.hospital_name,
                'status': item.status,
                'attempts': item.attempts,
                'failure_reason': item.failure_reason
            })
        
        response_data = {
            'batch_id': batch.batch_id,
            'status': batch.status,
            'total_hospitals': batch.total_hospitals,
            'processed_hospitals': batch.processed_hospitals,
            'failed_hospitals': batch.failed_hospitals,
            'processing_time_seconds': batch.processing_time_seconds,
            'batch_activated': batch.batch_activated,
            'activation_status': batch.activation_status,
            'hospitals': hospital_responses
        }
        
        if batch.error_message:
            response_data['error_message'] = batch.error_message
        
        return jsonify(response_data), 200
    
    except ValidationError as e:
        logger.warning(f"Validation error resuming batch: {e.message}")
        # Return 404 if batch not found, 400 for other validation errors
        status_code = 404 if 'not found' in e.message.lower() else 400
        return jsonify({
            'status': 'validation_error' if status_code == 400 else 'error',
            'message': e.message,
            'batch_id': batch_id
        }), status_code
    
    except Exception as e:
        logger.error(f"Error resuming batch: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error resuming batch',
            'batch_id': batch_id,
            'details': [str(e)]
        }), 500
