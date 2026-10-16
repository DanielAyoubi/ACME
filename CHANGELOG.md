# Changelog

## Unreleased

- Every device type has a safe state that it is set to when an experiment finishes and when
  the app disconnects or closes: MFCs to zero flow, the servo valve to position 1 (closed).
  Before, only MFC flows were set to 0.
- ACME now stands for Automated Control and Monitoring of Experiments. The README and citation
  describe it as general experiment automation, with the humidity tools as one built-in use case.
- Faster device scan: all ports are scanned at the same time, a deep scan only sweeps Modbus
  addresses on ports where no other device answered, and the Vaisala probe no longer retries
  silent addresses.
- More precise device scan: known addresses are only tried for their own device type, a quick
  scan finds every known address on a bus, ports another program holds are reported as such,
  and the servo valve is probed first so other probes no longer reset its Arduino.

## 1.0.0 — 2026-30-06

First tagged release.

- Device catalog with drivers for Vögtlin and Brooks MFCs, Vaisala HMP110 and EdgeTech
  DewMaster RH probes, Julabo chillers, PyroScience FireSting O₂ meters and a Swagelok
  3-way servo valve.
- Serial port scan that finds known devices, including a Modbus address sweep.
- Setup catalog: one JSON file per rig, switchable from the File menu.
- Live plot, latest readings and CSV logging of every reading.
- RH computed from a temperature and a dew point (Magnus formula), with an optional
  salt-deliquescence calibration.
- PID control of RH by splitting a total flow between a humid and a dry MFC.
- Experiment tab: step table, humidity-cycle generator, named experiments and a PNG
  summary plot at the end.
- Tests for the humidity, PID, experiment and driver logic, run on GitHub Actions.

## Before 1.0.0

Developed since November 2025 for humidity-controlled experiments in the lab, starting as a monitor for one MFC and an RH probe and growing into
the modular device setup.
