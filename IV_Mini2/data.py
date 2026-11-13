"""
data.py
Loading and aggregation. Every function here is pure pandas (no Dash),
so it can be tested on its own.
"""
import numpy as np
import pandas as pd

from config import DATA_PATH, RANK_BANDS, TOP_N_SONGS


def load_data(path=DATA_PATH):
    """Load the preprocessed CSV and add the derived columns the views need."""
    df = pd.read_csv(path, parse_dates=["snapshot_date"])

    # Spotify reports popularity = 0 for brand-new releases (it has not been
    # computed yet), e.g. a song at #1 on its release day. Treat as missing.
    df["popularity"] = df["popularity"].replace(0, np.nan)

    # Readable label for dropdowns, axes and tooltips.
    df["label"] = df["name"].str.slice(0, 32) + " – " + df["artists"].str.split(",").str[0]
    return df


def filter_rows(df, countries=None, start=None, end=None, songs=None):
    """Apply the global selection state.

    countries: None = no filter, [] = nothing selected (empty result).
    start/end/songs: None or empty = no filter.
    """
    mask = pd.Series(True, index=df.index)
    if countries is not None:
        mask &= df["country"].isin(countries)
    if start:
        mask &= df["snapshot_date"] >= pd.to_datetime(start)
    if end:
        mask &= df["snapshot_date"] <= pd.to_datetime(end)
    if songs:
        mask &= df["spotify_id"].isin(songs)
    return df[mask]


def line_data(df):
    """Mean popularity per country per day, re-indexed onto every calendar day.

    n_songs = how many songs had a popularity score that day (shown in the
    tooltip so users can judge how reliable each average is).
    Days missing from the source (2025-04-22 to 04-29) become NaN so the line
    breaks instead of drawing a misleading straight segment across the gap.
    """
    daily = df.groupby(["country", "snapshot_date"])["popularity"].agg(
        popularity="mean", n_songs="count")
    if daily.empty:
        return daily.reset_index()
    all_days = pd.date_range(df["snapshot_date"].min(), df["snapshot_date"].max(), freq="D")
    full_index = pd.MultiIndex.from_product(
        [daily.index.get_level_values(0).unique(), all_days], names=["country", "snapshot_date"]
    )
    return daily.reindex(full_index).reset_index()


def bar_data(df, selected_songs=None, top_n=TOP_N_SONGS):
    """Chart-days per (song, country) for the top songs, plus any selected songs.

    A 'chart-day' is one appearance of a song in one country's daily top 50.
    """
    per_song = df.groupby("spotify_id").size().sort_values(ascending=False)
    keep = list(per_song.head(top_n).index)
    for song in selected_songs or []:  # selected songs always stay visible
        if song in per_song.index and song not in keep:
            keep.append(song)

    counts = (
        df[df["spotify_id"].isin(keep)]
        .groupby(["spotify_id", "label", "country"])
        .size()
        .rename("chart_days")
        .reset_index()
    )
    counts["total"] = counts.groupby("spotify_id")["chart_days"].transform("sum")
    return counts


def song_data(df):
    """One row per song: the marks of the scatter plot."""
    songs = df.groupby(["spotify_id", "label"]).agg(
        popularity=("popularity", "mean"),
        danceability=("danceability", "first"),
        energy=("energy", "first"),
        valence=("valence", "first"),
        best_rank=("daily_rank", "min"),
        chart_days=("snapshot_date", "size"),
        countries=("country", lambda s: ", ".join(sorted(s.unique()))),
    ).reset_index()
    songs = songs.dropna(subset=["popularity"])
    songs["rank_band"] = pd.cut(
        songs["best_rank"], bins=[0, 10, 25, 50], labels=RANK_BANDS
    ).astype(str)
    return songs


def kpis(df):
    """Summary numbers for the cards above the charts."""
    if df.empty:
        return {"songs": 0, "cross": 0, "median_days": 0, "entries": 0}
    per_song_country = df.groupby(["spotify_id", "country"]).size()
    countries_per_song = df.groupby("spotify_id")["country"].nunique()
    return {
        "songs": int(df["spotify_id"].nunique()),
        "cross": int((countries_per_song >= 2).sum()),
        "median_days": float(per_song_country.median()),
        "entries": int(len(df)),
    }


def headline(df):
    """Facts for the page subtitle, computed from the data (not hardcoded).

    Returns the countries where a song stays on the chart longest and shortest
    (median days per song), and how many songs chart in 2+ countries.
    """
    days = df.groupby(["country", "spotify_id"]).size().groupby("country").median()
    countries_per_song = df.groupby("spotify_id")["country"].nunique()
    return {
        "longest": (days.idxmax(), float(days.max())),
        "shortest": (days.idxmin(), float(days.min())),
        "cross": int((countries_per_song >= 2).sum()),
        "songs": int(df["spotify_id"].nunique()),
    }