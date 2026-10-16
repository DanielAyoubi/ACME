---
title: 'ACME: open-source automated control and monitoring of multi-instrument laboratory experiments'
tags:
  - Python
  - laboratory automation
  - instrument control
  - data acquisition
  - real-time monitoring
  - experiment scheduling
authors:
  - given-names: Daniel
    surname: Ayoubi
    orcid: https://orcid.org/0000-0003-1972-6285
    affiliation: 1
  - given-names: Fabian
    surname: Mahrt
    orcid: https://orcid.org/0000-0002-7059-6765
    affiliation: 1
affiliations:
  - index: 1
    name: Department of Chemistry, Aarhus University, Denmark
    ror: 01aj84f44
date: 16 October 2026
bibliography: paper.bib
---

# Summary

ACME (Automated Control and Monitoring of Experiments) is an open-source Python
application that runs a set of instruments in an experimental setup from one graphical window.
It reads all connected devices at a fixed interval and writes every reading to a
timestamped CSV file and plots the readings in real time. When running an experimental setup
that requires a sequence of changes over hours or days, a set of instructions can be written
as a table of steps, each setting the setpoints of any device to hold for a given time.
Instruments are described in a JSON setup file, found by a serial port scan, and a new
instrument type is added with one small driver file. Built-in tools for humidity control
show how a domain-specific experiment is built on this general core.

# Statement of need

Laboratory setups often combine instruments from several vendors, such as mass flow
controllers, sensors and temperature baths, each with its own software and data format.
Running them by hand means watching several programs, merging their logs afterwards and
changing setpoints at the right moment. For experiments that run over many hours or days,
these manual changes are tedious and easy to get wrong, and require someone to be present.
ACME replaces this with one program that controls and logs all instruments together,
displays the data as it is recorded, and carries out scheduled changes to setpoints
on its own. It keeps running through brief device dropouts by reconnecting automatically,
and it is simple enough to be set up and extended by researchers without a software background.

# State of the field

LabVIEW [@labview] is widely used to build instrument control programs, but it is proprietary. 
Large research facilities use control systems such as EPICS [@dalesio1994] and the Bluesky data 
acquisition framework [@allan2019], which provide extensive capabilities but are generally intended 
for more complex experimental infrastructure. Open-source alternatives include PyOpticon [@randall2025] 
and NOMAD CAMELS [@fuchs2024]. PyOpticon provides graphical instrument control and automation, 
but requires Python scripting to define the interface and experiment sequences. NOMAD CAMELS provides 
a graphical environment for defining and executing measurement protocols, using the Bluesky run 
engine and ophyd-based instrument drivers. However, its protocol-based approach differs from setups 
where continuous monitoring and logging are required independently of an experiment sequence.

ACME addresses this use case by providing a ready-to-run application for controlling and monitoring 
small laboratory setups containing serial and Modbus instruments. The setup is described in a JSON file, 
experiments are defined as tables of timed setpoints, and no programming is required to operate the system. 
Continuous logging, automatic device reconnection and safe-state handling are built into the application. 
Rather than extending an existing framework, ACME was developed around these requirements, with a lightweight 
architecture that researchers can inspect, modify and extend.

# Software design

ACME is written in Python with a PyQt6 [@pyqt6] interface and PyQtGraph [@pyqtgraph]
live plots. A single worker thread (`src/worker.py`) owns all hardware access. The window
sends it commands, such as a new setpoint or the start of an experiment, through a queue,
and the worker returns readings and status messages through Qt signals. We chose one thread for all devices over
one thread per device because serial ports are not thread-safe and several Modbus devices
often share one port. The cost is that a slow device delays the whole poll, which is
acceptable when readings are taken every few seconds and the processes being studied
change on a timescale much slower than this.

Each poll gathers the readings of all devices into one row of a CSV file, which is flushed
after every row. We preferred plain CSV, as opposed to for instance a database, because of familiarity for user, while also
enabling continuous stream to a file that can be opened in any program while the run is still going, and a crash of the program loses no
recorded data. The price is that the file holds only the readings, not the units or the
setup that produced them.

A driver is a small class that declares its connection `settings`, its `readings` and
`controls` with their units, and a `safe_state`, and implements `connect`, `read` and `set`.
Drivers communicate through pySerial [@pyserial], MinimalModbus [@minimalmodbus] and
PyModbus [@pymodbus], and are registered in one dictionary (`src/devices/__init__.py`).
The device dialog, manual controls, plot panels, CSV columns and experiment table are all
built from these declarations, so adding a driver needs no change elsewhere in the program.
The same declarations drive the device scan (`src/devices/scan.py`), which probes all
serial ports in parallel for every known device type at its usual address and, in a deep
scan, at every Modbus address.

Two features make long, unattended runs possible. A device that fails to answer is
disconnected, logged as missing, and retried while the other devices keep
being recorded. When an experiment finishes, or the program disconnects or closes, every
device is returned to its declared safe state, such as zero flow for a mass flow controller.

An experiment is a list of steps typed into a table in the window rather than written as a
script. Each step sets the setpoints in its row and then holds for a given time or waits for a
condition: a target value of a humidity or temperature reading, which is met once the reading
has stayed within a tolerance of the target for a settle time. A step with both ends at
whichever comes first, so a condition that is never met cannot stall an unattended run. This
needs no programming, but the logic is limited to these two kinds of step, with no branching
or loops. When the experiment ends, a summary figure is saved with Matplotlib [@hunter2007].

The humidity tools show how a domain-specific experiment builds on this core: relative
humidity (RH) is calculated from a measured dew point and temperature with the Magnus formula
[@alduchov1996], a PID loop (`src/control.py`) holds a target RH by splitting a constant total
flow between a humid and a dry mass flow controller, and a cycle generator fills the step
table with stepwise humidity cycles. An RH condition in a step runs the same PID loop to reach
its target.

# Research impact statement

ACME was developed for, and first used in, the author's research on oxygen
diffusion in aerosol particles under atmospherically relevant humidity and temperature.
In these experiments it logs the oxygen concentration from a device sensor,
sets the relative humidity with the PID loop and humidity-cycle step tables, sets the
temperature through a chiller, and switches the gas between nitrogen and oxygen with a
servo valve, all in one scheduled run.

Beyond this study, ACME is used for humidity-controlled experiments in the
Aerosol and Cloud Microphysics group at Aarhus University, where it runs the humidity cells
used by several group members, and has already been used in research MSc thesis work [@msc_thesis]. 
It was also used to control the sample humidity during small- and wide-angle X-ray scattering (SAXS/WAXS)
experiments at Diamond Light Source (session SM43563-1 on I22), studying the response of
catechol and 4-nitrocatechol phase states to changing RH.

# AI usage disclosure

Claude Code (Anthropic) was used to develop the graphical user interface of ACME (`src/gui/`).
Claude Code was also used to write the test suite `tests/` and the contributing guidelines `CONTRIBUTING.md`.
All AI-assisted code, documentation and text were reviewed, edited and tested by the authors,
who take full responsibility for the content.

# Acknowledgements

This work was supported by the Novo Nordisk Foundation (grant NNF24OC0093745).
We acknowledge Diamond Light Source for time on beamline I22 under session SM43563-1.

# References
