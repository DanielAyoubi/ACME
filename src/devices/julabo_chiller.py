import time

import serial


class JulaboChiller:
    label = "Julabo chiller"
    settings = {"port": "", "baudrate": 9600}
    readings = {"temperature": "°C", "setpoint": "°C"}
    controls = {"temperature": "°C"}
    # Left at its setpoint: a jump in temperature could harm the sample.
    safe_state = {}

    def __init__(self, port, baudrate=9600, timeout=1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None

    def connect(self):
        self.disconnect()
        self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        # Any chatty instrument answers something, so insist on a setpoint that parses.
        try:
            float(self.query("in_sp_00"))
        except Exception:
            self.disconnect()
            raise

    def disconnect(self):
        if self.serial is not None:
            self.serial.close()
            self.serial = None

    def read(self):
        # in_pv_02 is the external probe, which sits in the sample environment.
        return {"temperature": float(self.query("in_pv_02")), "setpoint": float(self.query("in_sp_00"))}

    def set(self, name, value):
        self.send(f"out_sp_00 {value}")
        self.send("out_mode_05 1")  # start temperature control

    def send(self, command):
        self.serial.write(f"{command}\r\n".encode("ascii"))
        time.sleep(0.1)

    def query(self, command):
        self.serial.reset_input_buffer()
        self.send(command)
        return self.serial.readline().decode("ascii", errors="ignore").strip()
