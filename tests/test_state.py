from app.state import AppState, StateStore


def test_initial_state_defaults():
    store = StateStore()
    state = store.state
    assert state.loaded_file_path is None
    assert state.raw_dataframe is None
    assert state.scoring_system == "PPR"
    assert state.selected_positions == {"QB", "RB", "WR", "TE", "K", "DEF"}
    assert state.analysis_results is None


def test_update_notifies_subscribers():
    store = StateStore()
    received: list[AppState] = []
    store.subscribe(received.append)

    store.update(scoring_system="Half-PPR")

    assert len(received) == 1
    assert received[0].scoring_system == "Half-PPR"
    assert store.state.scoring_system == "Half-PPR"


def test_update_creates_new_state_object_not_mutating_old():
    store = StateStore()
    old_state = store.state
    store.update(scoring_system="Standard")
    assert old_state.scoring_system == "PPR"
    assert store.state is not old_state
    assert store.state.scoring_system == "Standard"


def test_unsubscribe_stops_notifications():
    store = StateStore()
    received: list[AppState] = []
    unsubscribe = store.subscribe(received.append)
    unsubscribe()

    store.update(scoring_system="Standard")

    assert received == []


def test_update_rejects_unknown_field():
    store = StateStore()
    try:
        store.update(not_a_real_field=123)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_reset_preserves_scoring_and_positions_by_default():
    store = StateStore()
    store.update(
        scoring_system="Standard",
        selected_positions={"QB", "RB"},
        loaded_file_path="/tmp/x.csv",
    )
    store.reset()
    assert store.state.loaded_file_path is None
    assert store.state.scoring_system == "Standard"
    assert store.state.selected_positions == {"QB", "RB"}


def test_reset_can_fully_clear_state():
    store = StateStore()
    store.update(scoring_system="Standard", selected_positions={"QB"})
    store.reset(keep_scoring_system=False, keep_positions=False)
    assert store.state.scoring_system == "PPR"
    assert store.state.selected_positions == {"QB", "RB", "WR", "TE", "K", "DEF"}
