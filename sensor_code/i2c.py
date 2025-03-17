import board

from log import logger


class I2CManager:

    i2c = None

    def get(self):
        if self.i2c is None:
            logger.log("Initializing I2C")
            self.i2c = board.I2C()
        return self.i2c

    def deinit(self):
        if self.i2c is None:
            return
        logger.log("De-initializing I2C")
        self.i2c.deinit()
        self.i2c = None
