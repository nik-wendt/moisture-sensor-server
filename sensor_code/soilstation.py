from alarm import sleep_memory
from analogio import AnalogIn

from config import BATT_REF_PIN, LOW_BATT_VALUE, SDA_PIN, MAC_ADDRESS
from enums import WakeError
from ioregistry import IOManager
from log import logger


class SoilStation:

    io: IOManager

    def __init__(self, io_manager: IOManager) -> None:
        self.io = io_manager

    def run(self):

        try:
            batt_value = self.measure_batt()
            self.io.external_power(True)
            soil_value = self.measure_soil()
            self.io.external_power(False)
        except Exception as e:
            sleep_memory[0] = WakeError.MEASURE
            raise e

        data = {"value": soil_value, "battery": batt_value, "mac_address": MAC_ADDRESS}
        from transmit import send_data

        send_data(data)

    def measure_batt(self) -> float:
        logger.log("measuring battery")
        batt = self.io.analog_in(BATT_REF_PIN)

        from time import sleep

        def delay_measure_batt():
            sleep(0.05)
            return batt.value

        batt_value = sum(delay_measure_batt() for _ in range(16)) / 16
        self.io.deinit(BATT_REF_PIN)

        return batt_value

    def measure_soil(self) -> int:
        logger.log("measuring soil")
        soil_pin = AnalogIn(SDA_PIN)
        soil_value = soil_pin.value
        soil_pin.deinit()
        return soil_value
