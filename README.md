# NFL Fantasy Draft Analyzer

A desktop app that analyzes how well fantasy football draft position (ADP)
predicted actual season performance. Import a spreadsheet, click **Run
Analysis**, and get correlation stats, bust/value rates, charts, and
plain-language draft strategy recommendations - no terminal or config files
required to use it.

## Requirements

- Python 3.11
- Windows 10+, macOS 12+, or Ubuntu 20.04+
- A screen resolution of at least 1280x720 (layout scales up to 4K)

## Running from source

Windows: double-click `run_windows.bat` (creates a venv, installs
dependencies, launches the app - first run takes a minute or two).
macOS/Linux: run `./run_mac_linux.sh`.

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Using the app

1. **Import** - drag a `.csv`, `.xlsx`, or `.xls` file onto the left panel,
   or click **Browse Files**. Don't have data handy? Click **Download Sample
   Template** for a ready-to-fill example.
2. If your spreadsheet's column names don't match the expected schema, a
   mapping dialog lets you match your columns to the required fields - no
   need to rename anything in your file.
3. Pick your **scoring system** (PPR / Half-PPR / Standard) and **league
   format** (Standard / Superflex) - both are remembered the next time you
   open the app. Superflex adds two pooled rows to your results: **FLEX**
   (RB/WR/TE) and **SUPERFLEX** (QB/RB/WR/TE) - the actual pools of players
   that compete for a single Flex or Superflex roster slot, so you can judge
   a player against the whole pool he's competing with for that slot, not
   just against his own position.
4. In the center panel, check/uncheck **positions** to include, then click
   **Run Analysis** (or press Enter while it's focused).
5. Results appear on the right in three tabs:
   - **Summary** - a color-coded table of correlation, MAE, bust rate, and
     value rate per position, plus written recommendations.
   - **Charts** - scatter plots, a correlation heatmap, and a bust/value bar
     chart. Double-click any chart to expand it full-screen.
   - **Export** - one-click buttons to save the summary as CSV, all charts
     as a `.zip` of PNGs, or a full Markdown report.

Your last file, scoring system, position filters, and export folder are
remembered automatically (stored in `~/.nfl_draft_analyzer/config.json`).
Session activity and any skipped/invalid rows are logged to
`~/.nfl_draft_analyzer/logs/` for troubleshooting - the app itself never
shows a raw error or traceback.

## Expected data schema

| Column | Type | Description |
|---|---|---|
| `player_name` | text | Full name |
| `position` | text | QB, RB, WR, TE, K, or DEF |
| `draft_rank` | integer (1-300) | ADP or draft pick number |
| `games_played` | integer | Games played that season |
| `total_points` | number | Total fantasy points under your scoring system |
| `points_per_game` | number | Points per game (auto-derived if left blank) |
| `season_rank` | integer | Final end-of-season rank |

Column names don't need to match exactly - the app auto-detects common
variants (e.g. `ADP`, `Pos`, `FPTS`) and falls back to a mapping dialog for
anything it can't guess.

## How bust/value rate is calculated

For each position, a regression fits "expected fantasy points" as a function
of draft slot. A player is a **bust** if they scored more than 20% below
that expectation, and a **value pick** if they beat it by 20% or more.

## Superflex leagues

Superflex ADP already reflects the format (QBs get drafted far earlier
since two can start at once), so the correlation/bust/value math above needs
no changes to work with Superflex data - just import your Superflex ADP as
usual. Switching **League Format** to Superflex only adds the pooled FLEX
and SUPERFLEX rows described above; each position keeps its own
draft-slot-vs-points regression (QB and RB point totals aren't on the same
scale, so pooling the regression itself would be meaningless) and the pooled
rows simply aggregate correlation/MAE/bust/value across the players who
actually share that roster slot.

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest
```

On a Linux machine without a display (e.g. CI, SSH), run headless:

```bash
QT_QPA_PLATFORM=offscreen pytest
```

## Draft assistant (VOR-based, Superflex-ready)

A separate CLI tool, `draft_assistant.py`, builds a live draft board using
Value Over Replacement (VOR) rather than raw rankings or ADP:

```bash
python draft_assistant.py                        # scrape + VOR + draft_board.csv
python draft_assistant.py --offline               # no network - bundled sample pool
python draft_assistant.py --config my_league.yaml --output board.json
```

- **League settings** come from a YAML/JSON config (`config/league_settings.yaml`
  by default - 10 teams, Half-PPR, Superflex). Edit it or pass `--config`.
- **Replacement baselines are dynamic**, derived from team count and roster
  construction (`app.draft.vor.compute_replacement_ranks`) - including a
  documented allocation of FLEX and SUPERFLEX slots across their eligible
  positions, so a Superflex league correctly pushes the QB replacement level
  (and therefore top-QB VOR) far deeper than a 1-QB league.
- **Scraping** targets FantasyPros' rankings (`app/draft/scraper.py`), with
  retries/backoff on transient failures, a fast-fail on permanent HTTP
  errors, and an automatic fallback to a bundled offline sample pool if the
  network or page-parsing fails for any reason - the pipeline never hard
  crashes because a website is down or changed layout. Raw HTML and parsed
  output are cached separately under `~/.nfl_draft_analyzer/draft_cache/`
  for debugging.
- **Output** is an import-ready CSV/JSON (`player_name, position, team,
  projected_points, vor, tier, adp, recommended_round`) plus a console
  summary of the top players per position.
- **Dry-run auditing**: `app.draft.recommend.recommend_pick(..., dry_run=True)`
  logs the VOR score and replacement baseline behind every candidate it
  considered for a pick, so a recommendation can always be verified.

Run `mypy app/draft` to type-check this package (see `mypy.ini`).

## Building a standalone app

PyInstaller cannot cross-compile, so build on the OS you're targeting:

| OS | Script | Output |
|---|---|---|
| Windows 10+ | `packaging\build_windows.bat` | `dist\NFLDraftAnalyzer\NFLDraftAnalyzer.exe` |
| macOS 12+ | `packaging/build_macos.sh` | `dist/NFLDraftAnalyzer.app` |
| Ubuntu 20.04+ | `packaging/build_linux.sh` | `dist/NFLDraftAnalyzer/NFLDraftAnalyzer` |

The macOS build is unsigned; sign and notarize it with your Apple Developer
account before distributing it to other Macs.

## Project layout

```
app/
  schema.py            required column schema + constants
  config.py            local JSON config persistence
  state.py             AppState dataclass + Observer-pattern StateStore
  logging_setup.py      session log file
  data/
    ingestion.py        file reading, friendly errors
    column_mapping.py   auto-detect/apply/validate/clean columns
    sample_template.py  bundled sample_data_template.xlsx generator
  analysis/
    metrics.py           correlation, MAE, bust/value rate (pandas + scikit-learn)
    recommendations.py   plain-language recommendation text
  visualization/
    charts.py            matplotlib/seaborn figure builders
  export/
    exporters.py         CSV / PNG-zip / Markdown export
  gui/                    PyQt6 widgets (Import/Control/Results panels, dialogs)
  draft/                  VOR draft assistant (separate CLI tool, see above)
    schema.py             projections/draft-board column schema
    settings.py           LeagueSettings/RosterSlots + YAML/JSON config loader
    vor.py                replacement-rank + VOR + tiering engine
    projections.py        rank-based points fallback when a source lacks real FPTS
    scraper.py            FantasyPros fetch/parse, retries, cache, offline fallback
    sample_projections.py bundled offline ADP pool (scrape fallback + demos)
    recommend.py          live pick recommendation + dry-run VOR audit logging
    exporter.py           CSV/JSON import-ready draft board export
    cli.py                console entry point (see draft_assistant.py)
main.py                   desktop app entry point
draft_assistant.py        draft assistant CLI entry point
config/
  league_settings.yaml    default 10-team Half-PPR Superflex league settings
tests/                    pytest + pytest-qt suite
packaging/                PyInstaller spec + per-OS build scripts
run_windows.bat           one-click Windows launcher
run_mac_linux.sh          one-click macOS/Linux launcher
```
