import json

import pandas as pd
import pytest
import requests

from app.draft import scraper


def _ecr_html(players: list[dict]) -> str:
    payload = json.dumps({"players": players})
    return f"<html><body><script>var ecrData = {payload};</script></body></html>"


class _FakeResponse:
    def __init__(self, status_code: int = 200, text: str = ""):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.HTTPError(f"{self.status_code} error")
            error.response = self  # type: ignore[assignment]
            raise error


# -- parse_fantasypros_rankings -------------------------------------------------


def test_parse_fantasypros_rankings_happy_path():
    html = _ecr_html(
        [
            {"player_name": "Josh Allen", "player_position_id": "QB1", "player_team_id": "BUF", "rank_ecr": 3, "rank_ave": 3.2},
            {"player_name": "Christian McCaffrey", "player_position_id": "RB1", "player_team_id": "SF", "rank_ecr": 1, "rank_ave": 1.1},
        ]
    )
    df = scraper.parse_fantasypros_rankings(html)
    assert list(df.columns) == ["player_name", "position", "team", "adp"]
    assert set(df["position"]) == {"QB", "RB"}
    assert df.loc[df["player_name"] == "Josh Allen", "adp"].iloc[0] == pytest.approx(3.2)


def test_parse_fantasypros_rankings_skips_malformed_rows_without_crashing():
    html = _ecr_html(
        [
            {"player_name": "Good Player", "player_position_id": "WR1", "player_team_id": "DAL", "rank_ecr": 10, "rank_ave": 10.5},
            {"player_name": "Bad Position", "player_position_id": "LB1", "player_team_id": "DAL", "rank_ecr": 200, "rank_ave": 200.0},
            {"player_position_id": "RB1", "player_team_id": "SF", "rank_ecr": 5, "rank_ave": 5.0},  # missing name
            {"player_name": "No Rank Field", "player_position_id": "TE1", "player_team_id": "KC"},  # missing rank_ecr/rank_ave
        ]
    )
    df = scraper.parse_fantasypros_rankings(html)
    assert list(df["player_name"]) == ["Good Player"]


def test_parse_fantasypros_rankings_missing_payload_raises_parse_error():
    with pytest.raises(scraper.ParseError):
        scraper.parse_fantasypros_rankings("<html><body>nothing here</body></html>")


def test_parse_fantasypros_rankings_invalid_json_raises_parse_error():
    html = "<script>var ecrData = {not valid json};</script>"
    with pytest.raises(scraper.ParseError):
        scraper.parse_fantasypros_rankings(html)


def test_parse_fantasypros_rankings_empty_players_list_raises_parse_error():
    html = _ecr_html([])
    with pytest.raises(scraper.ParseError):
        scraper.parse_fantasypros_rankings(html)


def test_parse_fantasypros_rankings_all_rows_malformed_raises_parse_error():
    html = _ecr_html([{"player_position_id": "RB1"}])  # missing everything else
    with pytest.raises(scraper.ParseError):
        scraper.parse_fantasypros_rankings(html)


# -- fetch_html -------------------------------------------------------------------


def test_fetch_html_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda *_: None)
    attempts = {"n": 0}

    def fake_get(url, timeout, headers):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise requests.ConnectionError("boom")
        return _FakeResponse(200, "<html>ok</html>")

    monkeypatch.setattr(requests, "get", fake_get)
    html = scraper.fetch_html("https://example.com", max_retries=3)
    assert html == "<html>ok</html>"
    assert attempts["n"] == 3


def test_fetch_html_raises_after_max_retries(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda *_: None)

    def fake_get(url, timeout, headers):
        raise requests.Timeout("too slow")

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(scraper.FetchError):
        scraper.fetch_html("https://example.com", max_retries=3)


def test_fetch_html_retries_on_retryable_status(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda *_: None)
    attempts = {"n": 0}

    def fake_get(url, timeout, headers):
        attempts["n"] += 1
        if attempts["n"] < 2:
            return _FakeResponse(503, "")
        return _FakeResponse(200, "<html>ok</html>")

    monkeypatch.setattr(requests, "get", fake_get)
    html = scraper.fetch_html("https://example.com", max_retries=3)
    assert html == "<html>ok</html>"
    assert attempts["n"] == 2


def test_fetch_html_fails_fast_on_non_retryable_status(monkeypatch):
    monkeypatch.setattr(scraper.time, "sleep", lambda *_: None)
    attempts = {"n": 0}

    def fake_get(url, timeout, headers):
        attempts["n"] += 1
        return _FakeResponse(404, "")

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(scraper.FetchError):
        scraper.fetch_html("https://example.com", max_retries=3)
    assert attempts["n"] == 1  # no wasted retries on a permanent error


# -- scrape_projections (fallback behavior) --------------------------------------


def test_scrape_projections_falls_back_to_sample_pool_on_total_failure(monkeypatch):
    def always_fails(*args, **kwargs):
        raise scraper.FetchError("network is down")

    monkeypatch.setattr(scraper, "fetch_html", always_fails)

    from app.draft.sample_projections import build_sample_projections

    result = scraper.scrape_projections(use_cache=False)
    pd.testing.assert_frame_equal(
        result.reset_index(drop=True), build_sample_projections().reset_index(drop=True)
    )


def test_scrape_projections_falls_back_on_parse_failure(monkeypatch):
    monkeypatch.setattr(scraper, "fetch_html", lambda *_a, **_k: "<html>no ecr data here</html>")
    result = scraper.scrape_projections(use_cache=False)
    assert not result.empty
    assert "player_name" in result.columns


def test_scrape_projections_writes_cache_on_success(monkeypatch, tmp_path):
    monkeypatch.setattr(scraper, "RAW_CACHE_DIR", tmp_path / "raw")
    monkeypatch.setattr(scraper, "PARSED_CACHE_DIR", tmp_path / "parsed")
    html = _ecr_html(
        [{"player_name": "Test Player", "player_position_id": "WR1", "player_team_id": "DAL", "rank_ecr": 1, "rank_ave": 1.0}]
    )
    monkeypatch.setattr(scraper, "fetch_html", lambda *_a, **_k: html)

    result = scraper.scrape_projections(use_cache=True)
    assert list(result["player_name"]) == ["Test Player"]
    assert list((tmp_path / "raw").glob("*.html"))
    assert list((tmp_path / "parsed").glob("*.json"))
