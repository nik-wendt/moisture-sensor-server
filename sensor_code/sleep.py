import alarm
import time

from log import logger


def deep_sleep(sleep_time, dios):
    logger.log(f"Going to sleep for {sleep_time}")
    monotonic_time = time.monotonic() + sleep_time
    logger.log(f"Alarm time {monotonic_time=}")
    time_alarm = alarm.time.TimeAlarm(monotonic_time=monotonic_time)
    logger.log(f"preserve_dios={str(dios)}")
    alarm.exit_and_deep_sleep_until_alarms(time_alarm, preserve_dios=dios)
