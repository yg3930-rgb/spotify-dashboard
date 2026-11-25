"""
app.py
Spotify Top Songs: trends and audio features across countries.

Run:  python app.py   then open http://127.0.0.1:8050

Interaction model:
  * Line chart  - drag horizontally to select a date range.
  * Bar chart   - click a bar to select a song; click it again to deselect.
  * Scatter     - lasso or box-select songs.
  * Sidebar     - the same state as editable controls, plus "Reset all".
Chart interactions write into the sidebar controls ;
the sidebar controls drive every figure .
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
# The bar chart only needs clicks; its toolbar covered the top bar (W4).
BAR_CONFIG = {"displayModeBar": False, "responsive": True}

LINE_TITLE = "How does popularity change over time?"
LINE_HINT = ("Mean Spotify popularity of each country's top 50. Drag across to pick dates. "
             "The break in late April is missing source data, not a drop.")


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
    # W2: a visible bar listing every active filter, so earlier selections
    # can't silently change later results.
    html.Div(id="active-filters", className="active-filters", **{"aria-live": "polite"}),

    html.Div([
        kpi_card("kpi-songs", "songs on the charts"),
        kpi_card("kpi-cross", "songs charting in 2+ countries"),
        kpi_card("kpi-days", "median days a song stays on a chart"),
        kpi_card("kpi-entries", "chart entries"),
    ], className="kpi-row"),

    html.Div([
        html.Section([
            # Title and hint are set by the callback so they always describe what is drawn (W6).
            html.H3(LINE_TITLE, id="line-title"),
            html.P(LINE_HINT, id="line-hint", className="hint"),
            dcc.Graph(id="line-chart", config=GRAPH_CONFIG, style={"height": f"{CHART_HEIGHT}px"}),
            html.Div(id="line-means", className="stat-row"),  # W5: exact averages
        ], className="card"),
        html.Section([
            html.H3("Which songs chart longest, and where?"),
            html.P("Days in a top 50, split by country. Click a bar to select a song; "
                   "click it again to deselect.", className="hint"),
            html.P(id="bar-selection", className="selection-note"),  # W3: selection feedback
            dcc.Graph(id="bar-chart", config=BAR_CONFIG, style={"height": f"{CHART_HEIGHT}px"}),
            html.Div(id="bar-legend", className="bar-legend"),  # W9: legend beside the chart
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
        html.P(id="scatter-stats", className="stat-row"),  # W5: n and correlation
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
    Output("min-days", "value"),
    Output("feature-select", "value"),
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
    keep = no_update
    # Outputs: start, end, songs, countries, min chart-days, scatter feature.

    if trigger == "reset-btn":
        # W1: reset restores EVERY control, including the scatter's slider and feature.
        return DATE_MIN, DATE_MAX, [], list(COUNTRIES), 1, "danceability"

    if trigger == "line-chart":
        rng = _range_from_line_selection(line_sel)
        if rng is None:  # selection cleared by a redraw: keep current state
            return keep, keep, keep, keep, keep, keep
        return rng[0], rng[1], keep, keep, keep, keep

    if trigger == "bar-chart" and bar_click:
        song = bar_click["points"][0]["customdata"][0]
        songs = [s for s in songs if s != song] if song in songs else songs + [song]
        return keep, keep, songs, keep, keep, keep

    if trigger == "scatter-chart" and scatter_sel and scatter_sel.get("points"):
        picked = list(dict.fromkeys(p["customdata"][0] for p in scatter_sel["points"]))
        return keep, keep, picked, keep, keep, keep

    return keep, keep, keep, keep, keep, keep


@app.callback(
    Output("line-chart", "figure"),
    Output("bar-chart", "figure"),
    Output("scatter-chart", "figure"),
    Output("kpi-songs", "children"),
    Output("kpi-cross", "children"),
    Output("kpi-days", "children"),
    Output("kpi-entries", "children"),
    Output("selection-summary", "children"),
    Output("active-filters", "children"),
    Output("active-filters", "className"),
    Output("line-title", "children"),
    Output("line-hint", "children"),
    Output("line-means", "children"),
    Output("bar-selection", "children"),
    Output("bar-legend", "children"),
    Output("scatter-stats", "children"),
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
    songs = songs or []
    min_days = min_days or 1
    start, end = start or DATE_MIN, end or DATE_MAX  # a cleared picker means "all dates"
    scoped = data.filter_rows(DF, countries, start, end)  # country + date filter
    labels = DF.drop_duplicates("spotify_id").set_index("spotify_id")["label"]
    song_names = [labels[s] for s in songs if s in labels.index]

    # ---- line chart: title, hint and annotations follow what is drawn (W6)
    line_rows = data.filter_rows(DF, countries, songs=songs)  # full time span
    if songs:
        one = len(songs) == 1
        line_title = (f"How does “{song_names[0]}” perform over time?" if one
                      else f"How do the {len(songs)} selected songs perform over time?")
        line_hint = ("Popularity on each day the selection charted, by country. Spotify "
                     "popularity is a global score, so lines overlap where a song charted "
                     "in several countries; gaps are days off the chart.")
        y_title = "Popularity (0–100)"
    else:
        line_title, line_hint, y_title = LINE_TITLE, LINE_HINT, "Mean popularity (0–100)"
    line_fig = figures.line_figure(data.line_data(line_rows), start, end,
                                   show_events=not songs,
                                   show_end_labels=not songs, y_title=y_title)

    # W5: exact averages for the brushed period, highest first.
    in_range = data.filter_rows(line_rows, start=start, end=end)
    means = data.country_means(in_range)
    period = f"{pd.to_datetime(start):%b %d}–{pd.to_datetime(end):%b %d}"
    line_means = [html.Span(f"Average, {period}:", className="stat-label")] + [
        html.Span([html.Span(className="swatch", style={"background": COUNTRY_COLORS[c]}),
                   f"{c} {v:.1f}"], className="stat-chip")
        for c, v in means.items()
    ] if len(means) else [html.Span("No data in this period.", className="stat-label")]

    # ---- bar chart
    bar_fig = figures.bar_figure(data.bar_data(scoped, songs), songs)
    if songs:
        shown = "; ".join(song_names[:3]) + (f" and {len(songs) - 3} more" if len(songs) > 3 else "")
        bar_selection = [html.Strong("Selected: "), shown,
                         html.Span(" (click the bar again to deselect)", className="muted")]
    else:
        bar_selection = html.Span("No song selected.", className="muted")
    # W9: compact legend for the countries currently drawn.
    bar_legend = [html.Span([html.Span(className="swatch", style={"background": COUNTRY_COLORS[c]}),
                             COUNTRIES[c]], className="legend-item")
                  for c in COUNTRIES if c in countries]

    # ---- scatter. The minimum chart-days slider only thins the scatter.
    song_rows = data.song_data(scoped)
    song_rows = song_rows[song_rows["chart_days"] >= min_days]
    scatter_fig = figures.scatter_figure(song_rows, feature, songs)
    r, strength = data.correlation(song_rows, feature)
    scatter_stats = (f"n = {len(song_rows):,} songs · Pearson r = {r:.2f} ({strength}) "
                     f"between {FEATURES[feature].split(' ')[0].lower()} and popularity"
                     if r is not None else f"n = {len(song_rows)} songs: too few to compute a correlation")

    # ---- summary numbers
    focus = data.filter_rows(scoped, songs=songs) if songs else scoped
    k = data.kpis(focus)
    summary = (f"{len(countries)} of {len(COUNTRIES)} countries, "
               f"{pd.to_datetime(start):%b %d} to {pd.to_datetime(end):%b %d}, "
               f"{len(songs) if songs else 'all'} song{'s' if not songs or len(songs) != 1 else ''}")

    # ---- W2: active-filter bar
    chips = []
    if len(countries) < len(COUNTRIES):
        chips.append(f"Countries: {', '.join(countries) if countries else 'none'}")
    if pd.to_datetime(start).date() > DATE_MIN or pd.to_datetime(end).date() < DATE_MAX:
        chips.append(f"Dates: {pd.to_datetime(start):%b %d} – {pd.to_datetime(end):%b %d}")
    if songs:
        chips.append(f"Songs: {len(songs)} selected")
    if min_days > 1:
        chips.append(f"Scatter: ≥ {min_days} chart-days")
    if chips:
        active = [html.Strong("Active filters")] + [html.Span(c, className="filter-chip") for c in chips] \
                 + [html.Span("Use Reset all in the sidebar to clear them.", className="muted")]
        active_class = "active-filters is-active"
    else:
        active = [html.Span("No filters active: showing all data.", className="muted")]
        active_class = "active-filters"

    return (line_fig, bar_fig, scatter_fig,
            f"{k['songs']:,}", f"{k['cross']:,}", f"{k['median_days']:.0f}", f"{k['entries']:,}",
            summary, active, active_class, line_title, line_hint, line_means,
            bar_selection, bar_legend, scatter_stats)


if __name__ == "__main__":
    import os
    # W8: debug mode off by default (its toolbar covered the page); set DASH_DEBUG=1 to enable.
    app.run(debug=os.environ.get("DASH_DEBUG") == "1")
