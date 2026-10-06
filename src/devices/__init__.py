from src.devices.brooks_mfc import BrooksMFC
from src.devices.dewmaster import DewMaster
from src.devices.firesting_o2 import FireStingO2
from src.devices.julabo_chiller import JulaboChiller
from src.devices.servo_valve import ServoValve
from src.devices.vaisala_rh import VaisalaRH
from src.devices.vogtlin_mfc import VogtlinMFC

# The device catalog: every device type the app knows.
# The scan tries them in this order, so keep the quick-to-probe ones first.
DEVICE_TYPES = {
    "vogtlin_mfc": VogtlinMFC,
    "vaisala_rh": VaisalaRH,
    "brooks_mfc": BrooksMFC,
    "servo_valve": ServoValve,
    "julabo_chiller": JulaboChiller,
    "firesting_o2": FireStingO2,
    "dewmaster": DewMaster,
}
