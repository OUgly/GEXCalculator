"""Dash callback definitions for the Gamma Exposure dashboard."""

import base64
import io
import json
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from dash import dcc, html, Input, Output, State, no_update, callback_context

from ..gex_backend import run_gex_analysis, load_chain_data
from .layout import DARK_THEME
from db import SessionLocal
from ..notes import get_or_create_note, update_note


def register_callbacks(app):
    """Register all Dash callbacks with the provided app instance."""

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
        """Process uploaded or fetched option chain data and store results."""
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
                    return None, "❌ Error fetching data. Ticker may not exist.", None, ticker, ""

            df, spot, zero, levels, profile = run_gex_analysis(json_data, ticker)

            def format_expiry_label(exp_date):
                from datetime import datetime
                date_str = exp_date.split(':')[0]
                date = datetime.strptime(date_str, '%Y-%m-%d')
                return f"Week of {date.strftime('%B %d')}", exp_date

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
                "raw_json": json_data
            }

            total_gex = df["TotalGEX"].sum()
            summary = f"Total GEX: {total_gex:+.2f}Bn | Spot: {spot:.2f}"
            if zero:
                summary += f" | Zero Gamma: {zero:.2f}"
            else:
                if button_id == 'fetch-chain-button':
                    summary += " | No Zero Gamma crossing found"

            return store, summary, None, ticker, ""

        except Exception as e:  # pragma: no cover - debug helper
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
        """Populate the expiry dropdown after data has been processed."""
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
        """Render the appropriate chart based on user selections."""
        if not data:
            return "Please upload data first."

        df = pd.DataFrame(data["df"])
        spot = data.get("spot", 0)
        zero = data.get("zero", None)
        levels = data.get("levels", [])
        profile = data.get("profile", [])

        if selected_expiry:
            df['NormalizedExpiry'] = df['Expiry'].apply(lambda x: x.split(':')[0] if ':' in x else x)
            normalized_selected = selected_expiry.split(':')[0] if ':' in selected_expiry else selected_expiry
            df = df[df['NormalizedExpiry'] == normalized_selected]
            json_data = data.get("raw_json", {})
            if json_data:
                ticker = data.get("ticker", "")
                _, spot, zero, levels, profile = run_gex_analysis(json_data, ticker, selected_expiry=selected_expiry)

        if selected_month and selected_month != "ALL":
            df['Month'] = pd.to_datetime(df['Expiry']).dt.strftime('%b').str.upper()
            df = df[df['Month'] == selected_month]

        chart_layout = {
            "template": theme,
            "font": {"size": 12, "color": DARK_THEME['text']},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "height": 700,
            "margin": dict(l=50, r=40, t=50, b=40),
            "xaxis": {"gridcolor": "#333333", "zerolinecolor": "#333333", "title_font": {"size": 14}, "nticks": 20},
            "yaxis": {"gridcolor": "#333333", "zerolinecolor": "#333333", "title_font": {"size": 14}},
            "legend": {"bgcolor": "rgba(0,0,0,0)", "font": {"size": 12}}
        }

        filtered_df = df

        if tab == "tab-overview":
            fig = go.Figure()
            fig.add_trace(go.Bar(x=filtered_df["Strike"], y=filtered_df["TotalGEX"], name="Total GEX", marker_color=DARK_THEME['accent']))
            fig.add_vline(x=spot, line_color="red", annotation_text=f"Spot: {spot:.2f}")
            if zero:
                fig.add_vline(x=zero, line_color="green", annotation_text=f"Zero Gamma: {zero:.2f}", annotation_position="left")
            fig.add_trace(go.Scatter(x=levels, y=profile, name="GEX Profile", line=dict(color=DARK_THEME['accent-light'], width=2), yaxis="y2"))
            fig.update_layout(title="Gamma Exposure Overview", xaxis_title="Strike Price", yaxis_title="Gamma Exposure (Bn)",
                              yaxis2=dict(title="GEX Profile", overlaying="y", side="right", showgrid=False), **chart_layout)
            return dcc.Graph(figure=fig, style={"backgroundColor": DARK_THEME['background']})

        if tab == "tab-detail":
            fig = make_subplots(rows=2, cols=1, subplot_titles=("Call vs Put Gamma Exposure", "Call vs Put Open Interest"), vertical_spacing=0.15)
            fig.add_trace(go.Bar(x=filtered_df["Strike"], y=filtered_df["CallGEX"], name="Call GEX", marker_color='green', opacity=0.7), row=1, col=1)
            fig.add_trace(go.Bar(x=filtered_df["Strike"], y=filtered_df["PutGEX"], name="Put GEX", marker_color=DARK_THEME['put-color'], opacity=0.7), row=1, col=1)
            fig.add_trace(go.Bar(x=filtered_df["Strike"], y=filtered_df["CallOI"], name="Call OI", marker_color='green', opacity=0.7), row=2, col=1)
            fig.add_trace(go.Bar(x=filtered_df["Strike"], y=filtered_df["PutOI"], name="Put OI", marker_color=DARK_THEME['put-color'], opacity=0.7), row=2, col=1)
            for row in [1, 2]:
                fig.add_vline(x=spot, line_color="red", row=row, col=1, annotation_text=f"Spot: {spot:.2f}" if row == 1 else None)
                if zero:
                    fig.add_vline(x=zero, line_color="green", row=row, col=1, annotation_text=f"Zero Gamma: {zero:.2f}" if row == 1 else None, annotation_position="left")
            layout = chart_layout.copy()
            layout.update(height=1000, barmode='overlay', showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig.update_layout(**layout)
            fig.update_xaxes(title_text="Strike Price", row=2, col=1)
            fig.update_yaxes(title_text="Gamma Exposure (Bn)", row=1, col=1)
            fig.update_yaxes(title_text="Open Interest", row=2, col=1)
            return dcc.Graph(figure=fig, style={"backgroundColor": DARK_THEME['background']})

        if tab == "tab-curve":
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(x=levels, y=profile, mode='lines', name='Gamma Profile', line=dict(color=DARK_THEME['accent'], width=2)))
            fig_curve.add_hline(y=0, line_color="#333333")
            fig_curve.add_vline(x=spot, line_color="red", annotation_text=f"Spot: {spot:.2f}")
            if zero:
                fig_curve.add_vline(x=zero, line_color="green", annotation_text=f"Zero Gamma: {zero:.2f}", annotation_position="left")
            fig_curve.update_layout(title="Gamma Exposure Profile", **chart_layout)
            return dcc.Graph(figure=fig_curve, style={"backgroundColor": DARK_THEME['background']})

        if tab == "tab-callput":
            fig_callput = go.Figure()
            fig_callput.add_bar(x=df["Strike"], y=df["CallGEX"] / 1e9, name="Call Gamma", marker_color=DARK_THEME['accent'])
            fig_callput.add_bar(x=df["Strike"], y=df["PutGEX"] / 1e9, name="Put Gamma", marker_color=DARK_THEME['put-color'])
            fig_callput.add_vline(x=spot, line_color="red", annotation_text=f"Spot: {spot:.2f}")
            fig_callput.update_layout(title="Call vs Put Gamma Exposure", xaxis_title="Strike", yaxis_title="Gamma (Bn)", barmode="relative", **chart_layout)
            return dcc.Graph(figure=fig_callput, style={"backgroundColor": DARK_THEME['background']})

        if tab == "tab-oi":
            fig_oi = go.Figure()
            fig_oi.add_bar(x=df["Strike"], y=df["CallOI"], name="Call OI", marker_color=DARK_THEME['accent'])
            fig_oi.add_bar(x=df["Strike"], y=-df["PutOI"], name="Put OI", marker_color=DARK_THEME['put-color'])
            fig_oi.add_vline(x=spot, line_color="red", annotation_text=f"Spot: {spot:.2f}")
            fig_oi.update_layout(title="Open Interest Distribution", xaxis_title="Strike", yaxis_title="Open Interest", barmode="relative", **chart_layout)
            return dcc.Graph(figure=fig_oi, style={"backgroundColor": DARK_THEME['background']})

        return "Unsupported tab selected"

    @app.callback(
        Output("notes-sidebar", "style"),
        Input("notes-toggle", "n_clicks"),
        State("notes-sidebar", "style"),
        prevent_initial_call=True,
    )
    def toggle_notes(n_clicks, style):
        style = style or {}
        current = style.get("transform", "translateX(100%)")
        style["transform"] = "translateX(0)" if current != "translateX(0)" else "translateX(100%)"
        return style

    @app.callback(
        [Output("notes-tabs", "children"), Output("notes-tabs", "value")],
        Input("gex-store", "data"),
        State("notes-tabs", "children"),
        prevent_initial_call=True,
    )
    def ensure_notes_tab(gex_data, children):
        symbol = (gex_data or {}).get("ticker") if isinstance(gex_data, dict) else None
        if not symbol:
            return no_update, no_update
        children = children or []
        existing_values = [
            (c.get("props", {}).get("value") if isinstance(c, dict) else getattr(c, "value", None))
            for c in children
        ]
        if symbol not in existing_values:
            children.append(dcc.Tab(label=symbol, value=symbol))
        return children, symbol

    @app.callback(
        Output("ui-store", "data"),
        Input("notes-editor", "value"),
        State("notes-tabs", "value"),
        prevent_initial_call=True,
    )
    def save_note(content, symbol):
        if not symbol:
            return no_update
        with SessionLocal() as session:
            update_note(session, symbol, content or "")
        return no_update

    @app.callback(
        Output("notes-editor", "value"),
        Input("notes-tabs", "value"),
        prevent_initial_call=True,
    )
    def load_note(symbol):
        if not symbol:
            return ""
        with SessionLocal() as session:
            note = get_or_create_note(session, symbol)
            return note.content
