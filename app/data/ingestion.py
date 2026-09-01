"""File ingestion: reads CSV/XLSX/XLS into a DataFrame with friendly errors.

No exception raised here should ever reach the UI as a raw traceback -
callers should pass caught exceptions through `friendly_message()`.
"""
from __future__ import annotations

import traceback
from pathlib import Path

import pandas as pd

from app.logging_setup import get_logger

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class DataError(Exception):
    """Base class for all recoverable data-ingestion problems."""


class UnsupportedFileFormatError(DataError):
    pass


class EmptyFileError(DataError):
    pass


class FileReadError(DataError):
    pass


def load_dataframe(path: str) -> pd.DataFrame:
    """Read a CSV/XLSX/XLS file into a DataFrame, or raise a DataError subclass."""
    logger = get_logger()
    file_path = Path(path)

    if not file_path.exists():
        raise FileReadError(f"The file '{file_path.name}' could not be found.")

    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileFormatError(
            f"'{ext or 'unknown'}' is not a supported file type. "
            "Please use a .csv, .xlsx, or .xls file."
        )

    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext == ".xls":
            df = pd.read_excel(file_path, engine="xlrd")
        else:
            df = pd.read_excel(file_path, engine="openpyxl")
    except pd.errors.EmptyDataError as exc:
        raise EmptyFileError("This file appears to be empty.") from exc
    except Exception as exc:  # noqa: BLE001 - deliberately broad, translated for the UI
        logger.error("Failed to read file '%s': %s", path, traceback.format_exc())
        raise FileReadError(
            f"We couldn't read '{file_path.name}'. It may be corrupted, "
            "password-protected, or open in another program."
        ) from exc

    if df.shape[1] == 0:
        raise EmptyFileError("This file has no columns to read.")
    if df.shape[0] == 0:
        raise EmptyFileError("This file has headers but no data rows.")

    df.columns = [str(c).strip() for c in df.columns]
    logger.info("Loaded file '%s' with shape %s", path, df.shape)
    return df


def friendly_message(exc: Exception) -> str:
    """Translate any exception into a short, non-technical message for a banner."""
    if isinstance(exc, DataError):
        return str(exc)
    get_logger().error("Unexpected error: %s", traceback.format_exc())
    return (
        "Something went wrong while processing your file. "
        "The details have been saved to the session log."
    )
