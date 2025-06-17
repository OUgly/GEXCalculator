"""Application entry point for the Gamma Exposure dashboard."""

from dash import Dash

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


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
