import csv
import os

import pytest

from src.experiment import humidity_cycle, save_summary_plot


def humid_levels(steps):
    return [round(step["setpoints"][("Humid", "flow")] / 2.0 * 100) for step in steps]


def test_one_cycle_goes_up_and_back():
    steps = humidity_cycle("Humid", "Dry", 2.0, 0, 100, 50, 10, 1)
    assert humid_levels(steps) == [0, 50, 100, 50, 0]
    assert all(step["minutes"] == 10 for step in steps)


def test_start_high_reverses_the_cycle():
    steps = humidity_cycle("Humid", "Dry", 2.0, 0, 100, 50, 10, 1, start_high=True)
    assert humid_levels(steps) == [100, 50, 0, 50, 100]


def test_cycles_do_not_repeat_the_turning_points():
    steps = humidity_cycle("Humid", "Dry", 2.0, 0, 100, 50, 10, 2)
    assert humid_levels(steps) == [0, 50, 100, 50, 0, 50, 100, 50, 0]


def test_last_level_is_high_even_when_step_does_not_fit():
    steps = humidity_cycle("Humid", "Dry", 2.0, 10, 95, 20, 10, 1)
    assert humid_levels(steps) == [10, 30, 50, 70, 90, 95, 90, 70, 50, 30, 10]


def test_humid_and_dry_add_up_to_total_flow():
    for step in humidity_cycle("Humid", "Dry", 1.5, 5, 95, 7, 10, 1):
        setpoints = step["setpoints"]
        assert setpoints[("Humid", "flow")] + setpoints[("Dry", "flow")] == pytest.approx(1.5)


def test_summary_plot_is_saved_next_to_the_csv(tmp_path):
    csv_path = str(tmp_path / "experiment_120000.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["time", "Humid MFC flow", "RH rh", "Valve position"])
        writer.writerow(["2026-01-01T12:00:00", "1.0", "40.0", "2"])
        writer.writerow(["2026-01-01T12:00:02", "1.2", "", "3"])
    units = {"Humid MFC flow": "L/min", "RH rh": "%", "Valve position": ""}

    png_path = save_summary_plot(csv_path, units)

    assert png_path == str(tmp_path / "experiment_120000.png")
    assert os.path.exists(png_path)


def test_no_plot_for_an_empty_csv(tmp_path):
    csv_path = str(tmp_path / "experiment_120000.csv")
    with open(csv_path, "w", encoding="utf-8") as file:
        file.write("time,Humid MFC flow\n")
    assert save_summary_plot(csv_path, {"Humid MFC flow": "L/min"}) is None
