from time import sleep
from microcontroller import Pin
from digitalio import DigitalInOut, Direction, DriveMode, Pull
from analogio import AnalogIn, AnalogOut

from config import EXT_PWR_PIN
from log import logger


class DummyManager:

    def deinit(self): ...


class IOManager:
    _io_map: dict[Pin, DigitalInOut | AnalogIn | AnalogOut]

    def __init__(self) -> None:
        self._io_map = {}
        self._i2c_manager = DummyManager()

    @property
    def i2c_manager(self):
        if isinstance(self._i2c_manager, DummyManager):
            from i2c import I2CManager

            self._i2c_manager = I2CManager()
        return self._i2c_manager

    def deinit_i2c(self):
        self._i2c_manager.deinit()

    def external_power(self, on: bool) -> None:
        """Enable/Disable external power"""
        if on:
            logger.log("Turning on external power")
        else:
            logger.log("Turning off external power")

        gate_io = self.digital(EXT_PWR_PIN)
        if gate_io.direction != Direction.OUTPUT:
            gate_io.switch_to_output(value=not on)
            return
        gate_io.value = not on
        sleep(0.1)  # ensure power state is ready before continuing

    def deinit(self, pin: Pin) -> None:
        """Deinit pin GPIO if exists"""
        existing_io = self._io_map.pop(pin)
        if existing_io is not None:
            logger.log(f"Deinit-ing pin: {pin}")
            existing_io.deinit()

    def get_digital_ios(self) -> list[DigitalInOut]:
        ios = [
            io
            for io in self._io_map.values()
            if isinstance(io, DigitalInOut) and io.direction == Direction.OUTPUT
        ]
        return ios

    def digital(self, pin: Pin) -> DigitalInOut:
        """Get or make a GPIO from pin"""
        existing_io = self._io_map.get(pin)
        if isinstance(existing_io, DigitalInOut):
            return existing_io
        elif existing_io is not None:
            logger.log("WARNING CLOBBERING EXISTING IO")
            self.deinit(pin)
        logger.log(f"Initializing DigitalInOut pin: {pin}")
        new_io = DigitalInOut(pin)
        self._io_map[pin] = new_io
        return new_io

    def digital_in(self, pin: Pin, pull: Pull | None = None):
        """Get or make digital in"""
        io = self.digital(pin)
        if io.direction != Direction.INPUT:
            logger.log(f"Switching to INPUT pin: {pin}")
            io.switch_to_input(pull=pull)
        io.pull = pull

    def digital_out(
        self, pin: Pin, value: bool, drive_mode: DriveMode = DriveMode.PUSH_PULL
    ):
        """Get or make digital out"""
        io = self.digital(pin)
        if io.direction != Direction.OUTPUT:
            logger.log(f"Switching to OUTPUT pin: {pin}")
            io.switch_to_output(value, drive_mode=drive_mode)
        io.value = value

    def analog_in(self, pin: Pin) -> AnalogIn:
        """Get or make analog in"""
        existing_io = self._io_map.get(pin)
        if isinstance(existing_io, AnalogIn):
            return existing_io
        elif existing_io is not None:
            logger.log("WARNING CLOBBERING EXISTING IO")
            self.deinit(pin)
        logger.log(f"Initializing AnalogIn pin: {pin}")
        new_io = AnalogIn(pin)
        self._io_map[pin] = new_io
        return new_io

    def analog_out(self, pin: Pin) -> AnalogOut:
        """Get or make analog out"""
        existing_io = self._io_map.get(pin)
        if isinstance(existing_io, AnalogOut):
            return existing_io
        elif existing_io is not None:
            logger.log("WARNING CLOBBERING EXISTING IO")
            self.deinit(pin)
        logger.log(f"Initializing AnalogOut pin: {pin}")
        new_io = AnalogOut(pin)
        self._io_map[pin] = new_io
        return new_io
