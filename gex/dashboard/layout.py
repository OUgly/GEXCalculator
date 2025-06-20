# Dash layout module
from dash import html, dcc

# Define theme colors used across the dashboard
DARK_THEME = {
    "background": "#121212",
    "secondary-background": "#1A1A1A",
    "text": "#e0e0e0",
    "accent": "#00D4FF",
    "accent-light": "#00A3CC",
    "put-color": "#FF3D71",
}

# Custom index string for a black background
INDEX_STRING = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600&family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body {
                margin: 0;
                background-color: #121212;
                font-family: 'Inter', sans-serif;
            }
            h1, h2, h3 {
                font-family: 'Montserrat', sans-serif;
            }
            .app-container {
                display: flex;
                min-height: 100vh;
                background-color: #121212;
                color: #e0e0e0;
            }
            #sidebar {
                width: 220px;
                background-color: #1A1A1A;
                padding: 20px;
            }
            #main {
                flex: 1;
                padding: 20px;
            }
            .nav-link {
                color: #e0e0e0;
                text-decoration: none;
                display: block;
                padding: 8px 0;
            }
            .nav-link:hover {
                color: #00D4FF;
            }
            #menu-toggle {
                display: none;
            }
            @media (max-width: 768px) {
                #sidebar {
                    position: fixed;
                    left: -220px;
                    top: 0;
                    bottom: 0;
                    z-index: 999;
                    transition: left 0.3s;
                }
                #sidebar.open {
                    left: 0;
                }
                #menu-toggle {
                    display: block;
                    position: fixed;
                    top: 10px;
                    left: 10px;
                    z-index: 1000;
                    background: #00D4FF;
                    color: #121212;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 4px;
                    cursor: pointer;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


def serve_layout():
    """Return the root layout for the Dash application."""
    return html.Div(
        className="app-container",
        children=[
            html.Button("☰", id="menu-toggle"),
            html.Div(
                id="sidebar",
                children=[
                    html.H2("GEX Dashboard", style={"color": DARK_THEME["accent"], "marginBottom": "30px"}),
                    html.A("Options Chain", href="#controls", className="nav-link"),
                    html.A("GEX Overview", href="#", className="nav-link", id="nav-overview"),
                    html.A("Historical GEX", href="#", className="nav-link", id="nav-historical"),
                    html.Button("Notes", id="notes-toggle", className="nav-link", style={"background": "none", "border": "none", "padding": "8px 0", "textAlign": "left", "cursor": "pointer"}),
                ],
            ),
            html.Div(
                id="main",
                children=[
                    html.Div(
                        children=[
                            html.H1(
                                "Gamma Exposure Dashboard",
                                style={"color": DARK_THEME["text"], "fontSize": "28px", "fontWeight": "600", "marginBottom": "10px"},
                            )
                        ],
                        style={
                            "padding": "20px",
                            "backgroundColor": DARK_THEME["secondary-background"],
                            "borderRadius": "10px",
                            "marginBottom": "20px",
                            "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
                        },
                    ),

            # Controls section
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    dcc.Upload(
                                        id="upload-json",
                                        children=html.Button(
                                            "📁 Upload JSON",
                                            style={
                                                "backgroundColor": DARK_THEME["accent"],
                                                "color": "white",
                                                "border": "none",
                                                "padding": "10px 20px",
                                                "borderRadius": "5px",
                                                "cursor": "pointer",
                                                "fontSize": "14px",
                                            },
                                        ),
                                        multiple=False,
                                    ),
                                    dcc.Input(
                                        id="ticker-input",
                                        type="text",
                                        placeholder="Ticker (e.g. SOXL)",
                                        style={
                                            "padding": "8px 15px",
                                            "borderRadius": "5px",
                                            "border": f"1px solid {DARK_THEME['accent']}",
                                            "backgroundColor": DARK_THEME["background"],
                                            "color": DARK_THEME["text"],
                                            "marginLeft": "10px",
                                            "width": "120px",
                                        },
                                    ),
                                    html.Button(
                                        "🔄 Fetch Chain",
                                        id="fetch-chain-button",
                                        style={
                                            "backgroundColor": DARK_THEME["accent"],
                                            "color": "white",
                                            "border": "none",
                                            "padding": "10px 20px",
                                            "borderRadius": "5px",
                                            "cursor": "pointer",
                                            "fontSize": "14px",
                                            "marginLeft": "10px",
                                        },
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center"},
                            ),
                            html.Div(
                                [
                                    dcc.Dropdown(
                                        id="expiry-filter",
                                        placeholder="Select Week",
                                        style={
                                            "width": "180px",
                                            "backgroundColor": DARK_THEME["background"],
                                            "color": DARK_THEME["text"],
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="month-filter",
                                        options=[
                                            {"label": "All Months", "value": "ALL"},
                                            {"label": "January", "value": "JAN"},
                                            {"label": "February", "value": "FEB"},
                                            {"label": "March", "value": "MAR"},
                                            {"label": "April", "value": "APR"},
                                            {"label": "May", "value": "MAY"},
                                            {"label": "June", "value": "JUN"},
                                            {"label": "July", "value": "JUL"},
                                            {"label": "August", "value": "AUG"},
                                            {"label": "September", "value": "SEP"},
                                            {"label": "October", "value": "OCT"},
                                            {"label": "November", "value": "NOV"},
                                            {"label": "December", "value": "DEC"},
                                        ],
                                        value="ALL",
                                        clearable=False,
                                        placeholder="Filter by Month",
                                        style={
                                            "width": "150px",
                                            "marginLeft": "10px",
                                            "backgroundColor": DARK_THEME["background"],
                                            "color": DARK_THEME["text"],
                                        },
                                    ),
                                    html.Button(
                                        "Run Analysis",
                                        id="run-button",
                                        style={
                                            "backgroundColor": DARK_THEME["accent"],
                                            "color": "white",
                                            "border": "none",
                                            "padding": "10px 20px",
                                            "borderRadius": "5px",
                                            "marginLeft": "10px",
                                            "cursor": "pointer",
                                            "fontSize": "14px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="theme-toggle",
                                        options=[
                                            {"label": "Dark Mode", "value": "plotly_dark"},
                                            {"label": "Light Mode", "value": "plotly_white"},
                                        ],
                                        value="plotly_dark",
                                        clearable=False,
                                        style={
                                            "width": "150px",
                                            "marginLeft": "10px",
                                            "backgroundColor": DARK_THEME["background"],
                                            "color": DARK_THEME["text"],
                                        },
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center", "marginTop": "10px"},
                            ),
                        ],
                        style={
                            "padding": "20px",
                            "backgroundColor": DARK_THEME["secondary-background"],
                            "borderRadius": "10px",
                            "marginBottom": "20px",
                            "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
                        },
                    )
                ],
                style={"marginBottom": "20px"},
                id="controls",
            ),

            # Summary section
            html.Div(
                id='summary',
                style={
                    "backgroundColor": DARK_THEME['secondary-background'],
                    "color": DARK_THEME['text'],
                    "padding": "15px",
                    "borderRadius": "10px",
                    "marginBottom": "20px",
                    "fontSize": "16px",
                    "textAlign": "center",
                    "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)"
                }
            ),

            # Tabs section
            dcc.Tabs(
                id="tabs",
                value="tab-overview",
                children=[
                    dcc.Tab(label="GEX Overview", value="tab-overview"),
                    dcc.Tab(label="Call/Put Analysis", value="tab-detail"),
                    dcc.Tab(label="Historical GEX", value="tab-historical"),
                ],
                colors={
                    "border": DARK_THEME['accent'],
                    "primary": DARK_THEME['accent'],
                    "background": DARK_THEME['secondary-background']
                }
            ),

            # Content section
            html.Div(
                id='tab-content',
                style={
                    "backgroundColor": DARK_THEME['secondary-background'],
                    "borderRadius": "10px",
                    "padding": "20px",
                    "marginTop": "20px",
                    "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)"
                }
            ),

            # Footer
            html.Div(
                "Built by Louie | v1.0",
                style={
                    "textAlign": "center",
                    "marginTop": "40px",
                    "marginBottom": "20px",
                    "color": DARK_THEME['text'],
                    "opacity": "0.7",
                    "fontSize": "12px"
                }
            ),

            # Store components
            dcc.Store(id="gex-store"),
            dcc.Store(id='ui-store'),

            # Error message container
            html.Div(
                id="error-message",
                style={"color": "#ff3333", "marginTop": "10px", "textAlign": "center", "fontWeight": "bold"},
            ),

            # Hidden notes sidebar
            html.Div(
                [
                    dcc.Dropdown(
                        id="symbol-dropdown",
                        placeholder="Select Symbol",
                        options=[],
                        style={"marginBottom": "10px", "width": "100%"},
                    ),
                    dcc.Tabs(id="notes-tabs", children=[], persistence=True),
                    dcc.Textarea(
                        id="notes-editor",
                        style={"width": "100%", "height": "80vh"},
                    ),
                ],
                id="notes-sidebar",
                style={
                    "position": "fixed",
                    "right": 0,
                    "top": 0,
                    "width": "320px",
                    "height": "100vh",
                    "transform": "translateX(100%)",
                    "transition": "transform 0.3s",
                    "backgroundColor": DARK_THEME["secondary-background"],
                    "padding": "10px",
                    "zIndex": 999,
                },
            )
        ],
        style={
            "width": "95%",
            "maxWidth": "1800px",
            "margin": "auto",
            "padding": "20px",
            "minHeight": "100vh",
            "backgroundColor": DARK_THEME["background"],
            "color": DARK_THEME["text"],
        },
    ),
]
    )
