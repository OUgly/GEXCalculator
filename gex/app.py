"""Application entry point for the Gamma Exposure dashboard."""

from dash import Dash
import os
import logging
from dotenv import load_dotenv

#These definitions are used to create the layout and register callbacks for the Dash app.
# Use the refined professional layout
from .dashboard.layout_pro import serve_layout, INDEX_STRING
from .dashboard.callbacks import register_callbacks


def create_app() -> Dash:
    """Create and configure the Dash application."""
    app = Dash(__name__)
    app.title = "Gamma Exposure Dashboard"
    app.index_string = INDEX_STRING
    app.layout = serve_layout()
    register_callbacks(app)
    return app

"""Initialize environment and logging before app creation."""
# Load environment variables from .env if present (early for logging config)
load_dotenv()

# Configure logging from LOG_LEVEL env var
level_str = os.getenv("LOG_LEVEL", "INFO").upper()
level = getattr(logging, level_str, logging.INFO)
logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
# Quiet noisy werkzeug logs in production
if level <= logging.INFO:
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Instantiate the Dash app.
# This is the main entry point for the application.
app = create_app()


if __name__ == "__main__":
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=8050, debug=debug_mode)

# Dash automatically wraps a Flask server underneath.
# The Flask server is used to serve the Dash app and handle HTTP requests.
# app.layout describes the layout of the app, which is rendered in the browser.
# register_callbacks is used to register the callbacks that handle user interactions with the app.
