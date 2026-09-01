"""Application state container using an Observer/callback pattern.

A single AppState dataclass holds everything the GUI needs to render.
StateStore is the mutable owner: components subscribe to be notified
whenever state changes, rather than polling or holding their own copies.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Optional

import pandas as pd

from app.logging_setup import get_logger

Listener = Callable[["AppState"], None]


@dataclass
class AppState:
    loaded_file_path: Optional[str] = None
    raw_dataframe: Optional[pd.DataFrame] = None
    mapped_columns: dict[str, str] = field(default_factory=dict)
    scoring_system: str = "PPR"
    selected_positions: set[str] = field(
        default_factory=lambda: {"QB", "RB", "WR", "TE", "K", "DEF"}
    )
    analysis_results: Optional[dict[str, Any]] = None
    export_directory: Optional[str] = None
    is_analyzing: bool = False
    status_message: str = ""


class StateStore:
    """Owns the AppState and notifies subscribers on every transition."""

    def __init__(self) -> None:
        self._state = AppState()
        self._listeners: list[Listener] = []
        self._logger = get_logger()

    @property
    def state(self) -> AppState:
        return self._state

    def subscribe(self, callback: Listener) -> Callable[[], None]:
        self._listeners.append(callback)

        def unsubscribe() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return unsubscribe

    def update(self, **changes: Any) -> None:
        """Apply a partial state transition and notify listeners."""
        unknown = set(changes) - set(self._state.__dataclass_fields__)
        if unknown:
            raise ValueError(f"Unknown AppState field(s): {unknown}")

        summary = {
            k: (f"<DataFrame {v.shape}>" if isinstance(v, pd.DataFrame) else v)
            for k, v in changes.items()
        }
        self._logger.info("State transition: %s", summary)

        self._state = replace(self._state, **changes)
        self._notify()

    def reset(self, keep_scoring_system: bool = True, keep_positions: bool = True) -> None:
        self._logger.info("State reset")
        new_state = AppState()
        if keep_scoring_system:
            new_state.scoring_system = self._state.scoring_system
        if keep_positions:
            new_state.selected_positions = set(self._state.selected_positions)
        self._state = new_state
        self._notify()

    def _notify(self) -> None:
        for callback in list(self._listeners):
            callback(self._state)
