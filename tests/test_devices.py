import inspect
import struct

import pytest

from src.devices import DEVICE_TYPES
from src.devices.brooks_mfc import BrooksMFC
from src.devices.julabo_chiller import JulaboChiller
from src.devices.vogtlin_mfc import VogtlinMFC


class FakeSerial:
    """Stands in for a serial port: replies with the queued lines and records what was written."""

    def __init__(self, lines):
        self.lines = [line.encode("ascii") + b"\r\n" for line in lines]
        self.written = []

    def write(self, data):
        self.written.append(data.decode("ascii").strip())

    def readline(self):
        if not self.lines:
            return b""
        return self.lines.pop(0)

    def reset_input_buffer(self):
        pass

    def close(self):
        pass


class FakeModbusInstrument:
    def __init__(self):
        self.registers = {}

    def read_registers(self, start, count):
        return [self.registers.get(start + i, 0) for i in range(count)]

    def write_registers(self, start, values):
        for i, value in enumerate(values):
            self.registers[start + i] = value


@pytest.mark.parametrize("type_key", DEVICE_TYPES)
def test_device_has_the_interface_the_app_expects(type_key):
    device_class = DEVICE_TYPES[type_key]
    assert isinstance(device_class.label, str)
    assert "port" in device_class.settings
    assert device_class.readings
    for method in ["connect", "disconnect", "read"]:
        assert callable(getattr(device_class, method))
    if device_class.controls:
        assert callable(getattr(device_class, "set"))
        assert set(device_class.controls) <= set(device_class.readings)
    assert set(device_class.safe_state) <= set(device_class.controls)
    for control, value in device_class.safe_state.items():
        if isinstance(device_class.controls[control], list):
            assert value in device_class.controls[control]

    # The constructor must take every setting, and Modbus devices also a timeout for the scan.
    parameters = inspect.signature(device_class.__init__).parameters
    for name in device_class.settings:
        assert name in parameters
    if "address" in device_class.settings:
        assert "timeout" in parameters


def test_julabo_reads_external_probe_and_setpoint():
    chiller = JulaboChiller("COM1")
    chiller.serial = FakeSerial(["21.53", "20.00"])
    assert chiller.read() == {"temperature": 21.53, "setpoint": 20.0}
    assert chiller.serial.written == ["in_pv_02", "in_sp_00"]


def test_julabo_set_starts_temperature_control():
    chiller = JulaboChiller("COM1")
    chiller.serial = FakeSerial([])
    chiller.set("temperature", 15.0)
    assert chiller.serial.written == ["out_sp_00 15.0", "out_mode_05 1"]


def brooks_status(flow, setpoint, state):
    return [
        "<--- BROOKS CONTROLLER STATUS --->",
        "<Unit: ml/m",
        f"<Live Flow: {flow} ml/m",
        f"<Setpoint: {setpoint}",
        f"<State: {state}",
        "<------------------------------->",
    ]


def test_brooks_reads_ml_per_min_as_l_per_min():
    mfc = BrooksMFC("COM1")
    mfc.serial = FakeSerial(brooks_status(1500, 1500, "RUNNING"))
    assert mfc.read() == {"flow": 1.5, "setpoint": 1.5}


def test_brooks_small_flow_reads_zero_and_stopped_setpoint_is_zero():
    mfc = BrooksMFC("COM1")
    mfc.serial = FakeSerial(brooks_status(25, 1500, "STOPPED"))
    assert mfc.read() == {"flow": 0.0, "setpoint": 0.0}


def test_vogtlin_setpoint_round_trips_as_32_bit_float():
    mfc = VogtlinMFC("COM1")
    mfc.instrument = FakeModbusInstrument()
    mfc.set("flow", 1.25)
    assert mfc.read()["setpoint"] == 1.25
    # Big-endian float in the setpoint register pair 0x0006-0x0007.
    assert struct.pack(">HH", mfc.instrument.registers[6], mfc.instrument.registers[7]) == struct.pack(">f", 1.25)
