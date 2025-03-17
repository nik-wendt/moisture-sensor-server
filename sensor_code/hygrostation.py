from alarm import sleep_memory
import adafruit_sht4x

from config import BATT_REF_PIN, LOW_BATT_VALUE, SDA_PIN, SCL_PIN
from enums import WakeError
from ioregistry import IOManager
from log import logger


class HygroStation:

    io: IOManager

    def __init__(self, io_manager: IOManager) -> None:
        self.io = io_manager

    def run(self):

        try:
            batt_value = self.measure_batt()
            self.io.external_power(True)
            temp, rel_hum = self.measure_hygro()
            self.io.external_power(False)
        except Exception as e:
            sleep_memory[0] = WakeError.MEASURE
            raise e

        if batt_value > LOW_BATT_VALUE:
            temp = int(temp)
            rel_hum = int(rel_hum)
            data = f"{temp=} {rel_hum=} {batt_value=}"
        else:
            data = f"LOW BATT {batt_value}"

        from transmit import send_data

        send_data(data)

        self.io.deinit_i2c()
        self.io.digital_out(SDA_PIN, False)
        self.io.digital_out(SCL_PIN, False)

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

    def measure_hygro(self) -> tuple[float, float]:
        logger.log("measuring hygrometer")
        i2c = self.io.i2c_manager.get()
        sht = adafruit_sht4x.SHT4x(i2c)
        temp_c, rel_hum = sht.measurements
        temp_f = temp_c * 1.8 + 32
        return temp_f, rel_hum
