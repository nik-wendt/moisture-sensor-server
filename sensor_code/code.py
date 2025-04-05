import alarm
import supervisor
import time

from config import SLEEP_TIME_MINS, WIFI_SSID, WIFI_PW, API_URL
from soilstation import SoilStation
from log import logger
from ioregistry import IOManager
from enums import WakeError
from sleep import deep_sleep


class TryThing:
    def __init__(self, error_fn=None, wake_error=None):
        self.error_fn = error_fn
        self.wake_error = wake_error

    def __enter__(self):
        logger.log(f"doing step {self.wake_error}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_val:
            return
        logger.log(exc_type)
        logger.log(exc_val)
        logger.log(exc_tb)
        if self.wake_error is not None:
            alarm.sleep_memory[0] = self.wake_error
        elif not alarm.sleep_memory[0]:
            alarm.sleep_memory[0] = WakeError.UNKNOWN
        if self.error_fn is not None:
            self.error_fn()
        return True


def quick_sleep():
    deep_sleep(180, ())


def main():
    with TryThing(error_fn=quick_sleep, wake_error=WakeError.START):
        logger.log("Initializing IO Manager")
        io_manager = IOManager()

    with TryThing(error_fn=quick_sleep):
        logger.log("Running Main program HygroStation")
        station = SoilStation(io_manager)
        station.run()

    with TryThing(wake_error=WakeError.EXTERNAL_POWER_OFF):
        logger.log("Confirming External Power is off")
        io_manager.external_power(False)

    with TryThing(wake_error=WakeError.PRE_SLEEP):
        logger.log("getting digital IOs")
        preserve_dios = io_manager.get_digital_ios()

    with TryThing(wake_error=WakeError.SLEEP):
        logger.log(f"Going to sleep for {DEEP_SLEEP_TIME}")
        time_alarm = alarm.time.TimeAlarm(
            monotonic_time=time.monotonic() + DEEP_SLEEP_TIME
        )

    alarm.exit_and_deep_sleep_until_alarms(time_alarm, preserve_dios=preserve_dios)

def soil_sensor():
    from config import EXT_PWR_PIN
    while True:
        io_manager = IOManager()
        station = SoilStation(io_manager)
        print(station.measure_soil())
        print(io_manager.get_digital_ios())
        time.sleep(2)

if __name__ == "__main__":
    logger.log("\n\n")
    logger.log("Starting program")
    if not supervisor.runtime.usb_connected:
        main()
    else:
        # soil_sensor()
        main()
