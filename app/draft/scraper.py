"""Scrapes current-season rankings from FantasyPros.

Network I/O (`fetch_html`) is kept separate from parsing
(`parse_fantasypros_rankings`) so parsing can be unit-tested against a fixed
HTML fixture with no network access, and so a change in FantasyPros' page
layout only ever requires touching the parser, never the
fetch/retry/caching plumbing.

Reliability: `fetch_html` retries transient failures (timeouts, connection
errors, 429/5xx) with exponential backoff and fails fast on a non-retryable
HTTP error (e.g. 404). `scrape_projections` falls back to the bundled
offline sample pool (app.draft.sample_projections) if every retry fails or
the page can't be parsed, so the rest of the pipeline (VOR, tiers, export)
always has *something* to run on - never a hard crash because a website was
briefly down or changed its layout. Every attempt is logged via
app.logging_setup, and both the raw HTML and the parsed output are cached
to disk (separately) for debugging.

Caveat: FantasyPros' exact page structure changes over time and can only be
verified against the live site (this parser targets FantasyPros' long-
documented `ecrData` embedded-JSON convention). If `parse_fantasypros_rankings`
starts raising ParseError against real traffic, the site has likely changed
its markup and this function is the only place that needs updating.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from app.logging_setup import get_logger
from app.schema import POSITIONS

DEFAULT_SOURCE_URL = "https://www.fantasypros.com/nfl/rankings/half-ppr-superflex-cheatsheets.php"
USER_AGENT = (
    "Mozilla/5.0 (compatible; NFLDraftAnalyzer/1.0; "
    "+https://github.com/dw1236-spec/football-follower)"
)

CACHE_DIR = Path.home() / ".nfl_draft_analyzer" / "draft_cache"
RAW_CACHE_DIR = CACHE_DIR / "raw"
PARSED_CACHE_DIR = CACHE_DIR / "parsed"

_ECR_DATA_PATTERN = re.compile(r"var\s+ecrData\s*=\s*(\{.*?\});", re.DOTALL)
_TRAILING_RANK_DIGITS = re.compile(r"\d+$")

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class ScrapeError(Exception):
    """Base class for scraper failures."""


class FetchError(ScrapeError):
    """Raised when the page could not be retrieved after all retries."""


class ParseError(ScrapeError):
    """Raised when a fetched page didn't match any known parsing strategy."""


def fetch_html(
    url: str = DEFAULT_SOURCE_URL,
    timeout: float = 10.0,
    max_retries: int = 3,
    backoff_seconds: float = 1.5,
) -> str:
    """Fetch a page's HTML, retrying transient failures with exponential
    backoff. Fails fast (no retry) on a non-retryable HTTP status like 404.
    Raises FetchError if every attempt is exhausted.
    """
    logger = get_logger()
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            return response.text
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in RETRYABLE_STATUS_CODES:
                raise FetchError(f"Non-retryable HTTP {status} fetching '{url}'.") from exc
            last_error = exc
            logger.warning("Fetch attempt %d/%d for %s got HTTP %s.", attempt, max_retries, url, status)
        except requests.RequestException as exc:
            last_error = exc
            logger.warning("Fetch attempt %d/%d for %s failed: %s", attempt, max_retries, url, exc)

        if attempt < max_retries:
            time.sleep(backoff_seconds * (2 ** (attempt - 1)))

    raise FetchError(f"Could not fetch '{url}' after {max_retries} attempts.") from last_error


def _normalize_position(raw_position: Any) -> str:
    # FantasyPros encodes flex-eligible slot labels like "QB1", "RB12" -
    # strip any trailing rank digits down to the bare position code.
    return _TRAILING_RANK_DIGITS.sub("", str(raw_position).strip().upper())


def parse_fantasypros_rankings(html: str) -> pd.DataFrame:
    """Parse FantasyPros' embedded `ecrData` ranking payload into a
    {player_name, position, team, adp} DataFrame.

    FantasyPros' free ranking pages don't publish raw fantasy-point
    projections directly - only a consensus expert rank (ECR) and each
    expert's average rank, which is used here as an ADP proxy. Real point
    projections are filled in separately by
    app.draft.projections.estimate_points_from_rank.
    """
    logger = get_logger()
    match = _ECR_DATA_PATTERN.search(html)
    if not match:
        raise ParseError(
            "Could not find the expected 'ecrData' ranking payload in the page. "
            "FantasyPros may have changed its page layout since this parser was written."
        )

    try:
        payload: dict[str, Any] = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ParseError(f"Ranking payload was not valid JSON: {exc}") from exc

    players = payload.get("players")
    if not isinstance(players, list) or not players:
        raise ParseError("Ranking payload had no usable 'players' list.")

    rows: list[dict[str, Any]] = []
    skipped = 0
    for entry in players:
        try:
            name = str(entry["player_name"]).strip()
            position = _normalize_position(entry["player_position_id"])
            team = str(entry.get("player_team_id") or "FA").strip().upper()
            adp = float(entry.get("rank_ave", entry["rank_ecr"]))
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue

        if not name or position not in POSITIONS:
            skipped += 1
            continue

        rows.append({"player_name": name, "position": position, "team": team, "adp": adp})

    if skipped:
        logger.warning("Skipped %d player row(s) with missing/invalid fields while parsing.", skipped)
    if not rows:
        raise ParseError("No usable player rows survived parsing.")

    return pd.DataFrame(rows)


def _write_cache(raw_html: str, parsed: pd.DataFrame) -> None:
    logger = get_logger()
    try:
        RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        PARSED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        (RAW_CACHE_DIR / f"{stamp}.html").write_text(raw_html, encoding="utf-8")
        parsed.to_json(PARSED_CACHE_DIR / f"{stamp}.json", orient="records", indent=2)
    except OSError as exc:
        logger.warning("Could not write scrape cache: %s", exc)


def scrape_projections(url: str = DEFAULT_SOURCE_URL, use_cache: bool = True) -> pd.DataFrame:
    """Scrape and parse current rankings, falling back to the bundled
    offline sample pool if the network call or parse fails for any reason.
    """
    logger = get_logger()
    try:
        html = fetch_html(url)
        parsed = parse_fantasypros_rankings(html)
        if use_cache:
            _write_cache(html, parsed)
        logger.info("Scraped %d players from %s", len(parsed), url)
        return parsed
    except ScrapeError as exc:
        logger.error("Scrape failed, falling back to bundled sample projections: %s", exc)
        from app.draft.sample_projections import build_sample_projections

        return build_sample_projections()
