import serial

# A 3-way Swagelok ball valve turned by a servo behind an Arduino UNO R3 (firmware swagelokServoV1).
# Position 1 connects port 1 to itself (closed), 2 connects port 1 to 2, and 3 connects port 1 to 3.
# `?help` on the port lists the ASCII commands; `?` reads and `>` writes, one per line.


class ServoValve:
    label = "Servo Valve"
    settings = {"port": "", "baudrate": 115200, "position_names": ""}
    readings = {"position": ""}
    controls = {"position": [1, 2, 3]}
    safe_state = {"position": 1}  # closed

    # position_names, such as "closed, nitrogen, oxygen", is only shown in the window.
    def __init__(self, port, baudrate=115200, position_names="", timeout=0.5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.angles = {}

    def connect(self):
        self.disconnect()
        # Opening the port normally resets the Arduino, which moves the valve to its power-on
        # position. Holding DTR and RTS low while opening stops that reset.
        self.serial = serial.Serial()
        self.serial.port = self.port
        self.serial.baudrate = self.baudrate
        self.serial.timeout = self.timeout
        self.serial.dtr = False
        self.serial.rts = False
        self.serial.open()
        try:
            for position in [1, 2, 3]:
                self.angles[position] = float(self.query(f"?av1{position}", f"1to{position} ang"))
        except Exception:
            self.disconnect()
            raise

    def disconnect(self):
        if self.serial is not None:
            self.serial.close()
            self.serial = None

    def read(self):
        angle = float(self.query("?ang", "current angle").removesuffix("deg"))
        position = None  # the valve is moving or between positions
        for number, position_angle in self.angles.items():
            if angle == position_angle:
                position = number
        return {"position": position}

    def set(self, name, value):
        position = round(value)
        if position not in [1, 2, 3]:
            raise ValueError(f"position {value:g} is not 1, 2 or 3")
        self.query(f">v1{position}", f"going to pos 1to{position}")

    def query(self, command, expected):
        self.serial.reset_input_buffer()
        self.serial.write(f"{command}\r\n".encode("ascii"))
        # The firmware also prints status lines on its own, so skip lines until the reply shows up.
        while True:
            line = self.serial.readline().decode("ascii", errors="replace").strip()
            if not line:
                raise TimeoutError(f"{self.port}: no reply to {command}")
            if expected in line:
                return line.split(":")[-1].strip()
