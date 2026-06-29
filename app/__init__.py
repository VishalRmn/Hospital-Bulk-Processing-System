"""Flask application factory."""

from flask import Flask, jsonify
from app.config import get_config
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_app(config_class=None):
    """Create and configure Flask application."""
    
    if config_class is None:
        config_class = get_config()
    
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    logger.info(f"Creating Flask app with config: {config_class.__name__}")

    # Register root endpoint
    @app.route("/", methods=["GET"])
    def index():
        """API root endpoint."""
        return jsonify({
            "service": "Hospital Bulk Processing API",
            "version": "1.0.0",
            "status": "running",
            "documentation": "See README.md in the GitHub repository.",
            "endpoints": {
                "health": "/health",
                "bulk_upload": "/hospitals/bulk",
                "batch_status": "/batches/<batch_id>",
                "resume_batch": "/batches/<batch_id>/resume"
            }
        }), 200
    
    # Register health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'Hospital Bulk Processing System'
        }), 200
    
    # Register bulk routes blueprint
    from app.routes.bulk_routes import bulk_routes
    app.register_blueprint(bulk_routes)
    logger.info("Bulk routes blueprint registered")
    
    # Error handler for 404
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({
            'status': 'error',
            'message': 'Endpoint not found'
        }), 404
    
    # Error handler for 500
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'status': 'error',
            'message': 'Internal server error'
        }), 500
    
    logger.info("Flask app created successfully")
    
    return app
