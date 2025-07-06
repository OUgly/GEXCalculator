"""Application entry point for the Gamma Exposure dashboard."""

from dash import Dash

#These definitions are used to create the layout and register callbacks for the Dash app.
from .dashboard.layout import serve_layout, INDEX_STRING
from .dashboard.callbacks import register_callbacks


def create_app() -> Dash:
    """Create and configure the Dash application."""
    app = Dash(__name__)
    app.title = "Gamma Exposure Dashboard"
    app.index_string = INDEX_STRING
    app.layout = serve_layout()
    register_callbacks(app)
    return app

#Instantiate the Dash app.
#This is the main entry point for the application.
app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

# Dash automatically wraps a Flask server underneath.
# The Flask server is used to serve the Dash app and handle HTTP requests.
# app.layout describes the layout of the app, which is rendered in the browser.
# register_callbacks is used to register the callbacks that handle user interactions with the app.