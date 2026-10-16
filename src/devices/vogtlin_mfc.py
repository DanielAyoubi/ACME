import struct

import minimalmodbus
import serial

# Register map: https://www.voegtlin.com/data/329-3042_en_manualsmart_digicom.pdf
FLOW_REGISTER = 0x0000
SETPOINT_REGISTER = 0x0006


class VogtlinMFC:
    label = "Vögtlin MFC"
    settings = {"port": "", "baudrate": 9600, "address": 1}
    readings = {"flow": "L/min", "setpoint": "L/min"}
    controls = {"flow": "L/min"}
    safe_state = {"flow": 0.0}  # what the app sets when it lets go of the device

    def __init__(self, port, baudrate=9600, address=1, timeout=0.5):
        self.port = port
        self.baudrate = baudrate
        self.address = address
        self.timeout = timeout
        self.serial = None
        self.instrument = None

    def connect(self):
        self.disconnect()
        self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        # Hand minimalmodbus an open port rather than a port name: by name it caches
        # the port in a module global, and a scan could then silently join a live bus.
        self.instrument = minimalmodbus.Instrument(self.serial, self.address, mode=minimalmodbus.MODE_RTU)
        try:
            self.read_float(FLOW_REGISTER)
        except Exception:
            self.disconnect()
            raise

    def disconnect(self):
        if self.serial is None:
            return
        self.serial.close()
        self.serial = None
        self.instrument = None

    def read(self):
        return {"flow": self.read_float(FLOW_REGISTER), "setpoint": self.read_float(SETPOINT_REGISTER)}

    def set(self, name, value):
        # The MFC stores a 32-bit float across two 16-bit registers, big-endian.
        registers = list(struct.unpack(">HH", struct.pack(">f", value)))
        self.instrument.write_registers(SETPOINT_REGISTER, registers)

    def read_float(self, register):
        registers = self.instrument.read_registers(register, 2)
        return struct.unpack(">f", struct.pack(">HH", *registers))[0]
