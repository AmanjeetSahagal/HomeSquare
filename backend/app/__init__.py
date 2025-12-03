from flask import Flask
from flask_cors import CORS

def create_app():
    """Factory function to create and configure the Flask app."""
    app = Flask(__name__)

    # Allow frontend to call Flask API
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register core routes
    from .routes.routes_main import main
    app.register_blueprint(main, url_prefix="/api")

    # Register AI routes
    from .routes.routes_ai import ai
    app.register_blueprint(ai, url_prefix="/api")

    # Register saved listings routes
    from .routes.routes_saved import saved, init_saved_listings_table
    app.register_blueprint(saved, url_prefix="/api")

    # Ensure DB table exists
    with app.app_context():
        init_saved_listings_table()

    return app