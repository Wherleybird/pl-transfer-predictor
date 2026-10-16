<div align="center">

# EPL's Value Gap

**What is a Premier League player worth, and where does the transfer market disagree with a simple, explainable model?**

[Live app](TODO-add-your-streamlit-link-after-deploying) · [How it works](#how-the-model-was-built) · [Run it yourself](#run-it-yourself) · [Every file explained](#every-file-explained)

![Python](https://img.shields.io/badge/Python-3.10+-17803A?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-app-17803A?logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-linear%20regression-17803A?logo=scikitlearn&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-0C1F3A)

![Home screen of EPL's Value Gap](docs/home.png)

</div>

---

## The idea

Transfer values are opinions: a crowd's estimate of what a player is worth. This project asks a question every fan has argued about: **if you knew only what a player did on the pitch, his age, position and club, what would you expect him to be worth?**

I trained a linear regression on five Premier League seasons (2021/22 to 2025/26) and compared its estimate with Transfermarkt's market value. The difference is the **gap**:

- **Market pays more** means the market values the player above what stats, age and club predict.
- **Market pays less** means the market values him below that.

The gap is not a verdict on any player. It is a way to see where the market is paying for something the model cannot see (potential, hype, contract length, injuries) and where it may have missed something.

## What the app does

| Page | What you can do |
|---|---|
| **Home** | See the season's biggest disagreement on a scoreboard, the biggest gaps as fixtures, a club league table, and how value changes with age |
| **Players** | Search any player and see market versus model across seasons, plus a breakdown of what drives the estimate (age, club, goals and assists, playing time...) |
| **Explorer** | Filter by season, position, club, age and value; rank by € or % gap; see the full table |
| **Estimator** | Enter a stat line (or start from a real player-season) and get an estimated value with a likely range |
| **How it works** | The full modelling story, the tests, the residuals and the limitations |
| **About me** | Who built this |

![Explorer](docs/explorer.png)

## Results

All scores are on **players the model had never seen** (cross-validation grouped by player, so a player's seasons never sit on both sides of the split).

| Model | What I added | CV R² | Test R² | Test MAE |
|---|---|---|---|---|
| A | Goals, assists, position | 0.183 | 0.156 | €18.2M |
| B | Age, minutes, per-90 rates | 0.430 | 0.394 | €16.1M |
| C | Age curve, season, defensive and goalkeeper stats | 0.589 | 0.585 | €14.0M |
| D | Club | 0.728 | 0.742 | €10.7M |
| E | Grouped clubs and age bands (**dropped**, it got worse) | 0.691 | 0.689 | €11.1M |
| F1 | D with small clubs pooled into "Other" | 0.730 | 0.734 | €10.8M |
| **F2** | **F1 plus age hinges (over 29, under 21)** | **0.739** | **0.747** | **€10.4M** |

R² is measured on log market value. MAE is in euros.

![How the model improved](docs/model_journey.png)

What the model learned:

- **Club is the single biggest jump** (+0.14 R²). Playing for Manchester City, Liverpool or Arsenal is worth roughly 2.7 to 3.3 times the value of the baseline club, all else equal. Part of that is real (better players, bigger platform), part is brand.
- **Values inflate**: 2025/26 is worth about 39% more than 2021/22 for the same player.
- **Age matters beyond a smooth curve**: after 29 value falls faster than a quadratic suggests, which is why the hinge features help.
- **Simple beat complex here**: a linear model (0.739) beat a random forest (0.627) and gradient boosting (0.694) on this small dataset, and it is explainable, so it stayed.

## How the model was built

1. **Collect.** Season stats for every Premier League player come from the public Fantasy Premier League API (current table plus each player's `history_past`).
2. **Match.** Players are matched to Transfermarkt by name. 364 matched automatically, 22 found nothing and 5 were ambiguous; I reviewed those by hand and fixed them with a 27-entry manual list. Every one of the 391 players ended up matched, giving **1,073 player-seasons**.
3. **Pick one value per player-season.** Transfermarkt has many valuations per player. I take the latest one from January to June of the season, while the player was at a Premier League club, so the value lines up with the season's stats.
4. **Engineer features.** Goals, assists, clean sheets, saves and bonus points per 90 minutes; minutes played; age, `(age - 25)²`, and hinges for over 29 and under 21; position; season; club (clubs with fewer than 10 rows are pooled as "Other").
5. **Fit a linear regression on log value**, because values are skewed and effects are multiplicative: age or club moves value by a percentage, not a fixed number of euros.
6. **Test honestly.** `GroupKFold` by player keeps one player's seasons together. The gap you see in the app uses out-of-fold predictions, so the model never saw that player when it estimated him.
7. **Export without pickle.** `export_model.py` writes the fitted coefficients to `assets/model.json`. The app evaluates the model itself, which makes the Estimator instant, lets it explain every prediction factor by factor, and avoids version problems from loading a pickled model. It checks that its own arithmetic reproduces scikit-learn exactly.

## Limitations

I would rather say these than have you find them:

- **No potential, hype, contract or injury information.** Teenagers with big futures often look "overvalued"; players with a year left on their contract may look "undervalued".
- **Club is measured at valuation time**, but stats cover the whole season, so a mid-season transfer blurs the link.
- **Survivorship bias.** Only players in the current FPL data are included, so players who left the league are missing.
- **Market values are rounded crowd opinions**, so some of the gap is just noise.
- **Small data.** About 1,000 rows and 5 seasons. Predictions for the very top end are compressed (log space pulls extremes towards the middle).
- **Stats are Fantasy Premier League stats**, which do not capture things like pressing, passing quality or off-ball work.

## Run it yourself

```bash
git clone https://github.com/TODO-your-username/TODO-repo-name.git
cd TODO-repo-name
python -m venv venv
venv\Scripts\activate          # Windows;  macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The repository includes the processed data (`data/predictions.csv`) and the exported model (`assets/model.json`), so the app runs straight away.

To rebuild everything from scratch, run the pipeline in order:

```bash
python TODO_fetch_current_players.py   # 1. current FPL player table
python TODO_fetch_player_history.py    # 2. each player's past seasons -> data/player_history.csv
# 3. download players.csv.gz and player_valuations.csv.gz from the transfermarkt-datasets
#    project into data/ (see Data sources below)
python build_dataset.py                # 4. match players, attach values -> data/merged.csv
python analyze.py                      # 5. fit final model, out-of-fold gaps -> data/predictions.csv
python export_model.py                 # 6. coefficients -> assets/model.json
python fetch_assets.py                 # 7. club badges and player photos -> assets/
streamlit run app.py
```

Optional, for the story and checks: `explore.py`, `compare_models.py`, `check_data.py`, `inspect_values.py`, `review_matches.py`, `review_remaining.py` (see below).

## Every file explained

### The app

| File | Purpose |
|---|---|
| `app.py` | The Streamlit app: page layout, navigation, charts and every page (Home, Players, Explorer, Estimator, How it works, About me). Start it with `streamlit run app.py` |
| `theme.py` | All the visual design: the CSS (pitch banner, scoreboard, fixture rows, league table), the chart theme, club badge and player photo handling, and the HTML builders for each component |
| `logic.py` | The app's brain, with no Streamlit in it: loads and validates `predictions.csv`, splits players into "market pays more" and "less" (the bug fix: a player can only be in one list), computes club tables and age curves, and evaluates the exported model for the Estimator |
| `clubs.py` | Club metadata: short names, 3-letter codes, badge ids and colours, keyed by Transfermarkt club name. Clubs missing from it still get a grey fallback badge |
| `about_me.py` | The text on the About me page. Edit this file to change it |
| `.streamlit/config.toml` | Streamlit theme (colours, font, rounded corners) and hides the developer toolbar |
| `requirements.txt` | Python packages needed to run everything |

### The data pipeline

| File | Purpose |
|---|---|
| `TODO_fetch_current_players.py` | Pulls the current player table from the Fantasy Premier League API |
| `TODO_fetch_player_history.py` | Pulls each player's past seasons (`history_past`) and writes `data/player_history.csv` |
| `build_dataset.py` | Matches FPL players to Transfermarkt by name, applies the manual fixes, picks one value per player-season and writes `data/merged.csv` |
| `features.py` | Shared feature engineering (per-90 rates, age terms, club grouping), so the experiments, the analysis and the export all use identical code |
| `analyze.py` | Fits the final model (F2), produces out-of-fold predictions and gaps, prints the biggest over- and undervalued players and saves `data/predictions.csv` |
| `export_model.py` | Fits the final model on all rows and writes its coefficients and baselines to `assets/model.json` for the app |
| `fetch_assets.py` | Downloads club badges and player photos into `assets/` (skips what it already has) |

### Analysis and checks (optional)

These are how I explored, validated and chose the model. You do not need them to run the app.

| File | Purpose |
|---|---|
| `explore.py` | First look at the data and the exploratory charts in `charts/` |
| `compare_models.py` | Compares the linear model against random forest and gradient boosting |
| `check_data.py` | Sanity checks on the FPL history (shape, players, rows per season) |
| `inspect_values.py` | Inspects the Transfermarkt files (columns, dates, clubs) before merging |
| `review_matches.py` | Prints uncertain and failed name matches for manual review |
| `review_remaining.py` | Lists the matches still unresolved after the first manual pass |
| `model.py` (or `experiments.py` if you renamed it) | The experiment log: models A to F2 with grouped cross-validation, the table in [Results](#results) |

### Data and assets

| Path | What it is |
|---|---|
| `data/player_history.csv` | FPL season-by-season stats for each player (output of the history fetch) |
| `data/players.csv.gz`, `data/player_valuations.csv.gz` | Raw Transfermarkt datasets (CC0) used for matching and values |
| `data/merged.csv` | Stats joined with market values: 1,073 player-seasons |
| `data/predictions.csv` | Merged data plus model estimate, gap in € and %. This is what the app reads |
| `assets/model.json` | The exported model (coefficients, means, residual spread) |
| `assets/logo.svg` | The wordmark. Drawn as vector paths, so it needs no font |
| `assets/badges/`, `assets/players/` | Club badges (named by club code) and player photos (named by FPL element code) |
| `assets/me.jpg` | Photo for the About me page |
| `charts/` | Exploration and analysis charts produced by `explore.py` and `analyze.py` |
| `docs/` | Screenshots used in this README |
| `.gitignore` | Keeps the virtual environment, caches and other local files out of Git |
| `LICENSE` | MIT licence for the code |

## Data sources and credits

- **Player statistics:** the public [Fantasy Premier League API](https://fantasy.premierleague.com/api/bootstrap-static/).
- **Market values:** [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets), released under CC0. The project has paused updates; its valuations run to June 2026.
- **Badges and photos** belong to their owners (the Premier League and its clubs) and are shown for non-commercial, illustrative purposes. This project is independent and not affiliated with or endorsed by the Premier League, any club, Transfermarkt or Fantasy Premier League. If you own an image and want it removed, open an issue and I will take it down.

## How this was built

I built this over several sessions, working through each stage myself: pulling the data, hitting and fixing errors, reviewing every uncertain name match by hand, and deciding which model ideas to keep or drop (the age-band model made things worse, so it went). I used Claude as an AI pair programmer and tutor along the way, including for the interface design, and I can explain any part of the code and every modelling decision here.

## Ideas for next time

- A player comparison page.
- Add potential proxies (youth caps, age relative to league, contract length) to tackle the biggest limitation.
- Predict next season's value, not just explain the current one.
- Add prediction intervals calibrated per position.

---

<div align="center">Built by <b>Cooper Wherley</b> · <a href="TODO-linkedin-url">LinkedIn</a> · <a href="TODO-github-url">GitHub</a></div>
