"""
Environmental Impact Dashboard for Dietary Analysis

This Dash application visualizes the environmental impact of different dietary patterns
using interactive sliders to adjust weightings for various environmental factors. The
visualization is presented as a sunburst chart showing hierarchical breakdown by diet group,
sex, and age group.

Data Source: https://ora.ox.ac.uk/objects/uuid:ca441840-db5a-48c8-9b82-1ec1d77c2e9c
"""

import pandas as pd
import plotly.express as px
import dash
from dash import Dash, html, dcc, Input, Output, State, ctx
import dash_bootstrap_components as dbc
from typing import List, Tuple

# Constants
DATA_URL = "https://raw.githubusercontent.com/milindreddy/RM/refs/heads/main/Results_21Mar2022.csv"
INITIAL_WEIGHTS = [0.25, 0.25, 0.25, 0.25]  # [climate, land, water, chemical]
ENV_CATEGORIES = [
    "Climate Impact",
    "Land & Biodiversity",
    "Water Impact",
    "Chemical Pollution"
]

# Initialize application
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Dietary Environmental Impact Analyzer"


def load_and_preprocess_data(url: str) -> pd.DataFrame:
    """
    Load and preprocess environmental impact data
    """
    # Load raw data
    df = pd.read_csv(url)

    # Z-score normalization for environmental metrics
    z_score_columns = [
        ('mean_ghgs', 'sd_ghgs'),
        ('mean_land', 'sd_land'),
        ('mean_watscar', 'sd_watscar'),
        ('mean_eut', 'sd_eut'),
        ('mean_ghgs_ch4', 'sd_ghgs_ch4'),
        ('mean_ghgs_n2o', 'sd_ghgs_n2o'),
        ('mean_bio', 'sd_bio'),
        ('mean_watuse', 'sd_watuse'),
        ('mean_acid', 'sd_acid')
    ]

    for mean_col, sd_col in z_score_columns:
        # Correct column name generation
        base_name = mean_col.replace('mean_', '')
        z_col = f'z_{base_name}'
        df[z_col] = df[mean_col] / df[sd_col]

    # Create composite environmental scores
    score_groups = {
        'Climate_Impact_Score': ['z_ghgs', 'z_ghgs_ch4', 'z_ghgs_n2o'],
        'Land_Biodiversity_Score': ['z_land', 'z_bio'],
        'Water_Impact_Score': ['z_watscar', 'z_watuse'],
        'Chemical_Pollution_Score': ['z_eut', 'z_acid']
    }

    for score_name, columns in score_groups.items():
        df[score_name] = df[columns].mean(axis=1)

    return df.groupby(['diet_group', 'sex', 'age_group']).agg({
        'Climate_Impact_Score': 'mean',
        'Land_Biodiversity_Score': 'mean',
        'Water_Impact_Score': 'mean',
        'Chemical_Pollution_Score': 'mean'
    }).reset_index()


def adjust_weights(current_weights: List[float], index: int, new_value: float) -> List[float]:
    """
    Adjust weight distribution while maintaining sum of 1

    Args:
        current_weights: Current list of weight values
        index: Index of weight being modified
        new_value: New value for the specified weight

    Returns:
        List[float]: Adjusted list of weights maintaining sum of 1

    """
    weights = current_weights.copy()
    delta = new_value - weights[index]
    weights[index] = new_value

    if delta == 0:
        return weights

    # Redistribute remaining delta across subsequent weights
    direction = -1 if delta > 0 else 1
    remaining_delta = abs(delta)

    for i in range(index + 1, len(weights)):
        available = weights[i] if direction == -1 else (1 - weights[i])
        adjustment = min(remaining_delta, available)

        if direction == -1:
            weights[i] -= adjustment
        else:
            weights[i] += adjustment

        remaining_delta -= adjustment
        if remaining_delta <= 1e-6:
            break

    # Normalize in case of floating point errors
    total = sum(weights)
    if abs(total - 1) > 1e-6:
        weights = [w / total for w in weights]

    return weights


# Load and preprocess data
agg_df = load_and_preprocess_data(DATA_URL)

# Application layout
app.layout = dbc.Container([
    # Header
    html.Div([
        html.H1("Dietary Environmental Impact Analysis", className="display-4"),
        html.P(
            "This Dash application visualizes the environmental impact of different dietary patterns using interactive sliders to adjust weightings for various environmental factors. The visualization is presented as a sunburst chart showing hierarchical breakdown by diet group, sex, and age group.",
            className="lead"
        )
    ], className="mb-4"),

    # Main content row
    dbc.Row([
        # Controls column
        dbc.Col([
            html.Div([
                html.H4("Environmental Impact Weights", className="mb-3"),
                html.Div(id="weight-sliders"),
                html.Br(),
                html.P(
                    [
                        "Adjust the sliders to change the relative importance of different environmental factors. Weights automatically rebalance to maintain sum of 100%. ",
                        html.Br(),
                        html.Br(),
                        html.Small([
                            html.Strong("Climate Impact: "), 
                            "GHG emissions (CO₂), CH4 (livestock), N2O (fertilizers). ",
                            html.Br(),
                            html.Strong("Land/Biodiversity: "), 
                            "Agricultural land use, Species extinction risk. ",
                            html.Br(),
                            html.Strong("Water Impact: "), 
                            "Water scarcity, Agricultural water usage. ",
                            html.Br(),
                            html.Strong("Chemical Pollution: "), 
                            "Eutrophication (algae blooms), Acidification (pH disruption)."
                        ])
                    ],
                    className="text-muted small"
                )
            ], className="card p-3 h-100")
        ], width=4, className="pr-3"),

        # Visualization column
        dbc.Col([
            html.Div([
                dcc.Graph(
                    id="sunburst-graph",
                    config={'displayModeBar': False},
                    className="border rounded",
                    style={'height': '80vh'}
                )
            ], className="h-100")
        ], width=8)
    ], className="g-0"),

    # Hidden storage for weights
    dcc.Store(id="stored-weights", data=INITIAL_WEIGHTS)
], fluid=True, className="p-4")


@app.callback(
    Output("weight-sliders", "children"),
    Input("stored-weights", "data")
)
def render_sliders(weights: List[float]) -> List[dbc.Row]:
    """Generate slider components based on current weights"""
    return [
        dbc.Row([
            dbc.Col(f"{label}", width=3, className="font-weight-bold"),
            dbc.Col(
                dcc.Slider(
                    id=f"weight-slider-{i}",
                    min=0,
                    max=1,
                    step=0.05,
                    value=weight,
                    marks=None,
                    tooltip={"placement": "bottom", "always_visible": True}
                ),
                width=9
            )
        ], align="center", className="mb-3")
        for i, (label, weight) in enumerate(zip(ENV_CATEGORIES, weights))
    ]


@app.callback(
    Output("stored-weights", "data"),
    [Input(f"weight-slider-{i}", "value") for i in range(4)],
    State("stored-weights", "data"),
    prevent_initial_call=True
)
def update_weights(*args) -> List[float]:
    """Handle weight updates from slider interactions"""
    weights = args[-1]
    trigger = ctx.triggered[0]
    index = int(trigger["prop_id"].split(".")[0].split("-")[-1])
    new_value = args[index]
    return adjust_weights(weights, index, new_value)


@app.callback(
    Output("sunburst-graph", "figure"),
    Input("stored-weights", "data")
)
def update_sunburst(weights: List[float]) -> dict:
    """Generate sunburst chart with current weight configuration"""
    temp_df = agg_df.copy()
    temp_df['impact_score'] = (
        temp_df['Climate_Impact_Score'] * weights[0] +
        temp_df['Land_Biodiversity_Score'] * weights[1] +
        temp_df['Water_Impact_Score'] * weights[2] +
        temp_df['Chemical_Pollution_Score'] * weights[3]
    )

    fig = px.sunburst(
        temp_df,
        path=['diet_group', 'sex', 'age_group'],
        values='impact_score',
        color='impact_score',
        color_continuous_scale='RdYlGn_r',
        height=700,
        labels={'impact_score': 'Environmental Impact Score'}
    )

    fig.update_layout(
        title_text="Dietary Impact Hierarchy",
        title_x=0.5,
        margin=dict(t=40, b=20),
        font=dict(family="Arial", size=15),
        coloraxis_colorbar=dict(
        title='Impact Score',
        title_font_size=15,
        tickfont_size=10,
        thickness=30,
        len=0.5,
        yanchor='middle',
        y=0.5)
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Impact Score: %{value:.2f}<extra></extra>"
        )
    )

    return fig

if __name__ == "__main__":
    app.run(debug=True, dev_tools_props_check=False)
