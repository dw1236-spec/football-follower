from pathlib import Path

import pandas as pd
import pytest

from app.data import ingestion


def test_load_csv(tmp_path: Path, sample_df: pd.DataFrame):
    path = tmp_path / "data.csv"
    sample_df.to_csv(path, index=False)
    loaded = ingestion.load_dataframe(str(path))
    assert list(loaded.columns) == list(sample_df.columns)
    assert len(loaded) == len(sample_df)


def test_load_xlsx(tmp_path: Path, sample_df: pd.DataFrame):
    path = tmp_path / "data.xlsx"
    sample_df.to_excel(path, index=False)
    loaded = ingestion.load_dataframe(str(path))
    assert len(loaded) == len(sample_df)


def test_unsupported_extension_raises_friendly_error(tmp_path: Path):
    path = tmp_path / "data.txt"
    path.write_text("hello")
    with pytest.raises(ingestion.UnsupportedFileFormatError):
        ingestion.load_dataframe(str(path))


def test_missing_file_raises_friendly_error(tmp_path: Path):
    with pytest.raises(ingestion.FileReadError):
        ingestion.load_dataframe(str(tmp_path / "does_not_exist.csv"))


def test_empty_csv_raises_friendly_error(tmp_path: Path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    with pytest.raises(ingestion.EmptyFileError):
        ingestion.load_dataframe(str(path))


def test_friendly_message_never_leaks_traceback():
    exc = ValueError("some internal pandas detail")
    message = ingestion.friendly_message(exc)
    assert "Traceback" not in message
    assert "ValueError" not in message
