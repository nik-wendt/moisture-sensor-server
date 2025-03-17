import logging
import time
from datetime import datetime, timedelta, UTC, timezone

import requests

from db_setup import SessionLocal, StatusChoices
from db_setup import Sensors, SensorData

SLEEP_TIME = 300
NTFY_URL = "http://192.168.1.138:80/"
NTFY_TOPIC = "moisture_sensor"
# MISSING_SENSOR_THRESHOLD_TIME = 86400 # 1 day
MISSING_SENSOR_THRESHOLD_TIME = 300
SAMPLES_TO_AVERAGE = 3

log = logging.getLogger(__name__)


def get_db_session():
    db = SessionLocal()
    return db


def check_for_missing_devices(sensors, db=None):
    # Should find any device that hasn't updated in a specified interval.
    # check for the latest SensorData for each Sensor and if it's older than a day, send an alert.
    if not db:
        db = get_db_session()

    missing_sensors = []
    for sensor in sensors:
        latest_data = (
            db.query(SensorData)
            .filter(SensorData.sensor_id == sensor.id)
            .order_by(SensorData.created_at.desc()).first()
        )
        latest_sensor_data_datetime = latest_data.created_at
        if latest_data and latest_sensor_data_datetime > (datetime.now() - timedelta(seconds=MISSING_SENSOR_THRESHOLD_TIME)):
            continue
        else:
            missing_sensors.append(sensor)
    return missing_sensors


def check_for_threshold_breaches(sensors, db=None):
    # Should check if any SensorData value is above the threshold and send an alert.
    if not db:
        db = get_db_session()

    red_alerts = []
    yellow_alerts = []
    status_greens = []
    for sensor in sensors:
        readings = (
            db
            .query(SensorData)
            .join(Sensors, SensorData.sensor_id == Sensors.id)
            .filter(SensorData.sensor_id == sensor.id)
            .order_by(SensorData.created_at.desc())
            .limit(SAMPLES_TO_AVERAGE)
            .all()
        )

        average_of_past_x_samples = sum([data.value for data in readings]) / SAMPLES_TO_AVERAGE
        if average_of_past_x_samples > sensor.threshold_green:
            status_greens.append(sensor)
        elif average_of_past_x_samples > sensor.threshold_yellow:
            yellow_alerts.append(sensor)
        elif average_of_past_x_samples > 0:
            red_alerts.append(sensor)
    return red_alerts, yellow_alerts, status_greens


def send_ntfy_message(
        message,
        priority: int = 1,
        title: str = "Moisture Sensor Alert",
        tags: str = "alien"
):
    headers = {
        "Title": title,
        "Priority": str(priority), # 1-5 with 5 being the highest
        "Tags": tags
    }
    response = requests.post(f"{NTFY_URL}{NTFY_TOPIC}", headers=headers, data=message)
    print(response.status_code, response.text)


def main():
    while True:
        log.info("Checking for missing sensors & threshold breaches")
        db = get_db_session()
        sensors = db.query(Sensors).filter(Sensors.active == True)

        missing_sensors = check_for_missing_devices(sensors, db)
        log.info("Missing sensors: %s", missing_sensors)
        sensor_names = [sensor.name for sensor in missing_sensors]
        if missing_sensors:
            send_ntfy_message(
                f"The following sensors have not reported in over {MISSING_SENSOR_THRESHOLD_TIME} seconds:\n {"\n".join(sensor_names)}",
                priority=3,
                title="Missing Moisture Sensors",
                tags="see_no_evil"
            )
        log.info("Sent missing sensor alerts")

        red_alerts, yellow_alerts, status_greens = check_for_threshold_breaches(sensors, db)
        log.info("Red alerts: %s", red_alerts)
        log.info("Yellow alerts: %s", yellow_alerts)

        if red_alerts:
            sensor_names = [sensor.name for sensor in red_alerts]
            send_ntfy_message(
                f"The following sensors have breached their red threshold:\n {"\n".join(sensor_names)}",
                priority=5,
                title="Red Alert",
                tags="fire"
            )
            log.info("Sent red alerts")

        if yellow_alerts:
            sensor_names = [sensor.name for sensor in yellow_alerts]
            send_ntfy_message(
                f"The following sensors have breached their yellow threshold:\n {"\n".join(sensor_names)}",
                priority=4,
                title="Yellow Alert",
                tags="warning"
            )
            log.info("Sent yellow alerts")

        # save statuses to the database
        for sensor in red_alerts:
            sensor.status = StatusChoices.RED
        for sensor in yellow_alerts:
            sensor.status = StatusChoices.YELLOW
        for sensor in status_greens:
            sensor.status = StatusChoices.GREEN
        for sensor in missing_sensors:
            sensor.status = StatusChoices.BLACK

        db.commit()
        db.close()

        log.info("Sleeping for %s seconds", SLEEP_TIME)
        time.sleep(SLEEP_TIME)
        log.info("Waking up. Starting next check...")


if __name__ == "__main__":
    main()
