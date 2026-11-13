"""
config.py
Shared constants: data path, country palette, audio features, rank bands.
Keeping these in one place guarantees every view uses the same colors
(Gestalt similarity) and makes the channel table easy to verify.
"""
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "spotify_filtered.csv"

# Country code -> display name. Order = order in the sidebar legend.
COUNTRIES = {
    "US": "United States",
    "DE": "Germany",
    "BR": "Brazil",
    "MX": "Mexico",
    "JP": "Japan",
    "KR": "South Korea",
}

# Okabe-Ito colorblind-safe palette (Okabe & Ito, 2008).
# Categorical data -> hue (identity channel). Yellow is skipped because it
# has poor contrast on a white background.
COUNTRY_COLORS = {
    "US": "#0072B2",  # blue
    "DE": "#E69F00",  # orange
    "BR": "#009E73",  # bluish green
    "MX": "#D55E00",  # vermillion
    "JP": "#CC79A7",  # reddish purple
    "KR": "#56B4E9",  # sky blue
}

# Audio features selectable on the scatter plot's x-axis (all 0-1 scales).
FEATURES = {
    "danceability": "Danceability",
    "energy": "Energy",
    "valence": "Valence (positivity)",
}

# Ordinal rank bands for a song's best daily rank.
# Ordinal data -> luminance (dark = better rank). Greys avoid clashing with
# the country hues, so color hue always means "country" across the dashboard.
RANK_BANDS = ["Top 10", "11-25", "26-50"]
RANK_BAND_COLORS = {"Top 10": "#1F2328", "11-25": "#76808C", "26-50": "#C3C9D1"}

TOP_N_SONGS = 15  # number of songs shown in the bar chart

# Fixed chart heights in px. Set on the figure itself (not only in CSS) so
# Plotly never measures a collapsed container inside the CSS grid.
CHART_HEIGHT = 380
# Steps of the scatter plot's "minimum chart-days" slider.
MIN_DAY_STEPS = [1, 3, 7, 14, 30]
SCATTER_HEIGHT = 460

# Editorial annotations on the line chart: real events found while exploring
# the data. Popularity is a lagging score, so a big album release floods a
# chart with new tracks whose popularity has not caught up yet.
EVENTS = [
    {"country": "US", "date": "2025-05-17",
     "text": "Morgan Wallen album release:<br>30 new tracks enter the US top 50"},
]

# Visual style shared by all Plotly figures.
FONT_FAMILY = "'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif"
TEXT_COLOR = "#1C2024"
MUTED_COLOR = "#5B6470"
GRID_COLOR = "#E6E9ED"
SELECTION_COLOR = "#0B5CAD"