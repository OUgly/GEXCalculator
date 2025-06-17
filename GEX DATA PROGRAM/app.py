import base64
import json
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output, State, no_update, callback_context
from gex_backend import run_gex_analysis, get_chain_data, load_chain_data

app = Dash(__name__)
app.title = "Gamma Exposure Dashboard"

# Define theme colors
DARK_THEME = {
    'background': '#000000',  # Changed to pure black
    'secondary-background': '#1a1a1a',  # Darker secondary background
    'text': '#e0e0e0',
    'accent': '#4C008F',
    'accent-light': '#6b00cc',
    'put-color': "#460023"  # Red color for puts, you can change this to any color you want
}

# Add CSS for full black background
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                margin: 0;
                background-color: #000000;
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
'''

# Define the layout
app.layout = html.Div(
    children=[
        # Header section
        html.Div(
            children=[
                html.H1(
                    "Gamma Exposure Dashboard", 
                    style={
                        "color": DARK_THEME['text'],
                        "fontSize": "28px",
                        "fontWeight": "500",
                        "marginBottom": "10px"
                    }
                )
    ], style={
        "padding": "20px",
        "backgroundColor": DARK_THEME['secondary-background'],
        "borderRadius": "10px",
        "marginBottom": "20px",
        "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)"
    }),

    # Controls section
    html.Div([
        html.Div([
            # File upload and ticker input
            html.Div([
                dcc.Upload(
                    id='upload-json',
                    children=html.Button('📁 Upload JSON', style={
                        "backgroundColor": DARK_THEME['accent'],
                        "color": "white",
                        "border": "none",
                        "padding": "10px 20px",
                        "borderRadius": "5px",
                        "cursor": "pointer",
                        "fontSize": "14px"
                    }),
                    multiple=False
                ),
                dcc.Input(
                    id='ticker-input',
                    type='text',
                    placeholder='Ticker (e.g. SOXL)',
                    style={
                        "padding": "8px 15px",
                        "borderRadius": "5px",
                        "border": f"1px solid {DARK_THEME['accent']}",
                        "backgroundColor": DARK_THEME['background'],
                        "color": DARK_THEME['text'],
                        "marginLeft": "10px",
                        "width": "120px"
                    }
                ),
                # Add Fetch Chain button
                html.Button('🔄 Fetch Chain', 
                    id='fetch-chain-button',
                    style={
                        "backgroundColor": DARK_THEME['accent'],
                        "color": "white",
                        "border": "none",
                        "padding": "10px 20px",
                        "borderRadius": "5px",
                        "cursor": "pointer",
                        "fontSize": "14px",
                        "marginLeft": "10px"
                    }
                ),
            ], style={"display": "flex", "alignItems": "center"}),

            # Expiry filter and theme toggle
            html.Div([                dcc.Dropdown(
                    id='expiry-filter',
                    placeholder="Select Week",
                    style={
                        "width": "180px",
                        "backgroundColor": DARK_THEME['background'],
                        "color": DARK_THEME['text']
                    }
                ),
                # Add month filter dropdown
                dcc.Dropdown(
                    id='month-filter',
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
                        {"label": "December", "value": "DEC"}
                    ],
                    value="ALL",
                    clearable=False,
                    placeholder="Filter by Month",
                    style={
                        "width": "150px",
                        "marginLeft": "10px",
                        "backgroundColor": DARK_THEME['background'],
                        "color": DARK_THEME['text']
                    }
                ),
                html.Button(
                    'Run Analysis',
                    id='run-button',
                    style={
                        "backgroundColor": DARK_THEME['accent'],
                        "color": "white",
                        "border": "none",
                        "padding": "10px 20px",
                        "borderRadius": "5px",
                        "marginLeft": "10px",
                        "cursor": "pointer",
                        "fontSize": "14px"
                    }
                ),
                dcc.Dropdown(
                    id='theme-toggle',
                    options=[
                        {"label": "Dark Mode", "value": "plotly_dark"},
                        {"label": "Light Mode", "value": "plotly_white"}
                    ],
                    value="plotly_dark",
                    clearable=False,
                    style={
                        "width": "150px",
                        "marginLeft": "10px",
                        "backgroundColor": DARK_THEME['background'],
                        "color": DARK_THEME['text']
                    }
                )
            ], style={
                "display": "flex",
                "alignItems": "center",
                "marginTop": "10px"
            })
        ], style={
            "padding": "20px",
            "backgroundColor": DARK_THEME['secondary-background'],
            "borderRadius": "10px",
            "marginBottom": "20px",
            "boxShadow": "0 4px 6px rgba(0, 0, 0, 0.1)"
        })
    ], style={"marginBottom": "20px"}, id="controls"),

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
            dcc.Tab(label='GEX Overview', value="tab-overview"),
            dcc.Tab(label='Call/Put Analysis', value="tab-detail")
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
            "fontSize": "12px"    }
    ),
    
    # Store components
    dcc.Store(id="gex-store"),
    dcc.Store(id='ui-store'),
    
    # Error message container
    html.Div(
        id='error-message', 
        style={
            "color": "#ff3333",
            "marginTop": "10px",
            "textAlign": "center",
            "fontWeight": "bold"
        }
    )],
    style={
        "width": "95%",
        "maxWidth": "1800px",
        "margin": "auto",
        "padding": "20px",
        "minHeight": "100vh",
        "backgroundColor": DARK_THEME['background'],
        "color": DARK_THEME['text']
    }
)




@app.callback(
    [Output('gex-store', 'data'),
     Output('summary', 'children'),
     Output('ui-store', 'data'),
     Output('ticker-input', 'value'),
     Output('error-message', 'children')],
    [Input('run-button', 'n_clicks'),
     Input('fetch-chain-button', 'n_clicks')],
    [State('upload-json', 'contents'),
     State('ticker-input', 'value')],
    prevent_initial_call=True
)
def process_data(run_clicks, fetch_clicks, file_contents, ticker_input):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update, no_update
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        if button_id == 'run-button':
            if not file_contents:
                return None, "⚠️ Upload JSON first.", None, "", no_update

            content_string = file_contents.split(',')[1]
            decoded = base64.b64decode(content_string)
            json_data = json.load(io.StringIO(decoded.decode('utf-8')))
            ticker = json_data.get("symbol", "").upper()

        elif button_id == 'fetch-chain-button':
            if not ticker_input:
                return None, "⚠️ Enter a ticker first.", None, "", no_update
                
            ticker = ticker_input.upper()
            json_data = load_chain_data(ticker)
            
            if json_data is None:
                return None, "❌ Error fetching data. Ticker may not exist.", None, ticker, ""        # Process the data
        df, spot, zero, levels, profile = run_gex_analysis(json_data, ticker)
          # Format expiry dates nicely
        def format_expiry_label(exp_date):
            from datetime import datetime            # Handle both formats: '2025-06-21:1' and plain date strings
            date_str = exp_date.split(':')[0]
            date = datetime.strptime(date_str, '%Y-%m-%d')
            # Keep the original expiry format in the value to preserve API compatibility
            return f"Week of {date.strftime('%B %d')}", exp_date  # Return both display label and raw value
            
        expiries = sorted(df["Expiry"].unique())
        expiry_options = [{"label": label, "value": value} for label, value in [format_expiry_label(e) for e in expiries]]
        store = {
            "df": df.to_dict("records"),
            "spot": spot,
            "zero": zero,
            "levels": list(levels),
            "profile": list(profile),
            "ticker": ticker,
            "expiries": expiry_options,
            "raw_json": json_data  # Store the raw data for recalculation
        }

        # Update summary to include info about zero gamma
        total_gex = df["TotalGEX"].sum()
        summary = f"Total GEX: {total_gex:+.2f}Bn | Spot: {spot:.2f}"
        if zero:
            summary += f" | Zero Gamma: {zero:.2f}"
        else:
            if button_id == 'fetch-chain-button':
                summary += " | No Zero Gamma crossing found"
            
        return store, summary, None, ticker, ""

    except Exception as e:
        print(f"Error in process_data: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None, f"❌ Error: {str(e)}", None, ticker if ticker_input else "", f"❌ Error: {str(e)}"


@app.callback(
    Output('expiry-filter', 'options'),
    Input('gex-store', 'data'),
    prevent_initial_call=True
)
def update_expiry_options(data):
    return data.get("expiries", []) if data else []
@app.callback(
    Output('tab-content', 'children'),
    [Input('tabs', 'value'),
     Input('gex-store', 'data'),
     Input('theme-toggle', 'value'),
     Input('expiry-filter', 'value'),
     Input('month-filter', 'value')],
    prevent_initial_call=True
)
def display_chart(tab, data, theme, selected_expiry, selected_month):
    if not data:
        return "Please upload data first."
    
    df = pd.DataFrame(data["df"])
    spot = data.get("spot", 0)
    zero = data.get("zero", None)
    levels = data.get("levels", [])
    profile = data.get("profile", [])
    filtered_data = data.get("filtered_data", {})
    
    # Debug info for zero gamma calculation
    print(f"Debug - Zero Gamma: {zero}")
    print(f"Debug - Profile Shape: {len(profile)}")
    print(f"Debug - Levels Shape: {len(levels)}")
    if profile:
        print(f"Debug - Profile Range: {min(profile)} to {max(profile)}")    # Apply filters and recalculate
    if selected_expiry:
        print(f"\nDebug - Selected expiry: {selected_expiry}")
        print(f"Debug - Available expiries in df: {df['Expiry'].unique()}")
          # Use the normalized expiry date for filtering
        df['NormalizedExpiry'] = df['Expiry'].apply(lambda x: x.split(':')[0] if ':' in x else x)
        normalized_selected = selected_expiry.split(':')[0] if ':' in selected_expiry else selected_expiry
        df = df[df['NormalizedExpiry'] == normalized_selected]
        
        # Recalculate zero gamma and profile for the filtered data
        json_data = data.get("raw_json", {})
        if json_data:
            from gex_backend import run_gex_analysis
            ticker = data.get("ticker", "")
            print(f"Debug - Calling run_gex_analysis with expiry: {selected_expiry}")
            _, spot, zero, levels, profile = run_gex_analysis(json_data, ticker, selected_expiry=selected_expiry)
            print(f"Recalculated for {selected_expiry} - Zero Gamma: {zero}")
    
    if selected_month and selected_month != "ALL":
        # Extract month from expiry dates and filter
        df['Month'] = pd.to_datetime(df['Expiry']).dt.strftime('%b').str.upper()
        df = df[df['Month'] == selected_month]
    
    # Common chart settings
    chart_layout = {
        "template": theme,
        "font": {"size": 12, "color": DARK_THEME['text']},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "height": 700,
        "margin": dict(l=50, r=40, t=50, b=40),
        "xaxis": {
            "gridcolor": "#333333",
            "zerolinecolor": "#333333",
            "title_font": {"size": 14},
            "nticks": 20
        },
        "yaxis": {
            "gridcolor": "#333333",
            "zerolinecolor": "#333333",
            "title_font": {"size": 14}
        },
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 12}
        }
    }    # Apply data filters if needed
    if selected_expiry or selected_month:
        filtered_df = df.copy()
        if selected_expiry:
            filtered_df['NormalizedExpiry'] = filtered_df['Expiry'].apply(lambda x: x.split(':')[0] if ':' in x else x)
            normalized_selected = selected_expiry.split(':')[0] if ':' in selected_expiry else selected_expiry
            filtered_df = filtered_df[filtered_df['NormalizedExpiry'] == normalized_selected]
        if selected_month and selected_month != "ALL":
            filtered_df['Month'] = pd.to_datetime(filtered_df['Expiry']).dt.strftime('%b').str.upper()
            filtered_df = filtered_df[filtered_df['Month'] == selected_month]
    else:
        filtered_df = df

    if tab == "tab-overview":
        # Create a figure with subplots
        fig = go.Figure()
        
        # Total GEX by Strike
        fig.add_trace(go.Bar(
            x=filtered_df["Strike"],
            y=filtered_df["TotalGEX"],
            name="Total GEX",
            marker_color=DARK_THEME['accent']
        ))
        
        # Add zero gamma and spot lines
        fig.add_vline(x=spot, line_color="red", annotation_text=f"Spot: {spot:.2f}")
        if zero:
            fig.add_vline(
                x=zero,
                line_color="green",
                annotation_text=f"Zero Gamma: {zero:.2f}",
                annotation_position="left"
            )
        
        # Add the GEX curve on the same plot with a secondary y-axis
        fig.add_trace(go.Scatter(
            x=levels,
            y=profile,
            name="GEX Profile",
            line=dict(color=DARK_THEME['accent-light'], width=2),
            yaxis="y2"
        ))
        
        # Update layout with both y-axes
        fig.update_layout(
            title="Gamma Exposure Overview",
            xaxis_title="Strike Price",
            yaxis_title="Gamma Exposure (Bn)",
            yaxis2=dict(
                title="GEX Profile",
                overlaying="y",
                side="right",
                showgrid=False
            ),
            **chart_layout
        )
        return dcc.Graph(figure=fig, style={"backgroundColor": DARK_THEME['background']})
    
    elif tab == "tab-detail":
        # Create subplots for Call vs Put analysis
        fig = make_subplots(rows=2, cols=1,
                           subplot_titles=("Call vs Put Gamma Exposure", "Call vs Put Open Interest"),
                           vertical_spacing=0.15)
        
        # Call vs Put GEX
        fig.add_trace(go.Bar(x=filtered_df["Strike"], y=filtered_df["CallGEX"], name="Call GEX",
                            marker_color='green', opacity=0.7), row=1, col=1)
        fig.add_trace(go.Bar(x=filtered_df["Strike"], y=filtered_df["PutGEX"], name="Put GEX",
                            marker_color=DARK_THEME['put-color'], opacity=0.7), row=1, col=1)
        
        # Call vs Put OI
        fig.add_trace(go.Bar(x=filtered_df["Strike"], y=filtered_df["CallOI"], name="Call OI",
                            marker_color='green', opacity=0.7), row=2, col=1)
        fig.add_trace(go.Bar(x=filtered_df["Strike"], y=filtered_df["PutOI"], name="Put OI",
                            marker_color=DARK_THEME['put-color'], opacity=0.7), row=2, col=1)
        
        # Add spot and zero gamma lines to both plots
        for row in [1, 2]:
            fig.add_vline(x=spot, line_color="red", row=row, col=1,
                         annotation_text=f"Spot: {spot:.2f}" if row == 1 else None)
            if zero:
                fig.add_vline(x=zero, line_color="green", row=row, col=1,
                             annotation_text=f"Zero Gamma: {zero:.2f}" if row == 1 else None,
                             annotation_position="left")
        
        # Update layout
        layout = chart_layout.copy()
        layout.update(
            height=1000,  # Increased height for both charts
            barmode='overlay',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        fig.update_layout(**layout)
        
        fig.update_xaxes(title_text="Strike Price", row=2, col=1)
        fig.update_yaxes(title_text="Gamma Exposure (Bn)", row=1, col=1)
        fig.update_yaxes(title_text="Open Interest", row=2, col=1)
        
        return dcc.Graph(figure=fig, style={"backgroundColor": DARK_THEME['background']})

    elif tab == "tab-curve":
        fig_curve = go.Figure()
        fig_curve.add_trace(go.Scatter(
            x=levels,
            y=profile,
            mode='lines',
            name='Gamma Profile',
            line=dict(color=DARK_THEME['accent'], width=2)
        ))
        fig_curve.add_hline(y=0, line_color="#333333")
        fig_curve.add_vline(x=spot, line_color="red", annotation_text=f"Spot: {spot:.2f}")
        if zero:
            fig_curve.add_vline(
                x=zero,
                line_color="green",
                annotation_text=f"Zero Gamma: {zero:.2f}",
                annotation_position="left"
            )
        fig_curve.update_layout(title="Gamma Exposure Profile", **chart_layout)
        return dcc.Graph(figure=fig_curve, style={"backgroundColor": DARK_THEME['background']})

    elif tab == "tab-callput":
        fig_callput = go.Figure()
        fig_callput.add_bar(
            x=df["Strike"],
            y=df["CallGEX"] / 1e9,
            name="Call Gamma",
            marker_color=DARK_THEME['accent']
        )
        fig_callput.add_bar(
            x=df["Strike"],
            y=df["PutGEX"] / 1e9,
            name="Put Gamma",
            marker_color=DARK_THEME['put-color']
        )
        fig_callput.add_vline(x=spot, line_color="red", annotation_text=f"Spot: {spot:.2f}")
        fig_callput.update_layout(
            title="Call vs Put Gamma Exposure",
            xaxis_title="Strike",
            yaxis_title="Gamma (Bn)",
            barmode="relative",
            **chart_layout
        )
        return dcc.Graph(figure=fig_callput, style={"backgroundColor": DARK_THEME['background']})

    elif tab == "tab-oi":
        fig_oi = go.Figure()
        fig_oi.add_bar(
            x=df["Strike"],
            y=df["CallOI"],
            name="Call OI",
            marker_color=DARK_THEME['accent']
        )
        fig_oi.add_bar(
            x=df["Strike"],
            y=-df["PutOI"],
            name="Put OI",
            marker_color=DARK_THEME['put-color']
        )
        fig_oi.add_vline(x=spot, line_color="red", annotation_text=f"Spot: {spot:.2f}")
        fig_oi.update_layout(
            title="Open Interest Distribution",
            xaxis_title="Strike",
            yaxis_title="Open Interest",
            barmode="relative",
            **chart_layout
        )
        return dcc.Graph(figure=fig_oi, style={"backgroundColor": DARK_THEME['background']})


if __name__ == '__main__':
    app.run(debug=True)