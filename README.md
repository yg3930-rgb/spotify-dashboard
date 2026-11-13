# Spotify Top Songs: Trends and Audio Features Across Countries

Interactive dashboard for Mini-Project 2 (Information Visualization, NYU Tandon).
It compares the daily Spotify top 50 charts of six countries (US, DE, BR, MX, JP, KR)
from 2025-03-14 to 2025-06-11.

## Research questions
1. How do music popularity trends differ across countries over time?
2. Which songs perform consistently well across multiple countries?
3. How are audio features such as danceability and energy related to song popularity?

## Setup
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:8050 in a browser.

## Interactions
| View | Interaction | Effect on other views |
|---|---|---|
| Line chart | Drag horizontally to select dates | Bar, scatter and KPIs use only those dates; range is shaded on the line chart |
| Bar chart | Click a bar | Adds/removes the song: line chart shows that song's popularity, scatter and bar highlight it |
| Scatter plot | Lasso or box-select | Selected songs become the song selection |
| Sidebar | Countries, dates, songs | Same shared state as the chart interactions |
| Sidebar | Reset all | Clears every selection |

## Project structure
```
app.py           layout and callbacks (interaction logic)
data.py          loading and aggregation (pure pandas, testable)
figures.py       Plotly figure builders, one per view
config.py        palette, features, rank bands, shared constants
preprocess.py    builds data/spotify_filtered.csv from the raw Kaggle file
assets/style.css layout and styling
data/            filtered dataset (24,600 rows)
```

## Data
Source: "Top Spotify Songs in 73 Countries (Daily Updated)" by asaniczka, Kaggle.
To rebuild the filtered file, download the raw CSV and run:
```bash
python preprocess.py --input universal_top_spotify_songs.csv --output data/spotify_filtered.csv
```
Data notes:
- The United Kingdom was excluded because its data is almost entirely missing after April 2025.
- All countries are missing 2025-04-22 to 2025-04-29 in the source; the line chart shows this gap instead of interpolating.
- Spotify reports popularity = 0 for some brand-new releases; these values are treated as missing.

## References
- Colorblind-safe palette: Okabe, M. & Ito, K. (2008), *Color Universal Design*.
- Dash documentation: https://dash.plotly.com
- Development assistance: [describe any tools or AI assistance used, per course policy]
