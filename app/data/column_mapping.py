"""Column auto-detection, user-driven mapping, and post-mapping cleaning.

If a spreadsheet's headers don't exactly match the expected schema, the GUI
falls back to a mapping dialog built from `suggest_mapping`. Once a full
mapping is confirmed, `apply_mapping` + `validate_and_clean` turn the raw
sheet into a clean, analysis-ready DataFrame - never raising for row-level
issues, only collecting warnings for the caller to show/log.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.logging_setup import get_logger
from app.schema import DRAFT_RANK_MAX, DRAFT_RANK_MIN, POSITIONS, REQUIRED_FIELD_NAMES, REQUIRED_FIELDS


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(name).strip().lower()).strip()


def suggest_mapping(columns: list[str]) -> dict[str, str | None]:
    """Best-guess mapping of {schema_field_name: source_column_name | None}."""
    normalized_columns = {_normalize(c): c for c in columns}
    mapping: dict[str, str | None] = {}

    for schema_field in REQUIRED_FIELDS:
        match: str | None = None

        # 1. exact normalized match against the field name or any alias
        candidates = {schema_field.name, *schema_field.aliases}
        normalized_candidates = {_normalize(c) for c in candidates}
        for norm_col, original_col in normalized_columns.items():
            if norm_col in normalized_candidates:
                match = original_col
                break

        # 2. fuzzy match fallback
        if match is None:
            close = difflib.get_close_matches(
                _normalize(schema_field.name),
                list(normalized_columns.keys()),
                n=1,
                cutoff=0.72,
            )
            if close:
                match = normalized_columns[close[0]]

        mapping[schema_field.name] = match

    return mapping


def is_mapping_complete(mapping: dict[str, str | None]) -> bool:
    return all(mapping.get(name) for name in REQUIRED_FIELD_NAMES)


def missing_fields(mapping: dict[str, str | None]) -> list[str]:
    return [name for name in REQUIRED_FIELD_NAMES if not mapping.get(name)]


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Return a new DataFrame with only the required columns, canonically named."""
    rename = {source_col: field_name for field_name, source_col in mapping.items()}
    subset_cols = list(mapping.values())
    result = df[subset_cols].rename(columns=rename)
    return result[REQUIRED_FIELD_NAMES].copy()


@dataclass
class CleaningReport:
    warnings: list[str] = field(default_factory=list)
    rows_in: int = 0
    rows_out: int = 0


def validate_and_clean(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Coerce dtypes and drop/flag bad rows. Never raises; issues become warnings."""
    logger = get_logger()
    report = CleaningReport(rows_in=len(df))
    working = df.copy()

    working["player_name"] = working["player_name"].astype(str).str.strip()
    missing_name_mask = (working["player_name"] == "") | working["player_name"].isna()
    if missing_name_mask.any():
        report.warnings.append(
            f"Skipped {int(missing_name_mask.sum())} row(s) missing a player name."
        )
        working = working[~missing_name_mask]

    working["position"] = working["position"].astype(str).str.strip().str.upper()
    invalid_pos_mask = ~working["position"].isin(POSITIONS)
    if invalid_pos_mask.any():
        bad = sorted(set(working.loc[invalid_pos_mask, "position"]))
        report.warnings.append(
            f"Skipped {int(invalid_pos_mask.sum())} row(s) with an unrecognized "
            f"position ({', '.join(bad[:5])})."
        )
        working = working[~invalid_pos_mask]

    numeric_int_fields = ["draft_rank", "games_played", "season_rank"]
    numeric_float_fields = ["total_points", "points_per_game"]

    for col in numeric_int_fields + numeric_float_fields:
        coerced = pd.to_numeric(working[col], errors="coerce")
        bad_mask = coerced.isna() & working[col].notna()
        if bad_mask.any():
            report.warnings.append(
                f"Skipped {int(bad_mask.sum())} row(s) with a non-numeric '{col}'."
            )
        working[col] = coerced

    # derive points_per_game when missing but derivable
    derivable = (
        working["points_per_game"].isna()
        & working["total_points"].notna()
        & working["games_played"].notna()
        & (working["games_played"] > 0)
    )
    working.loc[derivable, "points_per_game"] = (
        working.loc[derivable, "total_points"] / working.loc[derivable, "games_played"]
    )

    required_notna = working[REQUIRED_FIELD_NAMES].notna().all(axis=1)
    if (~required_notna).any():
        report.warnings.append(
            f"Skipped {int((~required_notna).sum())} row(s) with missing required values."
        )
    working = working[required_notna]

    out_of_range = ~working["draft_rank"].between(DRAFT_RANK_MIN, DRAFT_RANK_MAX)
    if out_of_range.any():
        report.warnings.append(
            f"Skipped {int(out_of_range.sum())} row(s) with a draft rank outside "
            f"{DRAFT_RANK_MIN}-{DRAFT_RANK_MAX}."
        )
        working = working[~out_of_range]

    negative_mask = (working["games_played"] < 0) | (working["season_rank"] < 1)
    if negative_mask.any():
        report.warnings.append(
            f"Skipped {int(negative_mask.sum())} row(s) with an invalid (negative) value."
        )
        working = working[~negative_mask]

    dup_mask = working.duplicated(subset=["player_name", "position"], keep="first")
    if dup_mask.any():
        report.warnings.append(
            f"Removed {int(dup_mask.sum())} duplicate player entry/entries "
            "(kept the first occurrence)."
        )
        working = working[~dup_mask]

    for col in numeric_int_fields:
        working[col] = working[col].astype(np.int64)
    for col in numeric_float_fields:
        working[col] = working[col].astype(np.float64)

    working = working.reset_index(drop=True)
    report.rows_out = len(working)

    logger.info(
        "Cleaning complete: %d -> %d rows. Warnings: %s",
        report.rows_in, report.rows_out, report.warnings,
    )
    return working, report
