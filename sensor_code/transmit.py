import socketpool
import ssl
import wifi
from alarm import sleep_memory

import adafruit_requests

from config import API_URL, WIFI_SSID, WIFI_PW
from log import logger
from enums import WakeError


def send_data(data):
    """Connect to wifi and send data"""
    try:
        logger.log("Connecting to WIFI")
        wifi.radio.connect(WIFI_SSID, WIFI_PW)
        logger.log("WIFI connected")
    except Exception as e:
        logger.log("COULD NOT CONNECT TO WIFI")
        sleep_memory[0] = WakeError.WIFI_CONN
        raise e

    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())

    try:
        logger.log(f"sending data: {data} to {API_URL}")
        response = requests.post(API_URL, json=data, timeout=100)
        if response.status_code != 200:
            logger.log(response.status_code)
            logger.log(response.content)
            sleep_memory[0] = WakeError.TRANSMIT
            raise ValueError(response.content)
        logger.log("sending complete")

        sleep_memory[0] = 0
    except Exception as e:
        print(e)
        raise e
