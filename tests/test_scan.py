import pytest
import serial

from src.devices.scan import scan

present = set()  # (class name, port, address) of every fake device that answers
probed = []  # (class name, port, address) of every probe, in order


class FakeModbus:
    label = "Fake Modbus"
    settings = {"port": "", "address": 1}

    def __init__(self, port, address=None, timeout=0.5):
        self.port = port
        self.address = address

    def connect(self):
        key = (type(self).__name__, self.port, self.address)
        probed.append(key)
        if key not in present:
            raise IOError("no answer")

    def disconnect(self):
        pass


class OtherModbus(FakeModbus):
    label = "Other Modbus"
    settings = {"port": "", "address": 240}


class FakeAscii(FakeModbus):
    label = "Fake ASCII"
    settings = {"port": ""}


class FakePort:
    """Stands in for serial.Serial in the scan's open check; the port "BUSY" is held elsewhere."""

    def __init__(self):
        self.port = None

    def open(self):
        if self.port == "BUSY":
            raise serial.SerialException("access denied")

    def close(self):
        pass


@pytest.fixture(autouse=True)
def fake_hardware(monkeypatch):
    present.clear()
    probed.clear()
    monkeypatch.setattr("src.devices.scan.DEVICE_TYPES",
                        {"modbus": FakeModbus, "other_modbus": OtherModbus, "ascii": FakeAscii})
    monkeypatch.setattr(serial, "Serial", FakePort)


def run_scan(ports, deep, known_devices):
    statuses = {}

    def on_progress(port, text):
        statuses[port] = text
        return True

    return scan(ports, deep, known_devices, on_progress), statuses


def probes_on(port):
    return [(name, address) for name, probed_port, address in probed if probed_port == port]


def test_quick_scan_finds_every_known_address_and_tries_them_only_for_their_own_type():
    present.update({("FakeModbus", "COM1", 1), ("FakeModbus", "COM1", 24)})
    known = [{"type": "modbus", "port": "COM1", "address": 24},
             {"type": "other_modbus", "port": "COM2", "address": 7}]
    found, statuses = run_scan(["COM1", "COM2"], False, known)

    assert [(device["port"], device["address"]) for device in found] == [("COM1", 1), ("COM1", 24)]
    assert probes_on("COM2") == [("FakeModbus", 1), ("FakeModbus", 24), ("OtherModbus", 240),
                                 ("OtherModbus", 7), ("FakeAscii", None)]
    assert statuses["COM2"] == "nothing recognised"


def test_deep_scan_sweeps_for_a_modbus_device_at_an_unusual_address():
    present.add(("OtherModbus", "COM1", 57))
    found, statuses = run_scan(["COM1"], True, [])

    assert found == [{"type": "other_modbus", "port": "COM1", "address": 57}]
    assert len(probed) == len(set(probed))  # no address is tried twice


def test_deep_scan_keeps_sweeping_a_bus_but_only_for_the_type_found_on_it():
    present.update({("FakeModbus", "COM1", 1), ("FakeModbus", "COM1", 200)})
    found, statuses = run_scan(["COM1"], True, [])

    assert [device["address"] for device in found] == [1, 200]
    assert all(name == "FakeModbus" for name, address in probes_on("COM1"))


def test_deep_scan_does_not_sweep_a_port_with_an_ascii_device():
    present.add(("FakeAscii", "COM1", None))
    found, statuses = run_scan(["COM1"], True, [])

    assert found == [{"type": "ascii", "port": "COM1"}]
    assert probes_on("COM1") == [("FakeModbus", 1), ("OtherModbus", 240), ("FakeAscii", None)]


def test_a_port_that_will_not_open_is_skipped():
    found, statuses = run_scan(["BUSY"], True, [])

    assert found == []
    assert probed == []
    assert statuses["BUSY"].startswith("could not open")
