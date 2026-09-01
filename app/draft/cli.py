"""Console entry point for the draft assistant:
load league settings -> scrape/estimate projections -> compute VOR/tiers ->
print a console summary -> write the import-ready draft board file.

Run via the repo-root script: `python draft_assistant.py [options]`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from app.draft.exporter import export_draft_board
from app.draft.projections import estimate_points_from_rank
from app.draft.scraper import DEFAULT_SOURCE_URL, scrape_projections
from app.draft.settings import LeagueSettings, load_league_settings
from app.draft.vor import compute_vor
from app.logging_setup import get_logger

TOP_N_PER_POSITION = 5


def print_console_summary(board: pd.DataFrame, league: LeagueSettings) -> None:
    format_label = f"{league.team_count}-team {league.scoring}"
    if league.superflex:
        format_label += " Superflex"
    print(f"\nTop picks by position - {format_label} draft board")
    print("=" * 60)

    for position, group in board.groupby("position"):
        top = group.sort_values("vor", ascending=False).head(TOP_N_PER_POSITION)
        print(f"\n{position}")
        for _, row in top.iterrows():
            print(
                f"  #{int(row['overall_vor_rank']):>3}  {row['player_name']:<24} "
                f"VOR {row['vor']:6.1f}  Tier {int(row['tier'])}  "
                f"Round {int(row['recommended_round'])}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NFL Superflex draft assistant")
    parser.add_argument(
        "--config", type=Path, default=None, help="League settings YAML/JSON file (default: bundled)"
    )
    parser.add_argument(
        "--source-url", default=DEFAULT_SOURCE_URL, help="Rankings page to scrape"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("draft_board.csv"), help="Output .csv or .json file"
    )
    parser.add_argument(
        "--offline", action="store_true", help="Skip scraping; use the bundled sample pool"
    )
    return parser


def run(argv: list[str] | None = None) -> Path:
    args = build_parser().parse_args(argv)
    logger = get_logger()

    league = load_league_settings(args.config)
    logger.info(
        "League: %d teams, %s, superflex=%s", league.team_count, league.scoring, league.superflex
    )

    if args.offline:
        from app.draft.sample_projections import build_sample_projections

        projections = build_sample_projections()
    else:
        projections = scrape_projections(args.source_url)

    projections = estimate_points_from_rank(projections)
    board = compute_vor(projections, league)

    print_console_summary(board, league)
    destination = export_draft_board(board, args.output)
    print(f"\nDraft board written to {destination}")
    return destination


if __name__ == "__main__":
    run()
