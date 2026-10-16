from concurrent.futures import ThreadPoolExecutor

import serial

from src.devices import DEVICE_TYPES

# A Modbus reply arrives within milliseconds, so silent addresses can be skipped quickly.
# The ASCII instruments keep their own timeouts, because some only answer after a measurement.
MODBUS_TIMEOUT = 0.15


def scan(ports, deep, known_devices, on_progress):
    """Find known devices on `ports`; `on_progress(port, text)` returns False to cancel."""
    if not ports:
        return []
    # Every port is its own bus, so all ports are scanned at the same time.
    with ThreadPoolExecutor(len(ports)) as pool:
        results = pool.map(lambda port: scan_port(port, deep, known_devices, on_progress), ports)
    found = []
    for port_found in results:
        found += port_found
    return found


def scan_port(port, deep, known_devices, on_progress):
    # A port another program holds would fail every probe, so check it once.
    # DTR and RTS stay low, as in ServoValve, so an Arduino on the port does not reset.
    test = serial.Serial()
    test.port = port
    test.dtr = False
    test.rts = False
    try:
        test.open()
    except serial.SerialException:
        on_progress(port, "could not open the port, is another program using it?")
        return []
    test.close()

    # Each type's default address, then the addresses the setup uses for that same type.
    likely_addresses = {}
    for type_key, device_class in DEVICE_TYPES.items():
        if "address" in device_class.settings:
            known = [device["address"] for device in known_devices if device["type"] == type_key]
            likely_addresses[type_key] = list(dict.fromkeys([device_class.settings["address"]] + known))
        else:
            likely_addresses[type_key] = [None]

    found = []
    for type_key, addresses in likely_addresses.items():
        for address in addresses:
            text = f"looking for {DEVICE_TYPES[type_key].label}"
            if address is not None:
                text += f" at address {address}"
            if not on_progress(port, text):
                return found
            device = probe(port, type_key, address)
            if device is not None:
                found.append(device)
        # A port is one bus, and a bus runs one protocol at one speed.
        if found:
            break

    if deep:
        # Only a Modbus bus can hold more devices. A port with an ASCII instrument is done.
        if found:
            sweep_types = [found[0]["type"]]
        else:
            sweep_types = list(DEVICE_TYPES)
        for type_key in sweep_types:
            if "address" not in DEVICE_TYPES[type_key].settings:
                continue
            for address in range(1, 248):
                if address in likely_addresses[type_key]:
                    continue
                if not on_progress(port, f"looking for {DEVICE_TYPES[type_key].label} at address {address} of 247"):
                    return found
                device = probe(port, type_key, address)
                if device is not None:
                    found.append(device)
            if found:
                break

    if found:
        on_progress(port, f"found {len(found)} device(s)")
    else:
        on_progress(port, "nothing recognised")
    return found


def probe(port, type_key, address):
    device_class = DEVICE_TYPES[type_key]
    settings = dict(device_class.settings)
    settings["port"] = port
    if address is None:
        device = device_class(**settings)
    else:
        settings["address"] = address
        device = device_class(**settings, timeout=MODBUS_TIMEOUT)
    try:
        device.connect()
        device.disconnect()
    except Exception:
        return None
    return {"type": type_key, **settings}
