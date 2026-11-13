"""
figures.py
Builds the three Plotly figures. Each function takes already-filtered data
plus the current selection and returns a go.Figure.
"""
import pandas as pd
import plotly.graph_objects as go

from config import (
    COUNTRIES, COUNTRY_COLORS, EVENTS, FEATURES, RANK_BANDS, RANK_BAND_COLORS,
    CHART_HEIGHT, SCATTER_HEIGHT, FONT_FAMILY, TEXT_COLOR, MUTED_COLOR, GRID_COLOR, SELECTION_COLOR,
)


def _base_layout(**overrides):
    """Shared minimal style: light grid, no chart junk (data-ink ratio)."""
    layout = dict(
        font=dict(family=FONT_FAMILY, size=12, color=TEXT_COLOR),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=48, r=16, t=8, b=40),
        showlegend=False,  # one shared country legend lives in the sidebar
        hoverlabel=dict(font_family=FONT_FAMILY, bgcolor="white"),
        xaxis=dict(gridcolor=GRID_COLOR, zeroline=False, linecolor="#B8BFC8"),
        yaxis=dict(gridcolor=GRID_COLOR, zeroline=False, linecolor="#B8BFC8"),
        uirevision="keep",  # keep zoom/pan when the data updates
    )
    layout.update(overrides)
    return layout


def _short(text, limit=28):
    """Trim long song labels so the bar chart keeps room for the bars."""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _empty(message, height=CHART_HEIGHT):
    fig = go.Figure()
    fig.update_layout(**_base_layout(
        height=height,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(text=message, showarrow=False, font=dict(color=MUTED_COLOR, size=13))],
    ))
    return fig


def line_figure(daily, start=None, end=None):
    """View 1: mean popularity over time, one line per country.

    x = date (time flows left to right), y = popularity (position, the most
    accurate channel), hue = country. Countries are labelled directly at the
    line ends instead of using a legend.
    """
    if daily.empty:
        return _empty("No data for this selection. Try clearing a filter.")

    fig = go.Figure()
    end_labels = []
    for code, group in daily.groupby("country"):
        color = COUNTRY_COLORS[code]
        fig.add_trace(go.Scatter(
            x=group["snapshot_date"], y=group["popularity"],
            mode="lines", name=COUNTRIES[code],
            line=dict(color=color, width=2),
            connectgaps=False,  # show the data gap honestly
            customdata=group["n_songs"],
            hovertemplate="%{x|%b %d}: %{y:.1f} (avg of %{customdata} songs)<extra>"
                          + COUNTRIES[code] + "</extra>",
        ))
        last = group.dropna(subset=["popularity"]).tail(1)
        if not last.empty:
            end_labels.append([code, last["snapshot_date"].iloc[0], last["popularity"].iloc[0]])

    # Direct labels at line ends, nudged apart so close lines don't overlap.
    if end_labels:
        y_span = daily["popularity"].max() - daily["popularity"].min()
        min_gap = max(y_span, 1) * 0.045
        end_labels.sort(key=lambda item: -item[2])
        for i in range(1, len(end_labels)):
            if end_labels[i - 1][2] - end_labels[i][2] < min_gap:
                end_labels[i][2] = end_labels[i - 1][2] - min_gap
        for code, x, y in end_labels:
            fig.add_annotation(x=x, y=y, text=code, showarrow=False, xanchor="left",
                               xshift=6, font=dict(color=COUNTRY_COLORS[code], size=11))

    # Editorial annotations (see config.EVENTS) for countries currently shown.
    shown = set(daily["country"].unique())
    for event in EVENTS:
        if event["country"] in shown:
            point = daily[(daily["country"] == event["country"])
                          & (daily["snapshot_date"] == pd.Timestamp(event["date"]))]
            if not point.empty and pd.notna(point["popularity"].iloc[0]):
                fig.add_annotation(
                    x=point["snapshot_date"].iloc[0], y=point["popularity"].iloc[0],
                    text=event["text"], showarrow=True, arrowhead=0, arrowcolor=MUTED_COLOR,
                    ax=-90, ay=10, xanchor="right", align="right",
                    font=dict(color=MUTED_COLOR, size=11),
                )

    # Highlight the selected date range instead of cropping the line, so the
    # user keeps the full temporal context. Skip it when nothing is narrowed.
    data_start, data_end = daily["snapshot_date"].min(), daily["snapshot_date"].max()
    if start and end and (pd.Timestamp(start) > data_start or pd.Timestamp(end) < data_end):
        fig.add_vrect(x0=start, x1=end, fillcolor=SELECTION_COLOR, opacity=0.10, line_width=0)

    fig.update_layout(**_base_layout(
        height=CHART_HEIGHT,
        dragmode="select", selectdirection="h",  # horizontal brush = date range
        margin=dict(l=48, r=36, t=8, b=40),
        yaxis=dict(title="Mean popularity (0–100)", gridcolor=GRID_COLOR, zeroline=False),
        xaxis=dict(gridcolor=GRID_COLOR, zeroline=False),
    ))
    return fig


def bar_figure(counts, selected_songs=None):
    """View 2: chart-days per song, stacked by country.

    Bar length = chart-days (length on a common baseline), segment hue =
    country, so songs that chart in several countries are easy to spot.
    """
    if counts.empty:
        return _empty("No songs match this selection.")

    selected = set(selected_songs or [])
    order = (counts.drop_duplicates("spotify_id")
             .sort_values("total")["spotify_id"].tolist())  # longest bar on top
    labels = counts.drop_duplicates("spotify_id").set_index("spotify_id")["label"]

    fig = go.Figure()
    for code, group in counts.groupby("country"):
        # Selected songs stay fully opaque; others fade when a selection exists.
        opacity = [1.0 if (not selected or s in selected) else 0.25 for s in group["spotify_id"]]
        fig.add_trace(go.Bar(
            y=group["spotify_id"], x=group["chart_days"], orientation="h",
            name=COUNTRIES[code],
            marker=dict(color=COUNTRY_COLORS[code], opacity=opacity, line=dict(width=0)),
            customdata=group[["spotify_id", "label"]],
            hovertemplate="%{customdata[1]}<br>" + COUNTRIES[code]
                          + ": %{x} chart-days<extra></extra>",
        ))

    fig.update_layout(**_base_layout(
        height=CHART_HEIGHT,
        barmode="stack", bargap=0.25,
        margin=dict(l=8, r=16, t=8, b=40),
        transition=dict(duration=300),
        xaxis=dict(title="Chart-days (song × country × day in top 50)", gridcolor=GRID_COLOR),
        yaxis=dict(categoryorder="array", categoryarray=order,
                   tickmode="array", tickvals=order, ticktext=[_short(labels[s]) for s in order],
                   automargin=True),
    ))
    return fig


def scatter_figure(songs, feature, selected_songs=None):
    """View 3: one point per song.

    x = chosen audio feature, y = mean popularity (position for the variable
    research question 3 is about), size = chart-days (area for a secondary
    quantity), lightness = best-rank band (ordinal -> ordered luminance).
    """
    if songs.empty:
        return _empty("No songs match this selection.", SCATTER_HEIGHT)

    selected = set(selected_songs or [])
    fig = go.Figure()
    for band in RANK_BANDS:  # draw worst band first so top songs sit on top
        group = songs[songs["rank_band"] == band]
        if group.empty:
            continue
        sel_idx = [i for i, s in enumerate(group["spotify_id"]) if s in selected]
        fig.add_trace(go.Scatter(
            x=group[feature], y=group["popularity"], mode="markers", name=band,
            marker=dict(
                size=group["chart_days"], sizemode="area", sizemin=4,
                sizeref=2.0 * songs["chart_days"].max() / (26 ** 2),
                color=RANK_BAND_COLORS[band], line=dict(color="white", width=0.8),
            ),
            # Brushing highlight: keep every point visible, dim the rest.
            selectedpoints=sel_idx if selected else None,
            unselected=dict(marker=dict(opacity=0.15)),
            customdata=group[["spotify_id", "label", "countries", "best_rank", "chart_days"]],
            hovertemplate=("<b>%{customdata[1]}</b><br>Countries: %{customdata[2]}"
                           "<br>Best rank: #%{customdata[3]}<br>Chart-days: %{customdata[4]}"
                           "<br>" + FEATURES[feature] + ": %{x:.2f}<br>Popularity: %{y:.1f}"
                           "<extra></extra>"),
        ))

    # Median reference lines split the plot into quadrants, so "above or below
    # the typical song" can be read at a glance.
    for value, kind, label in [(songs["popularity"].median(), "h", "median popularity"),
                               (songs[feature].median(), "v", f"median {FEATURES[feature].split(' ')[0].lower()}")]:
        line = dict(line_dash="dot", line_color=MUTED_COLOR, line_width=1, opacity=0.8,
                    annotation_text=label, annotation_font=dict(size=11, color=MUTED_COLOR))
        if kind == "h":
            fig.add_hline(y=value, annotation_position="bottom left", **line)
        else:
            fig.add_vline(x=value, annotation_position="top right", **line)

    fig.update_layout(**_base_layout(
        height=SCATTER_HEIGHT,
        dragmode="lasso", transition=dict(duration=300),
        xaxis=dict(title=FEATURES[feature], range=[0, 1], gridcolor=GRID_COLOR, zeroline=False),
        yaxis=dict(title="Mean popularity (0–100)", gridcolor=GRID_COLOR, zeroline=False),
    ))
    return fig