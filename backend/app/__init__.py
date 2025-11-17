from flask import Flask
from flask_cors import CORS


def create_app():
    """Factory function to create and configure the Flask app."""
    app = Flask(__name__)

    # Allow frontend (Next.js) to call Flask API
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register core routes
    from .routes.routes_main import main
    app.register_blueprint(main, url_prefix="/api")

    # Register AI-related routes
    from .routes.routes_ai import ai
    app.register_blueprint(ai, url_prefix="/api")

    # Placeholder: database and models will be initialized here later
    # e.g. from .models import db
    # db.init_app(app)

    return app