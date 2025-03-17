from config import WRITE_TO_STORAGE, WRITE_TO_UART, LOGGER_FILEPATH


class Logger:
    uart = None

    def __init__(self) -> None:
        self.fp = LOGGER_FILEPATH

        if WRITE_TO_STORAGE:
            with open(self.fp, mode="w") as file:
                file.write("Log file initialized")
        if WRITE_TO_UART:
            from board import UART

            self.uart = UART()

    def log(self, data):
        print(data)
        if WRITE_TO_STORAGE:
            with open(self.fp, mode="a") as file:
                file.write("\n")
                file.write(data)
        if WRITE_TO_UART:
            self.uart.write(f"{data}\n")


logger = Logger()
