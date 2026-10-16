# Contributing to ACME controller

Thanks for helping out. ACME controller is developed in the Aerosol and Cloud Microphysics
group at Aarhus University, but it is not tied to one field: drivers for any lab instrument and
other contributions are welcome.

## Reporting a bug or asking for help

Open an issue at https://github.com/DanielAyoubi/ACME/issues. Please include:

- what you did and what happened instead,
- the device types involved and your setup JSON (from `src/setups/`), with anything private removed,
- the error text from the window or terminal,
- your operating system and Python version.

Questions about using the program are also welcome as issues.

## Adding a device

Most contributions are new instrument drivers. Follow *Adding a new device* in the
[README](README.md#adding-a-new-device): one file in `src/devices/` and one line in
`DEVICE_TYPES`. If you can, add a test in `tests/test_devices.py` that feeds the driver
recorded replies through the `FakeSerial` stand-in, so it can be checked without the hardware.

## Proposing a change

1. Fork the repository and make a branch.
2. Keep the code simple and in the style of existing code.
3. Run the tests:

   ```
   pip install -r requirements.txt pytest
   pytest
   ```

4. Open a pull request describing the change and, for driver changes, which hardware you tested on.
