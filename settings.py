import logging

from envparse import env

log = logging.getLogger(__name__)
DEBUG = env.bool('DEBUG', default=False)
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
log.setLevel(LOG_LEVEL)
log.info("Logging set up at level %s", LOG_LEVEL)

DATABASE_URL = env.str('DATABASE_URL', default='postgresql://postgres:postgres@localhost:5432/postgres')
log.info("Database URL: %s", DATABASE_URL)