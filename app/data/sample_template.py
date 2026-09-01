"""Generates the bundled sample_data_template.xlsx used by the Import Panel's
"Download Sample Template" button, so users know exactly what format to prepare.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.schema import REQUIRED_FIELD_NAMES

ASSET_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "sample_data_template.xlsx"

_SAMPLE_ROWS = [
    ("Patrick Mahomes", "QB", 12, 16, 372.4, 23.3, 3),
    ("Josh Allen", "QB", 15, 17, 389.1, 22.9, 1),
    ("Jalen Hurts", "QB", 22, 15, 340.2, 22.7, 5),
    ("Christian McCaffrey", "RB", 1, 16, 355.8, 22.2, 2),
    ("Bijan Robinson", "RB", 8, 17, 280.5, 16.5, 12),
    ("Jonathan Taylor", "RB", 18, 11, 150.2, 13.7, 34),
    ("Saquon Barkley", "RB", 25, 16, 298.7, 18.7, 7),
    ("Justin Jefferson", "WR", 4, 10, 210.4, 21.0, 22),
    ("Tyreek Hill", "WR", 6, 17, 330.9, 19.5, 3),
    ("Ja'Marr Chase", "WR", 10, 16, 305.6, 19.1, 4),
    ("CeeDee Lamb", "WR", 14, 17, 340.0, 20.0, 1),
    ("Puka Nacua", "WR", 60, 17, 289.3, 17.0, 6),
    ("Travis Kelce", "TE", 20, 15, 210.8, 14.1, 3),
    ("Sam LaPorta", "TE", 90, 17, 205.4, 12.1, 1),
    ("Mark Andrews", "TE", 35, 9, 90.5, 10.1, 18),
    ("Justin Tucker", "K", 140, 16, 148.0, 9.3, 5),
    ("Harrison Butker", "K", 155, 16, 152.5, 9.5, 3),
    ("San Francisco 49ers", "DEF", 100, 17, 175.0, 10.3, 4),
    ("Dallas Cowboys", "DEF", 110, 17, 160.2, 9.4, 8),
    ("Buffalo Bills", "DEF", 120, 17, 168.5, 9.9, 6),
]


def build_sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame(_SAMPLE_ROWS, columns=REQUIRED_FIELD_NAMES)


def write_sample_template(destination: str | Path) -> Path:
    """Write the sample template workbook to `destination` and return its path."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    df = build_sample_dataframe()
    with pd.ExcelWriter(destination, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sample Data")
    return destination


def ensure_bundled_template() -> Path:
    """Ensure the bundled asset copy exists (used at build/dev time)."""
    if not ASSET_PATH.exists():
        write_sample_template(ASSET_PATH)
    return ASSET_PATH


if __name__ == "__main__":
    path = write_sample_template(ASSET_PATH)
    print(f"Wrote sample template to {path}")
