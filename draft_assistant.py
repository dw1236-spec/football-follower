"""Entry point for the Superflex draft assistant CLI.

Scrapes current rankings, computes Value Over Replacement (VOR) for the
configured league, prints a console summary, and writes an import-ready
draft board file. Run `python draft_assistant.py --help` for options.
"""
from __future__ import annotations

from app.draft.cli import run

if __name__ == "__main__":
    run()
