from PyQt6.QtCore import Qt

from app.analysis.metrics import analyze
from app.gui.control_panel import ControlPanel
from app.gui.import_panel import ImportPanel
from app.gui.main_window import MainWindow
from app.gui.results_panel import ResultsPanel
from app.gui.widgets import Banner
from app.visualization.charts import generate_all_charts


def test_banner_show_error_and_dismiss(qtbot):
    banner = Banner()
    qtbot.addWidget(banner)
    assert not banner.isVisible()
    banner.show_error("Something broke")
    assert banner.isVisible()
    assert "Something broke" in banner.message_label.text()
    banner.dismiss()
    assert not banner.isVisible()


def test_banner_show_success(qtbot):
    banner = Banner()
    qtbot.addWidget(banner)
    banner.show_success("All good", auto_hide_ms=0)
    assert banner.isVisible()
    assert "All good" in banner.message_label.text()


def test_control_panel_position_toggle_emits_signal(qtbot):
    panel = ControlPanel()
    qtbot.addWidget(panel)
    received: list[set[str]] = []
    panel.positions_changed.connect(received.append)
    panel._checkboxes["QB"].setChecked(False)
    assert received
    assert "QB" not in received[-1]


def test_control_panel_run_button_enter_key(qtbot):
    panel = ControlPanel()
    qtbot.addWidget(panel)
    panel.show()
    received = []
    panel.run_requested.connect(lambda: received.append(True))
    panel.run_button.setFocus()
    qtbot.keyClick(panel.run_button, Qt.Key.Key_Return)
    assert received


def test_control_panel_set_running_swaps_widgets(qtbot):
    panel = ControlPanel()
    qtbot.addWidget(panel)
    panel.set_running(True)
    assert panel.action_stack.currentIndex() == 1
    panel.set_running(False)
    assert panel.action_stack.currentIndex() == 0


def test_import_panel_load_valid_csv(qtbot, tmp_path, sample_df):
    path = tmp_path / "players.csv"
    sample_df.to_csv(path, index=False)

    panel = ImportPanel()
    qtbot.addWidget(panel)

    received = []
    panel.data_loaded.connect(lambda df, mapping, warnings, p: received.append(df))

    panel.load_file(str(path))
    qtbot.waitUntil(lambda: len(received) == 1, timeout=3000)
    assert len(received[0]) == len(sample_df)
    assert panel.preview_table.rowCount() == min(10, len(sample_df))


def test_import_panel_invalid_extension_emits_error(qtbot):
    panel = ImportPanel()
    qtbot.addWidget(panel)
    errors = []
    panel.error_occurred.connect(errors.append)
    panel.drop_zone._handle_path("/tmp/not_a_spreadsheet.txt")
    assert errors


def test_results_panel_empty_then_display(qtbot, sample_df):
    panel = ResultsPanel()
    qtbot.addWidget(panel)
    assert panel.stack.currentWidget() is panel._empty_state

    result = analyze(sample_df)
    charts = generate_all_charts(result)
    panel.display_results(result, charts)
    assert panel.stack.currentWidget() is panel.tabs
    assert panel.summary_table.rowCount() == len(result.position_metrics) + 1

    panel.reset()
    assert panel.stack.currentWidget() is panel._empty_state


def test_main_window_full_flow(qtbot, tmp_path, sample_df):
    path = tmp_path / "players.csv"
    sample_df.to_csv(path, index=False)

    window = MainWindow()
    qtbot.addWidget(window)

    window.import_panel.load_file(str(path))
    qtbot.waitUntil(lambda: window._store.state.raw_dataframe is not None, timeout=3000)
    assert window.control_panel.run_button.isEnabled()

    window.control_panel.run_requested.emit()
    qtbot.waitUntil(lambda: window._store.state.analysis_results is not None, timeout=5000)

    assert window.results_panel.stack.currentWidget() is window.results_panel.tabs

    window.control_panel.reset_requested.emit()
    assert window._store.state.raw_dataframe is None
    assert window.results_panel.stack.currentWidget() is window.results_panel._empty_state
