"""
app.py
Spotify Top Songs: trends and audio features across countries.

Run:  python app.py   then open http://127.0.0.1:8050

Interaction model (all views are coordinated through shared state):
  * Line chart  - drag horizontally to select a date range.
  * Bar chart   - click a bar to add/remove that song from the selection.
  * Scatter     - lasso or box-select songs.
  * Sidebar     - the same state as editable controls, plus "Reset all".
Chart interactions write into the sidebar controls (callback 1);
the sidebar controls drive every figure (callback 2).
"""
from pathlib import Path

import pandas as pd
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

import data
import figures
from config import CHART_HEIGHT, SCATTER_HEIGHT, MIN_DAY_STEPS, COUNTRIES, COUNTRY_COLORS, FEATURES, RANK_BANDS, RANK_BAND_COLORS

# ---------------------------------------------------------------- data ----
DF = data.load_data()
DATE_MIN = DF["snapshot_date"].min().date()
DATE_MAX = DF["snapshot_date"].max().date()
FACTS = data.headline(DF)
SONG_OPTIONS = (
    DF.drop_duplicates("spotify_id").sort_values("label")
    .apply(lambda r: {"label": r["label"], "value": r["spotify_id"]}, axis=1).tolist()
)

app = Dash(
    __name__,
    title="Spotify Top Songs Explorer",
    # Absolute path so styles load no matter which folder the app is run from.
    assets_folder=str(Path(__file__).parent / "assets"),
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap"
    ],
)

GRAPH_CONFIG = {"displaylogo": False, "responsive": True,
                "modeBarButtonsToRemove": ["toImage", "autoScale2d"]}


# -------------------------------------------------------------- layout ----
def country_option(code):
    """Checklist option whose colored swatch doubles as the global legend."""
    return {
        "label": html.Span([
            html.Span(className="swatch", style={"background": COUNTRY_COLORS[code]}),
            COUNTRIES[code],
        ], className="country-label"),
        "value": code,
    }


def kpi_card(card_id, label):
    return html.Div([html.Div(id=card_id, className="kpi-value"),
                     html.Div(label, className="kpi-label")], className="kpi")


sidebar = html.Aside([
    html.H2("Filters"),

    html.Label("Countries", className="control-label"),
    dcc.Checklist(id="country-filter", options=[country_option(c) for c in COUNTRIES],
                  value=list(COUNTRIES), className="country-list"),

    html.Label("Date range", className="control-label"),
    dcc.DatePickerRange(id="date-filter", min_date_allowed=DATE_MIN, max_date_allowed=DATE_MAX,
                        start_date=DATE_MIN, end_date=DATE_MAX, display_format="MMM D, YYYY"),

    html.Label("Songs", className="control-label"),
    dcc.Dropdown(id="song-filter", options=SONG_OPTIONS, value=[], multi=True,
                 placeholder="All songs (click a bar or lasso points)"),

    html.P(id="selection-summary", className="selection-summary"),
    html.Button("Reset all", id="reset-btn", n_clicks=0, className="reset-btn"),
], className="sidebar")

main = html.Main([
    html.Div([
        kpi_card("kpi-songs", "songs on the charts"),
        kpi_card("kpi-cross", "songs charting in 2+ countries"),
        kpi_card("kpi-days", "median days a song stays on a chart"),
        kpi_card("kpi-entries", "chart entries"),
    ], className="kpi-row"),

    html.Div([
        html.Section([
            html.H3("How does popularity change over time?"),
            html.P("Mean Spotify popularity of each country's top 50. Drag across to pick dates. "
                   "The break in late April is missing source data, not a drop.",
                   className="hint"),
            dcc.Graph(id="line-chart", config=GRAPH_CONFIG, style={"height": f"{CHART_HEIGHT}px"}),
        ], className="card"),
        html.Section([
            html.H3("Which songs chart longest, and where?"),
            html.P("Days in a top 50, split by country. Click a bar to select the song.",
                   className="hint"),
            dcc.Graph(id="bar-chart", config=GRAPH_CONFIG, style={"height": f"{CHART_HEIGHT}px"}),
        ], className="card"),
    ], className="row-two"),

    html.Section([
        html.Div([
            html.Div([
                html.H3("Do audio features relate to popularity?"),
                html.P("One point per song. Size shows days on the chart; shade shows best rank. "
                       "Lasso points to select songs. Songs with few chart-days have noisy "
                       "popularity; raise the minimum to hide them.", className="hint"),
            ]),
            html.Div([
                dcc.RadioItems(id="feature-select",
                               options=[{"label": v, "value": k} for k, v in FEATURES.items()],
                               value="danceability", inline=True, className="feature-select"),
                html.Label("Minimum chart-days", htmlFor="min-days", className="control-label"),
                dcc.Slider(id="min-days", min=1, max=30, step=None, value=1,
                           marks={v: str(v) for v in MIN_DAY_STEPS}, className="min-days"),
            ], className="scatter-controls"),
        ], className="card-header"),
        html.Div([
            html.Span([html.Span(className="dot", style={"background": RANK_BAND_COLORS[b]}), b],
                      className="band-key")
            for b in RANK_BANDS
        ], className="band-legend"),
        dcc.Graph(id="scatter-chart", config=GRAPH_CONFIG, style={"height": f"{SCATTER_HEIGHT}px"}),
    ], className="card"),
], className="main")

app.layout = html.Div([
    html.Header([
        html.H1("Spotify top songs across six countries"),
        # Lead with the finding, then tell people how to use the dashboard.
        html.P(
            f"A song stays a median of {FACTS['longest'][1]:g} days on "
            f"{COUNTRIES[FACTS['longest'][0]]}'s chart but only {FACTS['shortest'][1]:g} on "
            f"{COUNTRIES[FACTS['shortest'][0]]}'s, and just {FACTS['cross']} of "
            f"{FACTS['songs']:,} songs chart in two or more countries.",
            className="lead"),
        html.P(f"Daily top 50 charts, {DATE_MIN:%b %d} to {DATE_MAX:%b %d, %Y}. "
               "Drag across the line chart, click a bar, or lasso points to filter every view; "
               "Reset all starts over.", className="how-to"),
    ], className="page-header"),
    html.Div([sidebar, main], className="layout"),
], className="page")


# ----------------------------------------------------------- callbacks ----
def _range_from_line_selection(selected):
    """Extract (start, end) dates from the line chart's selectedData."""
    if not selected:
        return None
    if "range" in selected and "x" in selected["range"]:
        x0, x1 = selected["range"]["x"]
    elif selected.get("points"):
        xs = [p["x"] for p in selected["points"]]
        x0, x1 = min(xs), max(xs)
    else:
        return None
    start, end = sorted([pd.to_datetime(x0).date(), pd.to_datetime(x1).date()])
    return max(start, DATE_MIN), min(end, DATE_MAX)


@app.callback(
    Output("date-filter", "start_date"),
    Output("date-filter", "end_date"),
    Output("song-filter", "value"),
    Output("country-filter", "value"),
    Input("line-chart", "selectedData"),
    Input("bar-chart", "clickData"),
    Input("scatter-chart", "selectedData"),
    Input("reset-btn", "n_clicks"),
    State("song-filter", "value"),
    prevent_initial_call=True,
)
def sync_selection(line_sel, bar_click, scatter_sel, _reset, songs):
    """Callback 1: translate chart interactions into the shared selection state."""
    trigger = ctx.triggered_id
    songs = list(songs or [])

    if trigger == "reset-btn":
        return DATE_MIN, DATE_MAX, [], list(COUNTRIES)

    if trigger == "line-chart":
        rng = _range_from_line_selection(line_sel)
        if rng is None:  # selection cleared by a redraw: keep current state
            return no_update, no_update, no_update, no_update
        return rng[0], rng[1], no_update, no_update

    if trigger == "bar-chart" and bar_click:
        song = bar_click["points"][0]["customdata"][0]
        songs = [s for s in songs if s != song] if song in songs else songs + [song]
        return no_update, no_update, songs, no_update

    if trigger == "scatter-chart" and scatter_sel and scatter_sel.get("points"):
        picked = list(dict.fromkeys(p["customdata"][0] for p in scatter_sel["points"]))
        return no_update, no_update, picked, no_update

    return no_update, no_update, no_update, no_update


@app.callback(
    Output("line-chart", "figure"),
    Output("bar-chart", "figure"),
    Output("scatter-chart", "figure"),
    Output("kpi-songs", "children"),
    Output("kpi-cross", "children"),
    Output("kpi-days", "children"),
    Output("kpi-entries", "children"),
    Output("selection-summary", "children"),
    Input("country-filter", "value"),
    Input("date-filter", "start_date"),
    Input("date-filter", "end_date"),
    Input("song-filter", "value"),
    Input("feature-select", "value"),
    Input("min-days", "value"),
)
def update_views(countries, start, end, songs, feature, min_days):
    """Callback 2: redraw every view from the shared selection state.

    Filtering vs highlighting:
      * countries and dates FILTER all views;
      * songs FILTER the line chart (showing those songs' popularity over
        time) but only HIGHLIGHT in the bar and scatter, so the user keeps
        the context of the other songs.
    """
    countries = countries or []
    start, end = start or DATE_MIN, end or DATE_MAX  # a cleared picker means "all dates"
    scoped = data.filter_rows(DF, countries, start, end)  # country + date filter

    line_rows = data.filter_rows(DF, countries, songs=songs)  # full time span
    line_fig = figures.line_figure(data.line_data(line_rows), start, end)
    bar_fig = figures.bar_figure(data.bar_data(scoped, songs), songs)
    # The minimum chart-days slider only thins the scatter; other views keep all songs.
    song_rows = data.song_data(scoped)
    song_rows = song_rows[song_rows["chart_days"] >= (min_days or 1)]
    scatter_fig = figures.scatter_figure(song_rows, feature, songs)

    focus = data.filter_rows(scoped, songs=songs) if songs else scoped
    k = data.kpis(focus)

    summary = (f"{len(countries)} of {len(COUNTRIES)} countries, "
               f"{pd.to_datetime(start):%b %d} to {pd.to_datetime(end):%b %d}, "
               f"{len(songs) if songs else 'all'} song{'s' if not songs or len(songs) != 1 else ''}")

    return (line_fig, bar_fig, scatter_fig,
            f"{k['songs']:,}", f"{k['cross']:,}", f"{k['median_days']:.0f}", f"{k['entries']:,}",
            summary)


if __name__ == "__main__":
    app.run(debug=True)