---
title: 'ACME controller: open-source automated control and monitoring of multi-instrument laboratory experiments'
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
date: 30 September 2026
bibliography: paper.bib
---

# Summary

ACME controller (Automated Control and Monitoring of Experiments) is an open-source Python
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
these manual changes are tedious and easy to get wrong, and requires someone to be present.
ACME replaces this with one program that controls and logs all instruments together, 
displays the data as it is recorded, and carries out scheduled setpoint changes
on its own. It keeps running through brief device dropouts by reconnecting automatically,
and it is simple enough to be set up and extended by researchers without a software background.

# State of the field

<!-- TODO -->

# Software design


<!-- TODO (optional): a figure of an RH cycle from a real experiment, see figures/README.md
![Humidity cycle recorded with ACME controller: RH setpoint and measured RH (top) and the humid and dry flows (bottom).\label{fig:cycle}](figures/beamtime_rh_cycle.png)
-->

# Research impact statement

Its first application is humidity control: ACME controller is used for humidity-controlled
experiments in the Aerosol and Cloud Microphysics group at Aarhus University, where it runs the humidity cells used by several
group members. It was used to control the sample humidity during small- and wide-angle X-ray
scattering (SAXS/WAXS) experiments at Diamond Light Source, studying the
response of catechol and 4-nitrocatechol to changing RH.
<!-- TODO: Diamond beamtime — beamline, proposal number, dates; cite once there is a publication, abstract or proposal reference [@diamond_beamtime]. -->
<!-- TODO: MSc thesis — once public, add an msc_thesis entry to paper.bib and move this sentence out of the comment:
-->

# AI usage disclosure

Claude Code (Anthropic) was used to develop the graphical user interface of ACME (`src/gui/`). 
Claude Code was also used to write the test suite and the contributing guidelines.
All AI-assisted code, documentation and text were reviewed, edited and tested by the authors,
who take full responsibility for the content.

# Acknowledgements

<!-- TODO: funding sources? + others. -->

# References
