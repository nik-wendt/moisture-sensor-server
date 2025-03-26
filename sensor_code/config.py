from os import getenv
import board
import storage
import wifi

mac = wifi.radio.mac_address
MAC_ADDRESS = ":".join("{:02X}".format(b) for b in mac)


API_URL = getenv("API_URL", "")
WIFI_SSID = getenv("WIFI_SSID", "")
WIFI_PW = getenv("WIFI_PW", "")

DEEP_SLEEP_TIME = 30 * 60  # 30 minutes
LOW_BATT_VALUE = 33200  # somewhere around 3.4 volts

# SMD Expansion Board Pins
# BATT_REF_PIN = board.D1
# EXT_PWR_PIN = board.D0 # Gate pin

# Through Hole Expansion Board Pins
BATT_REF_PIN = board.D0
EXT_PWR_PIN = board.D1 # Gate pin

SDA_PIN = board.SDA
SCL_PIN = board.SCL

WRITE_TO_STORAGE = False
WRITE_TO_UART = True
LOGGER_FILEPATH = "log.txt"

try:
    mount = storage.getmount("/")
    WRITE_TO_STORAGE = not mount.readonly
except Exception:
    pass
