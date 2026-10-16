import pytest

import src.worker
from src.devices import DEVICE_TYPES
from src.worker import Worker


class FakeMFC:
    label = "Fake MFC"
    settings = {"port": ""}
    readings = {"flow": "L/min", "setpoint": "L/min"}
    controls = {"flow": "L/min"}
    safe_state = {"flow": 0.0}

    def __init__(self, port):
        self.flow = 0.0

    def connect(self):
        pass

    def disconnect(self):
        pass

    def read(self):
        return {"flow": self.flow, "setpoint": self.flow}

    def set(self, name, value):
        self.flow = value


class FakeProbe:
    label = "Fake probe"
    settings = {"port": ""}
    readings = {"RH": "%", "temperature": "°C"}
    controls = {}
    safe_state = {}

    def __init__(self, port):
        self.values = {"RH": 40.0, "temperature": 20.0}

    def connect(self):
        pass

    def disconnect(self):
        pass

    def read(self):
        return dict(self.values)


class Clock:
    """Stands in for the time module in the worker, so a test sets the time itself."""

    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    clock = Clock()
    monkeypatch.setattr(src.worker, "time", clock)
    return clock


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setitem(DEVICE_TYPES, "fake_mfc", FakeMFC)
    monkeypatch.setitem(DEVICE_TYPES, "fake_probe", FakeProbe)
    setup = {
        "log_folder": str(tmp_path),
        "poll_interval": 2.0,
        "devices": [
            {"name": "Humid", "type": "fake_mfc"},
            {"name": "Dry", "type": "fake_mfc"},
            {"name": "Probe", "type": "fake_probe"},
        ],
        "computed_rh": [],
        "rh_control": {"source": "Probe RH", "humid_mfc": "Humid", "dry_mfc": "Dry", "target": 50.0,
                       "total_flow": 2.0, "kp": 1.0, "ki": 0.03, "kd": 0.0},
        "conditions": {"rh_tolerance": 1.0, "temperature_tolerance": 0.2, "settle_minutes": 5.0},
    }
    worker = Worker(setup)
    worker.messages = []
    worker.message.connect(worker.messages.append)
    for name in worker.devices:
        worker.try_connect(name)
    yield worker
    worker.close_log()  # so the temporary folder can be removed on Windows


def run_once(worker):
    # One pass of the worker's loop: move on if the step is done, then take a reading.
    if worker.steps and worker.step_finished():
        worker.next_step()
    worker.poll()


def test_condition_waits_until_the_reading_has_settled(worker, clock):
    worker.start_experiment([
        {"minutes": None, "condition": ("Probe temperature", 5.0), "setpoints": {}},
        {"minutes": 10, "condition": None, "setpoints": {}},
    ])
    probe = worker.devices["Probe"]
    for now, temperature in [(0, 20.0), (60, 5.1), (200, 5.5), (300, 4.9), (599, 4.9)]:
        clock.now = now
        probe.values["temperature"] = temperature
        run_once(worker)
        assert worker.step_index == 0
    # Within 0.2 °C since 300 s: the 5 min settle time has passed. Leaving the band at 200 s
    # restarted the clock, so 60 s does not count.
    clock.now = 600
    run_once(worker)
    assert worker.step_index == 1


def test_hold_time_limits_a_condition_that_never_settles(worker, clock):
    worker.start_experiment([
        {"minutes": 2, "condition": ("Probe temperature", 5.0), "setpoints": {}},
        {"minutes": 10, "condition": None, "setpoints": {}},
    ])
    clock.now = 0
    run_once(worker)
    clock.now = 119
    run_once(worker)
    assert worker.step_index == 0
    clock.now = 120
    run_once(worker)
    assert worker.step_index == 1


def test_rh_condition_runs_the_rh_loop_until_a_step_sets_the_flows(worker, clock):
    worker.start_experiment([
        {"minutes": None, "condition": ("Probe RH", 60.0), "setpoints": {}},
        {"minutes": 30, "condition": None, "setpoints": {}},
        {"minutes": 10, "condition": None, "setpoints": {("Humid", "flow"): 0.5}},
    ])
    probe = worker.devices["Probe"]
    clock.now = 0
    run_once(worker)
    assert worker.rh_enabled
    assert worker.rh["source"] == "Probe RH" and worker.rh["target"] == 60.0
    # Too dry, so the loop sends more than half of the flow through the humid MFC.
    assert worker.devices["Humid"].flow > 1.0

    probe.values["RH"] = 60.0
    clock.now = 10
    run_once(worker)
    clock.now = 310
    run_once(worker)
    assert worker.step_index == 1
    assert worker.rh_enabled  # still holding the RH through a step that leaves the flows alone

    clock.now = 310 + 30 * 60
    run_once(worker)
    assert worker.step_index == 2
    assert not worker.rh_enabled
    assert worker.devices["Humid"].flow == 0.5


def test_stopping_the_experiment_ends_the_rh_loop(worker, clock):
    worker.start_experiment([{"minutes": None, "condition": ("Probe RH", 60.0), "setpoints": {}}])
    run_once(worker)
    assert worker.rh_enabled
    worker.stop_experiment("Experiment stopped.")
    assert not worker.rh_enabled


def test_rh_condition_step_may_not_set_the_flows_itself(worker, clock):
    worker.start_experiment([
        {"minutes": None, "condition": ("Probe RH", 60.0), "setpoints": {("Humid", "flow"): 1.0}},
    ])
    assert worker.steps == []
    assert "Leave those cells empty" in worker.messages[-1]
