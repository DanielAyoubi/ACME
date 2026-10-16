import time

import serial


class FireStingO2:
    """PyroScience FireSting O2 meter, legacy ASCII protocol (firmware < 4)."""

    label = "FireSting O2"
    settings = {"port": "", "baudrate": 19200}
    readings = {"oxygen": "%"}
    controls = {}
    safe_state = {}

    def __init__(self, port, baudrate=19200, timeout=4.0):
        self.port = port
        self.baudrate = baudrate
        # MSR and TMP only reply once the optical measurement is done, so this must cover that.
        self.timeout = timeout
        self.serial = None

    def connect(self):
        self.disconnect()
        self.serial = serial.Serial(self.port, self.baudrate, timeout=0.5)
        time.sleep(0.5)
        # The FireSting echoes the command it was given, which other instruments won't.
        if "LOGO" not in self.send("#LOGO").upper():
            self.disconnect()
            raise IOError(f"No FireSting on {self.port}")

    def disconnect(self):
        if self.serial is not None:
            self.serial.close()
            self.serial = None

    def read(self):
        # Oxygen is temperature compensated, and the temperature is only valid after TMP.
        self.send("TMP 1")
        self.send("MSR 1")
        reply = self.send("REA 1 3 4")  # "REA 1 3 4 <air saturation x 1000>"
        air_saturation = int(reply.split()[-1]) / 1000
        if air_saturation <= -300:  # the device's "invalid" value
            return {"oxygen": None}
        # Air-saturated gas at the calibration conditions holds 20.95 % O2.
        return {"oxygen": air_saturation * 0.2095}

    def send(self, command):
        self.serial.reset_input_buffer()
        self.serial.write(f"{command}\r".encode("ascii"))
        deadline = time.time() + self.timeout
        buffer = b""
        while time.time() < deadline:
            if self.serial.in_waiting:
                buffer += self.serial.read(self.serial.in_waiting)
                if buffer.endswith(b"\r"):
                    return buffer.decode("ascii", errors="ignore").strip()
            time.sleep(0.02)
        raise TimeoutError(f"No reply to {command} from FireSting on {self.port}")
